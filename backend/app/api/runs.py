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
from app.services.jobs import derive_run_status, refresh_job_from_slurm
from app.services.run_events import create_run_event


from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

import shlex

M3_REPO_PATH = "/home/slo/vf38_scratch2/sloo0021/slm_repo"

def resolve_remote_training_git_commit() -> str | None:
    remote_repo_path = M3_REPO_PATH

    code, stdout, stderr = run_ssh_command(
        f"cd {shlex.quote(remote_repo_path)} && git rev-parse HEAD"
    )

    if code != 0:
        return None

    commit = stdout.strip()
    return commit or None

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
    error_log_path: str | None = None

    resolved_git_commit = payload.git_commit or resolve_remote_training_git_commit()

    if payload.launch_now and not resolved_git_commit:
        raise HTTPException(
            status_code=400,
            detail="launch_now=true requires a valid git commit, but TAP could not resolve one.",
        )

    git_commit = resolved_git_commit or "unknown"

    if payload.launch_now:
        code, stdout, stderr, slurm_job_id = launch_training_run(
            run_name=payload.name,
            git_commit=git_commit,
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
                git_commit,
                payload.config_path,
                json_dumps(payload.config_overrides),
                payload.wandb_config_ref,
                slurm_job_id,
                payload.wandb_run_id,
                created_at,
                error_message,
            ),
        )

        conn.execute(
            """
            INSERT INTO run_events (
                event_id,
                run_id,
                event_type,
                message,
                old_status,
                new_status,
                created_at,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                run_id,
                "RUN_CREATED",
                "Run was created",
                None,
                status,
                created_at,
                json_dumps(
                    {
                        "name": payload.name,
                        "config_path": payload.config_path,
                        "launch_now": payload.launch_now,
                        "slurm_job_id": slurm_job_id,
                        "wandb_run_id": payload.wandb_run_id,
                    }
                ),
            ),
        )

        if slurm_job_id:

            conn.execute(
                """
                INSERT INTO run_events (
                    event_id,
                    run_id,
                    event_type,
                    message,
                    old_status,
                    new_status,
                    created_at,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    run_id,
                    "SLURM_JOB_SUBMITTED",
                    f"Slurm job {slurm_job_id} was submitted",
                    "created",
                    "queued",
                    created_at,
                    json_dumps(
                        {
                            "slurm_job_id": slurm_job_id,
                            "log_path": log_path,
                            "error_log_path": error_log_path,
                        }
                    ),
                ),
            )

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
        git_commit=git_commit,
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


@router.post("/runs/{run_id}/refresh")
def refresh_run(run_id: str) -> dict[str, Any]:
    run_row = ensure_run_exists(run_id)
    checked_at = utc_now_iso()

    slurm_job_id = run_row.get("slurm_job_id")

    if not slurm_job_id:
        with get_db() as conn:
            conn.execute(
                """
                UPDATE runs
                SET last_checked_at = ?
                WHERE run_id = ?
                """,
                (checked_at, run_id),
            )

            updated_run = conn.execute(
                "SELECT * FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

        run_dict = dict(updated_run)
        run_dict["config_overrides"] = json_loads(run_dict.get("config_overrides"))

        return {
            "run": run_dict,
            "job": None,
            "sync": {
                "checked_at": checked_at,
                "message": "Run has no Slurm job ID, so no Slurm refresh was performed.",
            },
        }

    job_snapshot = refresh_job_from_slurm(slurm_job_id)

    old_status = run_row["status"]

    new_status = derive_run_status(
        current_status=old_status,
        queue_state=job_snapshot["queue_state"],
        execution_state=job_snapshot["execution_state"],
        exit_status=job_snapshot["exit_status"],
    )

    with get_db() as conn:
        existing_job = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (slurm_job_id,),
        ).fetchone()

        if existing_job:
            conn.execute(
                """
                UPDATE jobs
                SET queue_state = ?,
                    execution_state = ?,
                    node_info = ?,
                    start_time = ?,
                    end_time = ?,
                    exit_status = ?
                WHERE job_id = ?
                """,
                (
                    job_snapshot["queue_state"],
                    job_snapshot["execution_state"],
                    job_snapshot["node_info"],
                    job_snapshot["start_time"],
                    job_snapshot["end_time"],
                    job_snapshot["exit_status"],
                    slurm_job_id,
                ),
            )
        else:
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
                    exit_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slurm_job_id,
                    run_id,
                    job_snapshot["queue_state"],
                    job_snapshot["execution_state"],
                    job_snapshot["node_info"],
                    job_snapshot["start_time"],
                    job_snapshot["end_time"],
                    job_snapshot["exit_status"],
                ),
            )

        if new_status != old_status:
            create_run_event(
                conn,
                run_id=run_id,
                event_type="STATUS_CHANGED",
                message=f"Run status changed from {old_status} to {new_status}",
                old_status=old_status,
                new_status=new_status,
                payload={
                    "slurm_job_id": slurm_job_id,
                    "queue_state": job_snapshot["queue_state"],
                    "execution_state": job_snapshot["execution_state"],
                    "exit_status": job_snapshot["exit_status"],
                    "source": job_snapshot.get("source"),
                },
            )

        conn.execute(
            """
            UPDATE runs
            SET status = ?,
                last_checked_at = ?
            WHERE run_id = ?
            """,
            (new_status, checked_at, run_id),
        )

        updated_run = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

        updated_job = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (slurm_job_id,),
        ).fetchone()

    run_dict = dict(updated_run)
    run_dict["config_overrides"] = json_loads(run_dict.get("config_overrides"))

    return {
        "run": run_dict,
        "job": dict(updated_job) if updated_job else None,
        "sync": {
            "checked_at": checked_at,
            "slurm_job_id": slurm_job_id,
            "slurm_status": new_status,
            "job_source": job_snapshot.get("source"),
        },
    }

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