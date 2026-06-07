from .base_adapter import BaseBenchmarkAdapter, first_value


class SpiderAdapter(BaseBenchmarkAdapter):
    dataset_type = "spider"
    task_type = "database_config_reasoning"

    def validate_example(self, raw_example: dict) -> tuple[bool, str]:
        question = first_value(raw_example, ["question"])
        db_context = first_value(raw_example, ["schema", "query", "db_id", "database_id"])
        return bool(question and db_context), "missing question or database context field"

    def convert_to_driftguard_case(self, raw_example: dict, index: int = 1) -> dict:
        database_config = first_value(raw_example, ["schema", "query", "db_id", "database_id"])
        return {
            "case_id": f"SPIDER-{index:03d}",
            "title": "Spider database/config reasoning case",
            "documentation": first_value(raw_example, ["question"]),
            "code": "",
            "jira": "",
            "commit": "",
            "logs": "",
            "database_config": database_config,
            "expected_label": "uncertain",
            "expected_drift_type": "Database/Config Reasoning",
            "expected_severity": "Medium",
        }
