from uuid import uuid4

from auth_store import create_session, create_user


def _headers_for_role(role: str) -> dict:
    suffix = uuid4().hex
    user = create_user(f"ML {role}", f"ml-{role}-{suffix}@example.com", "Passw0rd!", role)
    session = create_session(user["user_id"])
    return {"Authorization": f"Bearer {session['token']}"}


def test_training_endpoint_reaches_runtime_validation_without_login(client, workspace):
    response = client.post(
        "/ml/experiments/train",
        json={"workspace_id": workspace["workspace_id"], "task_type": "label_classification", "model_type": "logistic_regression"},
    )

    assert response.status_code == 400
    assert "No training examples found" in response.json()["message"]


def test_leaderboard_works_without_login(client, workspace):
    response = client.get(f"/ml/leaderboard?workspace_id={workspace['workspace_id']}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_predict_returns_fallback_when_no_model_deployed(client, admin_headers, workspace):
    response = client.post(
        "/ml/predict",
        json={"workspace_id": workspace["workspace_id"], "task_type": "label_classification", "input_context": {"documentation": "Endpoint is public."}},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["fallback_required"] is True


def test_invalid_task_type_rejected(client, admin_headers, workspace):
    response = client.post(
        "/ml/experiments/train",
        json={"workspace_id": workspace["workspace_id"], "task_type": "bad_task", "model_type": "logistic_regression"},
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_invalid_model_type_rejected(client, admin_headers, workspace):
    response = client.post(
        "/ml/experiments/train",
        json={"workspace_id": workspace["workspace_id"], "task_type": "label_classification", "model_type": "transformer"},
        headers=admin_headers,
    )

    assert response.status_code == 400
