"""Pure SLURM state-mapping functions. No SQL, no HTTP."""
from __future__ import annotations

import shlex
from typing import Any

from app.services.launcher import run_ssh_command


_SUCCESS_EXIT_CODES = {"", "0", "0:0", "completed", "complete", "success"}
_CANCEL_STATES = {"cancelled", "canceled", "ca"}
_QUEUED_STATES = {"pending", "queued", "pd", "configuring", "cf"}
_RUNNING_STATES = {"running", "r", "completing", "cg"}
_COMPLETED_STATES = {"completed", "complete", "cd"}
_FAILED_STATES = {
    "failed", "fail", "f", "timeout", "to", "node_fail", "nf",
    "out_of_memory", "oom", "preempted", "boot_fail", "deadline",
}


def _normalise(value: str | None) -> str:
    return (value or "").strip().lower()


def _state_tokens(*values: str | None) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = _normalise(value)
        if not text:
            continue
        tokens.add(text)
        tokens.add(text.split()[0])
        tokens.add(text.split("+")[0])
    return tokens


def _exit_code_is_success(exit_status: str | None) -> bool:
    status = _normalise(exit_status)
    if status in _SUCCESS_EXIT_CODES:
        return True
    if ":" in status:
        return status.split(":", 1)[0] == "0"
    return False


def derive_run_status(
    current_status: str,
    queue_state: str | None,
    execution_state: str | None,
    exit_status: str | None,
) -> str:
    current_status = _normalise(current_status)
    states = _state_tokens(queue_state, execution_state)

    if current_status == "cancelled":
        return "cancelled"
    if states & _CANCEL_STATES or any("cancel" in s for s in states):
        return "cancelled"
    if states & _COMPLETED_STATES or any("complete" in s for s in states):
        return "completed" if _exit_code_is_success(exit_status) else "failed"
    if states & _FAILED_STATES or any(
        marker in s for s in states for marker in ("fail", "timeout", "out_of_memory", "oom")
    ):
        return "failed"
    if exit_status and not _exit_code_is_success(exit_status):
        return "failed"
    if states & _RUNNING_STATES:
        return "running"
    if states & _QUEUED_STATES:
        return "queued"
    return current_status or "unknown"


def reconcile_run_status(
    *,
    current_status: str,
    slurm_status: str | None = None,
    wandb_status: str | None = None,
) -> str:
    current = _normalise(current_status)
    slurm = _normalise(slurm_status)
    wandb = _normalise(wandb_status)

    if current == "cancelled" or slurm == "cancelled" or wandb == "cancelled":
        return "cancelled"
    if slurm == "failed" or wandb == "failed":
        return "failed"
    if slurm == "completed" or wandb == "completed":
        return "completed"
    if slurm == "running" or wandb == "running":
        return "running"
    if slurm == "queued":
        return "queued"
    return current or wandb or slurm or "unknown"


def refresh_job_from_slurm(job_id: str) -> dict[str, Any]:
    code, stdout, _ = run_ssh_command(
        f"squeue -j {shlex.quote(job_id)} -h -o '%T|%N'"
    )
    if code == 0 and stdout.strip():
        parts = stdout.strip().split("|", 1)
        queue_state = parts[0].strip()
        node_info = parts[1].strip() if len(parts) > 1 else None
        return {
            "job_id": job_id,
            "queue_state": queue_state,
            "execution_state": queue_state.lower(),
            "node_info": node_info,
            "start_time": None,
            "end_time": None,
            "exit_status": None,
            "source": "squeue",
        }

    code, stdout, _ = run_ssh_command(
        f"sacct -j {shlex.quote(job_id)} --format=State,NodeList,Start,End,ExitCode -P -n"
    )
    if code == 0 and stdout.strip():
        parts = stdout.strip().splitlines()[0].split("|")
        state = parts[0].strip() if parts else None
        return {
            "job_id": job_id,
            "queue_state": state,
            "execution_state": state.lower() if state else None,
            "node_info": parts[1].strip() if len(parts) > 1 else None,
            "start_time": parts[2].strip() or None if len(parts) > 2 else None,
            "end_time": parts[3].strip() or None if len(parts) > 3 else None,
            "exit_status": parts[4].strip() or None if len(parts) > 4 else None,
            "source": "sacct",
        }

    return {
        "job_id": job_id,
        "queue_state": None,
        "execution_state": None,
        "node_info": None,
        "start_time": None,
        "end_time": None,
        "exit_status": None,
        "source": "unknown",
    }
