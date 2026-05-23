from __future__ import annotations

import shlex
from typing import Any

from fastapi import HTTPException, APIRouter

from app.db import get_db
from app.repositories.run_repo import RunRepository
from app.schemas import RunCreate, RunResponse, RunEventResponse, RunCompareEntry, RunCompareResponse
from app.services.launcher import run_ssh_command
from app.services.run_service import RunNotFoundError, RunService


router = APIRouter(tags=["runs"])


def _make_service(conn) -> RunService:
    return RunService(conn)


@router.post("/runs", response_model=RunResponse)
def create_run(payload: RunCreate) -> RunResponse:
    try:
        with get_db() as conn:
            run = _make_service(conn).create(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return RunResponse.from_domain(run)


@router.get("/runs")
def list_runs() -> list[RunResponse]:
    with get_db() as conn:
        runs = RunRepository(conn).list_all()
    return [RunResponse.from_domain(r) for r in runs]


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> RunResponse:
    with get_db() as conn:
        run = RunRepository(conn).find(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return RunResponse.from_domain(run)


@router.post("/runs/refresh-active")
def refresh_active_runs_endpoint() -> dict[str, Any]:
    with get_db() as conn:
        run_ids = [r.run_id for r in RunRepository(conn).list_active()]

    refreshed = []
    failed = []
    for run_id in run_ids:
        try:
            with get_db() as conn:
                run = _make_service(conn).refresh(run_id)
            refreshed.append({"run_id": run_id, "status": run.status})
        except Exception as exc:
            failed.append({"run_id": run_id, "error": str(exc)})

    return {
        "total": len(run_ids),
        "refreshed": refreshed,
        "failed": failed,
        "refreshed_count": len(refreshed),
        "failed_count": len(failed),
    }


@router.post("/runs/{run_id}/refresh")
def refresh_run(run_id: str) -> dict[str, Any]:
    try:
        with get_db() as conn:
            run = _make_service(conn).refresh(run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {"run": RunResponse.from_domain(run).model_dump()}


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, str]:
    try:
        with get_db() as conn:
            run = _make_service(conn).cancel(run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"run_id": run.run_id, "status": run.status}


@router.get("/runs/{run_id}/events")
def list_run_events(run_id: str) -> list[RunEventResponse]:
    with get_db() as conn:
        if RunRepository(conn).find(run_id) is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        events = RunRepository(conn).events.list_for_run(run_id)
    return [RunEventResponse.from_domain(e) for e in events]


@router.get("/runs/{run_id}/logs")
def get_run_logs(run_id: str, tail_lines: int = 300) -> dict[str, Any]:
    with get_db() as conn:
        run = RunRepository(conn).find(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        job = RunRepository(conn).jobs.find(run.slurm_job_id) if run.slurm_job_id else None

    if not run.slurm_job_id:
        no_job_msg = "No Slurm job ID associated with this run"
        return _logs_response(run_id, None, no_job_msg, no_job_msg)

    if job is None:
        no_row_msg = "No job row found for this run"
        return _logs_response(run_id, run.slurm_job_id, no_row_msg, no_row_msg)

    return {
        "run_id": run_id,
        "job_id": run.slurm_job_id,
        "stdout": _read_remote_log(job.log_path, tail_lines=tail_lines),
        "stderr": _read_remote_log(job.error_log_path, tail_lines=tail_lines),
    }


def _logs_response(run_id: str, job_id: str | None, stdout_err: str, stderr_err: str) -> dict[str, Any]:
    empty = {"path": None, "exists": False, "content": "", "error": stdout_err}
    return {"run_id": run_id, "job_id": job_id, "stdout": empty, "stderr": {**empty, "error": stderr_err}}


def _read_remote_log(path: str | None, *, tail_lines: int = 300) -> dict[str, Any]:
    if not path:
        return {"path": None, "exists": False, "content": "", "error": "No log path stored"}

    safe_path = shlex.quote(path)
    safe_lines = max(1, min(tail_lines, 2000))
    command = (
        f"if [ -f {safe_path} ]; then tail -n {safe_lines} {safe_path}; "
        f"else echo '__TAP_LOG_FILE_MISSING__'; fi"
    )
    code, stdout, stderr = run_ssh_command(command)

    if code != 0:
        return {"path": path, "exists": False, "content": "", "error": stderr or f"Failed to read {path}"}
    if "__TAP_LOG_FILE_MISSING__" in stdout:
        return {"path": path, "exists": False, "content": "", "error": "Log file does not exist yet"}
    return {"path": path, "exists": True, "content": stdout, "error": None}


@router.get("/runs/compare", response_model=RunCompareResponse)
def compare_runs(run_ids: str) -> RunCompareResponse:
    """
    Compare 2-5 runs side by side.
    Usage: GET /runs/compare?run_ids=id1,id2,id3
    """
    ids = [r.strip() for r in run_ids.split(",") if r.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 run_ids")
    if len(ids) > 5:
        raise HTTPException(status_code=400, detail="Compare at most 5 runs at a time")

    entries: list[RunCompareEntry] = []

    with get_db() as conn:
        run_repo = RunRepository(conn)
        for run_id in ids:
            run = run_repo.find(run_id)
            if run is None:
                raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

            snapshot = run_repo.metrics.find_snapshot(run_id)
            best_val_loss = run_repo.metrics.get_best_validation_loss(run_id)

            entries.append(RunCompareEntry(
                run_id=run.run_id,
                name=run.name,
                status=run.status,
                git_commit=run.git_commit,
                config_path=run.config_path,
                created_at=run.created_at,
                error_message=run.error_message,
                current_step=snapshot.current_step if snapshot else None,
                current_epoch=snapshot.current_epoch if snapshot else None,
                training_loss=snapshot.training_loss if snapshot else None,
                validation_loss=snapshot.validation_loss if snapshot else None,
                best_validation_loss=best_val_loss,
                learning_rate=snapshot.learning_rate if snapshot else None,
                runtime=snapshot.runtime if snapshot else None,
                config_overrides=run.config_overrides,
                config_snapshot=run.config_snapshot or None,
            ))

    config_diff = _diff_configs(entries)
    return RunCompareResponse(runs=entries, config_diff=config_diff)


def _diff_configs(entries: list[RunCompareEntry]) -> dict:
    """Return only the config_override keys where runs differ."""
    if len(entries) < 2:
        return {}

    all_keys: set[str] = set()
    for e in entries:
        all_keys.update(e.config_overrides.keys())

    diff: dict = {}
    for key in sorted(all_keys):
        values = {e.run_id: e.config_overrides.get(key) for e in entries}
        unique_vals = set(str(v) for v in values.values())
        if len(unique_vals) > 1:  # only include keys where runs differ
            diff[key] = values

    return diff