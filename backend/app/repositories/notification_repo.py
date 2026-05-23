from __future__ import annotations

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository):

    def find(self, notification_id: str) -> Notification | None:
        row = self._conn.execute(
            "SELECT * FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()
        return Notification.from_row(row) if row else None

    def list_all(self, unread_only: bool = False) -> list[Notification]:
        if unread_only:
            rows = self._conn.execute(
                "SELECT * FROM notifications WHERE read_state = 0 ORDER BY datetime(timestamp) DESC"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM notifications ORDER BY datetime(timestamp) DESC"
            ).fetchall()
        return [Notification.from_row(r) for r in rows]

    def create(self, notification: Notification) -> Notification:
        self._conn.execute(
            """
            INSERT INTO notifications (
                notification_id, event_type, severity, title, message,
                run_id, job_id, timestamp, read_state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification.notification_id,
                notification.event_type,
                notification.severity,
                notification.title,
                notification.message,
                notification.run_id,
                notification.job_id,
                notification.timestamp,
                int(notification.read_state),
            ),
        )
        return self.find(notification.notification_id)  # type: ignore[return-value]

    def mark_read(self, notification_id: str) -> None:
        self._conn.execute(
            "UPDATE notifications SET read_state = 1 WHERE notification_id = ?",
            (notification_id,),
        )

    def mark_all_read(self) -> int:
        result = self._conn.execute(
            "UPDATE notifications SET read_state = 1 WHERE read_state = 0"
        )
        return result.rowcount or 0

    def exists(self, run_id: str, event_type: str, message: str | None = None) -> bool:
        if message is not None:
            row = self._conn.execute(
                """
                SELECT notification_id FROM notifications
                WHERE run_id = ? AND event_type = ? AND message = ?
                LIMIT 1
                """,
                (run_id, event_type, message),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT notification_id FROM notifications
                WHERE run_id = ? AND event_type = ?
                LIMIT 1
                """,
                (run_id, event_type),
            ).fetchone()
        return row is not None

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM notifications"
        ).fetchone()
        return int(row["c"]) if row else 0
