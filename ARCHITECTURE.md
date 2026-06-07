# TAP Architecture

TAP (Training Administration Platform) is a web app that manages ML training runs on an M3 HPC cluster from a local Windows machine.

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│  Local machine (Windows)                                │
│                                                         │
│  ┌──────────────┐      ┌──────────────────────────────┐ │
│  │  Next.js 16  │◄────►│  FastAPI backend             │ │
│  │  (frontend)  │ HTTP │  + SQLite (tap.db)           │ │
│  └──────────────┘      └──────────┬───────────────────┘ │
│                                   │ SSH                  │
└───────────────────────────────────┼─────────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  M3 HPC cluster                │
                    │  slm_repo/                     │
                    │  SLURM scheduler               │
                    │  W&B (cloud)                   │
                    └────────────────────────────────┘
```

---

## Backend

### Entry point — `app/main.py`

FastAPI application. On startup:
1. `init_db()` — executes `db/schema.sql`, runs column migrations
2. `orchestrator.start()` — asyncio loop for template promotion
3. `run_manager.start()` — spawns per-run watcher threads for all active runs

### Database — `db/schema.sql`

Single SQLite file at `TAP_DB_PATH` (default `data/tap.db`). `schema.sql` is the canonical source; `_run_migrations()` in `db.py` upgrades existing databases at startup.

| Table | Purpose |
|---|---|
| `runs` | Every training run — 21 columns including `seed`, `data_ref`, `wandb_run_id`, `launch_mode`, checkpoint paths |
| `jobs` | SLURM job state (queue/execution/node/times/exit code) |
| `run_events` | Immutable audit log per run (RUN_CREATED, STATUS_CHANGED, SLURM_JOB_SUBMITTED, …) |
| `templates` | Sweep definitions (params stored as JSON blob) |
| `template_runs` | Many-to-many: which runs belong to which template combo |
| `metrics` | Latest snapshot per run — one row, overwritten each sync |
| `metric_points` | Full per-step history — `metrics_json` blob, unique on `(run_id, step, source)` |
| `metric_sync_status` | W&B sync state per run |
| `notifications` | In-app alerts with severity and read state |
| `push_subscriptions` | Web Push VAPID endpoints |

### API routers

| Router | Key endpoints |
|---|---|
| `runs` | POST create/launch, GET list/detail, POST refresh/cancel/checkpoint |
| `jobs` | GET list, PATCH state |
| `metrics` | GET snapshot + history, PUT upsert, POST add point |
| `notifications` | GET, PATCH read, DELETE |
| `templates` | POST create, GET list/detail/preview/runs, POST launch |
| `configs` | POST generate/save YAML |
| `push` | POST subscribe/unsubscribe |
| `system` | `/health`, `/system/status` — health check + dependency status |
| `registry` | `/registry/slm` — proxies `registry.yaml` from M3 |

### Run lifecycle

**`RunService`** owns creation and refresh:

```
create(RunCreate payload)
  1. SSH → get HEAD commit from M3
  2. Generate wandb_run_id = "tap-<uuid8>" (stored before job starts)
  3. If launch_now:
       slurm → sbatch → parse job ID → status=queued
       direct → nohup torchrun → parse PID  → status=running
       failure → status=failed
  4. SSH → snapshot YAML config file (best-effort, never blocks run creation)
  5. INSERT run + RUN_CREATED event [+ SLURM_JOB_SUBMITTED event + jobs row]

refresh(run_id)
  1. [slurm] squeue → sacct fallback → derive_run_status → update jobs row
  2. [wandb]  get_run_snapshot + scan_history → upsert metrics + metric_points
              → metric alerts (NaN loss, new best val loss)
  3. If status changed → STATUS_CHANGED event + notification + Web Push
