from __future__ import annotations

import ast
import operator
from itertools import product as iterproduct
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_db
from app.models.template import Template, TemplateRun
from app.repositories.base import BaseRepository
from app.repositories.run_repo import RunRepository
from app.repositories.template_repo import TemplateRepository
from app.schemas import CreateTemplateRequest, RunCreate, TemplateResponse
from app.services.config_gen import (
    SLMConfigGenerateRequest,
    copy_config_to_cluster,
    generate_slm_config,
    save_slm_config,
)
from app.services.run_service import RunService


router = APIRouter(tags=["templates"])

# Maps template dotted-key params → SLMConfigGenerateRequest field names
_PARAM_KEY_MAP: dict[str, str] = {
    # Model Architecture
    "model.d_model":          "model_dim",
    "model.n_layers":         "num_layers",
    "model.n_heads":          "num_heads",
    "model.n_kv_heads":       "num_kv_heads",
    "model.attention_type":   "attention_type",
    "model.mlp_type":         "mlp_type",
    "model.mlp_mult":         "mlp_mult",
    "model.normalization":    "norm_type",
    "model.rope_base":        "rope_base",
    "model.vocab_size":       "vocab_size",
    # Optimizer
    "optimizer.type":         "optimizer_type",
    "optimizer.lr":           "learning_rate",
    "optimizer.weight_decay": "weight_decay",
    "optimizer.beta1":        "beta1",
    "optimizer.beta2":        "beta2",
    # Scheduler
    "scheduler.type":         "scheduler_type",
    "scheduler.warmup_steps": "warmup_steps",
    # Trainer
    "trainer.max_steps":      "max_steps",
    "trainer.batch_size":     "batch_size",
    "trainer.grad_accum":     "grad_accum_steps",
    "trainer.precision":      "precision",
    "trainer.seed":           "seed",
    "trainer.grad_clip":      "grad_clip",
    "trainer.eval_every":     "eval_every",
    "trainer.z_loss":         "z_loss_coeff",
    # Data
    "data.seq_len":           "seq_len",
    "data.dataset_name":      "dataset_name",
    # Tokenizer
    "tokenizer.vocab_size":   "vocab_size",
}

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
}


def _eval_expr(node: ast.expr) -> float:
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_expr(node.left), _eval_expr(node.right))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def _resolve_derive(expr: str, from_key: str, from_val: float) -> int | float:
    substituted = expr.replace(from_key, str(from_val))
    try:
        tree = ast.parse(substituted, mode="eval")
        result = _eval_expr(tree.body)
        return int(result) if result == int(result) else result
    except Exception:
        return float("nan")


def _expand_combos(params: dict[str, Any]) -> list[dict[str, Any]]:
    vary_keys = [k for k, v in params.items() if isinstance(v, dict) and v.get("role") == "vary"]

    if vary_keys:
        vary_values = [params[k]["values"] for k in vary_keys]
        combos: list[dict[str, Any]] = [
            {vary_keys[i]: v for i, v in enumerate(row)}
            for row in iterproduct(*vary_values)
        ]
    else:
        combos = [{}]

    for key, spec in params.items():
        if isinstance(spec, dict) and spec.get("role") == "fixed":
            for c in combos:
                c[key] = spec["value"]

    for key, spec in params.items():
        if isinstance(spec, dict) and spec.get("role") == "derive":
            from_key = spec.get("from", "")
            expr = spec.get("expr", "")
            for c in combos:
                from_val = c.get(from_key)
                if isinstance(from_val, (int, float)):
                    c[key] = _resolve_derive(expr, from_key, float(from_val))

    return combos


def _combo_to_config_request(combo: dict[str, Any], experiment_name: str) -> SLMConfigGenerateRequest:
    kwargs: dict[str, Any] = {"experiment_name": experiment_name}
    for dotted_key, field_name in _PARAM_KEY_MAP.items():
        if dotted_key in combo:
            kwargs[field_name] = combo[dotted_key]
    return SLMConfigGenerateRequest(**kwargs)


