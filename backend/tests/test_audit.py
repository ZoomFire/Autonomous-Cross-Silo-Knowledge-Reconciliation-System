def test_audit_summary_endpoint_requires_admin(client, viewer_headers):
    response = client.get("/audit/summary", headers=viewer_headers)

    assert response.status_code == 403


def test_audit_events_endpoint_requires_admin(client, viewer_headers):
    response = client.get("/audit/events", headers=viewer_headers)

    assert response.status_code == 403


def test_permission_denied_action_is_logged(client, admin_headers, viewer_headers):
    client.get("/auth/users", headers=viewer_headers)

    response = client.get("/audit/events?action=permission_denied", headers=admin_headers)

    assert response.status_code == 200
    assert any(event.get("action") == "permission_denied" for event in response.json())
