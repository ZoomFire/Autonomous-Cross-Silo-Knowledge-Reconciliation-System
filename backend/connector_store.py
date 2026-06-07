import json
from datetime import datetime, timezone
from pathlib import Path

from config import STORAGE_DIR, USE_DATABASE
from security_utils import mask_secret


CONNECTOR_DIR = STORAGE_DIR / "connectors"
SOURCE_DIR = STORAGE_DIR / "imported_sources"
SYNC_DIR = STORAGE_DIR / "connector_sync_runs"
GENERATED_CASE_DIR = STORAGE_DIR / "generated_dataset_cases"


def ensure_connector_dirs():
    for directory in [CONNECTOR_DIR, SOURCE_DIR, SYNC_DIR, GENERATED_CASE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_connector_config(config: dict) -> dict:
    masked = dict(config or {})
    for key, value in list(masked.items()):
        if any(term in key.lower() for term in ["token", "secret", "password", "api_key", "access_key"]):
            masked[key] = mask_secret(value)
    return masked


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write(directory: Path, item_id: str, payload: dict):
    ensure_connector_dirs()
    (directory / f"{item_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _delete(directory: Path, item_id: str) -> bool:
    path = directory / f"{item_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def _list(directory: Path) -> list[dict]:
    ensure_connector_dirs()
    return [item for item in (_read(path) for path in directory.glob("*.json")) if item]


def create_connector(payload: dict) -> dict:
    if USE_DATABASE:
        from database.repositories import ConnectorRepository

        return ConnectorRepository.create(payload)
    _write(CONNECTOR_DIR, payload["connector_id"], payload)
    return {**payload, "config": mask_connector_config(payload.get("config", {}))}


def get_connector(connector_id: str, mask_config: bool = True) -> dict | None:
    if USE_DATABASE:
        from database.repositories import ConnectorRepository

        return ConnectorRepository.get_by_id(connector_id, mask_config=mask_config)
    payload = _read(CONNECTOR_DIR / f"{connector_id}.json")
    if payload and mask_config:
        payload = {**payload, "config": mask_connector_config(payload.get("config", {}))}
    return payload


def list_connectors(workspace_id: str) -> list[dict]:
    if USE_DATABASE:
        from database.repositories import ConnectorRepository

        return ConnectorRepository.list_by_workspace(workspace_id)
    items = [item for item in _list(CONNECTOR_DIR) if item.get("workspace_id") == workspace_id]
    return sorted([{**item, "config": mask_connector_config(item.get("config", {}))} for item in items], key=lambda item: item.get("created_at", ""), reverse=True)


def update_connector(connector_id: str, payload: dict) -> dict | None:
    if USE_DATABASE:
        from database.repositories import ConnectorRepository

        return ConnectorRepository.update(connector_id, payload)
    existing = get_connector(connector_id, mask_config=False)
    if not existing:
        return None
    updated = {**existing, **payload, "connector_id": connector_id, "updated_at": payload.get("updated_at", utc_now())}
    _write(CONNECTOR_DIR, connector_id, updated)
    return get_connector(connector_id)


def delete_connector(connector_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import ConnectorRepository

        return ConnectorRepository.delete(connector_id)
    return _delete(CONNECTOR_DIR, connector_id)


def create_source(payload: dict) -> dict:
    if USE_DATABASE:
        from database.repositories import ImportedSourceRepository

        return ImportedSourceRepository.create(payload)
    _write(SOURCE_DIR, payload["source_id"], payload)
    return payload


def get_source(source_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import ImportedSourceRepository

        return ImportedSourceRepository.get_by_id(source_id)
    return _read(SOURCE_DIR / f"{source_id}.json")


def list_sources(workspace_id: str, connector_id: str = "", source_type: str = "", search: str = "") -> list[dict]:
    if USE_DATABASE:
        from database.repositories import ImportedSourceRepository

        return ImportedSourceRepository.list_by_workspace(workspace_id, connector_id, source_type, search)
    lowered = search.lower()
    items = []
    for item in _list(SOURCE_DIR):
        if item.get("workspace_id") != workspace_id:
            continue
        if connector_id and item.get("connector_id") != connector_id:
            continue
        if source_type and item.get("source_type") != source_type:
            continue
        haystack = f"{item.get('source_name', '')} {item.get('source_path', '')} {item.get('content_text', '')}".lower()
        if lowered and lowered not in haystack:
            continue
        items.append({**item, "content_preview": item.get("content_text", "")[:400], "content_text": ""})
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def list_sources_by_connector(connector_id: str) -> list[dict]:
    if USE_DATABASE:
        from database.repositories import ImportedSourceRepository

        return ImportedSourceRepository.list_by_connector(connector_id)
    return [item for item in _list(SOURCE_DIR) if item.get("connector_id") == connector_id]


def delete_source(source_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import ImportedSourceRepository

        return ImportedSourceRepository.delete(source_id)
    return _delete(SOURCE_DIR, source_id)


def save_sync_run(payload: dict) -> dict:
    if USE_DATABASE:
        from database.repositories import ConnectorSyncRepository

        return ConnectorSyncRepository.save_sync_run(payload)
    _write(SYNC_DIR, payload["sync_id"], payload)
    return payload


def list_sync_runs(connector_id: str) -> list[dict]:
    if USE_DATABASE:
        from database.repositories import ConnectorSyncRepository

        return ConnectorSyncRepository.list_sync_runs(connector_id)
    rows = [item for item in _list(SYNC_DIR) if item.get("connector_id") == connector_id]
    return sorted(rows, key=lambda item: item.get("started_at", ""), reverse=True)


def create_generated_case(payload: dict) -> dict:
    if USE_DATABASE:
        from database.repositories import GeneratedDatasetCaseRepository

        return GeneratedDatasetCaseRepository.create(payload)
    _write(GENERATED_CASE_DIR, payload["generated_case_id"], payload)
    return payload
