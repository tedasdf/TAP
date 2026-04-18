def create_run(client, *, name="notif-run"):
    payload = {
        "name": name,
        "git_commit": "abc123def456",
        "config_path": "configs/train/baseline.yaml",
        "config_overrides": {},
        "submit_script": None,
        "wandb_config_ref": None,
        "wandb_run_id": None,
        "launch_now": False,
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 200
    return response.json()


def test_create_notification(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.notifications.send_discord_message",
        lambda message: True,
    )

    response = client.post(
        "/notifications",
        json={
            "event_type": "info",
            "message": "Hello from TAP",
            "run_id": None,
            "job_id": None,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["event_type"] == "info"
    assert data["message"] == "Hello from TAP"
    assert data["read_state"] == 0
    assert data["discord_sent"] is True


def test_create_notification_with_run_id(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.notifications.send_discord_message",
        lambda message: True,
    )

    run = create_run(client, name="notif-run-linked")

    response = client.post(
        "/notifications",
        json={
            "event_type": "run_update",
            "message": "Run started",
            "run_id": run["run_id"],
            "job_id": None,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == run["run_id"]
    assert data["discord_sent"] is True


def test_list_notifications(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.notifications.send_discord_message",
        lambda message: True,
    )

    create_response = client.post(
        "/notifications",
        json={
            "event_type": "info",
            "message": "Test list notifications",
            "run_id": None,
            "job_id": None,
        },
    )
    assert create_response.status_code == 200

    response = client.get("/notifications")
    assert response.status_code == 200

    notifications = response.json()
    assert len(notifications) >= 1
    assert any(n["message"] == "Test list notifications" for n in notifications)


def test_mark_notification_read(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.notifications.send_discord_message",
        lambda message: True,
    )

    create_response = client.post(
        "/notifications",
        json={
            "event_type": "info",
            "message": "Mark me read",
            "run_id": None,
            "job_id": None,
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    response = client.patch(f"/notifications/{created['notification_id']}/read")
    assert response.status_code == 200

    data = response.json()
    assert data["notification_id"] == created["notification_id"]
    assert data["read_state"] == 1


def test_test_notification_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.notifications.send_discord_message",
        lambda message: True,
    )

    response = client.post("/notifications/test")
    assert response.status_code == 200

    data = response.json()
    assert data["event_type"] == "test"
    assert data["message"] == "TAP test notification"
    assert data["discord_sent"] is True