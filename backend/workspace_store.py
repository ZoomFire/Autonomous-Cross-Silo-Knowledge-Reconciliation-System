import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import USE_DATABASE


WORKSPACES_DIR = Path(__file__).resolve().parent / "storage" / "workspaces"
VALID_ROLES = {"admin", "engineer", "reviewer", "viewer"}


def ensure_workspace_dir():
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return None


def _write(path: Path, payload: dict):
    ensure_workspace_dir()
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def create_workspace(name: str, description: str, created_by: str, role: str = "admin") -> dict:
    if role not in VALID_ROLES:
        raise ValueError("Invalid workspace role.")
    if not name.strip():
        raise ValueError("Workspace name is required.")
    now = _now()
    workspace = {
        "workspace_id": str(uuid4()),
        "name": name.strip(),
        "description": description or "",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "members": [{"user_id": created_by, "role": role}],
    }
    if USE_DATABASE:
        from database.repositories import WorkspaceRepository

        return WorkspaceRepository.create(workspace)
    _write(WORKSPACES_DIR / f"{workspace['workspace_id']}.json", workspace)
    return workspace


def list_workspaces() -> list[dict]:
    if USE_DATABASE:
        from database.repositories import WorkspaceRepository

        return WorkspaceRepository.list()
    ensure_workspace_dir()
    items = []
    for path in WORKSPACES_DIR.glob("*.json"):
        workspace = _read(path)
        if workspace:
            items.append(workspace)
    return sorted(items, key=lambda item: item.get("created_at", ""))


def get_workspace(workspace_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import WorkspaceRepository

        return WorkspaceRepository.get_by_id(workspace_id)
    ensure_workspace_dir()
    return _read(WORKSPACES_DIR / f"{workspace_id}.json")


def update_workspace(workspace_id: str, payload: dict) -> dict | None:
    workspace = get_workspace(workspace_id)
    if not workspace:
        return None
    if "name" in payload:
        if not str(payload["name"]).strip():
            raise ValueError("Workspace name is required.")
        workspace["name"] = str(payload["name"]).strip()
    if "description" in payload:
        workspace["description"] = payload["description"] or ""
    workspace["updated_at"] = _now()
    if USE_DATABASE:
        from database.repositories import WorkspaceRepository

        return WorkspaceRepository.update(workspace_id, workspace)
    _write(WORKSPACES_DIR / f"{workspace_id}.json", workspace)
    return workspace


def delete_workspace(workspace_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import WorkspaceRepository

        return WorkspaceRepository.delete(workspace_id)
    path = WORKSPACES_DIR / f"{workspace_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def list_workspace_members(workspace_id: str) -> list[dict]:
    if USE_DATABASE:
        from database.repositories import WorkspaceMemberRepository

        return WorkspaceMemberRepository.list(workspace_id)
    workspace = get_workspace(workspace_id)
    return workspace.get("members", []) if workspace else []


def get_member_role(workspace_id: str, user_id: str) -> str | None:
    return next((member.get("role") for member in list_workspace_members(workspace_id) if member.get("user_id") == user_id), None)


def is_workspace_member(workspace_id: str, user_id: str) -> bool:
    return get_member_role(workspace_id, user_id) is not None


def add_user_to_workspace(workspace_id: str, user_id: str, role: str = "viewer") -> dict | None:
    if role not in VALID_ROLES:
        raise ValueError("Invalid workspace role.")
    workspace = get_workspace(workspace_id)
    if not workspace:
        return None
    members = workspace.setdefault("members", [])
    existing = next((member for member in members if member.get("user_id") == user_id), None)
    if existing:
        existing["role"] = role
    else:
        members.append({"user_id": user_id, "role": role})
    if USE_DATABASE:
        from database.repositories import WorkspaceMemberRepository

        WorkspaceMemberRepository.add(workspace_id, user_id, role)
        return get_workspace(workspace_id)
    workspace["updated_at"] = _now()
    _write(WORKSPACES_DIR / f"{workspace_id}.json", workspace)
    return workspace


def remove_user_from_workspace(workspace_id: str, user_id: str) -> dict | None:
    workspace = get_workspace(workspace_id)
    if not workspace:
        return None
    members = workspace.get("members", [])
    if len([member for member in members if member.get("role") == "admin"]) <= 1:
        target = next((member for member in members if member.get("user_id") == user_id), None)
        if target and target.get("role") == "admin":
            raise ValueError("Cannot remove the last workspace admin.")
    if USE_DATABASE:
        from database.repositories import WorkspaceMemberRepository

        WorkspaceMemberRepository.remove(workspace_id, user_id)
        return get_workspace(workspace_id)
    workspace["members"] = [member for member in members if member.get("user_id") != user_id]
    workspace["updated_at"] = _now()
    _write(WORKSPACES_DIR / f"{workspace_id}.json", workspace)
    return workspace


def get_user_workspaces(user_id: str) -> list[dict]:
    return [workspace for workspace in list_workspaces() if is_workspace_member(workspace.get("workspace_id", ""), user_id)]
