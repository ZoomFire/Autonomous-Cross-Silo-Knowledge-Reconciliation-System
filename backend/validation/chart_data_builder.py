def build_chart_data(metrics: dict) -> dict:
    evaluation = metrics.get("evaluation", {})
    drift = metrics.get("drift", {})
    incidents = metrics.get("incidents", {})
    root_cause = metrics.get("root_cause", {})
    business = metrics.get("business", {})
    return {
        "accuracy_bar_chart": {
            "labels": ["Label", "Drift Type", "Severity"],
            "values": [evaluation.get("label_accuracy", 0), evaluation.get("drift_type_accuracy", 0), evaluation.get("severity_accuracy", 0)],
        },
        "severity_distribution_pie": {
            "labels": ["Critical", "High", "Medium", "Low"],
            "values": [drift.get("critical_drift_cases", 0), drift.get("high_drift_cases", 0), drift.get("medium_drift_cases", 0), drift.get("low_drift_cases", 0)],
        },
        "root_cause_distribution_bar": {
            "labels": list((root_cause.get("responsible_source_distribution") or {}).keys()),
            "values": list((root_cause.get("responsible_source_distribution") or {}).values()),
        },
        "incident_status_chart": {
            "labels": ["Open", "Resolved", "Closed"],
            "values": [incidents.get("open_incidents", 0), incidents.get("resolved_incidents", 0), 0],
        },
        "model_comparison_chart": {"labels": ["Rule-based", "ML", "Hybrid"], "accuracy": [evaluation.get("accuracy", 0), 0, 0], "f1": [0, 0, 0]},
        "roi_chart": {
            "labels": ["Cost Saved", "Drift Cost Avoided", "Total Value"],
            "values": [business.get("estimated_cost_saved", 0), max(business.get("estimated_total_value", 0) - business.get("estimated_cost_saved", 0), 0), business.get("estimated_total_value", 0)],
        },
    }