```

### Background workers

Two independent systems run concurrently:

**`RunManager`** (`services/run_manager.py`) — per-run watcher threads:
- One `RunWatcher` daemon thread per active run
- Status-adaptive poll intervals: `queued=120s`, `running=30s`, `created/unknown=60s`
- Stops automatically when run reaches a terminal status (`completed`, `failed`, `cancelled`)
- Resumes on backend restart for all active runs

**`Orchestrator`** (`services/orchestrator.py`) — asyncio loop (requires `TAP_BACKGROUND_REFRESH_ENABLED=1`, default 60s):
- **Phase 1 — TemplatePromoter**: finds `created` template runs, submits to SLURM up to `TAP_MAX_CONCURRENT_JOBS` per template
- **Phase 2 — RunRefresher**: polls SLURM + syncs W&B for every active run
- **Stuck-queue check**: fires warning notification + push after 5 hours queued

### Launcher — `services/launcher.py`

All cluster interaction is SSH via `subprocess.run(["ssh", TAP_M3_HOST, ...])`.

**SLURM path:**
```bash
cd <TAP_M3_REPO_PATH>
sbatch --job-name=<name> \
  --export=CONFIG_PATH=...,CONFIG_OVERRIDES_JSON=...,
           TAP_GIT_COMMIT=...,TAP_RUN_NAME=...,TAP_RUN_ID=...,
           TAP_API_URL=...,WANDB_RUN_ID=...,WANDB_PROJECT=...,WANDB_ENTITY=... \
  <TAP_M3_SUBMIT_SCRIPT>
```
Named `--export=VAR=val,...` (not `--export=ALL`) so SLURM initialises the job environment normally — cluster vars like `$SCRATCH` are set by SLURM, not overridden by the TAP SSH session.

**Direct path:**
```bash
nohup torchrun --nproc_per_node=1 -m src.slm.main \
  --config <config_path> > logs/direct/<name>.out 2>&1 &
