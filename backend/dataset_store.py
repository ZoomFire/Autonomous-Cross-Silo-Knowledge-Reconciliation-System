import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import USE_DATABASE
from dataset_evaluator import validate_dataset_quality
from models import DatasetCase, DatasetEvaluationResponse


STORAGE_DIR = Path(__file__).resolve().parent / "storage"
DATASETS_DIR = STORAGE_DIR / "datasets"
EVALUATIONS_DIR = STORAGE_DIR / "evaluations"


def ensure_storage_dirs():
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    EVALUATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload):
    ensure_storage_dirs()
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def save_dataset(
    cases: list[DatasetCase],
    filename: str,
    name: str,
    description: str = "",
    version: str = "1.0",
    workspace_id: str = "",
) -> dict:
    ensure_storage_dirs()
    quality_report = validate_dataset_quality(cases)
    dataset_id = str(uuid4())
    now = _utc_now()
    metadata = {
        "dataset_id": dataset_id,
        "name": name,
        "filename": filename,
        "created_at": now,
        "updated_at": now,
        "total_cases": len(cases),
        "label_distribution": quality_report.label_distribution,
        "drift_type_distribution": quality_report.drift_type_distribution,
        "severity_distribution": quality_report.severity_distribution,
        "quality_score": quality_report.quality_score,
        "version": version or "1.0",
        "description": description or "",
        "workspace_id": workspace_id,
    }
    case_payloads = [case.model_dump() for case in cases]
    if USE_DATABASE:
        from database.repositories import DatasetRepository

        DatasetRepository.create(metadata, case_payloads)
    else:
        _write_json(
            DATASETS_DIR / f"{dataset_id}.json",
            {"metadata": metadata, "cases": case_payloads},
        )
    return metadata


def list_datasets(workspace_id: str = "") -> list[dict]:
    if USE_DATABASE:
        from database.repositories import DatasetRepository

        return DatasetRepository.list(workspace_id)
    ensure_storage_dirs()
    datasets: list[dict] = []
    for path in DATASETS_DIR.glob("*.json"):
        try:
            metadata = _read_json(path)["metadata"]
            if workspace_id and metadata.get("workspace_id", "") != workspace_id:
                continue
            datasets.append(metadata)
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return sorted(datasets, key=lambda item: item.get("created_at", ""), reverse=True)


