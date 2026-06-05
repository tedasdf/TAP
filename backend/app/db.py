import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import settings


DB_PATH = Path(settings.TAP_DB_PATH)
_SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


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
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    with get_db() as conn:
        conn.executescript(schema_sql)
        conn.execute("PRAGMA foreign_keys = ON")
        _run_migrations(conn)


def _run_migrations(conn: sqlite3.Connection) -> None:
    existing_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }

    existing_notif_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(notifications)").fetchall()
    }
    if "severity" not in existing_notif_cols:
        conn.execute(
            "ALTER TABLE notifications ADD COLUMN severity TEXT NOT NULL DEFAULT 'info'"
        )
    if "title" not in existing_notif_cols:
        conn.execute(
            "ALTER TABLE notifications ADD COLUMN title TEXT NOT NULL DEFAULT 'Notification'"
        )

    existing_run_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(runs)").fetchall()
    }
    if "config_snapshot_json" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN config_snapshot_json TEXT")
    if "template_id" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN template_id TEXT")
    if "launch_mode" not in existing_run_cols:
        conn.execute(
            "ALTER TABLE runs ADD COLUMN launch_mode TEXT NOT NULL DEFAULT 'slurm'"
        )
    if "direct_pid" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN direct_pid INTEGER")
    if "direct_log_path" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN direct_log_path TEXT")
    if "latest_checkpoint_path" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN latest_checkpoint_path TEXT")
    if "best_checkpoint_path" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN best_checkpoint_path TEXT")
    if "seed" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN seed INTEGER")
    if "data_ref" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN data_ref TEXT")

    # migration-001: run_events table and last_checked_at on runs
    if "run_events" not in existing_tables:
        conn.execute(
            """
            CREATE TABLE run_events (
                event_id     TEXT PRIMARY KEY,
                run_id       TEXT NOT NULL,
                event_type   TEXT NOT NULL,
                message      TEXT NOT NULL,
                old_status   TEXT,
                new_status   TEXT,
                created_at   TEXT NOT NULL,
                payload_json TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )
    if "last_checked_at" not in existing_run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN last_checked_at TEXT")

    if "metric_points" in existing_tables:
        existing_mp_cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(metric_points)").fetchall()
        }
        if "metrics_json" not in existing_mp_cols:
            conn.execute(
                "ALTER TABLE metric_points ADD COLUMN metrics_json TEXT NOT NULL DEFAULT '{}'"
            )

    if "push_subscriptions" not in existing_tables:
        conn.execute(
            """
            CREATE TABLE push_subscriptions (
                subscription_id TEXT PRIMARY KEY,
                endpoint        TEXT NOT NULL UNIQUE,
                p256dh          TEXT NOT NULL,
                auth            TEXT NOT NULL,
                created_at      TEXT NOT NULL
            )
            """
        )
