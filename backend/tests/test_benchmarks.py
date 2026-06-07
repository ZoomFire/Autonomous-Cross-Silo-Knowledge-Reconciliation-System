import io


def test_benchmark_registry_returns_supported_datasets(client, admin_headers):
    response = client.get("/benchmarks/registry", headers=admin_headers)

    assert response.status_code == 200
    assert {"cosqa", "snli", "commitpack", "spider"}.issubset(response.json().keys())


def test_invalid_benchmark_dataset_type_rejected(client, admin_headers, workspace):
    file_data = {"file": ("sample.json", io.BytesIO(b"[]"), "application/json")}
    response = client.post(
        "/benchmarks/upload",
        data={"workspace_id": workspace["workspace_id"], "dataset_type": "unknown", "name": "Bad Dataset"},
        files=file_data,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_benchmark_upload_requires_permission(client, viewer_headers, workspace):
    file_data = {"file": ("snli.jsonl", io.BytesIO(b'{"sentence1":"A","sentence2":"B","gold_label":"neutral"}\n'), "application/json")}
    response = client.post(
        "/benchmarks/upload",
        data={"workspace_id": workspace["workspace_id"], "dataset_type": "snli", "name": "SNLI Sample"},
        files=file_data,
        headers=viewer_headers,
    )

    assert response.status_code == 403


def test_quality_endpoint_requires_existing_benchmark(client, admin_headers):
    response = client.get("/benchmarks/missing-benchmark/quality", headers=admin_headers)

    assert response.status_code == 404


def test_training_exports_endpoint_requires_auth(client, workspace):
    response = client.get(f"/benchmarks/training/exports?workspace_id={workspace['workspace_id']}")

    assert response.status_code == 401
