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
        "vocab_size": 50257,
        "seq_len": 256,
    },
    "training": {
        "optimizer": "adamw",
        "scheduler": "cosine",
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
    },
    "tracking": {
        "wandb_enabled": True,
    },
    "tokenizer": {
        "type": "bpe",
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
