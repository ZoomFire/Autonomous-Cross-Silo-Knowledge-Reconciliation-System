def test_demo_readiness_requires_auth(client, workspace):
    response = client.get(f"/validation/demo-readiness?workspace_id={workspace['workspace_id']}")
    assert response.status_code == 401


def test_validation_run_endpoint_requires_permission(client, viewer_headers, workspace):
    response = client.post("/validation/run-full-system", headers=viewer_headers, json={"workspace_id": workspace["workspace_id"], "name": "Full Validation"})
    assert response.status_code == 403


def test_validation_runs_list_works(client, admin_headers, workspace):
    response = client.get(f"/validation/runs?workspace_id={workspace['workspace_id']}", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_baseline_comparison_handles_missing_ml_gracefully(client, admin_headers, workspace):
    response = client.post("/validation/baseline-comparison", headers=admin_headers, json={"workspace_id": workspace["workspace_id"], "dataset_id": "missing"})
    assert response.status_code == 200
    assert response.json()["baseline_results"][0]["mode"] == "rule_based"
    assert "No deployed ML model" in response.text


def test_research_report_export_returns_clear_response(client, admin_headers, workspace):
    created = client.post("/validation/run-full-system", headers=admin_headers, json={"workspace_id": workspace["workspace_id"], "name": "Full Validation"})
    assert created.status_code == 200
    validation_id = created.json()["validation_id"]
    response = client.get(f"/validation/runs/{validation_id}/research-report/export-markdown", headers=admin_headers)
    assert response.status_code == 200
    assert "DriftGuard AI Validation and Research Results Report" in response.text


def test_ablation_endpoint_requires_permission(client, viewer_headers, workspace):
    response = client.post("/validation/ablation-study", headers=viewer_headers, json={"workspace_id": workspace["workspace_id"], "dataset_id": "missing"})
    assert response.status_code == 403
