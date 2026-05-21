
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class SLMConfigGenerateRequest(BaseModel):
    experiment_name: str = Field(default="slm-smoke")
    model_name: str = Field(default="small-transformer")

    vocab_size: int = Field(default=50257, ge=1)
    seq_len: int = Field(default=256, ge=8)
    d_model: int = Field(default=256, ge=16)
    n_layers: int = Field(default=4, ge=1)
    n_heads: int = Field(default=4, ge=1)

    batch_size: int = Field(default=4, ge=1)
    max_steps: int = Field(default=100, ge=1)
    learning_rate: float = Field(default=3e-4, gt=0)

    dataset_source: Literal["fineweb_edu", "local_jsonl", "synthetic"] = "fineweb_edu"
    attention_type: str = Field(default="baseline")
    normalization: str = Field(default="rmsnorm")
    mlp_type: str = Field(default="gelu")
    optimizer: str = Field(default="adamw")
    scheduler: str = Field(default="cosine")
    tokenizer: str = Field(default="bpe")

class SLMConfigSaveRequest(SLMConfigGenerateRequest):
    filename: str | None = None


class SLMConfigSaveResponse(BaseModel):
    config: dict
    yaml: str
    saved_path: str
    config_path: str

def slugify_filename(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug)
    slug = slug.strip("-._")

    if not slug:
        slug = "slm-config"

    if not slug.endswith((".yaml", ".yml")):
        slug = f"{slug}.yaml"

    return slug


def get_generated_config_dir() -> Path:
    base = os.environ.get("TAP_GENERATED_CONFIG_DIR", "generated_configs/slm")
    path = Path(base).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_slm_config(payload: SLMConfigGenerateRequest) -> dict:
    return {
        "experiment": {
            "name": payload.experiment_name,
            "family": "slm",
            "task": "causal_language_modeling",
            "tags": ["generated", "tap"],
        },
        "model": {
            "name": payload.model_name,
            "type": "decoder_transformer",
            "attention_type": payload.attention_type,
            "normalization": payload.normalization,
            "mlp_type": payload.mlp_type,
            "vocab_size": payload.vocab_size,
            "seq_len": payload.seq_len,
            "d_model": payload.d_model,
            "n_layers": payload.n_layers,
            "n_heads": payload.n_heads,
        },
        "training": {
            "batch_size": payload.batch_size,
            "max_steps": payload.max_steps,
            "learning_rate": payload.learning_rate,
            "optimizer": payload.optimizer,
            "scheduler": payload.scheduler,
        },
        "data": {
            "mode": "text",
            "backend": "torch",
            "source_type": "huggingface",
            "dataset_name": "HuggingFaceFW/fineweb-edu",
            "dataset_config_name": "sample-10BT",
            "train_split_name": "train",
            "streaming": True,
            "text_fields": ["text"],
            "max_train_samples": 1000,
            "val_fraction": 0.01,
            "max_val_samples": 100,
        },
        "tracking": {
            "wandb_enabled": True,
        },
        "tokenizer": {
            "type": payload.tokenizer,
        },
    }


@router.post("/configs/generate/slm")
def generate_slm_config(payload: SLMConfigGenerateRequest) -> dict:
    config = build_slm_config(payload)
    yaml_text = yaml.safe_dump(config, sort_keys=False)

    return {
        "config": config,
        "yaml": yaml_text,
    }

@router.post("/configs/save/slm", response_model=SLMConfigSaveResponse)
def save_slm_config(payload: SLMConfigSaveRequest) -> SLMConfigSaveResponse:
    config = build_slm_config(payload)
    yaml_text = yaml.safe_dump(config, sort_keys=False)

    generated_dir = get_generated_config_dir()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    default_filename = f"{payload.experiment_name}-{timestamp}.yaml"
    filename = slugify_filename(payload.filename or default_filename)

    output_path = (generated_dir / filename).resolve()

    if generated_dir not in output_path.parents and output_path != generated_dir:
        raise ValueError("Invalid generated config path")

    output_path.write_text(yaml_text, encoding="utf-8")

    return SLMConfigSaveResponse(
        config=config,
        yaml=yaml_text,
        saved_path=str(output_path),
        config_path=str(output_path),
    )