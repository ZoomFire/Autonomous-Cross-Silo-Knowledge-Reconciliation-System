import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


os.environ["APP_ENV"] = "test"
os.environ["USE_DATABASE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./storage/test_driftguard.db"
os.environ["DEFAULT_REASONING_MODE"] = "local_only"

from main import app  # noqa: E402
from auth_store import create_session, create_user  # noqa: E402
from workspace_store import create_workspace  # noqa: E402
from rate_limiter import reset_rate_limits  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    db_path = Path(__file__).resolve().parents[1] / "storage" / "test_driftguard.db"
    if db_path.exists():
        db_path.unlink()
    yield


@pytest.fixture()
def client():
    reset_rate_limits()
    with TestClient(app) as test_client:
        yield test_client


def _create_test_user(role: str = "admin") -> dict:
    suffix = uuid4().hex
    return create_user(
        name=f"Test {role.title()}",
        email=f"{role}-{suffix}@example.com",
        password="Passw0rd!",
        role=role,
    )


def headers_for_user(user: dict) -> dict:
    session = create_session(user["user_id"])
    return {"Authorization": f"Bearer {session['token']}"}


@pytest.fixture()
def admin_user(client):
    return _create_test_user("admin")


@pytest.fixture()
def admin_headers(admin_user):
    return headers_for_user(admin_user)


@pytest.fixture()
def viewer_user(client):
    return _create_test_user("viewer")


@pytest.fixture()
def viewer_headers(viewer_user):
    return headers_for_user(viewer_user)


@pytest.fixture()
def workspace(admin_user):
    return create_workspace(f"QA Workspace {uuid4().hex[:8]}", "Workspace for automated tests.", admin_user["user_id"], "admin")
