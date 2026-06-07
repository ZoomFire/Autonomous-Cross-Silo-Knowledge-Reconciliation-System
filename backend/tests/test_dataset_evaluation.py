import io
import json


def test_sample_dataset_loads(client, admin_headers):
    response = client.get("/dataset/sample", headers=admin_headers)

    assert response.status_code == 200
    assert len(response.json()) > 0


def test_sample_evaluation_runs(client, admin_headers, workspace):
    response = client.post(f"/dataset/evaluate?workspace_id={workspace['workspace_id']}", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_cases"] > 0
    assert "accuracy" in body


def test_invalid_uploaded_dataset_returns_error(client, admin_headers):
    response = client.post(
        "/dataset/upload-preview",
        files={"file": ("bad.json", io.BytesIO(b'{"not": "a list"}'), "application/json")},
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_valid_uploaded_dataset_preview_works(client, admin_headers):
    sample = client.get("/dataset/sample", headers=admin_headers).json()
    response = client.post(
        "/dataset/upload-preview",
        files={"file": ("sample.json", io.BytesIO(json.dumps(sample[:1]).encode("utf-8")), "application/json")},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()[0]["case_id"] == sample[0]["case_id"]
