import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import USE_DATABASE
from dataset_evaluator import evaluate_dataset_cases
from dataset_store import get_dataset, save_evaluation_result
from impact_graph import build_evaluation_impact_graph
from models import DatasetCase
from root_cause_analyzer import build_root_cause_report


BASE_DIR = Path(__file__).resolve().parent / "storage" / "monitoring"
RULES_DIR = BASE_DIR / "rules"
RUNS_DIR = BASE_DIR / "runs"
ALERTS_DIR = BASE_DIR / "alerts"

DEFAULT_THRESHOLDS = {
    "minimum_accuracy": 80,
    "minimum_label_accuracy": 85,
    "minimum_drift_type_accuracy": 75,
    "minimum_severity_accuracy": 70,
    "max_critical_cases": 0,
    "max_high_cases": 2,
    "max_average_priority_score": 70,
}
DEFAULT_ALERT_SETTINGS = {
    "alert_on_accuracy_drop": True,
    "alert_on_critical_drift": True,
    "alert_on_high_priority_component": True,
    "alert_on_regression": True,
}


def ensure_monitoring_dirs():
    for folder in [RULES_DIR, RUNS_DIR, ALERTS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write(path: Path, payload: dict):
    ensure_monitoring_dirs()
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def _list(folder: Path) -> list[dict]:
    ensure_monitoring_dirs()
    items = []
    for path in folder.glob("*.json"):
        try:
            items.append(_read(path))
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def create_monitoring_rule(payload: dict) -> dict:
    dataset_id = payload.get("dataset_id")
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise FileNotFoundError("Dataset not found.")
    metadata = dataset["metadata"]
    workspace_id = payload.get("workspace_id") or metadata.get("workspace_id", "")
    now = _now()
    rule = {
        "rule_id": str(uuid4()),
        "name": payload.get("name", "").strip(),
        "dataset_id": dataset_id,
        "dataset_name": metadata.get("name", "Saved Dataset"),
        "workspace_id": workspace_id,
        "created_at": now,
        "updated_at": now,
        "enabled": bool(payload.get("enabled", True)),
        "description": payload.get("description", ""),
        "thresholds": {**DEFAULT_THRESHOLDS, **payload.get("thresholds", {})},
        "alert_settings": {**DEFAULT_ALERT_SETTINGS, **payload.get("alert_settings", {})},
    }
    if not rule["name"]:
        raise ValueError("Rule name is required.")
    if USE_DATABASE:
        from database.repositories import MonitoringRuleRepository

        MonitoringRuleRepository.create(rule)
    else:
        _write(RULES_DIR / f"{rule['rule_id']}.json", rule)
    return rule


def list_monitoring_rules(workspace_id: str = "") -> list[dict]:
    if USE_DATABASE:
        from database.repositories import MonitoringRuleRepository

        return MonitoringRuleRepository.list(workspace_id)
    rules = _list(RULES_DIR)
    if workspace_id:
        return [rule for rule in rules if rule.get("workspace_id", "") == workspace_id]
    return rules


def get_monitoring_rule(rule_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import MonitoringRuleRepository

        return MonitoringRuleRepository.get_by_id(rule_id)
    path = RULES_DIR / f"{rule_id}.json"
    return _read(path) if path.exists() else None


def update_monitoring_rule(rule_id: str, payload: dict) -> dict | None:
    rule = get_monitoring_rule(rule_id)
    if not rule:
        return None
    for key in ["name", "description", "enabled"]:
        if key in payload:
            rule[key] = payload[key]
    if "thresholds" in payload:
        rule["thresholds"] = {**rule.get("thresholds", {}), **payload["thresholds"]}
    if "alert_settings" in payload:
        rule["alert_settings"] = {**rule.get("alert_settings", {}), **payload["alert_settings"]}
    rule["updated_at"] = _now()
    if USE_DATABASE:
        from database.repositories import MonitoringRuleRepository

        MonitoringRuleRepository.create(rule)
    else:
        _write(RULES_DIR / f"{rule_id}.json", rule)
    return rule


def delete_monitoring_rule(rule_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import MonitoringRuleRepository

        return MonitoringRuleRepository.delete(rule_id)
    path = RULES_DIR / f"{rule_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def _alert_severity(metric: str, actual: float, threshold: float) -> str:
    if metric in {"critical_cases", "average_priority_score"} and actual > threshold:
        return "Critical" if actual >= 85 or metric == "critical_cases" else "High"
    gap = threshold - actual
    if gap > 20:
        return "Critical"
    if gap >= 10:
        return "High"
    if gap >= 5:
        return "Medium"
    return "Low"


def save_alert(alert: dict) -> dict:
    alert["alert_id"] = alert.get("alert_id") or str(uuid4())
    alert["created_at"] = alert.get("created_at") or _now()
    alert["status"] = alert.get("status", "open")
    if USE_DATABASE:
        from database.repositories import AlertRepository

        AlertRepository.create(alert)
    else:
        _write(ALERTS_DIR / f"{alert['alert_id']}.json", alert)
    return alert


def generate_alerts_from_evaluation(rule: dict, run: dict, root_report: dict, impact_graph: dict) -> list[dict]:
    thresholds = rule["thresholds"]
    alerts = []

    def add(alert_type, metric, actual, threshold, title, message, related_cases=None):
        alerts.append(save_alert({
            "rule_id": rule["rule_id"],
            "run_id": run["run_id"],
            "dataset_id": rule["dataset_id"],
            "dataset_name": rule["dataset_name"],
            "workspace_id": rule.get("workspace_id", ""),
            "alert_type": alert_type,
            "severity": _alert_severity(metric, actual, threshold),
            "title": title,
            "message": message,
            "metric_name": metric,
            "actual_value": actual,
            "threshold_value": threshold,
            "recommended_action": "Review critical cases, inspect root cause report, and assign to suggested owner.",
            "related_evaluation_id": run["evaluation_id"],
            "related_cases": related_cases or [],
        }))

    for key, alert_type in [
        ("accuracy", "accuracy_below_threshold"),
        ("label_accuracy", "label_accuracy_below_threshold"),
        ("drift_type_accuracy", "drift_type_accuracy_below_threshold"),
        ("severity_accuracy", "severity_accuracy_below_threshold"),
    ]:
        threshold_key = f"minimum_{key}"
        if run[key] < thresholds[threshold_key]:
            add(alert_type, key, run[key], thresholds[threshold_key], f"{key.replace('_', ' ').title()} below threshold", f"{run[key]}% is below threshold {thresholds[threshold_key]}%.")

    if run["critical_cases"] > thresholds["max_critical_cases"]:
        cases = [case["case_id"] for case in root_report["cases"] if case["priority_level"] == "Critical"]
        add("critical_drift", "critical_cases", run["critical_cases"], thresholds["max_critical_cases"], f"Critical drift detected in {rule['dataset_name']}", f"{run['critical_cases']} critical drift cases were found. Threshold allows {thresholds['max_critical_cases']}.", cases)
    if run["high_cases"] > thresholds["max_high_cases"]:
        add("high_drift_volume", "high_cases", run["high_cases"], thresholds["max_high_cases"], "High drift volume detected", f"{run['high_cases']} high-priority cases exceed threshold {thresholds['max_high_cases']}.")
    if run["average_priority_score"] > thresholds["max_average_priority_score"]:
        add("high_priority_score", "average_priority_score", run["average_priority_score"], thresholds["max_average_priority_score"], "Average priority score is high", f"Average priority score {run['average_priority_score']} exceeds threshold {thresholds['max_average_priority_score']}.")
    for component in impact_graph.get("most_risky_components", []):
        if component["risk_level"] in {"Critical", "High"}:
            add("risky_component_detected", "component_risk_score", component["risk_score"], 70, f"Risky component detected: {component['component']}", f"{component['component']} component risk is {component['risk_score']}.")
            break
    return alerts


def save_monitoring_run(run: dict) -> dict:
    if USE_DATABASE:
        from database.repositories import MonitoringRunRepository

        MonitoringRunRepository.create(run)
    else:
        _write(RUNS_DIR / f"{run['run_id']}.json", run)
    return run


def run_monitoring_check(rule_id: str) -> dict:
    rule = get_monitoring_rule(rule_id)
    if not rule:
        raise FileNotFoundError("Monitoring rule not found.")
    if not rule.get("enabled", True):
        raise PermissionError("Monitoring rule is disabled.")
    dataset = get_dataset(rule["dataset_id"])
    if not dataset:
        raise FileNotFoundError("Dataset not found.")
    cases = [DatasetCase(**case) for case in dataset.get("cases", [])]
    evaluation = evaluate_dataset_cases(cases)
    eval_meta = save_evaluation_result(evaluation, rule["dataset_id"], rule["dataset_name"], rule.get("workspace_id", ""))
    root_report = build_root_cause_report(evaluation, eval_meta["evaluation_id"])
    impact_graph = build_evaluation_impact_graph(evaluation, eval_meta["evaluation_id"])
    run = {
        "run_id": str(uuid4()),
        "rule_id": rule_id,
        "rule_name": rule["name"],
        "dataset_id": rule["dataset_id"],
        "dataset_name": rule["dataset_name"],
        "workspace_id": rule.get("workspace_id", ""),
        "created_at": _now(),
        "status": "completed",
        "evaluation_id": eval_meta["evaluation_id"],
        "accuracy": evaluation.accuracy,
        "label_accuracy": evaluation.label_accuracy,
        "drift_type_accuracy": evaluation.drift_type_accuracy,
        "severity_accuracy": evaluation.severity_accuracy,
        "critical_cases": root_report["critical_priority_cases"],
        "high_cases": root_report["high_priority_cases"],
        "average_priority_score": root_report["average_priority_score"],
        "alerts_created": 0,
        "summary": "Monitoring completed.",
    }
    alerts = generate_alerts_from_evaluation(rule, run, root_report, impact_graph)
    run["alerts_created"] = len(alerts)
    if alerts:
        run["summary"] = "Monitoring detected threshold violations and created alerts."
    save_monitoring_run(run)
    return {"run": run, "alerts": alerts}


def list_monitoring_runs(workspace_id: str = "") -> list[dict]:
    if USE_DATABASE:
        from database.repositories import MonitoringRunRepository

        return MonitoringRunRepository.list(workspace_id)
    runs = _list(RUNS_DIR)
    if workspace_id:
        return [run for run in runs if run.get("workspace_id", "") == workspace_id]
    return runs


def get_monitoring_run(run_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import MonitoringRunRepository

        return MonitoringRunRepository.get_by_id(run_id)
    path = RUNS_DIR / f"{run_id}.json"
    return _read(path) if path.exists() else None


def delete_monitoring_run(run_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import MonitoringRunRepository

        return MonitoringRunRepository.delete(run_id)
    path = RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def list_alerts(workspace_id: str = "") -> list[dict]:
    if USE_DATABASE:
        from database.repositories import AlertRepository

        return AlertRepository.list(workspace_id)
    alerts = _list(ALERTS_DIR)
    if workspace_id:
        return [alert for alert in alerts if alert.get("workspace_id", "") == workspace_id]
    return alerts


def get_alert(alert_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import AlertRepository

        return AlertRepository.get_by_id(alert_id)
    path = ALERTS_DIR / f"{alert_id}.json"
    return _read(path) if path.exists() else None


def mark_alert_status(alert_id: str, status: str) -> dict | None:
    if status not in {"open", "acknowledged", "resolved"}:
        raise ValueError("Invalid alert status.")
    alert = get_alert(alert_id)
    if not alert:
        return None
    alert["status"] = status
    if USE_DATABASE:
        from database.repositories import AlertRepository

        AlertRepository.create(alert)
    else:
        _write(ALERTS_DIR / f"{alert_id}.json", alert)
    return alert


def delete_alert(alert_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import AlertRepository

        return AlertRepository.delete(alert_id)
    path = ALERTS_DIR / f"{alert_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def export_alerts_markdown(alerts: list[dict]) -> str:
    counts = {status: sum(1 for alert in alerts if alert.get("status") == status) for status in ["open", "acknowledged", "resolved"]}
    severity_counts = {sev: sum(1 for alert in alerts if alert.get("severity") == sev) for sev in ["Critical", "High", "Medium", "Low"]}
    lines = [
        "# DriftGuard AI Monitoring Alerts Report",
        "",
        "## Summary",
        f"- Total alerts: {len(alerts)}",
        f"- Open alerts: {counts['open']}",
        f"- Acknowledged alerts: {counts['acknowledged']}",
        f"- Resolved alerts: {counts['resolved']}",
        f"- Critical alerts: {severity_counts['Critical']}",
        f"- High alerts: {severity_counts['High']}",
        f"- Medium alerts: {severity_counts['Medium']}",
        f"- Low alerts: {severity_counts['Low']}",
        "",
        "## Alerts",
    ]
    for alert in alerts:
        lines.extend([
            f"### {alert['alert_id']} - {alert['title']}",
            f"- Status: {alert['status']}",
            f"- Severity: {alert['severity']}",
            f"- Alert type: {alert['alert_type']}",
            f"- Dataset: {alert['dataset_name']}",
            f"- Created at: {alert['created_at']}",
            f"- Metric: {alert['metric_name']}",
            f"- Actual value: {alert['actual_value']}",
            f"- Threshold value: {alert['threshold_value']}",
            f"- Related evaluation: {alert['related_evaluation_id']}",
            f"- Related cases: {', '.join(alert.get('related_cases', []))}",
            f"- Recommended action: {alert['recommended_action']}",
            "",
        ])
    return "\n".join(lines)
