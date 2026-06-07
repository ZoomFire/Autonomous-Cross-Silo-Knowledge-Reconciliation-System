def incident_to_markdown(incident: dict, comments: list[dict], timeline: list[dict]) -> str:
    lines = [
        f"# Incident: {incident.get('title', '')}",
        "",
        f"- ID: `{incident.get('incident_id', '')}`",
        f"- Workspace: `{incident.get('workspace_id', '')}`",
        f"- Severity: {incident.get('severity', '')}",
        f"- Status: {incident.get('status', '')}",
        f"- Source: {incident.get('source_type', '')} `{incident.get('source_id', '')}`",
        f"- Assigned to: {incident.get('assigned_to') or 'Unassigned'}",
        f"- Created by: {incident.get('created_by', '')}",
        f"- Created at: {incident.get('created_at', '')}",
        f"- SLA due at: {incident.get('sla_due_at') or 'Not set'}",
        "",
        "## Description",
        "",
        incident.get("description") or "No description provided.",
        "",
        "## Timeline",
        "",
    ]
    if timeline:
        for event in timeline:
            lines.append(f"- {event.get('created_at', '')}: **{event.get('event_type', '')}** - {event.get('message', '')}")
    else:
        lines.append("- No timeline events recorded.")
    lines.extend(["", "## Comments", ""])
    if comments:
        for comment in comments:
            lines.append(f"- {comment.get('created_at', '')} `{comment.get('user_id', '')}`: {comment.get('comment_text', '')}")
    else:
        lines.append("- No comments recorded.")
    return "\n".join(lines) + "\n"
