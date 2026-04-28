# TAP truthfulness patch

Apply from the TAP repo root:

```bash
unzip -o tap_truthfulness_patch.zip
```

Main changes:

- Frontend Refresh button now calls `POST /runs/{run_id}/refresh` instead of only refetching stale DB data.
- Backend refresh now combines Slurm status and W&B status into one reconciled TAP status.
- Slurm `ExitCode=0:0` is treated as success, so completed jobs are not incorrectly marked failed.
- `/system/status` imports missing dependencies and can run.
- Create Run page now sends `git_commit`, `launch_now`, `wandb_run_id`, and parses config overrides into a dict.
- Logs tab accepts backend `lines` response as well as `logs/stdout/stderr`.
- System page reads the backend `checks.database/checks.ssh/checks.wandb` shape.

Backend syntax check run in the container:

```bash
python -S -m py_compile backend/app/api/runs.py backend/app/services/jobs.py backend/app/api/system.py backend/app/api/jobs.py backend/app/api/metrics.py backend/app/schemas.py
```

Not included yet:

- run_events table
- background sync worker
- proper test suite / CI
