def test_health_returns_healthy_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_returns_health_message(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Silo Backend is running"}


def test_cors_allows_local_frontend_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_allows_vercel_frontend_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "https://autonomous-cross-silo-knowledge-rec.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://autonomous-cross-silo-knowledge-rec.vercel.app"


def test_cors_allows_loopback_frontend_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cors_allows_executive_roi_preflight(client):
    response = client.options(
        "/executive/roi",
        headers={
            "Origin": "https://autonomous-cross-silo-knowledge-rec.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://autonomous-cross-silo-knowledge-rec.vercel.app"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_debug_returns_allowed_origins(client):
    response = client.get("/cors-debug")

    assert response.status_code == 200
    body = response.json()
    assert body["frontend_url"]
    assert "https://autonomous-cross-silo-knowledge-rec.vercel.app" in body["allowed_origins"]


def test_ready_returns_readiness_checks(client):
    response = client.get("/system/ready")

    assert response.status_code == 200
    body = response.json()
    assert "ready" in body
    assert body["checks"]["storage"] == "ok"
