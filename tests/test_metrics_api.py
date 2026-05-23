from __future__ import annotations

from fastapi.testclient import TestClient


def test_latest_and_history_are_empty_for_new_run(client: TestClient, run_id: str) -> None:
    latest_response = client.get(f"/runs/{run_id}/metrics/latest")
    history_response = client.get(f"/runs/{run_id}/metrics/history")
    sync_status_response = client.get(f"/runs/{run_id}/metrics/sync-status")

    assert latest_response.status_code == 200
    assert latest_response.json() is None

    assert history_response.status_code == 200
    assert history_response.json() == []

    assert sync_status_response.status_code == 200
    sync_status = sync_status_response.json()
    assert sync_status["run_id"] == run_id
    assert sync_status["sync_status"] == "never_synced"
    assert sync_status["sync_source"] is None


def test_put_metrics_updates_latest_history_and_sync_status(client: TestClient, run_id: str) -> None:
    payload = {
        "current_step": 1,
        "current_epoch": 0,
        "training_loss": 4.2,
        "validation_loss": 4.4,
        "learning_rate": 0.0003,
        "runtime": 10,
        "latest_metric_timestamp": "2026-05-08T00:01:00+00:00",
    }

    put_response = client.put(f"/runs/{run_id}/metrics", json=payload)
    assert put_response.status_code == 200
    latest = put_response.json()
    assert latest["run_id"] == run_id
    assert latest["current_step"] == 1
    assert latest["training_loss"] == 4.2
    assert latest["validation_loss"] == 4.4
    assert latest["runtime"] == 10.0

    latest_response = client.get(f"/runs/{run_id}/metrics/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["current_step"] == 1

    history_response = client.get(f"/runs/{run_id}/metrics/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["run_id"] == run_id
    assert history[0]["step"] == 1
    assert history[0]["epoch"] == 0
    assert history[0]["train_loss"] == 4.2
    assert history[0]["val_loss"] == 4.4
    assert history[0]["learning_rate"] == 0.0003
    assert history[0]["runtime_seconds"] == 10.0
    assert history[0]["source"] == "manual"

    sync_status_response = client.get(f"/runs/{run_id}/metrics/sync-status")
    assert sync_status_response.status_code == 200
    sync_status = sync_status_response.json()
    assert sync_status["sync_status"] == "ok"
    assert sync_status["sync_source"] == "manual"
    assert sync_status["last_successful_sync_at"] is not None
    assert sync_status["last_error"] is None


def test_metric_history_deduplicates_same_run_step_and_source(client: TestClient, run_id: str) -> None:
    payload = {
        "current_step": 7,
        "current_epoch": 0,
        "training_loss": 3.0,
        "validation_loss": 3.2,
        "learning_rate": 0.0002,
        "runtime": 70,
        "latest_metric_timestamp": "2026-05-08T00:07:00+00:00",
    }

    first = client.put(f"/runs/{run_id}/metrics", json=payload)
    second = client.put(f"/runs/{run_id}/metrics", json={**payload, "training_loss": 2.9})

    assert first.status_code == 200
    assert second.status_code == 200

    history_response = client.get(f"/runs/{run_id}/metrics/history")
    assert history_response.status_code == 200
    history = history_response.json()

    assert len(history) == 1
    assert history[0]["step"] == 7
    assert history[0]["source"] == "manual"

    latest_response = client.get(f"/runs/{run_id}/metrics/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["training_loss"] == 2.9


def test_metrics_endpoints_return_404_for_missing_run(client: TestClient) -> None:
    assert client.get("/runs/missing-run/metrics/latest").status_code == 404
    assert client.get("/runs/missing-run/metrics/history").status_code == 404
    assert client.get("/runs/missing-run/metrics/sync-status").status_code == 404


def test_wandb_sync_without_wandb_run_id_records_error_status(
    client: TestClient,
    run_id: str,
) -> None:
    response = client.post(f"/runs/{run_id}/metrics/sync")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["message"] == "No wandb_run_id stored for this run"
    assert detail["sync_status"]["sync_status"] == "error"
    assert detail["sync_status"]["sync_source"] == "wandb_history"
    assert "No wandb_run_id" in detail["sync_status"]["last_error"]

    sync_status_response = client.get(f"/runs/{run_id}/metrics/sync-status")
    assert sync_status_response.status_code == 200
    sync_status = sync_status_response.json()
    assert sync_status["sync_status"] == "error"
    assert sync_status["sync_source"] == "wandb_history"
