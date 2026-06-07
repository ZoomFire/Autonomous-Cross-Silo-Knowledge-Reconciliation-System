INCIDENT_TO_EXTERNAL = {
    "open": "Open",
    "triaged": "To Do",
    "in_progress": "In Progress",
    "resolved": "Done",
    "closed": "Closed",
}


def map_incident_status_to_external(status: str) -> str:
    return INCIDENT_TO_EXTERNAL.get(status, status or "Open")


def map_external_status_to_incident(status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"open", "new"}:
        return "open"
    if normalized in {"to do", "todo", "triaged"}:
        return "triaged"
    if normalized in {"in progress", "doing"}:
        return "in_progress"
    if normalized in {"done", "resolved"}:
        return "resolved"
    if normalized == "closed":
        return "closed"
    return "open"
