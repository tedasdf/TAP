from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.schemas import MetricSnapshotUpsert


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