from auth_store import create_user


def test_weak_password_rejected(client):
    response = client.post("/auth/signup", json={"name": "Weak", "email": "weak@example.com", "password": "short1"})

    assert response.status_code in {400, 401}


def test_failed_login_returns_error(client):
    user = create_user("Login User", "login-user@example.com", "Passw0rd!", "viewer")
    response = client.post("/auth/login", json={"email": user["email"], "password": "wrong-password"})

    assert response.status_code == 401


def test_repeated_failed_login_locks_account(client):
    user = create_user("Lock User", "lock-user@example.com", "Passw0rd!", "viewer")

    for _ in range(5):
        client.post("/auth/login", json={"email": user["email"], "password": "wrong-password"})
    response = client.post("/auth/login", json={"email": user["email"], "password": "Passw0rd!"})

    assert response.status_code == 403


def test_security_summary_admin_only(client, viewer_headers, admin_headers):
    assert client.get("/security/summary", headers=viewer_headers).status_code == 403
    response = client.get("/security/summary", headers=admin_headers)

    assert response.status_code == 200
    assert "security_risk_level" in response.json()


def test_rate_limit_returns_429(client):
    for _ in range(10):
        client.post("/auth/login", json={"email": "rate-limit@example.com", "password": "wrong"})
    response = client.post("/auth/login", json={"email": "rate-limit@example.com", "password": "wrong"})

    assert response.status_code == 429


def test_session_list_and_revoke(client, admin_headers):
    sessions = client.get("/auth/sessions", headers=admin_headers)
    assert sessions.status_code == 200
    session_id = sessions.json()[0]["session_id"]

    revoked = client.delete(f"/auth/sessions/{session_id}", headers=admin_headers)
    assert revoked.status_code == 200
