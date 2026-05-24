from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricSnapshot:
    run_id: str
    current_step: int | None = None
    current_epoch: int | None = None
    training_loss: float | None = None
    validation_loss: float | None = None
    runtime: float | None = None
    learning_rate: float | None = None
    latest_metric_timestamp: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> MetricSnapshot:
        d = dict(row)
        return cls(
            run_id=d["run_id"],
            current_step=d.get("current_step"),
            current_epoch=d.get("current_epoch"),
            training_loss=d.get("training_loss"),
            validation_loss=d.get("validation_loss"),
            runtime=d.get("runtime"),
            learning_rate=d.get("learning_rate"),
            latest_metric_timestamp=d.get("latest_metric_timestamp"),
        )


@dataclass
class MetricPoint:
    run_id: str
    step: int
    source: str
    metrics: dict[str, float] = field(default_factory=dict)
    point_id: str = ""
    epoch: int | None = None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> MetricPoint:
        d = dict(row)
        raw = d.get("metrics_json") or "{}"
        try:
            metrics = json.loads(raw)
        except (ValueError, TypeError):
            metrics = {}
        return cls(
            point_id=d.get("point_id", ""),
            run_id=d["run_id"],
            step=d["step"],
            epoch=d.get("epoch"),
            source=d.get("source", "manual"),
            metrics=metrics,
            created_at=d.get("created_at"),
        )


@dataclass
class MetricSyncStatus:
    run_id: str
    source: str | None = None
    status: str = "never_synced"
    last_started_at: str | None = None
    last_finished_at: str | None = None
    error_message: str | None = None
    points_synced: int = 0

    @classmethod
    def from_row(cls, row: Any) -> MetricSyncStatus:
        d = dict(row)
        return cls(
            run_id=d["run_id"],
            source=d.get("source"),
            status=d.get("status", "never_synced"),
            last_started_at=d.get("last_started_at"),
            last_finished_at=d.get("last_finished_at"),
            error_message=d.get("error_message"),
            points_synced=d.get("points_synced", 0),
        )
