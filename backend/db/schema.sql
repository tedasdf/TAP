-- TAP canonical database schema.
-- init_db() in app/db.py executes this file on startup (CREATE IF NOT EXISTS is idempotent).
-- Add new columns / tables via _run_migrations() in db.py so existing databases are upgraded.

CREATE TABLE IF NOT EXISTS templates (
    template_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    params_json TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id                 TEXT PRIMARY KEY,
    name                   TEXT NOT NULL,
    status                 TEXT NOT NULL,
    git_commit             TEXT NOT NULL,
    config_path            TEXT NOT NULL,
    config_overrides       TEXT,
    wandb_config_ref       TEXT,
    slurm_job_id           TEXT,
    wandb_run_id           TEXT,
    created_at             TEXT NOT NULL,
    last_checked_at        TEXT,
    error_message          TEXT,
    config_snapshot_json   TEXT,
    template_id            TEXT REFERENCES templates(template_id),
    launch_mode            TEXT NOT NULL DEFAULT 'slurm',
    direct_pid             INTEGER,
    direct_log_path        TEXT,
    latest_checkpoint_path TEXT,
    best_checkpoint_path   TEXT,
    seed                   INTEGER,
    data_ref               TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    queue_state     TEXT,
    execution_state TEXT,
    node_info       TEXT,
    start_time      TEXT,
    end_time        TEXT,
    exit_status     TEXT,
    log_path        TEXT,
    error_log_path  TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS run_events (
    event_id     TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    message      TEXT NOT NULL,
    old_status   TEXT,
    new_status   TEXT,
    created_at   TEXT NOT NULL,
    payload_json TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS template_runs (
    id          TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    run_id      TEXT NOT NULL,
    combo_index INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (template_id) REFERENCES templates(template_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id)      REFERENCES runs(run_id)      ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metrics (
    run_id                  TEXT PRIMARY KEY,
    current_step            INTEGER,
    current_epoch           INTEGER,
    training_loss           REAL,
    validation_loss         REAL,
    runtime                 REAL,
    learning_rate           REAL,
    latest_metric_timestamp TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metric_points (
    point_id     TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL,
    step         INTEGER NOT NULL,
    epoch        INTEGER,
    source       TEXT NOT NULL DEFAULT 'manual',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL,
    UNIQUE (run_id, step, source),
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metric_points_run_id
    ON metric_points(run_id);

CREATE INDEX IF NOT EXISTS idx_metric_points_run_step
    ON metric_points(run_id, step);

CREATE TABLE IF NOT EXISTS metric_sync_status (
    run_id           TEXT PRIMARY KEY,
    source           TEXT,
    status           TEXT NOT NULL,
    last_started_at  TEXT,
    last_finished_at TEXT,
    error_message    TEXT,
    points_synced    INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    event_type      TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'info',
    title           TEXT NOT NULL DEFAULT 'Notification',
    message         TEXT NOT NULL,
    run_id          TEXT,
    job_id          TEXT,
    timestamp       TEXT NOT NULL,
    read_state      INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    subscription_id TEXT PRIMARY KEY,
    endpoint        TEXT NOT NULL UNIQUE,
    p256dh          TEXT NOT NULL,
    auth            TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
