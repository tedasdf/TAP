import json
import urllib.request
import urllib.error

from app.config import settings


def send_discord_message(message: str) -> bool:
    if not settings.DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL is empty")
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
            print("Discord status:", response.status)
            body = response.read().decode("utf-8", errors="replace")
            print("Discord body:", body)
            return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print("Discord HTTPError:", e.code, body)
        return False
    except urllib.error.URLError as e:
        print("Discord URLError:", str(e))
        return False