from backend.app.db import get_db


def create_run(client, *, name="job-test-run", launch_now=False):
    payload = {
        "name": name,
        "git_commit": "abc123def456",
        "config_path": "configs/train/baseline.yaml",
        "config_overrides": {},
        "submit_script": None,
        "wandb_config_ref": None,
        "wandb_run_id": None,
        "launch_now": launch_now,
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 200
    return response.json()


def create_job_for_run(run_id: str, job_id: str = "123456"):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                job_id,
                run_id,
                queue_state,
                execution_state,
                node_info,
                start_time,
                end_time,
                exit_status,
                log_path,
                error_log_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                run_id,
                "queued",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        )


def test_get_jobs_list(client):
    run = create_run(client, name="jobs-list-run")
    create_job_for_run(run["run_id"], job_id="111111")

    response = client.get("/jobs")
    assert response.status_code == 200

    jobs = response.json()
    job_ids = [job["job_id"] for job in jobs]
    assert "111111" in job_ids


def test_get_job_by_id(client):
    run = create_run(client, name="jobs-get-run")
    create_job_for_run(run["run_id"], job_id="222222")

    response = client.get("/jobs/222222")
    assert response.status_code == 200

    job = response.json()
    assert job["job_id"] == "222222"
    assert job["run_id"] == run["run_id"]
    assert job["queue_state"] == "queued"


def test_update_job_updates_run_status_to_running(client):
    run = create_run(client, name="jobs-update-running")
    create_job_for_run(run["run_id"], job_id="333333")

    response = client.patch(
        "/jobs/333333",
        json={
            "queue_state": "running",
            "execution_state": "running",
            "node_info": "m3g109",
        },
    )
    assert response.status_code == 200

    with get_db() as conn:
        run_row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run["run_id"],),
        ).fetchone()

    assert run_row["status"] == "running"


def test_update_job_updates_run_status_to_completed(client):
    run = create_run(client, name="jobs-update-completed")
    create_job_for_run(run["run_id"], job_id="444444")

    response = client.patch(
        "/jobs/444444",
        json={
            "queue_state": "completed",
            "execution_state": "completed",
            "exit_status": "0",
        },
    )
    assert response.status_code == 200

    with get_db() as conn:
        run_row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run["run_id"],),
        ).fetchone()

    assert run_row["status"] == "completed"


def test_get_job_logs_pending_without_log_path(client):
    run = create_run(client, name="jobs-log-pending")
    create_job_for_run(run["run_id"], job_id="555555")

    response = client.get("/jobs/555555/logs")
    assert response.status_code == 200

    data = response.json()
    assert data["job_id"] == "555555"
    assert data["status"] == "pending"
    assert data["lines"] == []


def test_get_missing_job_returns_404(client):
    response = client.get("/jobs/999999")
    assert response.status_code == 404