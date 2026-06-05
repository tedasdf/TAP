"""End-to-end tests for POST /runs.

Covers:
  - Non-launch path  (launch_now=False)  → status=created, no slurm_job_id, no jobs row
  - SLURM-launch path (launch_now=True)  → status=queued,  slurm_job_id stored, jobs row present
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


_FAKE_COMMIT = "deadbeef1234"
_FAKE_CONFIG_SNAPSHOT = {
    "path": "configs/test.yaml",
    "source": "remote_ssh",
    "content": "model:\n  hidden_size: 256\n",
    "error": None,
}


def _make_client(monkeypatch, tmp_path: Path) -> TestClient:
    import app.db as db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tap_test.db")
    db.init_db()

    from app.main import app
    return TestClient(app)


def _patch_remote(monkeypatch, *, slurm_job_id: str | None = None):
    """Stub all SSH/remote calls used by RunService.create()."""
    import app.services.run_service as svc

    monkeypatch.setattr(
        svc, "get_remote_git_state",
        lambda: {"commit": _FAKE_COMMIT, "branch": "main", "dirty": False},
    )
    monkeypatch.setattr(
        svc, "read_remote_config_file",
        lambda path: _FAKE_CONFIG_SNAPSHOT,
    )
    if slurm_job_id is not None:
        monkeypatch.setattr(
            svc, "launch_training_run",
            lambda **kw: (0, f"Submitted batch job {slurm_job_id}", "", slurm_job_id),
        )


# ---------------------------------------------------------------------------
# Non-launch path
# ---------------------------------------------------------------------------

def test_post_runs_no_launch_creates_deferred_run(monkeypatch, tmp_path):
    client = _make_client(monkeypatch, tmp_path)
    _patch_remote(monkeypatch)

    resp = client.post("/runs", json={
        "name": "deferred-run",
        "config_path": "configs/test.yaml",
        "launch_now": False,
        "launch_mode": "slurm",
    })

    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "created"
    assert body["slurm_job_id"] is None
    assert body["git_commit"] == _FAKE_COMMIT
    assert body["launch_mode"] == "slurm"

    run_id = body["run_id"]

    # DB-level: runs row
    import app.db as db
    with db.get_db() as conn:
        run_row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        assert run_row is not None
        assert run_row["status"] == "created"
        assert run_row["slurm_job_id"] is None

        # No jobs row should exist
        job_row = conn.execute(
            "SELECT * FROM jobs WHERE run_id = ?", (run_id,)
        ).fetchone()
        assert job_row is None

        # RUN_CREATED event should exist
        events = conn.execute(
            "SELECT event_type FROM run_events WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        event_types = [e["event_type"] for e in events]
        assert "RUN_CREATED" in event_types
        assert "SLURM_JOB_SUBMITTED" not in event_types


# ---------------------------------------------------------------------------
# SLURM-launch path
# ---------------------------------------------------------------------------

def test_post_runs_slurm_launch_creates_queued_run_with_job(monkeypatch, tmp_path):
    client = _make_client(monkeypatch, tmp_path)
    _patch_remote(monkeypatch, slurm_job_id="99999")

    resp = client.post("/runs", json={
        "name": "slurm-run",
        "config_path": "configs/test.yaml",
        "launch_now": True,
        "launch_mode": "slurm",
        "submit_script": "scripts/slurm/test.slurm",
    })

    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "queued"
    assert body["slurm_job_id"] == "99999"
    assert body["git_commit"] == _FAKE_COMMIT

    run_id = body["run_id"]

    import app.db as db
    with db.get_db() as conn:
        run_row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        assert run_row is not None
        assert run_row["status"] == "queued"
        assert run_row["slurm_job_id"] == "99999"

        # Matching jobs row
        job_row = conn.execute(
            "SELECT * FROM jobs WHERE run_id = ?", (run_id,)
        ).fetchone()
        assert job_row is not None
        assert job_row["job_id"] == "99999"
        assert job_row["queue_state"] == "queued"

        # Both events present, in order
        events = conn.execute(
            "SELECT event_type FROM run_events WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        event_types = [e["event_type"] for e in events]
        assert "RUN_CREATED" in event_types
        assert "SLURM_JOB_SUBMITTED" in event_types
        assert event_types.index("RUN_CREATED") < event_types.index("SLURM_JOB_SUBMITTED")
