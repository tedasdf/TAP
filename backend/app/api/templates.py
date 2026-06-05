from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.models.event import RunEvent
from app.models.run import Run
from app.models.template import Template, TemplateRun
from app.repositories.base import BaseRepository
from app.repositories.run_repo import RunRepository
from app.repositories.template_repo import TemplateRepository
from app.schemas import CreateTemplateRequest, LaunchTemplateRequest, TemplateResponse
from app.services.launcher import get_remote_git_state, read_remote_config_file
from app.services.template_engine import expand_template, validate_template_params


router = APIRouter(tags=["templates"])


@router.get("/templates")
def list_templates() -> list[TemplateResponse]:
    with get_db() as conn:
        templates = TemplateRepository(conn).list_all()
    return [TemplateResponse.from_domain(t) for t in templates]


@router.get("/templates/{template_id}")
def get_template(template_id: str) -> TemplateResponse:
    with get_db() as conn:
        template = TemplateRepository(conn).find(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return TemplateResponse.from_domain(template)


@router.post("/templates", response_model=TemplateResponse)
def create_template(payload: CreateTemplateRequest) -> TemplateResponse:
    with get_db() as conn:
        repo = TemplateRepository(conn)
        template = Template(
            template_id=BaseRepository._new_id(),
            name=payload.name,
            description=payload.description,
            params=payload.params,
            created_at=BaseRepository._utc_now(),
        )
        saved = repo.create(template)
    return TemplateResponse.from_domain(saved)


@router.post("/templates/{template_id}/launch")
def launch_template(template_id: str, payload: LaunchTemplateRequest) -> dict:
    """Expand a template into deferred runs (status=created).

    The orchestrator's TemplatePromoter picks them up and submits to SLURM
    as concurrency slots open.
    """
    with get_db() as conn:
        template = TemplateRepository(conn).find(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    errors = validate_template_params(template.params)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    combos = expand_template(template.params)

    # Resolve git state and config file once — not once per combo.
    git_state = get_remote_git_state()
    git_commit = payload.git_commit or git_state["commit"]
    config_file_snapshot = read_remote_config_file(payload.config_path)

    run_ids: list[str] = []

    with get_db() as conn:
        runs = RunRepository(conn)
        templates = TemplateRepository(conn)

        for combo in combos:
            run_id = BaseRepository._new_id()
            created_at = BaseRepository._utc_now()
            run_name = f"{template.name}-{combo['combo_index']}"
            overrides: dict = combo["params"]

            config_snapshot = {
                "run_id": run_id,
                "name": run_name,
                "git_commit": git_commit,
                "config_path": payload.config_path,
                "config_overrides": overrides,
                "config_file": config_file_snapshot,
                "template_id": template_id,
                "combo_index": combo["combo_index"],
                "derive_trace": combo.get("derive_trace", {}),
                "created_at": created_at,
            }

            run = Run(
                run_id=run_id,
                name=run_name,
                status="created",
                git_commit=git_commit,
                config_path=payload.config_path,
                created_at=created_at,
                config_overrides=overrides,
                config_snapshot=config_snapshot,
                template_id=template_id,
                launch_mode="slurm",
            )
            runs.create(run)

            runs.events.create(RunEvent(
                event_id=BaseRepository._new_id(),
                run_id=run_id,
                event_type="RUN_CREATED",
                message=f"Deferred run created from template (combo {combo['combo_index']})",
                new_status="created",
                created_at=BaseRepository._utc_now(),
                payload={
                    "template_id": template_id,
                    "combo_index": combo["combo_index"],
                    "params": overrides,
                },
            ))

            templates.add_run(TemplateRun(
                id=BaseRepository._new_id(),
                template_id=template_id,
                run_id=run_id,
                combo_index=combo["combo_index"],
            ))

            run_ids.append(run_id)

    return {
        "template_id": template_id,
        "runs_created": len(run_ids),
        "run_ids": run_ids,
    }
