from fastapi import APIRouter

from app.db import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]: # placeholder function for now 
    return {
        "status": "ok",
        "service": "tap-api",
    }


@router.get("/system/status")
def system_status() -> dict[str, int | str]:
    with get_db() as conn:
        run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        active_run_count = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE status IN ('created', 'queued', 'running')"
        ).fetchone()[0]
        notification_count = conn.execute(
            "SELECT COUNT(*) FROM notifications"
        ).fetchone()[0]

    return {
        "service": "tap-api",
        "status": "ok",
        "run_count": run_count,
        "active_run_count": active_run_count,
        "notification_count": notification_count,
    }