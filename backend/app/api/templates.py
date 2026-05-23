import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.schemas import (
    CreateTemplateRequest,
    LaunchResponse,
    LaunchTemplateRequest,
    ParamDerive,
    ParamVary,
    PreviewResponse,
    RunCombo,
    TemplateListResponse,
    TemplateResponse,
    TemplateRunItem,
    TemplateRunsResponse,
    TemplateSummaryResponse,
)
from app.config import settings
from app.services.configs import generate_slm_config
from app.services.launcher import (
    build_remote_error_log_path,
    build_remote_log_path,
    launch_training_run,
    resolve_remote_training_git_commit,
)
from app.services.run_events import create_run_event
from app.services.template_engine import expand_template

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_GENERATED_CONFIGS_DIR = _BACKEND_ROOT / "generated_configs"

router = APIRouter(tags=["templates"])


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(payload: CreateTemplateRequest) -> TemplateResponse:
    if not payload.name:
        raise HTTPException(status_code=422, detail="name must be non-empty")

    vary_params = [k for k, v in payload.params.items() if isinstance(v, ParamVary)]
    if not vary_params:
        raise HTTPException(
            status_code=422,
            detail="At least one param must have role 'vary'",
        )

    param_keys = set(payload.params.keys())
    for key, param in payload.params.items():
        if isinstance(param, ParamDerive) and param.from_param not in param_keys:
            raise HTTPException(
                status_code=422,
                detail=f"Derive param '{key}' references unknown param '{param.from_param}'",
            )

    template_id = str(uuid.uuid4())
    created_at = utc_now_iso()

    params_for_storage = {
        k: v.model_dump(by_alias=True) for k, v in payload.params.items()
    }
    params_json = json.dumps(params_for_storage, ensure_ascii=False)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO templates (template_id, name, description, params_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (template_id, payload.name, payload.description, params_json, created_at),
        )

    return TemplateResponse(
        template_id=template_id,
        name=payload.name,
        description=payload.description,
        params=params_for_storage,
        created_at=created_at,
        run_count=0,
    )


def _row_to_template_response(row: dict, run_count: int) -> TemplateResponse:
    return TemplateResponse(
        template_id=row["template_id"],
        name=row["name"],
        description=row["description"],
        params=json.loads(row["params_json"]),
        created_at=row["created_at"],
        run_count=run_count,
    )


