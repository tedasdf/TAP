"""End-to-end tests for the template launch + promoter flow.

Flow under test:
  POST /templates           → create template with vary/fixed/derive params
  POST /templates/{id}/launch → expand into N deferred runs (status=created)
  TemplatePromoter._submit() → promote one run to queued, create jobs row
  TemplatePromoter cap       → stops promoting when active_count >= cap
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


_FAKE_COMMIT = "cafebabe9876"
_FAKE_CONFIG = {
    "path": "configs/smoke.yaml",
    "source": "remote_ssh",
    "content": "model:\n  d_model: 256\n",
    "error": None,
}

_TEMPLATE_PARAMS = {
    "model.d_model":  {"role": "vary",   "values": [256, 512]},
    "training.lr":    {"role": "vary",   "values": [1e-3, 3e-4]},
    "model.n_layers": {"role": "fixed",  "value": 4},
    "model.n_heads":  {"role": "derive", "expr": "model.d_model / 64",
                       "from": "model.d_model"},
}


def _make_client(monkeypatch, tmp_path: Path) -> TestClient:
    import app.db as db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tap_test.db")
    db.init_db()

    from app.main import app
    return TestClient(app)


def _patch_remote(monkeypatch):
    import app.api.templates as tpl

    monkeypatch.setattr(tpl, "get_remote_git_state",
                        lambda: {"commit": _FAKE_COMMIT, "branch": "main", "dirty": False})
    monkeypatch.setattr(tpl, "read_remote_config_file",
                        lambda path: _FAKE_CONFIG)


# ---------------------------------------------------------------------------
# Test 1: launch creates the right number of deferred runs
# ---------------------------------------------------------------------------

def test_launch_template_creates_deferred_runs(monkeypatch, tmp_path):
    client = _make_client(monkeypatch, tmp_path)
    _patch_remote(monkeypatch)

    # Create the template
    resp = client.post("/templates", json={
        "name": "sweep-lr-dmodel",
        "description": "LR × d_model sweep",
        "params": _TEMPLATE_PARAMS,
    })
    assert resp.status_code == 200, resp.text
    template_id = resp.json()["template_id"]

    # Launch it
    resp = client.post(f"/templates/{template_id}/launch", json={
        "config_path": "configs/smoke.yaml",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # 2 vary values × 2 vary values = 4 combos
    assert body["runs_created"] == 4
    assert len(body["run_ids"]) == 4

    import app.db as db
    with db.get_db() as conn:
        # All runs are deferred (created), linked to the template
        rows = conn.execute(
            "SELECT status, template_id, config_overrides FROM runs ORDER BY created_at"
        ).fetchall()
        assert len(rows) == 4
        for row in rows:
            assert row["status"] == "created"
            assert row["template_id"] == template_id

        # Each combo has a distinct d_model value
        import json
        dmodels = {json.loads(r["config_overrides"])["model.d_model"] for r in rows}
        assert dmodels == {256, 512}

        # template_runs rows exist
        tr_rows = conn.execute(
            "SELECT * FROM template_runs WHERE template_id = ?", (template_id,)
        ).fetchall()
        assert len(tr_rows) == 4
        assert {r["combo_index"] for r in tr_rows} == {0, 1, 2, 3}

        # RUN_CREATED event per run
        for run_id in body["run_ids"]:
            events = conn.execute(
                "SELECT event_type FROM run_events WHERE run_id = ?", (run_id,)
            ).fetchall()
            assert any(e["event_type"] == "RUN_CREATED" for e in events)

        # No jobs rows yet — nothing launched
        assert conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"] == 0


# ---------------------------------------------------------------------------
# Test 2: TemplatePromoter promotes a deferred run to queued
# ---------------------------------------------------------------------------

def test_promoter_promotes_run_to_queued(monkeypatch, tmp_path):
    client = _make_client(monkeypatch, tmp_path)
    _patch_remote(monkeypatch)

    resp = client.post("/templates", json={
        "name": "single-sweep",
        "params": {"training.lr": {"role": "vary", "values": [1e-3]}},
    })
    template_id = resp.json()["template_id"]
    resp = client.post(f"/templates/{template_id}/launch", json={
        "config_path": "configs/smoke.yaml",
    })
    run_id = resp.json()["run_ids"][0]

    # Patch launch_training_run in the orchestrator
    import app.services.orchestrator as orch
    monkeypatch.setattr(
        orch, "launch_training_run",
        lambda **kw: (0, "Submitted batch job 77777", "", "77777"),
    )

    promoter = orch.TemplatePromoter(cap=3)
    run_dict = {
        "run_id": run_id,
        "name": "single-sweep-0",
        "git_commit": _FAKE_COMMIT,
        "config_path": "configs/smoke.yaml",
        "template_id": template_id,
        "active_count": 0,
    }
    promoter._submit(run_dict)

    import app.db as db
    with db.get_db() as conn:
        run_row = conn.execute(
            "SELECT status, slurm_job_id FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        assert run_row["status"] == "queued"
        assert run_row["slurm_job_id"] == "77777"

        job_row = conn.execute(
            "SELECT * FROM jobs WHERE run_id = ?", (run_id,)
        ).fetchone()
        assert job_row is not None
        assert job_row["job_id"] == "77777"
        assert job_row["queue_state"] == "queued"

        events = conn.execute(
            "SELECT event_type FROM run_events WHERE run_id = ?", (run_id,)
        ).fetchall()
        assert any(e["event_type"] == "TEMPLATE_RUN_PROMOTED" for e in events)


# ---------------------------------------------------------------------------
# Test 3: promoter respects the concurrency cap
# ---------------------------------------------------------------------------

def test_promoter_respects_cap(monkeypatch, tmp_path):
    client = _make_client(monkeypatch, tmp_path)
    _patch_remote(monkeypatch)

    # Template with 4 combos
    resp = client.post("/templates", json={
        "name": "cap-test",
        "params": {
            "training.lr": {"role": "vary", "values": [1e-3, 1e-4, 3e-4, 1e-5]},
        },
    })
    template_id = resp.json()["template_id"]
    client.post(f"/templates/{template_id}/launch", json={
        "config_path": "configs/smoke.yaml",
    })

    # Seed 2 already-active runs against this template to consume slots
    import app.db as db
    from datetime import datetime, timezone
    with db.get_db() as conn:
        for i in range(2):
            conn.execute(
                """
                INSERT INTO runs (run_id, name, status, git_commit, config_path,
                                  config_overrides, created_at, template_id)
                VALUES (?, ?, 'queued', ?, ?, '{}', ?, ?)
                """,
                (f"active-{i}", f"active-{i}", _FAKE_COMMIT,
                 "configs/smoke.yaml",
                 datetime.now(timezone.utc).isoformat(),
                 template_id),
            )

    import app.services.orchestrator as orch

    promoted: list[str] = []

    def _fake_launch(**kw):
        job_id = f"job-{len(promoted)}"
        promoted.append(job_id)
        return (0, f"Submitted batch job {job_id}", "", job_id)

    monkeypatch.setattr(orch, "launch_training_run", _fake_launch)

    # cap=3, 2 already active → only 1 more should be promoted per template
    to_promote = orch.TemplatePromoter(cap=3)._find_runs_to_promote()
    assert len(to_promote) == 1, f"expected 1, got {len(to_promote)}"
