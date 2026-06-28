def test_health_returns_healthy_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["message"] == "Silo Project Backend is running"
    assert body.get("storage_available") is True


def test_root_returns_health_message(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "Silo Project Backend is running",
    }


def test_cors_allows_local_frontend_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_ready_returns_readiness_checks(client):
    response = client.get("/system/ready")

    assert response.status_code == 200
    body = response.json()
    assert "ready" in body
    assert body["checks"]["storage"] == "ok"
