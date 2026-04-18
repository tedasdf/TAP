from tests.conftest import client

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "tap-api"


def test_system_status(client):
    response = client.get("/system/status")
    assert response.status_code == 200

    data = response.json()
    assert "service" in data
    assert "status" in data
    assert "run_count" in data
    assert "active_run_count" in data
    assert "notification_count" in data