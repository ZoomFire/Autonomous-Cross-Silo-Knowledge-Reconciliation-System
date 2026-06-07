from database.repositories import ResearchResultRepository, ValidationRunRepository


def build_research_report(workspace_id: str, validation_id: str) -> dict:
    validation = ValidationRunRepository.get_by_id(validation_id) or {}
    metrics = validation.get("metrics", {})
    summary = validation.get("summary", {})
    return {
        "title": "DriftGuard AI Validation and Research Results Report",
        "abstract_summary": f"Validation run {validation.get('name', validation_id)} completed with status {validation.get('status', 'unknown')}.",
        "problem_statement": "Enterprise teams need a local way to detect cross-silo architectural drift and prove operational impact.",
        "methodology": "The validation suite runs dataset evaluation, root-cause analysis, incident workflow checks, executive reporting, and integration readiness checks using local DriftGuard data.",
        "dataset_description": f"Dataset: {validation.get('dataset_id') or 'workspace/demo data'}",
        "system_components": ["Dataset Evaluation", "RAG Search", "Root Cause", "Incidents", "Integrations", "Executive ROI"],
        "evaluation_metrics": metrics.get("evaluation", {}),
        "results_summary": summary,
        "ablation_summary": {},
        "business_impact": metrics.get("business", {}),
        "limitations": ["ML and hybrid comparisons are best-effort unless deployed model scoring data exists.", "Ablation results are simulated for MVP where module disabling is not practical."],
        "future_scope": ["Connect external benchmark suites.", "Add scheduled continuous validation.", "Add production-grade statistical significance tests."],
        "conclusion": "DriftGuard AI provides an end-to-end local validation workflow for demo and research reporting without paid APIs.",
    }


def save_research_report(workspace_id: str, validation_id: str, report: dict) -> dict:
    from uuid import uuid4

    return ResearchResultRepository.create({
        "research_result_id": str(uuid4()),
        "workspace_id": workspace_id,
        "validation_id": validation_id,
        "result_type": "metrics_summary",
        "title": report["title"],
        "result": report,
    })


def export_research_report_markdown(report: dict) -> str:
    sections = [
        ("Abstract Summary", report.get("abstract_summary", "")),
        ("Problem Statement", report.get("problem_statement", "")),
        ("Methodology", report.get("methodology", "")),
        ("Dataset Description", report.get("dataset_description", "")),
        ("System Architecture Summary", ", ".join(report.get("system_components", []))),
        ("Evaluation Metrics", report.get("evaluation_metrics", {})),
        ("Results", report.get("results_summary", {})),
        ("Confusion Matrix Summary", "Available in validation result JSON when evaluation output includes it."),
        ("Root Cause Analysis Results", "Root-cause output is summarized in validation metrics."),
        ("Agent Workflow Results", "Agent run counts are included in validation metrics."),
        ("Active Learning Results", "Active-learning metrics are included when available."),
        ("Model Governance and Monitoring Results", "Model comparison metrics are best-effort in MVP."),
        ("Incident and Integration Results", "Incident and external sync metrics are included in validation metrics."),
        ("ROI and Business Impact", report.get("business_impact", {})),
        ("Ablation Study", report.get("ablation_summary", {})),
        ("Limitations", report.get("limitations", [])),
        ("Future Scope", report.get("future_scope", [])),
        ("Conclusion", report.get("conclusion", "")),
    ]
    lines = ["# DriftGuard AI Validation and Research Results Report", ""]
    for title, content in sections:
        lines.extend([f"## {title}", ""])
        if isinstance(content, dict):
            lines.extend([f"- {key}: {value}" for key, value in content.items()] or ["- None"])
        elif isinstance(content, list):
            lines.extend([f"- {item}" for item in content] or ["- None"])
        else:
            lines.append(str(content))
        lines.append("")
    return "\n".join(lines)
