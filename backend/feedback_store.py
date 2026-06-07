import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import USE_DATABASE
from dataset_store import get_evaluation_result
from models import CaseFeedbackRequest, DatasetCase


FEEDBACK_DIR = Path(__file__).resolve().parent / "storage" / "feedback"
LABELS = {"contradiction", "no_contradiction", "uncertain"}
SEVERITIES = {"Critical", "High", "Medium", "Low", "None"}
STATUSES = {"reviewed", "unreviewed"}


def ensure_feedback_dir():
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write(path: Path, payload: dict):
    ensure_feedback_dir()
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def _all_feedback() -> list[dict]:
    if USE_DATABASE:
        from database.repositories import FeedbackRepository

        return FeedbackRepository.list()
    ensure_feedback_dir()
    items = []
    for path in FEEDBACK_DIR.glob("*.json"):
        try:
            items.append(_read(path))
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)


def _find_existing(evaluation_id: str, case_id: str) -> dict | None:
    return next(
        (
            item
            for item in _all_feedback()
            if item.get("evaluation_id") == evaluation_id and item.get("case_id") == case_id
        ),
        None,
    )


def _validate_feedback(request: CaseFeedbackRequest):
    if request.corrected_label not in LABELS:
        raise ValueError("Invalid corrected label.")
    if request.corrected_severity not in SEVERITIES:
        raise ValueError("Invalid corrected severity.")
    if request.review_status not in STATUSES:
        raise ValueError("Invalid review status.")


def save_case_feedback(request: CaseFeedbackRequest, workspace_id: str = "") -> dict:
    _validate_feedback(request)
    existing = _find_existing(request.evaluation_id, request.case_id)
    now = _now()
    payload = request.model_dump()
    if workspace_id:
        payload["workspace_id"] = workspace_id
    payload["feedback_id"] = existing["feedback_id"] if existing else str(uuid4())
    payload["created_at"] = existing.get("created_at", now) if existing else now
    payload["updated_at"] = now
    payload["is_prediction_correct_after_review"] = (
        request.original_predicted_label == request.corrected_label
        and request.original_predicted_drift_type == request.corrected_drift_type
        and request.original_predicted_severity == request.corrected_severity
    )
    if USE_DATABASE:
        from database.repositories import FeedbackRepository

        FeedbackRepository.create(payload)
    else:
        _write(FEEDBACK_DIR / f"{payload['feedback_id']}.json", payload)
    return payload


def list_feedback(workspace_id: str = "") -> list[dict]:
    items = _all_feedback()
    if workspace_id:
        return [item for item in items if item.get("workspace_id", "") == workspace_id]
    return items


