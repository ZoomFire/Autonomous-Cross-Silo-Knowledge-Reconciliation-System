from uuid import uuid4

from auth_store import create_session, create_user
from workspace_store import add_user_to_workspace


def _incident_payload(workspace_id: str) -> dict:
    return {
        "workspace_id": workspace_id,
        "title": "Critical workflow drift",
        "description": "Docs and implementation diverged for checkout flow.",
        "severity": "Critical",
    }


def _integration_payload(workspace_id: str) -> dict:
    return {
        "workspace_id": workspace_id,
        "name": "Demo Jira Mock",
        "integration_type": "jira",
        "mode": "mock",
        "enabled": True,
        "config": {"project_key": "DG", "api_token": "super-secret-token"},
        "secret": "webhook-secret",
    }


def test_create_mock_integration_requires_engineer_or_admin(client, admin_headers, viewer_headers, workspace):
    denied = client.post("/integrations", headers=viewer_headers, json=_integration_payload(workspace["workspace_id"]))
    assert denied.status_code == 403

    created = client.post("/integrations", headers=admin_headers, json=_integration_payload(workspace["workspace_id"]))
    assert created.status_code == 200
    assert created.json()["integration_type"] == "jira"
    assert created.json()["mode"] == "mock"


def test_engineer_can_create_integration(client, workspace):
    engineer = create_user("Integration Engineer", f"integration-engineer-{uuid4().hex}@example.com", "Passw0rd!", "engineer")
    add_user_to_workspace(workspace["workspace_id"], engineer["user_id"], "engineer")
    headers = {"Authorization": f"Bearer {create_session(engineer['user_id'])['token']}"}
    response = client.post("/integrations", headers=headers, json=_integration_payload(workspace["workspace_id"]))
    assert response.status_code == 200


def test_list_integrations_works(client, admin_headers, workspace):
    client.post("/integrations", headers=admin_headers, json=_integration_payload(workspace["workspace_id"]))
    response = client.get(f"/integrations?workspace_id={workspace['workspace_id']}", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_test_mock_integration_works(client, admin_headers, workspace):
    integration = client.post("/integrations", headers=admin_headers, json=_integration_payload(workspace["workspace_id"])).json()
    response = client.post(f"/integrations/{integration['integration_id']}/test", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["result"]["success"] is True
    assert response.json()["integration"]["last_health_status"] == "healthy"


def test_sync_incident_to_mock_jira_creates_mock_item(client, admin_headers, workspace):
    integration = client.post("/integrations", headers=admin_headers, json=_integration_payload(workspace["workspace_id"])).json()
    incident = client.post("/incidents", headers=admin_headers, json=_incident_payload(workspace["workspace_id"])).json()

    response = client.post(f"/integrations/{integration['integration_id']}/incident/{incident['incident_id']}/sync", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["result"]["success"] is True
    assert response.json()["linked_resource"]["external_type"] == "jira_ticket"

    mock_items = client.get(f"/integrations/mock-items?workspace_id={workspace['workspace_id']}", headers=admin_headers)
    assert mock_items.status_code == 200
    assert any(item["source_id"] == incident["incident_id"] for item in mock_items.json())


def test_sync_records_are_created(client, admin_headers, workspace):
    integration = client.post("/integrations", headers=admin_headers, json=_integration_payload(workspace["workspace_id"])).json()
    incident = client.post("/incidents", headers=admin_headers, json=_incident_payload(workspace["workspace_id"])).json()
    client.post(f"/integrations/{integration['integration_id']}/incident/{incident['incident_id']}/sync", headers=admin_headers)

    records = client.get(f"/integrations/sync-records?workspace_id={workspace['workspace_id']}", headers=admin_headers)
    assert records.status_code == 200
    assert any(record["source_id"] == incident["incident_id"] and record["status"] == "success" for record in records.json())


def test_secrets_are_masked_in_integration_response(client, admin_headers, workspace):
    response = client.post("/integrations", headers=admin_headers, json=_integration_payload(workspace["workspace_id"]))
    assert response.status_code == 200
    body = response.json()
    assert body["config"]["api_token"] != "super-secret-token"
    assert "super-secret-token" not in str(body)


def test_viewer_cannot_create_integration(client, viewer_headers, workspace):
    response = client.post("/integrations", headers=viewer_headers, json=_integration_payload(workspace["workspace_id"]))
    assert response.status_code == 403
