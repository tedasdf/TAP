CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    git_commit TEXT NOT NULL,
    config_path TEXT NOT NULL,
    config_overrides TEXT,
    wandb_config_ref TEXT,
    slurm_job_id TEXT,
    wandb_run_id TEXT,
    created_at TEXT NOT NULL,
    last_checked_at TEXT,
    error_message TEXT,
    template_id TEXT REFERENCES templates(template_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    queue_state TEXT,
    execution_state TEXT,
    node_info TEXT,
    start_time TEXT,
    end_time TEXT,
    exit_status TEXT,
    log_path TEXT,
    error_log_path TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS run_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    created_at TEXT NOT NULL,
    payload_json TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metrics (
    run_id TEXT PRIMARY KEY,
    current_step INTEGER,
    current_epoch INTEGER,
    training_loss REAL,
    validation_loss REAL,
    runtime REAL,
    learning_rate REAL,
    latest_metric_timestamp TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    run_id TEXT,
    job_id TEXT,
    timestamp TEXT NOT NULL,
    read_state INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS templates (
    template_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    params_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS template_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id TEXT NOT NULL REFERENCES templates(template_id),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    combo_index INTEGER NOT NULL
);
