from .base_adapter import BaseBenchmarkAdapter, first_value


class CommitPackAdapter(BaseBenchmarkAdapter):
    dataset_type = "commitpack"
    task_type = "commit_drift_reasoning"

    def validate_example(self, raw_example: dict) -> tuple[bool, str]:
        commit = first_value(raw_example, ["commit_message", "message"])
        code = first_value(raw_example, ["diff", "patch", "new_code", "code", "old_code"])
        return bool(commit and code), "missing commit message or code/diff field"

    def convert_to_driftguard_case(self, raw_example: dict, index: int = 1) -> dict:
        return {
            "case_id": f"COMMIT-{index:03d}",
            "title": "Commit-code drift reasoning case",
            "documentation": "",
            "code": first_value(raw_example, ["new_code", "code", "diff", "patch", "old_code"]),
            "jira": "",
            "commit": first_value(raw_example, ["commit_message", "message"]),
            "logs": "",
            "database_config": "",
            "expected_label": "uncertain",
            "expected_drift_type": "Commit Introduced Drift",
            "expected_severity": "Medium",
        }
