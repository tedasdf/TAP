import shlex
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.schemas import JobUpdate
from app.services.jobs import derive_run_status
from app.services.launcher import run_ssh_command
from app.services.run_events import create_run_event


router = APIRouter(tags=["jobs"])


def ensure_job_exists(job_id: str) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return dict(row)


@router.get("/jobs")
def list_jobs() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM jobs
            ORDER BY COALESCE(datetime(start_time), datetime(end_time)) DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    return ensure_job_exists(job_id)


@router.patch("/jobs/{job_id}")
def update_job(job_id: str, payload: JobUpdate) -> dict[str, Any]:
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return ensure_job_exists(job_id)

    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [job_id]

        conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE job_id = ?",
            values,
        )

        updated = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

        run_row = conn.execute(
            "SELECT status FROM runs WHERE run_id = ?",
            (updated["run_id"],),
        ).fetchone()
        
        if run_row is None:
            raise HTTPException(
                status_code=500,
                detail=f"Job '{job_id}' points to missing run '{updated['run_id']}'",
            )

        old_run_status = run_row["status"]

        new_run_status = derive_run_status(
            current_status=old_run_status,
            queue_state=updated["queue_state"],
            execution_state=updated["execution_state"],
            exit_status=updated["exit_status"],
        )

        if new_run_status != old_run_status:
            create_run_event(
                conn,
                run_id=updated["run_id"],
                event_type="STATUS_CHANGED",
                message=f"Run status changed from {old_run_status} to {new_run_status}",
                old_status=old_run_status,
                new_status=new_run_status,
                payload={
                    "source": "PATCH /jobs/{job_id}",
                    "job_id": job_id,
                    "queue_state": updated["queue_state"],
                    "execution_state": updated["execution_state"],
                    "exit_status": updated["exit_status"],
                },
            )

        conn.execute(
            "UPDATE runs SET status = ? WHERE run_id = ?",
            (new_run_status, updated["run_id"]),
        )

    return dict(updated)


@router.get("/jobs/{job_id}/logs")
def get_job_logs(job_id: str, lines: int = 50, stream: str = "out") -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if lines <= 0:
        raise HTTPException(status_code=400, detail="'lines' must be greater than 0")

    stream = stream.lower()
    if stream not in {"out", "err"}:
        raise HTTPException(status_code=400, detail="stream must be 'out' or 'err'")

    queue_state = (row["queue_state"] or "").lower()
    execution_state = (row["execution_state"] or "").lower()

    log_path = row["log_path"] if stream == "out" else row["error_log_path"]

    if not log_path and queue_state in {"pending", "queued"}:
        return {
            "job_id": job_id,
            "stream": stream,
            "status": "pending",
            "message": "Job has not started yet, so no log path is available.",
            "lines": [],
        }

    if not log_path and execution_state in {"pending", "queued"}:
        return {
            "job_id": job_id,
            "stream": stream,
            "status": "pending",
            "message": "Job has not started yet, so no log path is available.",
            "lines": [],
        }

    if not log_path:
        raise HTTPException(status_code=404, detail=f"No {stream} log path stored for this job")

    remote_command = f"tail -n {lines} {shlex.quote(log_path)}"
    code, stdout, stderr = run_ssh_command(remote_command)

    if code != 0:
        raise HTTPException(
            status_code=404,
            detail=stderr or f"Could not read log file: {log_path}",
        )

    return {
        "job_id": job_id,
        "stream": stream,
        "status": execution_state or queue_state or "unknown",
        "log_path": log_path,
        "lines": stdout.splitlines(),
    }