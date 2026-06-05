from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.db import get_db
from app.repositories.push_repo import PushRepository

router = APIRouter(tags=["push"])


class PushSubscribePayload(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class PushUnsubscribePayload(BaseModel):
    endpoint: str


@router.get("/push/vapid-public-key")
def get_vapid_public_key() -> dict:
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/push/subscribe")
def subscribe(payload: PushSubscribePayload) -> dict:
    with get_db() as conn:
        PushRepository(conn).save(payload.endpoint, payload.p256dh, payload.auth)
    return {"ok": True}


@router.post("/push/unsubscribe")
def unsubscribe(payload: PushUnsubscribePayload) -> dict:
    with get_db() as conn:
        PushRepository(conn).delete(payload.endpoint)
    return {"ok": True}


@router.post("/push/test")
def test_push() -> dict:
    from app.services.push_service import send_push
    with get_db() as conn:
        subs = PushRepository(conn).get_all()
    if not subs:
        return {"subscriptions": 0, "sent": 0, "error": "no subscriptions"}
    errors = []
    sent = 0
    for sub in subs:
        try:
            from pywebpush import webpush
            webpush(
                subscription_info=sub,
                data='{"title":"TAP Test","body":"Push working!"}',
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
            )
            sent += 1
        except Exception as exc:
            errors.append(str(exc))
    return {"subscriptions": len(subs), "sent": sent, "errors": errors}
