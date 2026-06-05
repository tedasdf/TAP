from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from app.config import settings


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


def generate_slm_config(payload: SLMConfigGenerateRequest) -> dict:
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


def build_slm_yaml(config: dict) -> str:
    return yaml.safe_dump(config, sort_keys=False)


def save_slm_config(config: dict, filename: str | None) -> tuple[str, str, str]:
    """Save config YAML locally. Returns (local_abs_path, relative_config_path, yaml_text).

    relative_config_path is the path relative to the repo root (e.g. configs/generated/foo.yaml)
    and is what gets stored in the run record and passed to the cluster at launch time.
    """
    yaml_text = build_slm_yaml(config)
    local_dir = Path(settings.TAP_LOCAL_CONFIG_DIR).resolve()
    local_dir.mkdir(parents=True, exist_ok=True)

    experiment_name = config.get("experiment", {}).get("name", "slm-config")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    default_filename = f"{experiment_name}-{timestamp}.yaml"
    safe_filename = _slugify_filename(filename or default_filename)

    local_path = (local_dir / safe_filename).resolve()
    if local_dir not in local_path.parents and local_path != local_dir:
        raise ValueError("Invalid config path")

    local_path.write_text(yaml_text, encoding="utf-8")

    relative_path = f"{settings.TAP_M3_CONFIG_DIR}/{safe_filename}"
    return str(local_path), relative_path, yaml_text


def copy_config_to_cluster(
    local_path: str,
    *,
    cluster_host: str,
    remote_repo_path: str,
    relative_config_path: str,
) -> None:
    """SCP a local config file to the cluster repo. Idempotent — safe to call before every launch."""
    remote_path = f"{remote_repo_path}/{relative_config_path}"
    remote_dir = str(Path(remote_path).parent)

    mkdir = subprocess.run(
        ["ssh", cluster_host, f"mkdir -p {remote_dir}"],
        capture_output=True, text=True, check=False,
    )
    if mkdir.returncode != 0:
        raise RuntimeError(f"Could not create remote dir {remote_dir}: {mkdir.stderr}")

    scp = subprocess.run(
        ["scp", local_path, f"{cluster_host}:{remote_path}"],
        capture_output=True, text=True, check=False,
    )
    if scp.returncode != 0:
        raise RuntimeError(f"SCP failed: {scp.stderr}")


def _slugify_filename(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug)
    slug = slug.strip("-._")
    if not slug:
        slug = "slm-config"
    if not slug.endswith((".yaml", ".yml")):
        slug = f"{slug}.yaml"
    return slug
