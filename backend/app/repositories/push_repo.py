from __future__ import annotations

from app.repositories.base import BaseRepository


class PushRepository(BaseRepository):

    def save(self, endpoint: str, p256dh: str, auth: str) -> None:
        self._conn.execute(
            """
            INSERT INTO push_subscriptions (subscription_id, endpoint, p256dh, auth, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET
                p256dh = excluded.p256dh,
                auth   = excluded.auth
            """,
            (self._new_id(), endpoint, p256dh, auth, self._utc_now()),
        )

    def get_all(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT endpoint, p256dh, auth FROM push_subscriptions"
        ).fetchall()
        return [
            {"endpoint": r["endpoint"], "keys": {"p256dh": r["p256dh"], "auth": r["auth"]}}
            for r in rows
        ]

    def delete(self, endpoint: str) -> None:
        self._conn.execute(
            "DELETE FROM push_subscriptions WHERE endpoint = ?",
            (endpoint,),
        )
