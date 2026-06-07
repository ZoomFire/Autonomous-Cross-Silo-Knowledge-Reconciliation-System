from datetime import datetime, timezone

from database.repositories import EscalationRuleRepository, IncidentRepository, IncidentTimelineRepository

from .incident_service import add_timeline_event, utc_now
from .notification_service import notify_incident_event


def _parse_dt(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return datetime.now(timezone.utc)


def _rule_matches(rule: dict, incident: dict) -> bool:
    if rule.get("severity") and rule["severity"] != incident.get("severity"):
        return False
    if rule.get("status_filter") and rule["status_filter"] != incident.get("status"):
        return False
    age_minutes = (datetime.now(timezone.utc) - _parse_dt(incident.get("created_at", utc_now()))).total_seconds() / 60
    return age_minutes >= int(rule.get("escalate_after_minutes") or 0)


def check_escalations(workspace_id: str, user: dict) -> dict:
    rules = EscalationRuleRepository.list_by_workspace(workspace_id, enabled_only=True)
    incidents = IncidentRepository.list_by_workspace(workspace_id)
    escalated = []
    for rule in rules:
        for incident in incidents:
            if not _rule_matches(rule, incident):
                continue
            if IncidentTimelineRepository.has_escalation_event(incident["incident_id"], rule["rule_id"]):
                continue
            metadata = {"rule_id": rule["rule_id"], "rule_name": rule["name"], "target_role": rule.get("target_role", ""), "target_user_id": rule.get("target_user_id", "")}
            updated = IncidentRepository.update(incident["incident_id"], {"status": "escalated", "updated_at": utc_now()}) or incident
            add_timeline_event(updated, "incident_escalated", user.get("user_id", ""), f"Incident escalated by rule {rule['name']}.", metadata)
            if rule.get("webhook_enabled", True):
                notify_incident_event(workspace_id, "incident.escalated", updated, metadata)
            escalated.append({"incident_id": updated["incident_id"], "rule_id": rule["rule_id"]})
    return {"checked_rules": len(rules), "escalated_count": len(escalated), "escalations": escalated}
