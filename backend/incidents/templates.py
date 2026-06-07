DEFAULT_NOTIFICATION_TEMPLATES = {
    "incident.created": {
        "subject": "New {{severity}} incident: {{title}}",
        "body": "Incident {{incident_id}} was created in workspace {{workspace_id}}.",
    },
    "incident.status_changed": {
        "subject": "Incident status changed: {{title}}",
        "body": "Incident {{incident_id}} moved to {{status}}.",
    },
    "incident.assigned": {
        "subject": "Incident assigned: {{title}}",
        "body": "Incident {{incident_id}} was assigned to {{assigned_to}}.",
    },
    "incident.comment_added": {
        "subject": "Comment added: {{title}}",
        "body": "A comment was added to incident {{incident_id}}.",
    },
    "incident.escalated": {
        "subject": "Incident escalated: {{title}}",
        "body": "Incident {{incident_id}} matched escalation rule {{rule_name}}.",
    },
}


def render_template(template: str, context: dict) -> str:
    rendered = template or ""
    for key, value in context.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered
