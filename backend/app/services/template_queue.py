"""Background worker that promotes deferred template runs as SLURM slots open."""

import logging
import threading
import time

from app.config import settings
from app.db import get_db
from app.services.launcher import (
    build_remote_error_log_path,
    build_remote_log_path,
    launch_training_run,
)
from app.services.run_events import create_run_event

log = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60


def _promote_waiting_runs() -> None:
    cap = settings.TAP_MAX_CONCURRENT_JOBS

    # Read phase: find all created template runs and their template's active count.
    # A single query avoids a round-trip per template.
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                r.run_id, r.name, r.git_commit, r.config_path, r.template_id,
                (
                    SELECT COUNT(*) FROM runs r2
                    WHERE r2.template_id = r.template_id
                      AND r2.status IN ('queued', 'running')
                ) AS active_count
            FROM runs r
            WHERE r.status = 'created' AND r.template_id IS NOT NULL
            ORDER BY r.template_id, r.created_at ASC
            """,
        ).fetchall()

    # For each template, only promote runs while active_count + promoted < cap.
    slots_used: dict[str, int] = {}
    to_promote: list[dict] = []

    for row in rows:
        tid: str = row["template_id"]
        if tid not in slots_used:
            slots_used[tid] = row["active_count"]
        if slots_used[tid] >= cap:
            continue
        to_promote.append(dict(row))
        slots_used[tid] += 1

    if not to_promote:
        return

    log.info("Template queue: promoting %d deferred run(s)", len(to_promote))

    # Launch phase: SSH calls happen outside the DB connection.
    for run in to_promote:
        run_id: str = run["run_id"]
        run_name: str = run["name"]
        git_commit: str = run["git_commit"]
        config_path: str = run["config_path"]

        slurm_job_id: str | None = None
        log_path: str | None = None
        error_log_path: str | None = None
        error_message: str | None = None
        new_status = "failed"

        try:
            code, stdout, stderr, slurm_job_id = launch_training_run(
                run_name=run_name,
                git_commit=git_commit,
                config_path=config_path,
            )
            combined = "\n".join(p for p in [stdout, stderr] if p)

            if code == 0 and slurm_job_id:
                new_status = "queued"
                log_path = build_remote_log_path(run_name, slurm_job_id)
                error_log_path = build_remote_error_log_path(run_name, slurm_job_id)
            elif code == 0:
                # sbatch succeeded but we couldn't parse a job ID — leave deferred
                new_status = "created"
                error_message = "Launch succeeded but no Slurm job ID was parsed"
                slurm_job_id = None
            else:
                error_message = combined or f"sbatch failed with exit code {code}"
                slurm_job_id = None

        except Exception:
            log.exception("Template queue: launch failed for run %s", run_id)
            error_message = "Unexpected error during promotion"
            slurm_job_id = None

        with get_db() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, slurm_job_id = ?, error_message = ?
                WHERE run_id = ?
                """,
                (new_status, slurm_job_id, error_message, run_id),
            )
            create_run_event(
                conn,
                run_id=run_id,
                event_type="TEMPLATE_RUN_PROMOTED",
                message=(
                    f"Promoted from template queue: Slurm job {slurm_job_id}"
                    if slurm_job_id
                    else f"Promotion attempted but failed: {error_message}"
                ),
                old_status="created",
                new_status=new_status,
                payload={"slurm_job_id": slurm_job_id, "log_path": log_path},
            )
            if slurm_job_id:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO jobs (
                        job_id, run_id, queue_state, execution_state,
                        node_info, start_time, end_time, exit_status,
                        log_path, error_log_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slurm_job_id, run_id, "queued", None,
                        None, None, None, None,
                        log_path, error_log_path,
                    ),
                )


def _worker_loop() -> None:
    while True:
        try:
            _promote_waiting_runs()
        except Exception:
            log.exception("Template queue: poll cycle error")
        time.sleep(POLL_INTERVAL_SECONDS)


def start_template_queue_worker() -> None:
    t = threading.Thread(target=_worker_loop, daemon=True, name="template-queue-worker")
    t.start()
    log.info(
        "Template queue worker started (interval=%ds, cap=%d)",
        POLL_INTERVAL_SECONDS,
        settings.TAP_MAX_CONCURRENT_JOBS,
    )
