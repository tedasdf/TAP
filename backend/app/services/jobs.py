from typing import Optional


def derive_run_status(
    current_status: str,
    queue_state: Optional[str],
    execution_state: Optional[str],
    exit_status: Optional[str],
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
        or ("timeout" in queue_state)
        or ("timeout" in execution_state)
        or ("node_fail" in queue_state)
        or ("node_fail" in execution_state)
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