@router.get("/templates", response_model=TemplateListResponse)
def list_templates() -> TemplateListResponse:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT t.template_id, t.name, t.description, t.params_json, t.created_at,
                   COUNT(tr.id) AS run_count
            FROM templates t
            LEFT JOIN template_runs tr ON tr.template_id = t.template_id
            GROUP BY t.template_id
            ORDER BY datetime(t.created_at) DESC
            """
        ).fetchall()

    return TemplateListResponse(
        templates=[_row_to_template_response(dict(r), r["run_count"]) for r in rows]
    )


@router.get("/templates/{template_id}/preview", response_model=PreviewResponse)
def preview_template(template_id: str) -> PreviewResponse:
    with get_db() as conn:
        row = conn.execute(
            "SELECT template_id, params_json FROM templates WHERE template_id = ?",
            (template_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    params = json.loads(row["params_json"])

    try:
        expanded = expand_template(params)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    combos = [
        RunCombo(
            combo_index=c["combo_index"],
            params=c["params"],
            derive_trace=c["derive_trace"],
        )
        for c in expanded
    ]

    return PreviewResponse(
        template_id=template_id,
        total_runs=len(combos),
        combos=combos,
    )


@router.get("/templates/{template_id}", response_model=TemplateSummaryResponse)
def get_template(template_id: str) -> TemplateSummaryResponse:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT t.template_id, t.name, t.description, t.params_json, t.created_at,
                   COUNT(tr.id) AS run_count
            FROM templates t
            LEFT JOIN template_runs tr ON tr.template_id = t.template_id
            WHERE t.template_id = ?
            GROUP BY t.template_id
            """,
            (template_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        run_rows = conn.execute(
            """
            SELECT tr.combo_index, tr.run_id, r.name, r.status, r.created_at
            FROM template_runs tr
            JOIN runs r ON r.run_id = tr.run_id
            WHERE tr.template_id = ?
            ORDER BY tr.combo_index
            """,
            (template_id,),
        ).fetchall()

    runs = [
        {
            "run_id": r["run_id"],
            "name": r["name"],
            "status": r["status"],
            "combo_index": r["combo_index"],
            "created_at": r["created_at"],
        }
        for r in run_rows
    ]

    return TemplateSummaryResponse(
        template_id=row["template_id"],
        name=row["name"],
        description=row["description"],
        params=json.loads(row["params_json"]),
        created_at=row["created_at"],
        run_count=row["run_count"],
        runs=runs,
    )


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


@router.post("/templates/{template_id}/launch", response_model=LaunchResponse)
def launch_template(template_id: str, payload: LaunchTemplateRequest) -> LaunchResponse:
    with get_db() as conn:
        tpl_row = conn.execute(
            "SELECT template_id, name, params_json FROM templates WHERE template_id = ?",
            (template_id,),
        ).fetchone()

    if tpl_row is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    template_name: str = tpl_row["name"]
    params = json.loads(tpl_row["params_json"])

    try:
        combos = expand_template(params)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Resolve git commit once for all combos
    git_commit = payload.git_commit
    if git_commit is None and not payload.dry_run:
        git_commit, git_error = resolve_remote_training_git_commit()
        if git_commit is None:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resolve git commit from remote: {git_error}",
            )
    if git_commit is None:
        git_commit = "dry-run"

    cap = settings.TAP_MAX_CONCURRENT_JOBS

    config_dir = _GENERATED_CONFIGS_DIR / "slm" / template_id
    config_dir.mkdir(parents=True, exist_ok=True)

    run_results: list[dict] = []
    launched = 0
    failed = 0

    for combo in combos:
        combo_index: int = combo["combo_index"]
        resolved_params: dict[str, Any] = dict(combo["params"])

        if payload.max_steps is not None:
            resolved_params["training.max_steps"] = payload.max_steps

        run_name = f"{template_name}-{combo_index:03d}"
        config_path = config_dir / f"{combo_index}.yaml"
        config_path.write_text(generate_slm_config(name=run_name, resolved_params=resolved_params))
        config_path_str = str(config_path)

        run_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        status = "created"
        slurm_job_id: str | None = None
        error_message: str | None = None
        log_path: str | None = None
        error_log_path: str | None = None

        # Only submit the first `cap` combos immediately; the rest are stored as
        # "created" and promoted by the background template_queue worker.
        within_cap = combo_index < cap
        if not payload.dry_run and within_cap:
            try:
                code, stdout, stderr, slurm_job_id = launch_training_run(
                    run_name=run_name,
                    git_commit=git_commit,
                    config_path=config_path_str,
                )
                combined = "\n".join(p for p in [stdout, stderr] if p)
                if code == 0 and slurm_job_id:
                    status = "queued"
                    log_path = build_remote_log_path(run_name, slurm_job_id)
                    error_log_path = build_remote_error_log_path(run_name, slurm_job_id)
                elif code == 0:
                    status = "created"
                    error_message = "Launch succeeded but no Slurm job ID was parsed"
                else:
                    status = "failed"
                    error_message = combined or f"Launch failed with exit code {code}"
            except Exception as exc:
                status = "failed"
                error_message = str(exc)

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, name, status, git_commit, config_path,
                    config_overrides, config_snapshot_json,
                    wandb_config_ref, slurm_job_id, wandb_run_id,
                    created_at, error_message, template_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, run_name, status, git_commit, config_path_str,
                    None,
                    _json_dumps({"template_id": template_id, "combo_index": combo_index}),
                    None, slurm_job_id, None,
                    created_at, error_message, template_id,
                ),
            )

            create_run_event(
                conn,
                run_id=run_id,
                event_type="RUN_CREATED",
                message=f"Run created from template {template_name} combo {combo_index}",
                old_status=None,
                new_status=status,
                payload={"template_id": template_id, "combo_index": combo_index, "dry_run": payload.dry_run},
            )

            if slurm_job_id:
                create_run_event(
                    conn,
                    run_id=run_id,
                    event_type="SLURM_JOB_SUBMITTED",
                    message=f"Slurm job {slurm_job_id} was submitted",
                    old_status="created",
                    new_status="queued",
                    payload={"slurm_job_id": slurm_job_id, "log_path": log_path, "error_log_path": error_log_path},
                )
                conn.execute(
                    """
                    INSERT INTO jobs (
                        job_id, run_id, queue_state, execution_state,
                        node_info, start_time, end_time, exit_status,
                        log_path, error_log_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (slurm_job_id, run_id, "queued", None, None, None, None, None, log_path, error_log_path),
                )

            conn.execute(
                "INSERT INTO template_runs (template_id, run_id, combo_index) VALUES (?, ?, ?)",
                (template_id, run_id, combo_index),
            )

        if slurm_job_id:
            launched += 1
        elif not payload.dry_run and status == "failed":
            failed += 1

        run_results.append({
            "run_id": run_id,
            "combo_index": combo_index,
            "status": status,
            "slurm_job_id": slurm_job_id,
        })

    return LaunchResponse(
        template_id=template_id,
        total=len(combos),
        launched=launched,
        failed=failed,
        runs=run_results,
    )


@router.get("/templates/{template_id}/runs", response_model=TemplateRunsResponse)
def get_template_runs(template_id: str) -> TemplateRunsResponse:
    with get_db() as conn:
        tpl_row = conn.execute(
            "SELECT template_id, name, params_json FROM templates WHERE template_id = ?",
            (template_id,),
        ).fetchone()

        if tpl_row is None:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        rows = conn.execute(
            """
            SELECT
                tr.combo_index,
                r.run_id, r.name, r.status, r.slurm_job_id, r.created_at,
                m.training_loss, m.validation_loss, m.learning_rate,
                m.current_step, m.latest_metric_timestamp
            FROM template_runs tr
            JOIN runs r ON r.run_id = tr.run_id
            LEFT JOIN metrics m ON m.run_id = r.run_id
            WHERE tr.template_id = ?
            ORDER BY tr.combo_index ASC
            """,
            (template_id,),
        ).fetchall()

    params = json.loads(tpl_row["params_json"])
    try:
        combos = expand_template(params)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    combo_params: dict[int, dict] = {c["combo_index"]: c["params"] for c in combos}

    items: list[TemplateRunItem] = []
    for row in rows:
        has_metrics = row["latest_metric_timestamp"] is not None
        metrics: dict | None = (
            {
                "training_loss": row["training_loss"],
                "validation_loss": row["validation_loss"],
                "learning_rate": row["learning_rate"],
                "current_step": row["current_step"],
                "latest_metric_timestamp": row["latest_metric_timestamp"],
            }
            if has_metrics
            else None
        )
        items.append(
            TemplateRunItem(
                run_id=row["run_id"],
                name=row["name"],
                combo_index=row["combo_index"],
                status=row["status"],
                slurm_job_id=row["slurm_job_id"],
                created_at=row["created_at"],
                params=combo_params.get(row["combo_index"], {}),
                metrics=metrics,
            )
        )

    return TemplateRunsResponse(
        template_id=template_id,
        template_name=tpl_row["name"],
        runs=items,
    )
