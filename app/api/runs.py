# POST /runs
# GET /runs
# GET /runs/{run_id}
# POST /runs/{run_id}/cancel

import json
import shlex
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.schemas import RunCreate, RunResponse
from app.services.launcher import (
    launch_training_run,
    build_remote_log_path,
    build_remote_error_log_path,
    run_ssh_command,
)

router = APIRouter(tags=["runs"])


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)


def ensure_run_exists(run_id: str) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return dict(row)

@router.post("/runs", response_model=RunResponse)
def create_run(payload: RunCreate) -> RunResponse:
    run_id = str(uuid.uuid4())
    created_at = utc_now_iso()

    status = "created"
    slurm_job_id: str | None = None
    error_message: str | None = None
    log_path: str | None = None
    error_log_path = None

    if payload.launch_now:
        code, stdout, stderr, slurm_job_id = launch_training_run(
            run_name=payload.name,
            git_commit=payload.git_commit,
            config_path=payload.config_path,
            config_overrides=payload.config_overrides,
            submit_script=payload.submit_script,
        )

        combined_output = "\n".join(part for part in [stdout, stderr] if part)

        if code == 0 and slurm_job_id:
            status = "queued"
            log_path = build_remote_log_path(payload.name, slurm_job_id)
            error_log_path = build_remote_error_log_path(payload.name, slurm_job_id)
        elif code == 0:
            status = "created"
            error_message = "Launch succeeded but no Slurm job ID was parsed"
        else:
            status = "failed"
            error_message = combined_output or f"Launch failed with exit code {code}"

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id,
                name,
                status,
                git_commit,
                config_path,
                config_overrides,
                wandb_config_ref,
                slurm_job_id,
                wandb_run_id,
                created_at,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                payload.name,
                status,
                payload.git_commit,
                payload.config_path,
                json_dumps(payload.config_overrides),
                payload.wandb_config_ref,
                slurm_job_id,
                payload.wandb_run_id,
                created_at,
                error_message,
            ),
        )

        if slurm_job_id:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id,
                    run_id,
                    queue_state,
                    execution_state,
                    node_info,
                    start_time,
                    end_time,
                    exit_status,
                    log_path,
                    error_log_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slurm_job_id,
                    run_id,
                    "queued",
                    None,
                    None,
                    None,
                    None,
                    None,
                    log_path,
                    error_log_path,
                ),
            )

    return RunResponse(
        run_id=run_id,
        name=payload.name,
        status=status,
        git_commit=payload.git_commit,
        config_path=payload.config_path,
        config_overrides=payload.config_overrides,
        wandb_config_ref=payload.wandb_config_ref,
        slurm_job_id=slurm_job_id,
        wandb_run_id=payload.wandb_run_id,
        created_at=created_at,
        error_message=error_message,
    )

@router.get("/runs")
def list_runs() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM runs
            ORDER BY datetime(created_at) DESC
            """
        ).fetchall()

    runs: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["config_overrides"] = json_loads(item.get("config_overrides"))
        runs.append(item)

    return runs


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    item = ensure_run_exists(run_id)
    item["config_overrides"] = json_loads(item.get("config_overrides"))
    return item

@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, str]:
    run_row = ensure_run_exists(run_id)
    slurm_job_id = run_row.get("slurm_job_id")

    if not slurm_job_id:
        raise HTTPException(status_code=400, detail="No Slurm job ID associated with this run")

    remote_command = f"scancel {shlex.quote(slurm_job_id)}"
    code, stdout, stderr = run_ssh_command(remote_command)

    if code != 0:
        raise HTTPException(
            status_code=500,
            detail=stderr or f"Failed to cancel Slurm job {slurm_job_id}",
        )

    with get_db() as conn:
        conn.execute(
            "UPDATE runs SET status = ?, error_message = ? WHERE run_id = ?",
            ("cancelled", "Cancelled from TAP", run_id),
        )

        conn.execute(
            """
            UPDATE jobs
            SET queue_state = ?, execution_state = ?
            WHERE job_id = ?
            """,
            ("cancelled", "cancelled", slurm_job_id),
        )

    return {"run_id": run_id, "status": "cancelled"}