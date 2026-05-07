"""Metric storage helpers for latest metric snapshots and metric history."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from sqlite3 import Connection, Row
from typing import Any, Iterable

from app.config import settings
from app.services.wandb_client import get_wandb_run_path


STEP_KEYS = ["_step", "step", "global_step"]
EPOCH_KEYS = ["epoch", "current_epoch"]
TRAIN_LOSS_KEYS = ["train_loss", "train/loss", "loss", "training_loss"]
VAL_LOSS_KEYS = ["val_loss", "val/loss", "validation_loss", "valid/loss"]
LR_KEYS = ["learning_rate", "lr", "optimizer/lr", "train/lr"]
RUNTIME_KEYS = ["_runtime", "runtime", "runtime_seconds", "train/runtime"]
TOKENS_SEEN_KEYS = ["tokens_seen", "train/tokens_seen", "token_count", "tokens"]
SAMPLES_SEEN_KEYS = ["samples_seen", "train/samples_seen", "samples"]
TOKENS_PER_SECOND_KEYS = ["tokens_per_second", "tokens/sec", "train/tokens_per_second"]
GPU_MEMORY_KEYS = ["gpu_memory_used", "gpu/memory_used", "system/gpu.0.memoryAllocated"]
GPU_UTILIZATION_KEYS = ["gpu_utilization", "gpu/utilization", "system/gpu.0.gpu"]

WAND_MARKER_KEYS = list(
    dict.fromkeys(
        STEP_KEYS
        + EPOCH_KEYS
        + TRAIN_LOSS_KEYS
        + VAL_LOSS_KEYS
        + LR_KEYS
        + RUNTIME_KEYS
        + TOKENS_SEEN_KEYS
        + SAMPLES_SEEN_KEYS
        + TOKENS_PER_SECOND_KEYS
        + GPU_MEMORY_KEYS
        + GPU_UTILIZATION_KEYS
    )
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(row: Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _clean_scalar(value: Any) -> Any:
    """Return None for empty/NaN-like values, otherwise return original value."""

    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def first_present(row: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = _clean_scalar(row.get(key))
        if value is not None:
            return value
    return None


def to_int(value: Any) -> int | None:
    value = _clean_scalar(value)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    value = _clean_scalar(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def upsert_latest_metrics(
    conn: Connection,
    *,
    run_id: str,
    current_step: int | None = None,
    current_epoch: int | None = None,
    training_loss: float | None = None,
    validation_loss: float | None = None,
    runtime: float | None = None,
    learning_rate: float | None = None,
    latest_metric_timestamp: str | None = None,
) -> dict[str, Any]:
    """Insert/update the latest metric snapshot for a run."""

    timestamp = latest_metric_timestamp or utc_now_iso()

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
            current_step,
            current_epoch,
            training_loss,
            validation_loss,
            runtime,
            learning_rate,
            timestamp,
        ),
    )

    row = conn.execute(
        "SELECT * FROM metrics WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    result = row_to_dict(row)
    if result is None:
        raise RuntimeError(f"Failed to upsert latest metrics for run '{run_id}'")
    return result


def insert_metric_history(
    conn: Connection,
    *,
    run_id: str,
    step: int | None = None,
    epoch: int | None = None,
    train_loss: float | None = None,
    val_loss: float | None = None,
    learning_rate: float | None = None,
    runtime_seconds: float | None = None,
    tokens_seen: int | None = None,
    samples_seen: int | None = None,
    tokens_per_second: float | None = None,
    gpu_memory_used: float | None = None,
    gpu_utilization: float | None = None,
    source: str = "manual",
    created_at: str | None = None,
    metric_id: str | None = None,
) -> dict[str, Any] | None:
    """Insert one metric-history point.

    Duplicates for the same run_id + step + source are ignored. If step is null,
    SQLite allows multiple nulls in a unique index, which is acceptable for now.
    """

    point_id = metric_id or str(uuid.uuid4())
    timestamp = created_at or utc_now_iso()

    conn.execute(
        """
        INSERT OR IGNORE INTO metric_history (
            metric_id,
            run_id,
            step,
            epoch,
            train_loss,
            val_loss,
            learning_rate,
            runtime_seconds,
            tokens_seen,
            samples_seen,
            tokens_per_second,
            gpu_memory_used,
            gpu_utilization,
            source,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            point_id,
            run_id,
            step,
            epoch,
            train_loss,
            val_loss,
            learning_rate,
            runtime_seconds,
            tokens_seen,
            samples_seen,
            tokens_per_second,
            gpu_memory_used,
            gpu_utilization,
            source,
            timestamp,
        ),
    )

    if step is not None:
        row = conn.execute(
            """
            SELECT *
            FROM metric_history
            WHERE run_id = ? AND step = ? AND source = ?
            ORDER BY datetime(created_at) ASC
            LIMIT 1
            """,
            (run_id, step, source),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM metric_history WHERE metric_id = ?",
            (point_id,),
        ).fetchone()

    return row_to_dict(row)


