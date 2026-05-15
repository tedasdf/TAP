import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from datetime import datetime, timezone
from uuid import uuid4
from app.config import settings


DB_PATH = Path(settings.TAP_DB_PATH)

def _ensure_db_parent() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    _ensure_db_parent()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    _ensure_db_parent()

    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                git_commit TEXT NOT NULL,
                config_path TEXT NOT NULL,
                config_overrides TEXT,
                wandb_config_ref TEXT,
                slurm_job_id TEXT,
                wandb_run_id TEXT,
                created_at TEXT NOT NULL,
                last_checked_at TEXT,
                error_message TEXT,
                config_snapshot_json TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                queue_state TEXT,
                execution_state TEXT,
                node_info TEXT,
                start_time TEXT,
                end_time TEXT,
                exit_status TEXT,
                log_path TEXT,
                error_log_path TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                created_at TEXT NOT NULL,
                payload_json TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                run_id TEXT PRIMARY KEY,
                current_step INTEGER,
                current_epoch INTEGER,
                training_loss REAL,
                validation_loss REAL,
                runtime REAL,
                learning_rate REAL,
                latest_metric_timestamp TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_points (
                point_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                epoch INTEGER,
                training_loss REAL,
                validation_loss REAL,
                runtime REAL,
                learning_rate REAL,
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL,
                UNIQUE(run_id, step, source),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metric_points_run_step
            ON metric_points(run_id, step)
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'info',
                title TEXT NOT NULL DEFAULT 'Notification',
                message TEXT NOT NULL,
                run_id TEXT,
                job_id TEXT,
                timestamp TEXT NOT NULL,
                read_state INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )
            """
        )

        existing_notification_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(notifications)").fetchall()
        }

        if "severity" not in existing_notification_columns:
            conn.execute(
                "ALTER TABLE notifications ADD COLUMN severity TEXT NOT NULL DEFAULT 'info'"
            )

        if "title" not in existing_notification_columns:
            conn.execute(
                "ALTER TABLE notifications ADD COLUMN title TEXT NOT NULL DEFAULT 'Notification'"
            )

        existing_run_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(runs)").fetchall()
        }

        if "config_snapshot_json" not in existing_run_columns:
            conn.execute(
                "ALTER TABLE runs ADD COLUMN config_snapshot_json TEXT"
            )
        

def create_notification(
    *,
    event_type: str,
    severity: str,
    title: str,
    message: str,
    run_id: str | None = None,
    job_id: str | None = None,
) -> sqlite3.Row:
    notification_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
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
                notification_id,
                event_type,
                severity,
                title,
                message,
                run_id,
                job_id,
                timestamp,
            ),
        )

        notification = conn.execute(
            """
            SELECT *
            FROM notifications
            WHERE notification_id = ?
            """,
            (notification_id,),
        ).fetchone()

        if notification is None:
            raise RuntimeError("Failed to create notification")

        return notification
