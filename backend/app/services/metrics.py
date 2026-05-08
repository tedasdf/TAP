from __future__ import annotations

from datetime import datetime, timezone
from sqlite3 import Connection, Row
from typing import Any
from uuid import uuid4


STEP_KEYS = ["_step", "step", "global_step"]
TRAIN_LOSS_KEYS = ["train_loss", "train/loss", "loss", "training_loss"]
VAL_LOSS_KEYS = ["val_loss", "val/loss", "validation_loss", "valid/loss"]
LR_KEYS = ["learning_rate", "lr", "optimizer/lr", "train/lr"]
RUNTIME_KEYS = ["_runtime", "runtime", "runtime_seconds", "train/runtime"]
EPOCH_KEYS = ["epoch", "current_epoch"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(row: Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
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
    """Insert/update the latest metric snapshot for one run."""

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
        raise RuntimeError(f"Failed to upsert latest metrics for run {run_id}")

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
) -> dict[str, Any] | None:
    """Insert one real metric-history point.

    Duplicate prevention is handled by the DB unique index on:
    run_id + step + source.
    """

    timestamp = created_at or utc_now_iso()
    metric_id = str(uuid4())

    cursor = conn.execute(
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
            timestamp,
        ),
    )

    if cursor.rowcount == 0:
        row = conn.execute(
            """
            SELECT *
            FROM metric_history
            WHERE run_id = ?
              AND step IS ?
              AND source = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (run_id, step, source),
        ).fetchone()
        return row_to_dict(row)

    row = conn.execute(
        "SELECT * FROM metric_history WHERE metric_id = ?",
        (metric_id,),
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


def get_metric_history(
    conn: Connection,
    run_id: str,
    *,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM metric_history
        WHERE run_id = ?
        ORDER BY
            CASE WHEN step IS NULL THEN 1 ELSE 0 END,
            step ASC,
            created_at ASC
        LIMIT ?
        """,
        (run_id, limit),
    ).fetchall()

    return [dict(row) for row in rows]


def normalize_wandb_history_row(
    *,
    run_id: str,
    row: dict[str, Any],
) -> dict[str, Any] | None:
    step = safe_int(first_present(row, STEP_KEYS))

    if step is None:
        return None

    return {
        "run_id": run_id,
        "step": step,
        "epoch": safe_int(first_present(row, EPOCH_KEYS)),
        "train_loss": safe_float(first_present(row, TRAIN_LOSS_KEYS)),
        "val_loss": safe_float(first_present(row, VAL_LOSS_KEYS)),
        "learning_rate": safe_float(first_present(row, LR_KEYS)),
        "runtime_seconds": safe_float(first_present(row, RUNTIME_KEYS)),
        "source": "wandb_history",
    }


def sync_wandb_metric_history(
    conn: Connection,
    *,
    run_id: str,
    wandb_run_id: str,
    max_rows: int = 5000,
) -> dict[str, Any]:
    """Sync W&B history rows into metric_history.

    This intentionally imports W&B lazily so the service module does not create
    import-time dependency/circular-import issues.
    """

    import wandb

    try:
        from app.services.wandb_client import get_wandb_run_path

        wandb_path = get_wandb_run_path(wandb_run_id)
    except Exception:
        wandb_path = wandb_run_id

    api = wandb.Api()
    wandb_run = api.run(wandb_path)

    scanned_count = 0
    inserted_or_existing_count = 0
    latest_point: dict[str, Any] | None = None

    for row in wandb_run.scan_history(keys=None, page_size=1000):
        if scanned_count >= max_rows:
            break

        scanned_count += 1

        point = normalize_wandb_history_row(run_id=run_id, row=dict(row))
        if point is None:
            continue

        history_row = insert_metric_history(conn, **point)
        if history_row is not None:
            inserted_or_existing_count += 1
            latest_point = history_row

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
        "source": "wandb_history",
        "wandb_run_id": wandb_run_id,
        "scanned_count": scanned_count,
        "history_points_inserted": inserted_or_existing_count,
    }