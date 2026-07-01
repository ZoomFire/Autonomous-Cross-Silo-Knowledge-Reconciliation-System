def test_auth_endpoints_are_disabled(client):
    for method, path in [
        ("post", "/auth/signup"),
        ("post", "/auth/login"),
        ("post", "/auth/logout"),
        ("get", "/auth/me"),
        ("get", "/auth/sessions"),
        ("get", "/auth/users"),
    ]:
        if method == "post":
            response = client.post(path, json={})
        else:
            response = client.get(path)

        assert response.status_code == 410
        assert "Authentication has been removed" in response.json()["message"]


def test_workspace_api_works_without_authorization_header(client):
    response = client.get("/workspaces")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
