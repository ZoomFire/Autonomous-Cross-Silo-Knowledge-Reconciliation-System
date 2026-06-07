def test_agent_plan_works(client, admin_headers, workspace):
    response = client.post(
        "/agent/plan",
        json={"workspace_id": workspace["workspace_id"], "goal": "Review recent drift signals"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["plan"]


def test_agent_run_endpoint_is_permission_protected(client, viewer_headers, workspace):
    response = client.post(
        "/agent/run",
        json={"workspace_id": workspace["workspace_id"], "goal": "Run restricted workflow"},
        headers=viewer_headers,
    )

    assert response.status_code in {403, 404}


def test_agent_history_endpoint_works(client, admin_headers, workspace):
    response = client.get(f"/agent/runs?workspace_id={workspace['workspace_id']}", headers=admin_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
