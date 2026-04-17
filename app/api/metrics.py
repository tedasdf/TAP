from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.schemas import MetricSnapshotUpsert
from app.services.wandb_client import get_run_snapshot

router = APIRouter(tags=["metrics"])


def ensure_run_exists(run_id: str) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT run_id FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


@router.put("/runs/{run_id}/metrics")
def upsert_metrics(run_id: str, payload: MetricSnapshotUpsert) -> dict[str, Any]:
    ensure_run_exists(run_id)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO metrics (
                run_id,
                current_step,
                current_epoch,
                training_loss,
                validation_loss,
                runtime,
                learning_rate,
                latest_metric_timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                current_step = excluded.current_step,
                current_epoch = excluded.current_epoch,
                training_loss = excluded.training_loss,
                validation_loss = excluded.validation_loss,
                runtime = excluded.runtime,
                learning_rate = excluded.learning_rate,
                latest_metric_timestamp = excluded.latest_metric_timestamp
            """,
            (
                run_id,
                payload.current_step,
                payload.current_epoch,
                payload.training_loss,
                payload.validation_loss,
                payload.runtime,
                payload.learning_rate,
                payload.latest_metric_timestamp,
            ),
        )

        row = conn.execute(
            "SELECT * FROM metrics WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    return dict(row)


@router.get("/runs/{run_id}/metrics")
def get_metrics(run_id: str) -> dict[str, Any]:
    ensure_run_exists(run_id)

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM metrics WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics found for run '{run_id}'",
        )

    return dict(row)


@router.post("/runs/{run_id}/sync-wandb")
def sync_metrics_from_wandb(run_id: str) -> dict[str, Any]:
    ensure_run_exists(run_id)

    with get_db() as conn:
        run_row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    if run_row is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    wandb_run_id = run_row["wandb_run_id"]
    if not wandb_run_id:
        raise HTTPException(
            status_code=400,
            detail="No wandb_run_id stored for this run",
        )

    try:
        snapshot = get_run_snapshot(wandb_run_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"W&B sync failed: {str(exc)}")

    metrics = snapshot["metrics"]

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO metrics (
                run_id,
                current_step,
                current_epoch,
                training_loss,
                validation_loss,
                runtime,
                learning_rate,
                latest_metric_timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(run_id) DO UPDATE SET
                current_step = excluded.current_step,
                current_epoch = excluded.current_epoch,
                training_loss = excluded.training_loss,
                validation_loss = excluded.validation_loss,
                runtime = excluded.runtime,
                learning_rate = excluded.learning_rate,
                latest_metric_timestamp = CURRENT_TIMESTAMP
            """,
            (
                run_id,
                metrics["current_step"],
                metrics["current_epoch"],
                metrics["training_loss"],
                metrics["validation_loss"],
                metrics["runtime"],
                metrics["learning_rate"],
            ),
        )

        current_status = run_row["status"]
        new_status = snapshot["tap_status"]

        if current_status != "cancelled":
            conn.execute(
                "UPDATE runs SET status = ? WHERE run_id = ?",
                (new_status, run_id),
            )

        updated_metrics = conn.execute(
            "SELECT * FROM metrics WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    return {
        "run_id": run_id,
        "wandb_run_id": wandb_run_id,
        "wandb_state": snapshot["wandb_state"],
        "wandb_url": snapshot["url"],
        "metrics": dict(updated_metrics),
    }