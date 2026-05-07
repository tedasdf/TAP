# POST /runs
# GET /runs
# GET /runs/{run_id}
# POST /runs/{run_id}/cancel

import json
import shlex
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, APIRouter
from app.db import get_db
from app.services.jobs import refresh_job_from_slurm, derive_run_status, reconcile_run_status
from app.services.wandb_client import get_run_snapshot
from app.services.metrics import insert_metric_history_from_latest, upsert_latest_metrics
from app.schemas import RunCreate, RunResponse
from app.services.launcher import (
    launch_training_run,
    build_remote_log_path,
    build_remote_error_log_path,
    run_ssh_command,
    get_remote_git_state,
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

def create_run_event(
    conn,
    *,
    run_id: str,
    event_type: str,
    message: str,
    old_status: str | None = None,
    new_status: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
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
            event_type,
            message,
            old_status,
            new_status,
            utc_now_iso(),
            json_dumps(payload),
        ),
    )

@router.post("/runs", response_model=RunResponse)
def create_run(payload: RunCreate) -> RunResponse:
    run_id = str(uuid.uuid4())
    created_at = utc_now_iso()

    try:
        git_state = get_remote_git_state()
        git_commit = payload.git_commit or git_state["commit"]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read slm_repo git state: {exc}",
        )

    status = "created"
    slurm_job_id: str | None = None
    error_message: str | None = None
    log_path: str | None = None
    error_log_path: str | None = None

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
        create_run_event(
            conn,
            run_id=run_id,
            event_type="RUN_CREATED",
            message="Run created from slm_repo",
            new_status=status,
            payload={
                "name": payload.name,
                "config_path": payload.config_path,
                "git_commit": git_commit,
                "launch_now": payload.launch_now,
            },
        )

        if slurm_job_id:
            create_run_event(
                conn,
                run_id=run_id,
                event_type="SLURM_JOB_SUBMITTED",
                message=f"Slurm job {slurm_job_id} submitted",
                new_status=status,
                payload={
                    "slurm_job_id": slurm_job_id,
                    "log_path": log_path,
                    "error_log_path": error_log_path,
                },
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


@router.get("/runs/{run_id}/events")
def list_run_events(run_id: str) -> list[dict[str, Any]]:
    ensure_run_exists(run_id)

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM run_events
            WHERE run_id = ?
            ORDER BY datetime(created_at) ASC
            """,
            (run_id,),
        ).fetchall()

    events = []
    for row in rows:
        item = dict(row)
        item["payload"] = json_loads(item.get("payload_json"))
        events.append(item)

    return events

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
    wandb_run_id = run_row.get("wandb_run_id")

    job_snapshot = None
    metrics_snapshot = None
    wandb_snapshot = None
    slurm_status = None
    wandb_status = None

    with get_db() as conn:
        if slurm_job_id:
            job_snapshot = refresh_job_from_slurm(slurm_job_id)

            existing_job = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (slurm_job_id,),
            ).fetchone()

            if existing_job:
                conn.execute(
                    """
                    UPDATE jobs
                    SET queue_state = ?, execution_state = ?, node_info = ?,
                        start_time = ?, end_time = ?, exit_status = ?
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

            slurm_status = derive_run_status(
                current_status=run_row["status"],
                queue_state=job_snapshot["queue_state"],
                execution_state=job_snapshot["execution_state"],
                exit_status=job_snapshot["exit_status"],
            )

        if wandb_run_id:
            try:
                wandb_snapshot = get_run_snapshot(wandb_run_id)
                wandb_status = wandb_snapshot.get("tap_status")
                metrics = wandb_snapshot["metrics"]

                metrics_snapshot = upsert_latest_metrics(
                    conn,
                    run_id=run_id,
                    current_step=metrics["current_step"],
                    current_epoch=metrics["current_epoch"],
                    training_loss=metrics["training_loss"],
                    validation_loss=metrics["validation_loss"],
                    runtime=metrics["runtime"],
                    learning_rate=metrics["learning_rate"],
                )
                insert_metric_history_from_latest(
                    conn,
                    run_id=run_id,
                    current_step=metrics["current_step"],
                    current_epoch=metrics["current_epoch"],
                    training_loss=metrics["training_loss"],
                    validation_loss=metrics["validation_loss"],
                    runtime=metrics["runtime"],
                    learning_rate=metrics["learning_rate"],
                    source="wandb_summary",
                )

            except Exception as exc:
                wandb_snapshot = {"error": str(exc)}
                metrics_snapshot = None

                create_run_event(
                    conn,
                    run_id=run_id,
                    event_type="WANDB_SYNC_FAILED",
                    message=f"W&B sync failed: {exc}",
                    old_status=run_row["status"],
                    new_status=None,
                    payload={
                        "wandb_run_id": wandb_run_id,
                        "error": str(exc),
                    },
                )

        new_status = reconcile_run_status(
            current_status=run_row["status"],
            slurm_status=slurm_status,
            wandb_status=wandb_status,
        )

        old_status = run_row["status"]

        if new_status != old_status:
            create_run_event(
                conn,
                run_id=run_id,
                event_type="STATUS_CHANGED",
                message=f"Run status changed from {old_status} to {new_status}",
                old_status=old_status,
                new_status=new_status,
                payload={
                    "slurm_status": slurm_status,
                    "wandb_status": wandb_status,
                    "slurm_job_id": slurm_job_id,
                    "wandb_run_id": wandb_run_id,
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

        updated_job = None
        if slurm_job_id:
            job_row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (slurm_job_id,),
            ).fetchone()
            updated_job = dict(job_row) if job_row else None

    run_dict = dict(updated_run)
    run_dict["config_overrides"] = json_loads(run_dict.get("config_overrides"))

    return {
        "run": run_dict,
        "job": updated_job,
        "metrics": metrics_snapshot,
        "sync": {
            "checked_at": checked_at,
            "slurm_status": slurm_status,
            "wandb_status": wandb_status,
            "wandb_state": (wandb_snapshot or {}).get("wandb_state") if isinstance(wandb_snapshot, dict) else None,
            "wandb_error": (wandb_snapshot or {}).get("error") if isinstance(wandb_snapshot, dict) else None,
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

        create_run_event(
            conn,
            run_id=run_id,
            event_type="RUN_CANCELLED",
            message=f"Run cancelled from TAP. Slurm job {slurm_job_id} was cancelled.",
            old_status=run_row["status"],
            new_status="cancelled",
            payload={
                "slurm_job_id": slurm_job_id,
                "stdout": stdout,
                "stderr": stderr,
            },
        )

    return {"run_id": run_id, "status": "cancelled"}