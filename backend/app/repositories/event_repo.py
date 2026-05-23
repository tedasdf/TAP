from __future__ import annotations

import json

from app.models.event import RunEvent
from app.repositories.base import BaseRepository


class RunEventRepository(BaseRepository):

    def create(self, event: RunEvent) -> RunEvent:
        self._conn.execute(
            """
            INSERT INTO run_events (
                event_id, run_id, event_type, message,
                old_status, new_status, created_at, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.run_id,
                event.event_type,
                event.message,
                event.old_status,
                event.new_status,
                event.created_at,
                json.dumps(event.payload, ensure_ascii=False),
            ),
        )
        row = self._conn.execute(
            "SELECT * FROM run_events WHERE event_id = ?",
            (event.event_id,),
        ).fetchone()
        return RunEvent.from_row(row)

    def list_for_run(self, run_id: str) -> list[RunEvent]:
        rows = self._conn.execute(
            """
            SELECT * FROM run_events
            WHERE run_id = ?
            ORDER BY datetime(created_at) ASC
            """,
            (run_id,),
        ).fetchall()
        return [RunEvent.from_row(r) for r in rows]
