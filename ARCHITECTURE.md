# TAP Architecture

TAP (Training Administration Platform) is a mobile-first web app for submitting, monitoring, and comparing ML training runs on a remote HPC cluster (M3 / Slurm).

---

## 1. System Overview

```
┌──────────────────────────────────────────────────────────┐
│  Browser / Mobile                                        │
│  Next.js frontend  (port 3000)                          │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP / JSON
┌────────────────────────▼─────────────────────────────────┐
│  FastAPI backend  (port 8000)                            │
│  Python 3.10+  ·  SQLite WAL  ·  background threads     │
└───────┬──────────────────────────────────┬───────────────┘
        │ SQLite (data/tap.db)             │ SSH
┌───────▼───────┐                ┌─────────▼───────────────┐
│  tap.db       │                │  M3 (GPU cluster)       │
│  (local)      │                │  Slurm  ·  slm_repo     │
└───────────────┘                └─────────────────────────┘
```

Key constraints:
- The backend never holds a long-running DB connection; every request opens and closes its own SQLite connection via `get_db()`.
- All SSH calls to M3 are synchronous — one SSH subprocess per request.
- Training configs are generated locally as YAML files and their paths are passed to Slurm via `CONFIG_PATH` env var.

---

## 2. Repository Layout

```
TAP/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (one file per resource)
│   │   ├── services/     # Business logic, no HTTP concerns
│   │   ├── db.py         # Connection factory + init_db()
│   │   ├── schemas.py    # Pydantic request/response models
│   │   ├── config.py     # Settings from env vars
│   │   └── main.py       # App factory, startup hooks
│   ├── db/
│   │   ├── schema.sql            # Canonical table definitions
│   │   └── migrations/           # Sequential ALTER TABLE scripts
│   ├── generated_configs/        # YAML configs written at launch time
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/          # Next.js App Router pages
│       ├── components/   # Shared UI components
│       └── lib/
│           ├── api/      # fetch wrappers per resource
│           ├── hooks/    # TanStack Query hooks
│           └── types/    # API shapes (api.ts) + view shapes (view.ts)
└── data/
    └── tap.db            # SQLite database (WAL mode)
```

---

## 3. API Routers

| Router file       | Prefix          | Endpoints |
|-------------------|-----------------|-----------|
| `system.py`       | —               | `GET /health`, `GET /system/status` |
| `runs.py`         | `/runs`         | `POST /runs`, `GET /runs`, `GET /runs/{id}`, `POST /runs/{id}/refresh`, `POST /runs/{id}/cancel`, `DELETE /runs/{id}` |
| `jobs.py`         | `/jobs`         | `GET /jobs`, `GET /jobs/{id}`, `PATCH /jobs/{id}`, `GET /jobs/{id}/logs` |
| `metrics.py`      | —               | `PUT /runs/{id}/metrics`, `GET /runs/{id}/metrics`, `POST /runs/{id}/sync-wandb` |
| `notifications.py`| `/notifications`| `GET /notifications`, `POST /notifications`, `POST /notifications/test`, `PATCH /notifications/{id}/read` |
| `configs.py`      | —               | `GET /registry/slm`, `POST /configs/generate/slm`, `POST /configs/save/slm` |
| `templates.py`    | `/templates`    | `POST /templates`, `GET /templates`, `GET /templates/{id}`, `GET /templates/{id}/preview`, `GET /templates/{id}/runs`, `POST /templates/{id}/launch` |

---

## 4. Services

| File                  | Responsibility |
|-----------------------|----------------|
| `launcher.py`         | Builds and runs SSH commands to submit Slurm jobs; resolves remote `git HEAD`; parses job IDs from sbatch output |
| `run_events.py`       | Writes rows to `run_events` (status transitions, launch confirmations) |
| `jobs.py`             | Derives canonical run status from Slurm job state; polls `squeue`/`sacct` via SSH |
| `metrics.py`          | W&B client wrapper — syncs run metrics into the `metrics` table |
| `notifications.py`    | Creates notification rows when run events occur |
| `configs.py`          | Generates SLM YAML configs from a flat param dict using `_set_nested`; reads the param registry |
| `template_engine.py`  | **Template expansion:** cartesian product of vary params, fixed param injection, safe AST-based derive expression evaluator, param validation (see §8) |
| `template_queue.py`   | **Background worker:** daemon thread polling every 60 s; promotes deferred template runs to Slurm as active job count drops below `TAP_MAX_CONCURRENT_JOBS` |
| `ssh_client.py`       | Low-level SSH wrapper |
| `wandb_client.py`     | W&B API client |

