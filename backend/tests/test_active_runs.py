from datetime import datetime, timezone


def seed_run(conn, *, run_id: str, status: str):
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
            run_id,
            status,
            "abc123",
            "configs/test.yaml",
            "{}",
            None,
            None,
            None,
            datetime.now(timezone.utc).isoformat(),
            None,
        ),
    )


def test_list_active_run_ids(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    make_client(monkeypatch, tmp_path)

    import app.db as db
    from app.services.run_refresh import list_active_run_ids

    with db.get_db() as conn:
        seed_run(conn, run_id="created-run", status="created")
        seed_run(conn, run_id="queued-run", status="queued")
        seed_run(conn, run_id="running-run", status="running")
        seed_run(conn, run_id="completed-run", status="completed")
        seed_run(conn, run_id="failed-run", status="failed")
        seed_run(conn, run_id="cancelled-run", status="cancelled")

    active_run_ids = list_active_run_ids()

    assert "created-run" in active_run_ids
    assert "queued-run" in active_run_ids
    assert "running-run" in active_run_ids

    assert "completed-run" not in active_run_ids
    assert "failed-run" not in active_run_ids
    assert "cancelled-run" not in active_run_ids