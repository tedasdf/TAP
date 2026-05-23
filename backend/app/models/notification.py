from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Notification:
    notification_id: str
    event_type: str
    severity: str
    title: str
    message: str
    timestamp: str
    read_state: bool = False
    run_id: str | None = None
    job_id: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> Notification:
        d = dict(row)
        return cls(
            notification_id=d["notification_id"],
            event_type=d["event_type"],
            severity=d.get("severity", "info"),
            title=d.get("title", "Notification"),
            message=d["message"],
            timestamp=d["timestamp"],
            read_state=bool(d.get("read_state", 0)),
            run_id=d.get("run_id"),
            job_id=d.get("job_id"),
        )
