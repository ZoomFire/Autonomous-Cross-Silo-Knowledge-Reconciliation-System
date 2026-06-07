def test_signup_endpoint_exists(client):
    response = client.post("/auth/signup", json={})

    assert response.status_code in {400, 401, 422}


def test_login_endpoint_exists(client):
    response = client.post("/auth/login", json={})

    assert response.status_code == 401


def test_invalid_login_returns_error_response(client):
    response = client.post("/auth/login", json={"email": "missing@example.com", "password": "wrong"})

    assert response.status_code == 401
    body = response.json()
    assert body.get("error") is True or "detail" in body
