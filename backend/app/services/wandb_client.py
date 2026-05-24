from typing import Any, Dict, Optional

import wandb

from app.config import settings


def get_wandb_run_path(wandb_run_id: str) -> str:
    if not settings.WANDB_ENTITY or not settings.WANDB_PROJECT:
        raise ValueError("WANDB_ENTITY and WANDB_PROJECT must be set")
    return f"{settings.WANDB_ENTITY}/{settings.WANDB_PROJECT}/{wandb_run_id}"


def map_wandb_state_to_tap_status(wandb_state: Optional[str]) -> str:
    state = (wandb_state or "").lower()

    if state in {"running"}:
        return "running"
    if state in {"finished"}:
        return "completed"
    if state in {"failed", "crashed"}:
        return "failed"
    if state in {"killed", "cancelled", "canceled"}:
        return "cancelled"

    return "created"


def pick_metric(summary: Dict[str, Any], candidates: list) -> Any:
    for key in candidates:
        if key in summary:
            return summary[key]
    return None


def get_run_history_since(wandb_run_id: str, min_step: int = 0) -> list[Dict[str, Any]]:
    """Return all history rows with step >= min_step as {step, metrics} dicts."""
    api = wandb.Api()
    run = api.run(get_wandb_run_path(wandb_run_id))
    rows: list[Dict[str, Any]] = []
    for row in run.scan_history(min_step=min_step):
        step = row.get("_step")
        if step is None:
            continue
        metrics = {
            k: float(v)
            for k, v in row.items()
            if not k.startswith("_")
            and isinstance(v, (int, float))
            and v == v  # exclude NaN
        }
        if metrics:
            rows.append({"step": int(step), "metrics": metrics})
    return rows


def get_run_snapshot(wandb_run_id: str) -> Dict[str, Any]:
    api = wandb.Api()
    run = api.run(get_wandb_run_path(wandb_run_id))

    summary = dict(run.summary)

    return {
        "wandb_state": getattr(run, "state", None),
        "tap_status": map_wandb_state_to_tap_status(getattr(run, "state", None)),
        "url": getattr(run, "url", None),
        "summary": summary,
        "metrics": {
            "current_step": pick_metric(summary, ["_step", "global_step", "step"]),
            "current_epoch": pick_metric(summary, ["epoch", "current_epoch"]),
            "training_loss": pick_metric(
                summary,
                ["train_loss", "train/loss", "loss", "training_loss"],
            ),
            "validation_loss": pick_metric(
                summary,
                ["val_loss", "val/loss", "validation_loss", "valid/loss"],
            ),
            "runtime": pick_metric(
                summary,
                ["_runtime", "runtime", "train/runtime"],
            ),
            "learning_rate": pick_metric(
                summary,
                ["lr", "learning_rate", "optimizer/lr", "train/lr"],
            ),
        },
    }