import json
import urllib.request
import urllib.error

from app.config import settings


def send_discord_message(message: str) -> bool:
    if not settings.DISCORD_WEBHOOK_URL:
        return False

    payload = {
        "content": message,
        "username": "TAP",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        settings.DISCORD_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300
    except urllib.error.URLError:
        return False