def test_create_run_without_launch(client):
    payload = {
        "name": "test-run-1",
        "git_commit": "abc123def456",
        "config_path": "configs/train/baseline.yaml",
        "config_overrides": {
            "trainer.max_steps": 100
        },
        "submit_script": None,
        "wandb_config_ref": None,
        "wandb_run_id": "kxys4xix",
        "launch_now": False
    }

    response = client.post("/runs", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "test-run-1"
    assert data["status"] == "created"
    assert data["git_commit"] == "abc123def456"
    assert data["config_path"] == "configs/train/baseline.yaml"
    assert data["config_overrides"]["trainer.max_steps"] == 100
    assert data["wandb_run_id"] == "kxys4xix"
    assert data["slurm_job_id"] is None
    assert data["error_message"] is None
    assert "run_id" in data


def test_list_runs_contains_created_run(client):
    payload = {
        "name": "test-run-2",
        "git_commit": "commit-2",
        "config_path": "configs/train/baseline.yaml",
        "config_overrides": {},
        "submit_script": None,
        "wandb_config_ref": None,
        "wandb_run_id": None,
        "launch_now": False
    }

    create_response = client.post("/runs", json=payload)
    assert create_response.status_code == 200
    created = create_response.json()

    response = client.get("/runs")
    assert response.status_code == 200

    runs = response.json()
    run_ids = [run["run_id"] for run in runs]
    assert created["run_id"] in run_ids


def test_get_run_by_id(client):
    payload = {
        "name": "test-run-3",
        "git_commit": "commit-3",
        "config_path": "configs/train/baseline.yaml",
        "config_overrides": {},
        "submit_script": None,
        "wandb_config_ref": None,
        "wandb_run_id": None,
        "launch_now": False
    }

    create_response = client.post("/runs", json=payload)
    assert create_response.status_code == 200
    created = create_response.json()

    response = client.get(f"/runs/{created['run_id']}")
    assert response.status_code == 200

    run_data = response.json()
    assert run_data["run_id"] == created["run_id"]
    assert run_data["name"] == "test-run-3"
    assert run_data["status"] == "created"