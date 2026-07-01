from uuid import uuid4

from database.repositories import DatasetRepository, ValidationRunRepository


def _create_validation_dataset(workspace_id: str) -> str:
    dataset_id = str(uuid4())
    cases = [
        {
            "case_id": "case-1",
            "title": "Payment API response drift",
            "documentation": "Payment API returns approved for successful charges.",
            "code": "Payment API returns declined for successful charges.",
            "jira": "Update payment response handling.",
            "commit": "Changed charge response mapping.",
            "logs": "Declined responses increased after release.",
            "database_config": "payments.status stores declined.",
            "expected_label": "contradiction",
            "expected_drift_type": "Logical Contradiction",
            "expected_severity": "High",
        }
    ]
    DatasetRepository.create({
        "dataset_id": dataset_id,
        "workspace_id": workspace_id,
        "name": "Validation Test Dataset",
        "filename": "validation-test.json",
        "description": "Dataset used by validation tests.",
        "version": "1.0",
        "total_cases": len(cases),
        "quality_score": 90,
    }, cases)
    return dataset_id


def test_demo_readiness_requires_auth(client, workspace):
    response = client.get(f"/validation/demo-readiness?workspace_id={workspace['workspace_id']}")
    assert response.status_code == 200
    assert "checks" in response.json()


def test_validation_run_endpoint_requires_permission(client, viewer_headers, workspace):
    response = client.post("/validation/run-full-system", headers=viewer_headers, json={"workspace_id": workspace["workspace_id"], "name": "Full Validation"})
    assert response.status_code == 200
    assert response.json()["workspace_id"] == workspace["workspace_id"]


def test_real_dataset_validation_persists_summary_metrics_and_chart_data(client, workspace):
    dataset_id = _create_validation_dataset(workspace["workspace_id"])
    response = client.post("/validation/run-real-dataset", json={
        "workspace_id": workspace["workspace_id"],
        "dataset_id": dataset_id,
        "name": "Real Dataset Validation",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["validation_type"] == "real_dataset"
    assert body["summary"]["drift_cases"] >= 1
    assert body["metrics"]["evaluation"]["total_cases"] == 1
    assert "accuracy_bar_chart" in body["chart_data"]


def test_demo_scenario_validation_persists_demo_type_and_scenario(client, workspace):
    _create_validation_dataset(workspace["workspace_id"])
    response = client.post("/validation/run-demo-scenario", json={
        "workspace_id": workspace["workspace_id"],
        "scenario_name": "Payment API Drift Demo",
    })
    assert response.status_code == 200
    body = response.json()
    saved = ValidationRunRepository.get_by_id(body["validation_id"])
    assert saved["validation_type"] == "demo_scenario"
    assert saved["scenario_name"] == "Payment API Drift Demo"


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
    assert response.status_code == 200
    assert response.json()["ablation_results"]
