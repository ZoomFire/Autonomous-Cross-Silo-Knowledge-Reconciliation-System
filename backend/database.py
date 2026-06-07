import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from models import DriftReport, HistoryReport


DB_PATH = Path(__file__).resolve().parent / "driftguard.db"


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drift_id TEXT,
                entity TEXT,
                summary TEXT,
                drift_type TEXT,
                severity TEXT,
                confidence_score REAL,
                recommended_action TEXT,
                status TEXT,
                evidence TEXT,
                created_at TEXT
            )
            """
        )


def save_report(report: DriftReport) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analysis_reports (
                drift_id, entity, summary, drift_type, severity, confidence_score,
                recommended_action, status, evidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.drift_id,
                report.entity,
                report.summary,
                report.drift_type,
                report.severity,
                report.confidence_score,
                report.recommended_action,
                report.status,
                json.dumps(report.evidence),
                created_at,
            ),
        )
        return int(cursor.lastrowid)


def _row_to_history(row) -> HistoryReport:
    return HistoryReport(
        id=row[0],
        drift_id=row[1],
        entity=row[2],
        summary=row[3],
        drift_type=row[4],
        severity=row[5],
        confidence_score=row[6],
        recommended_action=row[7],
        status=row[8],
        created_at=row[10],
    )


def get_reports() -> list[HistoryReport]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, drift_id, entity, summary, drift_type, severity, confidence_score,
                   recommended_action, status, evidence, created_at
            FROM analysis_reports
            ORDER BY datetime(created_at) DESC, id DESC
            """
        ).fetchall()
    return [_row_to_history(row) for row in rows]


def get_report_by_id(report_id: int) -> HistoryReport | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, drift_id, entity, summary, drift_type, severity, confidence_score,
                   recommended_action, status, evidence, created_at
            FROM analysis_reports
            WHERE id = ?
            """,
            (report_id,),
        ).fetchone()
    return _row_to_history(row) if row else None
