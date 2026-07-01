import json
from datetime import datetime, timezone

from sqlalchemy import func, or_
from security_utils import mask_secret

from .db import SessionLocal, init_database
from .models import AblationStudyResult, AgentRun, AgentStep, Alert, AuditEvent, BenchmarkDataset, BenchmarkExample, BenchmarkImportRun, Connector, ConnectorSyncRun, Dataset, DemoModeState, DeployedModel, EscalationRule, Evaluation, ExecutiveReport, ExternalIntegration, ExternalLinkedResource, ExternalSyncRecord, Feedback, GeneratedDatasetCase, HybridAnalysisResult, ImportedSource, Incident, IncidentComment, IncidentTimelineEvent, LLMSettings, MockExternalTicket, ModelArtifact, ModelExperiment, MonitoringRule, MonitoringRun, NotificationDeliveryLog, NotificationTemplate, PromptTemplate, ReasoningTrace, ResearchResult, SearchQuery, Session, SourceChunk, TrainingDatasetExport, User, ValidationRun, ValidationStepResult, WebhookEndpoint, Workspace, WorkspaceMember


def _dump(value) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _load(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_connector_config(config: dict) -> dict:
    masked = dict(config or {})
    for key, value in list(masked.items()):
        if any(term in key.lower() for term in ["token", "secret", "password", "api_key", "access_key"]):
            masked[key] = mask_secret(value)
    return masked


def _mask_secret_config(config: dict) -> dict:
    masked = dict(config or {})
    for key, value in list(masked.items()):
        if any(term in key.lower() for term in ["token", "secret", "password", "api_key", "access_key"]):
            masked[key] = mask_secret(str(value))
    return masked


class BaseRepository:
    model = None
    id_field = ""

    @classmethod
    def exists(cls, item_id: str) -> bool:
        with SessionLocal() as db:
            return db.query(cls.model).filter(getattr(cls.model, cls.id_field) == item_id).first() is not None

    @classmethod
    def delete(cls, item_id: str) -> bool:
        with SessionLocal() as db:
            row = db.query(cls.model).filter(getattr(cls.model, cls.id_field) == item_id).first()
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True


class UserRepository(BaseRepository):
    model = User
    id_field = "user_id"

    @staticmethod
    def to_dict(row: User, include_private: bool = True) -> dict:
        payload = {key: getattr(row, key, "") for key in ["user_id", "name", "email", "password_hash", "salt", "role", "created_at", "updated_at", "failed_login_attempts", "locked_until", "last_failed_login_at", "last_login_at"]}
        if not include_private:
            payload.pop("password_hash", None)
            payload.pop("salt", None)
        return payload

    @classmethod
    def create(cls, payload: dict) -> dict:
        with SessionLocal() as db:
            row = User(**payload)
            db.add(row)
            db.commit()
            return cls.to_dict(row)

    @classmethod
    def list(cls, include_private: bool = True) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(User).order_by(User.created_at.asc()).all()
            return [cls.to_dict(row, include_private) for row in rows]

    @classmethod
    def get_by_id(cls, user_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(User).filter(User.user_id == user_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def get_by_email(cls, email: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(User).filter(User.email == email.strip().lower()).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def update_role(cls, user_id: str, role: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(User).filter(User.user_id == user_id).first()
            if not row:
                return None
            row.role = role
            row.updated_at = _now()
            db.commit()
            return cls.to_dict(row)

    @classmethod
    def update_security_fields(cls, user_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(User).filter(User.user_id == user_id).first()
            if not row:
                return None
            for key in ["password_hash", "salt", "failed_login_attempts", "locked_until", "last_failed_login_at", "last_login_at", "updated_at"]:
                if key in payload:
                    setattr(row, key, payload[key])
            db.commit()
            return cls.to_dict(row)


class SessionRepository(BaseRepository):
    model = Session
    id_field = "token"

    @staticmethod
    def to_dict(row: Session) -> dict:
        return {key: getattr(row, key) for key in ["token", "user_id", "created_at", "expires_at"]}

    @classmethod
    def create(cls, payload: dict) -> dict:
        with SessionLocal() as db:
            row = Session(**payload)
            db.merge(row)
            db.commit()
            return cls.to_dict(row)

    @classmethod
    def get_by_token(cls, token: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Session).filter(Session.token == token).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_user(cls, user_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(Session).filter(Session.user_id == user_id).order_by(Session.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def delete(cls, token: str) -> bool:
        with SessionLocal() as db:
            row = db.query(Session).filter(Session.token == token).first()
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True

    @classmethod
    def delete_for_user(cls, user_id: str):
        with SessionLocal() as db:
            db.query(Session).filter(Session.user_id == user_id).delete()
            db.commit()


class WorkspaceRepository(BaseRepository):
    model = Workspace
    id_field = "workspace_id"

    @staticmethod
    def to_dict(row: Workspace, members: list[dict] | None = None) -> dict:
        return {
            "workspace_id": row.workspace_id,
            "name": row.name,
            "description": row.description or "",
            "created_by": row.created_by,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "members": members or [],
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        members = payload.pop("members", [])
        with SessionLocal() as db:
            row = Workspace(**payload)
            db.add(row)
            for member in members:
                db.add(WorkspaceMember(workspace_id=row.workspace_id, user_id=member["user_id"], role=member["role"], created_at=row.created_at))
            db.commit()
            return cls.get_by_id(row.workspace_id)

    @classmethod
    def get_by_id(cls, workspace_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
            if not row:
                return None
            members = [WorkspaceMemberRepository.to_dict(member) for member in db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()]
            return cls.to_dict(row, members)

    @classmethod
    def list(cls) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(Workspace).order_by(Workspace.created_at.asc()).all()
            return [cls.get_by_id(row.workspace_id) for row in rows]

    @classmethod
    def update(cls, workspace_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
            if not row:
                return None
            for key in ["name", "description", "updated_at"]:
                if key in payload:
                    setattr(row, key, payload[key])
            db.commit()
            return cls.get_by_id(workspace_id)


class WorkspaceMemberRepository:
    @staticmethod
    def to_dict(row: WorkspaceMember) -> dict:
        return {"user_id": row.user_id, "role": row.role}

    @classmethod
    def list(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def add(cls, workspace_id: str, user_id: str, role: str) -> None:
        with SessionLocal() as db:
            row = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id).first()
            if row:
                row.role = role
            else:
                db.add(WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role, created_at=_now()))
            db.commit()

    @classmethod
    def remove(cls, workspace_id: str, user_id: str) -> None:
        with SessionLocal() as db:
            db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id).delete()
            db.commit()


class DatasetRepository(BaseRepository):
    model = Dataset
    id_field = "dataset_id"

    @staticmethod
    def metadata(row: Dataset) -> dict:
        metadata = _load(row.metadata_json, {})
        metadata.update({"workspace_id": row.workspace_id})
        return metadata

    @staticmethod
    def to_dict(row: Dataset) -> dict:
        return {"metadata": DatasetRepository.metadata(row), "cases": _load(row.cases_json, [])}

    @classmethod
    def create(cls, metadata: dict, cases: list[dict]) -> dict:
        row = Dataset(
            dataset_id=metadata["dataset_id"],
            workspace_id=metadata.get("workspace_id", ""),
            name=metadata.get("name", ""),
            filename=metadata.get("filename", ""),
            description=metadata.get("description", ""),
            version=metadata.get("version", ""),
            total_cases=metadata.get("total_cases", 0),
            quality_score=metadata.get("quality_score", 0),
            metadata_json=_dump(metadata),
            cases_json=_dump(cases),
            created_at=metadata.get("created_at", _now()),
            updated_at=metadata.get("updated_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return metadata

    @classmethod
    def list(cls, workspace_id: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(Dataset)
            if workspace_id:
                query = query.filter(Dataset.workspace_id == workspace_id)
            rows = query.order_by(Dataset.created_at.desc()).all()
            return [cls.metadata(row) for row in rows]

    @classmethod
    def get_by_id(cls, dataset_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            return cls.to_dict(row) if row else None


class EvaluationRepository(BaseRepository):
    model = Evaluation
    id_field = "evaluation_id"

    @staticmethod
    def summary(row: Evaluation) -> dict:
        return {
            "evaluation_id": row.evaluation_id,
            "dataset_id": row.dataset_id,
            "dataset_name": row.dataset_name,
            "workspace_id": row.workspace_id,
            "created_at": row.created_at,
            "total_cases": row.total_cases,
            "accuracy": row.accuracy,
            "label_accuracy": row.label_accuracy,
            "drift_type_accuracy": row.drift_type_accuracy,
            "severity_accuracy": row.severity_accuracy,
            "quality_score": row.quality_score,
        }

    @staticmethod
    def to_dict(row: Evaluation) -> dict:
        payload = EvaluationRepository.summary(row)
        payload["result"] = _load(row.result_json, {})
        return payload

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = Evaluation(
            evaluation_id=payload["evaluation_id"],
            workspace_id=payload.get("workspace_id", ""),
            dataset_id=payload.get("dataset_id", ""),
            dataset_name=payload.get("dataset_name", ""),
            total_cases=payload.get("total_cases", 0),
            accuracy=payload.get("accuracy", 0),
            label_accuracy=payload.get("label_accuracy", 0),
            drift_type_accuracy=payload.get("drift_type_accuracy", 0),
            severity_accuracy=payload.get("severity_accuracy", 0),
            quality_score=payload.get("quality_score", 0),
            result_json=_dump(payload.get("result", {})),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return payload

    @classmethod
    def list(cls, workspace_id: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(Evaluation)
            if workspace_id:
                query = query.filter(Evaluation.workspace_id == workspace_id)
            return [cls.summary(row) for row in query.order_by(Evaluation.created_at.desc()).all()]

    @classmethod
    def get_by_id(cls, evaluation_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Evaluation).filter(Evaluation.evaluation_id == evaluation_id).first()
            return cls.to_dict(row) if row else None


class FeedbackRepository(BaseRepository):
    model = Feedback
    id_field = "feedback_id"

    @staticmethod
    def to_dict(row: Feedback) -> dict:
        return _load(row.feedback_json, {})

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = Feedback(
            feedback_id=payload["feedback_id"],
            workspace_id=payload.get("workspace_id", ""),
            evaluation_id=payload.get("evaluation_id", ""),
            dataset_id=payload.get("dataset_id", ""),
            case_id=payload.get("case_id", ""),
            corrected_label=payload.get("corrected_label", ""),
            corrected_drift_type=payload.get("corrected_drift_type", ""),
            corrected_severity=payload.get("corrected_severity", ""),
            review_status=payload.get("review_status", ""),
            reviewer_notes=payload.get("reviewer_notes", ""),
            correction_reason=payload.get("correction_reason", ""),
            feedback_json=_dump(payload),
            created_at=payload.get("created_at", _now()),
            updated_at=payload.get("updated_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return payload

    @classmethod
    def list(cls, workspace_id: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(Feedback)
            if workspace_id:
                query = query.filter(Feedback.workspace_id == workspace_id)
            return [cls.to_dict(row) for row in query.order_by(Feedback.updated_at.desc()).all()]


class JsonRepositoryMixin(BaseRepository):
    json_field = ""

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = cls.row_from_payload(payload)
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return payload

    @classmethod
    def get_by_id(cls, item_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(cls.model).filter(getattr(cls.model, cls.id_field) == item_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list(cls, workspace_id: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(cls.model)
            if workspace_id:
                query = query.filter(cls.model.workspace_id == workspace_id)
            rows = query.order_by(cls.model.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def to_dict(cls, row):
        return _load(getattr(row, cls.json_field), {})


class MonitoringRuleRepository(JsonRepositoryMixin):
    model = MonitoringRule
    id_field = "rule_id"
    json_field = "rule_json"

    @staticmethod
    def row_from_payload(payload: dict) -> MonitoringRule:
        return MonitoringRule(
            rule_id=payload["rule_id"],
            workspace_id=payload.get("workspace_id", ""),
            dataset_id=payload.get("dataset_id", ""),
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            enabled=payload.get("enabled", True),
            thresholds_json=_dump(payload.get("thresholds", {})),
            alert_settings_json=_dump(payload.get("alert_settings", {})),
            rule_json=_dump(payload),
            created_at=payload.get("created_at", _now()),
            updated_at=payload.get("updated_at", _now()),
        )


class MonitoringRunRepository(JsonRepositoryMixin):
    model = MonitoringRun
    id_field = "run_id"
    json_field = "run_json"

    @staticmethod
    def row_from_payload(payload: dict) -> MonitoringRun:
        return MonitoringRun(
            run_id=payload["run_id"],
            workspace_id=payload.get("workspace_id", ""),
            rule_id=payload.get("rule_id", ""),
            dataset_id=payload.get("dataset_id", ""),
            dataset_name=payload.get("dataset_name", ""),
            status=payload.get("status", ""),
            evaluation_id=payload.get("evaluation_id", ""),
            accuracy=payload.get("accuracy", 0),
            critical_cases=payload.get("critical_cases", 0),
            high_cases=payload.get("high_cases", 0),
            average_priority_score=payload.get("average_priority_score", 0),
            alerts_created=payload.get("alerts_created", 0),
            summary=payload.get("summary", ""),
            run_json=_dump(payload),
            created_at=payload.get("created_at", _now()),
        )


class AlertRepository(JsonRepositoryMixin):
    model = Alert
    id_field = "alert_id"
    json_field = "alert_json"

    @staticmethod
    def row_from_payload(payload: dict) -> Alert:
        return Alert(
            alert_id=payload["alert_id"],
            workspace_id=payload.get("workspace_id", ""),
            rule_id=payload.get("rule_id", ""),
            run_id=payload.get("run_id", ""),
            dataset_id=payload.get("dataset_id", ""),
            dataset_name=payload.get("dataset_name", ""),
            status=payload.get("status", ""),
            alert_type=payload.get("alert_type", ""),
            severity=payload.get("severity", ""),
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            metric_name=payload.get("metric_name", ""),
            actual_value=payload.get("actual_value", 0),
            threshold_value=payload.get("threshold_value", 0),
            recommended_action=payload.get("recommended_action", ""),
            related_evaluation_id=payload.get("related_evaluation_id", ""),
            related_cases_json=_dump(payload.get("related_cases", [])),
            alert_json=_dump(payload),
            created_at=payload.get("created_at", _now()),
        )


class ConnectorRepository(BaseRepository):
    model = Connector
    id_field = "connector_id"

    @staticmethod
    def to_dict(row: Connector, mask_config: bool = True) -> dict:
        config = _load(row.config_json, {})
        return {
            "connector_id": row.connector_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "connector_type": row.connector_type or "",
            "status": row.status or "active",
            "config": _mask_connector_config(config) if mask_config else config,
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
            "last_sync_at": row.last_sync_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = Connector(
            connector_id=payload["connector_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            connector_type=payload.get("connector_type", ""),
            status=payload.get("status", "active"),
            config_json=_dump(payload.get("config", {})),
            created_by=payload.get("created_by", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
            last_sync_at=payload.get("last_sync_at", ""),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["connector_id"]) or payload

    @classmethod
    def get_by_id(cls, connector_id: str, mask_config: bool = True) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Connector).filter(Connector.connector_id == connector_id).first()
            return cls.to_dict(row, mask_config) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str, mask_config: bool = True) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(Connector).filter(Connector.workspace_id == workspace_id).order_by(Connector.created_at.desc()).all()
            return [cls.to_dict(row, mask_config) for row in rows]

    @classmethod
    def update(cls, connector_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Connector).filter(Connector.connector_id == connector_id).first()
            if not row:
                return None
            for key in ["name", "connector_type", "status", "last_sync_at"]:
                if key in payload:
                    setattr(row, key, payload[key])
            if "config" in payload:
                row.config_json = _dump(payload["config"])
            row.updated_at = payload.get("updated_at", _now())
            db.commit()
        return cls.get_by_id(connector_id)

    @classmethod
    def search(cls, workspace_id: str, text: str = "", connector_type: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(Connector).filter(Connector.workspace_id == workspace_id)
            if connector_type:
                query = query.filter(Connector.connector_type == connector_type)
            if text:
                query = query.filter(func.lower(Connector.name).contains(text.lower()))
            return [cls.to_dict(row) for row in query.order_by(Connector.created_at.desc()).all()]


class ImportedSourceRepository(BaseRepository):
    model = ImportedSource
    id_field = "source_id"

    @staticmethod
    def to_dict(row: ImportedSource, include_content: bool = True) -> dict:
        payload = {
            "source_id": row.source_id,
            "workspace_id": row.workspace_id or "",
            "connector_id": row.connector_id or "",
            "source_type": row.source_type or "unknown",
            "source_name": row.source_name or "",
            "source_path": row.source_path or "",
            "source_url": row.source_url or "",
            "content_hash": row.content_hash or "",
            "metadata": _load(row.metadata_json, {}),
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }
        content = row.content_text or ""
        payload["content_text"] = content if include_content else ""
        payload["content_preview"] = content[:400]
        return payload

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = ImportedSource(
            source_id=payload["source_id"],
            workspace_id=payload.get("workspace_id", ""),
            connector_id=payload.get("connector_id", ""),
            source_type=payload.get("source_type", "unknown"),
            source_name=payload.get("source_name", ""),
            source_path=payload.get("source_path", ""),
            source_url=payload.get("source_url", ""),
            content_text=payload.get("content_text", ""),
            content_hash=payload.get("content_hash", ""),
            metadata_json=_dump(payload.get("metadata", {})),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["source_id"]) or payload

    @classmethod
    def get_by_id(cls, source_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ImportedSource).filter(ImportedSource.source_id == source_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str, connector_id: str = "", source_type: str = "", search: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(ImportedSource).filter(ImportedSource.workspace_id == workspace_id)
            if connector_id:
                query = query.filter(ImportedSource.connector_id == connector_id)
            if source_type:
                query = query.filter(ImportedSource.source_type == source_type)
            if search:
                lowered = search.lower()
                query = query.filter(or_(
                    func.lower(ImportedSource.source_name).contains(lowered),
                    func.lower(ImportedSource.source_path).contains(lowered),
                    func.lower(ImportedSource.content_text).contains(lowered),
                ))
            rows = query.order_by(ImportedSource.created_at.desc()).all()
            return [cls.to_dict(row, include_content=False) for row in rows]

    @classmethod
    def list_by_connector(cls, connector_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ImportedSource).filter(ImportedSource.connector_id == connector_id).order_by(ImportedSource.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def update(cls, source_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ImportedSource).filter(ImportedSource.source_id == source_id).first()
            if not row:
                return None
            for key in ["source_type", "source_name", "source_path", "source_url", "content_text", "content_hash"]:
                if key in payload:
                    setattr(row, key, payload[key])
            if "metadata" in payload:
                row.metadata_json = _dump(payload["metadata"])
            row.updated_at = payload.get("updated_at", _now())
            db.commit()
        return cls.get_by_id(source_id)

    @classmethod
    def search(cls, workspace_id: str, text: str) -> list[dict]:
        return cls.list_by_workspace(workspace_id, search=text)


class ConnectorSyncRepository(BaseRepository):
    model = ConnectorSyncRun
    id_field = "sync_id"

    @staticmethod
    def to_dict(row: ConnectorSyncRun) -> dict:
        return {
            "sync_id": row.sync_id,
            "workspace_id": row.workspace_id or "",
            "connector_id": row.connector_id or "",
            "connector_type": row.connector_type or "",
            "status": row.status or "",
            "started_at": row.started_at or "",
            "completed_at": row.completed_at or "",
            "files_imported": row.files_imported or 0,
            "files_skipped": row.files_skipped or 0,
            "errors": _load(row.errors_json, []),
            "summary": row.summary or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        return cls.save_sync_run(payload)

    @classmethod
    def save_sync_run(cls, payload: dict) -> dict:
        row = ConnectorSyncRun(
            sync_id=payload["sync_id"],
            workspace_id=payload.get("workspace_id", ""),
            connector_id=payload.get("connector_id", ""),
            connector_type=payload.get("connector_type", ""),
            status=payload.get("status", "completed"),
            started_at=payload.get("started_at", _now()),
            completed_at=payload.get("completed_at", ""),
            files_imported=payload.get("files_imported", 0),
            files_skipped=payload.get("files_skipped", 0),
            errors_json=_dump(payload.get("errors", [])),
            summary=payload.get("summary", ""),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["sync_id"]) or payload

    @classmethod
    def get_by_id(cls, sync_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ConnectorSyncRun).filter(ConnectorSyncRun.sync_id == sync_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_sync_runs(cls, connector_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ConnectorSyncRun).filter(ConnectorSyncRun.connector_id == connector_id).order_by(ConnectorSyncRun.started_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ConnectorSyncRun).filter(ConnectorSyncRun.workspace_id == workspace_id).order_by(ConnectorSyncRun.started_at.desc()).all()
            return [cls.to_dict(row) for row in rows]


class GeneratedDatasetCaseRepository(BaseRepository):
    model = GeneratedDatasetCase
    id_field = "generated_case_id"

    @staticmethod
    def to_dict(row: GeneratedDatasetCase) -> dict:
        return {
            "generated_case_id": row.generated_case_id,
            "workspace_id": row.workspace_id or "",
            "source_ids": _load(row.source_ids_json, []),
            "case": _load(row.case_json, {}),
            "created_at": row.created_at or "",
            "created_by": row.created_by or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = GeneratedDatasetCase(
            generated_case_id=payload["generated_case_id"],
            workspace_id=payload.get("workspace_id", ""),
            source_ids_json=_dump(payload.get("source_ids", [])),
            case_json=_dump(payload.get("case", {})),
            created_at=payload.get("created_at", _now()),
            created_by=payload.get("created_by", ""),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return payload

    @classmethod
    def get_by_id(cls, generated_case_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(GeneratedDatasetCase).filter(GeneratedDatasetCase.generated_case_id == generated_case_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(GeneratedDatasetCase).filter(GeneratedDatasetCase.workspace_id == workspace_id).order_by(GeneratedDatasetCase.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def update(cls, generated_case_id: str, payload: dict) -> dict | None:
        existing = cls.get_by_id(generated_case_id)
        if not existing:
            return None
        updated = {**existing, **payload, "generated_case_id": generated_case_id}
        cls.create(updated)
        return cls.get_by_id(generated_case_id)

    @classmethod
    def search(cls, workspace_id: str, text: str = "") -> list[dict]:
        rows = cls.list_by_workspace(workspace_id)
        if not text:
            return rows
        lowered = text.lower()
        return [row for row in rows if lowered in json.dumps(row.get("case", {})).lower()]


class BenchmarkDatasetRepository(BaseRepository):
    model = BenchmarkDataset
    id_field = "benchmark_id"

    @staticmethod
    def to_dict(row: BenchmarkDataset) -> dict:
        return {key: getattr(row, key) or "" for key in [
            "benchmark_id",
            "workspace_id",
            "name",
            "dataset_type",
            "description",
            "source_name",
            "source_url",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]} | {
            "total_examples": row.total_examples or 0,
            "imported_examples": row.imported_examples or 0,
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = BenchmarkDataset(
            benchmark_id=payload["benchmark_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            dataset_type=payload.get("dataset_type", ""),
            description=payload.get("description", ""),
            source_name=payload.get("source_name", ""),
            source_url=payload.get("source_url", ""),
            status=payload.get("status", "uploaded"),
            total_examples=payload.get("total_examples", 0),
            imported_examples=payload.get("imported_examples", 0),
            created_by=payload.get("created_by", ""),
            created_at=payload.get("created_at", _now()),
            updated_at=payload.get("updated_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["benchmark_id"]) or payload

    @classmethod
    def list(cls, workspace_id: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(BenchmarkDataset)
            if workspace_id:
                query = query.filter(BenchmarkDataset.workspace_id == workspace_id)
            rows = query.order_by(BenchmarkDataset.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def get_by_id(cls, benchmark_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(BenchmarkDataset).filter(BenchmarkDataset.benchmark_id == benchmark_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def delete(cls, benchmark_id: str) -> bool:
        with SessionLocal() as db:
            row = db.query(BenchmarkDataset).filter(BenchmarkDataset.benchmark_id == benchmark_id).first()
            if not row:
                return False
            db.query(BenchmarkExample).filter(BenchmarkExample.benchmark_id == benchmark_id).delete()
            db.query(BenchmarkImportRun).filter(BenchmarkImportRun.benchmark_id == benchmark_id).delete()
            db.delete(row)
            db.commit()
            return True


class BenchmarkImportRunRepository(BaseRepository):
    model = BenchmarkImportRun
    id_field = "import_id"

    @staticmethod
    def to_dict(row: BenchmarkImportRun) -> dict:
        return {
            "import_id": row.import_id,
            "workspace_id": row.workspace_id or "",
            "benchmark_id": row.benchmark_id or "",
            "dataset_type": row.dataset_type or "",
            "status": row.status or "",
            "started_at": row.started_at or "",
            "completed_at": row.completed_at or "",
            "examples_processed": row.examples_processed or 0,
            "examples_imported": row.examples_imported or 0,
            "examples_skipped": row.examples_skipped or 0,
            "errors": _load(row.errors_json, []),
            "summary": row.summary or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = BenchmarkImportRun(
            import_id=payload["import_id"],
            workspace_id=payload.get("workspace_id", ""),
            benchmark_id=payload.get("benchmark_id", ""),
            dataset_type=payload.get("dataset_type", ""),
            status=payload.get("status", "importing"),
            started_at=payload.get("started_at", _now()),
            completed_at=payload.get("completed_at", ""),
            examples_processed=payload.get("examples_processed", 0),
            examples_imported=payload.get("examples_imported", 0),
            examples_skipped=payload.get("examples_skipped", 0),
            errors_json=_dump(payload.get("errors", [])),
            summary=payload.get("summary", ""),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["import_id"]) or payload

    @classmethod
    def get_by_id(cls, import_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(BenchmarkImportRun).filter(BenchmarkImportRun.import_id == import_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_benchmark(cls, benchmark_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(BenchmarkImportRun).filter(BenchmarkImportRun.benchmark_id == benchmark_id).order_by(BenchmarkImportRun.started_at.desc()).all()
            return [cls.to_dict(row) for row in rows]


class BenchmarkExampleRepository(BaseRepository):
    model = BenchmarkExample
    id_field = "example_id"

    @staticmethod
    def to_dict(row: BenchmarkExample) -> dict:
        return {
            "example_id": row.example_id,
            "workspace_id": row.workspace_id or "",
            "benchmark_id": row.benchmark_id or "",
            "dataset_type": row.dataset_type or "",
            "original_id": row.original_id or "",
            "input": _load(row.input_json, {}),
            "target": _load(row.target_json, {}),
            "driftguard_case": _load(row.driftguard_case_json, {}),
            "split": row.split or "unsplit",
            "quality_score": row.quality_score or 0,
            "metadata": _load(row.metadata_json, {}),
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = BenchmarkExample(
            example_id=payload["example_id"],
            workspace_id=payload.get("workspace_id", ""),
            benchmark_id=payload.get("benchmark_id", ""),
            dataset_type=payload.get("dataset_type", ""),
            original_id=payload.get("original_id", ""),
            input_json=_dump(payload.get("input", {})),
            target_json=_dump(payload.get("target", {})),
            driftguard_case_json=_dump(payload.get("driftguard_case", {})),
            split=payload.get("split", "unsplit"),
            quality_score=payload.get("quality_score", 0),
            metadata_json=_dump(payload.get("metadata", {})),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return payload

    @classmethod
    def bulk_create(cls, examples: list[dict]) -> list[dict]:
        for example in examples:
            cls.create(example)
        return examples

    @classmethod
    def list(cls, benchmark_id: str = "", workspace_id: str = "", split: str = "", label: str = "", limit: int = 100, offset: int = 0) -> list[dict]:
        with SessionLocal() as db:
            query = db.query(BenchmarkExample)
            if benchmark_id:
                query = query.filter(BenchmarkExample.benchmark_id == benchmark_id)
            if workspace_id:
                query = query.filter(BenchmarkExample.workspace_id == workspace_id)
            if split:
                query = query.filter(BenchmarkExample.split == split)
            rows = query.order_by(BenchmarkExample.created_at.desc()).offset(max(0, offset)).limit(max(1, min(limit, 1000))).all()
            items = [cls.to_dict(row) for row in rows]
            if label:
                items = [item for item in items if item.get("target", {}).get("label") == label]
            return items

    @classmethod
    def get_by_id(cls, example_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(BenchmarkExample).filter(BenchmarkExample.example_id == example_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def update_split(cls, example_id: str, split: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(BenchmarkExample).filter(BenchmarkExample.example_id == example_id).first()
            if not row:
                return None
            row.split = split
            db.commit()
            return cls.to_dict(row)


class TrainingDatasetExportRepository(BaseRepository):
    model = TrainingDatasetExport
    id_field = "export_id"

    @staticmethod
    def to_dict(row: TrainingDatasetExport) -> dict:
        return {
            "export_id": row.export_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "description": row.description or "",
            "format": row.format or "jsonl",
            "total_examples": row.total_examples or 0,
            "train_count": row.train_count or 0,
            "validation_count": row.validation_count or 0,
            "test_count": row.test_count or 0,
            "included_dataset_types": _load(row.included_dataset_types_json, []),
            "export_path": row.export_path or "",
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = TrainingDatasetExport(
            export_id=payload["export_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            format=payload.get("format", "jsonl"),
            total_examples=payload.get("total_examples", 0),
            train_count=payload.get("train_count", 0),
            validation_count=payload.get("validation_count", 0),
            test_count=payload.get("test_count", 0),
            included_dataset_types_json=_dump(payload.get("included_dataset_types", [])),
            export_path=payload.get("export_path", ""),
            created_by=payload.get("created_by", ""),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["export_id"]) or payload

    @classmethod
    def list(cls, workspace_id: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(TrainingDatasetExport)
            if workspace_id:
                query = query.filter(TrainingDatasetExport.workspace_id == workspace_id)
            rows = query.order_by(TrainingDatasetExport.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def get_by_id(cls, export_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(TrainingDatasetExport).filter(TrainingDatasetExport.export_id == export_id).first()
            return cls.to_dict(row) if row else None


class ModelExperimentRepository(BaseRepository):
    model = ModelExperiment
    id_field = "experiment_id"

    @staticmethod
    def to_dict(row: ModelExperiment) -> dict:
        return {
            "experiment_id": row.experiment_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "task_type": row.task_type or "",
            "model_type": row.model_type or "",
            "dataset_source": row.dataset_source or "",
            "training_export_id": row.training_export_id or "",
            "benchmark_ids": _load(row.benchmark_ids_json, []),
            "status": row.status or "queued",
            "total_examples": row.total_examples or 0,
            "train_count": row.train_count or 0,
            "validation_count": row.validation_count or 0,
            "test_count": row.test_count or 0,
            "accuracy": row.accuracy or 0,
            "precision_macro": row.precision_macro or 0,
            "recall_macro": row.recall_macro or 0,
            "f1_macro": row.f1_macro or 0,
            "confusion_matrix": _load(row.confusion_matrix_json, {}),
            "label_distribution": _load(row.label_distribution_json, {}),
            "metrics": _load(row.metrics_json, {}),
            "training_log": _load(row.training_log_json, []),
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
            "completed_at": row.completed_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = ModelExperiment(
            experiment_id=payload["experiment_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            task_type=payload.get("task_type", ""),
            model_type=payload.get("model_type", ""),
            dataset_source=payload.get("dataset_source", ""),
            training_export_id=payload.get("training_export_id", ""),
            benchmark_ids_json=_dump(payload.get("benchmark_ids", [])),
            status=payload.get("status", "queued"),
            total_examples=payload.get("total_examples", 0),
            train_count=payload.get("train_count", 0),
            validation_count=payload.get("validation_count", 0),
            test_count=payload.get("test_count", 0),
            accuracy=payload.get("accuracy", 0),
            precision_macro=payload.get("precision_macro", 0),
            recall_macro=payload.get("recall_macro", 0),
            f1_macro=payload.get("f1_macro", 0),
            confusion_matrix_json=_dump(payload.get("confusion_matrix", {})),
            label_distribution_json=_dump(payload.get("label_distribution", {})),
            metrics_json=_dump(payload.get("metrics", {})),
            training_log_json=_dump(payload.get("training_log", [])),
            created_by=payload.get("created_by", ""),
            created_at=payload.get("created_at", _now()),
            completed_at=payload.get("completed_at", ""),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["experiment_id"]) or payload

    @classmethod
    def get_by_id(cls, experiment_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ModelExperiment).filter(ModelExperiment.experiment_id == experiment_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        with SessionLocal() as db:
            query = db.query(ModelExperiment).filter(ModelExperiment.workspace_id == workspace_id)
            for key in ["task_type", "model_type", "status"]:
                if filters.get(key):
                    query = query.filter(getattr(ModelExperiment, key) == filters[key])
            rows = query.order_by(ModelExperiment.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def leaderboard(cls, workspace_id: str, task_type: str = "") -> list[dict]:
        rows = [item for item in cls.list_by_workspace(workspace_id, {"task_type": task_type}) if item.get("status") == "completed"]
        return sorted(rows, key=lambda item: (item.get("f1_macro", 0), item.get("accuracy", 0)), reverse=True)

    @classmethod
    def update_status(cls, experiment_id: str, status: str, training_log: list | None = None, completed_at: str = "") -> dict | None:
        with SessionLocal() as db:
            row = db.query(ModelExperiment).filter(ModelExperiment.experiment_id == experiment_id).first()
            if not row:
                return None
            row.status = status
            if training_log is not None:
                row.training_log_json = _dump(training_log)
            if completed_at:
                row.completed_at = completed_at
            db.commit()
            return cls.to_dict(row)

    @classmethod
    def update_metrics(cls, experiment_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ModelExperiment).filter(ModelExperiment.experiment_id == experiment_id).first()
            if not row:
                return None
            for key in ["total_examples", "train_count", "validation_count", "test_count", "accuracy", "precision_macro", "recall_macro", "f1_macro", "completed_at"]:
                if key in payload:
                    setattr(row, key, payload[key])
            row.confusion_matrix_json = _dump(payload.get("confusion_matrix", {}))
            row.label_distribution_json = _dump(payload.get("label_distribution", {}))
            row.metrics_json = _dump(payload.get("metrics", {}))
            row.training_log_json = _dump(payload.get("training_log", []))
            db.commit()
            return cls.to_dict(row)


class ModelArtifactRepository(BaseRepository):
    model = ModelArtifact
    id_field = "artifact_id"

    @staticmethod
    def to_dict(row: ModelArtifact) -> dict:
        return {
            "artifact_id": row.artifact_id,
            "workspace_id": row.workspace_id or "",
            "experiment_id": row.experiment_id or "",
            "model_path": row.model_path or "",
            "vectorizer_path": row.vectorizer_path or "",
            "metadata_path": row.metadata_path or "",
            "model_type": row.model_type or "",
            "task_type": row.task_type or "",
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = ModelArtifact(
            artifact_id=payload["artifact_id"],
            workspace_id=payload.get("workspace_id", ""),
            experiment_id=payload.get("experiment_id", ""),
            model_path=payload.get("model_path", ""),
            vectorizer_path=payload.get("vectorizer_path", ""),
            metadata_path=payload.get("metadata_path", ""),
            model_type=payload.get("model_type", ""),
            task_type=payload.get("task_type", ""),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["artifact_id"]) or payload

    @classmethod
    def get_by_id(cls, artifact_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ModelArtifact).filter(ModelArtifact.artifact_id == artifact_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def get_by_experiment(cls, experiment_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ModelArtifact).filter(ModelArtifact.experiment_id == experiment_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ModelArtifact).filter(ModelArtifact.workspace_id == workspace_id).order_by(ModelArtifact.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]


class DeployedModelRepository(BaseRepository):
    model = DeployedModel
    id_field = "deployed_model_id"

    @staticmethod
    def to_dict(row: DeployedModel) -> dict:
        return {
            "deployed_model_id": row.deployed_model_id,
            "workspace_id": row.workspace_id or "",
            "task_type": row.task_type or "",
            "experiment_id": row.experiment_id or "",
            "artifact_id": row.artifact_id or "",
            "model_type": row.model_type or "",
            "status": row.status or "inactive",
            "deployed_by": row.deployed_by or "",
            "deployed_at": row.deployed_at or "",
        }

    @classmethod
    def deploy_model(cls, payload: dict) -> dict:
        with SessionLocal() as db:
            db.query(DeployedModel).filter(
                DeployedModel.workspace_id == payload.get("workspace_id", ""),
                DeployedModel.task_type == payload.get("task_type", ""),
                DeployedModel.status == "active",
            ).update({"status": "inactive"})
            row = DeployedModel(
                deployed_model_id=payload["deployed_model_id"],
                workspace_id=payload.get("workspace_id", ""),
                task_type=payload.get("task_type", ""),
                experiment_id=payload.get("experiment_id", ""),
                artifact_id=payload.get("artifact_id", ""),
                model_type=payload.get("model_type", ""),
                status="active",
                deployed_by=payload.get("deployed_by", ""),
                deployed_at=payload.get("deployed_at", _now()),
            )
            db.add(row)
            db.commit()
            return cls.to_dict(row)

    @classmethod
    def get_active_model_for_task(cls, workspace_id: str, task_type: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(DeployedModel).filter(
                DeployedModel.workspace_id == workspace_id,
                DeployedModel.task_type == task_type,
                DeployedModel.status == "active",
            ).order_by(DeployedModel.deployed_at.desc()).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(DeployedModel).filter(DeployedModel.workspace_id == workspace_id).order_by(DeployedModel.deployed_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def rollback_model(cls, workspace_id: str, task_type: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(DeployedModel).filter(
                DeployedModel.workspace_id == workspace_id,
                DeployedModel.task_type == task_type,
                DeployedModel.status == "active",
            ).first()
            if not row:
                return None
            row.status = "rolled_back"
            db.commit()
            return cls.to_dict(row)


class IncidentRepository(BaseRepository):
    model = Incident
    id_field = "incident_id"

    @staticmethod
    def to_dict(row: Incident) -> dict:
        return {
            "incident_id": row.incident_id,
            "workspace_id": row.workspace_id or "",
            "title": row.title or "",
            "description": row.description or "",
            "severity": row.severity or "Medium",
            "status": row.status or "open",
            "source_type": row.source_type or "manual",
            "source_id": row.source_id or "",
            "related_alert_id": row.related_alert_id or "",
            "related_evaluation_id": row.related_evaluation_id or "",
            "related_model_experiment_id": row.related_model_experiment_id or "",
            "related_active_learning_item_id": row.related_active_learning_item_id or "",
            "assigned_to": row.assigned_to or "",
            "created_by": row.created_by or "",
            "sla_due_at": row.sla_due_at or "",
            "resolved_at": row.resolved_at or "",
            "closed_at": row.closed_at or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
            "metadata": _load(row.metadata_json, {}),
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = Incident(
            incident_id=payload["incident_id"],
            workspace_id=payload.get("workspace_id", ""),
            title=payload.get("title", ""),
            description=payload.get("description", ""),
            severity=payload.get("severity", "Medium"),
            status=payload.get("status", "open"),
            source_type=payload.get("source_type", "manual"),
            source_id=payload.get("source_id", ""),
            related_alert_id=payload.get("related_alert_id", ""),
            related_evaluation_id=payload.get("related_evaluation_id", ""),
            related_model_experiment_id=payload.get("related_model_experiment_id", ""),
            related_active_learning_item_id=payload.get("related_active_learning_item_id", ""),
            assigned_to=payload.get("assigned_to", ""),
            created_by=payload.get("created_by", ""),
            sla_due_at=payload.get("sla_due_at", ""),
            resolved_at=payload.get("resolved_at", ""),
            closed_at=payload.get("closed_at", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
            metadata_json=_dump(payload.get("metadata", {})),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["incident_id"]) or payload

    @classmethod
    def get_by_id(cls, incident_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Incident).filter(Incident.incident_id == incident_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str, filters: dict | None = None) -> list[dict]:
        filters = {key: value for key, value in (filters or {}).items() if value}
        with SessionLocal() as db:
            query = db.query(Incident).filter(Incident.workspace_id == workspace_id)
            for key in ["status", "severity", "source_type", "assigned_to"]:
                if filters.get(key):
                    query = query.filter(getattr(Incident, key) == filters[key])
            return [cls.to_dict(row) for row in query.order_by(Incident.updated_at.desc()).all()]

    @classmethod
    def update(cls, incident_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(Incident).filter(Incident.incident_id == incident_id).first()
            if not row:
                return None
            for key in [
                "title",
                "description",
                "severity",
                "status",
                "source_type",
                "source_id",
                "related_alert_id",
                "related_evaluation_id",
                "related_model_experiment_id",
                "related_active_learning_item_id",
                "assigned_to",
                "sla_due_at",
                "resolved_at",
                "closed_at",
            ]:
                if key in payload:
                    setattr(row, key, payload[key])
            if "metadata" in payload:
                row.metadata_json = _dump(payload["metadata"])
            row.updated_at = payload.get("updated_at", _now())
            db.commit()
        return cls.get_by_id(incident_id)

    @classmethod
    def summary(cls, workspace_id: str) -> dict:
        incidents = cls.list_by_workspace(workspace_id)
        by_status: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for incident in incidents:
            by_status[incident["status"]] = by_status.get(incident["status"], 0) + 1
            by_severity[incident["severity"]] = by_severity.get(incident["severity"], 0) + 1
        open_statuses = {"open", "triaged", "in_progress", "escalated"}
        return {
            "total": len(incidents),
            "open": sum(1 for incident in incidents if incident["status"] in open_statuses),
            "resolved": sum(1 for incident in incidents if incident["status"] == "resolved"),
            "closed": sum(1 for incident in incidents if incident["status"] == "closed"),
            "by_status": by_status,
            "by_severity": by_severity,
        }


class IncidentCommentRepository(BaseRepository):
    model = IncidentComment
    id_field = "comment_id"

    @staticmethod
    def to_dict(row: IncidentComment) -> dict:
        return {
            "comment_id": row.comment_id,
            "incident_id": row.incident_id or "",
            "workspace_id": row.workspace_id or "",
            "user_id": row.user_id or "",
            "comment_text": row.comment_text or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = IncidentComment(
            comment_id=payload["comment_id"],
            incident_id=payload.get("incident_id", ""),
            workspace_id=payload.get("workspace_id", ""),
            user_id=payload.get("user_id", ""),
            comment_text=payload.get("comment_text", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)

    @classmethod
    def list_by_incident(cls, incident_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(IncidentComment).filter(IncidentComment.incident_id == incident_id).order_by(IncidentComment.created_at.asc()).all()
            return [cls.to_dict(row) for row in rows]


class IncidentTimelineRepository(BaseRepository):
    model = IncidentTimelineEvent
    id_field = "timeline_event_id"

    @staticmethod
    def to_dict(row: IncidentTimelineEvent) -> dict:
        return {
            "timeline_event_id": row.timeline_event_id,
            "incident_id": row.incident_id or "",
            "workspace_id": row.workspace_id or "",
            "event_type": row.event_type or "",
            "actor_user_id": row.actor_user_id or "",
            "message": row.message or "",
            "metadata": _load(row.metadata_json, {}),
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = IncidentTimelineEvent(
            timeline_event_id=payload["timeline_event_id"],
            incident_id=payload.get("incident_id", ""),
            workspace_id=payload.get("workspace_id", ""),
            event_type=payload.get("event_type", ""),
            actor_user_id=payload.get("actor_user_id", ""),
            message=payload.get("message", ""),
            metadata_json=_dump(payload.get("metadata", {})),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)

    @classmethod
    def list_by_incident(cls, incident_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(IncidentTimelineEvent).filter(IncidentTimelineEvent.incident_id == incident_id).order_by(IncidentTimelineEvent.created_at.asc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def has_escalation_event(cls, incident_id: str, rule_id: str) -> bool:
        with SessionLocal() as db:
            rows = db.query(IncidentTimelineEvent).filter(
                IncidentTimelineEvent.incident_id == incident_id,
                IncidentTimelineEvent.event_type == "incident_escalated",
            ).all()
            return any(_load(row.metadata_json, {}).get("rule_id") == rule_id for row in rows)


class WebhookRepository(BaseRepository):
    model = WebhookEndpoint
    id_field = "webhook_id"

    @staticmethod
    def to_dict(row: WebhookEndpoint) -> dict:
        return {
            "webhook_id": row.webhook_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "url": row.url or "",
            "event_types": _load(row.event_types_json, []),
            "enabled": bool(row.enabled),
            "secret_masked": row.secret_masked or "",
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = WebhookEndpoint(
            webhook_id=payload["webhook_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            url=payload.get("url", ""),
            event_types_json=_dump(payload.get("event_types", [])),
            enabled=payload.get("enabled", True),
            secret_masked=payload.get("secret_masked", ""),
            created_by=payload.get("created_by", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["webhook_id"]) or payload

    @classmethod
    def get_by_id(cls, webhook_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(WebhookEndpoint).filter(WebhookEndpoint.webhook_id == webhook_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str, enabled_only: bool = False) -> list[dict]:
        with SessionLocal() as db:
            query = db.query(WebhookEndpoint).filter(WebhookEndpoint.workspace_id == workspace_id)
            if enabled_only:
                query = query.filter(WebhookEndpoint.enabled == True)  # noqa: E712
            rows = query.order_by(WebhookEndpoint.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def update(cls, webhook_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(WebhookEndpoint).filter(WebhookEndpoint.webhook_id == webhook_id).first()
            if not row:
                return None
            for key in ["name", "url", "enabled", "secret_masked"]:
                if key in payload:
                    setattr(row, key, payload[key])
            if "event_types" in payload:
                row.event_types_json = _dump(payload["event_types"])
            row.updated_at = payload.get("updated_at", _now())
            db.commit()
        return cls.get_by_id(webhook_id)


class NotificationTemplateRepository(BaseRepository):
    model = NotificationTemplate
    id_field = "template_id"

    @staticmethod
    def to_dict(row: NotificationTemplate) -> dict:
        return {
            "template_id": row.template_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "event_type": row.event_type or "",
            "subject_template": row.subject_template or "",
            "body_template": row.body_template or "",
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = NotificationTemplate(
            template_id=payload["template_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            event_type=payload.get("event_type", ""),
            subject_template=payload.get("subject_template", ""),
            body_template=payload.get("body_template", ""),
            created_by=payload.get("created_by", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)


class NotificationDeliveryRepository(BaseRepository):
    model = NotificationDeliveryLog
    id_field = "delivery_id"

    @staticmethod
    def to_dict(row: NotificationDeliveryLog) -> dict:
        return {
            "delivery_id": row.delivery_id,
            "workspace_id": row.workspace_id or "",
            "webhook_id": row.webhook_id or "",
            "incident_id": row.incident_id or "",
            "event_type": row.event_type or "",
            "status": row.status or "",
            "request_payload": _load(row.request_payload_json, {}),
            "response_status_code": row.response_status_code or 0,
            "response_text": row.response_text or "",
            "error_message": row.error_message or "",
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = NotificationDeliveryLog(
            delivery_id=payload["delivery_id"],
            workspace_id=payload.get("workspace_id", ""),
            webhook_id=payload.get("webhook_id", ""),
            incident_id=payload.get("incident_id", ""),
            event_type=payload.get("event_type", ""),
            status=payload.get("status", ""),
            request_payload_json=_dump(payload.get("request_payload", {})),
            response_status_code=payload.get("response_status_code", 0),
            response_text=payload.get("response_text", ""),
            error_message=payload.get("error_message", ""),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)

    @classmethod
    def list_by_workspace(cls, workspace_id: str, limit: int = 100) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(NotificationDeliveryLog).filter(NotificationDeliveryLog.workspace_id == workspace_id).order_by(NotificationDeliveryLog.created_at.desc()).limit(limit).all()
            return [cls.to_dict(row) for row in rows]


class EscalationRuleRepository(BaseRepository):
    model = EscalationRule
    id_field = "rule_id"

    @staticmethod
    def to_dict(row: EscalationRule) -> dict:
        return {
            "rule_id": row.rule_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "enabled": bool(row.enabled),
            "severity": row.severity or "",
            "status_filter": row.status_filter or "open",
            "escalate_after_minutes": row.escalate_after_minutes or 0,
            "target_role": row.target_role or "",
            "target_user_id": row.target_user_id or "",
            "webhook_enabled": bool(row.webhook_enabled),
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = EscalationRule(
            rule_id=payload["rule_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            enabled=payload.get("enabled", True),
            severity=payload.get("severity", ""),
            status_filter=payload.get("status_filter", "open"),
            escalate_after_minutes=payload.get("escalate_after_minutes", 60),
            target_role=payload.get("target_role", ""),
            target_user_id=payload.get("target_user_id", ""),
            webhook_enabled=payload.get("webhook_enabled", True),
            created_by=payload.get("created_by", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["rule_id"]) or payload

    @classmethod
    def get_by_id(cls, rule_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(EscalationRule).filter(EscalationRule.rule_id == rule_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str, enabled_only: bool = False) -> list[dict]:
        with SessionLocal() as db:
            query = db.query(EscalationRule).filter(EscalationRule.workspace_id == workspace_id)
            if enabled_only:
                query = query.filter(EscalationRule.enabled == True)  # noqa: E712
            rows = query.order_by(EscalationRule.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def update(cls, rule_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(EscalationRule).filter(EscalationRule.rule_id == rule_id).first()
            if not row:
                return None
            for key in ["name", "enabled", "severity", "status_filter", "escalate_after_minutes", "target_role", "target_user_id", "webhook_enabled"]:
                if key in payload:
                    setattr(row, key, payload[key])
            row.updated_at = payload.get("updated_at", _now())
            db.commit()
        return cls.get_by_id(rule_id)


class ExternalIntegrationRepository(BaseRepository):
    model = ExternalIntegration
    id_field = "integration_id"

    @staticmethod
    def to_dict(row: ExternalIntegration, mask_config: bool = True) -> dict:
        config = _load(row.config_json, {})
        return {
            "integration_id": row.integration_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "integration_type": row.integration_type or "",
            "mode": row.mode or "mock",
            "enabled": bool(row.enabled),
            "config": _mask_secret_config(config) if mask_config else config,
            "secret_masked": row.secret_masked or "",
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
            "last_health_check_at": row.last_health_check_at or "",
            "last_health_status": row.last_health_status or "unknown",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = ExternalIntegration(
            integration_id=payload["integration_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            integration_type=payload.get("integration_type", ""),
            mode=payload.get("mode", "mock"),
            enabled=payload.get("enabled", True),
            config_json=_dump(payload.get("config", {})),
            secret_masked=payload.get("secret_masked", ""),
            created_by=payload.get("created_by", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
            last_health_check_at=payload.get("last_health_check_at", ""),
            last_health_status=payload.get("last_health_status", "unknown"),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["integration_id"]) or payload

    @classmethod
    def get_by_id(cls, integration_id: str, mask_config: bool = True) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ExternalIntegration).filter(ExternalIntegration.integration_id == integration_id).first()
            return cls.to_dict(row, mask_config) if row else None

    @classmethod
    def get_unmasked_by_id(cls, integration_id: str) -> dict | None:
        return cls.get_by_id(integration_id, mask_config=False)

    @classmethod
    def list_by_workspace(cls, workspace_id: str, mask_config: bool = True) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ExternalIntegration).filter(ExternalIntegration.workspace_id == workspace_id).order_by(ExternalIntegration.created_at.desc()).all()
            return [cls.to_dict(row, mask_config) for row in rows]

    @classmethod
    def update(cls, integration_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ExternalIntegration).filter(ExternalIntegration.integration_id == integration_id).first()
            if not row:
                return None
            for key in ["name", "integration_type", "mode", "enabled", "secret_masked", "last_health_check_at", "last_health_status"]:
                if key in payload:
                    setattr(row, key, payload[key])
            if "config" in payload:
                row.config_json = _dump(payload["config"])
            row.updated_at = payload.get("updated_at", _now())
            db.commit()
        return cls.get_by_id(integration_id)


class ExternalSyncRecordRepository(BaseRepository):
    model = ExternalSyncRecord
    id_field = "sync_record_id"

    @staticmethod
    def to_dict(row: ExternalSyncRecord) -> dict:
        return {
            "sync_record_id": row.sync_record_id,
            "workspace_id": row.workspace_id or "",
            "integration_id": row.integration_id or "",
            "integration_type": row.integration_type or "",
            "source_type": row.source_type or "",
            "source_id": row.source_id or "",
            "action": row.action or "",
            "status": row.status or "",
            "request_payload": _mask_secret_config(_load(row.request_payload_json, {})),
            "response_payload": _mask_secret_config(_load(row.response_payload_json, {})),
            "external_id": row.external_id or "",
            "external_url": row.external_url or "",
            "error_message": row.error_message or "",
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = ExternalSyncRecord(
            sync_record_id=payload["sync_record_id"],
            workspace_id=payload.get("workspace_id", ""),
            integration_id=payload.get("integration_id", ""),
            integration_type=payload.get("integration_type", ""),
            source_type=payload.get("source_type", ""),
            source_id=payload.get("source_id", ""),
            action=payload.get("action", ""),
            status=payload.get("status", ""),
            request_payload_json=_dump(payload.get("request_payload", {})),
            response_payload_json=_dump(payload.get("response_payload", {})),
            external_id=payload.get("external_id", ""),
            external_url=payload.get("external_url", ""),
            error_message=payload.get("error_message", ""),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)

    @classmethod
    def list_by_workspace(cls, workspace_id: str, filters: dict | None = None, limit: int = 200) -> list[dict]:
        filters = {key: value for key, value in (filters or {}).items() if value}
        with SessionLocal() as db:
            query = db.query(ExternalSyncRecord).filter(ExternalSyncRecord.workspace_id == workspace_id)
            for key in ["integration_id", "source_type", "status", "action"]:
                if filters.get(key):
                    query = query.filter(getattr(ExternalSyncRecord, key) == filters[key])
            rows = query.order_by(ExternalSyncRecord.created_at.desc()).limit(limit).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def recent_failures_count(cls, workspace_id: str, limit: int = 50) -> int:
        return sum(1 for item in cls.list_by_workspace(workspace_id, {"status": "failed"}, limit=limit))


class ExternalLinkedResourceRepository(BaseRepository):
    model = ExternalLinkedResource
    id_field = "linked_resource_id"

    @staticmethod
    def to_dict(row: ExternalLinkedResource) -> dict:
        return {
            "linked_resource_id": row.linked_resource_id,
            "workspace_id": row.workspace_id or "",
            "integration_id": row.integration_id or "",
            "source_type": row.source_type or "",
            "source_id": row.source_id or "",
            "external_type": row.external_type or "",
            "external_id": row.external_id or "",
            "external_url": row.external_url or "",
            "external_status": row.external_status or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = ExternalLinkedResource(
            linked_resource_id=payload["linked_resource_id"],
            workspace_id=payload.get("workspace_id", ""),
            integration_id=payload.get("integration_id", ""),
            source_type=payload.get("source_type", ""),
            source_id=payload.get("source_id", ""),
            external_type=payload.get("external_type", ""),
            external_id=payload.get("external_id", ""),
            external_url=payload.get("external_url", ""),
            external_status=payload.get("external_status", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)

    @classmethod
    def list_by_workspace(cls, workspace_id: str, filters: dict | None = None) -> list[dict]:
        filters = {key: value for key, value in (filters or {}).items() if value}
        with SessionLocal() as db:
            query = db.query(ExternalLinkedResource).filter(ExternalLinkedResource.workspace_id == workspace_id)
            for key in ["source_type", "source_id", "integration_id"]:
                if filters.get(key):
                    query = query.filter(getattr(ExternalLinkedResource, key) == filters[key])
            if filters.get("integration_type"):
                integration_ids = [
                    row.integration_id
                    for row in db.query(ExternalIntegration).filter(
                        ExternalIntegration.workspace_id == workspace_id,
                        ExternalIntegration.integration_type == filters["integration_type"],
                    ).all()
                ]
                query = query.filter(ExternalLinkedResource.integration_id.in_(integration_ids or [""]))
            rows = query.order_by(ExternalLinkedResource.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]


class MockExternalTicketRepository(BaseRepository):
    model = MockExternalTicket
    id_field = "mock_id"

    @staticmethod
    def to_dict(row: MockExternalTicket) -> dict:
        return {
            "mock_id": row.mock_id,
            "workspace_id": row.workspace_id or "",
            "integration_id": row.integration_id or "",
            "external_type": row.external_type or "",
            "title": row.title or "",
            "description": row.description or "",
            "severity": row.severity or "",
            "status": row.status or "",
            "source_type": row.source_type or "",
            "source_id": row.source_id or "",
            "external_id": row.external_id or "",
            "external_url": row.external_url or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = MockExternalTicket(
            mock_id=payload["mock_id"],
            workspace_id=payload.get("workspace_id", ""),
            integration_id=payload.get("integration_id", ""),
            external_type=payload.get("external_type", ""),
            title=payload.get("title", ""),
            description=payload.get("description", ""),
            severity=payload.get("severity", ""),
            status=payload.get("status", "Open"),
            source_type=payload.get("source_type", ""),
            source_id=payload.get("source_id", ""),
            external_id=payload.get("external_id", ""),
            external_url=payload.get("external_url", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(MockExternalTicket).filter(MockExternalTicket.workspace_id == workspace_id).order_by(MockExternalTicket.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def count_by_workspace_and_type(cls, workspace_id: str, external_type: str) -> int:
        with SessionLocal() as db:
            return db.query(MockExternalTicket).filter(MockExternalTicket.workspace_id == workspace_id, MockExternalTicket.external_type == external_type).count()


class ExecutiveReportRepository(BaseRepository):
    model = ExecutiveReport
    id_field = "report_id"

    @staticmethod
    def to_dict(row: ExecutiveReport, include_report: bool = True) -> dict:
        payload = {
            "report_id": row.report_id,
            "workspace_id": row.workspace_id or "",
            "title": row.title or "",
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
        }
        if include_report:
            payload["report"] = _load(row.report_json, {})
        return payload

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = ExecutiveReport(
            report_id=payload["report_id"],
            workspace_id=payload.get("workspace_id", ""),
            title=payload.get("title", "DriftGuard AI Executive Report"),
            report_json=_dump(payload.get("report", {})),
            created_by=payload.get("created_by", ""),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["report_id"]) or payload

    @classmethod
    def get_by_id(cls, report_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ExecutiveReport).filter(ExecutiveReport.report_id == report_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ExecutiveReport).filter(ExecutiveReport.workspace_id == workspace_id).order_by(ExecutiveReport.created_at.desc()).all()
            return [cls.to_dict(row, include_report=False) for row in rows]


class DemoModeRepository(BaseRepository):
    model = DemoModeState
    id_field = "demo_state_id"

    @staticmethod
    def to_dict(row: DemoModeState) -> dict:
        return {
            "demo_state_id": row.demo_state_id,
            "workspace_id": row.workspace_id or "",
            "enabled": bool(row.enabled),
            "scenario_name": row.scenario_name or "",
            "current_step": row.current_step or 0,
            "completed_steps": _load(row.completed_steps_json, []),
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def get_by_workspace(cls, workspace_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(DemoModeState).filter(DemoModeState.workspace_id == workspace_id).order_by(DemoModeState.updated_at.desc()).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def upsert(cls, payload: dict) -> dict:
        now = payload.get("updated_at", _now())
        with SessionLocal() as db:
            row = db.query(DemoModeState).filter(DemoModeState.workspace_id == payload.get("workspace_id", "")).first()
            if not row:
                row = DemoModeState(
                    demo_state_id=payload.get("demo_state_id", ""),
                    workspace_id=payload.get("workspace_id", ""),
                    created_at=payload.get("created_at", now),
                )
                db.add(row)
            row.enabled = payload.get("enabled", False)
            row.scenario_name = payload.get("scenario_name", "")
            row.current_step = payload.get("current_step", 0)
            row.completed_steps_json = json.dumps(payload.get("completed_steps") or [], ensure_ascii=False)
            row.updated_at = now
            db.commit()
            return cls.to_dict(row)


class ValidationRunRepository(BaseRepository):
    model = ValidationRun
    id_field = "validation_id"

    @staticmethod
    def to_dict(row: ValidationRun, include_payloads: bool = True) -> dict:
        payload = {
            "validation_id": row.validation_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "validation_type": row.validation_type or "",
            "status": row.status or "",
            "dataset_id": row.dataset_id or "",
            "scenario_name": row.scenario_name or "",
            "started_by": row.started_by or "",
            "started_at": row.started_at or "",
            "completed_at": row.completed_at or "",
            "summary": _load(row.summary_json, {}),
            "metrics": _load(row.metrics_json, {}),
        }
        if include_payloads:
            payload["report"] = _load(row.report_json, {})
        return payload

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = ValidationRun(
            validation_id=payload["validation_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            validation_type=payload.get("validation_type", ""),
            status=payload.get("status", "pending"),
            dataset_id=payload.get("dataset_id", ""),
            scenario_name=payload.get("scenario_name", ""),
            started_by=payload.get("started_by", ""),
            started_at=payload.get("started_at", _now()),
            completed_at=payload.get("completed_at", ""),
            summary_json=_dump(payload.get("summary", {})),
            metrics_json=_dump(payload.get("metrics", {})),
            report_json=_dump(payload.get("report", {})),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["validation_id"]) or payload

    @classmethod
    def get_by_id(cls, validation_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ValidationRun).filter(ValidationRun.validation_id == validation_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ValidationRun).filter(ValidationRun.workspace_id == workspace_id).order_by(ValidationRun.started_at.desc()).all()
            return [cls.to_dict(row, include_payloads=False) for row in rows]


class ValidationStepResultRepository(BaseRepository):
    model = ValidationStepResult
    id_field = "step_result_id"

    @staticmethod
    def to_dict(row: ValidationStepResult) -> dict:
        return {
            "step_result_id": row.step_result_id,
            "validation_id": row.validation_id or "",
            "workspace_id": row.workspace_id or "",
            "step_name": row.step_name or "",
            "status": row.status or "",
            "input": _load(row.input_json, {}),
            "output": _load(row.output_json, {}),
            "metrics": _load(row.metrics_json, {}),
            "error_message": row.error_message or "",
            "started_at": row.started_at or "",
            "completed_at": row.completed_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = ValidationStepResult(
            step_result_id=payload["step_result_id"],
            validation_id=payload.get("validation_id", ""),
            workspace_id=payload.get("workspace_id", ""),
            step_name=payload.get("step_name", ""),
            status=payload.get("status", ""),
            input_json=_dump(payload.get("input", {})),
            output_json=_dump(payload.get("output", {})),
            metrics_json=_dump(payload.get("metrics", {})),
            error_message=payload.get("error_message", ""),
            started_at=payload.get("started_at", _now()),
            completed_at=payload.get("completed_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)

    @classmethod
    def list_by_validation(cls, validation_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ValidationStepResult).filter(ValidationStepResult.validation_id == validation_id).order_by(ValidationStepResult.started_at.asc()).all()
            return [cls.to_dict(row) for row in rows]


class ResearchResultRepository(BaseRepository):
    model = ResearchResult
    id_field = "research_result_id"

    @staticmethod
    def to_dict(row: ResearchResult) -> dict:
        return {
            "research_result_id": row.research_result_id,
            "workspace_id": row.workspace_id or "",
            "validation_id": row.validation_id or "",
            "result_type": row.result_type or "",
            "title": row.title or "",
            "result": _load(row.result_json, {}),
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = ResearchResult(
            research_result_id=payload["research_result_id"],
            workspace_id=payload.get("workspace_id", ""),
            validation_id=payload.get("validation_id", ""),
            result_type=payload.get("result_type", ""),
            title=payload.get("title", ""),
            result_json=_dump(payload.get("result", {})),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ResearchResult).filter(ResearchResult.workspace_id == workspace_id).order_by(ResearchResult.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]


class AblationStudyRepository(BaseRepository):
    model = AblationStudyResult
    id_field = "ablation_id"

    @staticmethod
    def to_dict(row: AblationStudyResult) -> dict:
        return {
            "ablation_id": row.ablation_id,
            "workspace_id": row.workspace_id or "",
            "validation_id": row.validation_id or "",
            "experiment_name": row.experiment_name or "",
            "configuration_name": row.configuration_name or "",
            "enabled_modules": _load(row.enabled_modules_json, []),
            "disabled_modules": _load(row.disabled_modules_json, []),
            "metrics": _load(row.metrics_json, {}),
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = AblationStudyResult(
            ablation_id=payload["ablation_id"],
            workspace_id=payload.get("workspace_id", ""),
            validation_id=payload.get("validation_id", ""),
            experiment_name=payload.get("experiment_name", ""),
            configuration_name=payload.get("configuration_name", ""),
            enabled_modules_json=_dump(payload.get("enabled_modules", [])),
            disabled_modules_json=_dump(payload.get("disabled_modules", [])),
            metrics_json=_dump(payload.get("metrics", {})),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.to_dict(row)


class SourceChunkRepository(BaseRepository):
    model = SourceChunk
    id_field = "chunk_id"

    @staticmethod
    def to_dict(row: SourceChunk) -> dict:
        return {
            "chunk_id": row.chunk_id,
            "workspace_id": row.workspace_id or "",
            "source_id": row.source_id or "",
            "connector_id": row.connector_id or "",
            "source_type": row.source_type or "unknown",
            "source_name": row.source_name or "",
            "chunk_index": row.chunk_index or 0,
            "chunk_text": row.chunk_text or "",
            "token_count": row.token_count or 0,
            "keywords": _load(row.keywords_json, []),
            "metadata": _load(row.metadata_json, {}),
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = SourceChunk(
            chunk_id=payload["chunk_id"],
            workspace_id=payload.get("workspace_id", ""),
            source_id=payload.get("source_id", ""),
            connector_id=payload.get("connector_id", ""),
            source_type=payload.get("source_type", "unknown"),
            source_name=payload.get("source_name", ""),
            chunk_index=payload.get("chunk_index", 0),
            chunk_text=payload.get("chunk_text", ""),
            token_count=payload.get("token_count", 0),
            keywords_json=_dump(payload.get("keywords", [])),
            metadata_json=_dump(payload.get("metadata", {})),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return payload

    @classmethod
    def bulk_create(cls, chunks: list[dict]) -> list[dict]:
        if not chunks:
            return []
        rows = [
            SourceChunk(
                chunk_id=chunk["chunk_id"],
                workspace_id=chunk.get("workspace_id", ""),
                source_id=chunk.get("source_id", ""),
                connector_id=chunk.get("connector_id", ""),
                source_type=chunk.get("source_type", "unknown"),
                source_name=chunk.get("source_name", ""),
                chunk_index=chunk.get("chunk_index", 0),
                chunk_text=chunk.get("chunk_text", ""),
                token_count=chunk.get("token_count", 0),
                keywords_json=_dump(chunk.get("keywords", [])),
                metadata_json=_dump(chunk.get("metadata", {})),
                created_at=chunk.get("created_at", _now()),
            )
            for chunk in chunks
        ]
        with SessionLocal() as db:
            db.bulk_save_objects(rows)
            db.commit()
        return chunks

    @classmethod
    def get_by_id(cls, chunk_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(SourceChunk).filter(SourceChunk.chunk_id == chunk_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str, source_type: str = "", source_id: str = "") -> list[dict]:
        with SessionLocal() as db:
            query = db.query(SourceChunk).filter(SourceChunk.workspace_id == workspace_id)
            if source_type:
                query = query.filter(SourceChunk.source_type == source_type)
            if source_id:
                query = query.filter(SourceChunk.source_id == source_id)
            rows = query.order_by(SourceChunk.created_at.desc(), SourceChunk.chunk_index.asc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def search_by_workspace(cls, workspace_id: str, source_types: list[str] | None = None) -> list[dict]:
        with SessionLocal() as db:
            query = db.query(SourceChunk).filter(SourceChunk.workspace_id == workspace_id)
            if source_types:
                query = query.filter(SourceChunk.source_type.in_(source_types))
            return [cls.to_dict(row) for row in query.all()]

    @classmethod
    def delete_by_source(cls, source_id: str) -> int:
        with SessionLocal() as db:
            count = db.query(SourceChunk).filter(SourceChunk.source_id == source_id).delete()
            db.commit()
            return count


class SearchQueryRepository(BaseRepository):
    model = SearchQuery
    id_field = "query_id"

    @staticmethod
    def to_dict(row: SearchQuery) -> dict:
        return {
            "query_id": row.query_id,
            "workspace_id": row.workspace_id or "",
            "user_id": row.user_id or "",
            "query_text": row.query_text or "",
            "filters": _load(row.filters_json, {}),
            "answer": _load(row.answer_json, {}),
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        return cls.save_query(payload)

    @classmethod
    def save_query(cls, payload: dict) -> dict:
        row = SearchQuery(
            query_id=payload["query_id"],
            workspace_id=payload.get("workspace_id", ""),
            user_id=payload.get("user_id", ""),
            query_text=payload.get("query_text", ""),
            filters_json=_dump(payload.get("filters", {})),
            answer_json=_dump(payload.get("answer", {})),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return payload

    @classmethod
    def get_by_id(cls, query_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(SearchQuery).filter(SearchQuery.query_id == query_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        return cls.list_queries(workspace_id)

    @classmethod
    def list_queries(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(SearchQuery).filter(SearchQuery.workspace_id == workspace_id).order_by(SearchQuery.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]


class AgentRunRepository(BaseRepository):
    model = AgentRun
    id_field = "run_id"

    @staticmethod
    def to_dict(row: AgentRun) -> dict:
        return {
            "run_id": row.run_id,
            "workspace_id": row.workspace_id or "",
            "user_id": row.user_id or "",
            "goal": row.goal or "",
            "status": row.status or "planned",
            "plan": _load(row.plan_json, []),
            "final_report": _load(row.final_report_json, {}),
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
            "completed_at": row.completed_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = AgentRun(
            run_id=payload["run_id"],
            workspace_id=payload.get("workspace_id", ""),
            user_id=payload.get("user_id", ""),
            goal=payload.get("goal", ""),
            status=payload.get("status", "planned"),
            plan_json=_dump(payload.get("plan", [])),
            final_report_json=_dump(payload.get("final_report", {})),
            created_at=now,
            updated_at=payload.get("updated_at", now),
            completed_at=payload.get("completed_at", ""),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["run_id"]) or payload

    @classmethod
    def get_by_id(cls, run_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(AgentRun).filter(AgentRun.workspace_id == workspace_id).order_by(AgentRun.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def update_status(cls, run_id: str, status: str, completed: bool = False) -> dict | None:
        with SessionLocal() as db:
            row = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
            if not row:
                return None
            row.status = status
            row.updated_at = _now()
            if completed:
                row.completed_at = row.updated_at
            db.commit()
        return cls.get_by_id(run_id)

    @classmethod
    def update_final_report(cls, run_id: str, final_report: dict, status: str | None = None) -> dict | None:
        with SessionLocal() as db:
            row = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
            if not row:
                return None
            row.final_report_json = _dump(final_report)
            if status:
                row.status = status
            row.updated_at = _now()
            if status in {"completed", "failed", "partial"}:
                row.completed_at = row.updated_at
            db.commit()
        return cls.get_by_id(run_id)

    @classmethod
    def delete(cls, run_id: str) -> bool:
        AgentStepRepository.delete_by_run(run_id)
        return super().delete(run_id)


class AgentStepRepository(BaseRepository):
    model = AgentStep
    id_field = "step_id"

    @staticmethod
    def to_dict(row: AgentStep) -> dict:
        return {
            "step_id": row.step_id,
            "run_id": row.run_id or "",
            "workspace_id": row.workspace_id or "",
            "step_index": row.step_index or 0,
            "step_name": row.step_name or "",
            "tool_name": row.tool_name or "",
            "status": row.status or "pending",
            "input": _load(row.input_json, {}),
            "output": _load(row.output_json, {}),
            "error_message": row.error_message or "",
            "started_at": row.started_at or "",
            "completed_at": row.completed_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = AgentStep(
            step_id=payload["step_id"],
            run_id=payload.get("run_id", ""),
            workspace_id=payload.get("workspace_id", ""),
            step_index=payload.get("step_index", 0),
            step_name=payload.get("step_name", ""),
            tool_name=payload.get("tool_name", ""),
            status=payload.get("status", "pending"),
            input_json=_dump(payload.get("input", {})),
            output_json=_dump(payload.get("output", {})),
            error_message=payload.get("error_message", ""),
            started_at=payload.get("started_at", ""),
            completed_at=payload.get("completed_at", ""),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["step_id"]) or payload

    @classmethod
    def get_by_id(cls, step_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(AgentStep).filter(AgentStep.step_id == step_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_run(cls, run_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.step_index.asc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def update_status(cls, step_id: str, status: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(AgentStep).filter(AgentStep.step_id == step_id).first()
            if not row:
                return None
            row.status = status
            if status == "running":
                row.started_at = _now()
            if status in {"completed", "failed", "skipped"}:
                row.completed_at = _now()
            db.commit()
        return cls.get_by_id(step_id)

    @classmethod
    def update_output(cls, step_id: str, output: dict, status: str = "completed") -> dict | None:
        with SessionLocal() as db:
            row = db.query(AgentStep).filter(AgentStep.step_id == step_id).first()
            if not row:
                return None
            row.output_json = _dump(output)
            row.status = status
            row.completed_at = _now()
            db.commit()
        return cls.get_by_id(step_id)

    @classmethod
    def update_error(cls, step_id: str, error_message: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(AgentStep).filter(AgentStep.step_id == step_id).first()
            if not row:
                return None
            row.error_message = error_message
            row.status = "failed"
            row.completed_at = _now()
            db.commit()
        return cls.get_by_id(step_id)

    @classmethod
    def delete_by_run(cls, run_id: str) -> int:
        with SessionLocal() as db:
            count = db.query(AgentStep).filter(AgentStep.run_id == run_id).delete()
            db.commit()
            return count


class LLMSettingsRepository(BaseRepository):
    model = LLMSettings
    id_field = "settings_id"

    @staticmethod
    def to_dict(row: LLMSettings) -> dict:
        return {
            "settings_id": row.settings_id,
            "workspace_id": row.workspace_id or "",
            "provider": row.provider or "local",
            "model_name": row.model_name or "local-rule-engine",
            "reasoning_mode": row.reasoning_mode or "local_only",
            "api_key_masked": row.api_key_masked or "",
            "config": _load(row.config_json, {}),
            "enabled": bool(row.enabled),
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = LLMSettings(
            settings_id=payload["settings_id"],
            workspace_id=payload.get("workspace_id", ""),
            provider=payload.get("provider", "local"),
            model_name=payload.get("model_name", "local-rule-engine"),
            reasoning_mode=payload.get("reasoning_mode", "local_only"),
            api_key_masked=payload.get("api_key_masked", ""),
            config_json=_dump(payload.get("config", {})),
            enabled=payload.get("enabled", True),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["settings_id"]) or payload

    @classmethod
    def get_by_id(cls, settings_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(LLMSettings).filter(LLMSettings.settings_id == settings_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(LLMSettings).filter(LLMSettings.workspace_id == workspace_id).order_by(LLMSettings.updated_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def get_by_workspace_provider(cls, workspace_id: str, provider: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(LLMSettings).filter(LLMSettings.workspace_id == workspace_id, LLMSettings.provider == provider).order_by(LLMSettings.updated_at.desc()).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def update(cls, settings_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(LLMSettings).filter(LLMSettings.settings_id == settings_id).first()
            if not row:
                return None
            for key in ["provider", "model_name", "reasoning_mode", "api_key_masked", "enabled"]:
                if key in payload:
                    setattr(row, key, payload[key])
            if "config" in payload:
                row.config_json = _dump(payload["config"])
            row.updated_at = payload.get("updated_at", _now())
            db.commit()
        return cls.get_by_id(settings_id)


class PromptTemplateRepository(BaseRepository):
    model = PromptTemplate
    id_field = "template_id"

    @staticmethod
    def to_dict(row: PromptTemplate) -> dict:
        return {
            "template_id": row.template_id,
            "workspace_id": row.workspace_id or "",
            "name": row.name or "",
            "task_type": row.task_type or "",
            "template_text": row.template_text or "",
            "variables": _load(row.variables_json, []),
            "created_by": row.created_by or "",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = PromptTemplate(
            template_id=payload["template_id"],
            workspace_id=payload.get("workspace_id", ""),
            name=payload.get("name", ""),
            task_type=payload.get("task_type", ""),
            template_text=payload.get("template_text", ""),
            variables_json=_dump(payload.get("variables", [])),
            created_by=payload.get("created_by", ""),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["template_id"]) or payload

    @classmethod
    def get_by_id(cls, template_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(PromptTemplate).filter(PromptTemplate.template_id == template_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(PromptTemplate).filter(PromptTemplate.workspace_id == workspace_id).order_by(PromptTemplate.updated_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def update(cls, template_id: str, payload: dict) -> dict | None:
        with SessionLocal() as db:
            row = db.query(PromptTemplate).filter(PromptTemplate.template_id == template_id).first()
            if not row:
                return None
            for key in ["name", "task_type", "template_text"]:
                if key in payload:
                    setattr(row, key, payload[key])
            if "variables" in payload:
                row.variables_json = _dump(payload["variables"])
            row.updated_at = payload.get("updated_at", _now())
            db.commit()
        return cls.get_by_id(template_id)


class ReasoningTraceRepository(BaseRepository):
    model = ReasoningTrace
    id_field = "trace_id"

    @staticmethod
    def to_dict(row: ReasoningTrace) -> dict:
        return {
            "trace_id": row.trace_id,
            "workspace_id": row.workspace_id or "",
            "user_id": row.user_id or "",
            "task_type": row.task_type or "",
            "reasoning_mode": row.reasoning_mode or "local_only",
            "provider": row.provider or "local",
            "input_summary": row.input_summary or "",
            "local_output": _load(row.local_output_json, {}),
            "llm_output": _load(row.llm_output_json, {}),
            "final_output": _load(row.final_output_json, {}),
            "validation_result": _load(row.validation_result_json, {}),
            "status": row.status or "",
            "error_message": row.error_message or "",
            "created_at": row.created_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = ReasoningTrace(
            trace_id=payload["trace_id"],
            workspace_id=payload.get("workspace_id", ""),
            user_id=payload.get("user_id", ""),
            task_type=payload.get("task_type", ""),
            reasoning_mode=payload.get("reasoning_mode", "local_only"),
            provider=payload.get("provider", "local"),
            input_summary=payload.get("input_summary", ""),
            local_output_json=_dump(payload.get("local_output", {})),
            llm_output_json=_dump(payload.get("llm_output", {})),
            final_output_json=_dump(payload.get("final_output", {})),
            validation_result_json=_dump(payload.get("validation_result", {})),
            status=payload.get("status", "completed"),
            error_message=payload.get("error_message", ""),
            created_at=payload.get("created_at", _now()),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["trace_id"]) or payload

    @classmethod
    def get_by_id(cls, trace_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(ReasoningTrace).filter(ReasoningTrace.trace_id == trace_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(ReasoningTrace).filter(ReasoningTrace.workspace_id == workspace_id).order_by(ReasoningTrace.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]


class HybridAnalysisRepository(BaseRepository):
    model = HybridAnalysisResult
    id_field = "result_id"

    @staticmethod
    def to_dict(row: HybridAnalysisResult) -> dict:
        return {
            "result_id": row.result_id,
            "workspace_id": row.workspace_id or "",
            "trace_id": row.trace_id or "",
            "task_type": row.task_type or "",
            "source_context": _load(row.source_context_json, {}),
            "local_result": _load(row.local_result_json, {}),
            "llm_result": _load(row.llm_result_json, {}),
            "comparison": _load(row.comparison_json, {}),
            "final_result": _load(row.final_result_json, {}),
            "approved_by_user": bool(row.approved_by_user),
            "approval_status": row.approval_status or "pending",
            "created_at": row.created_at or "",
            "updated_at": row.updated_at or "",
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        now = payload.get("created_at", _now())
        row = HybridAnalysisResult(
            result_id=payload["result_id"],
            workspace_id=payload.get("workspace_id", ""),
            trace_id=payload.get("trace_id", ""),
            task_type=payload.get("task_type", ""),
            source_context_json=_dump(payload.get("source_context", {})),
            local_result_json=_dump(payload.get("local_result", {})),
            llm_result_json=_dump(payload.get("llm_result", {})),
            comparison_json=_dump(payload.get("comparison", {})),
            final_result_json=_dump(payload.get("final_result", {})),
            approved_by_user=payload.get("approved_by_user", False),
            approval_status=payload.get("approval_status", "pending"),
            created_at=now,
            updated_at=payload.get("updated_at", now),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return cls.get_by_id(payload["result_id"]) or payload

    @classmethod
    def get_by_id(cls, result_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(HybridAnalysisResult).filter(HybridAnalysisResult.result_id == result_id).first()
            return cls.to_dict(row) if row else None

    @classmethod
    def list_by_workspace(cls, workspace_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(HybridAnalysisResult).filter(HybridAnalysisResult.workspace_id == workspace_id).order_by(HybridAnalysisResult.created_at.desc()).all()
            return [cls.to_dict(row) for row in rows]

    @classmethod
    def update_approval(cls, result_id: str, approval_status: str, approved_by_user: bool = False, edited_output: dict | None = None) -> dict | None:
        with SessionLocal() as db:
            row = db.query(HybridAnalysisResult).filter(HybridAnalysisResult.result_id == result_id).first()
            if not row:
                return None
            row.approval_status = approval_status
            row.approved_by_user = approved_by_user
            if edited_output:
                row.final_result_json = _dump(edited_output)
            row.updated_at = _now()
            db.commit()
        return cls.get_by_id(result_id)


class AuditRepository(BaseRepository):
    model = AuditEvent
    id_field = "audit_id"

    @staticmethod
    def to_dict(row: AuditEvent) -> dict:
        return {
            "audit_id": row.audit_id,
            "created_at": row.created_at,
            "workspace_id": row.workspace_id or "",
            "workspace_name": row.workspace_name or "",
            "user_id": row.user_id or "",
            "user_name": row.user_name or "",
            "user_email": row.user_email or "",
            "user_role": row.user_role or "",
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id or "",
            "resource_name": row.resource_name or "",
            "status": row.status,
            "severity": row.severity,
            "message": row.message,
            "metadata": _load(row.metadata_json, {}),
        }

    @classmethod
    def create(cls, payload: dict) -> dict:
        row = AuditEvent(
            audit_id=payload["audit_id"],
            created_at=payload.get("created_at", _now()),
            workspace_id=payload.get("workspace_id", ""),
            workspace_name=payload.get("workspace_name", ""),
            user_id=payload.get("user_id", ""),
            user_name=payload.get("user_name", ""),
            user_email=payload.get("user_email", ""),
            user_role=payload.get("user_role", ""),
            action=payload.get("action", ""),
            resource_type=payload.get("resource_type", ""),
            resource_id=payload.get("resource_id", ""),
            resource_name=payload.get("resource_name", ""),
            status=payload.get("status", ""),
            severity=payload.get("severity", ""),
            message=payload.get("message", ""),
            metadata_json=_dump(payload.get("metadata", {})),
        )
        with SessionLocal() as db:
            db.merge(row)
            db.commit()
        return payload

    @classmethod
    def list(cls, filters: dict | None = None) -> list[dict]:
        filters = {key: value for key, value in (filters or {}).items() if value}
        with SessionLocal() as db:
            query = db.query(AuditEvent)
            for key, value in filters.items():
                query = query.filter(getattr(AuditEvent, key) == value)
            return [cls.to_dict(row) for row in query.order_by(AuditEvent.created_at.desc()).all()]

    @classmethod
    def get_by_id(cls, audit_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.query(AuditEvent).filter(AuditEvent.audit_id == audit_id).first()
            return cls.to_dict(row) if row else None


def table_counts() -> dict:
    init_database()
    tables = {
        "agent_runs": AgentRun,
        "agent_steps": AgentStep,
        "llm_settings": LLMSettings,
        "prompt_templates": PromptTemplate,
        "reasoning_traces": ReasoningTrace,
        "hybrid_analysis_results": HybridAnalysisResult,
        "users": User,
        "workspaces": Workspace,
        "datasets": Dataset,
        "evaluations": Evaluation,
        "feedback": Feedback,
        "alerts": Alert,
        "connectors": Connector,
        "imported_sources": ImportedSource,
        "connector_sync_runs": ConnectorSyncRun,
        "generated_dataset_cases": GeneratedDatasetCase,
        "benchmark_datasets": BenchmarkDataset,
        "benchmark_import_runs": BenchmarkImportRun,
        "benchmark_examples": BenchmarkExample,
        "training_dataset_exports": TrainingDatasetExport,
        "model_experiments": ModelExperiment,
        "model_artifacts": ModelArtifact,
        "deployed_models": DeployedModel,
        "incidents": Incident,
        "incident_comments": IncidentComment,
        "incident_timeline_events": IncidentTimelineEvent,
        "webhook_endpoints": WebhookEndpoint,
        "notification_templates": NotificationTemplate,
        "notification_delivery_logs": NotificationDeliveryLog,
        "escalation_rules": EscalationRule,
        "external_integrations": ExternalIntegration,
        "external_sync_records": ExternalSyncRecord,
        "external_linked_resources": ExternalLinkedResource,
        "mock_external_tickets": MockExternalTicket,
        "executive_reports": ExecutiveReport,
        "demo_mode_state": DemoModeState,
        "validation_runs": ValidationRun,
        "validation_step_results": ValidationStepResult,
        "research_results": ResearchResult,
        "ablation_study_results": AblationStudyResult,
        "source_chunks": SourceChunk,
        "search_queries": SearchQuery,
        "audit_events": AuditEvent,
    }
    with SessionLocal() as db:
        return {name: db.query(model).count() for name, model in tables.items()}
