from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db import get_db
from app.schemas import MetricSnapshotUpsert
from app.services.metrics import (
    mark_metric_sync_failed,
    mark_metric_sync_started,
    mark_metric_sync_success,
    upsert_metric_snapshot,
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

    metrics = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    metrics["source"] = "manual"

    with get_db() as conn:
        row = upsert_metric_snapshot(conn, run_id, metrics)
        mark_metric_sync_success(conn, run_id, "manual", 1)

    if row is None:
        raise HTTPException(status_code=500, detail="Metric upsert failed")

    return row


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


@router.get("/runs/{run_id}/metrics/history")
def get_metric_history(
    run_id: str,
    limit: int = Query(default=500, ge=1, le=10_000),
) -> list[dict[str, Any]]:
    ensure_run_exists(run_id)

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                step,
                epoch,
                training_loss,
                validation_loss,
                runtime,
                learning_rate,
                source,
                created_at
            FROM metric_points
            WHERE run_id = ?
            ORDER BY step ASC, created_at ASC
            LIMIT ?
            """,
            (run_id, limit),
        ).fetchall()

    return [dict(row) for row in rows]


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

    with get_db() as conn:
        mark_metric_sync_started(conn, run_id, "wandb")
    try:
        snapshot = get_run_snapshot(wandb_run_id)
    except Exception as exc:
        error_message = f"W&B sync failed: {str(exc)}"
        with get_db() as conn:
            mark_metric_sync_failed(conn, run_id, "wandb", error_message)
        raise HTTPException(status_code=500, detail=error_message)

    metrics = dict(snapshot["metrics"])
    metrics["source"] = "wandb"

    with get_db() as conn:
        updated_metrics = upsert_metric_snapshot(conn, run_id, metrics)

        current_status = run_row["status"]
        new_status = snapshot["tap_status"]

        if current_status != "cancelled":
            conn.execute(
                "UPDATE runs SET status = ? WHERE run_id = ?",
                (new_status, run_id),
            )

        points_synced_row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM metric_points
            WHERE run_id = ?
            AND source = ?
            """,
            (run_id, "wandb"),
        ).fetchone()

        points_synced = int(points_synced_row["count"] if points_synced_row else 0)
        mark_metric_sync_success(conn, run_id, "wandb", points_synced)

    return {
        "run_id": run_id,
        "wandb_run_id": wandb_run_id,
        "wandb_state": snapshot["wandb_state"],
        "wandb_url": snapshot["url"],
        "metrics": updated_metrics,
    }


@router.get("/runs/{run_id}/metrics/sync-status")
def get_metric_sync_status(run_id: str) -> dict[str, Any]:
    ensure_run_exists(run_id)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM metric_sync_status
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    if row is None:
        return {
            "run_id": run_id,
            "source": None,
            "status": "never_synced",
            "last_started_at": None,
            "last_finished_at": None,
            "error_message": None,
            "points_synced": 0,
        }

    return dict(row)


@router.get("/runs/{run_id}/metrics/sync-status")
def get_metric_sync_status(run_id: str) -> dict[str, Any]:
    ensure_run_exists(run_id)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM metric_sync_status
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    if row is None:
        return {
            "run_id": run_id,
            "source": None,
            "status": "never_synced",
            "last_started_at": None,
            "last_finished_at": None,
            "error_message": None,
            "points_synced": 0,
        }

    return dict(row)