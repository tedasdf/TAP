from __future__ import annotations

from typing import Any

from app.models.job import Job
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository):

    def find(self, job_id: str) -> Job | None:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        return Job.from_row(row) if row else None

    def find_by_run(self, run_id: str) -> Job | None:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE run_id = ? LIMIT 1",
            (run_id,),
        ).fetchone()
        return Job.from_row(row) if row else None

    def list_all(self) -> list[Job]:
        rows = self._conn.execute(
            "SELECT * FROM jobs ORDER BY COALESCE(datetime(start_time), datetime(end_time)) DESC"
        ).fetchall()
        return [Job.from_row(r) for r in rows]

    def create(self, job: Job) -> Job:
        self._conn.execute(
            """
            INSERT INTO jobs (
                job_id, run_id, queue_state, execution_state,
                node_info, start_time, end_time, exit_status,
                log_path, error_log_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id,
                job.run_id,
                job.queue_state,
                job.execution_state,
                job.node_info,
                job.start_time,
                job.end_time,
                job.exit_status,
                job.log_path,
                job.error_log_path,
            ),
        )
        return self.find(job.job_id)  # type: ignore[return-value]

    def create_or_ignore(self, job: Job) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO jobs (
                job_id, run_id, queue_state, execution_state,
                node_info, start_time, end_time, exit_status,
                log_path, error_log_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id,
                job.run_id,
                job.queue_state,
                job.execution_state,
                job.node_info,
                job.start_time,
                job.end_time,
                job.exit_status,
                job.log_path,
                job.error_log_path,
            ),
        )

    def update(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [job_id]
        self._conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE job_id = ?",
            values,
        )
