from __future__ import annotations

import math
import sqlite3
from typing import Any

from app.models.event import RunEvent
from app.models.job import Job
from app.models.metric import MetricPoint, MetricSnapshot, MetricSyncStatus
from app.models.notification import Notification
from app.models.run import Run
from app.repositories.push_repo import PushRepository
from app.repositories.run_repo import RunRepository
from app.schemas import RunCreate
from app.services.push_service import broadcast_push
from app.services.jobs import derive_run_status, reconcile_run_status, refresh_job_from_slurm
from app.services.launcher import (
    build_remote_error_log_path,
    build_remote_log_path,
    get_remote_git_state,
    launch_training_run,
    read_remote_config_file,
    run_ssh_command,
    launch_direct_run,
    poll_direct_process,
)
from app.services.wandb_client import get_run_history_since, get_run_snapshot


_STATUS_NOTIFICATION_MAP = {
    "running":   ("run_started",   "info",    "Run started",    "has started running"),
    "completed": ("run_completed", "success", "Run completed",  "completed successfully"),
    "failed":    ("run_failed",    "error",   "Run failed",     "failed"),
    "cancelled": ("run_cancelled", "warning", "Run cancelled",  "was cancelled"),
}


class RunService:
    """Owns the full run lifecycle. Access everything through self._runs.*."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._runs = RunRepository(conn)
        self._push = PushRepository(conn)

    def refresh(self, run_id: str) -> Run:
        run = self._runs.find(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        slurm_status: str | None = None
        wandb_status: str | None = None
        direct_status: str | None = None

        if not run.wandb_run_id:
            self._try_extract_wandb_run_id(run)
            run = self._runs.find(run_id)  # type: ignore[assignment]
            assert run is not None

        if run.launch_mode == "direct" and run.direct_pid:
            direct_status = poll_direct_process(run.direct_pid)
            new_status = direct_status
        else:
            if run.slurm_job_id:
                slurm_status = self._sync_slurm(run)
            if run.wandb_run_id:
                wandb_status = self._sync_wandb(run)
            new_status = reconcile_run_status(
                current_status=run.status,
                slurm_status=slurm_status,
                wandb_status=wandb_status,
            )

        job = self._runs.jobs.find(run.slurm_job_id) if run.slurm_job_id else None
        self._emit_status_change(run.status, new_status, run, job.job_id if job else None)
        self._runs.update_status(run_id, new_status)

        refreshed = self._runs.find(run_id)
        assert refreshed is not None
        return refreshed

    def cancel(self, run_id: str) -> Run:
        """scancel the SLURM job, update status, emit event/notification."""
        run = self._runs.find(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        if not run.slurm_job_id:
            raise ValueError("No Slurm job ID associated with this run")

        import shlex
        code, stdout, stderr = run_ssh_command(f"scancel {shlex.quote(run.slurm_job_id)}")
        if code != 0:
            raise RuntimeError(stderr or f"Failed to cancel Slurm job {run.slurm_job_id}")

        self._runs.update_status(run_id, "cancelled", error_message="Cancelled from TAP")
        self._runs.jobs.update(run.slurm_job_id, queue_state="cancelled", execution_state="cancelled")

        old_status = run.status
        self._runs.events.create(RunEvent(
            event_id=self._runs.events._new_id(),
            run_id=run_id,
            event_type="RUN_CANCELLED",
            message=f"Run cancelled from TAP. Slurm job {run.slurm_job_id} was cancelled.",
            old_status=old_status,
            new_status="cancelled",
            created_at=self._runs.events._utc_now(),
            payload={"slurm_job_id": run.slurm_job_id, "stdout": stdout, "stderr": stderr},
        ))
        self._emit_status_notification(old_status, "cancelled", run_id, run.slurm_job_id)

        cancelled = self._runs.find(run_id)
        assert cancelled is not None
        return cancelled

    def create(self, payload: RunCreate) -> Run:
        """Launch or defer a training run."""
        from app.config import settings
        import uuid
        from app.repositories.base import BaseRepository

        run_id = str(uuid.uuid4())
        created_at = BaseRepository._utc_now()

        git_state = get_remote_git_state()
        git_commit = _resolve_git_commit(payload.git_commit, git_state["commit"])

        status = "created"
        slurm_job_id: str | None = None
        error_message: str | None = None
        log_path: str | None = None
        error_log_path: str | None = None

        launch_command: str | None = None
        if payload.launch_now:
            if payload.launch_mode == "direct":
                code, stdout, stderr, pid, direct_log_path, launch_command = launch_direct_run(
                    run_name=payload.name,
                    run_id=run_id,
                    git_commit=git_commit,
                    config_path=payload.config_path,
                    config_overrides=payload.config_overrides,
                )
                if code == 0 and pid:
                    status = "running"  # direct runs start immediately, no queue
                else:
                    status = "failed"
                    error_message = stderr or f"Direct launch failed with exit code {code}"
            else:
                code, stdout, stderr, slurm_job_id, launch_command = launch_training_run(
                    run_name=payload.name,
                    run_id=run_id,
                    git_commit=git_commit,
                    config_path=payload.config_path,
                    config_overrides=payload.config_overrides,
                    submit_script=payload.submit_script,
                )
                combined = "\n".join(p for p in [stdout, stderr] if p)
                if code == 0 and slurm_job_id:
                    status = "queued"
                    log_path = build_remote_log_path(payload.name, slurm_job_id)
                    error_log_path = build_remote_error_log_path(payload.name, slurm_job_id)
                elif code == 0:
                    status = "created"
                    error_message = "Launch succeeded but no Slurm job ID was parsed"
                    slurm_job_id = None
                else:
                    status = "failed"
                    error_message = combined or f"Launch failed with exit code {code}"
        
        config_file_snapshot = read_remote_config_file(payload.config_path)
        config_snapshot = _build_config_snapshot(
            payload=payload,
            git_commit=git_commit,
            run_id=run_id,
            created_at=created_at,
            status=status,
            slurm_job_id=slurm_job_id,
            config_file_snapshot=config_file_snapshot,
            launch_command=launch_command,
        )

        run = Run(
            run_id=run_id,
            name=payload.name,
            status=status,
            git_commit=git_commit,
            config_path=payload.config_path,
            created_at=created_at,
            config_overrides=payload.config_overrides or {},
            config_snapshot=config_snapshot,
            wandb_config_ref=payload.wandb_config_ref,
            slurm_job_id=slurm_job_id,
            wandb_run_id=payload.wandb_run_id,
            error_message=error_message,
            launch_mode=payload.launch_mode,
            template_id=payload.template_id,
            direct_pid=pid if payload.launch_mode == "direct" else None,
            direct_log_path=direct_log_path if payload.launch_mode == "direct" else None,
        )

        created_run = self._runs.create(run)

        self._runs.events.create(RunEvent(
            event_id=self._runs.events._new_id(),
            run_id=run_id,
            event_type="RUN_CREATED",
            message="Run created",
            new_status=status,
            created_at=self._runs.events._utc_now(),
            payload={
                "name": payload.name,
                "config_path": payload.config_path,
                "git_commit": git_commit,
                "launch_now": payload.launch_now,
            },
        ))

        if slurm_job_id:
            self._runs.events.create(RunEvent(
                event_id=self._runs.events._new_id(),
                run_id=run_id,
                event_type="SLURM_JOB_SUBMITTED",
                message=f"Slurm job {slurm_job_id} submitted",
                new_status=status,
                created_at=self._runs.events._utc_now(),
                payload={"slurm_job_id": slurm_job_id, "log_path": log_path, "error_log_path": error_log_path},
            ))
            self._runs.jobs.create(Job(
                job_id=slurm_job_id,
                run_id=run_id,
                queue_state="queued",
                log_path=log_path,
                error_log_path=error_log_path,
            ))

        return created_run

    def _try_extract_wandb_run_id(self, run: Run) -> None:
        log_path = run.direct_log_path
        if not log_path and run.slurm_job_id:
            job = self._runs.jobs.find(run.slurm_job_id)
            if job:
                log_path = job.log_path
        if not log_path:
            return
        try:
            code, stdout, _ = run_ssh_command(f"grep -m1 'TAP_WANDB_RUN_ID=' {log_path} 2>/dev/null || true")
            if code == 0 and "TAP_WANDB_RUN_ID=" in stdout:
                wandb_run_id = stdout.strip().split("TAP_WANDB_RUN_ID=", 1)[1].strip()
                if wandb_run_id:
                    self._runs.update(run.run_id, wandb_run_id=wandb_run_id)
        except Exception:
            pass

    def _sync_slurm(self, run: Run) -> str:
        job_snapshot = refresh_job_from_slurm(run.slurm_job_id)  # type: ignore[arg-type]

        existing = self._runs.jobs.find(run.slurm_job_id)  # type: ignore[arg-type]
        if existing:
            self._runs.jobs.update(
                run.slurm_job_id,  # type: ignore[arg-type]
                queue_state=job_snapshot["queue_state"],
                execution_state=job_snapshot["execution_state"],
                node_info=job_snapshot["node_info"],
                start_time=job_snapshot["start_time"],
                end_time=job_snapshot["end_time"],
                exit_status=job_snapshot["exit_status"],
            )
        else:
            self._runs.jobs.create(Job(
                job_id=run.slurm_job_id,  # type: ignore[arg-type]
                run_id=run.run_id,
                queue_state=job_snapshot["queue_state"],
                execution_state=job_snapshot["execution_state"],
                node_info=job_snapshot["node_info"],
                start_time=job_snapshot["start_time"],
                end_time=job_snapshot["end_time"],
                exit_status=job_snapshot["exit_status"],
            ))

        return derive_run_status(
            current_status=run.status,
            queue_state=job_snapshot["queue_state"],
            execution_state=job_snapshot["execution_state"],
            exit_status=job_snapshot["exit_status"],
        )

    def _sync_wandb(self, run: Run) -> str | None:
        try:
            # Snapshot — status + summary metrics for the overview card
            wandb_snapshot = get_run_snapshot(run.wandb_run_id)  # type: ignore[arg-type]
            metrics_dict = dict(wandb_snapshot["metrics"])

            snapshot = MetricSnapshot(
                run_id=run.run_id,
                current_step=metrics_dict.get("current_step"),
                current_epoch=metrics_dict.get("current_epoch"),
                training_loss=metrics_dict.get("training_loss"),
                validation_loss=metrics_dict.get("validation_loss"),
                runtime=metrics_dict.get("runtime"),
                learning_rate=metrics_dict.get("learning_rate"),
                latest_metric_timestamp=metrics_dict.get("latest_metric_timestamp"),
            )
            self._runs.metrics.upsert_snapshot(snapshot)

            # History — fetch every step we haven't stored yet
            last_step = self._runs.metrics.get_last_step(run.run_id, source="wandb")
            min_step = (last_step + 1) if last_step is not None else 0
            new_rows = get_run_history_since(run.wandb_run_id, min_step=min_step)  # type: ignore[arg-type]
            for row in new_rows:
                self._runs.metrics.add_point(MetricPoint(
                    run_id=run.run_id,
                    step=row["step"],
                    source="wandb",
                    metrics=row["metrics"],
                ))

            self._create_metric_alert_notifications(run.run_id, metrics_dict)

            sync_status = MetricSyncStatus(
                run_id=run.run_id,
                source="wandb",
                status="success",
                last_finished_at=self._runs.metrics._utc_now(),
                points_synced=self._runs.metrics.count_points(run.run_id, "wandb"),
            )
            self._runs.metrics.upsert_sync_status(sync_status)

            return wandb_snapshot.get("tap_status")

        except Exception as exc:
            self._runs.events.create(RunEvent(
                event_id=self._runs.events._new_id(),
                run_id=run.run_id,
                event_type="WANDB_SYNC_FAILED",
                message=f"W&B sync failed: {exc}",
                old_status=run.status,
                created_at=self._runs.events._utc_now(),
                payload={"wandb_run_id": run.wandb_run_id, "error": str(exc)},
            ))
            if not self._runs.notifications.exists(run.run_id, "wandb_sync_failed"):
                self._runs.notifications.create(Notification(
                    notification_id=self._runs.notifications._new_id(),
                    event_type="wandb_sync_failed",
                    severity="warning",
                    title="W&B sync failed",
                    message=f"W&B sync failed for run {run.run_id}: {exc}",
                    timestamp=self._runs.notifications._utc_now(),
                    run_id=run.run_id,
                ))
            return None

    def _emit_status_change(
        self,
        old_status: str,
        new_status: str,
        run: Run,
        job_id: str | None,
    ) -> None:
        if old_status == new_status:
            return
        self._runs.events.create(RunEvent(
            event_id=self._runs.events._new_id(),
            run_id=run.run_id,
            event_type="STATUS_CHANGED",
            message=f"Run status changed from {old_status} to {new_status}",
            old_status=old_status,
            new_status=new_status,
            created_at=self._runs.events._utc_now(),
            payload={"slurm_job_id": run.slurm_job_id, "wandb_run_id": run.wandb_run_id},
        ))
        self._emit_status_notification(old_status, new_status, run.run_id, job_id)

    def _emit_status_notification(
        self,
        old_status: str | None,
        new_status: str,
        run_id: str,
        job_id: str | None,
    ) -> None:
        if old_status == new_status:
            return
        entry = _STATUS_NOTIFICATION_MAP.get(new_status.lower())
        if not entry:
            return
        event_type, severity, title, verb = entry
        if self._runs.notifications.exists(run_id, event_type):
            return
        self._runs.notifications.create(Notification(
            notification_id=self._runs.notifications._new_id(),
            event_type=event_type,
            severity=severity,
            title=title,
            message=f"Run {run_id} {verb}.",
            timestamp=self._runs.notifications._utc_now(),
            run_id=run_id,
            job_id=job_id,
        ))
        broadcast_push(self._push.get_all(), title=title, body=f"Run {run_id} {verb}.")

    def _create_metric_alert_notifications(
        self,
        run_id: str,
        metrics: dict[str, Any],
    ) -> None:
        previous_best = self._runs.metrics.get_best_validation_loss(run_id)
        step = metrics.get("current_step") or metrics.get("step") or metrics.get("global_step")
        step_text = f" at step {step}" if step is not None else ""

        train_loss = _to_float(metrics.get("training_loss") or metrics.get("train_loss"))
        val_loss = _to_float(metrics.get("validation_loss") or metrics.get("val_loss"))

        if train_loss is not None and math.isnan(train_loss):
            msg = f"Run {run_id} has NaN training loss{step_text}."
            if not self._runs.notifications.exists(run_id, "metric_train_loss_nan"):
                self._runs.notifications.create(Notification(
                    notification_id=self._runs.notifications._new_id(),
                    event_type="metric_train_loss_nan",
                    severity="error",
                    title="Training loss is NaN",
                    message=msg,
                    timestamp=self._runs.notifications._utc_now(),
                    run_id=run_id,
                ))

        if val_loss is not None and math.isnan(val_loss):
            msg = f"Run {run_id} has NaN validation loss{step_text}."
            if not self._runs.notifications.exists(run_id, "metric_validation_loss_nan"):
                self._runs.notifications.create(Notification(
                    notification_id=self._runs.notifications._new_id(),
                    event_type="metric_validation_loss_nan",
                    severity="error",
                    title="Validation loss is NaN",
                    message=msg,
                    timestamp=self._runs.notifications._utc_now(),
                    run_id=run_id,
                ))

        if val_loss is None or math.isnan(val_loss):
            return

        if previous_best is None or val_loss < previous_best:
            msg = f"Run {run_id} reached validation loss {val_loss:.6g}{step_text}."
            if not self._runs.notifications.exists(run_id, "metric_new_best_validation_loss", msg):
                self._runs.notifications.create(Notification(
                    notification_id=self._runs.notifications._new_id(),
                    event_type="metric_new_best_validation_loss",
                    severity="success",
                    title="New best validation loss",
                    message=msg,
                    timestamp=self._runs.notifications._utc_now(),
                    run_id=run_id,
                ))


class RunNotFoundError(Exception):
    pass


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_git_commit(payload_commit: str | None, remote_commit: str) -> str:
    requested = (payload_commit or "").strip()
    if not requested or requested.upper() == "HEAD":
        return remote_commit
    return requested


def _build_config_snapshot(
    *,
    payload: Any,
    git_commit: str,
    run_id: str,
    created_at: str,
    status: str,
    slurm_job_id: str | None = None,
    config_file_snapshot: dict[str, Any] | None = None,
    launch_command: str | None = None,
) -> dict[str, Any]:
    from app.config import settings

    config_overrides = payload.config_overrides or {}
    submitted_at = created_at if payload.launch_now else None

    if config_file_snapshot is None:
        config_file_snapshot = {
            "path": payload.config_path,
            "source": None,
            "content": None,
            "error": "Config file was not snapshotted",
        }

    return {
        "run_id": run_id,
        "name": payload.name,
        "git_commit": git_commit,
        "config_path": payload.config_path,
        "config_overrides": config_overrides,
        "config_file": config_file_snapshot,
        "submit_script": payload.submit_script,
        "launch_now": payload.launch_now,
        "status_at_creation": status,
        "slurm_job_id": slurm_job_id,
        "wandb_config_ref": payload.wandb_config_ref,
        "wandb_run_id": payload.wandb_run_id,
        "created_at": created_at,
        "launch_metadata": {
            "submit_script": payload.submit_script,
            "remote_repo_path": settings.TAP_M3_REPO_PATH,
            "remote_host": settings.TAP_M3_HOST,
            "working_directory": settings.TAP_M3_REPO_PATH,
            "submitted_at": submitted_at,
            "launch_command": launch_command,
        },
        "data_references": {
            "dataset": config_overrides.get("data.dataset_name"),
            "tokenizer": config_overrides.get("tokenizer.path"),
            "raw_config_path": payload.config_path,
        },
    }
