import re
from datetime import datetime, timezone
from uuid import uuid4


SOURCE_ORDER = {
    "jira": 1,
    "documentation": 2,
    "commit": 3,
    "code": 4,
    "database_config": 5,
    "logs": 6,
    "evaluation": 7,
    "root_cause": 8,
    "feedback": 9,
}

EVENT_TYPES = {
    "jira": "requirement",
    "documentation": "claim",
    "commit": "commit_change",
    "code": "code_behavior",
    "database_config": "config_state",
    "logs": "runtime_signal",
}

EVENT_TITLES = {
    "jira": "Jira requirement signal",
    "documentation": "Documentation claim",
    "commit": "Commit change signal",
    "code": "Code behavior signal",
    "database_config": "Database/config state",
    "logs": "Runtime log signal",
}

DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?)?\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(value) -> dict:
    return value.model_dump() if hasattr(value, "model_dump") else value or {}


def _source_text(case_result: dict, source: str) -> str:
    inputs = case_result.get("input", {}) or {}
    return str(inputs.get(source, "") or "").strip()


def _parse_date(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text or "")
        if not match:
            continue
        raw = match.group(0).replace(" ", "T")
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass
    return None


def _event(case_result: dict, source: str, event_type: str, title: str, description: str, confidence: float, related_text: str = "") -> dict:
    text = related_text or description
    return {
        "event_id": str(uuid4()),
        "case_id": case_result.get("case_id", "Unknown"),
        "source": source if source in SOURCE_ORDER else "evaluation",
        "event_type": event_type,
        "title": title,
        "description": description or "No event details were available.",
        "detected_at": _parse_date(text) or _now(),
        "inferred_order": SOURCE_ORDER.get(source, 99),
        "confidence": round(float(confidence or 0), 2),
        "related_text": related_text or description or "",
    }


def extract_timeline_events(case_result) -> list[dict]:
    case_result = _as_dict(case_result)
    events: list[dict] = []

    for source in ("jira", "documentation", "commit", "code", "database_config", "logs"):
        text = _source_text(case_result, source)
        if text:
            events.append(
                _event(
                    case_result,
                    source,
                    EVENT_TYPES[source],
                    EVENT_TITLES[source],
                    text,
                    0.8,
                    text,
                )
            )

    drift_type = case_result.get("predicted_drift_type") or case_result.get("expected_drift_type") or "Unknown Drift"
    severity = case_result.get("predicted_severity") or case_result.get("expected_severity") or "Unknown"
    label = case_result.get("predicted_label", "")
    if drift_type != "No Drift" or label in {"contradiction", "manual_review", "evaluation_error"}:
        events.append(
            _event(
                case_result,
                "evaluation",
                "detected_drift",
                f"Evaluation detected {drift_type}",
                case_result.get("mismatch_reason") or case_result.get("summary") or f"{severity} drift was detected.",
                case_result.get("confidence_score", 0.75),
            )
        )

    if case_result.get("mismatch_reason"):
        events.append(
            _event(
                case_result,
                "root_cause",
                "root_cause",
                "Root cause evidence from mismatch",
                case_result["mismatch_reason"],
                0.7,
                case_result["mismatch_reason"],
            )
        )

    if case_result.get("human_feedback") or case_result.get("feedback"):
        feedback_text = str(case_result.get("human_feedback") or case_result.get("feedback"))
        events.append(_event(case_result, "feedback", "human_correction", "Human correction captured", feedback_text, 0.9, feedback_text))

    return events


def infer_event_order(events: list[dict]) -> list[dict]:
    ordered = sorted(events, key=lambda item: (SOURCE_ORDER.get(item.get("source"), 99), item.get("detected_at", "")))
    for index, event in enumerate(ordered, start=1):
        event["inferred_order"] = index
    return ordered


def build_case_timeline(case_result) -> dict:
    case_result = _as_dict(case_result)
    return {
        "case_id": case_result.get("case_id", "Unknown"),
        "title": case_result.get("title", "Untitled case"),
        "drift_type": case_result.get("predicted_drift_type") or case_result.get("expected_drift_type") or "Unknown",
        "severity": case_result.get("predicted_severity") or case_result.get("expected_severity") or "Unknown",
        "events": infer_event_order(extract_timeline_events(case_result)),
    }


def generate_timeline_summary(timeline_report: dict) -> list[str]:
    sources = [event["source"] for case in timeline_report.get("cases", []) for event in case.get("events", [])]
    summaries: list[str] = []

    if "jira" in sources or "documentation" in sources:
        summaries.append("Most drift cases start with requirement or documentation signals before implementation evidence.")
    if "commit" in sources or "code" in sources:
        summaries.append("Code and commit events show where the behavior may have changed from the stated architecture.")
    if "logs" in sources:
        summaries.append("Runtime logs often confirm the drift after code or configuration changes.")
    if "database_config" in sources:
        summaries.append("Configuration state contributes to one or more architecture drift timelines.")
    if not summaries:
        summaries.append("No timeline events were extracted; add source text to build a richer drift evolution view.")
    return summaries


def build_evaluation_timeline(evaluation_result, evaluation_id: str = "latest") -> dict:
    result = _as_dict(evaluation_result)
    cases = [build_case_timeline(case) for case in result.get("results", [])]
    report = {
        "evaluation_id": evaluation_id,
        "created_at": _now(),
        "total_cases": len(cases),
        "total_events": sum(len(case.get("events", [])) for case in cases),
        "cases_with_drift": sum(1 for case in cases if case.get("drift_type") not in {"No Drift", "None"}),
        "timeline_summary": [],
        "cases": cases,
    }
    report["timeline_summary"] = generate_timeline_summary(report)
    return report


def export_timeline_markdown(timeline_report: dict) -> str:
    lines = [
        "# DriftGuard AI Architecture Drift Timeline Report",
        "",
        "## Summary",
        f"- Evaluation ID: {timeline_report.get('evaluation_id', '')}",
        f"- Total cases: {timeline_report.get('total_cases', 0)}",
        f"- Total events: {timeline_report.get('total_events', 0)}",
        f"- Cases with drift: {timeline_report.get('cases_with_drift', 0)}",
        "",
        "## Timeline Summary",
    ]
    lines.extend(f"- {item}" for item in timeline_report.get("timeline_summary", []))
    lines.extend(["", "## Case Timelines"])

    for case in timeline_report.get("cases", []):
        lines.extend(
            [
                "",
                f"### {case.get('case_id', 'Unknown')} - {case.get('title', 'Untitled case')}",
                f"- Drift type: {case.get('drift_type', 'Unknown')}",
                f"- Severity: {case.get('severity', 'Unknown')}",
                "",
                "| Order | Source | Event Type | Title | Confidence |",
                "|---|---|---|---|---|",
            ]
        )
        for event in case.get("events", []):
            lines.append(
                f"| {event.get('inferred_order', '')} | {event.get('source', '')} | "
                f"{event.get('event_type', '')} | {event.get('title', '')} | {event.get('confidence', '')} |"
            )
    return "\n".join(lines)
