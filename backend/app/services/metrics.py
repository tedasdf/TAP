# metric upsert/read logic
"""Metric storage helpers for latest metric snapshots and metric history."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlite3 import Connection, Row
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(row: Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


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
