from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


class BaseRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _new_id() -> str:
        return str(uuid4())
