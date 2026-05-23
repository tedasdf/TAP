from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.models.template import Template
from app.repositories.template_repo import TemplateRepository
from app.schemas import CreateTemplateRequest, TemplateResponse


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
            template_id=TemplateRepository._new_id(),
            name=payload.name,
            description=payload.description,
            params=payload.params,
            created_at=TemplateRepository._utc_now(),
        )
        saved = repo.create(template)
    return TemplateResponse.from_domain(saved)
