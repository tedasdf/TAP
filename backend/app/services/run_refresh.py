import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import get_db
from app.services.jobs import (
    derive_run_status,
    reconcile_run_status,
    refresh_job_from_slurm,
)
from app.services.metrics import upsert_metric_snapshot
from app.services.wandb_client import get_run_snapshot


class RunNotFoundError(Exception):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)


def ensure_run_exists_for_refresh(run_id: str) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        raise RunNotFoundError(run_id)

    return dict(row)


def create_run_event(
    conn,
    *,
    run_id: str,
    event_type: str,
    message: str,
    old_status: str | None = None,
    new_status: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO run_events (
            event_id,
            run_id,
            event_type,
            message,
            old_status,
            new_status,
            created_at,
            payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            run_id,
            event_type,
            message,
            old_status,
            new_status,
            utc_now_iso(),
            json_dumps(payload),
        ),
    )


def create_notification_row(
    conn,
    *,
    event_type: str,
    severity: str,
    title: str,
    message: str,
    run_id: str | None = None,
    job_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO notifications (
            notification_id,
            event_type,
            severity,
            title,
            message,
            run_id,
            job_id,
            timestamp,
            read_state
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            str(uuid.uuid4()),
            event_type,
            severity,
            title,
            message,
            run_id,
            job_id,
            utc_now_iso(),
        ),
    )


def create_run_status_notification(
    conn,
    *,
    run_id: str,
    old_status: str | None,
    new_status: str,
    job_id: str | None = None,
) -> None:
    if old_status == new_status:
        return

    status = new_status.lower()

    if status == "running":
        create_notification_row(
            conn,
            event_type="run_started",
            severity="info",
            title="Run started",
            message=f"Run {run_id} has started running.",
            run_id=run_id,
            job_id=job_id,
        )
        return

    if status == "completed":
        create_notification_row(
            conn,
            event_type="run_completed",
            severity="success",
            title="Run completed",
            message=f"Run {run_id} completed successfully.",
            run_id=run_id,
            job_id=job_id,
        )
        return

    if status == "failed":
        create_notification_row(
            conn,
            event_type="run_failed",
            severity="error",
            title="Run failed",
            message=f"Run {run_id} failed.",
            run_id=run_id,
            job_id=job_id,
        )
        return

    if status == "cancelled":
        create_notification_row(
            conn,
            event_type="run_cancelled",
            severity="warning",
            title="Run cancelled",
            message=f"Run {run_id} was cancelled.",
            run_id=run_id,
            job_id=job_id,
        )
        return


