def test_rag_index_endpoint_exists(client, admin_headers, workspace):
    response = client.post("/rag/index", json={"workspace_id": workspace["workspace_id"]}, headers=admin_headers)

    assert response.status_code == 200
    assert "status" in response.json()


def test_rag_search_returns_friendly_response(client, admin_headers, workspace):
    response = client.post(
        "/rag/search",
        json={"workspace_id": workspace["workspace_id"], "query": "authentication drift"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body.get("answer") or body.get("summary") or body.get("message") or body.get("evidence_summary")


def test_search_history_endpoint_exists(client, admin_headers, workspace):
    response = client.get(f"/rag/search-history?workspace_id={workspace['workspace_id']}", headers=admin_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
