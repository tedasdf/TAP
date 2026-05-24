from __future__ import annotations

import json
import logging

from app.config import settings

log = logging.getLogger(__name__)


def send_push(subscription: dict, title: str, body: str) -> bool:
    """Send a Web Push to one subscription.
    subscription = {"endpoint": ..., "keys": {"p256dh": ..., "auth": ...}}
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return False
    try:
        from pywebpush import webpush, WebPushException
        webpush(
            subscription_info=subscription,
            data=json.dumps({"title": title, "body": body}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
        )
        return True
    except Exception as exc:
        log.warning("Push failed: %s", exc)
        return False


def broadcast_push(subscriptions: list[dict], title: str, body: str) -> int:
    """Send to all subscriptions. Returns count of successes."""
    return sum(send_push(sub, title, body) for sub in subscriptions)
