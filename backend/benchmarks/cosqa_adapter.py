from .base_adapter import BaseBenchmarkAdapter, first_value, label_from_bool_or_text


class CosQAAdapter(BaseBenchmarkAdapter):
    dataset_type = "cosqa"
    task_type = "code_text_alignment"

    def validate_example(self, raw_example: dict) -> tuple[bool, str]:
        text = first_value(raw_example, ["question", "query", "doc"])
        code = first_value(raw_example, ["code", "code_snippet", "positive_code", "negative_code"])
        return bool(text and code), "missing question/query/doc or code field"

    def convert_to_driftguard_case(self, raw_example: dict, index: int = 1) -> dict:
        text = first_value(raw_example, ["question", "query", "doc"])
        code = first_value(raw_example, ["code", "code_snippet", "positive_code", "negative_code"])
        label = label_from_bool_or_text(raw_example.get("label"))
        if raw_example.get("positive_code") and not raw_example.get("negative_code") and raw_example.get("label") is None:
            label = "no_contradiction"
        if raw_example.get("negative_code") and not raw_example.get("positive_code") and raw_example.get("label") is None:
            label = "contradiction"
        return {
            "case_id": f"COSQA-{index:03d}",
            "title": "CosQA code-text alignment case",
            "documentation": text,
            "code": code,
            "jira": "",
            "commit": "",
            "logs": "",
            "database_config": "",
            "expected_label": label,
            "expected_drift_type": "Code-Documentation Alignment",
            "expected_severity": "Medium",
        }
