ALLOWED_LABELS = {"contradiction", "no_contradiction", "uncertain"}
ALLOWED_SEVERITIES = {"Critical", "High", "Medium", "Low", "None"}

REQUIRED_FIELDS = {
    "contradiction_detection": ["label", "drift_type", "severity", "explanation", "evidence"],
    "root_cause_analysis": ["root_cause_category", "responsible_source", "recommended_fix", "priority_level"],
    "agent_report": ["executive_summary", "risk_level", "recommended_actions"],
}


def validate_llm_output(task_type: str, output: dict) -> dict:
    normalized = dict(output or {})
    missing = [field for field in REQUIRED_FIELDS.get(task_type, []) if field not in normalized or normalized.get(field) in [None, ""]]
    warnings = []

    if task_type == "contradiction_detection":
        if normalized.get("label") not in ALLOWED_LABELS:
            warnings.append("label was outside allowed values and normalized to uncertain.")
            normalized["label"] = "uncertain"
        if normalized.get("severity") not in ALLOWED_SEVERITIES:
            warnings.append("severity was outside allowed values and normalized to None.")
            normalized["severity"] = "None"
        if "evidence" in normalized and not isinstance(normalized["evidence"], list):
            normalized["evidence"] = [normalized["evidence"]]
            warnings.append("evidence was normalized to a list.")

    if task_type == "agent_report":
        if "recommended_actions" in normalized and not isinstance(normalized["recommended_actions"], list):
            normalized["recommended_actions"] = [str(normalized["recommended_actions"])]
            warnings.append("recommended_actions was normalized to a list.")

    return {
        "valid": not missing,
        "missing_fields": missing,
        "warnings": warnings,
        "normalized_output": normalized,
    }

