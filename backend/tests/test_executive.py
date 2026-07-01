def test_executive_metrics_available_in_public_mode(client, workspace):
    response = client.get(f"/executive/metrics?workspace_id={workspace['workspace_id']}")
    assert response.status_code == 200
    assert response.json()["workspace_id"] == workspace["workspace_id"]


def test_roi_calculation_works(client, admin_headers, workspace):
    response = client.post("/executive/roi", headers=admin_headers, json={
        "workspace_id": workspace["workspace_id"],
        "assumptions": {"manual_review_hours_per_case": 2, "average_engineer_hourly_cost": 50},
    })
    assert response.status_code == 200
    assert "estimated_total_value" in response.json()
    assert response.json()["assumptions"]["manual_review_hours_per_case"] == 2
    assert "₹" in response.json()["roi_summary"]


def test_report_generation_works_in_public_mode(client, workspace):
    created = client.post("/executive/report", json={"workspace_id": workspace["workspace_id"], "assumptions": {}})
    assert created.status_code == 200
    assert created.json()["title"] == "DriftGuard AI Executive Report"


def test_demo_scenarios_endpoint_works(client, admin_headers):
    response = client.get("/demo/scenarios", headers=admin_headers)
    assert response.status_code == 200
    assert any(item["name"] == "Payment API Drift Demo" for item in response.json())


def test_demo_mode_enable_works_in_public_mode(client, workspace):
    response = client.post("/demo/enable", json={"workspace_id": workspace["workspace_id"], "scenario_name": "Payment API Drift Demo"})
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_reset_demo_works_in_public_mode(client, workspace):
    response = client.post("/demo/reset", json={"workspace_id": workspace["workspace_id"]})
    assert response.status_code == 200
    assert response.json()["enabled"] is False
