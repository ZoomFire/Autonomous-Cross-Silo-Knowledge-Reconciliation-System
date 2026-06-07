def test_privacy_settings_endpoint_admin_only(client, viewer_headers, admin_headers, workspace):
    url = f"/privacy/settings?workspace_id={workspace['workspace_id']}"

    assert client.get(url, headers=viewer_headers).status_code == 403
    response = client.get(url, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["privacy_mode_enabled"] is True


def test_workspace_export_endpoint_admin_only(client, viewer_headers, admin_headers, workspace):
    url = f"/privacy/workspace/{workspace['workspace_id']}/export"

    assert client.get(url, headers=viewer_headers).status_code == 403
    response = client.get(url, headers=admin_headers)
    assert response.status_code == 200
    assert "workspace" in response.json()


def test_delete_request_creation_works_for_admin(client, admin_headers, workspace):
    response = client.post(f"/privacy/workspace/{workspace['workspace_id']}/delete-request", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_non_admin_delete_request_denied(client, viewer_headers, workspace):
    response = client.post(f"/privacy/workspace/{workspace['workspace_id']}/delete-request", headers=viewer_headers)

    assert response.status_code == 403


def test_delete_requests_can_be_listed_and_approved(client, admin_headers, workspace):
    created = client.post(f"/privacy/workspace/{workspace['workspace_id']}/delete-request", headers=admin_headers).json()
    listed = client.get("/privacy/delete-requests", headers=admin_headers)
    approved = client.post(f"/privacy/delete-requests/{created['delete_request_id']}/approve", headers=admin_headers)

    assert listed.status_code == 200
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
