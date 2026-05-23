from __future__ import annotations

import shlex
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.repositories.job_repo import JobRepository
from app.repositories.run_repo import RunRepository
from app.schemas import JobResponse, JobUpdate
from app.services.jobs import derive_run_status
from app.services.launcher import run_ssh_command


router = APIRouter(tags=["jobs"])


@router.get("/jobs")
def list_jobs() -> list[JobResponse]:
    with get_db() as conn:
        jobs = JobRepository(conn).list_all()
    return [JobResponse.from_domain(j) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> JobResponse:
    with get_db() as conn:
        job = JobRepository(conn).find(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return JobResponse.from_domain(job)


@router.patch("/jobs/{job_id}")
def update_job(job_id: str, payload: JobUpdate) -> JobResponse:
    updates = payload.model_dump(exclude_none=True)

    with get_db() as conn:
        job_repo = JobRepository(conn)
        run_repo = RunRepository(conn)

        job = job_repo.find(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

        if updates:
            job_repo.update(job_id, **updates)
            job = job_repo.find(job_id)

        run = run_repo.find(job.run_id)  # type: ignore[union-attr]
        if run is not None:
            new_run_status = derive_run_status(
                current_status=run.status,
                queue_state=job.queue_state,  # type: ignore[union-attr]
                execution_state=job.execution_state,  # type: ignore[union-attr]
                exit_status=job.exit_status,  # type: ignore[union-attr]
            )
            run_repo.update_status(run.run_id, new_run_status)

    return JobResponse.from_domain(job)  # type: ignore[arg-type]


@router.get("/jobs/{job_id}/logs")
def get_job_logs(job_id: str, lines: int = 50, stream: str = "out") -> dict[str, Any]:
    if lines <= 0:
        raise HTTPException(status_code=400, detail="'lines' must be greater than 0")
    stream = stream.lower()
    if stream not in {"out", "err"}:
        raise HTTPException(status_code=400, detail="stream must be 'out' or 'err'")

    with get_db() as conn:
        job = JobRepository(conn).find(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    queue_state = (job.queue_state or "").lower()
    execution_state = (job.execution_state or "").lower()
    log_path = job.log_path if stream == "out" else job.error_log_path

    if not log_path and queue_state in {"pending", "queued"}:
        return {"job_id": job_id, "stream": stream, "status": "pending",
                "message": "Job has not started yet, so no log path is available.", "lines": []}

    if not log_path and execution_state in {"pending", "queued"}:
        return {"job_id": job_id, "stream": stream, "status": "pending",
                "message": "Job has not started yet, so no log path is available.", "lines": []}

    if not log_path:
        raise HTTPException(status_code=404, detail=f"No {stream} log path stored for this job")

    code, stdout, stderr = run_ssh_command(f"tail -n {lines} {shlex.quote(log_path)}")
    if code != 0:
        raise HTTPException(status_code=404, detail=stderr or f"Could not read log file: {log_path}")

    return {
        "job_id": job_id,
        "stream": stream,
        "status": execution_state or queue_state or "unknown",
        "log_path": log_path,
        "lines": stdout.splitlines(),
    }
