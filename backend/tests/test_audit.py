def test_audit_summary_endpoint_is_available_without_login(client):
    response = client.get("/audit/summary")

    assert response.status_code == 200
    assert "total_events" in response.json()


def test_audit_events_endpoint_is_available_without_login(client):
    response = client.get("/audit/events")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_auth_user_management_endpoint_is_removed(client):
    response = client.get("/auth/users")

    assert response.status_code == 410
