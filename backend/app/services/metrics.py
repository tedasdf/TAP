from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.schemas import (
    LatestMetricsResponse,
    MetricHistoryPointResponse,
    MetricSnapshotUpsert,
)

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
        latest = upsert_latest_metrics(
            conn,
            run_id=run_id,
            current_step=payload.current_step,
            current_epoch=payload.current_epoch,
            training_loss=payload.training_loss,
            validation_loss=payload.validation_loss,
            runtime=payload.runtime,
            learning_rate=payload.learning_rate,
            latest_metric_timestamp=payload.latest_metric_timestamp,
        )
        insert_metric_history_from_latest(
            conn,
            run_id=run_id,
            current_step=payload.current_step,
            current_epoch=payload.current_epoch,
            training_loss=payload.training_loss,
            validation_loss=payload.validation_loss,
            runtime=payload.runtime,
            learning_rate=payload.learning_rate,
            source="manual",
            created_at=payload.latest_metric_timestamp,
        )

    return latest


@router.get("/runs/{run_id}/metrics/latest", response_model=LatestMetricsResponse | None)
def get_latest_run_metrics(run_id: str) -> dict[str, Any] | None:
    ensure_run_exists(run_id)

    with get_db() as conn:
        return get_latest_metrics(conn, run_id)


@router.get("/runs/{run_id}/metrics/history", response_model=list[MetricHistoryPointResponse])
def get_run_metric_history(run_id: str) -> list[dict[str, Any]]:
    ensure_run_exists(run_id)

    with get_db() as conn:
        return get_metric_history(conn, run_id)


@router.get("/runs/{run_id}/metrics")
def get_metrics(run_id: str) -> dict[str, Any]:
    """Backward-compatible latest metrics endpoint."""

    ensure_run_exists(run_id)

    with get_db() as conn:
        row = get_latest_metrics(conn, run_id)

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics found for run '{run_id}'",
        )

    return row


@router.post("/runs/{run_id}/metrics/sync")
def sync_run_metrics(run_id: str) -> dict[str, Any]:
    """Preferred M3 metric sync endpoint.

    Syncs W&B history into metric_history when a wandb_run_id is available.
    Falls back to a clear 400 if the run has no W&B run attached.
    """

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
        with get_db() as conn:
            sync_result = sync_wandb_metric_history(
                conn,
                run_id=run_id,
                wandb_run_id=wandb_run_id,
            )
            latest = get_latest_metrics(conn, run_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"W&B history sync failed: {str(exc)}")

    return {
        **sync_result,
        "latest_metrics": latest,
        "status": "ok",
    }


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
        updated_metrics = upsert_latest_metrics(
            conn,
            run_id=run_id,
            current_step=metrics["current_step"],
            current_epoch=metrics["current_epoch"],
            training_loss=metrics["training_loss"],
            validation_loss=metrics["validation_loss"],
            runtime=metrics["runtime"],
            learning_rate=metrics["learning_rate"],
        )
        history_point = insert_metric_history_from_latest(
            conn,
            run_id=run_id,
            current_step=metrics["current_step"],
            current_epoch=metrics["current_epoch"],
            training_loss=metrics["training_loss"],
            validation_loss=metrics["validation_loss"],
            runtime=metrics["runtime"],
            learning_rate=metrics["learning_rate"],
            source="wandb_summary",
        )

        current_status = run_row["status"]
        new_status = snapshot["tap_status"]

        if current_status != "cancelled":
            conn.execute(
                "UPDATE runs SET status = ? WHERE run_id = ?",
                (new_status, run_id),
            )

    return {
        "run_id": run_id,
        "wandb_run_id": wandb_run_id,
        "wandb_state": snapshot["wandb_state"],
        "wandb_url": snapshot["url"],
        "metrics": updated_metrics,
        "history_point": history_point,
    }
