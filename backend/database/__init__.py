import json
from datetime import datetime, timezone

from models import DriftReport, HistoryReport

from .db import Base, SessionLocal, engine, init_database


def init_db():
    init_database()


def save_report(report: DriftReport) -> int:
    from .models import AnalysisReport

    created_at = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as db:
        row = AnalysisReport(
            drift_id=report.drift_id,
            entity=report.entity,
            summary=report.summary,
            drift_type=report.drift_type,
            severity=report.severity,
            confidence_score=report.confidence_score,
            recommended_action=report.recommended_action,
            status=report.status,
            evidence=json.dumps(report.evidence),
            created_at=created_at,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return int(row.id)


def _row_to_history(row) -> HistoryReport:
    return HistoryReport(
        id=row.id,
        drift_id=row.drift_id,
        entity=row.entity,
        summary=row.summary,
        drift_type=row.drift_type,
        severity=row.severity,
        confidence_score=row.confidence_score,
        recommended_action=row.recommended_action,
        status=row.status,
        created_at=row.created_at,
    )


def get_reports() -> list[HistoryReport]:
    from .models import AnalysisReport

    with SessionLocal() as db:
        rows = db.query(AnalysisReport).order_by(AnalysisReport.created_at.desc(), AnalysisReport.id.desc()).all()
        return [_row_to_history(row) for row in rows]


def get_report_by_id(report_id: int) -> HistoryReport | None:
    from .models import AnalysisReport

    with SessionLocal() as db:
        row = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
        return _row_to_history(row) if row else None
