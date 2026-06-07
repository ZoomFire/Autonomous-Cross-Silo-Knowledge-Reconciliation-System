from datetime import datetime, timezone

from models import DatasetEvaluationResponse


OWNER_BY_SOURCE = {
    "documentation": "Technical Writer / API Documentation Team",
    "code": "Backend Team",
    "jira": "Product Manager / Business Analyst",
    "commit": "Engineering Team",
    "logs": "DevOps / SRE Team",
    "database_config": "Platform / DevOps Team",
    "multiple": "Engineering Lead",
    "unknown": "Triage Team",
    "none": "No Owner Required",
}


def _text(case_result: dict) -> str:
    values = [
        case_result.get("title", ""),
        case_result.get("expected_label", ""),
        case_result.get("predicted_label", ""),
        case_result.get("expected_drift_type", ""),
        case_result.get("predicted_drift_type", ""),
        case_result.get("expected_severity", ""),
        case_result.get("predicted_severity", ""),
        case_result.get("mismatch_reason", ""),
        case_result.get("explanation", ""),
        " ".join(case_result.get("evidence_sources", []) or []),
    ]
    return " ".join(values).lower()


def detect_responsible_source(case_result: dict) -> str:
    text = _text(case_result)
    if case_result.get("predicted_label") in {"match", "no_contradiction"} or case_result.get("predicted_drift_type") == "No Drift":
        return "none"
    if sum(token in text for token in ["documentation", "code", "jira", "commit", "logs", "database"]) >= 4:
        return "multiple"
    if "commit" in text and ("internal" in text or "access" in text):
        return "commit"
    if "database" in text or "config" in text or "feature_enabled" in text:
        return "database_config"
    if "logs" in text or "403" in text or "401" in text or "500" in text or "runtime" in text:
        return "logs"
    if "jira" in text or "ticket" in text:
        return "jira"
    if "code" in text or "github" in text or "admin" in text or "authentication" in text:
        return "code"
    if "documentation" in text or "docs" in text or "public" in text:
        return "documentation"
    return "unknown"


def analyze_root_cause(case_result: dict) -> tuple[str, str]:
    source = detect_responsible_source(case_result)
    predicted_drift_type = case_result.get("predicted_drift_type", "Unknown")
    text = _text(case_result)

    if source == "none":
        return "No Drift Detected", source
    if source == "multiple":
        return "Ambiguous Multi-Source Drift", source
    if source == "commit":
        return "Commit Introduced Drift", source
    if source == "database_config" and ("database" in text or "config" in text):
        return "Database/Config Drift", source
    if source == "logs" or "Operational" in predicted_drift_type:
        return "Runtime Failure", source
    if source == "jira":
        return "Ticket Requirement Conflict", source
    if source == "code":
        return "Code Behavior Changed", source
    if source == "documentation" or "Documentation" in predicted_drift_type:
        return "Documentation Outdated", source
    return "Unknown", source


def generate_fix_recommendation(case_result: dict) -> str:
    entity_hint = case_result.get("title", "the affected feature")
    category, source = analyze_root_cause(case_result)
    if category == "Documentation Outdated":
        return f"Update API documentation for {entity_hint} to match implementation/runtime behavior, or change the code if the documented behavior is intended."
    if category == "Code Behavior Changed":
        return f"Review the implementation for {entity_hint} and align access/auth behavior with the approved requirement."
    if category == "Ticket Requirement Conflict":
        return f"Clarify the Jira requirement for {entity_hint} and update implementation or acceptance criteria."
    if category in {"Configuration Mismatch", "Database/Config Drift"}:
        return f"Update database or feature flag configuration for {entity_hint}, then re-run evaluation."
    if category == "Runtime Failure":
        return f"Investigate runtime errors for {entity_hint}, fix failing service behavior, and verify logs return successful responses."
    if category == "Commit Introduced Drift":
        return f"Review the commit that changed behavior for {entity_hint}; revert, document, or complete the intended rollout."
    if source == "none":
        return "No fix required. Signals appear aligned."
    return "Open an engineering triage task to confirm the intended behavior and assign the responsible team."


def generate_action_plan(case_result: dict) -> list[str]:
    category, _ = analyze_root_cause(case_result)
    steps = [
        "Review the conflicting evidence and confirm intended behavior.",
        "Assign the suggested owner to validate the source of truth.",
        "Apply the recommended documentation, code, config, or runtime fix.",
        "Re-run DriftGuard evaluation after the fix.",
    ]
    if category == "Commit Introduced Drift":
        steps.insert(0, "Review the latest commit that changed access control.")
    if category == "Runtime Failure":
        steps.insert(0, "Inspect recent logs and production health checks.")
    return steps


def estimate_fix_effort(case_result: dict) -> str:
    category, source = analyze_root_cause(case_result)
    if source in {"documentation", "jira"}:
        return "Low"
    if source in {"database_config", "code", "commit"}:
        return "Medium"
    if source in {"logs", "multiple"}:
        return "High"
    if category == "No Drift Detected":
        return "Low"
    return "Unknown"


