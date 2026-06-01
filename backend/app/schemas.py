from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RunCreate(BaseModel):
    name: str
    git_commit: str | None = None
    config_path: str
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    submit_script: str | None = None
    wandb_config_ref: str | None = None
    wandb_run_id: str | None = None
    launch_now: bool = True
    launch_mode: str = "slurm"  # "slurm" | "direct"
    template_id: str | None = None

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


class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


class LaunchTemplateRequest(BaseModel):
    config_path: str
    git_commit: str | None = None
    submit_script: str | None = None
    overrides_list: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

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
    config_snapshot: dict[str, Any] | None = None
    launch_mode: str = "slurm"
    direct_pid: int | None = None
    direct_log_path: str | None = None
    current_step: int | None = None
    current_epoch: int | None = None
    training_loss: float | None = None
    validation_loss: float | None = None
    runtime: float | None = None
    learning_rate: float | None = None
    latest_metric_timestamp: str | None = None

    @classmethod
    def from_domain(cls, run: Any) -> RunResponse:
        return cls(
            run_id=run.run_id,
            name=run.name,
            status=run.status,
            git_commit=run.git_commit,
            config_path=run.config_path,
            config_overrides=run.config_overrides,
            wandb_config_ref=run.wandb_config_ref,
            slurm_job_id=run.slurm_job_id,
            wandb_run_id=run.wandb_run_id,
            created_at=run.created_at,
            error_message=run.error_message,
            config_snapshot=run.config_snapshot or None,
            launch_mode=run.launch_mode,
            direct_pid=run.direct_pid,
            direct_log_path=run.direct_log_path,
            current_step=run.current_step,
            current_epoch=run.current_epoch,
            training_loss=run.training_loss,
            validation_loss=run.validation_loss,
            runtime=run.runtime,
            learning_rate=run.learning_rate,
            latest_metric_timestamp=run.latest_metric_timestamp,
        )

class JobResponse(BaseModel):
    job_id: str
    run_id: str
    queue_state: str | None
    execution_state: str | None
    node_info: str | None
    start_time: str | None
    end_time: str | None
    exit_status: str | None
    log_path: str | None
    error_log_path: str | None

    @classmethod
    def from_domain(cls, job: Any) -> JobResponse:
        return cls(
            job_id=job.job_id,
            run_id=job.run_id,
            queue_state=job.queue_state,
            execution_state=job.execution_state,
            node_info=job.node_info,
            start_time=job.start_time,
            end_time=job.end_time,
            exit_status=job.exit_status,
            log_path=job.log_path,
            error_log_path=job.error_log_path,
        )


class MetricSnapshotResponse(BaseModel):
    run_id: str
    current_step: int | None
    current_epoch: int | None
    training_loss: float | None
    validation_loss: float | None
    runtime: float | None
    learning_rate: float | None
    latest_metric_timestamp: str | None

    @classmethod
    def from_domain(cls, snap: Any) -> MetricSnapshotResponse:
        return cls(
            run_id=snap.run_id,
            current_step=snap.current_step,
            current_epoch=snap.current_epoch,
            training_loss=snap.training_loss,
            validation_loss=snap.validation_loss,
            runtime=snap.runtime,
            learning_rate=snap.learning_rate,
            latest_metric_timestamp=snap.latest_metric_timestamp,
        )


class MetricPointCreate(BaseModel):
    step: int
    epoch: int | None = None
    source: str = "manual"
    metrics: dict[str, float] = {}


class MetricPointResponse(BaseModel):
    point_id: str
    run_id: str
    step: int
    epoch: int | None
    source: str
    metrics: dict[str, float]
    created_at: str | None

    @classmethod
    def from_domain(cls, point: Any) -> "MetricPointResponse":
        return cls(
            point_id=point.point_id,
            run_id=point.run_id,
            step=point.step,
            epoch=point.epoch,
            source=point.source,
            metrics=point.metrics,
            created_at=point.created_at,
        )


class CheckpointPost(BaseModel):
    checkpoint_path: str
    is_best: bool = False


class MetricSyncStatusResponse(BaseModel):
    run_id: str
    source: str | None
    status: str
    last_started_at: str | None
    last_finished_at: str | None
    error_message: str | None
    points_synced: int

    @classmethod
    def from_domain(cls, s: Any) -> MetricSyncStatusResponse:
        return cls(
            run_id=s.run_id,
            source=s.source,
            status=s.status,
            last_started_at=s.last_started_at,
            last_finished_at=s.last_finished_at,
            error_message=s.error_message,
            points_synced=s.points_synced,
        )


class NotificationResponse(BaseModel):
    notification_id: str
    event_type: str
    severity: str
    title: str
    message: str
    run_id: str | None
    job_id: str | None
    timestamp: str
    read_state: int

    @classmethod
    def from_domain(cls, n: Any) -> NotificationResponse:
        return cls(
            notification_id=n.notification_id,
            event_type=n.event_type,
            severity=n.severity,
            title=n.title,
            message=n.message,
            run_id=n.run_id,
            job_id=n.job_id,
            timestamp=n.timestamp,
            read_state=int(n.read_state),
        )


class RunEventResponse(BaseModel):
    event_id: str
    run_id: str
    event_type: str
    message: str
    old_status: str | None
    new_status: str | None
    created_at: str
    payload: dict[str, Any]

    @classmethod
    def from_domain(cls, e: Any) -> RunEventResponse:
        return cls(
            event_id=e.event_id,
            run_id=e.run_id,
            event_type=e.event_type,
            message=e.message,
            old_status=e.old_status,
            new_status=e.new_status,
            created_at=e.created_at,
            payload=e.payload,
        )


class TemplateResponse(BaseModel):
    template_id: str
    name: str
    description: str
    params: dict[str, Any]
    created_at: str
    run_count: int

    @classmethod
    def from_domain(cls, t: Any) -> TemplateResponse:
        return cls(
            template_id=t.template_id,
            name=t.name,
            description=t.description,
            params=t.params,
            created_at=t.created_at,
            run_count=t.run_count,
        )


class RunCompareEntry(BaseModel):
    run_id: str
    name: str
    status: str
    git_commit: str
    config_path: str
    created_at: str
    error_message: str | None

    # latest metrics
    current_step: int | None
    current_epoch: int | None
    training_loss: float | None
    validation_loss: float | None
    best_validation_loss: float | None
    learning_rate: float | None
    runtime: float | None

    # config snapshot fields (flattened for easy comparison)
    config_overrides: dict[str, Any]
    config_snapshot: dict[str, Any] | None


class RunCompareResponse(BaseModel):
    runs: list[RunCompareEntry]
    config_diff: dict[str, Any]  # keys where runs differ