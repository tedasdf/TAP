from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class RunCreate(BaseModel):
    name: str
    git_commit: str | None = None
    config_path: str
    config_overrides: dict[str, Any] | None = None
    submit_script: str | None = None
    wandb_config_ref: str | None = None
    wandb_run_id: str | None = None
    launch_now: bool = False


class RunResponse(BaseModel):
    run_id: str
    name: str
    status: str
    git_commit: str
    config_path: str
    config_overrides: dict[str, Any] | None = None
    config_snapshot: dict[str, Any] | None = None
    wandb_config_ref: str | None = None
    slurm_job_id: str | None = None
    wandb_run_id: str | None = None
    created_at: str
    last_checked_at: str | None = None
    error_message: str | None = None


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


class ParamFixed(BaseModel):
    role: Literal["fixed"]
    value: str | int | float


class ParamVary(BaseModel):
    role: Literal["vary"]
    values: list[str | int | float]


class ParamDerive(BaseModel):
    role: Literal["derive"]
    expr: str
    from_param: str = Field(alias="from")

    model_config = {"populate_by_name": True}


class CreateTemplateRequest(BaseModel):
    name: str
    description: str | None = None
    params: dict[str, ParamFixed | ParamVary | ParamDerive]


class TemplateResponse(BaseModel):
    template_id: str
    name: str
    description: str | None
    params: dict
    created_at: str
    run_count: int


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]


class TemplateSummaryResponse(TemplateResponse):
    runs: list[dict]


class RunCombo(BaseModel):
    combo_index: int
    params: dict[str, str | int | float]
    derive_trace: dict[str, str]


class PreviewResponse(BaseModel):
    template_id: str
    total_runs: int
    combos: list[RunCombo]


class LaunchTemplateRequest(BaseModel):
    git_commit: str | None = None
    max_steps: int | None = None
    dry_run: bool = False


class LaunchResponse(BaseModel):
    template_id: str
    total: int
    launched: int
    failed: int
    runs: list[dict]


class TemplateRunItem(BaseModel):
    run_id: str
    name: str
    combo_index: int
    status: str
    slurm_job_id: str | None
    created_at: str
    params: dict
    metrics: dict | None


class TemplateRunsResponse(BaseModel):
    template_id: str
    template_name: str
    runs: list[TemplateRunItem]