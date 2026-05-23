# TAP — Training Automation Platform

TAP is a single-user ML research orchestration tool for fast iteration through neural network experiments. It lets you configure model architectures, submit training jobs to a remote GPU cluster (via SLURM), and monitor metrics in real time — all from a unified web UI.

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                      Browser / UI                       │
│                  Next.js 16 Frontend                    │
│         (Dashboard · Runs · Config Builder · Alerts)    │
└────────────────────────┬────────────────────────────────┘
                         │ REST  (port 8000)
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                       │
│     Runs · Jobs · Metrics · Configs · Notifications     │
│                  Background Worker                      │
└───────────┬─────────────────────────┬───────────────────┘
            │ SSH (sbatch / squeue)   │ W&B API
┌───────────▼──────────┐   ┌──────────▼──────────────────┐
│   GPU Cluster (M3)   │   │   Weights & Biases           │
│   SLURM Scheduler    │   │   Experiment Tracking        │
└──────────────────────┘   └─────────────────────────────┘
            │
┌───────────▼──────────┐
│   SQLite Database    │
│  runs · jobs ·       │
│  metrics · events    │
└──────────────────────┘
```

---

## Subsystems

### 1. Frontend — Next.js Web UI

**Stack:** Next.js 16, React 19, TypeScript, TailwindCSS 4, shadcn/ui, Recharts, TanStack React Query 5

The frontend is a mobile-friendly single-page application with a bottom navigation bar and live-polling data via React Query.

#### Pages

| Route | Purpose |
|-------|---------|
| `/` | Dashboard: system status strip, run summary counts, active runs, recent alerts, quick actions |
| `/runs` | Full run list with search and status filter |
| `/runs/new` | Form to create and launch a new training run |
| `/runs/[runId]` | Run detail: Overview, Metrics, Logs, Config, Job, Events tabs |
| `/config-builder` | Interactive SLM neural network config builder |
| `/alerts` | Notification centre |
| `/system` | Live health check for all backend connections |

#### Key Components

- **`status-strip.tsx`** — 5-indicator health bar (Backend · M3 · SLURM · Database · W&B)
- **`metrics-tab.tsx`** — Recharts `LineChart` for training loss, validation loss, and learning rate over steps
- **`RunEventsTimeline.tsx`** — Chronological event log per run (status transitions, errors)
- **`run-card.tsx`** — Compact run summary with live status badge and latest metric values
- **`config-builder/page.tsx`** — Form-driven YAML config generator; can save and immediately launch a run

#### Data Layer

- **`src/lib/api/`** — Thin REST client (`apiRequest<T>()`) with typed wrappers per resource (runs, metrics, jobs, configs, notifications, system)
- **`src/lib/hooks/`** — React Query hooks with polling intervals: runs every 10–15 s, system status on demand
- **`src/lib/types/api.ts`** — Shared TypeScript types mirroring backend Pydantic schemas

---

### 2. Backend — FastAPI Service

**Stack:** Python 3.11, FastAPI, SQLite (via raw `sqlite3`), Pydantic, Paramiko (SSH), `wandb` SDK

Entry point: `backend/app/main.py` — registers routers, configures CORS, starts background worker.

#### API Routers (`backend/app/api/`)

| Router | Prefix | Responsibility |
|--------|--------|---------------|
| `runs.py` | `/runs` | Create, list, get, cancel, refresh training runs |
| `jobs.py` | `/jobs` | List SLURM jobs, patch job state, retrieve logs |
| `metrics.py` | `/metrics` | Upsert current metrics, fetch metric history |
| `configs.py` | `/configs` | Generate and save SLM YAML configs |
| `registry.py` | `/registry` | Return available model component options |
| `notifications.py` | `/notifications` | List, create, mark-read notifications |
| `system.py` | `/system` | Health checks for all external connections |

#### Services (`backend/app/services/`)

**`launcher.py` — Job Submission**
Builds and executes a SLURM `sbatch` command over SSH:
1. Reads current git commit and config snapshot from remote repo
2. Constructs an environment-variable-driven bash script
3. SSHs into M3, runs the script, parses the returned SLURM job ID
4. Stores the job ID and config snapshot in the database

**`wandb_client.py` — W&B Integration**
- `get_run_snapshot()` — Fetches run state, step count, loss, learning rate from W&B API
- Maps W&B states (`running`, `finished`, `crashed`, `failed`) → TAP statuses
- Handles multiple metric key variants (`train_loss`, `loss`, `training_loss`, etc.)

**`background_worker.py` — Polling Loop**
- Runs on a configurable interval (default 60 s)
- For every active run: refreshes SLURM job state via SSH + syncs metrics from W&B
- Records state-transition events and fires Discord notifications on status changes

**`jobs.py` — SLURM State Machine**
Maps raw SLURM queue/execution states to TAP statuses:

| SLURM States | TAP Status |
|---|---|
| `PD`, `pending`, `configuring` | `queued` |
| `R`, `running`, `completing` | `running` |
| `CD`, `completed` (exit 0) | `completed` |
| `F`, `failed`, `timeout`, `OOM` | `failed` |
| `CA`, `cancelled` | `cancelled` |

**`metrics.py`** — Upserts current metric snapshot and historical `metric_points` rows

**`run_events.py`** — Creates timestamped event records for every status transition

**`notifications.py`** — Sends alert messages to a Discord webhook

---

### 3. Database — SQLite

Schema initialised in `backend/app/db.py`.

| Table | Key Columns |
|-------|------------|
| `runs` | `run_id`, `name`, `status`, `git_commit`, `config_path`, `config_snapshot_json`, `slurm_job_id`, `wandb_run_id` |
| `jobs` | `job_id`, `run_id`, `queue_state`, `execution_state`, `node_info`, `exit_status`, `log_path` |
| `metrics` | `run_id`, `current_step`, `training_loss`, `validation_loss`, `learning_rate` (latest snapshot) |
| `metric_points` | `run_id`, `step`, `training_loss`, `validation_loss`, `learning_rate` (full history) |
| `run_events` | `run_id`, `event_type`, `old_status`, `new_status`, `message`, `created_at` |
| `notifications` | `event_type`, `severity`, `title`, `message`, `run_id`, `read_state` |
| `metric_sync_status` | `run_id`, `source`, `status`, `last_started_at`, `error_message` |

---

### 4. GPU Cluster Integration — M3 / SLURM

All cluster communication is SSH-based (Paramiko). The remote machine ("M3") runs a SLURM scheduler against a GPU partition.

#### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TAP_M3_HOST` | `m3` | SSH hostname |
| `TAP_M3_REPO_PATH` | `~/slm_repo` | Training repo on remote |
| `TAP_M3_SUBMIT_SCRIPT` | `slurm/train.sh` | sbatch script |
| `TAP_M3_LOG_DIR` | `logs/slurm/` | Remote log directory |

