def test_monitoring_rules_endpoint_exists(client, admin_headers, workspace):
    response = client.get(f"/monitoring/rules?workspace_id={workspace['workspace_id']}", headers=admin_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_alerts_endpoint_exists(client, admin_headers, workspace):
    response = client.get(f"/monitoring/alerts?workspace_id={workspace['workspace_id']}", headers=admin_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_non_authenticated_monitoring_request_is_rejected(client, workspace):
    response = client.get(f"/monitoring/rules?workspace_id={workspace['workspace_id']}")

    assert response.status_code == 401
