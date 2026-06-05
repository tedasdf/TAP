from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.config_gen import (
    SLMConfigGenerateRequest,
    SLMConfigSaveRequest,
    build_slm_yaml,
    generate_slm_config,
    save_slm_config,
)


router = APIRouter()


class SLMConfigSaveResponse(BaseModel):
    config: dict
    yaml: str
    local_path: str
    config_path: str


@router.post("/configs/generate/slm")
def generate_slm_config_route(payload: SLMConfigGenerateRequest) -> dict:
    config = generate_slm_config(payload)
    return {"config": config, "yaml": build_slm_yaml(config)}


@router.post("/configs/save/slm", response_model=SLMConfigSaveResponse)
def save_slm_config_route(payload: SLMConfigSaveRequest) -> SLMConfigSaveResponse:
    config = generate_slm_config(payload)
    local_path, relative_path, yaml_text = save_slm_config(config, payload.filename)
    return SLMConfigSaveResponse(
        config=config,
        yaml=yaml_text,
        local_path=local_path,
        config_path=relative_path,
    )
