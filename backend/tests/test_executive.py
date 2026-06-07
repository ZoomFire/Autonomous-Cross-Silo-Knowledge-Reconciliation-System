from uuid import uuid4

from auth_store import create_session, create_user
from workspace_store import add_user_to_workspace


def _engineer_headers(workspace_id: str) -> dict:
    engineer = create_user("Executive Engineer", f"exec-engineer-{uuid4().hex}@example.com", "Passw0rd!", "engineer")
    add_user_to_workspace(workspace_id, engineer["user_id"], "engineer")
    return {"Authorization": f"Bearer {create_session(engineer['user_id'])['token']}"}


def test_executive_metrics_requires_auth(client, workspace):
    response = client.get(f"/executive/metrics?workspace_id={workspace['workspace_id']}")
    assert response.status_code == 401


def test_roi_calculation_works(client, admin_headers, workspace):
    response = client.post("/executive/roi", headers=admin_headers, json={
        "workspace_id": workspace["workspace_id"],
        "assumptions": {"manual_review_hours_per_case": 2, "average_engineer_hourly_cost": 50},
    })
    assert response.status_code == 200
    assert "estimated_total_value" in response.json()
    assert response.json()["assumptions"]["manual_review_hours_per_case"] == 2


def test_report_generation_requires_proper_permission(client, viewer_headers, admin_headers, workspace):
    denied = client.post("/executive/report", headers=viewer_headers, json={"workspace_id": workspace["workspace_id"], "assumptions": {}})
    assert denied.status_code == 403

    created = client.post("/executive/report", headers=admin_headers, json={"workspace_id": workspace["workspace_id"], "assumptions": {}})
    assert created.status_code == 200
    assert created.json()["title"] == "DriftGuard AI Executive Report"


def test_demo_scenarios_endpoint_works(client, admin_headers):
    response = client.get("/demo/scenarios", headers=admin_headers)
    assert response.status_code == 200
    assert any(item["name"] == "Payment API Drift Demo" for item in response.json())


def test_demo_mode_enable_requires_engineer_or_admin(client, viewer_headers, workspace):
    denied = client.post("/demo/enable", headers=viewer_headers, json={"workspace_id": workspace["workspace_id"], "scenario_name": "Payment API Drift Demo"})
    assert denied.status_code == 403

    engineer_headers = _engineer_headers(workspace["workspace_id"])
    response = client.post("/demo/enable", headers=engineer_headers, json={"workspace_id": workspace["workspace_id"], "scenario_name": "Payment API Drift Demo"})
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_reset_demo_requires_admin(client, viewer_headers, admin_headers, workspace):
    denied = client.post("/demo/reset", headers=viewer_headers, json={"workspace_id": workspace["workspace_id"]})
    assert denied.status_code == 403

    response = client.post("/demo/reset", headers=admin_headers, json={"workspace_id": workspace["workspace_id"]})
    assert response.status_code == 200
    assert response.json()["enabled"] is False
