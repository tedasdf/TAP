from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class RunCreate(BaseModel):
    name: str
    git_commit: str
    config_path: str
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    submit_script: str | None = None
    wandb_config_ref: str | None = None
    wandb_run_id: str | None = None


class RunResponse(BaseModel):
    run_id: str
    name: str
    status: str
    git_commit: str
    config_path: str
    config_overrides: dict[str, Any]
    wandb_config_ref: str | None
    slurm_job_id: str | None
    wandb_run_id: str | None
    created_at: str
    error_message: str | None


class JobUpdate(BaseModel):
    queue_state: str | None = None
    execution_state: str | None = None
    node_info: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    exit_status: str | None = None
    log_path: str | None = None


class MetricSnapshotUpsert(BaseModel):
    current_step: int | None = None
    current_epoch: int | None = None
    training_loss: float | None = None
    validation_loss: float | None = None
    runtime: float | None = None
    learning_rate: float | None = None
    latest_metric_timestamp: str = Field(default_factory=utc_now_iso)


class NotificationCreate(BaseModel):
    event_type: str
    message: str
    run_id: str | None = None
    job_id: str | None = None