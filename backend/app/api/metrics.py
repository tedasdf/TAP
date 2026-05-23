from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db import get_db
from app.models.metric import MetricSnapshot, MetricSyncStatus
from app.repositories.metric_repo import MetricRepository
from app.repositories.run_repo import RunRepository
from app.schemas import MetricSnapshotUpsert, MetricSnapshotResponse, MetricPointResponse, MetricSyncStatusResponse
from app.services.wandb_client import get_run_snapshot


router = APIRouter(tags=["metrics"])


def _require_run(run_id: str) -> None:
    with get_db() as conn:
        if RunRepository(conn).find(run_id) is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


@router.put("/runs/{run_id}/metrics")
def upsert_metrics(run_id: str, payload: MetricSnapshotUpsert) -> MetricSnapshotResponse:
    _require_run(run_id)

    with get_db() as conn:
        repo = MetricRepository(conn)
        snapshot = MetricSnapshot(
            run_id=run_id,
            current_step=payload.current_step,
            current_epoch=payload.current_epoch,
            training_loss=payload.training_loss,
            validation_loss=payload.validation_loss,
            runtime=payload.runtime,
            learning_rate=payload.learning_rate,
            latest_metric_timestamp=payload.latest_metric_timestamp,
        )
        saved = repo.upsert_snapshot(snapshot)
        sync = MetricSyncStatus(
            run_id=run_id,
            source="manual",
            status="success",
            last_finished_at=MetricRepository._utc_now(),
            points_synced=1,
        )
        repo.upsert_sync_status(sync)

    return MetricSnapshotResponse.from_domain(saved)


@router.get("/runs/{run_id}/metrics")
def get_metrics(run_id: str) -> MetricSnapshotResponse:
    _require_run(run_id)

    with get_db() as conn:
        snapshot = MetricRepository(conn).find_snapshot(run_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No metrics found for run '{run_id}'")
    return MetricSnapshotResponse.from_domain(snapshot)


@router.get("/runs/{run_id}/metrics/history")
def get_metric_history(
    run_id: str,
    limit: int = Query(default=500, ge=1, le=10_000),
) -> list[MetricPointResponse]:
    _require_run(run_id)

    with get_db() as conn:
        points = MetricRepository(conn).list_history(run_id, limit=limit)
    return [MetricPointResponse.from_domain(p) for p in points]


@router.post("/runs/{run_id}/sync-wandb")
def sync_metrics_from_wandb(run_id: str) -> dict[str, Any]:
    _require_run(run_id)

    with get_db() as conn:
        run = RunRepository(conn).find(run_id)

    wandb_run_id = run.wandb_run_id if run else None  # type: ignore[union-attr]
    if not wandb_run_id:
        error_msg = "No wandb_run_id stored for this run"
        with get_db() as conn:
            repo = MetricRepository(conn)
            repo.upsert_sync_status(MetricSyncStatus(
                run_id=run_id, source="wandb", status="failed",
                last_finished_at=MetricRepository._utc_now(), error_message=error_msg,
            ))
        raise HTTPException(status_code=400, detail=error_msg)

    with get_db() as conn:
        repo = MetricRepository(conn)
        repo.upsert_sync_status(MetricSyncStatus(
            run_id=run_id, source="wandb", status="syncing",
            last_started_at=MetricRepository._utc_now(),
        ))

    try:
        wandb_snapshot = get_run_snapshot(wandb_run_id)
    except Exception as exc:
        error_msg = f"W&B sync failed: {exc}"
        with get_db() as conn:
            MetricRepository(conn).upsert_sync_status(MetricSyncStatus(
                run_id=run_id, source="wandb", status="failed",
                last_finished_at=MetricRepository._utc_now(), error_message=error_msg,
            ))
        raise HTTPException(status_code=500, detail=error_msg)

    metrics_dict = dict(wandb_snapshot["metrics"])
    metrics_dict["source"] = "wandb"

    with get_db() as conn:
        repo = MetricRepository(conn)
        run_repo = RunRepository(conn)

        snapshot = MetricSnapshot(
            run_id=run_id,
            current_step=metrics_dict.get("current_step"),
            current_epoch=metrics_dict.get("current_epoch"),
            training_loss=metrics_dict.get("training_loss"),
            validation_loss=metrics_dict.get("validation_loss"),
            runtime=metrics_dict.get("runtime"),
            learning_rate=metrics_dict.get("learning_rate"),
        )
        saved_snapshot = repo.upsert_snapshot(snapshot)

        current_run = run_repo.find(run_id)
        new_status = wandb_snapshot["tap_status"]
        if current_run and current_run.status != "cancelled":
            run_repo.update_status(run_id, new_status)

        points_synced = repo.count_points(run_id, "wandb")
        repo.upsert_sync_status(MetricSyncStatus(
            run_id=run_id, source="wandb", status="success",
            last_finished_at=MetricRepository._utc_now(), points_synced=points_synced,
        ))

    return {
        "run_id": run_id,
        "wandb_run_id": wandb_run_id,
        "wandb_state": wandb_snapshot["wandb_state"],
        "wandb_url": wandb_snapshot["url"],
        "metrics": MetricSnapshotResponse.from_domain(saved_snapshot).model_dump(),
    }


@router.get("/runs/{run_id}/metrics/sync-status")
def get_metric_sync_status(run_id: str) -> MetricSyncStatusResponse:
    _require_run(run_id)

    with get_db() as conn:
        status = MetricRepository(conn).find_sync_status(run_id)

    if status is None:
        return MetricSyncStatusResponse(
            run_id=run_id, source=None, status="never_synced",
            last_started_at=None, last_finished_at=None,
            error_message=None, points_synced=0,
        )
    return MetricSyncStatusResponse.from_domain(status)
