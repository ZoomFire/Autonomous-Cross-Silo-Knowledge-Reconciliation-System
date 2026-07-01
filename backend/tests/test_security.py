def test_signup_endpoint_is_disabled(client):
    response = client.post("/auth/signup", json={"name": "Weak", "email": "weak@example.com", "password": "short1"})

    assert response.status_code == 410


def test_login_endpoint_is_disabled(client):
    response = client.post("/auth/login", json={"email": "login-user@example.com", "password": "wrong-password"})

    assert response.status_code == 410


def test_repeated_login_attempts_remain_disabled(client):
    for _ in range(5):
        client.post("/auth/login", json={"email": "lock-user@example.com", "password": "wrong-password"})
    response = client.post("/auth/login", json={"email": "lock-user@example.com", "password": "Passw0rd!"})

    assert response.status_code == 410


def test_security_summary_works_without_login(client):
    response = client.get("/security/summary")

    assert response.status_code == 200
    assert "security_risk_level" in response.json()


def test_auth_login_rate_limit_is_removed_with_auth(client):
    for _ in range(10):
        client.post("/auth/login", json={"email": "rate-limit@example.com", "password": "wrong"})
    response = client.post("/auth/login", json={"email": "rate-limit@example.com", "password": "wrong"})

    assert response.status_code == 410


def test_session_list_and_revoke_are_disabled(client, admin_headers):
    sessions = client.get("/auth/sessions", headers=admin_headers)
    assert sessions.status_code == 410

    revoked = client.delete("/auth/sessions/removed-session", headers=admin_headers)
    assert revoked.status_code == 410
