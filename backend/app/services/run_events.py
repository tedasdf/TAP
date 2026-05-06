import json
import uuid
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def create_run_event(
    conn,
    *,
    run_id: str,
    event_type: str,
    message: str,
    old_status: str | None = None,
    new_status: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO run_events (
            event_id,
            run_id,
            event_type,
            message,
            old_status,
            new_status,
            created_at,
            payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            run_id,
            event_type,
            message,
            old_status,
            new_status,
            utc_now_iso(),
            json_dumps(payload),
        ),
    )