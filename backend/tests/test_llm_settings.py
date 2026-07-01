def test_saving_same_provider_updates_existing_settings(client, workspace):
    first = client.post("/llm/settings", json={
        "workspace_id": workspace["workspace_id"],
        "provider": "local",
        "model_name": "local-rule-engine",
        "reasoning_mode": "local_only",
        "enabled": True,
    })
    assert first.status_code == 200

    second = client.post("/llm/settings", json={
        "workspace_id": workspace["workspace_id"],
        "provider": "local",
        "model_name": "local-rule-engine-v2",
        "reasoning_mode": "hybrid",
        "enabled": True,
    })
    assert second.status_code == 200

    listed = client.get(f"/llm/settings?workspace_id={workspace['workspace_id']}")
    assert listed.status_code == 200
    local_settings = [item for item in listed.json() if item["provider"] == "local"]
    assert len(local_settings) == 1
    assert local_settings[0]["settings_id"] == first.json()["settings_id"]
    assert local_settings[0]["model_name"] == "local-rule-engine-v2"
    assert local_settings[0]["reasoning_mode"] == "hybrid"
