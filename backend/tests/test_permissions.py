def test_workspace_creation_works_with_stale_viewer_header(client, viewer_headers):
    response = client.post(
        "/workspaces",
        json={"name": "Public Workspace", "description": "Created by public admin mode."},
        headers=viewer_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Public Workspace"


def test_auth_user_management_endpoint_is_disabled(client, admin_headers):
    response = client.get("/auth/users", headers=admin_headers)

    assert response.status_code == 410


def test_disabled_auth_endpoint_returns_error_response(client, viewer_headers):
    response = client.get("/auth/users", headers=viewer_headers)

    assert response.status_code == 410
    assert response.json().get("error") is True
