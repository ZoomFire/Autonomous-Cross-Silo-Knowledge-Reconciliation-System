from .base_adapter import BaseBenchmarkAdapter


REQUIRED_CASE_FIELDS = [
    "case_id",
    "title",
    "documentation",
    "code",
    "jira",
    "commit",
    "logs",
    "database_config",
    "expected_label",
    "expected_drift_type",
    "expected_severity",
]


class CustomAdapter(BaseBenchmarkAdapter):
    dataset_type = "custom"
    task_type = "custom_driftguard_cases"

    def validate_example(self, raw_example: dict) -> tuple[bool, str]:
        missing = [field for field in REQUIRED_CASE_FIELDS if field not in raw_example]
        return not missing, f"missing fields: {', '.join(missing)}" if missing else ""

    def convert_to_driftguard_case(self, raw_example: dict, index: int = 1) -> dict:
        return {field: raw_example.get(field, "") for field in REQUIRED_CASE_FIELDS}
