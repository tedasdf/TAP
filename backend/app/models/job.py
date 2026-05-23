from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Job:
    job_id: str
    run_id: str
    queue_state: str | None = None
    execution_state: str | None = None
    node_info: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    exit_status: str | None = None
    log_path: str | None = None
    error_log_path: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> Job:
        d = dict(row)
        return cls(
            job_id=d["job_id"],
            run_id=d["run_id"],
            queue_state=d.get("queue_state"),
            execution_state=d.get("execution_state"),
            node_info=d.get("node_info"),
            start_time=d.get("start_time"),
            end_time=d.get("end_time"),
            exit_status=d.get("exit_status"),
            log_path=d.get("log_path"),
            error_log_path=d.get("error_log_path"),
        )
