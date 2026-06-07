from auth_store import create_session, create_user
from workspace_store import add_user_to_workspace
from uuid import uuid4


def _payload(workspace_id: str) -> dict:
    return {
        "workspace_id": workspace_id,
        "title": "Critical label drift",
        "description": "Classifier labels no longer match reviewed cases.",
        "severity": "Critical",
        "source_type": "manual",
    }


def test_create_incident_requires_auth(client, workspace):
    response = client.post("/incidents", json=_payload(workspace["workspace_id"]))
    assert response.status_code == 401


def test_list_incidents_works(client, admin_headers, workspace):
    created = client.post("/incidents", headers=admin_headers, json=_payload(workspace["workspace_id"]))
    assert created.status_code == 200

    response = client.get(f"/incidents?workspace_id={workspace['workspace_id']}", headers=admin_headers)
    assert response.status_code == 200
    assert any(item["incident_id"] == created.json()["incident_id"] for item in response.json())


def test_update_status_works(client, admin_headers, workspace):
    created = client.post("/incidents", headers=admin_headers, json=_payload(workspace["workspace_id"])).json()
    response = client.put(f"/incidents/{created['incident_id']}/status", headers=admin_headers, json={"status": "resolved"})
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["resolved_at"]


def test_add_comment_works(client, admin_headers, workspace):
    created = client.post("/incidents", headers=admin_headers, json=_payload(workspace["workspace_id"])).json()
    response = client.post(f"/incidents/{created['incident_id']}/comments", headers=admin_headers, json={"comment_text": "Assigned to review owner."})
    assert response.status_code == 200
    assert response.json()["comment_text"] == "Assigned to review owner."

    detail = client.get(f"/incidents/{created['incident_id']}", headers=admin_headers)
    assert detail.status_code == 200
    assert len(detail.json()["comments"]) == 1


def test_webhook_creation_requires_engineer_or_admin(client, admin_headers, viewer_headers, workspace):
    payload = {"workspace_id": workspace["workspace_id"], "name": "Ops webhook", "url": "https://example.com/webhook", "event_types": ["incident.created"], "enabled": False}
    denied = client.post("/incidents/webhooks", headers=viewer_headers, json=payload)
    assert denied.status_code == 403

    created = client.post("/incidents/webhooks", headers=admin_headers, json=payload)
    assert created.status_code == 200
    assert created.json()["name"] == "Ops webhook"


def test_escalation_check_requires_permission(client, admin_headers, viewer_headers, workspace):
    denied = client.post("/incidents/escalations/check", headers=viewer_headers, json={"workspace_id": workspace["workspace_id"]})
    assert denied.status_code == 403

    rule = client.post("/incidents/escalation-rules", headers=admin_headers, json={
        "workspace_id": workspace["workspace_id"],
        "name": "Critical immediate",
        "severity": "Critical",
        "status_filter": "open",
        "escalate_after_minutes": 0,
        "webhook_enabled": False,
    })
    assert rule.status_code == 200
    created = client.post("/incidents", headers=admin_headers, json=_payload(workspace["workspace_id"]))
    assert created.status_code == 200

    checked = client.post("/incidents/escalations/check", headers=admin_headers, json={"workspace_id": workspace["workspace_id"]})
    assert checked.status_code == 200
    assert checked.json()["escalated_count"] >= 1


def test_incident_summary_works(client, admin_headers, workspace):
    client.post("/incidents", headers=admin_headers, json=_payload(workspace["workspace_id"]))
    response = client.get(f"/incidents/summary?workspace_id={workspace['workspace_id']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert "by_status" in response.json()


def test_export_markdown_works(client, admin_headers, workspace):
    created = client.post("/incidents", headers=admin_headers, json=_payload(workspace["workspace_id"])).json()
    response = client.get(f"/incidents/{created['incident_id']}/export-markdown", headers=admin_headers)
    assert response.status_code == 200
    assert "Incident: Critical label drift" in response.text


def test_engineer_can_create_webhook(client, workspace):
    engineer = create_user("Incident Engineer", f"incident-engineer-{uuid4().hex}@example.com", "Passw0rd!", "engineer")
    add_user_to_workspace(workspace["workspace_id"], engineer["user_id"], "engineer")
    headers = {"Authorization": f"Bearer {create_session(engineer['user_id'])['token']}"}
    response = client.post("/incidents/webhooks", headers=headers, json={
        "workspace_id": workspace["workspace_id"],
        "name": "Engineer webhook",
        "url": "https://example.com/engineer",
        "enabled": False,
    })
    assert response.status_code == 200
