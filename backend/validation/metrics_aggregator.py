from database.repositories import AgentRunRepository, ExternalSyncRecordRepository, IncidentRepository
from executive.metrics_collector import collect_executive_metrics


def aggregate_validation_metrics(validation_outputs: dict) -> dict:
    evaluation = validation_outputs.get("evaluation", {}) or {}
    result = evaluation.get("result", {}) or {}
    cases = result.get("cases", [])
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    drift_cases = 0
    for case in cases:
        severity = case.get("predicted_severity") or case.get("severity") or "Low"
        if severity in severity_counts:
            severity_counts[severity] += 1
        if str(case.get("predicted_label") or "").lower() in {"contradiction", "drift", "manual_review"} or severity in {"Critical", "High"}:
            drift_cases += 1
    workspace_id = validation_outputs.get("workspace_id", "")
    executive = collect_executive_metrics(workspace_id) if workspace_id else {"summary": {}, "risk": {}, "operations": {}}
    incidents = IncidentRepository.list_by_workspace(workspace_id) if workspace_id else []
    syncs = ExternalSyncRecordRepository.list_by_workspace(workspace_id, limit=500) if workspace_id else []
    agent_runs = AgentRunRepository.list_by_workspace(workspace_id) if workspace_id else []
    return {
        "evaluation": {
            "total_cases": evaluation.get("total_cases", result.get("total_cases", len(cases))),
            "correct_cases": result.get("passed", 0),
            "incorrect_cases": result.get("failed", 0),
            "accuracy": evaluation.get("accuracy", result.get("accuracy", 0)),
            "label_accuracy": evaluation.get("label_accuracy", 0),
            "drift_type_accuracy": evaluation.get("drift_type_accuracy", 0),
            "severity_accuracy": evaluation.get("severity_accuracy", 0),
        },
        "model": {"model_accuracy": 0, "f1_macro": 0, "precision_macro": 0, "recall_macro": 0},
        "drift": {
            "total_drift_cases": drift_cases,
            "critical_drift_cases": severity_counts["Critical"],
            "high_drift_cases": severity_counts["High"],
            "medium_drift_cases": severity_counts["Medium"],
            "low_drift_cases": severity_counts["Low"],
        },
        "root_cause": {
            "root_cause_cases": len((validation_outputs.get("root_cause") or {}).get("case_insights", [])),
            "top_root_cause_categories": [],
            "responsible_source_distribution": {},
        },
        "incidents": {
            "incidents_created": validation_outputs.get("incidents_created", 0),
            "open_incidents": sum(1 for item in incidents if item.get("status") in {"open", "triaged", "in_progress", "escalated"}),
            "resolved_incidents": sum(1 for item in incidents if item.get("status") in {"resolved", "closed"}),
            "average_resolution_time": executive.get("operations", {}).get("average_resolution_time_hours", 0),
        },
        "active_learning": {"active_learning_items_created": 0, "reviewed_items": executive.get("summary", {}).get("active_learning_reviewed_items", 0), "training_pool_examples": 0, "retraining_recommended": False},
        "agent": {"agent_runs": len(agent_runs), "successful_agent_runs": sum(1 for item in agent_runs if item.get("status") == "completed"), "partial_agent_runs": sum(1 for item in agent_runs if item.get("status") not in {"completed", "failed"})},
        "business": {
            "estimated_hours_saved": (validation_outputs.get("executive_report") or {}).get("roi", {}).get("estimated_hours_saved", 0),
            "estimated_cost_saved": (validation_outputs.get("executive_report") or {}).get("roi", {}).get("estimated_cost_saved", 0),
            "estimated_total_value": (validation_outputs.get("executive_report") or {}).get("roi", {}).get("estimated_total_value", 0),
        },
        "security": {"audit_events": 0, "security_risk_level": executive.get("risk", {}).get("security_risk_level", "Low"), "compliance_risk_level": executive.get("risk", {}).get("compliance_risk", "Low")},
        "external_syncs": len(syncs),
    }
