import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import USE_DATABASE
from security_utils import sanitize_metadata


AUDIT_DIR = Path(__file__).resolve().parent / "storage" / "audit"
STATUSES = {"success", "failed", "denied", "warning"}
SEVERITIES = {"Info", "Low", "Medium", "High", "Critical"}
SECURITY_ACTIONS = {"permission_denied", "unauthorized_access", "login_failed", "invalid_token", "expired_token"}
DELETE_ACTIONS = {"delete_workspace", "delete_user", "delete_dataset", "delete_evaluation", "delete_monitoring_rule", "delete_monitoring_run", "delete_alert", "delete_feedback"}
EXPORT_ACTIONS = {"export_json_report", "export_markdown_report", "export_corrected_dataset", "build_training_dataset", "export_root_cause", "export_timeline", "export_impact_graph", "export_alerts", "export_audit"}


def ensure_audit_dir():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return None


def _write(path: Path, payload: dict):
    ensure_audit_dir()
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def _workspace_fields(workspace: dict | None) -> dict:
    workspace = workspace or {}
    return {
        "workspace_id": workspace.get("workspace_id", ""),
        "workspace_name": workspace.get("name", ""),
    }


def _user_fields(user: dict | None) -> dict:
    user = user or {}
    return {
        "user_id": user.get("user_id", ""),
        "user_name": user.get("name", "Unknown User"),
        "user_email": user.get("email", ""),
        "user_role": user.get("role", ""),
    }


