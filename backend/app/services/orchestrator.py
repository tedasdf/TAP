"""Single background orchestrator for the full run lifecycle.

One asyncio loop, two phases per tick:

  Phase 1 — Promote:  find 'created' template runs and submit them to SLURM
  Phase 2 — Refresh:  poll SLURM + sync W&B for every active run
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.db import get_db
from app.models.event import RunEvent
from app.models.job import Job
from app.models.notification import Notification
from app.repositories.run_repo import RunRepository
from app.repositories.template_repo import TemplateRepository
from app.services.launcher import (
    build_remote_error_log_path,
    build_remote_log_path,
    launch_training_run,
)
from app.services.run_service import RunService

log = logging.getLogger(__name__)


@dataclass
class OrchestratorStatus:
    enabled: bool = False
    running: bool = False
    interval_seconds: int = 60
    last_cycle_started_at: str | None = None
    last_cycle_finished_at: str | None = None
    last_cycle_run_count: int = 0
    last_cycle_error_count: int = 0
    last_cycle_promoted_count: int = 0
    last_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "running": self.running,
            "interval_seconds": self.interval_seconds,
            "last_cycle_started_at": self.last_cycle_started_at,
            "last_cycle_finished_at": self.last_cycle_finished_at,
            "last_cycle_run_count": self.last_cycle_run_count,
            "last_cycle_error_count": self.last_cycle_error_count,
            "last_cycle_promoted_count": self.last_cycle_promoted_count,
            "last_error": self.last_error,
        }


class TemplatePromoter:
    """Finds 'created' template runs and submits them to SLURM up to the concurrency cap."""

    def __init__(self, cap: int) -> None:
        self._cap = cap

    def _find_runs_to_promote(self) -> list[dict]:
        with get_db() as conn:
            return TemplateRepository(conn).find_pending_runs(self._cap)

    def _submit(self, run: dict) -> None:
        run_id = run["run_id"]
        run_name = run["name"]

        slurm_job_id: str | None = None
        log_path: str | None = None
        error_log_path: str | None = None
        error_message: str | None = None
        new_status = "failed"

        try:
            code, stdout, stderr, slurm_job_id = launch_training_run(
                run_name=run_name,
                git_commit=run["git_commit"],
                config_path=run["config_path"],
            )
            combined = "\n".join(p for p in [stdout, stderr] if p)
            if code == 0 and slurm_job_id:
                new_status = "queued"
                log_path = build_remote_log_path(run_name, slurm_job_id)
                error_log_path = build_remote_error_log_path(run_name, slurm_job_id)
            elif code == 0:
                new_status = "created"
                error_message = "Launch succeeded but no Slurm job ID was parsed"
                slurm_job_id = None
            else:
                error_message = combined or f"sbatch failed with exit code {code}"
                slurm_job_id = None
        except Exception as exc:
            log.exception("TemplatePromoter: launch failed for run %s", run_id)
            error_message = str(exc)

        with get_db() as conn:
            runs = RunRepository(conn)

            runs.update_status(run_id, new_status, error_message=error_message)
            runs.update(run_id, slurm_job_id=slurm_job_id)

            runs.events.create(RunEvent(
                event_id=runs.events._new_id(),
                run_id=run_id,
                event_type="TEMPLATE_RUN_PROMOTED",
                message=(
                    f"Promoted from template queue: Slurm job {slurm_job_id}"
                    if slurm_job_id
                    else f"Promotion attempted but failed: {error_message}"
                ),
                old_status="created",
                new_status=new_status,
                created_at=runs.events._utc_now(),
                payload={"slurm_job_id": slurm_job_id, "log_path": log_path},
            ))

            if slurm_job_id:
                runs.jobs.create_or_ignore(Job(
                    job_id=slurm_job_id,
                    run_id=run_id,
                    queue_state="queued",
                    log_path=log_path,
                    error_log_path=error_log_path,
                ))

    async def run(self) -> int:
        to_promote = await asyncio.to_thread(self._find_runs_to_promote)
        if not to_promote:
            return 0
        log.info("TemplatePromoter: promoting %d run(s)", len(to_promote))
        for run in to_promote:
            await asyncio.to_thread(self._submit, run)
        return len(to_promote)


class RunRefresher:
    """Polls SLURM and syncs W&B metrics for every active run."""

    def _refresh_one(self, run_id: str) -> None:
        with get_db() as conn:
            RunService(conn).refresh(run_id)

    def _record_failure(self, run_id: str, error: Exception) -> None:
        message = f"Background refresh failed for run {run_id}: {error}"
        with get_db() as conn:
            runs = RunRepository(conn)

            runs.events.create(RunEvent(
                event_id=runs.events._new_id(),
                run_id=run_id,
                event_type="BACKGROUND_REFRESH_FAILED",
                message=message,
                created_at=runs.events._utc_now(),
                payload={"error": str(error), "source": "orchestrator"},
            ))

            if not runs.notifications.exists(run_id, "background_refresh_failed", message):
                runs.notifications.create(Notification(
                    notification_id=runs.notifications._new_id(),
                    event_type="background_refresh_failed",
                    severity="warning",
                    title="Background refresh failed",
                    message=message,
                    timestamp=runs.notifications._utc_now(),
                    run_id=run_id,
                ))

    def _list_active_run_ids(self) -> list[str]:
        with get_db() as conn:
            return [r.run_id for r in RunRepository(conn).list_active()]

    def _check_stuck_runs(self) -> None:
        from app.repositories.push_repo import PushRepository
        from app.services.push_service import broadcast_push

        with get_db() as conn:
            runs = RunRepository(conn)
            rows = conn.execute(
                """
                SELECT run_id FROM runs
                WHERE status = 'queued'
                  AND created_at < datetime('now', '-5 hours')
                """
            ).fetchall()
            for row in rows:
                run_id = row["run_id"]
                event_type = "run_stuck_queued"
                if runs.notifications.exists(run_id, event_type):
                    continue
                msg = f"Run {run_id} has been queued for over 5 hours."
                runs.notifications.create(Notification(
                    notification_id=runs.notifications._new_id(),
                    event_type=event_type,
                    severity="warning",
                    title="Run stuck in queue",
                    message=msg,
                    timestamp=runs.notifications._utc_now(),
                    run_id=run_id,
                ))
                broadcast_push(PushRepository(conn).get_all(), title="Run stuck in queue", body=msg)

    async def run(self) -> tuple[int, int]:
        run_ids: list[str] = await asyncio.to_thread(self._list_active_run_ids)
        errors = 0
        for run_id in run_ids:
            try:
                await asyncio.to_thread(self._refresh_one, run_id)
            except Exception as exc:
                errors += 1
                try:
                    await asyncio.to_thread(self._record_failure, run_id, exc)
                except Exception:
                    log.exception("RunRefresher: failed to record failure for %s", run_id)
        try:
            await asyncio.to_thread(self._check_stuck_runs)
        except Exception:
            log.exception("RunRefresher: stuck-run check failed")
        return len(run_ids), errors


class Orchestrator:
    """Coordinates the full run lifecycle in a single background asyncio loop."""

    def __init__(self) -> None:
        self.status = OrchestratorStatus()
        self._promoter = TemplatePromoter(cap=settings.TAP_MAX_CONCURRENT_JOBS)
        self._refresher = RunRefresher()
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None

    @staticmethod
    def _is_enabled() -> bool:
        v = os.environ.get("TAP_BACKGROUND_REFRESH_ENABLED")
        return v.lower() in {"1", "true", "yes", "on"} if v else False

    @staticmethod
    def _interval() -> int:
        try:
            return max(10, int(os.environ.get("TAP_BACKGROUND_REFRESH_INTERVAL_SECONDS", "60")))
        except ValueError:
            return 60

    async def _loop(self, stop: asyncio.Event) -> None:
        interval = self._interval()
        self.status.running = True
        self.status.interval_seconds = interval
        log.info("Orchestrator started (interval=%ds)", interval)

        try:
            while not stop.is_set():
                self.status.last_cycle_started_at = datetime.now(timezone.utc).isoformat()
                self.status.last_cycle_error_count = 0
                self.status.last_error = None

                try:
                    self.status.last_cycle_promoted_count = await self._promoter.run()
                except Exception as exc:
                    log.exception("Orchestrator: promote phase error")
                    self.status.last_error = f"promote: {exc}"

                try:
                    run_count, errors = await self._refresher.run()
                    self.status.last_cycle_run_count = run_count
                    self.status.last_cycle_error_count += errors
                    if errors:
                        self.status.last_error = f"{errors} refresh error(s) this cycle"
                except Exception as exc:
                    log.exception("Orchestrator: refresh phase error")
                    self.status.last_error = f"refresh: {exc}"

                self.status.last_cycle_finished_at = datetime.now(timezone.utc).isoformat()

                try:
                    await asyncio.wait_for(stop.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            self.status.running = False
            log.info("Orchestrator stopped")

    def start(self) -> None:
        if not self._is_enabled():
            self.status.enabled = False
            self.status.running = False
            self.status.interval_seconds = self._interval()
            log.info("Orchestrator disabled (TAP_BACKGROUND_REFRESH_ENABLED not set)")
            return

        if self._task is not None and not self._task.done():
            return

        self.status.enabled = True
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._loop(self._stop_event))

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                self._task.cancel()
        self._task = None
        self._stop_event = None


orchestrator = Orchestrator()
