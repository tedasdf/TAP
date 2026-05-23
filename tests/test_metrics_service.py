from __future__ import annotations

from app.services.metrics import normalize_wandb_history_row


def test_normalize_wandb_history_row_maps_common_keys() -> None:
    point = normalize_wandb_history_row(
        "run_123",
        {
            "_step": 12,
            "epoch": 1,
            "train/loss": 2.5,
            "val/loss": 2.8,
            "optimizer/lr": 0.0001,
            "_runtime": 120.5,
            "tokens_seen": 4096,
            "samples_seen": 32,
            "tokens/sec": 900.0,
            "gpu/memory_used": 10.5,
            "gpu/utilization": 77.0,
        },
    )

    assert point is not None
    assert point["run_id"] == "run_123"
    assert point["step"] == 12
    assert point["epoch"] == 1
    assert point["train_loss"] == 2.5
    assert point["val_loss"] == 2.8
    assert point["learning_rate"] == 0.0001
    assert point["runtime_seconds"] == 120.5
    assert point["tokens_seen"] == 4096
    assert point["samples_seen"] == 32
    assert point["tokens_per_second"] == 900.0
    assert point["gpu_memory_used"] == 10.5
    assert point["gpu_utilization"] == 77.0
    assert point["source"] == "wandb_history"


def test_normalize_wandb_history_row_ignores_rows_without_step() -> None:
    assert normalize_wandb_history_row("run_123", {"train/loss": 2.5}) is None


def test_normalize_wandb_history_row_ignores_rows_without_metric_values() -> None:
    assert normalize_wandb_history_row("run_123", {"_step": 1}) is None
