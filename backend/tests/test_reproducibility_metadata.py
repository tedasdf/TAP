from app.api.runs import build_config_snapshot
from app.config import settings

class DummyRunCreate:
    name = "m2-repro-test"
    git_commit = None
    config_path = "configs/train/test.yaml"
    config_overrides = {
        "trainer.max_steps": "10",
        "data.dataset_name": "fineweb10B_sp1024",
        "tokenizer.path": "artifacts/tokenizer/bpe16k/tokenizer.json",
    }
    submit_script = "scripts/slurm/test1.slurm"
    wandb_config_ref = None
    wandb_run_id = "abc123test"
    launch_now = True


def test_config_snapshot_contains_core_run_metadata():

    payload = DummyRunCreate()

    snapshot = build_config_snapshot(
        payload=payload,
        git_commit="abc123commit",
        run_id="run-123",
        created_at="2026-05-07T11:30:00+00:00",
        status="queued",
        slurm_job_id="55188672",
    )

    assert snapshot["run_id"] == "run-123"
    assert snapshot["name"] == "m2-repro-test"
    assert snapshot["git_commit"] == "abc123commit"
    assert snapshot["config_path"] == "configs/train/test.yaml"
    assert snapshot["config_overrides"]["trainer.max_steps"] == "10"
    assert snapshot["submit_script"] == "scripts/slurm/test1.slurm"
    assert snapshot["launch_now"] is True
    assert snapshot["status_at_creation"] == "queued"
    assert snapshot["slurm_job_id"] == "55188672"
    assert snapshot["created_at"] == "2026-05-07T11:30:00+00:00"


def test_config_snapshot_contains_launch_metadata():


    payload = DummyRunCreate()

    snapshot = build_config_snapshot(
        payload=payload,
        git_commit="abc123commit",
        run_id="run-123",
        created_at="2026-05-07T11:30:00+00:00",
        status="queued",
        slurm_job_id="55188672",
    )

    launch_metadata = snapshot["launch_metadata"]

    assert launch_metadata["submit_script"] == "scripts/slurm/test1.slurm"
    assert launch_metadata["remote_repo_path"] == settings.TAP_M3_REPO_PATH
    assert launch_metadata["remote_host"] == settings.TAP_M3_HOST
    assert launch_metadata["working_directory"] == settings.TAP_M3_REPO_PATH
    assert launch_metadata["submitted_at"] == "2026-05-07T11:30:00+00:00"
    assert "launch_command" in launch_metadata


def test_config_snapshot_contains_dataset_and_tokenizer_references():
   

    payload = DummyRunCreate()

    snapshot = build_config_snapshot(
        payload=payload,
        git_commit="abc123commit",
        run_id="run-123",
        created_at="2026-05-07T11:30:00+00:00",
        status="created",
        slurm_job_id=None,
    )

    data_references = snapshot["data_references"]

    assert data_references["dataset"] == "fineweb10B_sp1024"
    assert data_references["tokenizer"] == "artifacts/tokenizer/bpe16k/tokenizer.json"
    assert data_references["raw_config_path"] == "configs/train/test.yaml"


def test_config_snapshot_handles_missing_optional_metadata():
   
    class MinimalRunCreate:
        name = "minimal-run"
        git_commit = None
        config_path = "configs/train/minimal.yaml"
        config_overrides = None
        submit_script = None
        wandb_config_ref = None
        wandb_run_id = None
        launch_now = False

    snapshot = build_config_snapshot(
        payload=MinimalRunCreate(),
        git_commit="unknown",
        run_id="run-minimal",
        created_at="2026-05-07T11:30:00+00:00",
        status="created",
        slurm_job_id=None,
    )

    assert snapshot["config_overrides"] == {}
    assert snapshot["submit_script"] is None
    assert snapshot["slurm_job_id"] is None
    assert snapshot["wandb_run_id"] is None
    assert snapshot["launch_metadata"]["submitted_at"] is None
    assert snapshot["data_references"]["dataset"] is None
    assert snapshot["data_references"]["tokenizer"] is None

def test_create_run_resolves_head_to_actual_commit_and_stores_snapshot(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    client = make_client(monkeypatch, tmp_path)

    monkeypatch.setattr(
        "app.api.runs.get_remote_git_state",
        lambda: {"commit": "actualsha123", "branch": "main", "dirty": False},
    )

    response = client.post(
        "/runs",
        json={
            "name": "m2-create-run-test",
            "git_commit": "HEAD",
            "config_path": "configs/train/local_smoke.yaml",
            "config_overrides": {"training.max_steps": "10"},
            "wandb_run_id": "wandb-test-123",
            "launch_now": False,
        },
    )

    assert response.status_code == 200

    created_run = response.json()
    assert created_run["git_commit"] == "actualsha123"
    assert created_run["config_snapshot"]["git_commit"] == "actualsha123"
    assert created_run["config_snapshot"]["config_path"] == "configs/train/local_smoke.yaml"
    assert created_run["config_snapshot"]["config_overrides"] == {
        "training.max_steps": "10"
    }

    run_id = created_run["run_id"]
    get_response = client.get(f"/runs/{run_id}")

    assert get_response.status_code == 200
    stored_run = get_response.json()
    assert stored_run["git_commit"] == "actualsha123"
    assert stored_run["config_snapshot"]["run_id"] == run_id
    assert stored_run["config_snapshot"]["git_commit"] == "actualsha123"