def get_feedback(feedback_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import FeedbackRepository

        return next((item for item in FeedbackRepository.list() if item.get("feedback_id") == feedback_id), None)
    path = FEEDBACK_DIR / f"{feedback_id}.json"
    if not path.exists():
        return None
    try:
        return _read(path)
    except (json.JSONDecodeError, OSError):
        return None


def get_feedback_for_evaluation(evaluation_id: str, workspace_id: str = "") -> list[dict]:
    return [
        item
        for item in _all_feedback()
        if item.get("evaluation_id") == evaluation_id
        and (not workspace_id or item.get("workspace_id", "") == workspace_id)
    ]


def delete_feedback(feedback_id: str) -> bool:
    if USE_DATABASE:
        from database.repositories import FeedbackRepository

        return FeedbackRepository.delete(feedback_id)
    path = FEEDBACK_DIR / f"{feedback_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def _dist(items: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return out


def calculate_feedback_summary(evaluation_id: str) -> dict:
    evaluation = get_evaluation_result(evaluation_id)
    if not evaluation:
        raise FileNotFoundError("Evaluation result not found.")
    result_cases = evaluation.get("result", {}).get("results", [])
    feedback = get_feedback_for_evaluation(evaluation_id)
    reviewed = [item for item in feedback if item.get("review_status") == "reviewed"]
    corrected = [
        item for item in reviewed
        if not item.get("is_prediction_correct_after_review")
    ]
    confirmed = [item for item in reviewed if item.get("is_prediction_correct_after_review")]
    correction_counts = {"label": 0, "drift_type": 0, "severity": 0}
    for item in corrected:
        if item.get("original_predicted_label") != item.get("corrected_label"):
            correction_counts["label"] += 1
        if item.get("original_predicted_drift_type") != item.get("corrected_drift_type"):
            correction_counts["drift_type"] += 1
        if item.get("original_predicted_severity") != item.get("corrected_severity"):
            correction_counts["severity"] += 1
    most_common = max(correction_counts, key=correction_counts.get) if corrected else "none"
    total_cases = len(result_cases)
    return {
        "evaluation_id": evaluation_id,
        "total_cases": total_cases,
        "reviewed_cases": len(reviewed),
        "unreviewed_cases": max(total_cases - len(reviewed), 0),
        "corrected_cases": len(corrected),
        "confirmed_correct_cases": len(confirmed),
        "most_common_correction_type": most_common,
        "corrected_label_distribution": _dist([item["corrected_label"] for item in feedback]),
        "corrected_drift_type_distribution": _dist([item["corrected_drift_type"] for item in feedback]),
        "corrected_severity_distribution": _dist([item["corrected_severity"] for item in feedback]),
        "human_review_completion_percentage": round((len(reviewed) / total_cases) * 100, 2) if total_cases else 0,
    }


def _case_inputs_from_result(case_result: dict) -> dict:
    return case_result.get("input", {}) or {}


def _corrected_case(case_result: dict, feedback_by_case: dict[str, dict]) -> dict:
    case_id = case_result.get("case_id", "")
    feedback = feedback_by_case.get(case_id, {})
    return {
        "case_id": case_id,
        "title": case_result.get("title", ""),
        "documentation": _case_inputs_from_result(case_result).get("documentation", ""),
        "code": _case_inputs_from_result(case_result).get("code", ""),
        "jira": _case_inputs_from_result(case_result).get("jira", ""),
        "commit": _case_inputs_from_result(case_result).get("commit", ""),
        "logs": _case_inputs_from_result(case_result).get("logs", ""),
        "database_config": _case_inputs_from_result(case_result).get("database_config", ""),
        "expected_label": feedback.get("corrected_label", case_result.get("expected_label", "")),
        "expected_drift_type": feedback.get("corrected_drift_type", case_result.get("expected_drift_type", "")),
        "expected_severity": feedback.get("corrected_severity", case_result.get("expected_severity", "")),
    }


def export_corrected_dataset(evaluation_id: str) -> list[dict]:
    evaluation = get_evaluation_result(evaluation_id)
    if not evaluation:
        raise FileNotFoundError("Evaluation result not found.")
    feedback_by_case = {item["case_id"]: item for item in get_feedback_for_evaluation(evaluation_id)}
    return [_corrected_case(case, feedback_by_case) for case in evaluation.get("result", {}).get("results", [])]


def build_training_dataset(evaluation_id: str) -> list[dict]:
    evaluation = get_evaluation_result(evaluation_id)
    if not evaluation:
        raise FileNotFoundError("Evaluation result not found.")
    corrected_cases = export_corrected_dataset(evaluation_id)
    feedback_by_case = {item["case_id"]: item for item in get_feedback_for_evaluation(evaluation_id)}
    items = []
    for case in corrected_cases:
        feedback = feedback_by_case.get(case["case_id"], {})
        items.append({
            "input": {
                "documentation": case["documentation"],
                "code": case["code"],
                "jira": case["jira"],
                "commit": case["commit"],
                "logs": case["logs"],
                "database_config": case["database_config"],
            },
            "target": {
                "label": case["expected_label"],
                "drift_type": case["expected_drift_type"],
                "severity": case["expected_severity"],
                "explanation": feedback.get("reviewer_notes") or feedback.get("correction_reason", ""),
            },
            "metadata": {
                "case_id": case["case_id"],
                "evaluation_id": evaluation_id,
                "source": "human_corrected" if case["case_id"] in feedback_by_case else "evaluation_original",
            },
        })
    return items
