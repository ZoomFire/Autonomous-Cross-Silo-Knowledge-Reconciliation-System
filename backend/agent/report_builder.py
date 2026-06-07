def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if value:
        return [value]
    return []


def _first_text(items: list[str], fallback: str) -> str:
    return next((item for item in items if item), fallback)


def _evaluation(step_outputs: dict) -> dict:
    return step_outputs.get("dataset_evaluation", {}).get("evaluation", {})


def _risk_from_outputs(step_outputs: dict) -> str:
    search = step_outputs.get("rag_search", {}).get("answer", {})
    root = step_outputs.get("root_cause_analysis", {}).get("root_cause", {})
    evaluation = _evaluation(step_outputs)
    result = evaluation.get("result", evaluation)
    cases = result.get("results", [])
    severities = [
        case.get("predicted_severity") or case.get("expected_severity") or ""
        for case in cases
    ]

    if root.get("critical_priority_cases", 0) > 0 or "Critical" in severities or search.get("severity_hint") == "Critical":
        return "Critical"
    if root.get("high_priority_cases", 0) > 0 or "High" in severities or search.get("severity_hint") == "High":
        return "High"
    if search.get("possible_drift") or any(case.get("predicted_label") in {"contradiction", "manual_review"} for case in cases):
        return "Medium"
    if search or cases:
        return "Low"
    return "Unknown"


def _drift_findings(step_outputs: dict) -> list[dict]:
    evaluation = _evaluation(step_outputs)
    result = evaluation.get("result", evaluation)
    findings = []
    for case in result.get("results", []):
        if case.get("predicted_drift_type") in {"No Drift", "None"} and case.get("predicted_label") == "match":
            continue
        findings.append({
            "case_id": case.get("case_id", ""),
            "title": case.get("title", ""),
            "predicted_label": case.get("predicted_label", ""),
            "predicted_drift_type": case.get("predicted_drift_type", ""),
            "predicted_severity": case.get("predicted_severity", ""),
            "summary": case.get("summary", ""),
        })
    return findings


def build_agent_report(goal: str, step_outputs: dict) -> dict:
    search = step_outputs.get("rag_search", {}).get("answer", {})
    dataset = step_outputs.get("dataset_generation", {}).get("dataset", {})
    evaluation_output = step_outputs.get("dataset_evaluation", {})
    root = step_outputs.get("root_cause_analysis", {}).get("root_cause", {})
    timeline = step_outputs.get("timeline_generation", {}).get("timeline", {})
    impact = step_outputs.get("impact_graph_generation", {}).get("impact_graph", {})
    monitoring = step_outputs.get("monitoring_recommendation", {})

    drift_findings = _drift_findings(step_outputs)
    root_findings = root.get("cases", [])[:10]
    timeline_summary = _as_list(timeline.get("timeline_summary"))
    impact_summary = _as_list(impact.get("impact_summary"))
    risk_level = _risk_from_outputs(step_outputs)

    recommended_actions = [
        "Review documentation and code evidence for the same endpoint.",
        "Use Human Review Mode to validate uncertain generated cases.",
        "Export the final report for audit review.",
    ]
    if monitoring:
        recommended_actions.insert(2, "Create a monitoring rule for this component.")
    if root_findings:
        recommended_actions.insert(2, "Assign investigation to suggested owner from root cause report.")

    evidence_summary = search.get("evidence_summary") or search.get("short_answer") or "No evidence summary was available."
    executive_summary = _first_text(
        [
            search.get("short_answer", ""),
            f"Generated {len(drift_findings)} drift finding(s) from the available workflow outputs." if drift_findings else "",
        ],
        "The agent completed its local investigation with limited available evidence.",
    )

    return {
        "goal": goal,
        "status": "completed",
        "executive_summary": executive_summary,
        "evidence_summary": evidence_summary,
        "drift_findings": drift_findings,
        "root_cause_findings": root_findings,
        "timeline_summary": timeline_summary,
        "impact_summary": impact_summary,
        "risk_level": risk_level,
        "recommended_actions": recommended_actions,
        "monitoring_recommendation": monitoring,
        "generated_artifacts": {
            "search_query_id": search.get("query_id", ""),
            "dataset_id": dataset.get("dataset_id", ""),
            "evaluation_id": evaluation_output.get("evaluation_id", ""),
            "root_cause_available": bool(root),
            "timeline_available": bool(timeline),
            "impact_graph_available": bool(impact),
        },
    }


def agent_report_to_markdown(report: dict) -> str:
    artifacts = report.get("generated_artifacts", {})
    lines = [
        "# DriftGuard AI Agent Investigation Report",
        "",
        "## Goal",
        report.get("goal", ""),
        "",
        "## Executive Summary",
        report.get("executive_summary", ""),
        "",
        "## Evidence Summary",
        report.get("evidence_summary", ""),
        "",
        "## Drift Findings",
    ]
    drift_findings = report.get("drift_findings", [])
    lines.extend(
        f"- {item.get('case_id', '')}: {item.get('title', '')} ({item.get('predicted_severity', 'Unknown')})"
        for item in drift_findings
    )
    if not drift_findings:
        lines.append("- No major drift findings were produced.")

    lines.extend(["", "## Root Cause Findings"])
    root_findings = report.get("root_cause_findings", [])
    lines.extend(
        f"- {item.get('case_id', '')}: {item.get('root_cause_category', 'Unknown')} -> {item.get('suggested_owner', 'Triage Team')}"
        for item in root_findings
    )
    if not root_findings:
        lines.append("- No root cause findings were produced.")

    lines.extend(["", "## Timeline Summary"])
    lines.extend(f"- {item}" for item in report.get("timeline_summary", []) or ["No timeline summary was produced."])
    lines.extend(["", "## Impact Summary"])
    lines.extend(f"- {item}" for item in report.get("impact_summary", []) or ["No impact summary was produced."])
    lines.extend([
        "",
        "## Risk Level",
        report.get("risk_level", "Unknown"),
        "",
        "## Recommended Actions",
    ])
    lines.extend(f"{index}. {item}" for index, item in enumerate(report.get("recommended_actions", []), start=1))
    lines.extend([
        "",
        "## Generated Artifacts",
        f"- Search query: {artifacts.get('search_query_id', '')}",
        f"- Dataset: {artifacts.get('dataset_id', '')}",
        f"- Evaluation: {artifacts.get('evaluation_id', '')}",
        f"- Root cause: {artifacts.get('root_cause_available', False)}",
        f"- Timeline: {artifacts.get('timeline_available', False)}",
        f"- Impact graph: {artifacts.get('impact_graph_available', False)}",
    ])
    return "\n".join(lines)

