from datetime import datetime, timezone


def seed_run(conn, *, run_id="run-logs-test", slurm_job_id=None):
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
            "logs-test",
            "queued",
            "abc123",
            "configs/test.yaml",
            "{}",
            None,
            slurm_job_id,
            None,
            datetime.now(timezone.utc).isoformat(),
            None,
        ),
    )


def test_get_run_logs_without_slurm_job(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    with db.get_db() as conn:
        seed_run(conn, run_id="run-no-job", slurm_job_id=None)

    response = client.get("/runs/run-no-job/logs")

    assert response.status_code == 200

    data = response.json()

    assert data["run_id"] == "run-no-job"
    assert data["job_id"] is None
    assert data["stdout"]["exists"] is False
    assert data["stderr"]["exists"] is False
    assert data["stdout"]["error"] == "No Slurm job ID associated with this run"


def test_get_run_logs_with_missing_job_row(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    with db.get_db() as conn:
        seed_run(conn, run_id="run-missing-job-row", slurm_job_id="12345")

    response = client.get("/runs/run-missing-job-row/logs")

    assert response.status_code == 200

    data = response.json()

    assert data["run_id"] == "run-missing-job-row"
    assert data["job_id"] == "12345"
    assert data["stdout"]["exists"] is False
    assert data["stderr"]["exists"] is False
    assert data["stdout"]["error"] == "No job row found for this run"


def test_get_run_logs_reads_remote_log_files(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    client = make_client(monkeypatch, tmp_path)

    import app.db as db
    import app.api.runs as runs_api

    def fake_run_ssh_command(command: str):
        if "stdout.log" in command:
            return 0, "stdout line 1\nstdout line 2\n", ""

        if "stderr.log" in command:
            return 0, "stderr line 1\n", ""

        return 1, "", "unexpected command"

    monkeypatch.setattr(runs_api, "run_ssh_command", fake_run_ssh_command)

    with db.get_db() as conn:
        seed_run(conn, run_id="run-with-logs", slurm_job_id="999")

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
                "999",
                "run-with-logs",
                "running",
                "running",
                None,
                None,
                None,
                None,
                "/remote/path/stdout.log",
                "/remote/path/stderr.log",
            ),
        )

    response = client.get("/runs/run-with-logs/logs")

    assert response.status_code == 200

    data = response.json()

    assert data["run_id"] == "run-with-logs"
    assert data["job_id"] == "999"

    assert data["stdout"]["exists"] is True
    assert data["stdout"]["path"] == "/remote/path/stdout.log"
    assert "stdout line 1" in data["stdout"]["content"]

    assert data["stderr"]["exists"] is True
    assert data["stderr"]["path"] == "/remote/path/stderr.log"
    assert "stderr line 1" in data["stderr"]["content"]