echo $!   # returns PID
```

**Config SCP**: before sbatch, `ensure_config_on_cluster()` checks if the config was generated locally. If so, `copy_config_to_cluster()` SCPs it to `TAP_M3_REPO_PATH/TAP_M3_CONFIG_DIR/`.

### Config generation — `services/config_gen.py` + `services/configs.py`

Two separate builders:

| Builder | Used by | Input | Output |
|---|---|---|---|
| `config_gen.py` `generate_slm_config(SLMConfigGenerateRequest)` | `POST /configs/generate/slm`, template launch | Typed flat fields | Full YAML dict |
| `configs.py` `generate_slm_config(name, resolved_params)` | Template overlay path | `_BASE_CONFIG` + dotted-key overrides | YAML string |

`SLMConfigGenerateRequest` field names map 1-to-1 with slm_repo's `RunConfig` sections. `_PARAM_KEY_MAP` in `templates.py` maps frontend template param keys (e.g. `model.attention.num_heads`) to these field names.

### SLURM state mapping — `services/jobs.py`

Two-stage polling: `squeue` (live jobs) → `sacct` fallback (completed jobs). Exit code `0`/`0:0`/empty = success. `derive_run_status` maps raw SLURM states to TAP statuses; `reconcile_run_status` merges SLURM and W&B signals: `cancelled > failed > completed > running > queued`.

### W&B integration — `services/wandb_client.py`

- `get_run_snapshot()` reads `run.summary`, maps wandb states (`finished`→`completed`, `crashed`→`failed`), aliases metric keys (`train_loss`/`train/loss`/`loss`→`training_loss`)
- `get_run_history_since(min_step)` calls `run.scan_history()`, drops NaN, stores each step as a `metric_points` row
- `wandb_run_id` is pre-generated as `tap-<uuid8>` at run creation and exported to the job as `WANDB_RUN_ID`. Training script calls `wandb.init(id=os.environ["WANDB_RUN_ID"], resume="allow")`.

---

## Frontend

Next.js 16 (Turbopack), TypeScript, Tailwind CSS. App router.

### Pages

| Route | Purpose |
|---|---|
| `/` | Dashboard — active runs, recent activity |
| `/runs` | Run list with live status polling |
| `/runs/new` | Manual run creation form |
| `/runs/[runId]` | Run detail: status card, config tab, metrics charts, events timeline, logs |
| `/compare` | Side-by-side run comparison |
| `/templates` | Template list — preview, copy, launch |
| `/templates/new` | Template builder — vary/fixed/derive params, matrix preview |
| `/templates/[templateId]` | Template detail: config, runs, matrix tabs |
| `/configs/new` | Config YAML generator |
| `/config-builder` | Visual config builder |
| `/system` | Backend health + orchestrator status |

### Template builder (`/templates/new`)

A param registry (`PARAMS`) defines 22 sweep axes across four sections (Data, Tokenizer, Model Architecture, Trainer/Optimizer/Scheduler). Each param has a **Fixed / Vary / Derive** role:

- **Fixed**: one value, present in every combo
- **Vary**: multiple values — Cartesian product across all vary params
- **Derive**: computed from another param via a safe AST expression (e.g. `model.model_dim / 64`)

Matrix preview expands the full N-combo grid before save. "Save + Launch" creates the template then immediately calls `POST /templates/{id}/launch`, which generates a YAML config file per combo, SCPs each to M3, and creates deferred `Run` records. The orchestrator then promotes them to SLURM as slots open.

### Data flow

```
Component → React Query hook → api/client.ts → FastAPI backend
```

Active runs and notifications poll every 15–30s via React Query `refetchInterval`. No WebSocket.

---

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `TAP_DB_PATH` | `data/tap.db` | SQLite database path |
| `TAP_M3_HOST` | `m3` | SSH hostname for the cluster |
| `TAP_M3_REPO_PATH` | `~/slm_repo` | Absolute path to slm_repo on cluster |
| `TAP_M3_SUBMIT_SCRIPT` | `scripts/slurm/test.slurm` | sbatch script (relative to repo root) |
| `TAP_M3_CONDA_ENV` | — | Conda env for direct (non-SLURM) runs |
| `TAP_M3_CONFIG_DIR` | `configs/generated` | Where generated configs land on cluster |
| `TAP_LOCAL_CONFIG_DIR` | `data/configs/generated` | Local mirror for generated configs |
| `TAP_API_URL` | `http://localhost:8000` | Callback URL for training job metric POSTs |
| `TAP_MAX_CONCURRENT_JOBS` | `10` | Concurrency cap per template in promoter |
| `TAP_BACKGROUND_REFRESH_ENABLED` | unset | Set to `1` to enable orchestrator loop |
| `TAP_BACKGROUND_REFRESH_INTERVAL_SECONDS` | `60` | Orchestrator tick interval |
| `WANDB_ENTITY` | — | W&B entity (username or team) |
| `WANDB_PROJECT` | — | W&B project name |
| `WANDB_API_KEY` | — | W&B API key |
| `VAPID_PUBLIC_KEY` | — | Web Push public key |
| `VAPID_PRIVATE_KEY` | — | Web Push private key |
| `VAPID_CLAIMS_EMAIL` | `tap@localhost` | Web Push contact email |

---

## Key design decisions

**SQLite over Postgres** — single-user tool, no concurrency requirements beyond SQLite's own locking. Row-factory gives dict-like access throughout without an ORM.

**SSH over REST** — M3 exposes no HTTP API. All cluster interaction is `subprocess.run(["ssh", ...])`. Every SSH call blocks a thread; the orchestrator uses `asyncio.to_thread` to avoid blocking the event loop.

**Pre-generated W&B run IDs** — `wandb_run_id = "tap-<uuid8>"` is stored in the DB before the job starts and exported as `WANDB_RUN_ID`. W&B sync works immediately on first refresh; no log-scraping needed.

**Named `--export` not `--export=ALL`** — exporting the full TAP SSH environment clobbered cluster-set vars like `$SCRATCH`. Named variable export only; SLURM initialises the job environment from system profiles as normal.

**Dual background systems** — `RunManager` (per-run threads, status-adaptive intervals) handles active run polling independently. `Orchestrator` (asyncio loop) handles template promotion. Both are opt-in or self-terminating to avoid hammering the cluster during development.
