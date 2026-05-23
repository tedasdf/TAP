# TAP Frontend — Lovable Improvement Brief

## What is TAP?

TAP (Training Administration Platform) is a **mobile-first web app** for remotely monitoring and controlling ML training runs on an HPC cluster. The user submits training jobs to a Slurm scheduler on a remote GPU machine (M3), tracks them via W&B (Weights & Biases), and uses TAP to see status, metrics, and logs from their phone or tablet.

The frontend is a **Next.js + TypeScript** app styled with **Tailwind CSS** (dark zinc palette), using **TanStack Query** for data fetching and **Recharts** for charts. Navigation is a fixed bottom nav bar (mobile-first).

---

## Current App Structure

### Pages & Routes

| Route | Description |
|---|---|
| `/` | Dashboard — system health strip, run counts, needs-attention, current active runs, recent alerts |
| `/runs` | Runs list — searchable, filterable by status, sorted by priority |
| `/runs/new` | Create run form |
| `/runs/[runId]` | Run detail — tabs: Overview, Metrics, Logs, Job, Config |
| `/alerts` | All notifications, sorted by time |
| `/system` | System health cards for Backend, M3, Slurm, Database, W&B |

### Bottom Nav (4 tabs)
Home · Runs · Alerts · System

---

## Backend API (what data is available)

Base URL: `http://localhost:8000`

### Runs
- `GET /runs` — list all runs (most recent first)
- `POST /runs` — create a run
- `GET /runs/{run_id}` — single run
- `POST /runs/{run_id}/refresh` — re-poll Slurm status
- `POST /runs/{run_id}/cancel` — scancel the Slurm job

### Run statuses
`created` · `queued` · `running` · `completed` · `failed` · `cancelled` · `unknown`

### Run fields (key ones)
```
run_id, name, status, git_commit, config_path,
config_overrides (dict), config_snapshot (dict),
slurm_job_id, wandb_run_id, created_at,
last_checked_at, error_message
```

### Metrics (one snapshot per run, polled from W&B)
- `GET /runs/{run_id}/metrics`
- `PUT /runs/{run_id}/metrics`
- `POST /runs/{run_id}/sync-wandb`

Metric fields: `current_step`, `current_epoch`, `training_loss`, `validation_loss`, `runtime`, `learning_rate`, `latest_metric_timestamp`

