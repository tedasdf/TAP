# M1 Run Creation / Registration Flow

## Goal

Verify that TAP can create or register a training run with required metadata stored in SQLite.

## Backend endpoint

`POST /runs`

## Request fields

- `name`
- `git_commit`
- `config_path`
- `config_overrides`
- `submit_script`
- `wandb_config_ref`
- `wandb_run_id`
- `launch_now`

## Expected flow

1. Backend receives `POST /runs`.
2. Backend reads git state from the configured remote SLM repository.
3. If `launch_now = true`, backend submits a Slurm job.
4. Backend stores the run in the `runs` table.
5. Backend stores a `RUN_CREATED` event in `run_events`.
6. If Slurm returns a job ID:
   - store `slurm_job_id` on the run
   - create a row in `jobs`
   - store a `SLURM_JOB_SUBMITTED` event
7. Backend returns the created run.

## Non-launch registration test

Expected result:

- run is created
- status is `created`
- `slurm_job_id` is null
- optional `wandb_run_id` is stored
- run can be retrieved from `GET /runs/{run_id}`

## Slurm launch test

Expected result:

- run is created
- status is `queued`
- `slurm_job_id` is stored
- matching row exists in `jobs`
- run can be retrieved from `GET /runs/{run_id}`

## Result

TODO: Fill this in after testing.