---

## 5. Database Tables

All tables live in `data/tap.db` (SQLite, WAL mode). Foreign keys are enforced (`PRAGMA foreign_keys = ON`).

### `runs`

| Column              | Type    | Notes |
|---------------------|---------|-------|
| `run_id`            | TEXT PK | UUID4 |
| `name`              | TEXT    | Human-readable label |
| `status`            | TEXT    | `created` · `queued` · `running` · `completed` · `failed` · `cancelled` · `unknown` |
| `git_commit`        | TEXT    | Exact commit submitted to Slurm |
| `config_path`       | TEXT    | Path to YAML config (local or remote) |
| `config_overrides`  | TEXT    | JSON dict of override key/values |
| `config_snapshot_json` | TEXT | Full config captured at launch time |
| `wandb_config_ref`  | TEXT    | W&B config reference |
| `slurm_job_id`      | TEXT    | Slurm job ID (set on successful sbatch) |
| `wandb_run_id`      | TEXT    | W&B run ID |
| `created_at`        | TEXT    | ISO 8601 UTC |
| `last_checked_at`   | TEXT    | Last Slurm poll time |
| `error_message`     | TEXT    | Most recent failure reason |
| `template_id`       | TEXT FK | References `templates.template_id` — set for template-spawned runs |

### `jobs`

Slurm job details. One row per Slurm job ID, FK → `runs`.

Columns: `job_id`, `run_id`, `queue_state`, `execution_state`, `node_info`, `start_time`, `end_time`, `exit_status`, `log_path`, `error_log_path`.

### `run_events`

Immutable audit log of status transitions and significant events. FK → `runs` with `ON DELETE CASCADE`.

Columns: `event_id`, `run_id`, `event_type`, `message`, `old_status`, `new_status`, `created_at`, `payload_json`.

### `metrics`

Latest training snapshot per run (one row per run, upserted on W&B sync). FK → `runs`.

Columns: `run_id`, `current_step`, `current_epoch`, `training_loss`, `validation_loss`, `runtime`, `learning_rate`, `latest_metric_timestamp`.

### `notifications`

User-facing alerts. FK → `runs` and `jobs` with `ON DELETE CASCADE`.

Columns: `notification_id`, `event_type`, `message`, `run_id`, `job_id`, `timestamp`, `read_state`.

### `templates`

Saved experiment templates.

| Column        | Type    | Notes |
|---------------|---------|-------|
| `template_id` | TEXT PK | UUID4 |
| `name`        | TEXT    | Human label |
| `description` | TEXT    | Optional |
| `params_json` | TEXT    | JSON — see §8 |
| `created_at`  | TEXT    | ISO 8601 UTC |

### `template_runs`

Join table linking each spawned run to its template and combo position.

| Column        | Type       | Notes |
|---------------|------------|-------|
| `id`          | INTEGER PK | Auto-increment |
| `template_id` | TEXT FK    | References `templates` |
| `run_id`      | TEXT FK    | References `runs` |
| `combo_index` | INTEGER    | 0-based position in the cartesian product |

---

## 6. DB Migrations

Migrations live in `backend/db/migrations/` and are applied manually with `sqlite3 data/tap.db < <file>`. The canonical schema is `backend/db/schema.sql`.

| File | Description |
|------|-------------|
| `001_m1_run_tracking_schema.sql` | Initial run + job + run_events schema |
| `002_m15_config_snapshot.sql`   | Add `config_snapshot_json` to `runs` |
| `003_add_templates.sql`          | Add `templates` and `template_runs` tables |
| `004_add_template_id_to_runs.sql`| Add `template_id` FK column to `runs` |

---

## 7. Configuration (env vars)

