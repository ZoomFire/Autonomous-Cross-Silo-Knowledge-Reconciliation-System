DEFAULT_ROI_ASSUMPTIONS = {
    "manual_review_hours_per_case": 1.5,
    "average_engineer_hourly_cost": 40,
    "incident_cost_per_critical": 500,
    "incident_cost_per_high": 250,
    "automation_time_saved_percentage": 60,
}


def calculate_roi(metrics: dict, assumptions: dict | None = None) -> dict:
    merged = {**DEFAULT_ROI_ASSUMPTIONS, **(assumptions or {})}
    summary = metrics.get("summary", {})
    drift_cases = float(summary.get("drift_cases", 0) or 0)
    critical = float(summary.get("critical_drift_cases", 0) or 0)
    high = float(summary.get("high_drift_cases", 0) or 0)
    manual_hours = drift_cases * float(merged["manual_review_hours_per_case"])
    automated_hours = manual_hours * (1 - float(merged["automation_time_saved_percentage"]) / 100)
    hours_saved = max(manual_hours - automated_hours, 0)
    cost_saved = hours_saved * float(merged["average_engineer_hourly_cost"])
    drift_cost_avoided = critical * float(merged["incident_cost_per_critical"]) + high * float(merged["incident_cost_per_high"])
    total_value = cost_saved + drift_cost_avoided
    return {
        "estimated_manual_hours": round(manual_hours, 2),
        "estimated_automated_hours": round(automated_hours, 2),
        "estimated_hours_saved": round(hours_saved, 2),
        "estimated_cost_saved": round(cost_saved, 2),
        "estimated_drift_cost_avoided": round(drift_cost_avoided, 2),
        "estimated_total_value": round(total_value, 2),
        "assumptions": merged,
        "roi_summary": f"DriftGuard AI is estimated to save {hours_saved:.1f} hours and generate ${total_value:,.0f} in operational value for this workspace.",
    }
