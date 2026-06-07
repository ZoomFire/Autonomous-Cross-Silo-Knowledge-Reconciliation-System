from .status_mapper import map_incident_status_to_external


def _base_payload(incident: dict) -> dict:
    return {
        "workspace_id": incident.get("workspace_id", ""),
        "incident_id": incident.get("incident_id", ""),
        "title": incident.get("title", "DriftGuard incident"),
        "severity": incident.get("severity", "Medium"),
        "status": incident.get("status", "open"),
        "external_status": map_incident_status_to_external(incident.get("status", "open")),
        "description": incident.get("description", ""),
        "source_type": incident.get("source_type", "manual"),
        "source_id": incident.get("source_id", ""),
        "assigned_to": incident.get("assigned_to", ""),
        "sla_due_at": incident.get("sla_due_at", ""),
        "driftguard_url": f"driftguard://incidents/{incident.get('incident_id', '')}",
    }


def build_jira_ticket_payload(incident: dict) -> dict:
    payload = _base_payload(incident)
    payload["summary"] = f"[{payload['severity']}] {payload['title']}"
    return payload


def build_github_issue_payload(incident: dict) -> dict:
    payload = _base_payload(incident)
    payload["body"] = payload["description"]
    return payload


def build_slack_message_payload(incident: dict) -> dict:
    payload = _base_payload(incident)
    payload["message"] = f"{payload['severity']} DriftGuard incident: {payload['title']} ({payload['status']})"
    return payload


def build_teams_message_payload(incident: dict) -> dict:
    payload = _base_payload(incident)
    payload["message"] = f"{payload['severity']} DriftGuard incident: {payload['title']} ({payload['status']})"
    return payload


def build_generic_webhook_payload(incident: dict) -> dict:
    payload = _base_payload(incident)
    payload["event_type"] = "driftguard.incident"
    return payload