def metric_to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_metric_value(metrics: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in metrics:
            return metrics[name]

    return None


def get_best_validation_loss(conn, run_id: str) -> float | None:
    row = conn.execute(
        """
        SELECT MIN(validation_loss) AS best_validation_loss
        FROM metric_points
        WHERE run_id = ?
          AND validation_loss IS NOT NULL
        """,
        (run_id,),
    ).fetchone()

    if row is None:
        return None

    return metric_to_float(row["best_validation_loss"])


def notification_already_exists(
    conn,
    *,
    run_id: str,
    event_type: str,
    message: str,
) -> bool:
    row = conn.execute(
        """
        SELECT notification_id
        FROM notifications
        WHERE run_id = ?
          AND event_type = ?
          AND message = ?
        LIMIT 1
        """,
        (run_id, event_type, message),
    ).fetchone()

    return row is not None


def create_metric_notification_once(
    conn,
    *,
    run_id: str,
    event_type: str,
    severity: str,
    title: str,
    message: str,
    job_id: str | None = None,
) -> None:
    if notification_already_exists(
        conn,
        run_id=run_id,
        event_type=event_type,
        message=message,
    ):
        return

    create_notification_row(
        conn,
        event_type=event_type,
        severity=severity,
        title=title,
        message=message,
        run_id=run_id,
        job_id=job_id,
    )


def create_metric_alert_notifications(
    conn,
    *,
    run_id: str,
    metrics: dict[str, Any],
    previous_best_validation_loss: float | None,
    job_id: str | None = None,
) -> None:
    step = get_metric_value(metrics, "current_step", "step", "global_step")

    train_loss = metric_to_float(
        get_metric_value(metrics, "training_loss", "train_loss")
    )
    validation_loss = metric_to_float(
        get_metric_value(metrics, "validation_loss", "val_loss")
    )

    step_text = f" at step {step}" if step is not None else ""

    if train_loss is not None and math.isnan(train_loss):
        create_metric_notification_once(
            conn,
            run_id=run_id,
            event_type="metric_train_loss_nan",
            severity="error",
            title="Training loss is NaN",
            message=f"Run {run_id} has NaN training loss{step_text}.",
            job_id=job_id,
        )

    if validation_loss is not None and math.isnan(validation_loss):
        create_metric_notification_once(
            conn,
            run_id=run_id,
            event_type="metric_validation_loss_nan",
            severity="error",
            title="Validation loss is NaN",
            message=f"Run {run_id} has NaN validation loss{step_text}.",
            job_id=job_id,
        )

    if validation_loss is None or math.isnan(validation_loss):
        return

    if (
        previous_best_validation_loss is None
        or validation_loss < previous_best_validation_loss
    ):
        create_metric_notification_once(
            conn,
            run_id=run_id,
            event_type="metric_new_best_validation_loss",
            severity="success",
            title="New best validation loss",
            message=(
                f"Run {run_id} reached validation loss "
                f"{validation_loss:.6g}{step_text}."
            ),
            job_id=job_id,
        )


def refresh_run_by_id(run_id: str) -> dict[str, Any]:
    run_row = ensure_run_exists_for_refresh(run_id)
    checked_at = utc_now_iso()

    slurm_job_id = run_row.get("slurm_job_id")
    wandb_run_id = run_row.get("wandb_run_id")

    job_snapshot = None
    metrics_snapshot = None
    wandb_snapshot = None
    slurm_status = None
    wandb_status = None

    with get_db() as conn:
        if slurm_job_id:
            job_snapshot = refresh_job_from_slurm(slurm_job_id)

            existing_job = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (slurm_job_id,),
            ).fetchone()

            if existing_job:
                conn.execute(
                    """
                    UPDATE jobs
                    SET queue_state = ?, execution_state = ?, node_info = ?,
                        start_time = ?, end_time = ?, exit_status = ?
                    WHERE job_id = ?
                    """,
                    (
                        job_snapshot["queue_state"],
                        job_snapshot["execution_state"],
                        job_snapshot["node_info"],
                        job_snapshot["start_time"],
                        job_snapshot["end_time"],
                        job_snapshot["exit_status"],
                        slurm_job_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        job_id,
                        run_id,
                        queue_state,
                        execution_state,
                        node_info,
                        start_time,
                        end_time,
                        exit_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slurm_job_id,
                        run_id,
                        job_snapshot["queue_state"],
                        job_snapshot["execution_state"],
                        job_snapshot["node_info"],
                        job_snapshot["start_time"],
                        job_snapshot["end_time"],
                        job_snapshot["exit_status"],
                    ),
                )

            slurm_status = derive_run_status(
                current_status=run_row["status"],
                queue_state=job_snapshot["queue_state"],
                execution_state=job_snapshot["execution_state"],
                exit_status=job_snapshot["exit_status"],
            )

        if wandb_run_id:
            try:
                wandb_snapshot = get_run_snapshot(wandb_run_id)
                wandb_status = wandb_snapshot.get("tap_status")
                metrics = wandb_snapshot["metrics"]

                metric_payload = dict(metrics)
                metric_payload["source"] = "wandb"

                previous_best_validation_loss = get_best_validation_loss(conn, run_id)

                metrics_snapshot = upsert_metric_snapshot(
                    conn,
                    run_id,
                    metric_payload,
                )

                create_metric_alert_notifications(
                    conn,
                    run_id=run_id,
                    metrics=metric_payload,
                    previous_best_validation_loss=previous_best_validation_loss,
                    job_id=slurm_job_id,
                )

            except Exception as exc:
                wandb_snapshot = {"error": str(exc)}
                metrics_snapshot = None

                create_run_event(
                    conn,
                    run_id=run_id,
                    event_type="WANDB_SYNC_FAILED",
                    message=f"W&B sync failed: {exc}",
                    old_status=run_row["status"],
                    new_status=None,
                    payload={
                        "wandb_run_id": wandb_run_id,
                        "error": str(exc),
                    },
                )

                create_notification_row(
                    conn,
                    event_type="wandb_sync_failed",
                    severity="warning",
                    title="W&B sync failed",
                    message=f"W&B sync failed for run {run_id}: {exc}",
                    run_id=run_id,
                    job_id=slurm_job_id,
                )

        new_status = reconcile_run_status(
            current_status=run_row["status"],
            slurm_status=slurm_status,
            wandb_status=wandb_status,
        )

        old_status = run_row["status"]

        if new_status != old_status:
            create_run_event(
                conn,
                run_id=run_id,
                event_type="STATUS_CHANGED",
                message=f"Run status changed from {old_status} to {new_status}",
                old_status=old_status,
                new_status=new_status,
                payload={
                    "slurm_status": slurm_status,
                    "wandb_status": wandb_status,
                    "slurm_job_id": slurm_job_id,
                    "wandb_run_id": wandb_run_id,
                },
            )

            create_run_status_notification(
                conn,
                run_id=run_id,
                old_status=old_status,
                new_status=new_status,
                job_id=slurm_job_id,
            )

        conn.execute(
            """
            UPDATE runs
            SET status = ?,
                last_checked_at = ?
            WHERE run_id = ?
            """,
            (new_status, checked_at, run_id),
        )

        updated_run = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

        updated_job = None
        if slurm_job_id:
            job_row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (slurm_job_id,),
            ).fetchone()
            updated_job = dict(job_row) if job_row else None

    if updated_run is None:
        raise RunNotFoundError(run_id)

    run_dict = dict(updated_run)
    run_dict["config_overrides"] = json_loads(run_dict.get("config_overrides"))

    return {
        "run": run_dict,
        "job": updated_job,
        "metrics": metrics_snapshot,
        "sync": {
            "checked_at": checked_at,
            "slurm_status": slurm_status,
            "wandb_status": wandb_status,
            "wandb_state": (
                (wandb_snapshot or {}).get("wandb_state")
                if isinstance(wandb_snapshot, dict)
                else None
            ),
            "wandb_error": (
                (wandb_snapshot or {}).get("error")
                if isinstance(wandb_snapshot, dict)
                else None
            ),
        },
    }

def list_active_run_ids() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT run_id
            FROM runs
            WHERE status IN ('created', 'queued', 'running', 'unknown')
            ORDER BY datetime(created_at) ASC
            """
        ).fetchall()

    return [row["run_id"] for row in rows]