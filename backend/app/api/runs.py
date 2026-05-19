# POST /runs
# GET /runs
# GET /runs/{run_id}
# POST /runs/{run_id}/cancel

import json
import math
import shlex
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, APIRouter
from app.db import get_db

from app.schemas import RunCreate, RunResponse
from app.services.launcher import (
    launch_training_run,
    build_remote_log_path,
    build_remote_error_log_path,
    run_ssh_command,
    get_remote_git_state,
    read_remote_config_file,
)
from app.config import settings
from app.services.run_refresh import RunNotFoundError, refresh_run_by_id, refresh_active_runs


router = APIRouter(tags=["runs"])


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}
    

def resolve_git_commit_from_payload(payload_git_commit: str | None, remote_commit: str) -> str:
    """Resolve UI-friendly git refs into the actual commit stored by TAP."""
    requested = (payload_git_commit or "").strip()

    if not requested or requested.upper() == "HEAD":
        return remote_commit

    return requested


def parse_run_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["config_overrides"] = json_loads(item.get("config_overrides"))
    item["config_snapshot"] = json_loads(item.get("config_snapshot_json"))
    item.pop("config_snapshot_json", None)
    return item


def build_config_snapshot(
    *,
    payload: Any,
    git_commit: str,
    run_id: str,
    created_at: str,
    status: str,
    slurm_job_id: str | None = None,
    config_file_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_overrides = payload.config_overrides or {}

    dataset = config_overrides.get("data.dataset_name")
    tokenizer = config_overrides.get("tokenizer.path")

    submitted_at = created_at if payload.launch_now else None

    launch_command = None
    if payload.submit_script:
        launch_command = f"sbatch {payload.submit_script}"

    if config_file_snapshot is None:
        config_file_snapshot = {
            "path": payload.config_path,
            "source": None,
            "content": None,
            "error": "Config file was not snapshotted",
        }

    return {
        "run_id": run_id,
        "name": payload.name,
        "git_commit": git_commit,
        "config_path": payload.config_path,
        "config_overrides": config_overrides,
        "config_file": config_file_snapshot,
        "submit_script": payload.submit_script,
        "launch_now": payload.launch_now,
        "status_at_creation": status,
        "slurm_job_id": slurm_job_id,
        "wandb_config_ref": payload.wandb_config_ref,
        "wandb_run_id": payload.wandb_run_id,
        "created_at": created_at,

        "launch_metadata": {
            "submit_script": payload.submit_script,
            "remote_repo_path": settings.TAP_M3_REPO_PATH,
            "remote_host": settings.TAP_M3_HOST,
            "working_directory": settings.TAP_M3_REPO_PATH,
            "submitted_at": submitted_at,
            "launch_command": launch_command,
        },

        "data_references": {
            "dataset": dataset,
            "tokenizer": tokenizer,
            "raw_config_path": payload.config_path,
        },
    }


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


def create_notification_row(
    conn,
    *,
    event_type: str,
    severity: str,
    title: str,
    message: str,
    run_id: str | None = None,
    job_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO notifications (
            notification_id,
            event_type,
            severity,
            title,
            message,
            run_id,
            job_id,
            timestamp,
            read_state
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            str(uuid.uuid4()),
            event_type,
            severity,
            title,
            message,
            run_id,
            job_id,
            utc_now_iso(),
        ),
    )


def metric_to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_metric_value(metrics: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in metrics:
            return metrics[name]

    return None


def get_best_validation_loss(conn, run_id: str) -> float | None:
    row = conn.execute(
        """
        SELECT MIN(validation_loss) AS best_validation_loss
        FROM metric_points
        WHERE run_id = ?
          AND validation_loss IS NOT NULL
        """,
        (run_id,),
    ).fetchone()

    if row is None:
        return None

    return metric_to_float(row["best_validation_loss"])


def notification_already_exists(
    conn,
    *,
    run_id: str,
    event_type: str,
    message: str,
) -> bool:
    row = conn.execute(
        """
        SELECT notification_id
        FROM notifications
        WHERE run_id = ?
          AND event_type = ?
          AND message = ?
        LIMIT 1
        """,
        (run_id, event_type, message),
    ).fetchone()

    return row is not None


def create_metric_notification_once(
    conn,
    *,
    run_id: str,
    event_type: str,
    severity: str,
    title: str,
    message: str,
    job_id: str | None = None,
) -> None:
    if notification_already_exists(
        conn,
        run_id=run_id,
        event_type=event_type,
        message=message,
    ):
        return

    create_notification_row(
        conn,
        event_type=event_type,
        severity=severity,
        title=title,
        message=message,
        run_id=run_id,
        job_id=job_id,
    )


def create_metric_alert_notifications(
    conn,
    *,
    run_id: str,
    metrics: dict[str, Any],
    previous_best_validation_loss: float | None,
    job_id: str | None = None,
) -> None:
    step = get_metric_value(metrics, "current_step", "step", "global_step")

    train_loss = metric_to_float(
        get_metric_value(metrics, "training_loss", "train_loss")
    )
    validation_loss = metric_to_float(
        get_metric_value(metrics, "validation_loss", "val_loss")
    )

    step_text = f" at step {step}" if step is not None else ""

    if train_loss is not None and math.isnan(train_loss):
        create_metric_notification_once(
            conn,
            run_id=run_id,
            event_type="metric_train_loss_nan",
            severity="error",
            title="Training loss is NaN",
            message=f"Run {run_id} has NaN training loss{step_text}.",
            job_id=job_id,
        )

    if validation_loss is not None and math.isnan(validation_loss):
        create_metric_notification_once(
            conn,
            run_id=run_id,
            event_type="metric_validation_loss_nan",
            severity="error",
            title="Validation loss is NaN",
            message=f"Run {run_id} has NaN validation loss{step_text}.",
            job_id=job_id,
        )

    if validation_loss is None or math.isnan(validation_loss):
        return

    if (
        previous_best_validation_loss is None
        or validation_loss < previous_best_validation_loss
    ):
        create_metric_notification_once(
            conn,
            run_id=run_id,
            event_type="metric_new_best_validation_loss",
            severity="success",
            title="New best validation loss",
            message=(
                f"Run {run_id} reached validation loss "
                f"{validation_loss:.6g}{step_text}."
            ),
            job_id=job_id,
        )


def create_run_status_notification(
    conn,
    *,
    run_id: str,
    old_status: str | None,
    new_status: str,
    job_id: str | None = None,
) -> None:
    if old_status == new_status:
        return

    status = new_status.lower()

    if status == "running":
        create_notification_row(
            conn,
            event_type="run_started",
            severity="info",
            title="Run started",
            message=f"Run {run_id} has started running.",
            run_id=run_id,
            job_id=job_id,
        )
        return

    if status == "completed":
        create_notification_row(
            conn,
            event_type="run_completed",
            severity="success",
            title="Run completed",
            message=f"Run {run_id} completed successfully.",
            run_id=run_id,
            job_id=job_id,
        )
        return

    if status == "failed":
        create_notification_row(
            conn,
            event_type="run_failed",
            severity="error",
            title="Run failed",
            message=f"Run {run_id} failed.",
            run_id=run_id,
            job_id=job_id,
        )
        return

    if status == "cancelled":
        create_notification_row(
            conn,
            event_type="run_cancelled",
            severity="warning",
            title="Run cancelled",
            message=f"Run {run_id} was cancelled.",
            run_id=run_id,
            job_id=job_id,
        )
        return


def read_remote_log_file(path: str | None, *, tail_lines: int = 300) -> dict[str, Any]:
    if not path:
        return {
            "path": None,
            "exists": False,
            "content": "",
            "error": "No log path stored",
        }

    safe_path = shlex.quote(path)
    safe_tail_lines = max(1, min(tail_lines, 2000))

    command = (
        f"if [ -f {safe_path} ]; then "
        f"tail -n {safe_tail_lines} {safe_path}; "
        f"else "
        f"echo '__TAP_LOG_FILE_MISSING__'; "
        f"fi"
    )

    code, stdout, stderr = run_ssh_command(command)

    if code != 0:
        return {
            "path": path,
            "exists": False,
            "content": "",
            "error": stderr or f"Failed to read log file {path}",
        }

    if "__TAP_LOG_FILE_MISSING__" in stdout:
        return {
            "path": path,
            "exists": False,
            "content": "",
            "error": "Log file does not exist yet",
        }

    return {
        "path": path,
        "exists": True,
        "content": stdout,
        "error": None,
    }


@router.post("/runs", response_model=RunResponse)
def create_run(payload: RunCreate) -> RunResponse:
    run_id = str(uuid.uuid4())
    created_at = utc_now_iso()

    try:
        git_state = get_remote_git_state()
        git_commit = resolve_git_commit_from_payload(
            payload.git_commit,
            git_state["commit"],
        )
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

    config_file_snapshot = read_remote_config_file(payload.config_path)

    config_snapshot = build_config_snapshot(
        payload=payload,
        git_commit=git_commit,
        run_id=run_id,
        created_at=created_at,
        status=status,
        slurm_job_id=slurm_job_id,
        config_file_snapshot=config_file_snapshot,
    )

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
                error_message,
                config_snapshot_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json_dumps(config_snapshot),
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
        config_snapshot=config_snapshot,
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


@router.get("/runs/{run_id}/logs")
def get_run_logs(run_id: str, tail_lines: int = 300) -> dict[str, Any]:
    run = ensure_run_exists(run_id)
    slurm_job_id = run.get("slurm_job_id")

    if not slurm_job_id:
        return {
            "run_id": run_id,
            "job_id": None,
            "stdout": {
                "path": None,
                "exists": False,
                "content": "",
                "error": "No Slurm job ID associated with this run",
            },
            "stderr": {
                "path": None,
                "exists": False,
                "content": "",
                "error": "No Slurm job ID associated with this run",
            },
        }

    with get_db() as conn:
        job = conn.execute(
            """
            SELECT *
            FROM jobs
            WHERE job_id = ?
            """,
            (slurm_job_id,),
        ).fetchone()

    if job is None:
        return {
            "run_id": run_id,
            "job_id": slurm_job_id,
            "stdout": {
                "path": None,
                "exists": False,
                "content": "",
                "error": "No job row found for this run",
            },
            "stderr": {
                "path": None,
                "exists": False,
                "content": "",
                "error": "No job row found for this run",
            },
        }

    job_dict = dict(job)

    return {
        "run_id": run_id,
        "job_id": slurm_job_id,
        "stdout": read_remote_log_file(
            job_dict.get("log_path"),
            tail_lines=tail_lines,
        ),
        "stderr": read_remote_log_file(
            job_dict.get("error_log_path"),
            tail_lines=tail_lines,
        ),
    }


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

    return [parse_run_row(dict(row)) for row in rows]


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    return parse_run_row(ensure_run_exists(run_id))


@router.post("/runs/refresh-active")
def refresh_active_runs_endpoint() -> dict[str, Any]:
    return refresh_active_runs()

@router.post("/runs/{run_id}/refresh")
def refresh_run(run_id: str) -> dict[str, Any]:
    try:
        return refresh_run_by_id(run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

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
        
        create_run_status_notification(
            conn,
            run_id=run_id,
            old_status=run_row["status"],
            new_status="cancelled",
            job_id=slurm_job_id,
        )

    return {"run_id": run_id, "status": "cancelled"}
