from datetime import datetime, timezone

from .db import init_database
from .repositories import (
    AlertRepository,
    AuditRepository,
    DatasetRepository,
    EvaluationRepository,
    FeedbackRepository,
    MonitoringRuleRepository,
    MonitoringRunRepository,
    UserRepository,
    WorkspaceRepository,
)


BACKUP_KEYS = {
    "created_at",
    "version",
    "users",
    "workspaces",
    "workspace_members",
    "datasets",
    "evaluations",
    "feedback",
    "monitoring_rules",
    "monitoring_runs",
    "alerts",
    "audit_events",
}


def export_database_backup() -> dict:
    init_database()
    workspaces = WorkspaceRepository.list()
    datasets = [DatasetRepository.get_by_id(item["dataset_id"]) for item in DatasetRepository.list()]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "3.0",
        "users": UserRepository.list(include_private=True),
        "workspaces": [{key: value for key, value in workspace.items() if key != "members"} for workspace in workspaces],
        "workspace_members": [
            {"workspace_id": workspace["workspace_id"], **member}
            for workspace in workspaces
            for member in workspace.get("members", [])
        ],
        "datasets": datasets,
        "evaluations": [EvaluationRepository.get_by_id(item["evaluation_id"]) for item in EvaluationRepository.list()],
        "feedback": FeedbackRepository.list(),
        "monitoring_rules": MonitoringRuleRepository.list(),
        "monitoring_runs": MonitoringRunRepository.list(),
        "alerts": AlertRepository.list(),
        "audit_events": AuditRepository.list(),
    }


def validate_backup_file(payload: dict) -> bool:
    return isinstance(payload, dict) and BACKUP_KEYS.issubset(payload.keys()) and payload.get("version") == "3.0"


def import_database_backup(payload: dict) -> dict:
    if not validate_backup_file(payload):
        raise ValueError("Invalid backup file.")
    init_database()
    summary = {"restored": 0}
    for user in payload["users"]:
        if not UserRepository.exists(user["user_id"]):
            UserRepository.create(user)
            summary["restored"] += 1
    for workspace in payload["workspaces"]:
        if not WorkspaceRepository.exists(workspace["workspace_id"]):
            workspace["members"] = []
            WorkspaceRepository.create(workspace)
            summary["restored"] += 1
    from .repositories import WorkspaceMemberRepository

    for member in payload["workspace_members"]:
        WorkspaceMemberRepository.add(member["workspace_id"], member["user_id"], member["role"])
    for dataset in payload["datasets"]:
        metadata = dataset.get("metadata", {})
        if metadata and not DatasetRepository.exists(metadata["dataset_id"]):
            DatasetRepository.create(metadata, dataset.get("cases", []))
            summary["restored"] += 1
    for evaluation in payload["evaluations"]:
        if not EvaluationRepository.exists(evaluation["evaluation_id"]):
            EvaluationRepository.create(evaluation)
            summary["restored"] += 1
    for feedback in payload["feedback"]:
        if not FeedbackRepository.exists(feedback["feedback_id"]):
            FeedbackRepository.create(feedback)
            summary["restored"] += 1
    for item, repo, key in [
        ("monitoring_rules", MonitoringRuleRepository, "rule_id"),
        ("monitoring_runs", MonitoringRunRepository, "run_id"),
        ("alerts", AlertRepository, "alert_id"),
        ("audit_events", AuditRepository, "audit_id"),
    ]:
        for payload_item in payload[item]:
            if not repo.exists(payload_item[key]):
                repo.create(payload_item)
                summary["restored"] += 1
    return summary
