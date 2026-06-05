import copy
from typing import Any

import yaml


_BASE_CONFIG: dict[str, Any] = {
    "experiment": {
        "family": "slm",
        "task": "causal_language_modeling",
        "tags": ["generated", "tap"],
    },
    "model": {
        "type": "decoder_transformer",
        "model_dim": 512,
        "num_layers": 8,
        "num_heads": 8,
        "num_kv_heads": 8,
        "vocab_size": 32000,
        "max_seq_len": 512,
        "attention_type": "baseline",
        "normalization": "rmsnorm",
        "mlp_type": "relu2",
        "rope_base": 10000,
        "logit_softcap": None,
        "init": {
            "use_fan_in_init": True,
        },
    },
    "attention": {
        "qk_norm": False,
        "window_size": None,
    },
    "training": {
        "batch_size": 32,
        "grad_accum_steps": 8,
        "max_steps": 10000,
        "learning_rate": 3e-4,
        "min_lr": 1e-5,
        "warmup_steps": 5000,
        "optimizer": "adamw",
        "scheduler": "cosine",
        "beta1": 0.9,
        "beta2": 0.95,
        "epsilon": 1e-8,
        "weight_decay": 1e-4,
        "grad_clip": 1.0,
        "precision": "bf16",
        "seed": None,
        "z_loss_coeff": 0.0,
    },
    "trainer": {
        "compile_model": False,
        "resume_from_checkpoint": None,
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
        "hf_revision": None,
    },
    "tracking": {
        "wandb_enabled": True,
    },
    "tokenizer": {
        "type": "bpe",
        "path": None,
    },
}


def _set_nested(d: dict, dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value


def generate_slm_config(name: str, resolved_params: dict[str, Any]) -> str:
    """Merge resolved_params into the base SLM config and return a YAML string.

    Keys with dots (e.g. 'model.attention_type') are applied at the nested path.
    Flat keys are applied at the top level.
    """
    config = copy.deepcopy(_BASE_CONFIG)
    config["experiment"]["name"] = name
    for key, value in resolved_params.items():
        _set_nested(config, key, value)
    return yaml.dump(config, default_flow_style=False, sort_keys=False)
