from datetime import datetime, timedelta, timezone
from uuid import uuid4

from database.repositories import IncidentCommentRepository, IncidentRepository, IncidentTimelineRepository

from .notification_service import notify_incident_event


SLA_MINUTES_BY_SEVERITY = {
    "Critical": 60,
    "High": 240,
    "Medium": 1440,
    "Low": 4320,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sla_due_at(severity: str, created_at: str) -> str:
    minutes = SLA_MINUTES_BY_SEVERITY.get(severity, SLA_MINUTES_BY_SEVERITY["Medium"])
    try:
        base = datetime.fromisoformat(created_at)
    except ValueError:
        base = datetime.now(timezone.utc)
    return (base + timedelta(minutes=minutes)).isoformat()


def add_timeline_event(incident: dict, event_type: str, actor_user_id: str, message: str, metadata: dict | None = None) -> dict:
    return IncidentTimelineRepository.create({
        "timeline_event_id": str(uuid4()),
        "incident_id": incident["incident_id"],
        "workspace_id": incident["workspace_id"],
        "event_type": event_type,
        "actor_user_id": actor_user_id,
        "message": message,
        "metadata": metadata or {},
        "created_at": utc_now(),
    })


def create_incident(payload: dict, user: dict) -> dict:
    created_at = utc_now()
    severity = payload.get("severity", "Medium")
    incident = IncidentRepository.create({
        "incident_id": str(uuid4()),
        "workspace_id": payload.get("workspace_id", ""),
        "title": payload.get("title", "Untitled incident"),
        "description": payload.get("description", ""),
        "severity": severity,
        "status": payload.get("status", "open"),
        "source_type": payload.get("source_type", "manual"),
        "source_id": payload.get("source_id", ""),
        "related_alert_id": payload.get("related_alert_id", ""),
        "related_evaluation_id": payload.get("related_evaluation_id", ""),
        "related_model_experiment_id": payload.get("related_model_experiment_id", ""),
        "related_active_learning_item_id": payload.get("related_active_learning_item_id", ""),
        "assigned_to": payload.get("assigned_to", ""),
        "created_by": user.get("user_id", ""),
        "sla_due_at": payload.get("sla_due_at") or _sla_due_at(severity, created_at),
        "metadata": payload.get("metadata", {}),
        "created_at": created_at,
        "updated_at": created_at,
    })
    add_timeline_event(incident, "incident_created", user.get("user_id", ""), "Incident created.", {"source_type": incident["source_type"]})
    notify_incident_event(incident["workspace_id"], "incident.created", incident)
    return incident


def update_incident_status(incident: dict, status: str, user: dict) -> dict:
    updates = {"status": status, "updated_at": utc_now()}
    if status == "resolved":
        updates["resolved_at"] = utc_now()
    if status == "closed":
        updates["closed_at"] = utc_now()
    updated = IncidentRepository.update(incident["incident_id"], updates)
    add_timeline_event(updated, "incident_status_changed", user.get("user_id", ""), f"Status changed to {status}.", {"status": status})
    notify_incident_event(updated["workspace_id"], "incident.status_changed", updated)
    return updated


def assign_incident(incident: dict, assigned_to: str, user: dict) -> dict:
    updated = IncidentRepository.update(incident["incident_id"], {"assigned_to": assigned_to, "updated_at": utc_now()})
    add_timeline_event(updated, "incident_assigned", user.get("user_id", ""), f"Incident assigned to {assigned_to or 'unassigned'}.", {"assigned_to": assigned_to})
    notify_incident_event(updated["workspace_id"], "incident.assigned", updated)
    return updated


def add_comment(incident: dict, comment_text: str, user: dict) -> dict:
    now = utc_now()
    comment = IncidentCommentRepository.create({
        "comment_id": str(uuid4()),
        "incident_id": incident["incident_id"],
        "workspace_id": incident["workspace_id"],
        "user_id": user.get("user_id", ""),
        "comment_text": comment_text,
        "created_at": now,
        "updated_at": now,
    })
    add_timeline_event(incident, "incident_comment_added", user.get("user_id", ""), "Comment added.", {"comment_id": comment["comment_id"]})
    notify_incident_event(incident["workspace_id"], "incident.comment_added", incident, {"comment_id": comment["comment_id"]})
    return comment
