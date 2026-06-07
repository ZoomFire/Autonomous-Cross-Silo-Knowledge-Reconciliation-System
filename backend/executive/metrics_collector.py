from datetime import datetime, timezone

from audit_store import build_compliance_risk_summary
from database.repositories import (
    DatasetRepository,
    DeployedModelRepository,
    EvaluationRepository,
    ExternalSyncRecordRepository,
    FeedbackRepository,
    IncidentRepository,
    NotificationDeliveryRepository,
)
from monitoring_store import list_alerts


def _parse_dt(value: str):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _count_drift_cases(evaluations: list[dict]) -> tuple[int, int, int]:
    drift_cases = critical = high = 0
    for summary in evaluations:
        detail = EvaluationRepository.get_by_id(summary.get("evaluation_id", "")) or {}
        for case in (detail.get("result") or {}).get("cases", []):
            label = str(case.get("predicted_label") or case.get("label") or "").lower()
            severity = str(case.get("predicted_severity") or case.get("severity") or "").lower()
            if label in {"contradiction", "drift", "manual_review"} or severity in {"critical", "high"}:
                drift_cases += 1
            if severity == "critical":
                critical += 1
            if severity == "high":
                high += 1
    return drift_cases, critical, high


def _average_resolution_hours(incidents: list[dict]) -> float:
    durations = []
    for incident in incidents:
        start = _parse_dt(incident.get("created_at", ""))
        end = _parse_dt(incident.get("resolved_at", "")) or _parse_dt(incident.get("closed_at", ""))
        if start and end and end >= start:
            durations.append((end - start).total_seconds() / 3600)
    return round(sum(durations) / len(durations), 2) if durations else 0


def _risk_level(score: int) -> str:
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Medium"
    return "Low"


def collect_executive_metrics(workspace_id: str) -> dict:
    datasets = DatasetRepository.list(workspace_id)
    evaluations = EvaluationRepository.list(workspace_id)
    incidents = IncidentRepository.list_by_workspace(workspace_id)
    alerts = list_alerts(workspace_id)
    deployed_models = DeployedModelRepository.list_by_workspace(workspace_id)
    sync_records = ExternalSyncRecordRepository.list_by_workspace(workspace_id, limit=500)
    delivery_logs = NotificationDeliveryRepository.list_by_workspace(workspace_id, limit=500)
    feedback_items = FeedbackRepository.list(workspace_id=workspace_id)
    drift_cases, critical_cases, high_cases = _count_drift_cases(evaluations)
    now = datetime.now(timezone.utc)
    overdue = 0
    for incident in incidents:
        due = _parse_dt(incident.get("sla_due_at", ""))
        if due and due < now and incident.get("status") not in {"resolved", "closed"}:
            overdue += 1
    resolved = [item for item in incidents if item.get("status") in {"resolved", "closed"}]
    failed_syncs = [item for item in sync_records if item.get("status") == "failed"]
    sync_success = [item for item in sync_records if item.get("status") == "success"]
    review_done = [item for item in feedback_items if item.get("review_status") in {"reviewed", "approved", "corrected"}]
    review_completion_rate = round((len(review_done) / len(feedback_items)) * 100, 2) if feedback_items else 0
    automation_rate = round((len(sync_success) / max(len(incidents), 1)) * 100, 2) if incidents else 0
    external_success_rate = round((len(sync_success) / len(sync_records)) * 100, 2) if sync_records else 0
    drift_risk_score = min(100, critical_cases * 20 + high_cases * 10 + overdue * 8 + len([a for a in alerts if a.get("status") == "open"]) * 5)
    compliance = build_compliance_risk_summary(workspace_id)
    compliance_score = int(compliance.get("risk_score", 0) or 0)
    model_health_risk = "Low" if deployed_models else "Medium"
    top_components = []
    for alert in alerts[:5]:
        top_components.append({
            "component": alert.get("dataset_name") or alert.get("metric_name") or "Workspace",
            "risk_score": 80 if alert.get("severity") == "Critical" else 60 if alert.get("severity") == "High" else 35,
            "case_count": len(alert.get("related_cases", [])),
            "severity": alert.get("severity", "Medium"),
        })
    recommendations = []
    if critical_cases:
        recommendations.append("Prioritize critical drift cases and assign executive-visible owners.")
    if overdue:
        recommendations.append("Reduce overdue incidents by reviewing SLA ownership and escalation rules.")
    if failed_syncs:
        recommendations.append("Review failed external syncs before relying on workflow automation.")
    if not deployed_models:
        recommendations.append("Deploy at least one approved local model or document rule-based fallback ownership.")
    if not recommendations:
        recommendations.append("Maintain current monitoring cadence and continue collecting review feedback.")
    return {
        "workspace_id": workspace_id,
        "summary": {
            "datasets": len(datasets),
            "evaluations": len(evaluations),
            "drift_cases": drift_cases,
            "critical_drift_cases": critical_cases,
            "high_drift_cases": high_cases,
            "incidents": len(incidents),
            "open_incidents": sum(1 for item in incidents if item.get("status") in {"open", "triaged", "in_progress", "escalated"}),
            "resolved_incidents": len(resolved),
            "overdue_incidents": overdue,
            "alerts": len(alerts),
            "deployed_models": len(deployed_models),
            "external_syncs": len(sync_records),
            "model_drift_alerts": 0,
            "active_learning_pending_items": 0,
            "active_learning_reviewed_items": len(review_done),
            "webhook_notifications": len(delivery_logs),
        },
        "risk": {
            "drift_risk_score": drift_risk_score,
            "security_risk_level": "Low",
            "model_health_risk": model_health_risk,
            "compliance_risk": _risk_level(compliance_score),
        },
        "operations": {
            "average_resolution_time_hours": _average_resolution_hours(incidents),
            "review_completion_rate": review_completion_rate,
            "automation_rate": automation_rate,
            "external_sync_success_rate": external_success_rate,
        },
        "top_risky_components": top_components,
        "recommendations": recommendations,
    }
