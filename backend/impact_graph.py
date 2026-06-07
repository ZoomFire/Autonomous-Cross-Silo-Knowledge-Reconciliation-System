from datetime import datetime, timezone
from uuid import uuid4


COMPONENT_TERMS = {
    "payment": ["payment", "refund", "transaction"],
    "authentication": ["login", "auth", "jwt", "session", "token"],
    "user": ["user", "profile", "account"],
    "inventory": ["inventory", "stock", "product"],
    "order": ["order", "checkout", "cart"],
    "notification": ["email", "notification", "sms"],
    "platform": ["database", "config", "feature flag"],
}

SOURCE_NODE_TYPES = ("jira", "documentation", "commit", "code", "database_config", "logs")
SOURCE_LABELS = {
    "jira": "Jira requirement",
    "documentation": "Documentation",
    "commit": "Commit",
    "code": "Code",
    "database_config": "Database/config",
    "logs": "Runtime logs",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(value) -> dict:
    return value.model_dump() if hasattr(value, "model_dump") else value or {}


def _inputs(case_result: dict) -> dict:
    return case_result.get("input", {}) or {}


def _source_text(case_result: dict, source: str) -> str:
    return str(_inputs(case_result).get(source, "") or "").strip()


def _case_text(case_result: dict) -> str:
    input_text = " ".join(str(value) for value in _inputs(case_result).values())
    return " ".join(
        [
            str(case_result.get("title", "")),
            str(case_result.get("mismatch_reason", "")),
            str(case_result.get("summary", "")),
            input_text,
        ]
    ).lower()


def extract_components_from_case(case_result) -> list[str]:
    case_result = _as_dict(case_result)
    text = _case_text(case_result)
    matches = [component for component, terms in COMPONENT_TERMS.items() if any(term in text for term in terms)]
    return matches or ["general"]


def _node_id(node_type: str, component: str, case_id: str) -> str:
    return f"{node_type}:{component}:{case_id}"


def _node(node_type: str, component: str, case_result: dict, description: str) -> dict:
    case_id = case_result.get("case_id", "Unknown")
    label = f"{component} {SOURCE_LABELS.get(node_type, node_type.replace('_', ' '))}"
    return {
        "node_id": _node_id(node_type, component, case_id),
        "label": label,
        "type": node_type,
        "component": component,
        "risk_score": 0,
        "case_ids": [case_id],
        "description": description or f"{label} evidence",
    }


def _edge(from_id: str, to_id: str, relationship: str, severity: str, case_id: str, description: str) -> dict:
    return {
        "edge_id": str(uuid4()),
        "from": from_id,
        "to": to_id,
        "relationship": relationship,
        "severity": severity or "None",
        "case_id": case_id,
        "description": description or "No relationship details were available.",
    }


def _is_drift_case(case_result: dict) -> bool:
    return (
        case_result.get("predicted_drift_type") not in {"No Drift", "None", None}
        or case_result.get("predicted_label") in {"contradiction", "manual_review", "evaluation_error"}
    )


def build_case_impact_graph(case_result) -> dict:
    case_result = _as_dict(case_result)
    case_id = case_result.get("case_id", "Unknown")
    severity = case_result.get("predicted_severity") or case_result.get("expected_severity") or "None"
    relationship = "contradicts" if _is_drift_case(case_result) else "confirms"
    description = case_result.get("mismatch_reason") or case_result.get("summary") or case_result.get("title", "")

    nodes: list[dict] = []
    edges: list[dict] = []

    for component in extract_components_from_case(case_result):
        component_node = _node("component", component, case_result, f"{component} system area affected by drift evidence")
        case_node = _node("drift_case", component, case_result, case_result.get("title", "Drift case"))
        nodes.extend([component_node, case_node])
        edges.append(_edge(case_node["node_id"], component_node["node_id"], "impacts", severity, case_id, f"Case {case_id} impacts {component}."))

        source_nodes: dict[str, dict] = {}
        for source in SOURCE_NODE_TYPES:
            text = _source_text(case_result, source)
            if not text:
                continue
            source_node = _node(source, component, case_result, text)
            source_nodes[source] = source_node
            nodes.append(source_node)
            edges.append(_edge(source_node["node_id"], component_node["node_id"], "impacts", severity, case_id, text))

        if "documentation" in source_nodes and "code" in source_nodes:
            edges.append(_edge(source_nodes["documentation"]["node_id"], source_nodes["code"]["node_id"], relationship, severity, case_id, description))
        if "jira" in source_nodes and "documentation" in source_nodes:
            edges.append(_edge(source_nodes["jira"]["node_id"], source_nodes["documentation"]["node_id"], "depends_on", severity, case_id, "Documentation is expected to reflect Jira requirements."))
        if "commit" in source_nodes and "code" in source_nodes:
            edges.append(_edge(source_nodes["commit"]["node_id"], source_nodes["code"]["node_id"], "introduced_by", severity, case_id, "Commit evidence may have introduced or changed code behavior."))
        if "database_config" in source_nodes and "code" in source_nodes:
            edges.append(_edge(source_nodes["database_config"]["node_id"], source_nodes["code"]["node_id"], "configured_by", severity, case_id, "Configuration affects code behavior."))
        if "logs" in source_nodes and "code" in source_nodes:
            edges.append(_edge(source_nodes["logs"]["node_id"], source_nodes["code"]["node_id"], "observed_in", severity, case_id, "Runtime logs observe the implemented behavior."))

    return {"nodes": nodes, "edges": edges}


def _risk_level(score: int) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    if score >= 1:
        return "Low"
    return "None"


def calculate_component_risk_scores(graph_report: dict) -> list[dict]:
    severity_points = {"Critical": 30, "High": 20, "Medium": 10, "Low": 5, "None": 0}
    by_component: dict[str, dict] = {}
    nodes = graph_report.get("nodes", [])

    for node in nodes:
        component = node.get("component") or "general"
        item = by_component.setdefault(
            component,
            {
                "component": component,
                "risk_score": 0,
                "case_ids": set(),
                "critical_cases": set(),
                "high_cases": set(),
                "sources": set(),
            },
        )
        item["case_ids"].update(node.get("case_ids", []))
        item["sources"].add(node.get("type"))

    seen_cases: set[tuple[str, str]] = set()
    for edge in graph_report.get("edges", []):
        from_node = next((node for node in nodes if node.get("node_id") == edge.get("from")), None)
        if not from_node:
            continue
        component = from_node.get("component") or "general"
        case_id = edge.get("case_id", "")
        case_key = (component, case_id)
        item = by_component.setdefault(component, {"component": component, "risk_score": 0, "case_ids": set(), "critical_cases": set(), "high_cases": set(), "sources": set()})
        item["case_ids"].add(case_id)
        if case_key not in seen_cases:
            item["risk_score"] += severity_points.get(edge.get("severity", "None"), 0)
            seen_cases.add(case_key)
        if edge.get("severity") == "Critical":
            item["critical_cases"].add(case_id)
        if edge.get("severity") == "High":
            item["high_cases"].add(case_id)

    results = []
    for item in by_component.values():
        if "logs" in item["sources"]:
            item["risk_score"] += 10
        if "database_config" in item["sources"]:
            item["risk_score"] += 10
        score = max(0, min(100, item["risk_score"]))
        results.append(
            {
                "component": item["component"],
                "risk_score": score,
                "risk_level": _risk_level(score),
                "case_count": len({case_id for case_id in item["case_ids"] if case_id}),
                "critical_cases": len(item["critical_cases"]),
                "high_cases": len(item["high_cases"]),
            }
        )
    return sorted(results, key=lambda item: item["risk_score"], reverse=True)


def generate_impact_summary(graph_report: dict) -> list[str]:
    risky = graph_report.get("most_risky_components", [])
    if not risky:
        return ["No impacted components were identified."]

    top = risky[0]
    summary = [f"{top['component'].title()} component has the highest drift risk with score {top['risk_score']}."]
    if top["risk_level"] in {"Critical", "High"}:
        summary.append(f"{top['component'].title()} should be prioritized because it has {top['risk_level'].lower()} impact risk.")
    if any(node.get("type") == "logs" for node in graph_report.get("nodes", [])):
        summary.append("Runtime log evidence appears in the graph and helps confirm observed drift behavior.")
    if any(node.get("type") == "database_config" for node in graph_report.get("nodes", [])):
        summary.append("Database or configuration evidence is part of the affected architecture area.")
    return summary


def build_evaluation_impact_graph(evaluation_result, evaluation_id: str = "latest") -> dict:
    result = _as_dict(evaluation_result)
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: dict[str, dict] = {}

    for case in result.get("results", []):
        graph = build_case_impact_graph(case)
        for node in graph.get("nodes", []):
            existing = seen_nodes.get(node["node_id"])
            if existing:
                existing["case_ids"] = sorted(set(existing.get("case_ids", []) + node.get("case_ids", [])))
                continue
            seen_nodes[node["node_id"]] = node
            nodes.append(node)
        edges.extend(graph.get("edges", []))

    report = {
        "evaluation_id": evaluation_id,
        "created_at": _now(),
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "affected_components": sorted({node.get("component", "general") for node in nodes}),
        "most_risky_components": [],
        "impact_summary": [],
        "nodes": nodes,
        "edges": edges,
    }
    report["most_risky_components"] = calculate_component_risk_scores(report)
    risk_by_component = {item["component"]: item["risk_score"] for item in report["most_risky_components"]}
    for node in report["nodes"]:
        node["risk_score"] = risk_by_component.get(node.get("component"), 0)
    report["impact_summary"] = generate_impact_summary(report)
    return report


def export_impact_graph_json(graph_report: dict) -> dict:
    return graph_report
