import shlex
from typing import Any

from app.services.launcher import run_ssh_command


def derive_run_status(
    current_status: str,
    queue_state: str | None,
    execution_state: str | None,
    exit_status: str | None,
) -> str:
    queue_state = (queue_state or "").lower()
    execution_state = (execution_state or "").lower()
    exit_status = (exit_status or "").lower()

    if current_status == "cancelled":
        return "cancelled"

    if "cancel" in queue_state or "cancel" in execution_state:
        return "cancelled"

    if (
        "fail" in queue_state
        or "fail" in execution_state
        or "timeout" in queue_state
        or "timeout" in execution_state
        or "node_fail" in queue_state
        or "node_fail" in execution_state
        or exit_status not in {"", "0", "completed", "success"}
    ):
        return "failed"

    if "complete" in queue_state or "complete" in execution_state:
        return "completed"

    if queue_state == "running" or execution_state == "running":
        return "running"

    if queue_state in {"pending", "queued"} or execution_state in {"pending", "queued"}:
        return "queued"

    return current_status


def refresh_job_from_slurm(job_id: str) -> dict[str, Any]:
    squeue_cmd = (
        f"squeue -j {shlex.quote(job_id)} -h -o '%T|%N'"
    )
    code, stdout, stderr = run_ssh_command(squeue_cmd)

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

    sacct_cmd = (
        f"sacct -j {shlex.quote(job_id)} --format=State,NodeList,Start,End,ExitCode -P -n"
    )
    code, stdout, stderr = run_ssh_command(sacct_cmd)

    if code == 0 and stdout.strip():
        first_line = stdout.strip().splitlines()[0]
        parts = first_line.split("|")

        state = parts[0].strip() if len(parts) > 0 else None
        node_info = parts[1].strip() if len(parts) > 1 else None
        start_time = parts[2].strip() if len(parts) > 2 else None
        end_time = parts[3].strip() if len(parts) > 3 else None
        exit_status = parts[4].strip() if len(parts) > 4 else None

        return {
            "job_id": job_id,
            "queue_state": state,
            "execution_state": state.lower() if state else None,
            "node_info": node_info,
            "start_time": start_time or None,
            "end_time": end_time or None,
            "exit_status": exit_status or None,
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