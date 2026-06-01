import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

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
                config_snapshot_json TEXT,
                template_id TEXT,
                launch_mode TEXT,
                direct_pid INTEGER,
                direct_log_path TEXT
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
                metrics_json TEXT,
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

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                template_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                params_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS template_runs (
                id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                combo_index INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (template_id) REFERENCES templates(template_id) ON DELETE CASCADE,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                subscription_id TEXT PRIMARY KEY,
                endpoint TEXT NOT NULL UNIQUE,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        _run_migrations(conn)


def _run_migrations(conn: sqlite3.Connection) -> None:
    existing_notif_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(notifications)").fetchall()
    }
    if "severity" not in existing_notif_cols:
        conn.execute("ALTER TABLE notifications ADD COLUMN severity TEXT NOT NULL DEFAULT 'info'")
    if "title" not in existing_notif_cols:
        conn.execute("ALTER TABLE notifications ADD COLUMN title TEXT NOT NULL DEFAULT 'Notification'")

    existing_tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    if "push_subscriptions" not in existing_tables:
        conn.execute(
            """
            CREATE TABLE push_subscriptions (
                subscription_id TEXT PRIMARY KEY,
                endpoint TEXT NOT NULL UNIQUE,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    existing_run_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(runs)").fetchall()
    }
    if "config_snapshot_json" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN config_snapshot_json TEXT")
    if "template_id" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN template_id TEXT")
    if "launch_mode" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN launch_mode TEXT")
    if "direct_pid" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN direct_pid INTEGER")
    if "direct_log_path" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN direct_log_path TEXT")