def log_audit_event(
    action: str,
    resource_type: str = "system",
    resource_id: str = "",
    resource_name: str = "",
    status: str = "success",
    severity: str = "Info",
    message: str = "",
    user: dict | None = None,
    workspace: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    if status not in STATUSES:
        status = "warning"
    if severity not in SEVERITIES:
        severity = "Info"
    event = {
        "audit_id": str(uuid4()),
        "created_at": _now(),
        **_workspace_fields(workspace),
        **_user_fields(user),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "status": status,
        "severity": severity,
        "message": message or f"{action.replace('_', ' ').title()} event recorded.",
        "metadata": sanitize_metadata(metadata or {}),
    }
    if USE_DATABASE:
        from database.repositories import AuditRepository

        AuditRepository.create(event)
    else:
        _write(AUDIT_DIR / f"{event['audit_id']}.json", event)
    return event


def list_audit_events(filters: dict | None = None) -> list[dict]:
    if USE_DATABASE:
        from database.repositories import AuditRepository

        return AuditRepository.list(filters)
    ensure_audit_dir()
    filters = {key: value for key, value in (filters or {}).items() if value}
    events = []
    for path in AUDIT_DIR.glob("*.json"):
        event = _read(path)
        if not event:
            continue
        if any(str(event.get(key, "")) != str(value) for key, value in filters.items()):
            continue
        events.append(event)
    return sorted(events, key=lambda item: item.get("created_at", ""), reverse=True)


def get_audit_event(audit_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import AuditRepository

        return AuditRepository.get_by_id(audit_id)
    ensure_audit_dir()
    path = AUDIT_DIR / f"{audit_id}.json"
    return _read(path) if path.exists() else None


def delete_audit_event(audit_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import AuditRepository

        return AuditRepository.delete(audit_id)
    path = AUDIT_DIR / f"{audit_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def _counts(items: list[dict], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        value = item.get(key, "unknown") or "unknown"
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items(), key=lambda pair: pair[1], reverse=True))


def build_audit_summary(workspace_id: str = "") -> dict:
    events = list_audit_events({"workspace_id": workspace_id} if workspace_id else {})
    return {
        "total_events": len(events),
        "success_events": sum(1 for event in events if event.get("status") == "success"),
        "failed_events": sum(1 for event in events if event.get("status") == "failed"),
        "denied_events": sum(1 for event in events if event.get("status") == "denied"),
        "warning_events": sum(1 for event in events if event.get("status") == "warning"),
        "critical_events": sum(1 for event in events if event.get("severity") == "Critical"),
        "high_events": sum(1 for event in events if event.get("severity") == "High"),
        "medium_events": sum(1 for event in events if event.get("severity") == "Medium"),
        "low_events": sum(1 for event in events if event.get("severity") == "Low"),
        "info_events": sum(1 for event in events if event.get("severity") == "Info"),
        "export_events": sum(1 for event in events if event.get("action") in EXPORT_ACTIONS),
        "delete_events": sum(1 for event in events if event.get("action") in DELETE_ACTIONS),
        "top_actions": _counts(events, "action"),
        "top_users": _counts(events, "user_email"),
        "top_resource_types": _counts(events, "resource_type"),
        "recent_security_events": [event for event in events if event.get("action") in SECURITY_ACTIONS][:10],
        "recent_delete_events": [event for event in events if event.get("action") in DELETE_ACTIONS][:10],
        "recent_export_events": [event for event in events if event.get("action") in EXPORT_ACTIONS][:10],
    }


def build_compliance_risk_summary(workspace_id: str = "") -> dict:
    events = list_audit_events({"workspace_id": workspace_id} if workspace_id else {})
    score = 0
    factors = []
    recommendations = []

    def add(count: int, points: int, factor: str, recommendation: str):
        nonlocal score
        if count:
            score += count * points
            factors.append(factor.format(count=count))
            recommendations.append(recommendation)

    add(sum(1 for event in events if event.get("action") == "permission_denied"), 10, "{count} permission denied events found.", "Review permission denied events.")
    add(sum(1 for event in events if event.get("action") == "login_failed"), 15, "{count} failed login events found.", "Review failed login attempts.")
    add(sum(1 for event in events if event.get("action") == "unauthorized_access"), 20, "{count} unauthorized access events found.", "Investigate unauthorized access attempts.")
    add(sum(1 for event in events if event.get("action") in DELETE_ACTIONS), 10, "{count} delete events found.", "Enable stricter admin review for delete actions.")
    add(sum(1 for event in events if event.get("action") in EXPORT_ACTIONS), 5, "{count} export events found in recent activity.", "Verify exported reports were authorized.")
    add(sum(1 for event in events if event.get("action") == "delete_workspace"), 25, "{count} workspace deletion events found.", "Review workspace deletion approvals.")
    add(sum(1 for event in events if event.get("action") == "delete_user"), 20, "{count} user deletion events found.", "Review user deletion approvals.")
    add(sum(1 for event in events if event.get("action") == "delete_alert"), 10, "{count} alert deletion events found.", "Confirm alert deletions were intentional.")

    score = min(score, 100)
    if score <= 20:
        level = "Low"
    elif score <= 50:
        level = "Medium"
    elif score <= 80:
        level = "High"
    else:
        level = "Critical"

    return {
        "workspace_id": workspace_id,
        "risk_level": level,
        "risk_score": score,
        "risk_factors": factors or ["No compliance risk factors found."],
        "recommendations": recommendations or ["Continue monitoring audit activity."],
    }


def export_audit_json(workspace_id: str = "") -> dict:
    return {
        "summary": build_audit_summary(workspace_id),
        "compliance_risk": build_compliance_risk_summary(workspace_id),
        "events": list_audit_events({"workspace_id": workspace_id} if workspace_id else {}),
    }


def export_audit_markdown(workspace_id: str = "") -> str:
    payload = export_audit_json(workspace_id)
    summary = payload["summary"]
    risk = payload["compliance_risk"]
    lines = [
        "# DriftGuard AI Audit Trail Report",
        "",
        "## Summary",
        f"- Total events: {summary['total_events']}",
        f"- Success events: {summary['success_events']}",
        f"- Failed events: {summary['failed_events']}",
        f"- Denied events: {summary['denied_events']}",
        f"- Critical events: {summary['critical_events']}",
        f"- High events: {summary['high_events']}",
        f"- Medium events: {summary['medium_events']}",
        f"- Low events: {summary['low_events']}",
        "",
        "## Compliance Risk Summary",
        f"- Risk level: {risk['risk_level']}",
        f"- Risk score: {risk['risk_score']}",
        "",
        "### Risk Factors",
        *[f"- {factor}" for factor in risk["risk_factors"]],
        "",
        "### Recommendations",
        *[f"- {item}" for item in risk["recommendations"]],
        "",
        "## Recent Security Events",
        "",
        "| Time | User | Action | Status | Severity | Message |",
        "|---|---|---|---|---|---|",
    ]
    for event in summary["recent_security_events"]:
        lines.append(f"| {event['created_at']} | {event['user_email']} | {event['action']} | {event['status']} | {event['severity']} | {event['message']} |")
    lines.extend(["", "## Audit Events", "", "| Time | User | Role | Action | Resource | Status | Severity |", "|---|---|---|---|---|---|---|"])
    for event in payload["events"]:
        resource = f"{event.get('resource_type', '')}: {event.get('resource_name', '')}"
        lines.append(f"| {event['created_at']} | {event['user_email']} | {event['user_role']} | {event['action']} | {resource} | {event['status']} | {event['severity']} |")
    return "\n".join(lines)
