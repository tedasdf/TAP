from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.configs import generate_slm_config

router = APIRouter(tags=["configs"])

_OUTPUT_DIR = Path("generated_configs/slm")

# ── Registry ──────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, Any] = {
    "model": {
        "attention_type": {"options": ["baseline", "gqa", "mha"]},
        "normalization": {"options": ["rmsnorm", "layernorm", "none"]},
        "mlp_type": {"options": ["gelu", "silu", "relu"]},
        "d_model": {"options": [128, 256, 512, 1024]},
        "n_heads": {"options": [2, 4, 8, 16]},
        "n_layers": {"options": [2, 4, 6, 8, 12]},
        "seq_len": {"options": [128, 256, 512, 1024, 2048]},
    },
    "training": {
        "learning_rate": {"options": [0.001, 0.0003, 0.0001, 0.00003]},
        "batch_size": {"options": [4, 8, 16, 32]},
        "max_steps": {"options": [100, 500, 1000, 5000, 10000]},
        "scheduler": {"options": ["cosine", "linear", "constant"]},
        "optimizer": {"options": ["adamw", "adam"]},
    },
    "data": {
        "source_type": {"options": ["huggingface", "local"]},
        "dataset_name": {"options": ["HuggingFaceFW/fineweb-edu", "openwebtext", "wikitext-103"]},
        "dataset_config_name": {"options": ["sample-10BT", "sample-100BT", "default"]},
    },
}


@router.get("/registry/slm")
def get_slm_registry() -> dict[str, Any]:
    return _REGISTRY


# ── Generate / Save ───────────────────────────────────────────────────────────

class SlmConfigRequest(BaseModel):
    name: str
    params: dict[str, Any]


class SlmConfigResponse(BaseModel):
    yaml: str
    path: str | None = None


@router.post("/configs/generate/slm", response_model=SlmConfigResponse)
def generate_slm(payload: SlmConfigRequest) -> SlmConfigResponse:
    yaml_str = generate_slm_config(payload.name, payload.params)
    return SlmConfigResponse(yaml=yaml_str)


@router.post("/configs/save/slm", response_model=SlmConfigResponse)
def save_slm(payload: SlmConfigRequest) -> SlmConfigResponse:
    yaml_str = generate_slm_config(payload.name, payload.params)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = payload.name.strip().replace(" ", "-")
    filename = f"{safe_name}-{timestamp}.yaml"
    file_path = _OUTPUT_DIR / filename
    file_path.write_text(yaml_str)

    return SlmConfigResponse(yaml=yaml_str, path=str(file_path))
