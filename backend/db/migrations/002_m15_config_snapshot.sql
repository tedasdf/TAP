-- SQLite does not support IF NOT EXISTS for ADD COLUMN on older versions.
-- Run this once for existing TAP databases that predate M2 config snapshots.
ALTER TABLE runs ADD COLUMN config_snapshot_json TEXT;
