import json
import urllib.request

from llm.grok_provider import GrokProvider


def _payload(workspace_id: str, runtime_api_key: str = "") -> dict:
    return {
        "workspace_id": workspace_id,
        "task_type": "contradiction_detection",
        "reasoning_mode": "hybrid",
        "provider": "grok",
        "runtime_api_key": runtime_api_key,
        "documentation": "Only admins can access billing exports.",
        "code": "@public_route('/billing/export')",
        "jira": "Billing exports must be admin-only.",
        "commit": "Temporarily exposed billing export route.",
        "logs": "200 OK for viewer on /billing/export",
        "database_config": "billing_export_requires_role=admin",
    }


def test_grok_reasoning_missing_key_falls_back_without_leaking_secret(client, admin_headers, workspace, monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    response = client.post("/llm/reason", headers=admin_headers, json=_payload(workspace["workspace_id"]))

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "grok"
    assert body["status"] == "completed"
    assert "Grok/xAI API key is required" in body["llm_output"]["error"]
    assert "runtime_api_key" not in str(body)


def test_grok_reasoning_rejects_empty_sources(client, admin_headers, workspace):
    response = client.post(
        "/llm/reason",
        headers=admin_headers,
        json={
            "workspace_id": workspace["workspace_id"],
            "task_type": "contradiction_detection",
            "reasoning_mode": "hybrid",
            "provider": "grok",
            "runtime_api_key": "xai-test-secret",
            "documentation": "",
            "code": "",
            "jira": "",
            "commit": "",
            "logs": "",
            "database_config": "",
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Add at least one source field before running Grok reasoning."
    assert "xai-test-secret" not in str(response.json())


def test_grok_provider_parses_structured_response(monkeypatch):
    captured = {}
    grok_body = {
        "drift_detected": True,
        "summary": "Code exposes an admin-only export route.",
        "extracted_claims": [{"source": "documentation", "claim": "Billing exports require admin access."}],
        "contradictions": [{"source_a": "documentation", "source_b": "code", "issue": "Code route is public."}],
        "drift_types": ["Documentation Drift", "Security Drift"],
        "severity": "High",
        "confidence": 0.91,
        "suggested_actions": ["Update access control", "Verify route permissions"],
    }
    api_body = {"choices": [{"message": {"content": json.dumps(grok_body)}}]}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(api_body).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        captured["authorization"] = request.headers.get("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    response = GrokProvider().generate(
        "fallback prompt",
        "contradiction_detection",
        {"runtime_api_key": "xai-test-secret", "input_context": {"documentation": "Admin only", "code": "public"}},
    )

    assert response["success"] is True
    assert response["provider"] == "grok"
    assert response["output"]["label"] == "contradiction"
    assert response["output"]["drift_type"] == "Documentation Drift, Security Drift"
    assert response["output"]["confidence"] == 0.91
    assert captured["authorization"] == "Bearer xai-test-secret"
    assert "xai-test-secret" not in str(response)
