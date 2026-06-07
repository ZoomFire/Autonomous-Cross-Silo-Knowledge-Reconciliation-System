import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import STORAGE_DIR


PRIVACY_DIR = STORAGE_DIR / "privacy"
SETTINGS_DIR = PRIVACY_DIR / "settings"
DELETE_REQUESTS_DIR = PRIVACY_DIR / "delete_requests"


DEFAULT_PRIVACY_SETTINGS = {
    "privacy_mode_enabled": True,
    "redact_exports": True,
    "data_retention_days": 90,
    "allow_workspace_export": True,
    "allow_workspace_delete_request": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_privacy_dirs():
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    DELETE_REQUESTS_DIR.mkdir(parents=True, exist_ok=True)


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write(path: Path, payload: dict):
    ensure_privacy_dirs()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_privacy_settings(workspace_id: str) -> dict:
    ensure_privacy_dirs()
    existing = _read(SETTINGS_DIR / f"{workspace_id}.json")
    if existing:
        return {**DEFAULT_PRIVACY_SETTINGS, **existing}
    now = utc_now()
    settings = {"workspace_id": workspace_id, **DEFAULT_PRIVACY_SETTINGS, "created_at": now, "updated_at": now}
    _write(SETTINGS_DIR / f"{workspace_id}.json", settings)
    return settings


def update_privacy_settings(payload: dict) -> dict:
    workspace_id = payload.get("workspace_id", "")
    current = get_privacy_settings(workspace_id)
    updates = {key: payload[key] for key in DEFAULT_PRIVACY_SETTINGS if key in payload}
    if "data_retention_days" in updates:
        updates["data_retention_days"] = max(1, int(updates["data_retention_days"]))
    next_settings = {**current, **updates, "updated_at": utc_now()}
    _write(SETTINGS_DIR / f"{workspace_id}.json", next_settings)
    return next_settings


def create_delete_request(workspace_id: str, requested_by: str) -> dict:
    request = {
        "delete_request_id": str(uuid4()),
        "workspace_id": workspace_id,
        "requested_by": requested_by,
        "status": "pending",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "message": "Workspace deletion request created. Manual confirmation required.",
    }
    _write(DELETE_REQUESTS_DIR / f"{request['delete_request_id']}.json", request)
    return request


def list_delete_requests() -> list[dict]:
    ensure_privacy_dirs()
    items = [_read(path) for path in DELETE_REQUESTS_DIR.glob("*.json")]
    return sorted([item for item in items if item], key=lambda item: item.get("created_at", ""), reverse=True)


def approve_delete_request(delete_request_id: str, approved_by: str) -> dict | None:
    path = DELETE_REQUESTS_DIR / f"{delete_request_id}.json"
    request = _read(path)
    if not request:
        return None
    request.update({
        "status": "approved",
        "approved_by": approved_by,
        "updated_at": utc_now(),
        "message": "Delete request approved. Physical deletion can be performed from workspace admin tools.",
    })
    _write(path, request)
    return request
