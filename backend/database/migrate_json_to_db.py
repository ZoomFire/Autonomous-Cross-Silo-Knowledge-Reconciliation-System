import json
from pathlib import Path

from .db import init_database
from .repositories import (
    AlertRepository,
    AuditRepository,
    DatasetRepository,
    EvaluationRepository,
    FeedbackRepository,
    MonitoringRuleRepository,
    MonitoringRunRepository,
    SessionRepository,
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)


STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"


def _read(path: Path):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return None


def _json_files(folder: Path):
    return list(folder.glob("*.json")) if folder.exists() else []


def migrate_json_to_database() -> dict:
    init_database()
    summary = {
        "users_migrated": 0,
        "sessions_migrated": 0,
        "workspaces_migrated": 0,
        "datasets_migrated": 0,
        "evaluations_migrated": 0,
        "feedback_migrated": 0,
        "monitoring_rules_migrated": 0,
        "monitoring_runs_migrated": 0,
        "alerts_migrated": 0,
        "audit_events_migrated": 0,
        "skipped_or_corrupted": 0,
    }

    for path in _json_files(STORAGE_DIR / "auth" / "users"):
        user = _read(path)
        if not user:
            summary["skipped_or_corrupted"] += 1
            continue
        if not UserRepository.exists(user["user_id"]):
            UserRepository.create(user)
            summary["users_migrated"] += 1

    for path in _json_files(STORAGE_DIR / "auth" / "sessions"):
        session = _read(path)
        if not session:
            summary["skipped_or_corrupted"] += 1
            continue
        if not SessionRepository.exists(session["token"]):
            SessionRepository.create(session)
            summary["sessions_migrated"] += 1

    for path in _json_files(STORAGE_DIR / "workspaces"):
        workspace = _read(path)
        if not workspace:
            summary["skipped_or_corrupted"] += 1
            continue
        if not WorkspaceRepository.exists(workspace["workspace_id"]):
            WorkspaceRepository.create(workspace)
            summary["workspaces_migrated"] += 1
        else:
            for member in workspace.get("members", []):
                WorkspaceMemberRepository.add(workspace["workspace_id"], member["user_id"], member["role"])

    for path in _json_files(STORAGE_DIR / "datasets"):
        dataset = _read(path)
        if not dataset:
            summary["skipped_or_corrupted"] += 1
            continue
        metadata = dataset.get("metadata", {})
        if metadata and not DatasetRepository.exists(metadata["dataset_id"]):
            DatasetRepository.create(metadata, dataset.get("cases", []))
            summary["datasets_migrated"] += 1

    for path in _json_files(STORAGE_DIR / "evaluations"):
        evaluation = _read(path)
        if not evaluation:
            summary["skipped_or_corrupted"] += 1
            continue
        if not EvaluationRepository.exists(evaluation["evaluation_id"]):
            EvaluationRepository.create(evaluation)
            summary["evaluations_migrated"] += 1

    for path in _json_files(STORAGE_DIR / "feedback"):
        feedback = _read(path)
        if not feedback:
            summary["skipped_or_corrupted"] += 1
            continue
        if not FeedbackRepository.exists(feedback["feedback_id"]):
            FeedbackRepository.create(feedback)
            summary["feedback_migrated"] += 1

    for folder, repo, key, summary_key in [
        (STORAGE_DIR / "monitoring" / "rules", MonitoringRuleRepository, "rule_id", "monitoring_rules_migrated"),
        (STORAGE_DIR / "monitoring" / "runs", MonitoringRunRepository, "run_id", "monitoring_runs_migrated"),
        (STORAGE_DIR / "monitoring" / "alerts", AlertRepository, "alert_id", "alerts_migrated"),
        (STORAGE_DIR / "audit", AuditRepository, "audit_id", "audit_events_migrated"),
    ]:
        for path in _json_files(folder):
            payload = _read(path)
            if not payload:
                summary["skipped_or_corrupted"] += 1
                continue
            if not repo.exists(payload[key]):
                repo.create(payload)
                summary[summary_key] += 1

    return summary


if __name__ == "__main__":
    summary = migrate_json_to_database()
    for key, value in summary.items():
        print(f"{key}: {value}")
