
import shlex
from typing import Any, Optional

from app.services.launcher import run_ssh_command

def derive_run_status(
    current_status: str,
    queue_state: Optional[str],
    execution_state: Optional[str],
    exit_status: Optional[str],
) -> str:
    queue_state = (queue_state or "").strip().lower()
    execution_state = (execution_state or "").strip().lower()
    exit_status = (exit_status or "").strip().lower()

    if current_status in {"completed", "failed", "cancelled"}:
        return current_status

    states = {queue_state, execution_state}

    def exit_success(value: str) -> bool:
        if value in {"", "0", "0:0", "completed", "complete", "success"}:
            return True
        if ":" in value:
            return value.split(":", 1)[0] == "0"
        return False

    if any("cancel" in s or s in {"ca", "cancelled", "canceled"} for s in states):
        return "cancelled"

    if any(s in {"completed", "complete", "cd"} or "complete" in s for s in states):
        return "completed" if exit_success(exit_status) else "failed"

    if any(
        "fail" in s
        or "timeout" in s
        or "node_fail" in s
        or "out_of_memory" in s
        or "oom" in s
        or s in {"f", "to", "nf"}
        for s in states
    ):
        return "failed"

    if exit_status and not exit_success(exit_status):
        return "failed"

    if any(s in {"running", "r", "completing", "cg"} for s in states):
        return "running"

    if any(s in {"pending", "queued", "pd", "configuring", "cf"} for s in states):
        return "queued"

    return current_status or "unknown"




def refresh_job_from_slurm(job_id: str) -> dict[str, Any]:
    squeue_cmd = f"squeue -j {shlex.quote(job_id)} -h -o '%T|%N'"
    code, stdout, stderr = run_ssh_command(squeue_cmd)

    if code == 0 and stdout.strip():
        first_line = stdout.strip().splitlines()[0]
        parts = first_line.split("|", 1)

        queue_state = parts[0].strip() if len(parts) > 0 else None
        node_info = parts[1].strip() if len(parts) > 1 else None

        return {
            "job_id": job_id,
            "queue_state": queue_state,
            "execution_state": queue_state,
            "node_info": node_info,
            "start_time": None,
            "end_time": None,
            "exit_status": None,
            "source": "squeue",
        }

    sacct_cmd = (
        f"sacct -j {shlex.quote(job_id)} "
        "--format=State,NodeList,Start,End,ExitCode -P -n"
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
            "execution_state": state,
            "node_info": node_info or None,
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