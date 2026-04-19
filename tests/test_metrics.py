def create_run(client, *, name="metrics-test-run", wandb_run_id=None):
    payload = {
        "name": name,
        "git_commit": "abc123def456",
        "config_path": "configs/train/baseline.yaml",
        "config_overrides": {},
        "submit_script": None,
        "wandb_config_ref": None,
        "wandb_run_id": wandb_run_id,
        "launch_now": False,
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 200
    return response.json()


def test_upsert_metrics(client):
    run = create_run(client, name="metrics-upsert-run")

    response = client.put(
        f"/runs/{run['run_id']}/metrics",
        json={
            "current_step": 100,
            "current_epoch": 2,
            "training_loss": 1.23,
            "validation_loss": 1.11,
            "runtime": 300.5,
            "learning_rate": 0.0003,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == run["run_id"]
    assert data["current_step"] == 100
    assert data["current_epoch"] == 2
    assert data["training_loss"] == 1.23
    assert data["validation_loss"] == 1.11
    assert data["runtime"] == 300.5
    assert data["learning_rate"] == 0.0003


def test_get_metrics(client):
    run = create_run(client, name="metrics-get-run")

    put_response = client.put(
        f"/runs/{run['run_id']}/metrics",
        json={
            "current_step": 50,
            "current_epoch": 1,
            "training_loss": 2.34,
            "validation_loss": 2.01,
            "runtime": 120.0,
            "learning_rate": 0.001,
        },
    )
    assert put_response.status_code == 200

    response = client.get(f"/runs/{run['run_id']}/metrics")
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == run["run_id"]
    assert data["current_step"] == 50
    assert data["current_epoch"] == 1


def test_get_metrics_missing_returns_404(client):
    run = create_run(client, name="metrics-missing-run")

    response = client.get(f"/runs/{run['run_id']}/metrics")
    assert response.status_code == 404


def test_sync_wandb(client, monkeypatch):
    run = create_run(client, name="wandb-sync-run", wandb_run_id="kxys4xix")

    def fake_get_run_snapshot(wandb_run_id: str):
        assert wandb_run_id == "kxys4xix"
        return {
            "wandb_state": "finished",
            "tap_status": "completed",
            "url": "https://wandb.ai/fake/run",
            "summary": {},
            "metrics": {
                "current_step": 200,
                "current_epoch": 4,
                "training_loss": 0.55,
                "validation_loss": 0.66,
                "runtime": 999.0,
                "learning_rate": 0.0001,
            },
        }

    monkeypatch.setattr(
        "app.api.metrics.get_run_snapshot",
        fake_get_run_snapshot,
    )

    response = client.post(f"/runs/{run['run_id']}/sync-wandb")
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == run["run_id"]
    assert data["wandb_run_id"] == "kxys4xix"
    assert data["wandb_state"] == "finished"
    assert data["metrics"]["current_step"] == 200
    assert data["metrics"]["validation_loss"] == 0.66

    run_response = client.get(f"/runs/{run['run_id']}")
    assert run_response.status_code == 200
    assert run_response.json()["status"] == "completed"
    