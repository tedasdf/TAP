def test_create_notification(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    client = make_client(monkeypatch, tmp_path)

    import app.db as db

    notification = db.create_notification(
        event_type="test_notification",
        severity="info",
        title="Test notification",
        message="This is a test notification.",
    )

    assert notification["notification_id"] is not None
    assert notification["event_type"] == "test_notification"
    assert notification["severity"] == "info"
    assert notification["title"] == "Test notification"
    assert notification["message"] == "This is a test notification."
    assert notification["read_state"] == 0
    assert notification["timestamp"] is not None