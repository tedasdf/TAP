# M1 SQLite Schema Audit

## Goal

Compare the actual SQLite database schema against the backend schema assumptions used by TAP.

## Actual database path

`data/tap.db`

## Expected schema source

The expected schema is currently defined in:

- `backend/app/db.py`
- `backend/app/schemas.py`
- SQL queries in `backend/app/api/runs.py`

## Actual tables found

- `jobs`
- `metrics`
- `notifications`
- `runs`

## Expected M1 tables

- `runs`
- `jobs`
- `run_events`

## Audit result

### runs table

Status: MISMATCH

Expected columns:

- run_id
- name
- status
- git_commit
- config_path
- config_overrides
- wandb_config_ref
- slurm_job_id
- wandb_run_id
- created_at
- last_checked_at
- error_message

Actual columns:

- run_id
- name
- status
- git_commit
- config_path
- config_overrides
- wandb_config_ref
- slurm_job_id
- wandb_run_id
- created_at
- error_message

Mismatches:

- `last_checked_at` is missing from the actual SQLite database.
- This can break `/runs/{run_id}/refresh`, because the backend updates `runs.last_checked_at`.

---

### jobs table

Status: OK

Expected columns:

- job_id
- run_id
- queue_state
- execution_state
- node_info
- start_time
- end_time
- exit_status
- log_path
- error_log_path

Actual columns:

- job_id
- run_id
- queue_state
- execution_state
- node_info
- start_time
- end_time
- exit_status
- log_path
- error_log_path

Mismatches:

- None found.

---

### run_events table

Status: MISSING

Expected columns:

- event_id
- run_id
- event_type
- message
- old_status
- new_status
- created_at
- payload_json

Actual columns:

- Table does not exist.

Mismatches:

- `run_events` table is missing from the actual SQLite database.
- This can break run creation, refresh, cancellation, and event history endpoints because the backend inserts into `run_events`.

---

### metrics table

Status: OK

This table exists and is not a blocker for M1 reliable run tracking.

---

### notifications table

Status: OK

This table exists and is not a blocker for M1 reliable run tracking.

---

## Decision

The actual SQLite database does not fully match the backend schema assumptions.

The M1 schema needs a small database migration:

1. Add `last_checked_at` to `runs`.
2. Create the missing `run_events` table.

## Follow-up actions

- Create `backend/db/schema.sql` as the canonical schema.
- Create a migration SQL file for the current database.
- Apply the migration to `data/tap.db`.
- Re-run the schema inspection script.
- Confirm `runs.last_checked_at` exists.
- Confirm `run_events` exists.