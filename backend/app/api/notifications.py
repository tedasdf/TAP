from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db import get_db
from app.models.notification import Notification
from app.repositories.job_repo import JobRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.run_repo import RunRepository
from app.schemas import NotificationCreate, NotificationResponse
from app.services.notifications import send_discord_message


router = APIRouter(tags=["notifications"])


@router.get("/notifications")
def list_notifications(
    unread_only: bool = Query(default=False),
) -> list[NotificationResponse]:
    with get_db() as conn:
        notifications = NotificationRepository(conn).list_all(unread_only=unread_only)
    return [NotificationResponse.from_domain(n) for n in notifications]


@router.post("/notifications")
def create_notification(payload: NotificationCreate) -> dict:
    with get_db() as conn:
        if payload.run_id and RunRepository(conn).find(payload.run_id) is None:
            raise HTTPException(status_code=404, detail=f"Run '{payload.run_id}' not found")
        if payload.job_id and JobRepository(conn).find(payload.job_id) is None:
            raise HTTPException(status_code=404, detail=f"Job '{payload.job_id}' not found")

        repo = NotificationRepository(conn)
        notification = Notification(
            notification_id=NotificationRepository._new_id(),
            event_type=payload.event_type,
            severity="info",
            title="Notification",
            message=payload.message,
            timestamp=NotificationRepository._utc_now(),
            run_id=payload.run_id,
            job_id=payload.job_id,
        )
        saved = repo.create(notification)

    discord_ok = send_discord_message(payload.message)
    result = NotificationResponse.from_domain(saved).model_dump()
    result["discord_sent"] = discord_ok
    return result


@router.post("/notifications/test")
def create_test_notification() -> dict:
    return create_notification(NotificationCreate(event_type="test", message="TAP test notification"))


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str) -> NotificationResponse:
    with get_db() as conn:
        repo = NotificationRepository(conn)
        if repo.find(notification_id) is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        repo.mark_read(notification_id)
        notification = repo.find(notification_id)
    return NotificationResponse.from_domain(notification)  # type: ignore[arg-type]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read_post(notification_id: str) -> NotificationResponse:
    return mark_notification_read(notification_id)


@router.post("/notifications/read-all")
def mark_all_notifications_read() -> dict[str, int]:
    with get_db() as conn:
        updated = NotificationRepository(conn).mark_all_read()
    return {"updated": updated}
