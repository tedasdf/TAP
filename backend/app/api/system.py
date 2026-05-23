from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from app.config import settings
from app.db import get_db
from app.repositories.notification_repo import NotificationRepository
from app.repositories.run_repo import RunRepository
from app.services.launcher import run_ssh_command
from app.services.orchestrator import orchestrator
from app.services.wandb_client import get_run_snapshot


router = APIRouter(tags=["system"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_database() -> str:
    try:
        with get_db() as conn:
            RunRepository(conn).count()
        return "ok"
    except Exception:
        return "error"


def _check_ssh() -> str:
    try:
        code, stdout, _ = run_ssh_command("echo ok")
        return "ok" if code == 0 and stdout.strip() == "ok" else "error"
    except Exception:
        return "error"


def _check_slurm() -> str:
    try:
        code, _, _ = run_ssh_command(
            "command -v squeue >/dev/null 2>&1 && squeue --version >/dev/null 2>&1"
        )
        return "connected" if code == 0 else "error"
    except Exception:
        return "error"


def _check_wandb() -> str:
    try:
        if not settings.WANDB_HEALTHCHECK_RUN_ID:
            return "unknown"
        return "ok" if get_run_snapshot(settings.WANDB_HEALTHCHECK_RUN_ID) else "error"
    except Exception:
        return "error"


def _derive_overall_status(database: str, ssh: str, wandb: str) -> str:
    if database == "error":
        return "error"
    if "error" in {database, ssh, wandb}:
        return "degraded"
    return "ok"


def _get_counts() -> dict[str, int]:
    with get_db() as conn:
        run_repo = RunRepository(conn)
        notif_repo = NotificationRepository(conn)
        return {
            "run_count": run_repo.count(),
            "active_run_count": run_repo.count_active(),
            "notification_count": notif_repo.count(),
        }


@router.get("/health")
def get_health() -> dict[str, Any]:
    health: dict[str, Any] = {"backend": "ok", "database": "unknown", "timestamp": _utc_now_iso()}
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        health["database"] = "ok"
    except Exception as exc:
        health["database"] = "error"
        health["database_error"] = str(exc)
    return health


@router.get("/system/status")
def system_status() -> dict[str, Any]:
    database_status = _check_database()
    ssh_status = _check_ssh()
    slurm_status = _check_slurm() if ssh_status == "ok" else "unknown"
    wandb_status = _check_wandb()

    counts = {"run_count": 0, "active_run_count": 0, "notification_count": 0}
    try:
        counts = _get_counts()
    except Exception:
        database_status = "error"

    overall = _derive_overall_status(database=database_status, ssh=ssh_status, wandb=wandb_status)

    return {
        "service": "tap-api",
        "status": overall,
        "backend": "ok",
        "database": database_status,
        "m3": ssh_status,
        "slurm": slurm_status,
        "wandb": wandb_status,
        "timestamp": _utc_now_iso(),
        "checks": {
            "database": database_status,
            "ssh": ssh_status,
            "slurm": slurm_status,
            "wandb": wandb_status,
        },
        "background_worker": orchestrator.status.as_dict(),
        **counts,
    }
