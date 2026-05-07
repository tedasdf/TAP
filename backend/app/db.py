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
                error_message TEXT
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
            CREATE TABLE IF NOT EXISTS metric_history (
                metric_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step INTEGER,
                epoch INTEGER,
                train_loss REAL,
                val_loss REAL,
                learning_rate REAL,
                runtime_seconds REAL,
                tokens_seen INTEGER,
                samples_seen INTEGER,
                tokens_per_second REAL,
                gpu_memory_used REAL,
                gpu_utilization REAL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_metric_history_unique_run_step_source
            ON metric_history(run_id, step, source)
            WHERE step IS NOT NULL
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metric_history_run_id
            ON metric_history(run_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metric_history_run_step
            ON metric_history(run_id, step)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metric_history_run_created_at
            ON metric_history(run_id, created_at)
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
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