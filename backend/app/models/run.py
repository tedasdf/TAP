from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


_ACTIVE_STATUSES = frozenset({"created", "queued", "running", "unknown"})
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

@dataclass
class Run:
    run_id: str
    name: str
    status: str
    git_commit: str
    config_path: str
    created_at: str
    config_overrides: dict[str, Any] = field(default_factory=dict)
    config_snapshot: dict[str, Any] = field(default_factory=dict)
    wandb_config_ref: str | None = None
    slurm_job_id: str | None = None
    wandb_run_id: str | None = None
    template_id: str | None = None
    last_checked_at: str | None = None
    error_message: str | None = None
    launch_mode: str = "slurm"          # NEW
    direct_pid: int | None = None       # NEW
    direct_log_path: str | None = None  # NEW

    @classmethod
    def from_row(cls, row: Any) -> Run:
        d = dict(row)
        overrides_raw = d.get("config_overrides")
        snapshot_raw = d.get("config_snapshot_json")
        return cls(
            run_id=d["run_id"],
            name=d["name"],
            status=d["status"],
            git_commit=d["git_commit"],
            config_path=d["config_path"],
            created_at=d["created_at"],
            config_overrides=_parse_json(overrides_raw),
            config_snapshot=_parse_json(snapshot_raw),
            wandb_config_ref=d.get("wandb_config_ref"),
            slurm_job_id=d.get("slurm_job_id"),
            wandb_run_id=d.get("wandb_run_id"),
            template_id=d.get("template_id"),
            last_checked_at=d.get("last_checked_at"),
            error_message=d.get("error_message"),
            launch_mode=d.get("launch_mode") or "slurm",   # NEW
            direct_pid=d.get("direct_pid"),                 # NEW
            direct_log_path=d.get("direct_log_path"),       # NEW
        )

    @property
    def is_active(self) -> bool:
        return self.status in _ACTIVE_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES


def _parse_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
