def test_health_returns_healthy_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"healthy", "ok"}
    assert body.get("storage_available") is True


def test_ready_returns_readiness_checks(client):
    response = client.get("/system/ready")

    assert response.status_code == 200
    body = response.json()
    assert "ready" in body
    assert body["checks"]["storage"] == "ok"

