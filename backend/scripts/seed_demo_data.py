from uuid import uuid4

from auth_store import create_user, ensure_auth_dirs, get_user, list_users
from connector_store import create_connector, create_source, ensure_connector_dirs, list_sources, utc_now
from database import init_db
from rag.search_service import index_sources_for_workspace
from workspace_store import create_workspace, ensure_workspace_dir, list_workspaces


DEMO_EMAIL = "admin@driftguard.local"
DEMO_PASSWORD = "admin1234"

DEMO_SOURCES = [
    ("documentation", "Refund API Documentation", "The /api/payment/refund endpoint is public and available for all customers."),
    ("code", "Refund API Code", "@internal_only def refund_payment(): return process_refund()"),
    ("jira", "Refund Jira Ticket", "Refund feature should be customer-facing and ready for production."),
    ("logs", "Refund Production Logs", "403 Forbidden when customer tried to access /api/payment/refund"),
    ("database_config", "Refund Config", "refund_endpoint_access=internal"),
]


def _demo_user():
    existing = next((user for user in list_users() if user.get("email") == DEMO_EMAIL), None)
    if existing:
        print(f"Demo admin already exists: {DEMO_EMAIL}")
        return existing
    user = create_user("Demo Admin", DEMO_EMAIL, DEMO_PASSWORD, "admin")
    print(f"Created demo admin: {DEMO_EMAIL}")
    return user


def _demo_workspace(user_id: str):
    existing = next((workspace for workspace in list_workspaces() if workspace.get("name") == "Demo Workspace"), None)
    if existing:
        print("Demo Workspace already exists.")
        return existing
    workspace = create_workspace("Demo Workspace", "Seeded workspace for DriftGuard demos.", user_id, "admin")
    print("Created Demo Workspace.")
    return workspace


def _seed_sources(workspace_id: str, user_id: str):
    existing = list_sources(workspace_id)
    if existing:
        print(f"Workspace already has {len(existing)} imported source(s); skipping source seed.")
        return
    now = utc_now()
    connector = create_connector({
        "connector_id": str(uuid4()),
        "workspace_id": workspace_id,
        "name": "Demo Seed Sources",
        "connector_type": "manual_upload",
        "status": "active",
        "config": {"seeded": True},
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
        "last_sync_at": now,
    })
    for source_type, name, content in DEMO_SOURCES:
        create_source({
            "source_id": str(uuid4()),
            "workspace_id": workspace_id,
            "connector_id": connector["connector_id"],
            "source_type": source_type,
            "source_name": name,
            "source_path": f"demo/{source_type}.txt",
            "source_url": "",
            "content_text": content,
            "content_hash": "",
            "metadata": {"seeded": True},
            "created_at": now,
            "updated_at": now,
        })
    print("Created demo imported sources.")
    try:
        summary = index_sources_for_workspace(workspace_id)
        print(f"Rebuilt search index: {summary}")
    except Exception as exc:
        print(f"Demo sources were created, but indexing failed: {exc}")


def main():
    init_db()
    ensure_auth_dirs()
    ensure_workspace_dir()
    ensure_connector_dirs()
    user = _demo_user()
    workspace = _demo_workspace(user["user_id"])
    _seed_sources(workspace["workspace_id"], user["user_id"])
    print("")
    print("Demo login:")
    print(f"  Email: {DEMO_EMAIL}")
    print(f"  Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
