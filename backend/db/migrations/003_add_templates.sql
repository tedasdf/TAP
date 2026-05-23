-- Migration: add templates and template_runs tables

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