### Jobs (Slurm job details)
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/logs`

Job fields: `job_id`, `run_id`, `queue_state`, `execution_state`, `node_info`, `start_time`, `end_time`, `exit_status`, `log_path`, `error_log_path`

### Notifications / Alerts
- `GET /notifications` — all notifications
- `PATCH /notifications/{id}/read` — mark read

Notification fields: `notification_id`, `event_type`, `message`, `run_id`, `job_id`, `timestamp`, `read_state`

### System Status
- `GET /system/status`

Fields: `backend`, `m3`, `slurm`, `database`, `wandb`, `last_sync`, `last_job_launch`

### Templates (backend exists, NO frontend yet)
- `POST /templates` — create a template
- `GET /templates` — list templates
- `GET /templates/{template_id}` — single template
- `POST /templates/{template_id}/launch` — launch all combos from a template

Template schema:
```json
{
  "template_id": "uuid",
  "name": "string",
  "description": "string | null",
  "params": {
    "model.dim": { "role": "fixed", "value": 512 },
    "trainer.max_steps": { "role": "vary", "values": [1000, 2000, 5000] },
    "lr": { "role": "derive", "expr": "base_lr * 0.1", "from": "base_lr" }
  },
  "created_at": "ISO timestamp",
  "run_count": 3
}
```
A template generates one run per combination of `vary` parameters (cartesian product).

---

## Design System

- **Palette**: zinc-950 background, zinc-900 cards, zinc-800 borders, zinc-100/200 text, zinc-400/500 secondary text
- **Cards**: `rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4`
- **Badges**: status-colored pills (running=blue, queued=yellow, failed=red, completed=green, cancelled=zinc)
- **Primary action**: white bg, black text `bg-white text-black`
- **Destructive action**: `border-red-500/20 bg-red-500/10 text-red-200`
- **Icons**: Lucide React
- **Bottom nav**: fixed, `bg-black/95 backdrop-blur border-t border-zinc-800`

---

## What to Improve / Add

### 1. Templates Page (NEW — highest priority)

Add a `/templates` route and bottom nav entry (replace or add alongside existing 4 tabs).

**Templates list page** (`/templates`):
- Card per template showing: name, description, param count, run count, created date
- "+ New Template" button → `/templates/new`
- Tap a template → `/templates/[templateId]`

**Create template page** (`/templates/new`):
- Name field (required)
- Description field (optional)
- Dynamic param builder — add/remove params, each param has:
  - Key (e.g. `model.dim`)
  - Role dropdown: `fixed` / `vary` / `derive`
  - For `fixed`: single value field
  - For `vary`: multi-value input (comma-separated or tag input)
  - For `derive`: expr field + "from" field (which other param)
- Preview: show how many run combinations will be generated
- Submit → `POST /templates`

**Template detail page** (`/templates/[templateId]`):
- Header: name, description, run count
- Params table: key | role | values
- "Launch All" button → `POST /templates/{id}/launch` — confirm dialog before launching
- List of runs spawned from this template (filter `GET /runs` by matching names or link via `template_runs`)

---

### 2. Create Run Form Improvements

Current form at `/runs/new` is missing:

- **"Launch Now" toggle** — when on, TAP SSHes to M3 and submits the Slurm job immediately; when off, just registers the run. The backend field is `launch_now: bool`.
- **Git commit field** — optional, shown only when "Launch Now" is off. Backend field: `git_commit`.
- **Submit script field** — optional path to a custom submit script. Backend field: `submit_script`.
- **W&B Run ID field** — optional, shown collapsed under "Advanced". Backend field: `wandb_run_id`.

The existing `wandb_config_ref` field can stay but move it to an "Advanced" collapsible section.

---

### 3. Run Detail — Add "History" Tab

The backend stores a `run_events` table. Add a History tab to the run detail tabs (alongside Overview, Metrics, Logs, Job, Config).

API endpoint to add to backend: `GET /runs/{run_id}/events` (needs to be added)

Each event has: `event_type`, `message`, `old_status`, `new_status`, `created_at`

Display as a vertical timeline:
- Timestamp on left
- Event type as badge (e.g. `RUN_CREATED`, `SLURM_JOB_SUBMITTED`, `STATUS_CHANGED`)
- Message text
- Status transition arrow if `old_status` and `new_status` both present

---

### 4. Metrics Tab — Real Chart Data

Currently the metrics chart is faked with 4 interpolated points. The real fix:

- The backend only stores the latest snapshot (one row per run), so real multi-point history would require a separate time-series store.
- **For now**: Display the current snapshot values as a "Latest" stat block (step, epoch, training loss, validation loss, learning rate) with the timestamp. Remove the fake chart or clearly label it "Estimated curve".
- Add a "Sync from W&B" button prominently on the metrics tab (calls `POST /runs/{run_id}/sync-wandb`).

---

### 5. Alerts — Mark as Read

The `PATCH /notifications/{id}/read` endpoint exists but is not wired up.

- On the alerts page, each alert card should have a way to mark it read (tap-to-mark or a small checkmark button).
- Unread alerts should have a subtle accent (left border or dot).
- On the home page, show an unread count badge on the Alerts nav item.

---

### 6. Dashboard — Unread Badge on Nav

Show a red dot or count on the Alerts bottom nav item when there are unread notifications. The `/notifications` response includes `read_state: boolean` on each item.

---

### 7. System Page — Last Sync Formatting

`last_sync` and `last_job_launch` are raw ISO timestamps. Format them as relative time (e.g. "3 minutes ago", "2 hours ago") with the absolute time on hover/tap.

---

### 8. Runs List — Empty State for First Launch

When the runs list is empty (no runs yet), show a friendlier empty state with a "Create your first run" CTA button that goes to `/runs/new`.

---

## Tech Constraints

- Next.js App Router (not Pages Router)
- All pages are `"use client"` — no server components with async data fetching
- Data fetching via TanStack Query hooks in `src/lib/hooks/`
- API client in `src/lib/api/client.ts` (base URL from env `NEXT_PUBLIC_API_URL`)
- Types in `src/lib/types/api.ts` (raw API shapes) and `src/lib/types/view.ts` (mapped view shapes)
- Do not use `next/image` for icons — use Lucide React
- Tailwind only — no additional CSS frameworks
- Keep all pages mobile-first, max-width ~3xl, content padded `p-4`
