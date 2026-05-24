from __future__ import annotations

import yaml
from fastapi import APIRouter, HTTPException
from app.services.launcher import run_ssh_command
from app.config import settings

router = APIRouter()

_registry_cache: dict | None = None


def _fetch_registry_from_m3() -> dict:
    global _registry_cache

    remote_path = f"{settings.TAP_M3_REPO_PATH}/registry.yaml"
    code, stdout, stderr = run_ssh_command(f"cat {remote_path}")

    if code != 0:
        if _registry_cache is not None:
            return _registry_cache
        raise HTTPException(
            status_code=503,
            detail=f"Could not read registry from M3: {stderr}",
        )

    parsed = yaml.safe_load(stdout)
    _registry_cache = parsed
    return parsed


@router.get("/registry/slm")
def get_slm_registry() -> dict:
    return _fetch_registry_from_m3()


@router.post("/registry/slm/refresh")
def refresh_slm_registry() -> dict:
    global _registry_cache
    _registry_cache = None
    return _fetch_registry_from_m3()
