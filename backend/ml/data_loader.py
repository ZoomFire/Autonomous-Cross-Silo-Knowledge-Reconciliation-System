import json
import random
from pathlib import Path

from database.repositories import BenchmarkExampleRepository, FeedbackRepository, TrainingDatasetExportRepository
from .feature_builder import build_input_text


def _target_from_record(record: dict) -> dict:
    target = record.get("target", {})
    case = record.get("driftguard_case", {})
    return {
        "label": target.get("label") or case.get("expected_label", ""),
        "severity": target.get("severity") or case.get("expected_severity", ""),
        "drift_type": target.get("drift_type") or case.get("expected_drift_type", ""),
    }


def _normalize_training_record(record: dict) -> dict:
    target = _target_from_record(record)
    input_payload = record.get("input") or record.get("driftguard_case") or {}
    normalized = {
        "input": input_payload,
        "label": target["label"],
        "severity": target["severity"],
        "drift_type": target["drift_type"],
        "metadata": record.get("metadata", {}),
    }
    normalized["text"] = build_input_text(normalized)
    return normalized


def _records_from_training_export(export: dict) -> list[dict]:
    path = Path(export.get("export_path", ""))
    if not path.exists():
        return []
    if path.suffix.lower() == ".jsonl":
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            assistant = next((message for message in payload.get("messages", []) if message.get("role") == "assistant"), {})
            user = next((message for message in payload.get("messages", []) if message.get("role") == "user"), {})
            try:
                target = json.loads(assistant.get("content", "{}"))
            except json.JSONDecodeError:
                target = {}
            records.append({
                "input": {"context": user.get("content", "")},
                "target": target,
                "metadata": payload.get("metadata", {}),
            })
        return records
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        records = []
        for split_items in payload.values():
            if isinstance(split_items, list):
                records.extend(split_items)
        return records
    return payload if isinstance(payload, list) else []


def _human_corrected_examples(workspace_id: str) -> list[dict]:
    records = []
    for feedback in FeedbackRepository.list(workspace_id):
        records.append({
            "input": {"context": feedback.get("reviewer_notes", "") or feedback.get("correction_reason", "")},
            "target": {
                "label": feedback.get("corrected_label", ""),
                "severity": feedback.get("corrected_severity", ""),
                "drift_type": feedback.get("corrected_drift_type", ""),
            },
            "metadata": {"source_dataset": "human_corrected", "feedback_id": feedback.get("feedback_id", "")},
        })
    return records


def load_training_examples(workspace_id: str, training_export_id: str | None = None, benchmark_ids: list[str] | None = None, include_human_corrected: bool = True, max_examples: int = 5000) -> list[dict]:
    raw_records = []
    if training_export_id:
        export = TrainingDatasetExportRepository.get_by_id(training_export_id)
        if export and export.get("workspace_id") == workspace_id:
            raw_records.extend(_records_from_training_export(export))
    for benchmark_id in benchmark_ids or []:
        raw_records.extend(BenchmarkExampleRepository.list(benchmark_id=benchmark_id, limit=max_examples))
    if include_human_corrected:
        raw_records.extend(_human_corrected_examples(workspace_id))
    examples = [_normalize_training_record(record) for record in raw_records]
    examples = [item for item in examples if item.get("text")]
    if len(examples) > max_examples:
        random.Random(42).shuffle(examples)
        examples = examples[:max_examples]
    if not examples:
        raise ValueError("No training examples found. Export benchmark training data or include corrected human examples first.")
    return examples

