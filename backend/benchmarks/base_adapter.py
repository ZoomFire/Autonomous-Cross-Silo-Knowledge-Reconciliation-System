import csv
import json
from pathlib import Path


TRAINING_INPUT_FIELDS = ["documentation", "code", "jira", "commit", "logs", "database_config", "question", "context"]


def first_value(raw: dict, keys: list[str], default: str = "") -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return default


def label_from_bool_or_text(value, positive_words: set[str] | None = None) -> str:
    positive_words = positive_words or {"1", "true", "yes", "positive", "match", "matching", "no_contradiction"}
    if value is None or str(value).strip() == "":
        return "uncertain"
    text = str(value).strip().lower()
    if text in positive_words:
        return "no_contradiction"
    if text in {"0", "false", "no", "negative", "mismatch", "contradiction"}:
        return "contradiction"
    return "uncertain"


class BaseBenchmarkAdapter:
    dataset_type = "custom"
    task_type = "custom_driftguard_cases"

    def load_examples(self, file_path: str | Path) -> list[dict]:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for key in ["data", "examples", "rows", "items"]:
                    if isinstance(payload.get(key), list):
                        return [item for item in payload[key] if isinstance(item, dict)]
                return [payload]
            return [item for item in payload if isinstance(item, dict)]
        if suffix in {".jsonl", ".txt"}:
            items = []
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        items.append(parsed)
                except json.JSONDecodeError:
                    continue
            return items
        if suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as file:
                return [dict(row) for row in csv.DictReader(file)]
        raise ValueError("Unsupported benchmark file format.")

    def validate_example(self, raw_example: dict) -> tuple[bool, str]:
        return bool(raw_example), "empty example" if not raw_example else ""

    def convert_to_driftguard_case(self, raw_example: dict, index: int = 1) -> dict:
        raise NotImplementedError

    def convert_to_training_record(self, raw_example: dict, index: int = 1) -> dict:
        case = self.convert_to_driftguard_case(raw_example, index)
        return self.case_to_training_record(case, raw_example)

    def case_to_training_record(self, case: dict, raw_example: dict | None = None) -> dict:
        raw_example = raw_example or {}
        return {
            "input": {
                "documentation": case.get("documentation", ""),
                "code": case.get("code", ""),
                "jira": case.get("jira", ""),
                "commit": case.get("commit", ""),
                "logs": case.get("logs", ""),
                "database_config": case.get("database_config", ""),
                "question": raw_example.get("question", "") or case.get("documentation", ""),
                "context": raw_example.get("context", ""),
            },
            "target": {
                "label": case.get("expected_label", "uncertain"),
                "drift_type": case.get("expected_drift_type", ""),
                "severity": case.get("expected_severity", ""),
                "explanation": raw_example.get("explanation", "") or raw_example.get("reason", ""),
            },
            "metadata": {
                "source_dataset": self.dataset_type,
                "original_id": str(raw_example.get("id") or raw_example.get("guid") or case.get("case_id", "")),
                "task_type": self.task_type,
            },
        }
