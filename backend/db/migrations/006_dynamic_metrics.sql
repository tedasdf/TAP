-- Replace fixed-column metric_points with a flexible metrics_json blob.
-- Drops the old table (and metric_history from schema.sql) and recreates clean.

DROP TABLE IF EXISTS metric_points;
DROP TABLE IF EXISTS metric_history;

CREATE TABLE metric_points (
    point_id  TEXT PRIMARY KEY,
    run_id    TEXT NOT NULL,
    step      INTEGER NOT NULL,
    epoch     INTEGER,
    source    TEXT NOT NULL DEFAULT 'manual',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    UNIQUE (run_id, step, source)
);

CREATE INDEX IF NOT EXISTS idx_metric_points_run_id ON metric_points(run_id);
CREATE INDEX IF NOT EXISTS idx_metric_points_run_step ON metric_points(run_id, step);

-- Checkpoint paths on runs (kept across resets)
ALTER TABLE runs ADD COLUMN latest_checkpoint_path TEXT;
ALTER TABLE runs ADD COLUMN best_checkpoint_path TEXT;
