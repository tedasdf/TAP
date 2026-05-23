from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunEvent:
    event_id: str
    run_id: str
    event_type: str
    message: str
    created_at: str
    old_status: str | None = None
    new_status: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: Any) -> RunEvent:
        d = dict(row)
        raw = d.get("payload_json")
        payload: dict[str, Any] = {}
        if raw:
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                payload = {}
        return cls(
            event_id=d["event_id"],
            run_id=d["run_id"],
            event_type=d["event_type"],
            message=d["message"],
            created_at=d["created_at"],
            old_status=d.get("old_status"),
            new_status=d.get("new_status"),
            payload=payload,
        )