def get_dataset(dataset_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import DatasetRepository

        return DatasetRepository.get_by_id(dataset_id)
    ensure_storage_dirs()
    path = DATASETS_DIR / f"{dataset_id}.json"
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None


def delete_dataset(dataset_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import DatasetRepository

        return DatasetRepository.delete(dataset_id)
    path = DATASETS_DIR / f"{dataset_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def save_evaluation_result(
    result: DatasetEvaluationResponse,
    dataset_id: str,
    dataset_name: str,
    workspace_id: str = "",
) -> dict:
    ensure_storage_dirs()
    evaluation_id = str(uuid4())
    payload = {
        "evaluation_id": evaluation_id,
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "workspace_id": workspace_id,
        "created_at": _utc_now(),
        "total_cases": result.total_cases,
        "accuracy": result.accuracy,
        "label_accuracy": result.label_accuracy,
        "drift_type_accuracy": result.drift_type_accuracy,
        "severity_accuracy": result.severity_accuracy,
        "quality_score": result.dataset_quality_report.quality_score,
        "result": result.model_dump(),
    }
    if USE_DATABASE:
        from database.repositories import EvaluationRepository

        EvaluationRepository.create(payload)
    else:
        _write_json(EVALUATIONS_DIR / f"{evaluation_id}.json", payload)
    return payload


def list_evaluation_history(workspace_id: str = "") -> list[dict]:
    if USE_DATABASE:
        from database.repositories import EvaluationRepository

        return EvaluationRepository.list(workspace_id)
    ensure_storage_dirs()
    evaluations: list[dict] = []
    for path in EVALUATIONS_DIR.glob("*.json"):
        try:
            payload = _read_json(path)
            if workspace_id and payload.get("workspace_id", "") != workspace_id:
                continue
            evaluations.append({key: value for key, value in payload.items() if key != "result"})
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(evaluations, key=lambda item: item.get("created_at", ""), reverse=True)


def get_evaluation_result(evaluation_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import EvaluationRepository

        return EvaluationRepository.get_by_id(evaluation_id)
    ensure_storage_dirs()
    path = EVALUATIONS_DIR / f"{evaluation_id}.json"
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None


def delete_evaluation_result(evaluation_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import EvaluationRepository

        return EvaluationRepository.delete(evaluation_id)
    path = EVALUATIONS_DIR / f"{evaluation_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def _case_statuses(evaluation: dict) -> dict[str, bool]:
    result = evaluation.get("result", {})
    return {
        case.get("case_id", ""): bool(case.get("overall_correct"))
        for case in result.get("results", [])
        if case.get("case_id")
    }


def detect_regression(base: dict, current: dict, newly_failed_cases: list[str]) -> dict:
    accuracy_delta = round(current.get("accuracy", 0) - base.get("accuracy", 0), 2)
    label_delta = round(current.get("label_accuracy", 0) - base.get("label_accuracy", 0), 2)
    drift_delta = round(current.get("drift_type_accuracy", 0) - base.get("drift_type_accuracy", 0), 2)
    severity_delta = round(current.get("severity_accuracy", 0) - base.get("severity_accuracy", 0), 2)
    deltas = {
        "accuracy": accuracy_delta,
        "label accuracy": label_delta,
        "drift type accuracy": drift_delta,
        "severity accuracy": severity_delta,
    }
    worst_metric = min(deltas, key=deltas.get)
    has_regression = accuracy_delta < 0
    summary = (
        f"Accuracy dropped from {base.get('accuracy', 0)}% to {current.get('accuracy', 0)}%. "
        f"{worst_metric.title()} dropped the most."
        if has_regression
        else "No regression detected. Current evaluation is stable or improved."
    )
    return {
        "has_regression": has_regression,
        "regression_summary": summary,
        "accuracy_delta": accuracy_delta,
        "label_accuracy_delta": label_delta,
        "drift_type_accuracy_delta": drift_delta,
        "severity_accuracy_delta": severity_delta,
        "newly_failed_cases": newly_failed_cases,
    }


def compare_evaluations(base_id: str, current_id: str) -> dict | None:
    base = get_evaluation_result(base_id)
    current = get_evaluation_result(current_id)
    if not base or not current:
        return None

    base_statuses = _case_statuses(base)
    current_statuses = _case_statuses(current)
    shared_cases = set(base_statuses) & set(current_statuses)
    newly_failed = sorted(case_id for case_id in shared_cases if base_statuses[case_id] and not current_statuses[case_id])
    newly_passed = sorted(case_id for case_id in shared_cases if not base_statuses[case_id] and current_statuses[case_id])
    unchanged_failed = sorted(case_id for case_id in shared_cases if not base_statuses[case_id] and not current_statuses[case_id])
    regression = detect_regression(base, current, newly_failed)

    return {
        "base_id": base_id,
        "current_id": current_id,
        "accuracy_delta": regression["accuracy_delta"],
        "label_accuracy_delta": regression["label_accuracy_delta"],
        "drift_type_accuracy_delta": regression["drift_type_accuracy_delta"],
        "severity_accuracy_delta": regression["severity_accuracy_delta"],
        "total_cases_delta": current.get("total_cases", 0) - base.get("total_cases", 0),
        "quality_score_delta": current.get("quality_score", 0) - base.get("quality_score", 0),
        "newly_failed_cases": newly_failed,
        "newly_passed_cases": newly_passed,
        "unchanged_failed_cases": unchanged_failed,
        **regression,
    }
