from datetime import datetime, timezone

from security_utils import sanitize_metadata

from .metrics_collector import collect_executive_metrics
from .roi_calculator import calculate_roi, format_inr


def _summary_text(metrics: dict, roi: dict) -> str:
    summary = metrics.get("summary", {})
    return (
        f"DriftGuard AI analyzed {summary.get('datasets', 0)} datasets and detected "
        f"{summary.get('drift_cases', 0)} drift cases, including {summary.get('critical_drift_cases', 0)} critical issues. "
        f"The system created {summary.get('incidents', 0)} incidents and recorded {summary.get('external_syncs', 0)} external workflow syncs. "
        f"Estimated value generated is {format_inr(roi.get('estimated_total_value', 0))}."
    )


def build_executive_report(workspace_id: str, user_id: str, assumptions: dict | None = None, redact: bool = False) -> dict:
    metrics = collect_executive_metrics(workspace_id)
    roi = calculate_roi(metrics, assumptions)
    summary = metrics.get("summary", {})
    report = {
        "title": "DriftGuard AI Executive Report",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "workspace_id": workspace_id,
        "created_by": user_id,
        "executive_summary": _summary_text(metrics, roi),
        "key_metrics": summary,
        "risk_summary": metrics.get("risk", {}),
        "roi": roi,
        "incident_summary": {
            "total": summary.get("incidents", 0),
            "open": summary.get("open_incidents", 0),
            "resolved": summary.get("resolved_incidents", 0),
            "overdue": summary.get("overdue_incidents", 0),
            "alerts": summary.get("alerts", 0),
        },
        "model_summary": {
            "deployed_models": summary.get("deployed_models", 0),
            "model_health_risk": metrics.get("risk", {}).get("model_health_risk", "Low"),
        },
        "security_compliance_summary": {
            "security_risk_level": metrics.get("risk", {}).get("security_risk_level", "Low"),
            "compliance_risk": metrics.get("risk", {}).get("compliance_risk", "Low"),
        },
        "integration_summary": {
            "external_syncs": summary.get("external_syncs", 0),
            "external_sync_success_rate": metrics.get("operations", {}).get("external_sync_success_rate", 0),
            "webhook_notifications": summary.get("webhook_notifications", 0),
        },
        "top_risky_components": metrics.get("top_risky_components", []),
        "recommendations": metrics.get("recommendations", []),
        "next_steps": [
            "Review critical and high drift cases with engineering leadership.",
            "Assign owners for open and overdue incidents.",
            "Validate external workflow sync health before demos or executive reviews.",
            "Recalculate ROI after the next evaluation cycle.",
        ],
    }
    return sanitize_metadata(report) if redact else report


def _section_dict(data: dict) -> str:
    return "\n".join(f"- {key}: {value}" for key, value in data.items()) or "- None"


def export_executive_report_markdown(report: dict) -> str:
    lines = [
        "# DriftGuard AI Executive Report",
        "",
        "## Executive Summary",
        "",
        report.get("executive_summary", ""),
        "",
        "## Key Metrics",
        "",
        _section_dict(report.get("key_metrics", {})),
        "",
        "## Risk Summary",
        "",
        _section_dict(report.get("risk_summary", {})),
        "",
        "## ROI Estimate",
        "",
        _section_dict(report.get("roi", {})),
        "",
        "## Incident and Alert Summary",
        "",
        _section_dict(report.get("incident_summary", {})),
        "",
        "## Model Health Summary",
        "",
        _section_dict(report.get("model_summary", {})),
        "",
        "## Security and Compliance Summary",
        "",
        _section_dict(report.get("security_compliance_summary", {})),
        "",
        "## Integration Summary",
        "",
        _section_dict(report.get("integration_summary", {})),
        "",
        "## Top Risky Components",
        "",
    ]
    components = report.get("top_risky_components", [])
    lines.extend([f"- {item.get('component', 'Unknown')}: score {item.get('risk_score', 0)}, {item.get('severity', 'Medium')}" for item in components] or ["- None"])
    lines.extend(["", "## Recommendations", ""])
    lines.extend([f"- {item}" for item in report.get("recommendations", [])] or ["- None"])
    lines.extend(["", "## Next Steps", ""])
    lines.extend([f"- {item}" for item in report.get("next_steps", [])] or ["- None"])
    return "\n".join(lines) + "\n"
