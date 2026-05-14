from typing import Any

from fastapi import APIRouter

from app.config import settings
from app.db import get_db
from app.services.launcher import run_ssh_command
from app.services.wandb_client import get_run_snapshot

from datetime import datetime, timezone
from typing import Any
import os
from app.services.background_worker import get_background_worker_status

router = APIRouter(tags=["system"])


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_database() -> str:
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        return "ok"
    except Exception:
        return "error"


def check_m3_ssh() -> str:
    try:
        code, stdout, stderr = run_ssh_command("echo tap-health-ok")

        if code == 0 and "tap-health-ok" in stdout:
            return "connected"

        return "error"
    except Exception:
        return "error"


def check_slurm() -> str:
    try:
        code, stdout, stderr = run_ssh_command(
            "command -v squeue >/dev/null 2>&1 && squeue --version >/dev/null 2>&1"
        )

        if code == 0:
            return "connected"

        return "error"
    except Exception:
        return "error"


def check_wandb() -> str:
    # Keep this lightweight for now.
    # This checks whether W&B is configured, not whether the network API is reachable.
    if os.environ.get("WANDB_API_KEY"):
        return "connected"

    return "unknown"


def get_run_counts() -> dict[str, int]:
    with get_db() as conn:
        run_count = conn.execute(
            "SELECT COUNT(*) AS count FROM runs"
        ).fetchone()["count"]

        active_run_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM runs
            WHERE status IN ('created', 'queued', 'running')
            """
        ).fetchone()["count"]

        notification_count = conn.execute(
            "SELECT COUNT(*) AS count FROM notifications"
        ).fetchone()["count"]

    return {
        "run_count": run_count,
        "active_run_count": active_run_count,
        "notification_count": notification_count,
    }

@router.get("/health")
def get_health() -> dict[str, Any]:
    health: dict[str, Any] = {
        "backend": "ok",
        "database": "unknown",
        "timestamp": utc_now_iso(),
    }

    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()

        health["database"] = "ok"

    except Exception as exc:
        health["database"] = "error"
        health["database_error"] = str(exc)

    return health

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
    slurm_status = check_slurm() if ssh_status in ("connected", "ok") else "unknown"
    wandb_status = check_wandb()

    counts = {
        "run_count": 0,
        "active_run_count": 0,
        "notification_count": 0,
    }

    try:
        counts = get_run_counts()
    except Exception:
        database_status = "error"

    overall_status = derive_overall_status(
        database=database_status,
        ssh=ssh_status,
        wandb=wandb_status,
    )

    return {
        "service": "tap-api",
        "status": overall_status,
        "backend": "ok",
        "database": database_status,
        "m3": ssh_status,
        "slurm": slurm_status,
        "wandb": wandb_status,
        "timestamp": utc_now_iso(),
        "checks": {
            "database": database_status,
            "ssh": ssh_status,
            "slurm": slurm_status,
            "wandb": wandb_status,
        },
        "background_worker": get_background_worker_status(),
        **counts,
    }