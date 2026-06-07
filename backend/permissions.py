from fastapi import Header, HTTPException

from audit_store import log_audit_event
from auth_store import get_current_user
from workspace_store import get_member_role, get_workspace, is_workspace_member


ROLE_PERMISSIONS = {
    "admin": {
        "manage_users",
        "create_workspace",
        "save_dataset",
        "delete_dataset",
        "run_evaluation",
        "create_monitoring_rule",
        "delete_monitoring_rule",
        "manage_alerts",
        "add_feedback",
        "export_reports",
        "view_dashboard",
        "delete_history",
        "manage_connectors",
        "sync_connectors",
        "generate_connector_datasets",
        "delete_connectors",
        "view_connectors",
        "view_benchmarks",
        "manage_benchmarks",
        "export_training_data",
        "delete_benchmarks",
        "view_ml_models",
        "train_ml_models",
        "deploy_ml_models",
        "delete_ml_experiments",
        "view_incidents",
        "manage_incidents",
        "manage_incident_automation",
        "delete_incidents",
        "view_integrations",
        "manage_integrations",
        "delete_integrations",
        "view_executive",
        "generate_executive_reports",
        "manage_demo_mode",
        "reset_demo_data",
        "view_validation",
        "run_validation",
        "delete_validation",
    },
    "engineer": {
        "save_dataset",
        "run_evaluation",
        "create_monitoring_rule",
        "manage_alerts",
        "export_reports",
        "view_dashboard",
        "manage_connectors",
        "sync_connectors",
        "generate_connector_datasets",
        "view_connectors",
        "view_benchmarks",
        "manage_benchmarks",
        "export_training_data",
        "view_ml_models",
        "train_ml_models",
        "deploy_ml_models",
        "view_incidents",
        "manage_incidents",
        "manage_incident_automation",
        "view_integrations",
        "manage_integrations",
        "view_executive",
        "generate_executive_reports",
        "manage_demo_mode",
        "view_validation",
        "run_validation",
    },
    "reviewer": {
        "add_feedback",
        "export_reports",
        "view_dashboard",
        "view_connectors",
        "view_benchmarks",
        "view_ml_models",
        "view_incidents",
        "view_integrations",
        "manage_incidents",
        "view_executive",
        "generate_executive_reports",
        "view_validation",
        "run_validation",
    },
    "viewer": {"view_dashboard", "view_connectors", "view_benchmarks", "view_ml_models", "view_incidents", "view_integrations", "view_executive", "view_validation"},
}


def has_permission(user: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.get("role", ""), set())


def _token_from_header(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token.")
    return authorization.split(" ", 1)[1].strip()


def require_auth(authorization: str | None = Header(default=None)) -> dict:
    user = get_current_user(_token_from_header(authorization))
    if not user:
        log_audit_event(
            action="invalid_token",
            status="denied",
            severity="Critical",
            message="Request used a missing, invalid, or expired session token.",
        )
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")
    return user


def require_permission(permission: str):
    def dependency(user: dict = Header(default=None)):
        return user

    return dependency


def check_permission(user: dict, permission: str, workspace: dict | None = None):
    if not has_permission(user, permission):
        log_audit_event(
            action="permission_denied",
            resource_type="permission",
            resource_name=permission,
            status="denied",
            severity="High",
            message=f"Permission denied for {permission}.",
            user=user,
            workspace=workspace,
        )
        raise HTTPException(status_code=403, detail="Permission denied for this action.")


def require_workspace_member(user: dict, workspace_id: str):
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required.")
    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    if user.get("role") != "admin" and not is_workspace_member(workspace_id, user["user_id"]):
        raise HTTPException(status_code=403, detail="User is not a member of this workspace.")
    return workspace


def require_workspace_admin(user: dict, workspace_id: str):
    workspace = require_workspace_member(user, workspace_id)
    member_role = get_member_role(workspace_id, user["user_id"])
    if user.get("role") != "admin" and member_role != "admin":
        raise HTTPException(status_code=403, detail="Only workspace admins can perform this action.")
    return workspace
