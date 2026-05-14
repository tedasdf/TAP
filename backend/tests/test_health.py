def test_health_endpoint(monkeypatch, tmp_path):
    from tests.test_metrics import make_client

    client = make_client(monkeypatch, tmp_path)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    print(data)

    assert data["backend"] == "ok"
    assert data["database"] == "ok"
    assert "timestamp" in data