from datetime import datetime, timezone


def seed_run(conn, *, run_id: str, status: str = "running"):
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


def test_background_refresh_failure_creates_event_and_notification(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    make_client(monkeypatch, tmp_path)

    import app.db as db
    import app.services.background_worker as worker

    with db.get_db() as conn:
        seed_run(conn, run_id="bad-run", status="running")

    monkeypatch.setattr(worker, "list_active_run_ids", lambda: ["bad-run"])

    def fake_refresh_run_by_id(run_id: str):
        raise RuntimeError("refresh exploded")

    monkeypatch.setattr(worker, "refresh_run_by_id", fake_refresh_run_by_id)

    import asyncio

    asyncio.run(worker.run_background_refresh_cycle())

    with db.get_db() as conn:
        event = conn.execute(
            """
            SELECT *
            FROM run_events
            WHERE run_id = ?
              AND event_type = ?
            """,
            ("bad-run", "BACKGROUND_REFRESH_FAILED"),
        ).fetchone()

        notification = conn.execute(
            """
            SELECT *
            FROM notifications
            WHERE run_id = ?
              AND event_type = ?
            """,
            ("bad-run", "background_refresh_failed"),
        ).fetchone()

    assert event is not None
    assert "refresh exploded" in event["message"]

    assert notification is not None
    assert notification["severity"] == "warning"
    assert notification["title"] == "Background refresh failed"
    assert "refresh exploded" in notification["message"]

    status = worker.get_background_worker_status()

    assert status["last_cycle_error_count"] == 1
    assert "bad-run" in status["last_error"]