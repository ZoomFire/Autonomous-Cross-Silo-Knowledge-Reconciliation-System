def test_authenticated_user_can_create_workspace(client, admin_headers):
    response = client.post(
        "/workspaces",
        json={"name": "QA Workspace", "description": "Created by backend tests."},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "QA Workspace"
    assert body["workspace_id"]


def test_workspace_list_works(client, admin_headers, workspace):
    response = client.get("/workspaces", headers=admin_headers)

    assert response.status_code == 200
    assert any(item["workspace_id"] == workspace["workspace_id"] for item in response.json())


def test_workspace_detail_works(client, admin_headers, workspace):
    response = client.get(f"/workspaces/{workspace['workspace_id']}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["workspace_id"] == workspace["workspace_id"]
