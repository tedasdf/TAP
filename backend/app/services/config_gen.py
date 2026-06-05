from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.config import settings


class SLMConfigGenerateRequest(BaseModel):
    """
    Flat parameter bag that maps 1-to-1 with slm_repo's RunConfig sections.
    Field names and defaults match the actual schema in slm_repo.
    """
    experiment_name: str = "slm-generated"

    # ── Model ──────────────────────────────────────────────────────────────
    vocab_size: int = Field(default=32000, ge=1)
    max_seq_len: int = Field(default=512, ge=8)
    model_dim: int = Field(default=512, ge=16)
    num_layers: int = Field(default=8, ge=1)
    num_heads: int = Field(default=8, ge=1)
    num_kv_heads: int | None = None          # None → same as num_heads (MHA)
    rope_base: float = Field(default=10000.0, gt=0)
    attention_type: str = "baseline"
    qk_norm: bool = False
    mlp_type: str = "gelu"
    mlp_mult: float = Field(default=4.0, gt=0)
    norm_type: str = "rmsnorm"               # rmsnorm | layernorm
    block_type: str = "baseline"
    tie_embeddings: bool = False

    # ── Optimizer ──────────────────────────────────────────────────────────
    optimizer_type: str = "adamw"
    learning_rate: float = Field(default=3e-4, gt=0)
    weight_decay: float = Field(default=1e-4, ge=0)
    beta1: float = Field(default=0.9, gt=0, lt=1)
    beta2: float = Field(default=0.95, gt=0, lt=1)
    epsilon: float = Field(default=1e-8, gt=0)

    # ── Scheduler ──────────────────────────────────────────────────────────
    scheduler_type: str = "cosine_with_warmup"
    warmup_steps: int = Field(default=5000, ge=0)
    eta_min: float = Field(default=1e-5, gt=0)

    # ── Trainer ────────────────────────────────────────────────────────────
    max_steps: int = Field(default=10000, ge=1)
    batch_size: int = Field(default=32, ge=1)
    seq_len: int = Field(default=512, ge=8)
    grad_accum_steps: int = Field(default=8, ge=1)
    grad_clip: float = Field(default=1.0, gt=0)
    precision: str = "bf16"                  # bf16 | fp32
    seed: int = Field(default=42)
    eval_every: int = Field(default=1000, ge=1)
    train_log_every: int = Field(default=100, ge=1)
    z_loss_coeff: float = Field(default=0.0, ge=0)

    # ── Data ───────────────────────────────────────────────────────────────
    source_type: str = "huggingface"
    dataset_name: str = "HuggingFaceFW/fineweb-edu"
    dataset_config_name: str = "sample-10BT"
    streaming: bool = True
    max_train_samples: int | None = None

    # ── Tokenizer ──────────────────────────────────────────────────────────
    tokenizer_type: str = "bpe"
    tokenizer_path: str = "artifacts/tokenizer/baseline/tokenizer.json"
    reuse_existing_tokenizer: bool = True

    # ── Logging ────────────────────────────────────────────────────────────
    wandb_project: str = "slm-runs"


class SLMConfigSaveRequest(SLMConfigGenerateRequest):
    filename: str | None = None


def generate_slm_config(p: SLMConfigGenerateRequest) -> dict:
    """Produce a YAML-ready dict matching slm_repo's RunConfig schema exactly."""
    kv_heads = p.num_kv_heads if p.num_kv_heads is not None else p.num_heads
    return {
        "model": {
            "vocab_size": p.vocab_size,
            "max_seq_len": p.max_seq_len,
            "num_layers": p.num_layers,
            "model_dim": p.model_dim,
            "norm_type": p.norm_type,
            "block_type": p.block_type,
            "tie_embeddings": p.tie_embeddings,
            "attention": {
                "attention_type": p.attention_type,
                "num_heads": p.num_heads,
                "num_kv_heads": kv_heads,
                "rope_base": p.rope_base,
                "qk_norm": p.qk_norm,
            },
            "mlp": {
                "mlp_type": p.mlp_type,
                "mlp_mult": p.mlp_mult,
            },
            "init": {
                "use_fan_in_init": True,
                "init_std": 0.02,
            },
        },
        "optimizer": {
            "optimizer_type": p.optimizer_type,
            "lr": p.learning_rate,
            "weight_decay": p.weight_decay,
            "beta1": p.beta1,
            "beta2": p.beta2,
            "eps": p.epsilon,
        },
        "scheduler": {
            "scheduler_type": p.scheduler_type,
            "warmup_steps": p.warmup_steps,
            "t_max": p.max_steps,   # keep t_max in sync with training length
            "eta_min": p.eta_min,
        },
        "logging": {
            "use_print_callback": True,
            "use_wandb": True,
            "wandb_project": p.wandb_project,
            "wandb_run_name": p.experiment_name,
            "wandb_tags": ["generated", "tap"],
        },
        "trainer": {
            "device": "cuda",
            "precision": p.precision,
            "seed": p.seed,
            "train_tokenizer_before_fit": True,
            "text_key": "text",
            "max_seq_len": p.seq_len,
            "max_steps": p.max_steps,
            "grad_accum_steps": p.grad_accum_steps,
            "clip_grad_norm": p.grad_clip,
            "train_log_every": p.train_log_every,
            "eval_every": p.eval_every,
            "max_eval_batches": 50,
            "save_checkpoints": True,
            "checkpoint_every": 1000,
            "checkpoint_dir": "artifacts/checkpoints",
            "save_best_checkpoint": True,
            "metric_name_for_best": "val_loss",
            "metric_mode_for_best": "min",
            "num_sanity_val_steps": 1,
            "z_loss_coeff": p.z_loss_coeff,
        },
        "data": {
            "mode": "text",
            "backend": "torch",
            "source_type": p.source_type,
            "dataset_name": p.dataset_name,
            "dataset_config_name": p.dataset_config_name,
            "streaming": p.streaming,
            "text_fields": ["text"],
            "seq_len": p.seq_len,
            "batch_size": p.batch_size,
            "max_train_samples": p.max_train_samples,
            "max_val_samples": 2000,
            "val_fraction": 0.005,
            "split_seed": 42,
            "seed": p.seed,
            "shuffle": True,
            "shuffle_buffer_size": 10000,
            "num_workers": 2,
            "pin_memory": True,
            "drop_last": True,
        },
        "tokenizer": {
            "tokenizer_type": p.tokenizer_type,
            "vocab_size": p.vocab_size,
            "min_frequency": 2,
            "pad_token": "<pad>",
            "eos_token": "<eos>",
            "unk_token": "<unk>",
            "bos_token": None,
            "reuse_existing": p.reuse_existing_tokenizer,
            "tokenizer_train_samples": 500000,
            "tokenizer_path": p.tokenizer_path,
            "allow_missing_tokenizer": True,
        },
    }


def build_slm_yaml(config: dict) -> str:
    return yaml.safe_dump(config, sort_keys=False, allow_unicode=True)


def save_slm_config(config: dict, filename: str | None) -> tuple[str, str, str]:
    """Save config YAML locally. Returns (local_abs_path, relative_config_path, yaml_text)."""
    yaml_text = build_slm_yaml(config)
    local_dir = Path(settings.TAP_LOCAL_CONFIG_DIR).resolve()
    local_dir.mkdir(parents=True, exist_ok=True)

    # Support both old format (experiment.name) and new format (logging.wandb_run_name)
    experiment_name = (
        config.get("experiment", {}).get("name")
        or config.get("logging", {}).get("wandb_run_name")
        or "slm-generated"
    )
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
