"""Pure Discord notification sender. No SQL, no DB."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.config import settings


def send_discord_message(message: str) -> bool:
    if not settings.DISCORD_WEBHOOK_URL:
        return False

    data = json.dumps({"content": message, "username": "TAP"}).encode("utf-8")
    req = urllib.request.Request(
        settings.DISCORD_WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (https://github.com/tedasdf/TAP, 0.1.0)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False