def insert_metric_history_from_latest(
    conn: Connection,
    *,
    run_id: str,
    current_step: int | None = None,
    current_epoch: int | None = None,
    training_loss: float | None = None,
    validation_loss: float | None = None,
    runtime: float | None = None,
    learning_rate: float | None = None,
    source: str = "manual",
    created_at: str | None = None,
) -> dict[str, Any] | None:
    """Convert latest-metric field names into metric-history field names."""

    return insert_metric_history(
        conn,
        run_id=run_id,
        step=current_step,
        epoch=current_epoch,
        train_loss=training_loss,
        val_loss=validation_loss,
        learning_rate=learning_rate,
        runtime_seconds=runtime,
        source=source,
        created_at=created_at,
    )


def get_latest_metrics(conn: Connection, run_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM metrics WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    return row_to_dict(row)


def get_metric_history(conn: Connection, run_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM metric_history
        WHERE run_id = ?
        ORDER BY
            step IS NULL,
            step ASC,
            datetime(created_at) ASC,
            created_at ASC
        """,
        (run_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def normalize_wandb_history_row(run_id: str, row: dict[str, Any]) -> dict[str, Any] | None:
    """Map one W&B history row into TAP metric_history fields."""

    step = to_int(first_present(row, STEP_KEYS))
    if step is None:
        return None

    point = {
        "run_id": run_id,
        "step": step,
        "epoch": to_int(first_present(row, EPOCH_KEYS)),
        "train_loss": to_float(first_present(row, TRAIN_LOSS_KEYS)),
        "val_loss": to_float(first_present(row, VAL_LOSS_KEYS)),
        "learning_rate": to_float(first_present(row, LR_KEYS)),
        "runtime_seconds": to_float(first_present(row, RUNTIME_KEYS)),
        "tokens_seen": to_int(first_present(row, TOKENS_SEEN_KEYS)),
        "samples_seen": to_int(first_present(row, SAMPLES_SEEN_KEYS)),
        "tokens_per_second": to_float(first_present(row, TOKENS_PER_SECOND_KEYS)),
        "gpu_memory_used": to_float(first_present(row, GPU_MEMORY_KEYS)),
        "gpu_utilization": to_float(first_present(row, GPU_UTILIZATION_KEYS)),
        "source": "wandb_history",
    }

    has_metric_value = any(
        point.get(key) is not None
        for key in (
            "train_loss",
            "val_loss",
            "learning_rate",
            "runtime_seconds",
            "tokens_seen",
            "samples_seen",
            "tokens_per_second",
            "gpu_memory_used",
            "gpu_utilization",
        )
    )
    if not has_metric_value:
        return None

    return point


def sync_wandb_metric_history(
    conn: Connection,
    *,
    run_id: str,
    wandb_run_id: str,
    max_rows: int = 5000,
) -> dict[str, Any]:
    """Sync W&B history rows into metric_history.

    Uses scan_history(keys=None) so rows are not dropped just because different
    metrics are logged at different steps.
    """

    import wandb

    api = wandb.Api()
    wandb_run = api.run(get_wandb_run_path(wandb_run_id))

    scanned_count = 0
    normalized_count = 0
    inserted_count = 0
    duplicate_count = 0
    latest_point: dict[str, Any] | None = None

    for scanned_count, row in enumerate(wandb_run.scan_history(keys=None, page_size=1000), start=1):
        if scanned_count > max_rows:
            break

        normalized = normalize_wandb_history_row(run_id, dict(row))
        if normalized is None:
            continue

        normalized_count += 1
        before_changes = conn.total_changes
        inserted_row = insert_metric_history(conn, **normalized)
        if conn.total_changes > before_changes:
            inserted_count += 1
        else:
            duplicate_count += 1

        if inserted_row is not None:
            latest_point = inserted_row

    if latest_point is not None:
        upsert_latest_metrics(
            conn,
            run_id=run_id,
            current_step=latest_point.get("step"),
            current_epoch=latest_point.get("epoch"),
            training_loss=latest_point.get("train_loss"),
            validation_loss=latest_point.get("val_loss"),
            runtime=latest_point.get("runtime_seconds"),
            learning_rate=latest_point.get("learning_rate"),
            latest_metric_timestamp=latest_point.get("created_at"),
        )

    return {
        "run_id": run_id,
        "wandb_run_id": wandb_run_id,
        "wandb_entity": settings.WANDB_ENTITY,
        "wandb_project": settings.WANDB_PROJECT,
        "source": "wandb_history",
        "scanned_count": scanned_count,
        "normalized_count": normalized_count,
        "inserted_count": inserted_count,
        "duplicate_count": duplicate_count,
        "latest_point": latest_point,
    }
