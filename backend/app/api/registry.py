from __future__ import annotations

import importlib.util
import os

import yaml
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.launcher import run_ssh_command

router = APIRouter()

_registry_cache: dict | None = None


def _load_local_components() -> dict | None:
    """Load components.py directly from the local slm_repo via importlib.

    Uses spec_from_file_location so the slm package __init__.py (which imports
    torch) is never executed — this is safe to call without a GPU environment.
    """
    repo_path = os.path.expanduser(settings.TAP_M3_REPO_PATH)
    components_file = os.path.join(repo_path, "src/slm/model/components.py")

    if not os.path.isfile(components_file):
        return None

    spec = importlib.util.spec_from_file_location("slm_model_components", components_file)
    if spec is None or spec.loader is None:
        return None

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    components: dict | None = getattr(mod, "COMPONENTS", None)
    return components


def _fetch_registry_from_m3() -> dict:
    remote_path = f"{settings.TAP_M3_REPO_PATH}/registry.yaml"
    code, stdout, stderr = run_ssh_command(f"cat {remote_path}")

    if code != 0:
        raise HTTPException(
            status_code=503,
            detail=f"Could not read registry from M3: {stderr}",
        )

    return yaml.safe_load(stdout)


def _fetch_registry() -> dict:
    global _registry_cache

    components = _load_local_components()
    if components is not None:
        _registry_cache = components
        return components

    if _registry_cache is not None:
        return _registry_cache

    result = _fetch_registry_from_m3()
    _registry_cache = result
    return result


@router.get("/registry/slm")
def get_slm_registry() -> dict:
    return _fetch_registry()


@router.post("/registry/slm/refresh")
def refresh_slm_registry() -> dict:
    global _registry_cache
    _registry_cache = None
    return _fetch_registry()
