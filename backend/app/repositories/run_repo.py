from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.models.run import Run
from app.repositories.base import BaseRepository
from app.repositories.event_repo import RunEventRepository
from app.repositories.job_repo import JobRepository
from app.repositories.metric_repo import MetricRepository
from app.repositories.notification_repo import NotificationRepository


class RunRepository(BaseRepository):
    """Repository for Runs, with child repositories for everything that belongs to a run.

    Usage:
        with get_db() as conn:
            runs = RunRepository(conn)
            run  = runs.find(run_id)
            job  = runs.jobs.find_by_run(run_id)
            hist = runs.metrics.list_history(run_id)
            evts = runs.events.list_for_run(run_id)
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(conn)
        self.jobs          = JobRepository(conn)
        self.metrics       = MetricRepository(conn)
        self.events        = RunEventRepository(conn)
        self.notifications = NotificationRepository(conn)

    # ── Queries ───────────────────────────────────────────────────────────────

    def find(self, run_id: str) -> Run | None:
        row = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return Run.from_row(row) if row else None

    def list_all(self) -> list[Run]:
        rows = self._conn.execute(
            "SELECT * FROM runs ORDER BY datetime(created_at) DESC"
        ).fetchall()
        return [Run.from_row(r) for r in rows]

    def list_active(self) -> list[Run]:
        rows = self._conn.execute(
            """
            SELECT * FROM runs
            WHERE status IN ('created', 'queued', 'running', 'unknown')
            ORDER BY datetime(created_at) ASC
            """
        ).fetchall()
        return [Run.from_row(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM runs").fetchone()
        return int(row["c"]) if row else 0

    def count_active(self) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS c FROM runs
            WHERE status IN ('created', 'queued', 'running', 'unknown')
            """
        ).fetchone()
        return int(row["c"]) if row else 0

    # ── Mutations ─────────────────────────────────────────────────────────────

    def create(self, run: Run) -> Run:
        self._conn.execute(
            """
            INSERT INTO runs (
                run_id, name, status, git_commit, config_path,
                config_overrides, wandb_config_ref, slurm_job_id,
                wandb_run_id, created_at, last_checked_at, error_message,
                config_snapshot_json, template_id,
                launch_mode, direct_pid, direct_log_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id, run.name, run.status, run.git_commit,
                run.config_path,
                json.dumps(run.config_overrides, ensure_ascii=False),
                run.wandb_config_ref, run.slurm_job_id, run.wandb_run_id,
                run.created_at, run.last_checked_at, run.error_message,
                json.dumps(run.config_snapshot, ensure_ascii=False),
                run.template_id,
                run.launch_mode, run.direct_pid, run.direct_log_path,  # NEW
            ),
        )
        return self.find(run.run_id)  # type: ignore[return-value]
    
    def update_status(
        self,
        run_id: str,
        status: str,
        error_message: str | None = None,
        last_checked_at: str | None = None,
    ) -> None:
        self._conn.execute(
            "UPDATE runs SET status = ?, error_message = ?, last_checked_at = ? WHERE run_id = ?",
            (status, error_message, last_checked_at or self._utc_now(), run_id),
        )

    def update(self, run_id: str, **fields: Any) -> None:
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        self._conn.execute(
            f"UPDATE runs SET {set_clause} WHERE run_id = ?",
            list(fields.values()) + [run_id],
        )

    def delete(self, run_id: str) -> None:
        self._conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
