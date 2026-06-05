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

    # Model architecture — names match slm_repo keys exactly
    vocab_size: int = Field(default=32000, ge=1)
    max_seq_len: int = Field(default=512, ge=8)
    model_dim: int = Field(default=512, ge=16)
    num_layers: int = Field(default=8, ge=1)
    num_heads: int = Field(default=8, ge=1)
    num_kv_heads: int | None = None       # None → MHA (same as num_heads)
    rope_base: int = Field(default=10000, ge=1)
    logit_softcap: float | None = None
    use_fan_in_init: bool = True

    # Attention knobs
    attention_type: str = Field(default="baseline")
    qk_norm: bool = False
    window_size: int | None = None        # required when attention_type=swa

    # Norm / MLP
    normalization: str = Field(default="rmsnorm")
    mlp_type: str = Field(default="relu2")

    # Training
    batch_size: int = Field(default=32, ge=1)
    grad_accum_steps: int = Field(default=8, ge=1)
    max_steps: int = Field(default=10000, ge=1)
    learning_rate: float = Field(default=3e-4, gt=0)
    min_lr: float = Field(default=1e-5, gt=0)
    warmup_steps: int = Field(default=5000, ge=0)
    optimizer: str = Field(default="adamw")
    scheduler: str = Field(default="cosine")
    beta1: float = Field(default=0.9, gt=0, lt=1)
    beta2: float = Field(default=0.95, gt=0, lt=1)
    epsilon: float = Field(default=1e-8, gt=0)
    weight_decay: float = Field(default=1e-4, ge=0)
    grad_clip: float = Field(default=1.0, gt=0)
    precision: Literal["bf16", "fp32"] = "bf16"
    seed: int | None = None
    z_loss_coeff: float = Field(default=0.0, ge=0)

    # Trainer
    compile_model: bool = False
    resume_from_checkpoint: str | None = None

    # Data
    dataset_source: Literal["fineweb_edu", "local_jsonl", "synthetic"] = "fineweb_edu"
    hf_revision: str | None = None

    # Tokenizer
    tokenizer: str = Field(default="bpe")
    tokenizer_path: str | None = None


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
            "model_dim": payload.model_dim,
            "num_layers": payload.num_layers,
            "num_heads": payload.num_heads,
            "num_kv_heads": payload.num_kv_heads
                if payload.num_kv_heads is not None
                else payload.num_heads,
            "vocab_size": payload.vocab_size,
            "max_seq_len": payload.max_seq_len,
            "attention_type": payload.attention_type,
            "normalization": payload.normalization,
            "mlp_type": payload.mlp_type,
            "rope_base": payload.rope_base,
            "logit_softcap": payload.logit_softcap,
            "init": {
                "use_fan_in_init": payload.use_fan_in_init,
            },
        },
        "attention": {
            "qk_norm": payload.qk_norm,
            "window_size": payload.window_size,
        },
        "training": {
            "batch_size": payload.batch_size,
            "grad_accum_steps": payload.grad_accum_steps,
            "max_steps": payload.max_steps,
            "learning_rate": payload.learning_rate,
            "min_lr": payload.min_lr,
            "warmup_steps": payload.warmup_steps,
            "optimizer": payload.optimizer,
            "scheduler": payload.scheduler,
            "beta1": payload.beta1,
            "beta2": payload.beta2,
            "epsilon": payload.epsilon,
            "weight_decay": payload.weight_decay,
            "grad_clip": payload.grad_clip,
            "precision": payload.precision,
            "seed": payload.seed,
            "z_loss_coeff": payload.z_loss_coeff,
        },
        "trainer": {
            "compile_model": payload.compile_model,
            "resume_from_checkpoint": payload.resume_from_checkpoint,
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
            "hf_revision": payload.hf_revision,
        },
        "tracking": {
            "wandb_enabled": True,
        },
        "tokenizer": {
            "type": payload.tokenizer,
            "path": payload.tokenizer_path,
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
