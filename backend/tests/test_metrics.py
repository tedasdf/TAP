from pathlib import Path

from fastapi.testclient import TestClient


def seed_run(
    db,
    *,
    run_id: str = "m3-test-run",
    name: str = "M3 Test Run",
    status: str = "running",
    wandb_run_id: str | None = None,
) -> None:
    from app.db import get_db

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id,
                name,
                status,
                git_commit,
                config_path,
                config_overrides,
                wandb_config_ref,
                slurm_job_id,
                wandb_run_id,
                created_at,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                name,
                status,
                "test-sha",
                "configs/train/local_smoke.yaml",
                "{}",
                None,
                None,
                wandb_run_id,
                "2026-05-07T11:30:00+00:00",
                None,
            ),
        )


def make_client(monkeypatch, tmp_path: Path) -> TestClient:
    import app.db as db

    test_db_path = tmp_path / "tap_metrics_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)

    from app.db import init_db

    init_db()

    from app.main import app

    return TestClient(app)


def test_put_metrics_writes_latest_snapshot_and_history(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    seed_run(db, run_id="m3-test-run")

    response = client.put(
        "/runs/m3-test-run/metrics",
        json={
            "current_step": 1,
            "current_epoch": 0,
            "training_loss": 6.2,
            "validation_loss": 6.4,
            "runtime": 5.0,
            "learning_rate": 0.0005,
        },
    )

    assert response.status_code == 200

    latest = response.json()
    assert latest["run_id"] == "m3-test-run"
    assert latest["current_step"] == 1
    assert latest["current_epoch"] == 0
    assert latest["training_loss"] == 6.2
    assert latest["validation_loss"] == 6.4
    assert latest["runtime"] == 5.0
    assert latest["learning_rate"] == 0.0005

    history_response = client.get("/runs/m3-test-run/metrics/history")

    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 1
    assert history[0]["step"] == 1
    assert history[0]["epoch"] == 0
    assert history[0]["training_loss"] == 6.2
    assert history[0]["validation_loss"] == 6.4
    assert history[0]["runtime"] == 5.0
    assert history[0]["learning_rate"] == 0.0005
    assert history[0]["source"] == "manual"


def test_get_latest_metrics_returns_latest_snapshot(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    seed_run(db, run_id="m3-test-run")

    client.put(
        "/runs/m3-test-run/metrics",
        json={
            "current_step": 1,
            "training_loss": 6.2,
            "validation_loss": 6.4,
            "runtime": 5.0,
            "learning_rate": 0.0005,
        },
    )

    client.put(
        "/runs/m3-test-run/metrics",
        json={
            "current_step": 2,
            "training_loss": 5.7,
            "validation_loss": 6.0,
            "runtime": 10.0,
            "learning_rate": 0.00045,
        },
    )

    response = client.get("/runs/m3-test-run/metrics")

    assert response.status_code == 200

    latest = response.json()
    assert latest["run_id"] == "m3-test-run"
    assert latest["current_step"] == 2
    assert latest["training_loss"] == 5.7
    assert latest["validation_loss"] == 6.0
    assert latest["runtime"] == 10.0
    assert latest["learning_rate"] == 0.00045


def test_metric_history_returns_real_points_in_step_order(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    seed_run(db, run_id="m3-test-run")

    client.put(
        "/runs/m3-test-run/metrics",
        json={
            "current_step": 3,
            "training_loss": 5.3,
            "validation_loss": 5.8,
            "runtime": 15.0,
            "learning_rate": 0.00045,
        },
    )

    client.put(
        "/runs/m3-test-run/metrics",
        json={
            "current_step": 1,
            "training_loss": 6.2,
            "validation_loss": 6.4,
            "runtime": 5.0,
            "learning_rate": 0.0005,
        },
    )

    client.put(
        "/runs/m3-test-run/metrics",
        json={
            "current_step": 2,
            "training_loss": 5.7,
            "validation_loss": 6.0,
            "runtime": 10.0,
            "learning_rate": 0.0005,
        },
    )

    response = client.get("/runs/m3-test-run/metrics/history")

    assert response.status_code == 200

    history = response.json()
    assert [point["step"] for point in history] == [1, 2, 3]
    assert [point["training_loss"] for point in history] == [6.2, 5.7, 5.3]


def test_metric_history_respects_limit(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    seed_run(db, run_id="m3-test-run")

    for step in range(1, 6):
        client.put(
            "/runs/m3-test-run/metrics",
            json={
                "current_step": step,
                "training_loss": 7.0 - step,
                "validation_loss": 7.5 - step,
                "runtime": float(step * 5),
                "learning_rate": 0.0005,
            },
        )

    response = client.get("/runs/m3-test-run/metrics/history?limit=2")

    assert response.status_code == 200

    history = response.json()
    assert len(history) == 2
    assert [point["step"] for point in history] == [1, 2]


def test_metric_history_empty_for_run_with_no_metrics(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    seed_run(db, run_id="m3-empty-run")

    response = client.get("/runs/m3-empty-run/metrics/history")

    assert response.status_code == 200
    assert response.json() == []


def test_get_latest_metrics_returns_404_when_no_metrics_exist(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    seed_run(db, run_id="m3-empty-run")

    response = client.get("/runs/m3-empty-run/metrics")

    assert response.status_code == 404
    assert "No metrics found" in response.json()["detail"]


def test_metrics_endpoints_return_404_for_missing_run(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    put_response = client.put(
        "/runs/missing-run/metrics",
        json={
            "current_step": 1,
            "training_loss": 6.2,
        },
    )

    latest_response = client.get("/runs/missing-run/metrics")
    history_response = client.get("/runs/missing-run/metrics/history")

    assert put_response.status_code == 404
    assert latest_response.status_code == 404
    assert history_response.status_code == 404


def test_wandb_sync_requires_wandb_run_id(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    seed_run(db, run_id="m3-no-wandb-run", wandb_run_id=None)

    response = client.post("/runs/m3-no-wandb-run/sync-wandb")

    assert response.status_code == 400
    assert response.json()["detail"] == "No wandb_run_id stored for this run"


def test_wandb_sync_writes_latest_metrics_and_history(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db
    import app.api.metrics as metrics_api

    seed_run(
        db,
        run_id="m3-wandb-run",
        status="running",
        wandb_run_id="wandb-test-123",
    )

    def fake_get_run_snapshot(wandb_run_id: str):
        assert wandb_run_id == "wandb-test-123"

        return {
            "wandb_state": "finished",
            "tap_status": "completed",
            "url": "https://wandb.ai/test/slm-runs/runs/wandb-test-123",
            "metrics": {
                "current_step": 10,
                "current_epoch": 1,
                "training_loss": 4.2,
                "validation_loss": 4.5,
                "runtime": 120.0,
                "learning_rate": 0.0003,
            },
        }

    monkeypatch.setattr(metrics_api, "get_run_snapshot", fake_get_run_snapshot)

    response = client.post("/runs/m3-wandb-run/sync-wandb")

    assert response.status_code == 200

    payload = response.json()
    assert payload["run_id"] == "m3-wandb-run"
    assert payload["wandb_run_id"] == "wandb-test-123"
    assert payload["wandb_state"] == "finished"
    assert payload["wandb_url"] == "https://wandb.ai/test/slm-runs/runs/wandb-test-123"

    latest = payload["metrics"]
    assert latest["current_step"] == 10
    assert latest["training_loss"] == 4.2
    assert latest["validation_loss"] == 4.5
    assert latest["runtime"] == 120.0
    assert latest["learning_rate"] == 0.0003

    history_response = client.get("/runs/m3-wandb-run/metrics/history")

    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 1
    assert history[0]["step"] == 10
    assert history[0]["training_loss"] == 4.2
    assert history[0]["validation_loss"] == 4.5
    assert history[0]["source"] == "wandb"

    run_response = client.get("/runs/m3-wandb-run")

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "completed"


def test_wandb_sync_error_is_visible(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    import app.db as db
    import app.api.metrics as metrics_api

    seed_run(
        db,
        run_id="m3-wandb-error-run",
        status="running",
        wandb_run_id="bad-wandb-run",
    )

    def fake_get_run_snapshot(wandb_run_id: str):
        raise RuntimeError("fake W&B outage")

    monkeypatch.setattr(metrics_api, "get_run_snapshot", fake_get_run_snapshot)

    response = client.post("/runs/m3-wandb-error-run/sync-wandb")

    assert response.status_code == 500
    assert "W&B sync failed" in response.json()["detail"]
    assert "fake W&B outage" in response.json()["detail"]