#### Launch Flow

```
Frontend "New Run" form
        │
        ▼
POST /runs  (name, git_commit, config_path, overrides)
        │
        ▼
launcher.py
  1. SSH → git rev-parse HEAD  (get current commit)
  2. SSH → cat <config_path>   (snapshot config for reproducibility)
  3. Build env-var bash script
  4. SSH → sbatch slurm/train.sh
  5. Parse "Submitted batch job <JOBID>"
        │
        ▼
Run + Job rows created in SQLite
        │
        ▼
Background worker polls squeue + W&B every 60 s
```

---

### 5. W&B Integration

Configured via `WANDB_ENTITY`, `WANDB_PROJECT`, `WANDB_API_KEY`.

- The training script (on M3) logs metrics to W&B during the run
- TAP's background worker pulls metric snapshots from the W&B API independently
- Supported metric keys: `_step` / `global_step`, `epoch` / `current_epoch`, `train_loss` / `loss` / `training_loss`, `val_loss` / `validation_loss`, `lr` / `learning_rate`
- W&B run state is used alongside SLURM state to derive the authoritative TAP run status

---

### 6. Neural Network Config Builder — SLM System

TAP currently supports generating configs for **SLM (Small Language Models)** — decoder-only transformers.

#### Config Schema

```yaml
experiment:
  name: my-experiment
  family: slm
  task: causal_language_modeling

model:
  type: decoder_transformer
  attention_type: baseline | gqa | sliding_window | xsa
  normalization: rmsnorm | layernorm
  mlp_type: gelu | swiglu
  vocab_size: 50257
  seq_len: 256
  d_model: 256
  n_layers: 4
  n_heads: 4

training:
  batch_size: 4
  max_steps: 100
  learning_rate: 3.0e-4
  optimizer: adamw
  scheduler: cosine | constant

data:
  source_type: huggingface | local_jsonl | synthetic
  dataset_name: HuggingFaceFW/fineweb-edu
  streaming: true
  max_train_samples: 1000

tracking:
  wandb_enabled: true

tokenizer:
  type: bpe | sentencepiece
```

#### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /registry/slm` | Returns all valid options and compatibility rules |
| `POST /configs/generate/slm` | Generate YAML (no save) |
| `POST /configs/save/slm` | Generate + save to `generated_configs/slm/` |

The frontend Config Builder page fetches the registry to populate dropdowns, validates with Zod, and can optionally launch a training run immediately after saving.

---

### 7. Notifications — Discord Alerts

TAP fires Discord webhook messages on key events (configurable via `DISCORD_WEBHOOK_URL`):

- Run status transitions (queued → running → completed / failed)
- SLURM errors (OOM, timeout, node failure)
- Background worker errors

All notifications are also stored in the `notifications` table and surfaced in the `/alerts` UI with unread count on the notification bell.

---

## Deployment

```
docker-compose up
```

| Service | Container | Port |
|---------|-----------|------|
| Backend | `tap-api` | 8000 |
| Frontend | (run separately) | 3000 |

The backend container mounts:
- `./data/` → SQLite database persistence
- `~/.ssh/` → SSH keys for M3 access (read-only)

Frontend connects to the backend via `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.
