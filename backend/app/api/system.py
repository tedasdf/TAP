from typing import Any

from fastapi import APIRouter

from app.config import settings
from app.db import get_db
from app.services.launcher import run_ssh_command
from app.services.wandb_client import get_run_snapshot
router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]: # placeholder function for now 
    return {
        "status": "ok",
        "service": "tap-api",
    }


def check_database() -> str:
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
            conn.execute("SELECT COUNT(*) FROM runs").fetchone()
        return "ok"
    except Exception:
        return "error"


def check_ssh() -> str:
    try:
        code, stdout, stderr = run_ssh_command("echo ok")
        if code == 0 and stdout.strip() == "ok":
            return "ok"
        return "error"
    except Exception:
        return "error"


def check_wandb() -> str:
    try:
        if not settings.WANDB_HEALTHCHECK_RUN_ID:
            return "unknown"

        snapshot = get_run_snapshot(settings.WANDB_HEALTHCHECK_RUN_ID)
        if snapshot:
            return "ok"
        return "error"
    except Exception:
        return "error"


def derive_overall_status(database: str, ssh: str, wandb: str) -> str:
    if database == "error":
        return "error"

    if "error" in {database, ssh, wandb}:
        return "degraded"

    return "ok"


@router.get("/system/status")
def system_status() -> dict[str, Any]:
    database_status = check_database()
    ssh_status = check_ssh()
    wandb_status = check_wandb()

    with get_db() as conn:
        run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        active_run_count = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE status IN ('created', 'queued', 'running')"
        ).fetchone()[0]
        notification_count = conn.execute(
            "SELECT COUNT(*) FROM notifications"
        ).fetchone()[0]

    overall_status = derive_overall_status(
        database=database_status,
        ssh=ssh_status,
        wandb=wandb_status,
    )

    return {
        "service": "tap-api",
        "status": overall_status,
        "checks": {
            "database": database_status,
            "ssh": ssh_status,
            "wandb": wandb_status,
        },
        "run_count": run_count,
        "active_run_count": active_run_count,
        "notification_count": notification_count,
    }