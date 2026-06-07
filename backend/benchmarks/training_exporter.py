import json
import random
from pathlib import Path


SYSTEM_PROMPT = "You are DriftGuard AI, an enterprise architectural drift detection assistant."


def create_train_validation_test_split(examples: list[dict], train_ratio: float = 0.8, validation_ratio: float = 0.1, test_ratio: float = 0.1, seed: int = 42) -> list[dict]:
    total = train_ratio + validation_ratio + test_ratio
    if total <= 0:
        train_ratio, validation_ratio, test_ratio = 0.8, 0.1, 0.1
        total = 1
    train_ratio, validation_ratio, test_ratio = train_ratio / total, validation_ratio / total, test_ratio / total
    shuffled = list(examples)
    random.Random(seed).shuffle(shuffled)
    count = len(shuffled)
    if count == 0:
        return []
    train_end = max(1, int(count * train_ratio)) if count > 1 else 1
    validation_end = train_end + (max(1, int(count * validation_ratio)) if count > 2 else 0)
    validation_end = min(validation_end, count)
    for index, example in enumerate(shuffled):
        if index < train_end:
            example["split"] = "train"
        elif index < validation_end:
            example["split"] = "validation"
        else:
            example["split"] = "test"
    return shuffled


def _training_record(example: dict) -> dict:
    case = example.get("driftguard_case", {})
    return {
        "input": example.get("input", {}),
        "target": example.get("target", {}),
        "metadata": {
            **example.get("metadata", {}),
            "source_dataset": example.get("dataset_type", example.get("metadata", {}).get("source_dataset", "")),
        },
        "driftguard_case": case,
        "split": example.get("split", "unsplit"),
    }


def _jsonl_message(record: dict) -> dict:
    input_payload = record.get("input", {})
    target_payload = record.get("target", {})
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze the following sources for architectural drift: {json.dumps(input_payload, ensure_ascii=False)}"},
            {"role": "assistant", "content": json.dumps(target_payload, ensure_ascii=False)},
        ],
        "metadata": record.get("metadata", {}),
    }


def split_counts(examples: list[dict]) -> dict:
    return {
        "train": sum(1 for item in examples if item.get("split") == "train"),
        "validation": sum(1 for item in examples if item.get("split") == "validation"),
        "test": sum(1 for item in examples if item.get("split") == "test"),
    }


def export_training_jsonl(examples: list[dict], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [_jsonl_message(_training_record(example)) for example in examples]
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + ("\n" if records else ""), encoding="utf-8")
    return path


def export_training_json(examples: list[dict], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped = {"train": [], "validation": [], "test": []}
    for example in examples:
        split = example.get("split") if example.get("split") in grouped else "train"
        grouped[split].append(_training_record(example))
    path.write_text(json.dumps(grouped, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
