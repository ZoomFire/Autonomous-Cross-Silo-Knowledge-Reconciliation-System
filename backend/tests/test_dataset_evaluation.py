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


def test_snli_jsonl_upload_preview_converts_labels_and_skips_invalid_gold_label(client, admin_headers):
    records = [
        {"sentence1": "A person is outdoors.", "sentence2": "A person is outside.", "gold_label": "entailment"},
        {"sentence1": "A dog is running.", "sentence2": "No animal is moving.", "gold_label": "contradiction"},
        {"sentence1": "A child is playing.", "sentence2": "A child is near a park.", "gold_label": "neutral"},
        {"sentence1": "Ignored premise.", "sentence2": "Ignored hypothesis.", "gold_label": "-"},
    ]
    payload = "\n".join(json.dumps(record) for record in records).encode("utf-8")

    response = client.post(
        "/dataset/upload-preview",
        files={"file": ("snli.jsonl", io.BytesIO(payload), "application/jsonl")},
        headers=admin_headers,
    )

    assert response.status_code == 200
    cases = response.json()
    assert [case["expected_label"] for case in cases] == ["no_drift", "contradiction", "manual_review"]
    assert cases[0]["documentation"] == "A person is outdoors."
    assert cases[0]["code"] == "A person is outside."
    assert cases[0]["jira"] == "A person is outside."


def test_snli_jsonl_upload_preview_limits_cases(client, admin_headers):
    payload = "\n".join(
        json.dumps({"sentence1": f"Premise {index}", "sentence2": f"Hypothesis {index}", "gold_label": "entailment"})
        for index in range(150)
    ).encode("utf-8")

    response = client.post(
        "/dataset/upload-preview",
        files={"file": ("snli-large.jsonl", io.BytesIO(payload), "application/jsonl")},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 100


def test_invalid_jsonl_upload_returns_clear_error(client, admin_headers):
    response = client.post(
        "/dataset/upload-preview",
        files={"file": ("bad.jsonl", io.BytesIO(b'{"sentence1":"A"}\nnot json\n'), "application/jsonl")},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert "valid JSONL" in response.json()["message"]
