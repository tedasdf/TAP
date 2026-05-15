from __future__ import annotations

from sqlite3 import Connection
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_metric_sync_status_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metric_sync_status (
            run_id TEXT PRIMARY KEY,
            source TEXT,
            status TEXT NOT NULL,
            last_started_at TEXT,
            last_finished_at TEXT,
            error_message TEXT,
            points_synced INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
        )
        """
    )


def mark_metric_sync_started(conn: Connection, run_id: str, source: str) -> None:
    ensure_metric_sync_status_table(conn)
    now = utc_now_iso()

    conn.execute(
        """
        INSERT INTO metric_sync_status (
            run_id,
            source,
            status,
            last_started_at,
            last_finished_at,
            error_message,
            points_synced
        )
        VALUES (?, ?, 'syncing', ?, NULL, NULL, 0)
        ON CONFLICT(run_id) DO UPDATE SET
            source = excluded.source,
            status = 'syncing',
            last_started_at = excluded.last_started_at,
            error_message = NULL
        """,
        (run_id, source, now),
    )


def mark_metric_sync_success(
    conn: Connection,
    run_id: str,
    source: str,
    points_synced: int,
) -> None:
    ensure_metric_sync_status_table(conn)
    now = utc_now_iso()

    conn.execute(
        """
        INSERT INTO metric_sync_status (
            run_id,
            source,
            status,
            last_started_at,
            last_finished_at,
            error_message,
            points_synced
        )
        VALUES (?, ?, 'success', NULL, ?, NULL, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            source = excluded.source,
            status = 'success',
            last_finished_at = excluded.last_finished_at,
            error_message = NULL,
            points_synced = excluded.points_synced
        """,
        (run_id, source, now, points_synced),
    )


def mark_metric_sync_failed(
    conn: Connection,
    run_id: str,
    source: str,
    error_message: str,
) -> None:
    ensure_metric_sync_status_table(conn)
    now = utc_now_iso()

    conn.execute(
        """
        INSERT INTO metric_sync_status (
            run_id,
            source,
            status,
            last_started_at,
            last_finished_at,
            error_message,
            points_synced
        )
        VALUES (?, ?, 'failed', NULL, ?, ?, 0)
        ON CONFLICT(run_id) DO UPDATE SET
            source = excluded.source,
            status = 'failed',
            last_finished_at = excluded.last_finished_at,
            error_message = excluded.error_message
        """,
        (run_id, source, now, error_message),
    )


def upsert_metric_snapshot(conn: Connection, run_id: str, metrics: dict[str, Any]) -> dict[str, Any] | None:
    """Store the latest metric snapshot and append a real history point.

    This keeps the old one-row `metrics` table for summary cards while adding
    `metric_points` for real charts. The frontend should never synthesize fake
    points from this latest snapshot.
    """
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
        VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
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
            metrics.get("current_step"),
            metrics.get("current_epoch"),
            metrics.get("training_loss"),
            metrics.get("validation_loss"),
            metrics.get("runtime"),
            metrics.get("learning_rate"),
            metrics.get("latest_metric_timestamp"),
        ),
    )

    if metrics.get("current_step") is not None:
        conn.execute(
            """
            INSERT INTO metric_points (
                point_id,
                run_id,
                step,
                epoch,
                training_loss,
                validation_loss,
                runtime,
                learning_rate,
                source,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            ON CONFLICT(run_id, step, source) DO UPDATE SET
                epoch = excluded.epoch,
                training_loss = excluded.training_loss,
                validation_loss = excluded.validation_loss,
                runtime = excluded.runtime,
                learning_rate = excluded.learning_rate,
                created_at = excluded.created_at
            """,
            (
                str(uuid4()),
                run_id,
                metrics.get("current_step"),
                metrics.get("current_epoch"),
                metrics.get("training_loss"),
                metrics.get("validation_loss"),
                metrics.get("runtime"),
                metrics.get("learning_rate"),
                metrics.get("source", "wandb"),
                metrics.get("latest_metric_timestamp"),
            ),
        )

    row = conn.execute("SELECT * FROM metrics WHERE run_id = ?", (run_id,)).fetchone()
    return dict(row) if row else None

