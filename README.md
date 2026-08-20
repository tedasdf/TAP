# TAP — Training Administration Platform

TAP is a lightweight, mobile-friendly control panel for machine-learning jobs running on remote compute. It submits training runs to a SLURM cluster over SSH, follows their lifecycle, retrieves remote logs, synchronizes experiment metrics from Weights & Biases, and surfaces failures and alerts in one interface.

> **Project status:** TAP is a single-user research prototype and demo. It is not yet a production-grade or multi-tenant orchestration platform.

## Demo capabilities

- Submit a training run to remote SLURM compute over SSH
- Track `created`, `queued`, `running`, `completed`, `failed`, and `cancelled` states
- View remote stdout and stderr logs
- Synchronize current and historical W&B metrics
- Display loss and learning-rate charts
- Record status changes in an immutable run-event timeline
- Surface failure, stuck-queue, and metric alerts
- Launch experiment matrices with a configurable concurrency limit
- Capture the Git commit, configuration, seed, and data reference used for a run

## Architecture

```text
Browser / Next.js UI
        |
        | REST
        v
FastAPI backend + SQLite
        |                    |
        | SSH / SCP          | W&B API
        v                    v
Remote SLURM cluster     Weights & Biases
```

The backend communicates with the cluster using the local SSH client. SLURM supplies queue and execution state, while W&B supplies training state and metrics. A background orchestrator promotes deferred matrix runs up to the configured concurrency limit and refreshes active runs.

More detail is available in [ARCHITECTURE.md](ARCHITECTURE.md) and [Roadmap.md](Roadmap.md).

## Prerequisites

- Docker with Docker Compose
- An SSH-accessible Linux machine or cluster
- SLURM commands available on the remote host (`sbatch`, `squeue`, and `sacct`)
- A training repository already present on the remote host
- A compatible SLURM submission script in that repository
- A W&B account and API key if metric synchronization is required
- SSH credentials configured on the machine running TAP

## Quick start

1. Clone the repository:

   ```bash
   git clone https://github.com/tedasdf/TAP.git
   cd TAP
   ```

2. Create your local configuration:

   ```bash
   cp .env.example .env
   ```

3. Edit `.env` for your remote host, repository, SLURM script, and W&B project.

4. Confirm that SSH works non-interactively:

   ```bash
   ssh your-cluster-alias "echo connected"
   ```

5. Start TAP:

   ```bash
   docker compose up --build
   ```

6. Open the frontend at [http://localhost:3000](http://localhost:3000). The API is available at [http://localhost:8000](http://localhost:8000).

If the frontend is accessed from another device, set `NEXT_PUBLIC_API_BASE_URL` to a URL that device can reach before building the frontend.

## Configuration

| Variable | Purpose |
|---|---|
| `TAP_M3_HOST` | SSH hostname or alias for the remote cluster |
| `TAP_M3_REPO_PATH` | Training repository path on the remote host |
| `TAP_M3_SUBMIT_SCRIPT` | SLURM submission script relative to the training repository |
| `TAP_MAX_CONCURRENT_JOBS` | Maximum queued/running matrix jobs per template |
| `TAP_BACKGROUND_REFRESH_ENABLED` | Enables automatic SLURM and W&B refresh |
| `TAP_BACKGROUND_REFRESH_INTERVAL_SECONDS` | Background refresh interval |
| `TAP_API_URL` | API callback URL visible to training jobs |
| `WANDB_ENTITY` | W&B user or team |
| `WANDB_PROJECT` | W&B project |
| `WANDB_API_KEY` | W&B API credential; never commit it |
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL used by the browser |

See [.env.example](.env.example) for the complete safe template.

## Reproducible launch workflow

Before launching a run:

1. Commit changes in the training repository.
2. Push the commit to its Git remote.
3. Launch through TAP using that exact commit and a versioned configuration.
4. Avoid launching from an uncommitted or ambiguous working tree.

TAP records the resolved commit and a configuration snapshot with the run.

## Suggested demo

1. Submit a short training run.
2. Show the SLURM job ID and the transition from queued to running.
3. Open the remote logs.
4. Show W&B loss metrics appearing in the run dashboard.
5. Open a previously failed run and its alert/event history.
6. Launch a small experiment matrix with `TAP_MAX_CONCURRENT_JOBS=1` or `2` to demonstrate controlled promotion.

## Current limitations

- No built-in authentication or authorization
- Intended for a trusted, single-user private network
- No automatic retry policy for failed training jobs
- Dataset and checkpoint management are metadata-only and incomplete
- The orchestrator assumes a single backend process; it has no distributed lease
- Remote execution depends on an existing training environment and submit script
- Some legacy tests require reconciliation after recent service refactoring

Do not expose the API directly to the public internet. See [SECURITY.md](SECURITY.md) before deployment.

## Development

Backend tests use the locked `uv` environment:

```bash
uv run pytest
```

Frontend development:

```bash
cd frontend
npm install
npm run dev
```

## Roadmap

Planned work includes stronger artifact and checkpoint tracking, dataset management, retry policies, hardened SSH communication, worker coordination, authentication, and improved reproducible training environments. See [Roadmap.md](Roadmap.md).

## License

No open-source license has been selected yet. Until a license is added, the source is publicly visible but normal copyright restrictions still apply.