| Variable                    | Default             | Description |
|-----------------------------|---------------------|-------------|
| `TAP_DB_PATH`               | `data/tap.db`       | SQLite file path (relative to project root or absolute) |
| `TAP_M3_HOST`               | `m3`                | SSH host for the GPU cluster |
| `TAP_M3_REPO_PATH`          | (hardcoded fallback) | Absolute path to `slm_repo` on M3 |
| `TAP_M3_SUBMIT_SCRIPT`      | `slurm/train.sh`    | Path to sbatch script (relative to repo root) |
| `TAP_M3_LOG_DIR`            | `logs/slurm`        | Where Slurm output files are written on M3 |
| `TAP_MAX_CONCURRENT_JOBS`   | `10`                | Max active Slurm jobs from any one template launch |
| `WANDB_ENTITY`              | —                   | W&B entity |
| `WANDB_PROJECT`             | —                   | W&B project |
| `WANDB_API_KEY`             | —                   | W&B API key |
| `DISCORD_WEBHOOK_URL`       | —                   | Discord webhook for notifications |

---

## 8. Experiment Templates

Templates let users define a parameter sweep once and launch all combinations as individual Slurm jobs.

### `params_json` structure

Each key is a config parameter (dot-notation maps to YAML nesting, e.g. `model.attention_type`). Each value is one of three role objects:

```json
{
  "model.attention_type": { "role": "vary",   "values": ["baseline", "gqa"] },
  "model.normalization":  { "role": "fixed",  "value": "rmsnorm" },
  "model.n_heads":        { "role": "derive", "expr": "model.d_model / 64",
                            "from": "model.d_model" }
}
```

- **fixed** — one value, identical across all runs.
- **vary** — N values; generates N axis in the cartesian product.
- **derive** — computed from another param via a safe arithmetic expression (no `eval()`; AST-walked with `SUPPORTED_OPS = {Div, Mult, Add, Sub, FloorDiv}`). Conditional syntax: `param <= threshold → then, else other`.

### Expansion

`template_engine.expand_template(params)` returns one dict per combination:

```
vary["baseline", "gqa"] × vary[256, 512]  →  4 combos
combo 0: attention_type=baseline, d_model=256, n_heads=4.0
combo 1: attention_type=baseline, d_model=512, n_heads=8.0
combo 2: attention_type=gqa,      d_model=256, n_heads=4.0
combo 3: attention_type=gqa,      d_model=512, n_heads=8.0
```

### Launch flow

```
POST /templates/{id}/launch
          │
          ▼
1. Load template, call expand_template()
          │
          ▼
2. Resolve git HEAD from M3 (once, via SSH)
          │
          ▼
3. For each combo (0 … N-1):
   ├── Generate YAML config  →  generated_configs/slm/{id}/{i}.yaml
   ├── INSERT into runs (status = "created", template_id = id)
   ├── INSERT into template_runs (template_id, run_id, combo_index)
   └── if combo_index < TAP_MAX_CONCURRENT_JOBS AND not dry_run:
           SSH → sbatch  →  status = "queued"  (or "failed")
       else:
           leave as "created"  (deferred)
          │
          ▼
4. Return LaunchResponse {total, launched, failed, runs[]}
          │
          ▼  (background, every 60 s)
5. template_queue worker:
   ├── Count active (queued/running) runs per template
   ├── For each template below cap: promote next "created" runs
   └── SSH → sbatch → UPDATE runs SET status = "queued"
```

### Validation rules (enforced at `POST /templates`)

- At least one `vary` param (otherwise it's just a single fixed config).
- All `derive` `from` references must exist in the same params dict.
- No circular derive dependencies.

---

## 9. Frontend Structure

The frontend is a Next.js App Router app (`"use client"` on all pages — no server components with async data fetching).

| Route                    | Description |
|--------------------------|-------------|
| `/`                      | Dashboard: system health, run counts, active runs, recent alerts |
| `/runs`                  | Searchable, filterable run list |
| `/runs/new`              | Create run form |
| `/runs/[runId]`          | Run detail: Overview · Metrics · Logs · Job · Config tabs |
| `/alerts`                | All notifications |
| `/system`                | System health cards |
| `/templates`             | Template list with Preview sheet and Launch button |
| `/templates/new`         | Template builder: registry-based param editor + live matrix preview |
| `/templates/[templateId]`| Template detail: Config · Runs · Matrix tabs |

Data fetching uses TanStack Query. Polling intervals: runs 15 s, templates 30 s, template runs 15 s.