def calculate_priority_score(case_result: dict) -> tuple[int, str]:
    severity = case_result.get("predicted_severity") or case_result.get("expected_severity") or "None"
    score = {"Critical": 90, "High": 75, "Medium": 50, "Low": 25, "None": 0}.get(severity, 0)
    source = detect_responsible_source(case_result)
    drift_type = case_result.get("predicted_drift_type", "")
    text = _text(case_result)
    if source in {"logs", "database_config"}:
        score += 5
    if drift_type in {"Runtime Drift", "Operational Drift"}:
        score += 5
    if "customer" in text or "public" in text:
        score += 5
    if case_result.get("predicted_label") == "uncertain":
        score -= 10
    if source == "none":
        score -= 20
    score = max(0, min(100, score))
    if score >= 85:
        return score, "Critical"
    if score >= 65:
        return score, "High"
    if score >= 40:
        return score, "Medium"
    if score >= 1:
        return score, "Low"
    return score, "None"


def explain_risk_impact(case_result: dict) -> str:
    category, source = analyze_root_cause(case_result)
    severity = case_result.get("predicted_severity", "Unknown")
    drift_type = case_result.get("predicted_drift_type", "Unknown")
    if category == "No Drift Detected":
        return "No material risk detected because evaluated signals appear aligned."
    if source == "logs":
        return f"{severity} runtime drift may indicate active user-facing failures or operational instability."
    if source == "database_config":
        return f"{severity} configuration drift may route users to behavior that contradicts requirements or implementation."
    if source == "documentation":
        return f"{severity} {drift_type} may cause developers or customers to integrate against incorrect behavior."
    return f"{severity} {drift_type} can cause delivery confusion, support escalations, or unsafe rollout decisions."


def analyze_case(case_result: dict) -> dict:
    category, source = analyze_root_cause(case_result)
    priority_score, priority_level = calculate_priority_score(case_result)
    secondary = [item for item in (case_result.get("evidence_sources") or []) if item.lower() != source]
    return {
        "case_id": case_result.get("case_id", ""),
        "title": case_result.get("title", ""),
        "has_drift": category != "No Drift Detected",
        "root_cause_category": category,
        "responsible_source": source,
        "secondary_sources": secondary,
        "root_cause_explanation": case_result.get("mismatch_reason") or case_result.get("explanation", ""),
        "recommended_fix": generate_fix_recommendation(case_result),
        "action_plan": generate_action_plan(case_result),
        "suggested_owner": OWNER_BY_SOURCE.get(source, "Triage Team"),
        "priority_score": priority_score,
        "priority_level": priority_level,
        "fix_effort": estimate_fix_effort(case_result),
        "risk_impact": explain_risk_impact(case_result),
    }


def _distribution(values: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return out


def build_root_cause_report(evaluation_result, evaluation_id: str = "latest") -> dict:
    if isinstance(evaluation_result, DatasetEvaluationResponse):
        result_dict = evaluation_result.model_dump()
    else:
        result_dict = evaluation_result
    cases = [analyze_case(case) for case in result_dict.get("results", [])]
    priority_counts = _distribution([case["priority_level"] for case in cases])
    average_priority = round(sum(case["priority_score"] for case in cases) / len(cases), 2) if cases else 0
    return {
        "evaluation_id": evaluation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(cases),
        "drift_cases": sum(1 for case in cases if case["has_drift"]),
        "no_drift_cases": sum(1 for case in cases if not case["has_drift"]),
        "critical_priority_cases": priority_counts.get("Critical", 0),
        "high_priority_cases": priority_counts.get("High", 0),
        "medium_priority_cases": priority_counts.get("Medium", 0),
        "low_priority_cases": priority_counts.get("Low", 0),
        "root_cause_distribution": _distribution([case["root_cause_category"] for case in cases]),
        "responsible_source_distribution": _distribution([case["responsible_source"] for case in cases]),
        "recommended_owner_distribution": _distribution([case["suggested_owner"] for case in cases]),
        "average_priority_score": average_priority,
        "cases": cases,
    }


def root_cause_report_to_markdown(report: dict) -> str:
    def table(title: str, distribution: dict[str, int]) -> list[str]:
        lines = [f"## {title}", "| Value | Count |", "| --- | --- |"]
        lines.extend(f"| {key} | {value} |" for key, value in distribution.items())
        return lines

    lines = [
        "# DriftGuard AI Root Cause Analysis Report",
        "",
        "## Summary",
        f"- Evaluation ID: {report.get('evaluation_id')}",
        f"- Total cases: {report.get('total_cases')}",
        f"- Drift cases: {report.get('drift_cases')}",
        f"- No drift cases: {report.get('no_drift_cases')}",
        f"- Critical priority cases: {report.get('critical_priority_cases')}",
        f"- High priority cases: {report.get('high_priority_cases')}",
        f"- Average priority score: {report.get('average_priority_score')}",
        "",
    ]
    lines.extend(table("Root Cause Distribution", report.get("root_cause_distribution", {})))
    lines.append("")
    lines.extend(table("Responsible Source Distribution", report.get("responsible_source_distribution", {})))
    lines.append("")
    lines.extend(table("Recommended Owner Distribution", report.get("recommended_owner_distribution", {})))
    lines.extend(["", "## Case Analysis"])
    for case in report.get("cases", []):
        lines.extend([
            f"### {case['case_id']} - {case['title']}",
            f"- Root cause category: {case['root_cause_category']}",
            f"- Responsible source: {case['responsible_source']}",
            f"- Suggested owner: {case['suggested_owner']}",
            f"- Priority: {case['priority_level']} ({case['priority_score']})",
            f"- Fix effort: {case['fix_effort']}",
            f"- Risk impact: {case['risk_impact']}",
            f"- Recommended fix: {case['recommended_fix']}",
            "",
            "Action plan:",
        ])
        lines.extend(f"{index}. {step}" for index, step in enumerate(case["action_plan"], start=1))
        lines.append("")
    return "\n".join(lines)
