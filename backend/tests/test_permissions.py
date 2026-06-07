def test_viewer_cannot_run_restricted_action(client, viewer_headers):
    response = client.post(
        "/workspaces",
        json={"name": "Viewer Workspace", "description": "Should not be created."},
        headers=viewer_headers,
    )

    assert response.status_code == 403


def test_admin_can_access_admin_endpoint(client, admin_headers):
    response = client.get("/auth/users", headers=admin_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_permission_denied_returns_error_response(client, viewer_headers):
    response = client.get("/auth/users", headers=viewer_headers)

    assert response.status_code == 403
    assert response.json().get("error") is True
