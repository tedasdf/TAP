def test_system_status_endpoint(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    client = make_client(monkeypatch, tmp_path)

    import app.api.system as system_api

    monkeypatch.setattr(system_api, "check_ssh", lambda: "connected")
    monkeypatch.setattr(system_api, "check_slurm", lambda: "connected")
    monkeypatch.setattr(system_api, "check_wandb", lambda: "unknown")

    response = client.get("/system/status")

    assert response.status_code == 200

    data = response.json()

    assert data["backend"] == "ok"
    assert data["database"] == "ok"
    assert data["m3"] == "connected"
    assert data["slurm"] == "connected"
    assert "wandb" in data
    assert "timestamp" in data

    assert data["checks"]["database"] == "ok"
    assert data["checks"]["ssh"] == "connected"
    assert data["checks"]["slurm"] == "connected"
    assert "wandb" in data["checks"]

    assert "run_count" in data
    assert "active_run_count" in data
    assert "notification_count" in data

    assert "background_worker" in data

    worker = data["background_worker"]

    assert "enabled" in worker
    assert "running" in worker
    assert "interval_seconds" in worker
    assert "last_cycle_started_at" in worker
    assert "last_cycle_finished_at" in worker
    assert "last_cycle_run_count" in worker
    assert "last_cycle_error_count" in worker
    assert "last_error" in worker