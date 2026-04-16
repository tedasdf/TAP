from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.schemas import NotificationCreate


router = APIRouter(tags=["notifications"])


def ensure_notification_exists(notification_id: str) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    return dict(row)


def ensure_run_exists(run_id: str) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT run_id FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


def ensure_job_exists(job_id: str) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT job_id FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")


@router.get("/notifications")
def list_notifications() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM notifications
            ORDER BY datetime(timestamp) DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


@router.post("/notifications")
def create_notification(payload: NotificationCreate) -> dict[str, Any]:
    from datetime import datetime, timezone
    import uuid

    if payload.run_id:
        ensure_run_exists(payload.run_id)

    if payload.job_id:
        ensure_job_exists(payload.job_id)

    notification_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO notifications (
                notification_id,
                event_type,
                message,
                run_id,
                job_id,
                timestamp,
                read_state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                payload.event_type,
                payload.message,
                payload.run_id,
                payload.job_id,
                timestamp,
                0,
            ),
        )

        row = conn.execute(
            "SELECT * FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()

    return dict(row)


@router.post("/notifications/test")
def create_test_notification() -> dict[str, Any]:
    payload = NotificationCreate(
        event_type="test",
        message="TAP test notification",
    )
    return create_notification(payload)


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str) -> dict[str, Any]:
    ensure_notification_exists(notification_id)

    with get_db() as conn:
        conn.execute(
            "UPDATE notifications SET read_state = 1 WHERE notification_id = ?",
            (notification_id,),
        )

        row = conn.execute(
            "SELECT * FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()

    return dict(row)