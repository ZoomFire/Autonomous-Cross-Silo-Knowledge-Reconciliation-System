from .base_adapter import BaseBenchmarkAdapter, first_value


LABEL_MAP = {
    "entailment": "no_contradiction",
    "contradiction": "contradiction",
    "neutral": "uncertain",
    "-": "uncertain",
}


class SNLIAdapter(BaseBenchmarkAdapter):
    dataset_type = "snli"
    task_type = "contradiction_detection"

    def validate_example(self, raw_example: dict) -> tuple[bool, str]:
        left = first_value(raw_example, ["sentence1", "premise"])
        right = first_value(raw_example, ["sentence2", "hypothesis"])
        return bool(left and right), "missing sentence/premise or hypothesis field"

    def convert_to_driftguard_case(self, raw_example: dict, index: int = 1) -> dict:
        source_label = first_value(raw_example, ["gold_label", "label"], "-").lower()
        return {
            "case_id": f"SNLI-{index:03d}",
            "title": "SNLI contradiction case",
            "documentation": first_value(raw_example, ["sentence1", "premise"]),
            "code": "",
            "jira": first_value(raw_example, ["sentence2", "hypothesis"]),
            "commit": "",
            "logs": "",
            "database_config": "",
            "expected_label": LABEL_MAP.get(source_label, "uncertain"),
            "expected_drift_type": "Logical Contradiction",
            "expected_severity": "Low",
        }

    def convert_to_training_record(self, raw_example: dict, index: int = 1) -> dict:
        record = super().convert_to_training_record(raw_example, index)
        record["metadata"]["domain"] = "general_nli"
        return record