# ─── Request / Response models ────────────────────────────────────────────────

class TemplateLaunchPayload(BaseModel):
    dry_run: bool = False
    git_commit: str | None = None
    launch_mode: str = "slurm"


class TemplateLaunchResponse(BaseModel):
    template_id: str
    total: int
    launched: int
    failed: int
    errors: list[str] = []


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates() -> list[TemplateResponse]:
    with get_db() as conn:
        templates = TemplateRepository(conn).list_all()
    return [TemplateResponse.from_domain(t) for t in templates]


@router.get("/templates/{template_id}/preview")
def preview_template(template_id: str) -> dict:
    with get_db() as conn:
        template = TemplateRepository(conn).find(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    combos = _expand_combos(template.params)
    return {
        "template_id": template_id,
        "total_runs": len(combos),
        "combos": [
            {"combo_index": i, "params": combo, "derive_trace": {}}
            for i, combo in enumerate(combos)
        ],
    }


@router.get("/templates/{template_id}/runs")
def get_template_runs(template_id: str) -> dict:
    with get_db() as conn:
        repo = TemplateRepository(conn)
        template = repo.find(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        template_runs = repo.list_runs(template_id)
        run_repo = RunRepository(conn)
        runs_data = []
        for tr in template_runs:
            run = run_repo.find(tr.run_id)
            if run:
                runs_data.append({
                    "run_id": run.run_id,
                    "name": run.name,
                    "status": run.status,
                    "combo_index": tr.combo_index,
                    "slurm_job_id": run.slurm_job_id,
                    "created_at": run.created_at,
                    "params": {},
                    "metrics": {
                        "training_loss": run.training_loss,
                        "validation_loss": run.validation_loss,
                        "learning_rate": run.learning_rate,
                        "current_step": run.current_step,
                        "latest_metric_timestamp": run.latest_metric_timestamp,
                    },
                })

    return {
        "template_id": template_id,
        "template_name": template.name,
        "runs": runs_data,
    }


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


@router.post("/templates/{template_id}/launch", response_model=TemplateLaunchResponse)
def launch_template(template_id: str, payload: TemplateLaunchPayload) -> TemplateLaunchResponse:
    from app.config import settings


    with get_db() as conn:
        template = TemplateRepository(conn).find(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    combos = _expand_combos(template.params)

    if payload.dry_run:
        return TemplateLaunchResponse(
            template_id=template_id,
            total=len(combos),
            launched=0,
            failed=0,
        )

    launched = 0
    errors: list[str] = []

    for i, combo in enumerate(combos):
        exp_name = f"{template.name}-{i}"
        try:
            config_req = _combo_to_config_request(combo, exp_name)
            config = generate_slm_config(config_req)
            local_path, relative_path, _ = save_slm_config(config, None)

            copy_config_to_cluster(
                local_path,
                cluster_host=settings.TAP_M3_HOST,
                remote_repo_path=settings.TAP_M3_REPO_PATH,
                relative_config_path=relative_path,
            )

            run_payload = RunCreate(
                name=exp_name,
                git_commit=payload.git_commit,
                config_path=relative_path,
                config_overrides={},
                launch_now=True,
                launch_mode=payload.launch_mode,
                template_id=template_id,
            )

            with get_db() as conn:
                run = RunService(conn).create(run_payload)
                TemplateRepository(conn).add_run(TemplateRun(
                    id=BaseRepository._new_id(),
                    template_id=template_id,
                    run_id=run.run_id,
                    combo_index=i,
                ))

            launched += 1
        except Exception as exc:
            errors.append(f"Combo {i} ({exp_name}): {exc}")

    return TemplateLaunchResponse(
        template_id=template_id,
        total=len(combos),
        launched=launched,
        failed=len(combos) - launched,
        errors=errors,
    )
