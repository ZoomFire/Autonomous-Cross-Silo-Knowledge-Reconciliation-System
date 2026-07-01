import json
import tempfile
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import ValidationError

from audit_store import (
    build_audit_summary,
    build_compliance_risk_summary,
    delete_audit_event,
    ensure_audit_dir,
    export_audit_json,
    export_audit_markdown,
    get_audit_event,
    list_audit_events,
    log_audit_event,
)
from agent.executor import create_run_with_steps, execute_agent_run
from agent.planner import create_agent_plan
from agent.report_builder import agent_report_to_markdown
from config import (
    AGENT_RATE_LIMIT_PER_HOUR,
    APP_ENV,
    APP_NAME,
    CORS_ORIGINS,
    DATABASE_URL,
    INCIDENT_AUTO_CREATE_ENABLED,
    INCIDENT_AUTO_CREATE_SEVERITIES,
    MAX_UPLOAD_SIZE_MB,
    RAG_RATE_LIMIT_PER_MINUTE,
    STORAGE_DIR,
    UPLOAD_RATE_LIMIT_PER_HOUR,
    USE_DATABASE,
    WEBHOOK_TIMEOUT_SECONDS,
)
from database.backup_restore import export_database_backup, import_database_backup
from database.migrate_json_to_db import migrate_json_to_database
from database.repositories import (
    AgentRunRepository,
    AgentStepRepository,
    AlertRepository,
    BenchmarkDatasetRepository,
    BenchmarkExampleRepository,
    BenchmarkImportRunRepository,
    ConnectorRepository,
    AuditRepository,
    DatasetRepository,
    DeployedModelRepository,
    EscalationRuleRepository,
    EvaluationRepository,
    ExecutiveReportRepository,
    ExternalIntegrationRepository,
    ExternalLinkedResourceRepository,
    FeedbackRepository,
    HybridAnalysisRepository,
    ImportedSourceRepository,
    IncidentCommentRepository,
    IncidentRepository,
    IncidentTimelineRepository,
    LLMSettingsRepository,
    MockExternalTicketRepository,
    ModelArtifactRepository,
    ModelExperimentRepository,
    MonitoringRuleRepository,
    NotificationDeliveryRepository,
    PromptTemplateRepository,
    ReasoningTraceRepository,
    SearchQueryRepository,
    SessionRepository,
    TrainingDatasetExportRepository,
    UserRepository,
    ResearchResultRepository,
    ValidationRunRepository,
    ValidationStepResultRepository,
    WebhookRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
    table_counts,
)
from benchmarks.commitpack_adapter import CommitPackAdapter
from benchmarks.cosqa_adapter import CosQAAdapter
from benchmarks.custom_adapter import CustomAdapter
from benchmarks.quality_analyzer import analyze_benchmark_quality, score_example
from benchmarks.registry import get_supported_benchmark_datasets
from benchmarks.snli_adapter import SNLIAdapter
from benchmarks.spider_adapter import SpiderAdapter
from benchmarks.training_exporter import create_train_validation_test_split, export_training_json, export_training_jsonl, split_counts
from ml import SUPPORTED_MODEL_TYPES, SUPPORTED_TASK_TYPES
from ml.data_loader import load_training_examples
from ml.model_registry import delete_model_artifact, ensure_model_dirs, get_model_metadata
from ml.predictor import predict_with_active_model
from ml.trainer import train_model
from incidents.escalation_service import check_escalations
from incidents.exporter import incident_to_markdown
from incidents.incident_service import add_comment, assign_incident, create_incident, update_incident_status
from incidents.notification_service import send_test_webhook
from integrations.integration_service import create_integration, get_integration_health_summary, list_integrations as list_external_integrations, list_sync_records as list_external_sync_records, send_incident_notification, sync_incident_to_external, test_integration
from executive.demo_mode import advance_demo_step, disable_demo_mode, enable_demo_mode, get_demo_scenarios, get_demo_state, reset_demo_data, seed_executive_demo_data
from executive.metrics_collector import collect_executive_metrics
from executive.report_builder import build_executive_report, export_executive_report_markdown
from executive.roi_calculator import calculate_roi
from validation.ablation_runner import run_ablation_study
from validation.baseline_comparison import compare_baselines
from validation.chart_data_builder import build_chart_data
from validation.demo_flow_validator import validate_demo_flow
from validation.research_report_builder import build_research_report, export_research_report_markdown, save_research_report
from validation.validation_runner import run_demo_scenario_validation, run_full_system_validation, run_real_dataset_validation
from llm.hybrid_reasoner import reasoning_trace_to_markdown, run_hybrid_reasoning
from llm.prompt_manager import create_prompt_template, ensure_default_prompt_templates, list_prompt_templates, update_prompt_template
from logger import logger
from auth_store import get_user, list_user_sessions, list_users
from claim_extractor import build_truth_triangle, extract_claims, extract_entity
from connector_store import (
    create_connector,
    create_generated_case,
    create_source,
    delete_connector,
    delete_source,
    ensure_connector_dirs,
    get_connector,
    get_source,
    list_connectors,
    list_sources,
    list_sources_by_connector,
    list_sync_runs,
    save_sync_run,
    update_connector,
    utc_now,
)
from connectors.dataset_case_builder import build_dataset_cases_from_sources
from connectors.file_connector import FileConnector
from connectors.github_connector import GitHubConnector
from database import get_report_by_id, get_reports, init_db, save_report
from dataset_evaluator import evaluate_dataset, evaluate_dataset_cases, evaluation_to_markdown, load_sample_dataset
from dataset_store import (
    compare_evaluations,
    delete_dataset,
    delete_evaluation_result,
    ensure_storage_dirs,
    get_dataset,
    get_evaluation_result,
    list_datasets,
    list_evaluation_history,
    save_dataset,
    save_evaluation_result,
)
from drift_detector import detect_drift
from drift_timeline import build_evaluation_timeline, export_timeline_markdown
from errors import api_error
from feedback_store import (
    build_training_dataset,
    calculate_feedback_summary,
    delete_feedback,
    export_corrected_dataset,
    get_feedback_for_evaluation,
    list_feedback,
    save_case_feedback,
)
from root_cause_analyzer import build_root_cause_report, root_cause_report_to_markdown
from impact_graph import build_evaluation_impact_graph, export_impact_graph_json
from monitoring_store import (
    create_monitoring_rule,
    delete_alert,
    delete_monitoring_rule,
    delete_monitoring_run,
    ensure_monitoring_dirs,
    export_alerts_markdown,
    get_alert,
    get_monitoring_rule,
    get_monitoring_run,
    list_alerts,
    list_monitoring_rules,
    list_monitoring_runs,
    mark_alert_status,
    run_monitoring_check,
    update_monitoring_rule,
)
from models import (
    AnalysisRequest,
    AnalysisResponse,
    CaseFeedbackRequest,
    CaseFeedbackResponse,
    DatasetCase,
    DatasetEvaluationResponse,
    FeedbackSummaryResponse,
    HistoryReport,
)
from observability_store import (
    build_observability_summary,
    build_performance_health,
    ensure_observability_dir,
    list_error_events,
    list_request_metrics,
    save_error_event,
    save_request_metric,
)
from permissions import check_permission, require_auth, require_workspace_admin, require_workspace_member
from privacy_store import approve_delete_request, create_delete_request, ensure_privacy_dirs, get_privacy_settings, list_delete_requests, update_privacy_settings
from rate_limiter import check_rate_limit
from rag.search_service import export_answer_markdown, index_imported_sources, index_sources_for_workspace, search_workspace_sources
from security_utils import detect_sensitive_data, mask_secret, redact_sensitive_text, sanitize_metadata
from workspace_store import (
    add_user_to_workspace,
    create_workspace,
    delete_workspace,
    ensure_workspace_dir,
    get_user_workspaces,
    get_workspace,
    list_workspace_members,
    list_workspaces,
    remove_user_from_workspace,
    update_workspace,
)


app = FastAPI(title="DriftGuard AI Level 4.7 Backend")
LATEST_EVALUATION_RESULT: DatasetEvaluationResponse | None = None

INVALID_DATASET_MESSAGE = (
    "Invalid dataset format. Each case must include case_id, title, documentation, code, jira, "
    "commit, logs, database_config, expected_label, expected_drift_type, expected_severity."
)
SNLI_JSONL_PREVIEW_LIMIT = 100
SNLI_LABEL_MAP = {
    "contradiction": "contradiction",
    "entailment": "no_drift",
    "neutral": "manual_review",
}


async def _read_upload_limited(file: UploadFile) -> bytes:
    content = await file.read()
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds maximum allowed size.")
    return content

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith(("/auth", "/llm", "/agent", "/system", "/observability", "/privacy", "/security")):
        response.headers["Cache-Control"] = "no-store"
    return response


def _request_user_id(request: Request) -> str:
    return "public-user"


@app.middleware("http")
async def add_request_id(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        save_request_metric({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "duration_ms": (perf_counter() - started) * 1000,
            "user_id": _request_user_id(request),
            "workspace_id": request.query_params.get("workspace_id", "none"),
        })
        raise
    save_request_metric({
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": (perf_counter() - started) * 1000,
        "user_id": _request_user_id(request),
        "workspace_id": request.query_params.get("workspace_id", "none"),
    })
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        save_error_event({
            "request_id": getattr(request.state, "request_id", ""),
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "message": str(exc.detail),
            "error_type": exc.__class__.__name__,
            "user_id": _request_user_id(request),
        })
    details = exc.detail if isinstance(exc.detail, dict) else {}
    detail = exc.detail if isinstance(exc.detail, str) else details.get("message", "Request failed.")
    return JSONResponse(status_code=exc.status_code, content=api_error(detail, exc.status_code, details))


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error: %s", exc)
    save_error_event({
        "request_id": getattr(request.state, "request_id", ""),
        "path": request.url.path,
        "method": request.method,
        "status_code": 500,
        "message": "Internal server error",
        "error_type": exc.__class__.__name__,
        "user_id": _request_user_id(request),
    })
    return JSONResponse(status_code=500, content=api_error("Internal server error. Please check server logs.", 500))


@app.on_event("startup")
def on_startup():
    init_db()
    ensure_audit_dir()
    ensure_workspace_dir()
    ensure_storage_dirs()
    ensure_monitoring_dirs()
    ensure_connector_dirs()
    ensure_observability_dir()
    ensure_privacy_dirs()
    ensure_model_dirs()
    ensure_default_prompt_templates()
    logger.info("Startup complete for %s in %s mode. database=%s storage=%s", APP_NAME, APP_ENV, USE_DATABASE, STORAGE_DIR)


def _health_message() -> dict:
    return {"status": "ok", "message": "Silo Project Backend is running"}


@app.get("/")
def root():
    return _health_message()


@app.get("/health")
def health():
    storage_available = STORAGE_DIR.exists() and STORAGE_DIR.is_dir()
    return {
        **_health_message(),
        "app_name": APP_NAME,
        "service": "DriftGuard AI Level 4.7 Backend",
        "environment": APP_ENV,
        "database_enabled": USE_DATABASE,
        "storage_available": storage_available,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/system/ready")
def system_ready():
    checks = {"database": "unknown", "storage": "unknown"}
    try:
        table_counts()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        logger.error("Readiness database check failed: %s", exc)
    checks["storage"] = "ok" if STORAGE_DIR.exists() and STORAGE_DIR.is_dir() else "missing"
    return {"ready": all(value == "ok" for value in checks.values()), "checks": checks}


def _require_workspace_scope(user: dict, workspace_id: str):
    require_workspace_member(user, workspace_id)


def _assert_item_workspace(item: dict, workspace_id: str):
    if workspace_id and item.get("workspace_id", "") != workspace_id:
        raise HTTPException(status_code=404, detail="Item not found in this workspace.")


AUTH_REMOVED_MESSAGE = "Authentication has been removed. The app runs without login."


def _auth_removed():
    raise HTTPException(status_code=410, detail=AUTH_REMOVED_MESSAGE)


@app.post("/auth/signup")
def signup():
    _auth_removed()


@app.post("/auth/login")
def login():
    _auth_removed()


@app.post("/auth/logout")
def logout():
    _auth_removed()


@app.get("/auth/sessions")
def auth_sessions():
    _auth_removed()


@app.delete("/auth/sessions/{session_id}")
def auth_revoke_session(session_id: str):
    _auth_removed()


@app.get("/auth/me")
def auth_me():
    _auth_removed()


@app.get("/auth/users")
def auth_users():
    _auth_removed()


@app.put("/auth/users/{user_id}/role")
def auth_update_user_role(user_id: str):
    _auth_removed()


@app.delete("/auth/users/{user_id}")
def auth_delete_user(user_id: str):
    _auth_removed()


@app.post("/workspaces")
def create_workspace_endpoint(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "create_workspace")
    try:
        workspace = create_workspace(payload.get("name", ""), payload.get("description", ""), user["user_id"], user["role"])
        log_audit_event("create_workspace", "workspace", workspace["workspace_id"], workspace["name"], "success", "Low", f"Workspace {workspace['name']} created.", user=user, workspace=workspace)
        return workspace
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/workspaces")
def workspaces(user: dict = Depends(require_auth)):
    return list_workspaces() if user.get("role") == "admin" else get_user_workspaces(user["user_id"])


@app.get("/workspaces/{workspace_id}")
def workspace_item(workspace_id: str, user: dict = Depends(require_auth)):
    return require_workspace_member(user, workspace_id)


@app.put("/workspaces/{workspace_id}")
def update_workspace_endpoint(workspace_id: str, payload: dict, user: dict = Depends(require_auth)):
    require_workspace_admin(user, workspace_id)
    try:
        workspace = update_workspace(workspace_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    log_audit_event("update_workspace", "workspace", workspace_id, workspace.get("name", ""), "success", "Low", "Workspace updated.", user=user, workspace=workspace)
    return workspace


@app.delete("/workspaces/{workspace_id}")
def delete_workspace_endpoint(workspace_id: str, user: dict = Depends(require_auth)):
    workspace = require_workspace_admin(user, workspace_id)
    from database.repositories import SearchQueryRepository, SourceChunkRepository

    for chunk in SourceChunkRepository.list_by_workspace(workspace_id):
        SourceChunkRepository.delete(chunk["chunk_id"])
    for query in SearchQueryRepository.list_queries(workspace_id):
        SearchQueryRepository.delete(query["query_id"])
    if not delete_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found.")
    log_audit_event("delete_workspace", "workspace", workspace_id, workspace.get("name", ""), "success", "Critical", "Workspace deleted.", user=user, workspace=workspace)
    return {"status": "ok", "message": "Workspace deleted successfully."}


@app.post("/workspaces/{workspace_id}/members")
def add_workspace_member_endpoint(workspace_id: str, payload: dict, user: dict = Depends(require_auth)):
    require_workspace_admin(user, workspace_id)
    if not get_user(payload.get("user_id", "")):
        raise HTTPException(status_code=404, detail="User not found.")
    try:
        workspace = add_user_to_workspace(workspace_id, payload.get("user_id", ""), payload.get("role", "viewer"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    log_audit_event("add_workspace_member", "workspace", workspace_id, workspace.get("name", ""), "success", "Medium", "Workspace member added or updated.", user=user, workspace=workspace, metadata={"member_user_id": payload.get("user_id", ""), "member_role": payload.get("role", "viewer")})
    return workspace


@app.delete("/workspaces/{workspace_id}/members/{user_id}")
def remove_workspace_member_endpoint(workspace_id: str, user_id: str, user: dict = Depends(require_auth)):
    require_workspace_admin(user, workspace_id)
    try:
        workspace = remove_user_from_workspace(workspace_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    log_audit_event("remove_workspace_member", "workspace", workspace_id, workspace.get("name", ""), "success", "Medium", "Workspace member removed.", user=user, workspace=workspace, metadata={"member_user_id": user_id})
    return workspace


@app.get("/workspaces/{workspace_id}/members")
def workspace_members(workspace_id: str, user: dict = Depends(require_auth)):
    require_workspace_member(user, workspace_id)
    return list_workspace_members(workspace_id)


@app.get("/audit/events")
def audit_events(
    workspace_id: str = Query(""),
    user_id: str = Query(""),
    action: str = Query(""),
    resource_type: str = Query(""),
    status: str = Query(""),
    severity: str = Query(""),
    user: dict = Depends(require_auth),
):
    check_permission(user, "manage_users")
    return list_audit_events({
        "workspace_id": workspace_id,
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "status": status,
        "severity": severity,
    })


@app.get("/audit/events/{audit_id}")
def audit_event_item(audit_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    event = get_audit_event(audit_id)
    if not event:
        raise HTTPException(status_code=404, detail="Audit event not found.")
    return event


@app.get("/audit/summary")
def audit_summary(workspace_id: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    return build_audit_summary(workspace_id)


@app.get("/audit/compliance-risk")
def audit_compliance_risk(workspace_id: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    return build_compliance_risk_summary(workspace_id)


@app.get("/audit/export-json")
def audit_export_json(workspace_id: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    payload = export_audit_json(workspace_id)
    log_audit_event("export_audit", "audit", status="success", severity="Medium", message="User exported audit JSON.", user=user, metadata={"format": "json"})
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-audit-report.json"},
    )


@app.get("/audit/export-markdown")
def audit_export_markdown(workspace_id: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    content = export_audit_markdown(workspace_id)
    log_audit_event("export_audit", "audit", status="success", severity="Medium", message="User exported audit Markdown.", user=user, metadata={"format": "markdown"})
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=driftguard-audit-report.md"},
    )


@app.delete("/audit/events/{audit_id}")
def delete_audit_event_endpoint(audit_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    if not delete_audit_event(audit_id):
        raise HTTPException(status_code=404, detail="Audit event not found.")
    log_audit_event("delete_audit_event", "audit", audit_id, audit_id, "success", "High", "User deleted an audit event.", user=user)
    return {"status": "ok", "message": "Audit event deleted successfully."}


@app.get("/observability/summary")
def observability_summary(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    log_audit_event("observability_viewed", "observability", resource_name="System Observability", status="success", severity="Info", message="Admin viewed observability summary.", user=user)
    return build_observability_summary()


@app.get("/observability/requests")
def observability_requests(
    path: str = Query(""),
    status_code: str = Query(""),
    slow_only: bool = Query(False),
    user: dict = Depends(require_auth),
):
    check_permission(user, "manage_users")
    return list_request_metrics({"path": path, "status_code": status_code, "slow_only": slow_only})


@app.get("/observability/errors")
def observability_errors(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    log_audit_event("observability_errors_viewed", "observability", resource_name="Backend Errors", status="success", severity="Info", message="Admin viewed observability error events.", user=user)
    return list_error_events()


@app.get("/observability/health-performance")
def observability_health_performance(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    return build_performance_health()


SECURITY_AUDIT_ACTIONS = {
    "weak_password_rejected",
    "failed_login",
    "account_locked",
    "account_unlocked",
    "password_rehashed",
    "session_created",
    "session_revoked",
    "rate_limit_exceeded",
    "sensitive_data_detected",
    "workspace_exported",
    "workspace_delete_requested",
    "secrets_redacted",
    "permission_denied",
    "invalid_token",
}


def _events_in_last_24h(action: str) -> list[dict]:
    cutoff = datetime.now(timezone.utc).timestamp() - 86400
    rows = []
    for event in list_audit_events({"action": action}):
        try:
            if datetime.fromisoformat(event.get("created_at", "")).timestamp() >= cutoff:
                rows.append(event)
        except ValueError:
            continue
    return rows


@app.get("/security/summary")
def security_summary(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    users = list_users(include_private=True)
    locked_accounts = sum(1 for item in users if item.get("locked_until"))
    failed_logins = len(_events_in_last_24h("failed_login"))
    rate_limits = len(_events_in_last_24h("rate_limit_exceeded"))
    sensitive_events = len(_events_in_last_24h("sensitive_data_detected"))
    active_sessions = sum(len(list_user_sessions(item["user_id"])) for item in users)
    if failed_logins > 20:
        risk = "Critical"
    elif locked_accounts > 3:
        risk = "High"
    elif sensitive_events > 5:
        risk = "Medium"
    else:
        risk = "Low"
    recommendations = []
    if failed_logins:
        recommendations.append("Review failed login activity and locked accounts.")
    if sensitive_events:
        recommendations.append("Review sensitive data detections and enable privacy redaction.")
    if rate_limits:
        recommendations.append("Inspect rate limit events for abusive clients or automation.")
    return {
        "total_users": len(users),
        "locked_accounts": locked_accounts,
        "active_sessions": active_sessions,
        "failed_logins_24h": failed_logins,
        "rate_limit_events_24h": rate_limits,
        "sensitive_data_events_24h": sensitive_events,
        "security_risk_level": risk,
        "recommendations": recommendations or ["Security posture is within expected limits."],
    }


@app.get("/security/events")
def security_events(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    return [event for event in list_audit_events() if event.get("action") in SECURITY_AUDIT_ACTIONS]


def _redact_export_if_needed(payload: dict, redact: bool) -> dict:
    return sanitize_metadata(payload) if redact else payload


@app.get("/privacy/settings")
def privacy_settings(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    _require_workspace_scope(user, workspace_id)
    return get_privacy_settings(workspace_id)


@app.put("/privacy/settings")
def privacy_settings_update(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    workspace_id = payload.get("workspace_id", "")
    _require_workspace_scope(user, workspace_id)
    return update_privacy_settings(payload)


@app.get("/privacy/workspace/{workspace_id}/export")
def privacy_workspace_export(workspace_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    _require_workspace_scope(user, workspace_id)
    workspace = get_workspace(workspace_id) or {}
    settings = get_privacy_settings(workspace_id)
    if not settings.get("allow_workspace_export", True):
        raise HTTPException(status_code=403, detail="Workspace export is disabled by privacy settings.")
    payload = {
        "workspace": workspace,
        "privacy_settings": settings,
        "datasets": DatasetRepository.list(workspace_id),
        "evaluations": EvaluationRepository.list(workspace_id),
        "feedback": FeedbackRepository.list(workspace_id),
        "monitoring_rules": MonitoringRuleRepository.list(workspace_id),
        "alerts": AlertRepository.list(workspace_id),
        "audit_events": list_audit_events({"workspace_id": workspace_id}),
        "connectors": ConnectorRepository.list_by_workspace(workspace_id),
        "imported_sources": ImportedSourceRepository.list_by_workspace(workspace_id),
        "rag_search_history": SearchQueryRepository.list_by_workspace(workspace_id),
        "agent_runs": AgentRunRepository.list_by_workspace(workspace_id),
    }
    payload = _redact_export_if_needed(payload, settings.get("redact_exports", True))
    if settings.get("redact_exports", True):
        log_audit_event("secrets_redacted", "privacy", workspace_id, workspace.get("name", ""), "success", "Info", "Secrets redacted during workspace export.", user=user, workspace=workspace)
    log_audit_event("workspace_exported", "privacy", workspace_id, workspace.get("name", ""), "success", "Medium", "Workspace data exported.", user=user, workspace=workspace)
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=driftguard-workspace-{workspace_id[:8]}-export.json"},
    )


@app.post("/privacy/workspace/{workspace_id}/delete-request")
def privacy_workspace_delete_request(workspace_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    _require_workspace_scope(user, workspace_id)
    workspace = get_workspace(workspace_id) or {}
    settings = get_privacy_settings(workspace_id)
    if not settings.get("allow_workspace_delete_request", True):
        raise HTTPException(status_code=403, detail="Workspace delete requests are disabled by privacy settings.")
    request = create_delete_request(workspace_id, user["user_id"])
    log_audit_event("workspace_delete_requested", "privacy", request["delete_request_id"], workspace.get("name", ""), "success", "High", request["message"], user=user, workspace=workspace)
    return request


@app.get("/privacy/delete-requests")
def privacy_delete_requests(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    return list_delete_requests()


@app.post("/privacy/delete-requests/{delete_request_id}/approve")
def privacy_delete_request_approve(delete_request_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    request = approve_delete_request(delete_request_id, user["user_id"])
    if not request:
        raise HTTPException(status_code=404, detail="Delete request not found.")
    log_audit_event("workspace_delete_requested", "privacy", delete_request_id, request.get("workspace_id", ""), "success", "High", request["message"], user=user)
    return request


def _agent_run_or_404(run_id: str) -> dict:
    run = AgentRunRepository.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found.")
    return run


def _agent_run_detail(run_id: str) -> dict:
    run = _agent_run_or_404(run_id)
    return {
        "run": run,
        "steps": AgentStepRepository.list_by_run(run_id),
        "final_report": run.get("final_report", {}),
    }


@app.post("/agent/plan")
def agent_plan(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    goal = str(payload.get("goal", "")).strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal is required.")
    plan = create_agent_plan(goal, workspace_id)
    log_audit_event("agent_plan_created", "agent", workspace_id, "Agent Plan", "success", "Info", "User generated an agent plan.", user=user, workspace=workspace, metadata={"step_count": len(plan)})
    return {"workspace_id": workspace_id, "goal": goal, "plan": plan}


@app.post("/agent/run")
def agent_run(payload: dict, user: dict = Depends(require_auth)):
    check_rate_limit(f"agent-run:{user.get('user_id', '')}", AGENT_RATE_LIMIT_PER_HOUR, 3600, user)
    check_permission(user, "run_evaluation")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    goal = str(payload.get("goal", "")).strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal is required.")
    plan = create_agent_plan(goal, workspace_id)
    run = create_run_with_steps(workspace_id, user.get("user_id", ""), goal, plan)
    log_audit_event("agent_run_started", "agent_run", run["run_id"], goal[:80], "success", "Medium", "User started an agent workflow.", user=user, workspace=workspace, metadata={"step_count": len(plan)})
    try:
        result = execute_agent_run(run["run_id"])
        if payload.get("use_hybrid_reasoning"):
            hybrid = run_hybrid_reasoning(
                workspace_id=workspace_id,
                user_id=user.get("user_id", ""),
                task_type="agent_report",
                input_context={"goal": goal, "step_outputs": {"agent_report": result.get("final_report", {})}},
                reasoning_mode=payload.get("reasoning_mode", "hybrid"),
                provider=payload.get("provider", "local"),
                runtime_api_key=payload.get("runtime_api_key", ""),
            )
            if hybrid.get("final_output"):
                result["final_report"] = {**result.get("final_report", {}), **hybrid["final_output"], "hybrid_trace_id": hybrid.get("trace_id", "")}
                result["run"] = AgentRunRepository.update_final_report(run["run_id"], result["final_report"], result["run"].get("status", "completed")) or result["run"]
        final_status = result["run"].get("status", "completed")
        log_audit_event("agent_run_completed", "agent_run", run["run_id"], goal[:80], "success", "Medium", f"Agent workflow finished with status {final_status}.", user=user, workspace=workspace, metadata={"status": final_status})
        return result
    except ValueError as exc:
        AgentRunRepository.update_status(run["run_id"], "failed", completed=True)
        log_audit_event("agent_run_failed", "agent_run", run["run_id"], goal[:80], "failed", "High", str(exc), user=user, workspace=workspace)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        AgentRunRepository.update_status(run["run_id"], "failed", completed=True)
        log_audit_event("agent_run_failed", "agent_run", run["run_id"], goal[:80], "failed", "Critical", f"Agent workflow failed: {exc}", user=user, workspace=workspace)
        raise HTTPException(status_code=500, detail=f"Agent workflow failed: {exc}") from exc


@app.get("/agent/runs")
def agent_runs(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    return AgentRunRepository.list_by_workspace(workspace_id)


@app.get("/agent/runs/{run_id}")
def agent_run_item(run_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    run = _agent_run_or_404(run_id)
    _require_workspace_scope(user, run.get("workspace_id", ""))
    return _agent_run_detail(run_id)


@app.delete("/agent/runs/{run_id}")
def delete_agent_run(run_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    run = _agent_run_or_404(run_id)
    workspace = _require_workspace_scope(user, run.get("workspace_id", ""))
    if not AgentRunRepository.delete(run_id):
        raise HTTPException(status_code=404, detail="Agent run not found.")
    log_audit_event("agent_run_deleted", "agent_run", run_id, run.get("goal", "")[:80], "success", "High", "User deleted an agent run.", user=user, workspace=workspace)
    return {"status": "ok", "message": "Agent run deleted successfully."}


@app.get("/agent/runs/{run_id}/export-json")
def export_agent_report_json(run_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    run = _agent_run_or_404(run_id)
    workspace = _require_workspace_scope(user, run.get("workspace_id", ""))
    log_audit_event("agent_report_exported", "agent_run", run_id, run.get("goal", "")[:80], "success", "Medium", "User exported an agent report as JSON.", user=user, workspace=workspace, metadata={"format": "json"})
    return Response(
        content=json.dumps(run.get("final_report", {}), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=driftguard-agent-report-{run_id[:8]}.json"},
    )


@app.get("/agent/runs/{run_id}/export-markdown")
def export_agent_report_markdown(run_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    run = _agent_run_or_404(run_id)
    workspace = _require_workspace_scope(user, run.get("workspace_id", ""))
    log_audit_event("agent_report_exported", "agent_run", run_id, run.get("goal", "")[:80], "success", "Medium", "User exported an agent report as Markdown.", user=user, workspace=workspace, metadata={"format": "markdown"})
    return Response(
        content=agent_report_to_markdown(run.get("final_report", {})),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=driftguard-agent-report-{run_id[:8]}.md"},
    )


def _require_ai_settings_access(user: dict):
    if user.get("role") not in {"admin", "engineer"}:
        raise HTTPException(status_code=403, detail="AI settings are available to admin and engineer roles only.")


def _require_trace_access(user: dict):
    if user.get("role") not in {"admin", "engineer", "reviewer"}:
        raise HTTPException(status_code=403, detail="Reasoning traces are available to admin, engineer, and reviewer roles only.")


def _mask_runtime_key(runtime_api_key: str = "") -> str:
    if not runtime_api_key:
        return ""
    return f"{runtime_api_key[:2]}********{runtime_api_key[-2:]}" if len(runtime_api_key) > 4 else "********"


@app.get("/llm/settings")
def llm_settings(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    _require_ai_settings_access(user)
    _require_workspace_scope(user, workspace_id)
    return LLMSettingsRepository.list_by_workspace(workspace_id)


@app.post("/llm/settings")
def save_llm_settings(payload: dict, user: dict = Depends(require_auth)):
    _require_ai_settings_access(user)
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    now = utc_now()
    provider = payload.get("provider", "local")
    existing = LLMSettingsRepository.get_by_workspace_provider(workspace_id, provider)
    settings_payload = {
        "workspace_id": workspace_id,
        "provider": provider,
        "model_name": payload.get("model_name", "local-rule-engine"),
        "reasoning_mode": payload.get("reasoning_mode", "local_only"),
        "api_key_masked": _mask_runtime_key(payload.get("runtime_api_key", "")) or payload.get("api_key_masked", ""),
        "config": payload.get("config", {}),
        "enabled": payload.get("enabled", True),
        "updated_at": now,
    }
    if existing:
        if not settings_payload["api_key_masked"]:
            settings_payload["api_key_masked"] = existing.get("api_key_masked", "")
        settings = LLMSettingsRepository.update(existing["settings_id"], settings_payload)
    else:
        settings = LLMSettingsRepository.create({
            **settings_payload,
            "settings_id": str(uuid4()),
            "created_at": now,
        })
    log_audit_event("llm_settings_updated", "llm_settings", settings["settings_id"], settings["provider"], "success", "Medium", "User saved LLM settings.", user=user, workspace=workspace, metadata={"reasoning_mode": settings["reasoning_mode"]})
    return settings


@app.put("/llm/settings/{settings_id}")
def update_llm_settings(settings_id: str, payload: dict, user: dict = Depends(require_auth)):
    _require_ai_settings_access(user)
    existing = LLMSettingsRepository.get_by_id(settings_id)
    if not existing:
        raise HTTPException(status_code=404, detail="LLM settings not found.")
    workspace = _require_workspace_scope(user, existing.get("workspace_id", ""))
    updates = dict(payload)
    if payload.get("runtime_api_key"):
        updates["api_key_masked"] = _mask_runtime_key(payload.get("runtime_api_key", ""))
    updates.pop("runtime_api_key", None)
    updated = LLMSettingsRepository.update(settings_id, updates)
    log_audit_event("llm_settings_updated", "llm_settings", settings_id, updated.get("provider", ""), "success", "Medium", "User updated LLM settings.", user=user, workspace=workspace)
    return updated


@app.delete("/llm/settings/{settings_id}")
def delete_llm_settings(settings_id: str, user: dict = Depends(require_auth)):
    _require_ai_settings_access(user)
    existing = LLMSettingsRepository.get_by_id(settings_id)
    if not existing:
        raise HTTPException(status_code=404, detail="LLM settings not found.")
    _require_workspace_scope(user, existing.get("workspace_id", ""))
    if not LLMSettingsRepository.delete(settings_id):
        raise HTTPException(status_code=404, detail="LLM settings not found.")
    return {"status": "ok", "message": "LLM settings deleted successfully."}


@app.get("/llm/prompts")
def llm_prompts(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    _require_ai_settings_access(user)
    _require_workspace_scope(user, workspace_id)
    return list_prompt_templates(workspace_id)


@app.post("/llm/prompts")
def create_llm_prompt(payload: dict, user: dict = Depends(require_auth)):
    _require_ai_settings_access(user)
    workspace = _require_workspace_scope(user, payload.get("workspace_id", ""))
    template = create_prompt_template(payload, user.get("user_id", ""))
    log_audit_event("llm_prompt_created", "prompt_template", template["template_id"], template["name"], "success", "Low", "User created a prompt template.", user=user, workspace=workspace, metadata={"task_type": template["task_type"]})
    return template


@app.put("/llm/prompts/{template_id}")
def update_llm_prompt(template_id: str, payload: dict, user: dict = Depends(require_auth)):
    _require_ai_settings_access(user)
    existing = PromptTemplateRepository.get_by_id(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    workspace = _require_workspace_scope(user, existing.get("workspace_id", ""))
    updated = update_prompt_template(template_id, payload)
    log_audit_event("llm_prompt_updated", "prompt_template", template_id, updated.get("name", ""), "success", "Low", "User updated a prompt template.", user=user, workspace=workspace)
    return updated


@app.delete("/llm/prompts/{template_id}")
def delete_llm_prompt(template_id: str, user: dict = Depends(require_auth)):
    _require_ai_settings_access(user)
    existing = PromptTemplateRepository.get_by_id(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    workspace = _require_workspace_scope(user, existing.get("workspace_id", ""))
    if not PromptTemplateRepository.delete(template_id):
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    log_audit_event("llm_prompt_deleted", "prompt_template", template_id, existing.get("name", ""), "success", "Medium", "User deleted a prompt template.", user=user, workspace=workspace)
    return {"status": "ok", "message": "Prompt template deleted successfully."}


LLM_SOURCE_FIELDS = ("documentation", "code", "jira", "commit", "logs", "database_config")


def _llm_input_context(payload: dict) -> dict:
    context = dict(payload.get("input_context") or {})
    for field in LLM_SOURCE_FIELDS:
        if field in payload:
            context[field] = payload.get(field, "")
    return context


@app.post("/llm/reason")
def run_llm_reasoning(payload: dict, user: dict = Depends(require_auth)):
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    task_type = payload.get("task_type", "")
    if user.get("role") == "viewer" and task_type != "rag_answer":
        raise HTTPException(status_code=403, detail="Viewer role can only run read-only RAG answer reasoning.")
    if user.get("role") not in {"admin", "engineer", "reviewer", "viewer"}:
        raise HTTPException(status_code=403, detail="Permission denied for this action.")
    input_context = _llm_input_context(payload)
    if payload.get("provider") == "grok" and not any(str(input_context.get(field, "")).strip() for field in LLM_SOURCE_FIELDS):
        raise HTTPException(status_code=400, detail="Add at least one source field before running Grok reasoning.")
    result = run_hybrid_reasoning(
        workspace_id=workspace_id,
        user_id=user.get("user_id", ""),
        task_type=task_type,
        input_context=input_context,
        reasoning_mode=payload.get("reasoning_mode", "local_only"),
        provider=payload.get("provider", "local"),
        runtime_api_key=payload.get("runtime_api_key", ""),
    )
    log_audit_event("llm_reasoning_run", "reasoning_trace", result["trace_id"], task_type, "success" if result.get("status") != "failed" else "failed", "Medium", "User ran hybrid reasoning.", user=user, workspace=workspace, metadata={"reasoning_mode": result.get("reasoning_mode"), "provider": result.get("provider")})
    return result


@app.get("/llm/traces")
def llm_traces(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    _require_trace_access(user)
    _require_workspace_scope(user, workspace_id)
    return ReasoningTraceRepository.list_by_workspace(workspace_id)


@app.get("/llm/traces/{trace_id}")
def llm_trace_item(trace_id: str, user: dict = Depends(require_auth)):
    _require_trace_access(user)
    trace = ReasoningTraceRepository.get_by_id(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Reasoning trace not found.")
    workspace = _require_workspace_scope(user, trace.get("workspace_id", ""))
    log_audit_event("llm_trace_viewed", "reasoning_trace", trace_id, trace.get("task_type", ""), "success", "Info", "User viewed a reasoning trace.", user=user, workspace=workspace)
    return trace


@app.get("/llm/hybrid-results")
def llm_hybrid_results(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    _require_trace_access(user)
    _require_workspace_scope(user, workspace_id)
    return HybridAnalysisRepository.list_by_workspace(workspace_id)


@app.get("/llm/hybrid-results/{result_id}")
def llm_hybrid_result_item(result_id: str, user: dict = Depends(require_auth)):
    _require_trace_access(user)
    result = HybridAnalysisRepository.get_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Hybrid result not found.")
    _require_workspace_scope(user, result.get("workspace_id", ""))
    return result


@app.put("/llm/hybrid-results/{result_id}/approval")
def update_hybrid_result_approval(result_id: str, payload: dict, user: dict = Depends(require_auth)):
    if user.get("role") not in {"admin", "engineer", "reviewer"}:
        raise HTTPException(status_code=403, detail="Permission denied for this action.")
    existing = HybridAnalysisRepository.get_by_id(result_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Hybrid result not found.")
    workspace = _require_workspace_scope(user, existing.get("workspace_id", ""))
    status = payload.get("approval_status", "pending")
    updated = HybridAnalysisRepository.update_approval(result_id, status, payload.get("approved_by_user", False), payload.get("edited_output", {}))
    audit_action = "hybrid_result_approved" if status == "approved" else "hybrid_result_rejected" if status == "rejected" else "hybrid_result_approved"
    log_audit_event(audit_action, "hybrid_analysis_result", result_id, existing.get("task_type", ""), "success", "Medium", f"Hybrid result marked {status}.", user=user, workspace=workspace)
    return updated


@app.get("/llm/traces/{trace_id}/export-markdown")
def export_llm_trace_markdown(trace_id: str, user: dict = Depends(require_auth)):
    _require_trace_access(user)
    trace = ReasoningTraceRepository.get_by_id(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Reasoning trace not found.")
    _require_workspace_scope(user, trace.get("workspace_id", ""))
    return Response(
        content=reasoning_trace_to_markdown(trace),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=driftguard-reasoning-trace-{trace_id[:8]}.md"},
    )


def _database_type() -> str:
    return "sqlite" if DATABASE_URL.startswith("sqlite") else "external"


def _integrity_report() -> dict:
    workspaces = {workspace["workspace_id"] for workspace in WorkspaceRepository.list()}
    datasets = DatasetRepository.list()
    dataset_ids = {dataset["dataset_id"] for dataset in datasets}
    evaluations = EvaluationRepository.list()
    evaluation_ids = {evaluation["evaluation_id"] for evaluation in evaluations}
    feedback_items = FeedbackRepository.list()
    rules = MonitoringRuleRepository.list()
    alerts = AlertRepository.list()
    users = UserRepository.list(include_private=False)

    orphan_datasets = [item for item in datasets if item.get("workspace_id") and item.get("workspace_id") not in workspaces]
    orphan_evaluations = [item for item in evaluations if item.get("workspace_id") and item.get("workspace_id") not in workspaces]
    orphan_feedback = [item for item in feedback_items if item.get("evaluation_id") and item.get("evaluation_id") not in evaluation_ids]
    orphan_alerts = [item for item in alerts if item.get("related_evaluation_id") and item.get("related_evaluation_id") not in evaluation_ids]
    orphan_rules = [item for item in rules if item.get("dataset_id") and item.get("dataset_id") not in dataset_ids]
    workspace_members = {
        member["user_id"]
        for workspace in WorkspaceRepository.list()
        for member in WorkspaceMemberRepository.list(workspace["workspace_id"])
    }
    users_without_workspace = [user for user in users if user.get("role") != "admin" and user.get("user_id") not in workspace_members]
    emails = [user.get("email", "") for user in users]
    duplicate_emails = sorted({email for email in emails if email and emails.count(email) > 1})
    issues_found = sum(len(items) for items in [orphan_datasets, orphan_evaluations, orphan_feedback, orphan_alerts, orphan_rules, users_without_workspace]) + len(duplicate_emails)
    return {
        "orphan_datasets": orphan_datasets,
        "orphan_evaluations": orphan_evaluations,
        "orphan_feedback": orphan_feedback,
        "orphan_alerts": orphan_alerts,
        "orphan_monitoring_rules": orphan_rules,
        "users_without_workspace": users_without_workspace,
        "datasets_without_workspace": [item for item in datasets if not item.get("workspace_id")],
        "duplicate_emails": duplicate_emails,
        "issues_found": issues_found,
        "status": "clean" if issues_found == 0 else "issues_found",
    }


@app.get("/system/database/health")
def database_health(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    try:
        counts = table_counts()
        return {
            "database_enabled": USE_DATABASE,
            "database_type": _database_type(),
            "database_path": str(STORAGE_DIR / "driftguard.db"),
            "tables": counts,
            "status": "healthy",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {exc}") from exc


@app.post("/system/database/migrate-json")
def migrate_json_endpoint(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    try:
        summary = migrate_json_to_database()
        log_audit_event("migrate_json_to_database", "database", resource_name="SQLite Database", status="success", severity="Medium", message="Admin migrated JSON storage to database.", user=user, metadata=summary)
        return summary
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Migration failed: {exc}") from exc


@app.get("/system/database/backup")
def database_backup(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    payload = export_database_backup()
    log_audit_event("export_database_backup", "database", resource_name="SQLite Database", status="success", severity="Medium", message="Admin exported database backup.", user=user)
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-database-backup.json"},
    )


@app.post("/system/database/restore")
async def database_restore(file: UploadFile = File(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    try:
        payload = json.loads((await _read_upload_limited(file)).decode("utf-8-sig"))
        summary = import_database_backup(payload)
        log_audit_event("restore_database_backup", "database", resource_name="SQLite Database", status="success", severity="High", message="Admin restored database backup.", user=user, metadata=summary)
        return summary
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Restore failed: {exc}") from exc


@app.get("/system/database/integrity")
def database_integrity(user: dict = Depends(require_auth)):
    check_permission(user, "manage_users")
    return _integrity_report()


async def _parse_uploaded_dataset(file: UploadFile) -> list[DatasetCase]:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in {".json", ".jsonl"}:
        raise HTTPException(status_code=400, detail="Only JSON or SNLI JSONL dataset files are supported.")

    try:
        raw_content = await _read_upload_limited(file)
        decoded_content = raw_content.decode("utf-8-sig")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid dataset format. Please upload a JSON array of dataset cases.") from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Uploaded dataset must be valid UTF-8 JSON or JSONL.") from exc

    if suffix == ".jsonl":
        return _parse_snli_jsonl_dataset(decoded_content)

    try:
        parsed_json = json.loads(decoded_content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid dataset format. Please upload a JSON array of dataset cases.") from exc

    if not isinstance(parsed_json, list):
        raise HTTPException(status_code=400, detail="Dataset JSON must be a list of dataset cases.")
    if not parsed_json:
        raise HTTPException(status_code=400, detail="Dataset JSON must include at least one dataset case.")

    try:
        return [DatasetCase(**case) for case in parsed_json]
    except (TypeError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=INVALID_DATASET_MESSAGE) from exc


def _parse_snli_jsonl_dataset(content: str) -> list[DatasetCase]:
    cases: list[DatasetCase] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Uploaded dataset is not valid JSONL. Line {line_number} is invalid JSON.") from exc
        if not isinstance(record, dict):
            raise HTTPException(status_code=400, detail=f"Uploaded dataset is not valid JSONL. Line {line_number} must be a JSON object.")

        gold_label = str(record.get("gold_label", "")).strip().lower()
        if not gold_label or gold_label == "-":
            continue
        expected_label = SNLI_LABEL_MAP.get(gold_label)
        if expected_label is None:
            continue

        sentence1 = str(record.get("sentence1", "")).strip()
        sentence2 = str(record.get("sentence2", "")).strip()
        if not sentence1 or not sentence2:
            continue

        cases.append(DatasetCase(
            case_id=f"SNLI-{len(cases) + 1:03d}",
            title="SNLI natural language inference case",
            documentation=sentence1,
            code=sentence2,
            jira=sentence2,
            commit="",
            logs="",
            database_config="",
            expected_label=expected_label,
            expected_drift_type="No Drift" if expected_label == "no_drift" else "Logical Contradiction",
            expected_severity="None" if expected_label == "no_drift" else "Low",
        ))
        if len(cases) >= SNLI_JSONL_PREVIEW_LIMIT:
            break

    if not cases:
        raise HTTPException(status_code=400, detail="SNLI JSONL must include at least one valid record with sentence1, sentence2, and gold_label.")
    return cases


CONNECTOR_TYPES = {"github", "jira", "confluence", "logs", "config", "manual_upload"}
UPLOAD_CONNECTOR_TYPES = {"jira", "confluence", "logs", "config", "manual_upload"}
CONNECTOR_STATUSES = {"active", "disabled", "error"}


def _connector_or_404(connector_id: str, include_private_config: bool = False) -> dict:
    connector = get_connector(connector_id, mask_config=not include_private_config)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")
    return connector


def _source_or_404(source_id: str) -> dict:
    source = get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Imported source not found.")
    return source


def _require_connector_workspace(connector: dict, user: dict):
    _require_workspace_scope(user, connector.get("workspace_id", ""))
    return get_workspace(connector.get("workspace_id", ""))


def _can_delete_connector(user: dict, connector: dict) -> bool:
    return user.get("role") == "admin" or connector.get("created_by") == user.get("user_id")


def _connector_from_config(connector: dict):
    if connector.get("connector_type") == "github":
        return GitHubConnector(connector.get("config", {}))
    if connector.get("connector_type") in UPLOAD_CONNECTOR_TYPES:
        return FileConnector({"connector_type": connector.get("connector_type"), "files": []})
    raise ValueError("Unsupported connector type.")


def _save_normalized_sources(connector: dict, normalized_sources: list[dict]) -> list[dict]:
    saved = []
    now = utc_now()
    for item in normalized_sources:
        source = {
            "source_id": str(uuid4()),
            "workspace_id": connector.get("workspace_id", ""),
            "connector_id": connector.get("connector_id", ""),
            "created_at": now,
            "updated_at": now,
            **item,
        }
        saved.append(create_source(source))
    return saved


def _try_index_sources(sources: list[dict]) -> dict:
    if not sources:
        return {"sources_indexed": 0, "chunks_created": 0, "status": "skipped"}
    try:
        return index_imported_sources(sources)
    except Exception as exc:
        return {"sources_indexed": 0, "chunks_created": 0, "status": "warning", "warning": str(exc)}


def _record_sync(connector: dict, result: dict, status: str = "completed") -> dict:
    now = utc_now()
    sync_run = save_sync_run({
        "sync_id": str(uuid4()),
        "workspace_id": connector.get("workspace_id", ""),
        "connector_id": connector.get("connector_id", ""),
        "connector_type": connector.get("connector_type", ""),
        "status": status,
        "started_at": result.get("started_at", now),
        "completed_at": now,
        "files_imported": result.get("files_imported", 0),
        "files_skipped": result.get("files_skipped", 0),
        "errors": result.get("errors", []),
        "summary": result.get("summary", ""),
    })
    update_connector(connector["connector_id"], {"last_sync_at": now, "status": "active" if status in {"completed", "partial"} else "error"})
    return sync_run


def _save_generated_dataset(workspace_id: str, sources: list[dict], payload: dict, user: dict) -> dict:
    cases = build_dataset_cases_from_sources(sources)
    if not cases:
        raise HTTPException(status_code=400, detail="No dataset cases could be generated from the selected sources.")
    saved = save_dataset(
        cases,
        "generated-from-connectors.json",
        payload.get("dataset_name") or "Generated Dataset from Imported Sources",
        payload.get("description", "Auto-generated dataset from imported enterprise sources."),
        payload.get("version", "1.0"),
        workspace_id,
    )
    source_ids = [source["source_id"] for source in sources if source.get("source_id")]
    for case in cases:
        create_generated_case({
            "generated_case_id": str(uuid4()),
            "workspace_id": workspace_id,
            "source_ids": source_ids,
            "case": case.model_dump(),
            "created_at": utc_now(),
            "created_by": user.get("user_id", ""),
        })
    return {"dataset": saved, "cases": [case.model_dump() for case in cases]}


@app.post("/connectors")
def create_connector_endpoint(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_connectors")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    connector_type = payload.get("connector_type", "")
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported connector_type.")
    now = utc_now()
    connector = create_connector({
        "connector_id": str(uuid4()),
        "workspace_id": workspace_id,
        "name": payload.get("name", "").strip() or "Untitled Connector",
        "connector_type": connector_type,
        "status": payload.get("status", "active") if payload.get("status", "active") in CONNECTOR_STATUSES else "active",
        "config": payload.get("config", {}),
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
        "last_sync_at": "",
    })
    log_audit_event("create_connector", "connector", connector["connector_id"], connector["name"], "success", "Low", "User created connector.", user=user, workspace=workspace, metadata={"connector_type": connector_type})
    return connector


@app.get("/connectors")
def connectors(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_connectors")
    _require_workspace_scope(user, workspace_id)
    return list_connectors(workspace_id)


@app.get("/connectors/{connector_id}")
def connector_item(connector_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_connectors")
    connector = _connector_or_404(connector_id)
    _require_connector_workspace(connector, user)
    return connector


@app.put("/connectors/{connector_id}")
def update_connector_endpoint(connector_id: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_connectors")
    existing = _connector_or_404(connector_id, include_private_config=True)
    workspace = _require_connector_workspace(existing, user)
    updates = {key: payload[key] for key in ["name", "status", "connector_type"] if key in payload}
    if "connector_type" in updates and updates["connector_type"] not in CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported connector_type.")
    if "status" in updates and updates["status"] not in CONNECTOR_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported connector status.")
    if "config" in payload:
        updates["config"] = {**existing.get("config", {}), **payload.get("config", {})}
    updated = update_connector(connector_id, updates)
    log_audit_event("update_connector", "connector", connector_id, updated.get("name", ""), "success", "Low", "User updated connector.", user=user, workspace=workspace)
    return updated


@app.delete("/connectors/{connector_id}")
def delete_connector_endpoint(connector_id: str, user: dict = Depends(require_auth)):
    existing = _connector_or_404(connector_id)
    workspace = _require_connector_workspace(existing, user)
    if not _can_delete_connector(user, existing):
        check_permission(user, "delete_connectors", workspace)
    if not delete_connector(connector_id):
        raise HTTPException(status_code=404, detail="Connector not found.")
    log_audit_event("delete_connector", "connector", connector_id, existing.get("name", ""), "success", "High", "User deleted connector.", user=user, workspace=workspace)
    return {"status": "ok", "message": "Connector deleted successfully."}


@app.post("/connectors/{connector_id}/test")
def test_connector_endpoint(connector_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "sync_connectors")
    connector = _connector_or_404(connector_id, include_private_config=True)
    workspace = _require_connector_workspace(connector, user)
    try:
        result = _connector_from_config(connector).test_connection()
        log_audit_event("test_connector", "connector", connector_id, connector.get("name", ""), "success", "Low", "User tested connector.", user=user, workspace=workspace)
        return result
    except ValueError as exc:
        update_connector(connector_id, {"status": "error"})
        log_audit_event("test_connector", "connector", connector_id, connector.get("name", ""), "failed", "Medium", str(exc), user=user, workspace=workspace)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/connectors/{connector_id}/sync")
def sync_connector_endpoint(connector_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "sync_connectors")
    connector = _connector_or_404(connector_id, include_private_config=True)
    workspace = _require_connector_workspace(connector, user)
    try:
        result = _connector_from_config(connector).sync()
        saved_sources = _save_normalized_sources(connector, result.get("sources", []))
        index_summary = _try_index_sources(saved_sources)
        sync_run = _record_sync(connector, result, "completed" if not result.get("errors") else "partial")
        log_audit_event("sync_connector", "connector", connector_id, connector.get("name", ""), "success", "Medium", "User synced connector.", user=user, workspace=workspace, metadata={"files_imported": len(saved_sources), "index": index_summary})
        return {"connector": get_connector(connector_id), "sync_run": sync_run, "imported_sources": saved_sources, "index": index_summary}
    except ValueError as exc:
        failed_result = {"files_imported": 0, "files_skipped": 0, "errors": [{"error": str(exc)}], "summary": str(exc)}
        sync_run = _record_sync(connector, failed_result, "failed")
        log_audit_event("sync_connector", "connector", connector_id, connector.get("name", ""), "failed", "High", str(exc), user=user, workspace=workspace)
        raise HTTPException(status_code=400, detail={"message": str(exc), "sync_run": sync_run}) from exc


@app.post("/connectors/upload-sources")
async def upload_connector_sources(
    workspace_id: str = Form(...),
    connector_type: str = Form(...),
    name: str = Form(...),
    files: list[UploadFile] = File(...),
    user: dict = Depends(require_auth),
):
    check_rate_limit(f"upload:{user.get('user_id', '')}", UPLOAD_RATE_LIMIT_PER_HOUR, 3600, user)
    check_permission(user, "sync_connectors")
    workspace = _require_workspace_scope(user, workspace_id)
    if connector_type not in UPLOAD_CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported upload connector_type.")
    uploaded_files = [{"filename": file.filename or "uploaded-source.txt", "content": await _read_upload_limited(file)} for file in files]
    now = utc_now()
    connector = create_connector({
        "connector_id": str(uuid4()),
        "workspace_id": workspace_id,
        "name": name.strip() or "Uploaded Sources",
        "connector_type": connector_type,
        "status": "active",
        "config": {"file_count": len(uploaded_files)},
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
        "last_sync_at": "",
    })
    result = FileConnector({"connector_type": connector_type, "files": uploaded_files}).sync()
    saved_sources = _save_normalized_sources(connector, result.get("sources", []))
    index_summary = _try_index_sources(saved_sources)
    sync_run = _record_sync(connector, result, "completed" if not result.get("errors") else "partial")
    log_audit_event("upload_sources", "connector", connector["connector_id"], connector["name"], "success", "Medium", "User uploaded and imported source files.", user=user, workspace=workspace, metadata={"files_imported": len(saved_sources), "connector_type": connector_type, "index": index_summary})
    return {"connector": get_connector(connector["connector_id"]), "sync_run": sync_run, "imported_sources": saved_sources, "index": index_summary}


@app.get("/sources")
def imported_sources(
    workspace_id: str = Query(...),
    connector_id: str = Query(""),
    source_type: str = Query(""),
    search: str = Query(""),
    user: dict = Depends(require_auth),
):
    check_permission(user, "view_connectors")
    _require_workspace_scope(user, workspace_id)
    items = list_sources(workspace_id, connector_id, source_type, search)
    return sanitize_metadata(items) if get_privacy_settings(workspace_id).get("privacy_mode_enabled", True) else items


@app.post("/sources/generate-dataset")
def generate_dataset_from_sources(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "generate_connector_datasets")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    source_ids = payload.get("source_ids", [])
    sources = [_source_or_404(source_id) for source_id in source_ids]
    for source in sources:
        _assert_item_workspace(source, workspace_id)
    result = _save_generated_dataset(workspace_id, sources, payload, user)
    log_audit_event("generate_dataset_from_sources", "dataset", result["dataset"]["dataset_id"], result["dataset"]["name"], "success", "Medium", "User generated dataset from imported sources.", user=user, workspace=workspace, metadata={"source_count": len(sources), "case_count": len(result["cases"])})
    return result


@app.post("/sources/generate-dataset-from-connector/{connector_id}")
def generate_dataset_from_connector(connector_id: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "generate_connector_datasets")
    connector = _connector_or_404(connector_id)
    workspace = _require_connector_workspace(connector, user)
    sources = list_sources_by_connector(connector_id)
    result = _save_generated_dataset(connector.get("workspace_id", ""), sources, payload, user)
    log_audit_event("generate_dataset_from_sources", "connector", connector_id, connector.get("name", ""), "success", "Medium", "User generated dataset from connector sources.", user=user, workspace=workspace, metadata={"source_count": len(sources), "case_count": len(result["cases"])})
    return result


@app.get("/sources/{source_id}")
def imported_source_item(source_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_connectors")
    source = _source_or_404(source_id)
    workspace = _require_workspace_scope(user, source.get("workspace_id", ""))
    log_audit_event("view_source", "imported_source", source_id, source.get("source_name", ""), "success", "Info", "User viewed imported source.", user=user, workspace=workspace)
    return sanitize_metadata(source) if get_privacy_settings(source.get("workspace_id", "")).get("privacy_mode_enabled", True) else source


@app.delete("/sources/{source_id}")
def delete_source_endpoint(source_id: str, user: dict = Depends(require_auth)):
    source = _source_or_404(source_id)
    workspace = _require_workspace_scope(user, source.get("workspace_id", ""))
    connector = get_connector(source.get("connector_id", ""))
    if not (user.get("role") == "admin" or (connector and connector.get("created_by") == user.get("user_id"))):
        check_permission(user, "delete_connectors", workspace)
    from database.repositories import SourceChunkRepository

    SourceChunkRepository.delete_by_source(source_id)
    if not delete_source(source_id):
        raise HTTPException(status_code=404, detail="Imported source not found.")
    log_audit_event("delete_source", "imported_source", source_id, source.get("source_name", ""), "success", "High", "User deleted imported source.", user=user, workspace=workspace)
    return {"status": "ok", "message": "Imported source deleted successfully."}


@app.get("/connectors/{connector_id}/sync-runs")
def connector_sync_runs(connector_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_connectors")
    connector = _connector_or_404(connector_id)
    _require_connector_workspace(connector, user)
    return list_sync_runs(connector_id)


@app.post("/rag/index")
def rag_index(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "sync_connectors")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    summary = index_sources_for_workspace(workspace_id)
    log_audit_event("rag_index_workspace", "rag", workspace_id, "Search Index", "success", "Medium", "User rebuilt RAG search index.", user=user, workspace=workspace, metadata=summary)
    return summary


@app.post("/rag/search")
def rag_search(payload: dict, user: dict = Depends(require_auth)):
    check_rate_limit(f"rag-search:{user.get('user_id', '')}", RAG_RATE_LIMIT_PER_MINUTE, 60, user)
    check_permission(user, "view_connectors")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    query = str(payload.get("query", "")).strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required.")
    detection = detect_sensitive_data(query)
    if detection["has_sensitive_data"]:
        log_audit_event("sensitive_data_detected", "rag", workspace_id, "RAG Query", "warning", "Medium", "Sensitive data detected in a RAG query.", user=user, workspace=workspace, metadata=detection)
    answer = search_workspace_sources(
        workspace_id,
        query,
        payload.get("source_types") or [],
        int(payload.get("top_k", 8) or 8),
        user.get("user_id", ""),
    )
    if get_privacy_settings(workspace_id).get("privacy_mode_enabled", True):
        answer = sanitize_metadata(answer)
    log_audit_event("rag_search", "rag", answer.get("query_id", ""), query[:80], "success", "Info", "User searched imported sources.", user=user, workspace=workspace, metadata={"possible_drift": answer.get("possible_drift"), "confidence_score": answer.get("confidence_score")})
    return answer


@app.get("/rag/chunks")
def rag_chunks(workspace_id: str = Query(...), source_type: str = Query(""), source_id: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "sync_connectors")
    workspace = _require_workspace_scope(user, workspace_id)
    from database.repositories import SourceChunkRepository

    chunks = SourceChunkRepository.list_by_workspace(workspace_id, source_type, source_id)
    log_audit_event("rag_view_chunks", "rag", workspace_id, "Indexed Chunks", "success", "Info", "User viewed indexed chunks.", user=user, workspace=workspace, metadata={"chunk_count": len(chunks)})
    return chunks


@app.get("/rag/search-history")
def rag_search_history(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_connectors")
    workspace = _require_workspace_scope(user, workspace_id)
    from database.repositories import SearchQueryRepository

    history = SearchQueryRepository.list_queries(workspace_id)
    log_audit_event("rag_view_search_history", "rag", workspace_id, "Search History", "success", "Info", "User viewed RAG search history.", user=user, workspace=workspace)
    return history


@app.get("/rag/search-history/{query_id}")
def rag_search_history_item(query_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_connectors")
    from database.repositories import SearchQueryRepository

    item = SearchQueryRepository.get_by_id(query_id)
    if not item:
        raise HTTPException(status_code=404, detail="Search query not found.")
    _require_workspace_scope(user, item.get("workspace_id", ""))
    return item


@app.get("/rag/search-history/{query_id}/export-markdown")
def rag_export_search_markdown(query_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    from database.repositories import SearchQueryRepository

    item = SearchQueryRepository.get_by_id(query_id)
    if not item:
        raise HTTPException(status_code=404, detail="Search query not found.")
    workspace = _require_workspace_scope(user, item.get("workspace_id", ""))
    log_audit_event("rag_export_search_answer", "rag", query_id, item.get("query_text", "")[:80], "success", "Medium", "User exported RAG search answer.", user=user, workspace=workspace)
    return Response(
        content=export_answer_markdown(item),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=driftguard-search-answer.md"},
    )


@app.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest, user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    raw_text = " ".join([request.documentation, request.code, request.jira, request.commit, request.logs, request.database_config])
    detection = detect_sensitive_data(raw_text)
    if detection["has_sensitive_data"]:
        log_audit_event("sensitive_data_detected", "analysis", resource_name="Manual Analysis", status="warning", severity="Medium", message="Sensitive data detected in manual analysis input.", user=user, metadata=detection)
    entity = extract_entity(
        [
            request.documentation,
            request.code,
            request.jira,
            request.commit,
            request.logs,
            request.database_config,
        ]
    )
    claims = extract_claims(request, entity)
    truth_triangle = build_truth_triangle(claims)
    drift_report = detect_drift(truth_triangle, entity)
    save_report(drift_report)
    return AnalysisResponse(claims=claims, truth_triangle=truth_triangle, drift_report=drift_report)


@app.get("/reports", response_model=list[HistoryReport])
def reports(user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    return get_reports()


@app.get("/reports/{report_id}", response_model=HistoryReport)
def report_by_id(report_id: int, user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    report = get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/dataset/sample", response_model=list[DatasetCase])
def sample_dataset(user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    try:
        return load_sample_dataset()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/dataset/evaluate", response_model=DatasetEvaluationResponse)
def dataset_evaluation(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    global LATEST_EVALUATION_RESULT
    check_permission(user, "run_evaluation")
    _require_workspace_scope(user, workspace_id)
    try:
        LATEST_EVALUATION_RESULT = evaluate_dataset()
        save_evaluation_result(LATEST_EVALUATION_RESULT, "sample", "Built-in Sample Dataset", workspace_id)
        log_audit_event("run_evaluation", "dataset", "sample", "Built-in Sample Dataset", "success", "Low", "User ran sample dataset evaluation.", user=user, workspace=get_workspace(workspace_id), metadata={"accuracy": LATEST_EVALUATION_RESULT.accuracy, "total_cases": LATEST_EVALUATION_RESULT.total_cases})
        return LATEST_EVALUATION_RESULT
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/dataset/upload-preview", response_model=list[DatasetCase])
async def upload_dataset_preview(file: UploadFile = File(...), user: dict = Depends(require_auth)):
    check_rate_limit(f"upload:{user.get('user_id', '')}", UPLOAD_RATE_LIMIT_PER_HOUR, 3600, user)
    check_permission(user, "view_dashboard")
    cases = await _parse_uploaded_dataset(file)
    log_audit_event("preview_uploaded_dataset", "dataset", resource_name=file.filename or "Uploaded Dataset", status="success", severity="Info", message="User previewed an uploaded dataset.", user=user, metadata={"total_cases": len(cases)})
    return cases


@app.post("/dataset/upload-evaluate", response_model=DatasetEvaluationResponse)
async def upload_dataset_evaluation(
    file: UploadFile = File(...),
    workspace_id: str = Form(...),
    user: dict = Depends(require_auth),
):
    global LATEST_EVALUATION_RESULT
    check_rate_limit(f"upload:{user.get('user_id', '')}", UPLOAD_RATE_LIMIT_PER_HOUR, 3600, user)
    check_permission(user, "run_evaluation")
    _require_workspace_scope(user, workspace_id)
    uploaded_cases = await _parse_uploaded_dataset(file)
    LATEST_EVALUATION_RESULT = evaluate_dataset_cases(uploaded_cases)
    save_evaluation_result(LATEST_EVALUATION_RESULT, "uploaded_temp", file.filename or "Uploaded Dataset", workspace_id)
    log_audit_event("run_evaluation", "dataset", "uploaded_temp", file.filename or "Uploaded Dataset", "success", "Low", "User evaluated an uploaded dataset.", user=user, workspace=get_workspace(workspace_id), metadata={"accuracy": LATEST_EVALUATION_RESULT.accuracy, "total_cases": LATEST_EVALUATION_RESULT.total_cases})
    return LATEST_EVALUATION_RESULT


@app.post("/dataset/save-uploaded")
async def save_uploaded_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    version: str = Form("1.0"),
    workspace_id: str = Form(...),
    user: dict = Depends(require_auth),
):
    check_rate_limit(f"upload:{user.get('user_id', '')}", UPLOAD_RATE_LIMIT_PER_HOUR, 3600, user)
    check_permission(user, "save_dataset")
    _require_workspace_scope(user, workspace_id)
    if not name.strip():
        raise HTTPException(status_code=400, detail="Please enter a dataset name before saving.")
    cases = await _parse_uploaded_dataset(file)
    saved = save_dataset(cases, file.filename or "uploaded.json", name.strip(), description, version, workspace_id)
    log_audit_event("save_dataset", "dataset", saved["dataset_id"], saved["name"], "success", "Low", f"User saved dataset {saved['name']}.", user=user, workspace=get_workspace(workspace_id), metadata={"total_cases": saved["total_cases"]})
    return saved


@app.get("/dataset/library")
def dataset_library(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    return list_datasets(workspace_id)


@app.get("/dataset/library/{dataset_id}")
def dataset_library_item(dataset_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    _assert_item_workspace(dataset.get("metadata", {}), workspace_id)
    metadata = dataset.get("metadata", {})
    log_audit_event("view_dataset", "dataset", dataset_id, metadata.get("name", ""), "success", "Info", "User viewed a saved dataset.", user=user, workspace=get_workspace(workspace_id))
    return dataset


@app.delete("/dataset/library/{dataset_id}")
def delete_dataset_item(dataset_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "delete_dataset")
    _require_workspace_scope(user, workspace_id)
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    _assert_item_workspace(dataset.get("metadata", {}), workspace_id)
    if not delete_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found.")
    metadata = dataset.get("metadata", {})
    log_audit_event("delete_dataset", "dataset", dataset_id, metadata.get("name", ""), "success", "High", "User deleted a saved dataset.", user=user, workspace=get_workspace(workspace_id))
    return {"status": "ok", "message": "Dataset deleted successfully."}


ADAPTERS = {
    "cosqa": CosQAAdapter,
    "snli": SNLIAdapter,
    "commitpack": CommitPackAdapter,
    "spider": SpiderAdapter,
    "custom": CustomAdapter,
}
TRAINING_EXPORT_DIR = STORAGE_DIR / "exports" / "training"


def _adapter_for(dataset_type: str):
    adapter_cls = ADAPTERS.get((dataset_type or "").lower())
    if not adapter_cls:
        raise HTTPException(status_code=400, detail="Unsupported benchmark dataset_type.")
    return adapter_cls()


def _validate_benchmark_upload(file: UploadFile, dataset_type: str):
    filename = file.filename or "benchmark.json"
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Unsafe filename.")
    supported = get_supported_benchmark_datasets().get(dataset_type, {}).get("expected_formats", [])
    suffix = Path(filename).suffix.lower()
    if suffix not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension for {dataset_type}.")


def _benchmark_or_404(benchmark_id: str, user: dict) -> dict:
    benchmark = BenchmarkDatasetRepository.get_by_id(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark dataset not found.")
    _require_workspace_scope(user, benchmark.get("workspace_id", ""))
    return benchmark


def _redact_examples_if_needed(workspace_id: str, payload):
    settings = get_privacy_settings(workspace_id)
    if settings.get("privacy_mode_enabled", True) and settings.get("redact_exports", True):
        return sanitize_metadata(payload)
    return payload


def _benchmark_examples_for_ids(workspace_id: str, benchmark_ids: list[str], include_types: list[str] | None = None, max_examples: int = 1000) -> list[dict]:
    items = []
    include_types = set(include_types or [])
    for benchmark_id in benchmark_ids:
        benchmark = BenchmarkDatasetRepository.get_by_id(benchmark_id)
        if not benchmark or benchmark.get("workspace_id") != workspace_id:
            continue
        if include_types and benchmark.get("dataset_type") not in include_types:
            continue
        items.extend(BenchmarkExampleRepository.list(benchmark_id=benchmark_id, limit=max_examples))
        if len(items) >= max_examples:
            break
    return items[:max_examples]


def _human_corrected_training_examples(workspace_id: str, max_examples: int = 1000) -> list[dict]:
    items = []
    for feedback in FeedbackRepository.list(workspace_id):
        if feedback.get("review_status") and feedback.get("review_status") != "reviewed":
            continue
        items.append({
            "example_id": f"human-{feedback.get('feedback_id')}",
            "workspace_id": workspace_id,
            "benchmark_id": "human_corrected",
            "dataset_type": "driftguard_corrected",
            "original_id": feedback.get("case_id", ""),
            "input": {
                "documentation": "",
                "code": "",
                "jira": "",
                "commit": "",
                "logs": "",
                "database_config": "",
                "question": "",
                "context": feedback.get("reviewer_notes", ""),
            },
            "target": {
                "label": feedback.get("corrected_label", "uncertain"),
                "drift_type": feedback.get("corrected_drift_type", ""),
                "severity": feedback.get("corrected_severity", ""),
                "explanation": feedback.get("reviewer_notes") or feedback.get("correction_reason", ""),
            },
            "driftguard_case": {
                "case_id": feedback.get("case_id", ""),
                "title": "Human-corrected DriftGuard case",
                "documentation": "",
                "code": "",
                "jira": "",
                "commit": "",
                "logs": "",
                "database_config": "",
                "expected_label": feedback.get("corrected_label", "uncertain"),
                "expected_drift_type": feedback.get("corrected_drift_type", ""),
                "expected_severity": feedback.get("corrected_severity", ""),
            },
            "split": "unsplit",
            "quality_score": 75,
            "metadata": {"source_dataset": "driftguard_corrected", "feedback_id": feedback.get("feedback_id", ""), "task_type": "human_correction"},
            "created_at": feedback.get("created_at", ""),
        })
        if len(items) >= max_examples:
            break
    return items


def _merge_training_examples(payload: dict) -> tuple[list[dict], dict]:
    workspace_id = payload.get("workspace_id", "")
    max_examples = max(1, min(int(payload.get("max_examples", 1000)), 10000))
    examples = _benchmark_examples_for_ids(
        workspace_id,
        payload.get("benchmark_ids", []),
        payload.get("include_dataset_types", []),
        max_examples,
    )
    if payload.get("include_human_corrected", False) and len(examples) < max_examples:
        examples.extend(_human_corrected_training_examples(workspace_id, max_examples - len(examples)))
    examples = examples[:max_examples]
    quality = analyze_benchmark_quality(examples)
    return examples, {"total_examples": len(examples), **quality}


@app.get("/benchmarks/registry")
def benchmark_registry(user: dict = Depends(require_auth)):
    check_permission(user, "view_benchmarks")
    return get_supported_benchmark_datasets()


@app.post("/benchmarks/upload")
async def upload_benchmark_dataset(
    workspace_id: str = Form(...),
    dataset_type: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
):
    check_rate_limit(f"upload:{user.get('user_id', '')}", UPLOAD_RATE_LIMIT_PER_HOUR, 3600, user)
    check_permission(user, "manage_benchmarks")
    workspace = _require_workspace_scope(user, workspace_id)
    dataset_type = dataset_type.lower().strip()
    _validate_benchmark_upload(file, dataset_type)
    adapter = _adapter_for(dataset_type)
    content = await _read_upload_limited(file)
    now = utc_now()
    benchmark_id = str(uuid4())
    import_id = str(uuid4())
    errors = []
    imported = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / Path(file.filename or "benchmark.json").name
        temp_path.write_bytes(content)
        raw_examples = adapter.load_examples(temp_path)
    for index, raw in enumerate(raw_examples, start=1):
        valid, reason = adapter.validate_example(raw)
        if not valid:
            errors.append({"index": index, "reason": reason})
            continue
        case = adapter.convert_to_driftguard_case(raw, index)
        record = adapter.convert_to_training_record(raw, index)
        example = {
            "example_id": str(uuid4()),
            "workspace_id": workspace_id,
            "benchmark_id": benchmark_id,
            "dataset_type": dataset_type,
            "original_id": record.get("metadata", {}).get("original_id", "") or case.get("case_id", ""),
            "input": record.get("input", {}),
            "target": record.get("target", {}),
            "driftguard_case": case,
            "split": "unsplit",
            "metadata": record.get("metadata", {}),
            "created_at": now,
        }
        example["quality_score"] = score_example(example)
        imported.append(example)
    status = "imported" if imported and not errors else "partial" if imported else "failed"
    benchmark = BenchmarkDatasetRepository.create({
        "benchmark_id": benchmark_id,
        "workspace_id": workspace_id,
        "name": name.strip() or file.filename or "Benchmark Dataset",
        "dataset_type": dataset_type,
        "description": description,
        "source_name": file.filename or "",
        "source_url": "",
        "status": status,
        "total_examples": len(raw_examples),
        "imported_examples": len(imported),
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
    })
    BenchmarkExampleRepository.bulk_create(imported)
    import_run = BenchmarkImportRunRepository.create({
        "import_id": import_id,
        "workspace_id": workspace_id,
        "benchmark_id": benchmark_id,
        "dataset_type": dataset_type,
        "status": status,
        "started_at": now,
        "completed_at": utc_now(),
        "examples_processed": len(raw_examples),
        "examples_imported": len(imported),
        "examples_skipped": len(errors),
        "errors": errors[:50],
        "summary": f"Imported {len(imported)} of {len(raw_examples)} benchmark examples.",
    })
    log_audit_event("benchmark_dataset_uploaded", "benchmark_dataset", benchmark_id, benchmark["name"], "success", "Medium", "User uploaded a benchmark dataset.", user=user, workspace=workspace, metadata={"dataset_type": dataset_type, "examples": len(raw_examples)})
    log_audit_event("benchmark_dataset_imported", "benchmark_dataset", benchmark_id, benchmark["name"], status, "Medium", import_run["summary"], user=user, workspace=workspace, metadata={"import_id": import_id, "skipped": len(errors)})
    return {"benchmark": benchmark, "import_run": import_run, "preview": _redact_examples_if_needed(workspace_id, imported[:10])}


@app.get("/benchmarks")
def benchmark_datasets(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_benchmarks")
    _require_workspace_scope(user, workspace_id)
    return BenchmarkDatasetRepository.list(workspace_id)


@app.get("/benchmarks/{benchmark_id}")
def benchmark_dataset_item(benchmark_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_benchmarks")
    benchmark = _benchmark_or_404(benchmark_id, user)
    runs = BenchmarkImportRunRepository.list_by_benchmark(benchmark_id)
    return {"benchmark": benchmark, "import_runs": runs}


@app.get("/benchmarks/{benchmark_id}/examples")
def benchmark_examples(benchmark_id: str, split: str = Query(""), label: str = Query(""), limit: int = Query(100), offset: int = Query(0), user: dict = Depends(require_auth)):
    check_permission(user, "view_benchmarks")
    benchmark = _benchmark_or_404(benchmark_id, user)
    items = BenchmarkExampleRepository.list(benchmark_id=benchmark_id, split=split, label=label, limit=limit, offset=offset)
    return _redact_examples_if_needed(benchmark["workspace_id"], items)


@app.post("/benchmarks/{benchmark_id}/create-driftguard-dataset")
def create_driftguard_dataset_from_benchmark(benchmark_id: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_benchmarks")
    benchmark = _benchmark_or_404(benchmark_id, user)
    sample_size = int(payload.get("sample_size", 0) or 0)
    examples = BenchmarkExampleRepository.list(benchmark_id=benchmark_id, limit=10000)
    if sample_size > 0:
        examples = examples[:sample_size]
    cases = [DatasetCase(**example["driftguard_case"]) for example in examples]
    if not cases:
        raise HTTPException(status_code=400, detail="Benchmark has no importable examples.")
    saved = save_dataset(
        cases,
        f"{benchmark.get('dataset_type')}-converted.json",
        payload.get("dataset_name", benchmark.get("name", "Converted Benchmark")),
        payload.get("description", ""),
        payload.get("version", "1.0"),
        benchmark.get("workspace_id", ""),
    )
    log_audit_event("save_dataset", "dataset", saved["dataset_id"], saved["name"], "success", "Medium", "Benchmark converted to DriftGuard dataset.", user=user, workspace=get_workspace(benchmark["workspace_id"]), metadata={"benchmark_id": benchmark_id})
    return saved


@app.post("/benchmarks/{benchmark_id}/split")
def create_benchmark_split(benchmark_id: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_benchmarks")
    benchmark = _benchmark_or_404(benchmark_id, user)
    examples = BenchmarkExampleRepository.list(benchmark_id=benchmark_id, limit=10000)
    split_examples = create_train_validation_test_split(examples, float(payload.get("train_ratio", 0.8)), float(payload.get("validation_ratio", 0.1)), float(payload.get("test_ratio", 0.1)), int(payload.get("seed", 42)))
    for example in split_examples:
        BenchmarkExampleRepository.update_split(example["example_id"], example["split"])
    counts = split_counts(split_examples)
    log_audit_event("benchmark_split_created", "benchmark_dataset", benchmark_id, benchmark["name"], "success", "Medium", "Train/validation/test split created.", user=user, workspace=get_workspace(benchmark["workspace_id"]), metadata=counts)
    return {"benchmark_id": benchmark_id, "split_counts": counts}


@app.get("/benchmarks/{benchmark_id}/quality")
def benchmark_quality(benchmark_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_benchmarks")
    benchmark = _benchmark_or_404(benchmark_id, user)
    examples = BenchmarkExampleRepository.list(benchmark_id=benchmark_id, limit=10000)
    report = analyze_benchmark_quality(examples)
    log_audit_event("benchmark_quality_viewed", "benchmark_dataset", benchmark_id, benchmark["name"], "success", "Info", "Benchmark quality report viewed.", user=user, workspace=get_workspace(benchmark["workspace_id"]))
    return report


@app.post("/benchmarks/training/merge")
def merge_training_data(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "view_benchmarks")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    examples, summary = _merge_training_examples(payload)
    log_audit_event("training_dataset_merged", "training_dataset", workspace_id, "Training merge preview", "success", "Info", "Training data merged for preview.", user=user, workspace=workspace, metadata={"total_examples": len(examples)})
    return {"summary": summary, "preview": _redact_examples_if_needed(workspace_id, examples[:20])}


@app.post("/benchmarks/training/export")
def export_training_dataset(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "export_training_data")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    examples, summary = _merge_training_examples(payload)
    if not examples:
        raise HTTPException(status_code=400, detail="No examples available for export.")
    if any(example.get("split") == "unsplit" for example in examples):
        examples = create_train_validation_test_split(examples)
    settings = get_privacy_settings(workspace_id)
    export_examples = sanitize_metadata(examples) if settings.get("privacy_mode_enabled", True) and settings.get("redact_exports", True) else examples
    export_id = str(uuid4())
    fmt = payload.get("format", "jsonl")
    if fmt not in {"jsonl", "json"}:
        raise HTTPException(status_code=400, detail="Unsupported export format.")
    output_path = TRAINING_EXPORT_DIR / f"{export_id}.{fmt}"
    if fmt == "jsonl":
        export_training_jsonl(export_examples, output_path)
    else:
        export_training_json(export_examples, output_path)
    counts = split_counts(examples)
    included_types = sorted({example.get("dataset_type", "") for example in examples if example.get("dataset_type")})
    export = TrainingDatasetExportRepository.create({
        "export_id": export_id,
        "workspace_id": workspace_id,
        "name": payload.get("name", "DriftGuard Training Export"),
        "description": payload.get("description", ""),
        "format": fmt,
        "total_examples": len(examples),
        "train_count": counts["train"],
        "validation_count": counts["validation"],
        "test_count": counts["test"],
        "included_dataset_types": included_types,
        "export_path": str(output_path),
        "created_by": user.get("user_id", ""),
        "created_at": utc_now(),
    })
    log_audit_event("training_dataset_exported", "training_dataset_export", export_id, export["name"], "success", "Medium", "Training dataset exported.", user=user, workspace=workspace, metadata={"format": fmt, "summary": summary})
    return {"export": export, "download_url": f"/benchmarks/training/exports/{export_id}/download"}


@app.get("/benchmarks/training/exports")
def training_exports(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_benchmarks")
    _require_workspace_scope(user, workspace_id)
    return TrainingDatasetExportRepository.list(workspace_id)


@app.get("/benchmarks/training/exports/{export_id}/download")
def download_training_export(export_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "export_training_data")
    export = TrainingDatasetExportRepository.get_by_id(export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Training export not found.")
    workspace = _require_workspace_scope(user, export.get("workspace_id", ""))
    path = Path(export.get("export_path", ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="Training export file not found.")
    log_audit_event("training_export_downloaded", "training_dataset_export", export_id, export["name"], "success", "Info", "Training export downloaded.", user=user, workspace=workspace)
    return FileResponse(path, media_type="application/json", filename=path.name)


@app.delete("/benchmarks/{benchmark_id}")
def delete_benchmark_dataset(benchmark_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "delete_benchmarks")
    benchmark = _benchmark_or_404(benchmark_id, user)
    if not BenchmarkDatasetRepository.delete(benchmark_id):
        raise HTTPException(status_code=404, detail="Benchmark dataset not found.")
    log_audit_event("benchmark_dataset_deleted", "benchmark_dataset", benchmark_id, benchmark["name"], "success", "High", "Benchmark dataset deleted.", user=user, workspace=get_workspace(benchmark["workspace_id"]), metadata={"dataset_type": benchmark.get("dataset_type")})
    return {"status": "ok", "message": "Benchmark dataset deleted successfully."}


def _ml_experiment_or_404(experiment_id: str, user: dict) -> dict:
    experiment = ModelExperimentRepository.get_by_id(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Model experiment not found.")
    _require_workspace_scope(user, experiment.get("workspace_id", ""))
    return experiment


def _ml_compare_payload(base: dict, current: dict) -> dict:
    accuracy_delta = round(current.get("accuracy", 0) - base.get("accuracy", 0), 4)
    f1_delta = round(current.get("f1_macro", 0) - base.get("f1_macro", 0), 4)
    precision_delta = round(current.get("precision_macro", 0) - base.get("precision_macro", 0), 4)
    recall_delta = round(current.get("recall_macro", 0) - base.get("recall_macro", 0), 4)
    better = current if (current.get("f1_macro", 0), current.get("accuracy", 0)) >= (base.get("f1_macro", 0), base.get("accuracy", 0)) else base
    return {
        "base_experiment": base,
        "current_experiment": current,
        "accuracy_delta": accuracy_delta,
        "f1_delta": f1_delta,
        "precision_delta": precision_delta,
        "recall_delta": recall_delta,
        "better_experiment_id": better.get("experiment_id", ""),
        "summary": f"Current model changes F1 by {f1_delta:+.2f} and accuracy by {accuracy_delta:+.2f}.",
    }


def _experiment_report_markdown(experiment: dict, artifact: dict | None) -> str:
    metrics = experiment.get("metrics", {})
    confusion = experiment.get("confusion_matrix", {})
    lines = [
        "# DriftGuard AI Model Experiment Report",
        "",
        "## Experiment Summary",
        f"- Name: {experiment.get('name', '')}",
        f"- Task type: {experiment.get('task_type', '')}",
        f"- Model type: {experiment.get('model_type', '')}",
        f"- Status: {experiment.get('status', '')}",
        f"- Total examples: {experiment.get('total_examples', 0)}",
        f"- Train count: {experiment.get('train_count', 0)}",
        f"- Test count: {experiment.get('test_count', 0)}",
        "",
        "## Metrics",
        f"- Accuracy: {experiment.get('accuracy', 0)}",
        f"- Precision macro: {experiment.get('precision_macro', 0)}",
        f"- Recall macro: {experiment.get('recall_macro', 0)}",
        f"- F1 macro: {experiment.get('f1_macro', 0)}",
        "",
        "## Confusion Matrix",
        json.dumps(confusion, indent=2),
        "",
        "## Classification Report",
        json.dumps(metrics.get("classification_report", {}), indent=2),
        "",
        "## Training Logs",
    ]
    lines.extend(f"- {item}" for item in experiment.get("training_log", []))
    lines.extend(["", "## Artifact Metadata", json.dumps(get_model_metadata(artifact or {}), indent=2)])
    return "\n".join(lines)


@app.post("/ml/experiments/train")
def train_model_experiment(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "train_ml_models")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    task_type = payload.get("task_type", "")
    model_type = payload.get("model_type", "")
    if task_type not in SUPPORTED_TASK_TYPES:
        raise HTTPException(status_code=400, detail="Invalid task_type.")
    if model_type not in SUPPORTED_MODEL_TYPES:
        raise HTTPException(status_code=400, detail="Invalid model_type.")
    experiment_id = str(uuid4())
    now = utc_now()
    experiment = ModelExperimentRepository.create({
        "experiment_id": experiment_id,
        "workspace_id": workspace_id,
        "name": payload.get("name", "").strip() or "Model Training Experiment",
        "task_type": task_type,
        "model_type": model_type,
        "dataset_source": "training_export+benchmark+human_corrected",
        "training_export_id": payload.get("training_export_id", ""),
        "benchmark_ids": payload.get("benchmark_ids", []),
        "status": "running",
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "training_log": ["Training experiment started."],
    })
    log_audit_event("ml_training_started", "model_experiment", experiment_id, experiment["name"], "success", "Medium", "ML training experiment started.", user=user, workspace=workspace, metadata={"task_type": task_type, "model_type": model_type})
    try:
        examples = load_training_examples(
            workspace_id,
            payload.get("training_export_id") or None,
            payload.get("benchmark_ids", []),
            payload.get("include_human_corrected", True),
            int(payload.get("max_examples", 5000)),
        )
        result = train_model(
            workspace_id,
            experiment_id,
            task_type,
            model_type,
            examples,
            float(payload.get("test_size", 0.2)),
            int(payload.get("random_seed", 42)),
        )
        metrics = result["metrics"]
        updated = ModelExperimentRepository.update_metrics(experiment_id, {
            "status": "completed",
            "total_examples": result["total_examples"],
            "train_count": result["train_count"],
            "validation_count": result["validation_count"],
            "test_count": result["test_count"],
            "accuracy": metrics["accuracy"],
            "precision_macro": metrics["precision_macro"],
            "recall_macro": metrics["recall_macro"],
            "f1_macro": metrics["f1_macro"],
            "confusion_matrix": metrics["confusion_matrix"],
            "label_distribution": result["label_distribution"],
            "metrics": metrics,
            "training_log": result["training_log"],
            "completed_at": utc_now(),
        })
        ModelExperimentRepository.update_status(experiment_id, "completed", result["training_log"], updated.get("completed_at", ""))
        artifact = ModelArtifactRepository.create({
            "artifact_id": str(uuid4()),
            "workspace_id": workspace_id,
            "experiment_id": experiment_id,
            "model_path": result["artifact"]["model_path"],
            "vectorizer_path": result["artifact"]["vectorizer_path"],
            "metadata_path": result["artifact"]["metadata_path"],
            "model_type": model_type,
            "task_type": task_type,
            "created_at": utc_now(),
        })
        log_audit_event("ml_training_completed", "model_experiment", experiment_id, experiment["name"], "success", "Medium", "ML training experiment completed.", user=user, workspace=workspace, metadata={"f1_macro": metrics["f1_macro"], "accuracy": metrics["accuracy"]})
        return {"experiment": ModelExperimentRepository.get_by_id(experiment_id), "artifact": artifact}
    except ValueError as exc:
        log = ["Training experiment started.", str(exc)]
        failed = ModelExperimentRepository.update_status(experiment_id, "failed", log, utc_now())
        log_audit_event("ml_training_failed", "model_experiment", experiment_id, experiment["name"], "failed", "High", str(exc), user=user, workspace=workspace)
        raise HTTPException(status_code=400, detail={"message": str(exc), "experiment": failed}) from exc


@app.get("/ml/experiments")
def model_experiments(workspace_id: str = Query(...), task_type: str = Query(""), model_type: str = Query(""), status: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "view_ml_models")
    _require_workspace_scope(user, workspace_id)
    return ModelExperimentRepository.list_by_workspace(workspace_id, {"task_type": task_type, "model_type": model_type, "status": status})


@app.get("/ml/leaderboard")
def model_leaderboard(workspace_id: str = Query(...), task_type: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "view_ml_models")
    _require_workspace_scope(user, workspace_id)
    return ModelExperimentRepository.leaderboard(workspace_id, task_type)


@app.get("/ml/experiments/compare")
def compare_model_experiments(base_id: str = Query(...), current_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_ml_models")
    base = _ml_experiment_or_404(base_id, user)
    current = _ml_experiment_or_404(current_id, user)
    if base.get("workspace_id") != current.get("workspace_id"):
        raise HTTPException(status_code=400, detail="Experiments must belong to the same workspace.")
    return _ml_compare_payload(base, current)


@app.get("/ml/experiments/{experiment_id}")
def model_experiment_item(experiment_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_ml_models")
    experiment = _ml_experiment_or_404(experiment_id, user)
    return {"experiment": experiment, "artifact": ModelArtifactRepository.get_by_experiment(experiment_id)}


@app.delete("/ml/experiments/{experiment_id}")
def delete_model_experiment(experiment_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "delete_ml_experiments")
    experiment = _ml_experiment_or_404(experiment_id, user)
    artifact = ModelArtifactRepository.get_by_experiment(experiment_id)
    if artifact:
        delete_model_artifact(artifact)
        ModelArtifactRepository.delete(artifact["artifact_id"])
    if not ModelExperimentRepository.delete(experiment_id):
        raise HTTPException(status_code=404, detail="Model experiment not found.")
    log_audit_event("ml_experiment_deleted", "model_experiment", experiment_id, experiment["name"], "success", "High", "ML experiment deleted.", user=user, workspace=get_workspace(experiment["workspace_id"]))
    return {"status": "ok", "message": "Model experiment deleted successfully."}


@app.post("/ml/experiments/{experiment_id}/deploy")
def deploy_model_experiment(experiment_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "deploy_ml_models")
    experiment = _ml_experiment_or_404(experiment_id, user)
    if experiment.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Only completed experiments can be deployed.")
    artifact = ModelArtifactRepository.get_by_experiment(experiment_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Model artifact not found.")
    deployed = DeployedModelRepository.deploy_model({
        "deployed_model_id": str(uuid4()),
        "workspace_id": experiment["workspace_id"],
        "task_type": experiment["task_type"],
        "experiment_id": experiment_id,
        "artifact_id": artifact["artifact_id"],
        "model_type": experiment["model_type"],
        "deployed_by": user.get("user_id", ""),
        "deployed_at": utc_now(),
    })
    log_audit_event("ml_model_deployed", "deployed_model", deployed["deployed_model_id"], experiment["name"], "success", "High", "ML model deployed.", user=user, workspace=get_workspace(experiment["workspace_id"]), metadata={"experiment_id": experiment_id})
    return deployed


@app.post("/ml/deployed/{task_type}/rollback")
def rollback_deployed_model(task_type: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "delete_ml_experiments")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    rolled_back = DeployedModelRepository.rollback_model(workspace_id, task_type)
    if not rolled_back:
        raise HTTPException(status_code=404, detail="No active deployed model found for this task.")
    log_audit_event("ml_model_rolled_back", "deployed_model", rolled_back["deployed_model_id"], task_type, "success", "High", "ML model rolled back to rule-based fallback.", user=user, workspace=workspace)
    return rolled_back


@app.get("/ml/deployed")
def deployed_models(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_ml_models")
    _require_workspace_scope(user, workspace_id)
    return DeployedModelRepository.list_by_workspace(workspace_id)


@app.post("/ml/predict")
def ml_predict(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "view_ml_models")
    workspace_id = payload.get("workspace_id", "")
    workspace = _require_workspace_scope(user, workspace_id)
    task_type = payload.get("task_type", "")
    if task_type not in SUPPORTED_TASK_TYPES:
        raise HTTPException(status_code=400, detail="Invalid task_type.")
    result = predict_with_active_model(workspace_id, task_type, payload.get("input_context", {}))
    log_audit_event("ml_prediction_run", "model_prediction", workspace_id, task_type, "success", "Info", "ML prediction endpoint called.", user=user, workspace=workspace, metadata={"fallback_used": result.get("fallback_used", True), "experiment_id": result.get("experiment_id", "")})
    return result


@app.get("/ml/experiments/{experiment_id}/export-markdown")
def export_model_experiment_markdown(experiment_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_ml_models")
    experiment = _ml_experiment_or_404(experiment_id, user)
    artifact = ModelArtifactRepository.get_by_experiment(experiment_id)
    content = _experiment_report_markdown(experiment, artifact)
    log_audit_event("ml_report_exported", "model_experiment", experiment_id, experiment["name"], "success", "Info", "ML experiment report exported.", user=user, workspace=get_workspace(experiment["workspace_id"]))
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=driftguard-model-experiment-{experiment_id[:8]}.md"},
    )


@app.post("/dataset/library/{dataset_id}/evaluate", response_model=DatasetEvaluationResponse)
def evaluate_library_dataset(dataset_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    global LATEST_EVALUATION_RESULT
    check_permission(user, "run_evaluation")
    _require_workspace_scope(user, workspace_id)
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    _assert_item_workspace(dataset.get("metadata", {}), workspace_id)
    cases = [DatasetCase(**case) for case in dataset.get("cases", [])]
    LATEST_EVALUATION_RESULT = evaluate_dataset_cases(cases)
    save_evaluation_result(
        LATEST_EVALUATION_RESULT,
        dataset_id,
        dataset.get("metadata", {}).get("name", "Saved Dataset"),
        workspace_id,
    )
    log_audit_event("run_evaluation", "dataset", dataset_id, dataset.get("metadata", {}).get("name", "Saved Dataset"), "success", "Low", "User ran evaluation on saved dataset.", user=user, workspace=get_workspace(workspace_id), metadata={"accuracy": LATEST_EVALUATION_RESULT.accuracy, "total_cases": LATEST_EVALUATION_RESULT.total_cases})
    return LATEST_EVALUATION_RESULT


@app.get("/dataset/evaluations/history")
def evaluation_history(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    return list_evaluation_history(workspace_id)


@app.get("/dataset/evaluations/history/{evaluation_id}")
def evaluation_history_item(evaluation_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    global LATEST_EVALUATION_RESULT
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    evaluation = get_evaluation_result(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation result not found.")
    _assert_item_workspace(evaluation, workspace_id)
    LATEST_EVALUATION_RESULT = DatasetEvaluationResponse(**evaluation["result"])
    log_audit_event("view_evaluation", "evaluation", evaluation_id, evaluation.get("dataset_name", ""), "success", "Info", "User viewed an evaluation result.", user=user, workspace=get_workspace(workspace_id))
    return evaluation


@app.delete("/dataset/evaluations/history/{evaluation_id}")
def delete_evaluation_history_item(evaluation_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "delete_history")
    _require_workspace_scope(user, workspace_id)
    evaluation = get_evaluation_result(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation result not found.")
    _assert_item_workspace(evaluation, workspace_id)
    if not delete_evaluation_result(evaluation_id):
        raise HTTPException(status_code=404, detail="Evaluation result not found.")
    log_audit_event("delete_evaluation", "evaluation", evaluation_id, evaluation.get("dataset_name", ""), "success", "High", "User deleted an evaluation result.", user=user, workspace=get_workspace(workspace_id))
    return {"status": "ok", "message": "Evaluation result deleted successfully."}


@app.get("/dataset/evaluations/compare")
def compare_evaluation_runs(
    base_id: str = Query(...),
    current_id: str = Query(...),
    workspace_id: str = Query(...),
    user: dict = Depends(require_auth),
):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    for evaluation_id in [base_id, current_id]:
        evaluation = get_evaluation_result(evaluation_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="One or both evaluation results were not found.")
        _assert_item_workspace(evaluation, workspace_id)
    comparison = compare_evaluations(base_id, current_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="One or both evaluation results were not found.")
    log_audit_event("compare_evaluations", "evaluation", resource_name=f"{base_id[:8]} vs {current_id[:8]}", status="success", severity="Info", message="User compared evaluation runs.", user=user, workspace=get_workspace(workspace_id))
    return comparison


def _latest_evaluation_or_404() -> DatasetEvaluationResponse:
    if LATEST_EVALUATION_RESULT is None:
        raise HTTPException(status_code=404, detail="No evaluation result available. Please run an evaluation first.")
    return LATEST_EVALUATION_RESULT


@app.get("/dataset/evaluation/latest/export-json")
def export_latest_evaluation_json(user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    evaluation = _latest_evaluation_or_404()
    log_audit_event("export_json_report", "evaluation", status="success", severity="Medium", message="User exported latest evaluation JSON report.", user=user)
    return Response(
        content=evaluation.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-evaluation-report.json"},
    )


@app.get("/dataset/evaluation/latest/export-markdown")
def export_latest_evaluation_markdown(user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    evaluation = _latest_evaluation_or_404()
    log_audit_event("export_markdown_report", "evaluation", status="success", severity="Medium", message="User exported latest evaluation Markdown report.", user=user)
    return Response(
        content=evaluation_to_markdown(evaluation),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=driftguard-evaluation-report.md"},
    )


@app.post("/feedback/case", response_model=CaseFeedbackResponse)
def save_feedback_for_case(
    request: CaseFeedbackRequest,
    workspace_id: str = Query(...),
    user: dict = Depends(require_auth),
):
    check_permission(user, "add_feedback")
    _require_workspace_scope(user, workspace_id)
    try:
        feedback = save_case_feedback(request, workspace_id)
        log_audit_event("save_feedback", "feedback", feedback["feedback_id"], request.case_id, "success", "Medium", "User saved human feedback.", user=user, workspace=get_workspace(workspace_id), metadata={"evaluation_id": request.evaluation_id})
        return feedback
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/feedback", response_model=list[CaseFeedbackResponse])
def all_feedback(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    return list_feedback(workspace_id)


@app.get("/feedback/evaluation/{evaluation_id}", response_model=list[CaseFeedbackResponse])
def feedback_for_evaluation(evaluation_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    return get_feedback_for_evaluation(evaluation_id, workspace_id)


@app.get("/feedback/evaluation/{evaluation_id}/summary", response_model=FeedbackSummaryResponse)
def feedback_summary(evaluation_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    try:
        return calculate_feedback_summary(evaluation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/feedback/{feedback_id}")
def delete_feedback_item(feedback_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "add_feedback")
    if not delete_feedback(feedback_id):
        raise HTTPException(status_code=404, detail="Feedback not found.")
    log_audit_event("delete_feedback", "feedback", feedback_id, feedback_id, "success", "High", "User deleted feedback.", user=user)
    return {"status": "ok", "message": "Feedback deleted successfully."}


@app.get("/feedback/evaluation/{evaluation_id}/export-corrected-dataset")
def export_corrected_dataset_endpoint(evaluation_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    try:
        payload = export_corrected_dataset(evaluation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_audit_event("export_corrected_dataset", "feedback", evaluation_id, evaluation_id, "success", "Medium", "User exported corrected dataset.", user=user)
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-corrected-dataset.json"},
    )


@app.get("/feedback/evaluation/{evaluation_id}/build-training-dataset")
def build_training_dataset_endpoint(evaluation_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    try:
        payload = build_training_dataset(evaluation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_audit_event("build_training_dataset", "feedback", evaluation_id, evaluation_id, "success", "Medium", "User built training dataset.", user=user)
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-training-dataset.json"},
    )


@app.get("/root-cause/latest")
def latest_root_cause(user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    evaluation = _latest_evaluation_or_404()
    log_audit_event("generate_root_cause", "root_cause", "latest", "Latest Evaluation", "success", "Info", "User generated root cause analysis.", user=user)
    return build_root_cause_report(evaluation, "latest")


@app.get("/root-cause/evaluation/{evaluation_id}")
def root_cause_for_evaluation(evaluation_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    evaluation = get_evaluation_result(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation result not found.")
    log_audit_event("generate_root_cause", "root_cause", evaluation_id, evaluation.get("dataset_name", ""), "success", "Info", "User generated root cause analysis for evaluation.", user=user)
    return build_root_cause_report(evaluation.get("result", {}), evaluation_id)


@app.get("/root-cause/latest/export-json")
def export_latest_root_cause_json(user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    report = build_root_cause_report(_latest_evaluation_or_404(), "latest")
    log_audit_event("export_root_cause", "root_cause", "latest", "Latest Evaluation", "success", "Medium", "User exported root cause JSON.", user=user)
    return Response(
        content=json.dumps(report, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-root-cause-report.json"},
    )


@app.get("/root-cause/latest/export-markdown")
def export_latest_root_cause_markdown(user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    report = build_root_cause_report(_latest_evaluation_or_404(), "latest")
    log_audit_event("export_root_cause", "root_cause", "latest", "Latest Evaluation", "success", "Medium", "User exported root cause Markdown.", user=user)
    return Response(
        content=root_cause_report_to_markdown(report),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=driftguard-root-cause-report.md"},
    )


@app.get("/timeline/latest")
def latest_timeline(user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    evaluation = _latest_evaluation_or_404()
    log_audit_event("generate_timeline", "timeline", "latest", "Latest Evaluation", "success", "Info", "User generated drift timeline.", user=user)
    return build_evaluation_timeline(evaluation, "latest")


@app.get("/timeline/evaluation/{evaluation_id}")
def timeline_for_evaluation(evaluation_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    evaluation = get_evaluation_result(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation result not found.")
    log_audit_event("generate_timeline", "timeline", evaluation_id, evaluation.get("dataset_name", ""), "success", "Info", "User generated timeline for evaluation.", user=user)
    return build_evaluation_timeline(evaluation.get("result", {}), evaluation_id)


@app.get("/timeline/latest/export-json")
def export_latest_timeline_json(user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    report = build_evaluation_timeline(_latest_evaluation_or_404(), "latest")
    log_audit_event("export_timeline", "timeline", "latest", "Latest Evaluation", "success", "Medium", "User exported timeline JSON.", user=user)
    return Response(
        content=json.dumps(report, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-timeline-report.json"},
    )


@app.get("/timeline/latest/export-markdown")
def export_latest_timeline_markdown(user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    report = build_evaluation_timeline(_latest_evaluation_or_404(), "latest")
    log_audit_event("export_timeline", "timeline", "latest", "Latest Evaluation", "success", "Medium", "User exported timeline Markdown.", user=user)
    return Response(
        content=export_timeline_markdown(report),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=driftguard-timeline-report.md"},
    )


@app.get("/impact-graph/latest")
def latest_impact_graph(user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    evaluation = _latest_evaluation_or_404()
    log_audit_event("generate_impact_graph", "impact_graph", "latest", "Latest Evaluation", "success", "Info", "User generated impact graph.", user=user)
    return build_evaluation_impact_graph(evaluation, "latest")


@app.get("/impact-graph/evaluation/{evaluation_id}")
def impact_graph_for_evaluation(evaluation_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    evaluation = get_evaluation_result(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation result not found.")
    log_audit_event("generate_impact_graph", "impact_graph", evaluation_id, evaluation.get("dataset_name", ""), "success", "Info", "User generated impact graph for evaluation.", user=user)
    return build_evaluation_impact_graph(evaluation.get("result", {}), evaluation_id)


@app.get("/impact-graph/latest/export-json")
def export_latest_impact_graph_json(user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    report = export_impact_graph_json(build_evaluation_impact_graph(_latest_evaluation_or_404(), "latest"))
    log_audit_event("export_impact_graph", "impact_graph", "latest", "Latest Evaluation", "success", "Medium", "User exported impact graph JSON.", user=user)
    return Response(
        content=json.dumps(report, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-impact-graph.json"},
    )


@app.post("/monitoring/rules")
def create_monitoring_rule_endpoint(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "create_monitoring_rule")
    _require_workspace_scope(user, payload.get("workspace_id", ""))
    try:
        rule = create_monitoring_rule(payload)
        log_audit_event("create_monitoring_rule", "monitoring_rule", rule["rule_id"], rule["name"], "success", "Medium", "User created monitoring rule.", user=user, workspace=get_workspace(rule.get("workspace_id", "")))
        return rule
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/monitoring/rules")
def monitoring_rules(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    return list_monitoring_rules(workspace_id)


@app.get("/monitoring/rules/{rule_id}")
def monitoring_rule(rule_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    rule = get_monitoring_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Monitoring rule not found.")
    _assert_item_workspace(rule, workspace_id)
    return rule


@app.put("/monitoring/rules/{rule_id}")
def update_monitoring_rule_endpoint(rule_id: str, payload: dict, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "create_monitoring_rule")
    _require_workspace_scope(user, workspace_id)
    existing = get_monitoring_rule(rule_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Monitoring rule not found.")
    _assert_item_workspace(existing, workspace_id)
    try:
        rule = update_monitoring_rule(rule_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if rule is None:
        raise HTTPException(status_code=404, detail="Monitoring rule not found.")
    log_audit_event("update_monitoring_rule", "monitoring_rule", rule_id, rule.get("name", ""), "success", "Medium", "User updated monitoring rule.", user=user, workspace=get_workspace(workspace_id))
    return rule


@app.delete("/monitoring/rules/{rule_id}")
def delete_monitoring_rule_endpoint(rule_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "delete_monitoring_rule")
    _require_workspace_scope(user, workspace_id)
    rule = get_monitoring_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Monitoring rule not found.")
    _assert_item_workspace(rule, workspace_id)
    if not delete_monitoring_rule(rule_id):
        raise HTTPException(status_code=404, detail="Monitoring rule not found.")
    log_audit_event("delete_monitoring_rule", "monitoring_rule", rule_id, rule.get("name", ""), "success", "High", "User deleted monitoring rule.", user=user, workspace=get_workspace(workspace_id))
    return {"status": "ok", "message": "Monitoring rule deleted successfully."}


@app.post("/monitoring/rules/{rule_id}/run")
def run_monitoring_rule_endpoint(rule_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "run_evaluation")
    _require_workspace_scope(user, workspace_id)
    rule = get_monitoring_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Monitoring rule not found.")
    _assert_item_workspace(rule, workspace_id)
    try:
        result = run_monitoring_check(rule_id)
        log_audit_event("run_monitoring_check", "monitoring_rule", rule_id, rule.get("name", ""), "success", "Low", "User ran monitoring check.", user=user, workspace=get_workspace(workspace_id), metadata={"alerts_created": result["run"].get("alerts_created", 0)})
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Monitoring evaluation failed: {exc}") from exc


@app.get("/monitoring/runs")
def monitoring_runs(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    return list_monitoring_runs(workspace_id)


@app.get("/monitoring/runs/{run_id}")
def monitoring_run(run_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    run = get_monitoring_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Monitoring run not found.")
    _assert_item_workspace(run, workspace_id)
    return run


@app.delete("/monitoring/runs/{run_id}")
def delete_monitoring_run_endpoint(run_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "delete_history")
    _require_workspace_scope(user, workspace_id)
    run = get_monitoring_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Monitoring run not found.")
    _assert_item_workspace(run, workspace_id)
    if not delete_monitoring_run(run_id):
        raise HTTPException(status_code=404, detail="Monitoring run not found.")
    log_audit_event("delete_monitoring_run", "monitoring_run", run_id, run.get("rule_name", ""), "success", "High", "User deleted monitoring run.", user=user, workspace=get_workspace(workspace_id))
    return {"status": "ok", "message": "Monitoring run deleted successfully."}


@app.get("/monitoring/alerts")
def monitoring_alerts(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    return list_alerts(workspace_id)


@app.get("/monitoring/alerts/export-json")
def export_monitoring_alerts_json(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    _require_workspace_scope(user, workspace_id)
    alerts = list_alerts(workspace_id)
    log_audit_event("export_alerts", "alert", resource_name="Monitoring Alerts", status="success", severity="Medium", message="User exported monitoring alerts JSON.", user=user, workspace=get_workspace(workspace_id), metadata={"total_alerts": len(alerts), "format": "json"})
    return Response(
        content=json.dumps(alerts, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftguard-monitoring-alerts.json"},
    )


@app.get("/monitoring/alerts/export-markdown")
def export_monitoring_alerts_markdown(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "export_reports")
    _require_workspace_scope(user, workspace_id)
    log_audit_event("export_alerts", "alert", resource_name="Monitoring Alerts", status="success", severity="Medium", message="User exported monitoring alerts Markdown.", user=user, workspace=get_workspace(workspace_id), metadata={"format": "markdown"})
    return Response(
        content=export_alerts_markdown(list_alerts(workspace_id)),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=driftguard-monitoring-alerts.md"},
    )


@app.get("/monitoring/alerts/{alert_id}")
def monitoring_alert(alert_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_dashboard")
    _require_workspace_scope(user, workspace_id)
    alert = get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    _assert_item_workspace(alert, workspace_id)
    return alert


@app.put("/monitoring/alerts/{alert_id}/status")
def update_monitoring_alert_status(alert_id: str, payload: dict, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_alerts")
    _require_workspace_scope(user, workspace_id)
    existing = get_alert(alert_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    _assert_item_workspace(existing, workspace_id)
    try:
        alert = mark_alert_status(alert_id, payload.get("status", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    log_audit_event("update_alert_status", "alert", alert_id, alert.get("title", ""), "success", "Medium", f"User updated alert status to {alert.get('status')}.", user=user, workspace=get_workspace(workspace_id))
    return alert


@app.delete("/monitoring/alerts/{alert_id}")
def delete_monitoring_alert_endpoint(alert_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_alerts")
    _require_workspace_scope(user, workspace_id)
    alert = get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    _assert_item_workspace(alert, workspace_id)
    if not delete_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found.")
    log_audit_event("delete_alert", "alert", alert_id, alert.get("title", ""), "success", "High", "User deleted alert.", user=user, workspace=get_workspace(workspace_id))
    return {"status": "ok", "message": "Alert deleted successfully."}


def _incident_or_404(incident_id: str, user: dict) -> dict:
    check_permission(user, "view_incidents")
    incident = IncidentRepository.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    _require_workspace_scope(user, incident["workspace_id"])
    return incident


@app.post("/incidents")
def create_incident_endpoint(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_incidents")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    if not payload.get("title"):
        raise HTTPException(status_code=400, detail="Incident title is required.")
    incident = create_incident(payload, user)
    log_audit_event("incident_created", "incident", incident["incident_id"], incident["title"], "success", incident["severity"], "Incident created.", user=user, workspace=workspace)
    return incident


@app.post("/incidents/from-alert")
def create_incident_from_alert(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_incidents")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    alert_id = payload.get("alert_id", "")
    alert = get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    _assert_item_workspace(alert, workspace_id)
    incident = create_incident({
        "workspace_id": workspace_id,
        "title": payload.get("title") or alert.get("title") or "Monitoring alert incident",
        "description": payload.get("description") or alert.get("message", ""),
        "severity": payload.get("severity") or alert.get("severity", "Medium"),
        "source_type": "monitoring_alert",
        "source_id": alert_id,
        "related_alert_id": alert_id,
        "related_evaluation_id": alert.get("related_evaluation_id", ""),
        "metadata": {"alert": alert},
    }, user)
    log_audit_event("incident_created_from_alert", "incident", incident["incident_id"], incident["title"], "success", incident["severity"], "Incident created from alert.", user=user, workspace=workspace, metadata={"alert_id": alert_id})
    return incident


@app.get("/incidents")
def list_incidents(workspace_id: str = Query(...), status: str = Query(""), severity: str = Query(""), source_type: str = Query(""), assigned_to: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "view_incidents")
    _require_workspace_scope(user, workspace_id)
    return IncidentRepository.list_by_workspace(workspace_id, {"status": status, "severity": severity, "source_type": source_type, "assigned_to": assigned_to})


@app.get("/incidents/summary")
def incident_summary(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_incidents")
    _require_workspace_scope(user, workspace_id)
    summary = IncidentRepository.summary(workspace_id)
    summary["config"] = {
        "auto_create_enabled": INCIDENT_AUTO_CREATE_ENABLED,
        "auto_create_severities": INCIDENT_AUTO_CREATE_SEVERITIES,
        "webhook_timeout_seconds": WEBHOOK_TIMEOUT_SECONDS,
    }
    return summary


@app.post("/incidents/webhooks")
def create_incident_webhook(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_incident_automation")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    url = payload.get("url", "")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Webhook URL must start with http:// or https://.")
    now = utc_now()
    webhook = WebhookRepository.create({
        "webhook_id": str(uuid4()),
        "workspace_id": workspace_id,
        "name": payload.get("name", "Incident webhook"),
        "url": url,
        "event_types": payload.get("event_types", ["incident.created", "incident.status_changed", "incident.escalated"]),
        "enabled": payload.get("enabled", True),
        "secret_masked": mask_secret(payload.get("secret", "")) if payload.get("secret") else "",
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
    })
    log_audit_event("incident_webhook_created", "webhook", webhook["webhook_id"], webhook["name"], "success", "Medium", "Incident webhook created.", user=user, workspace=workspace)
    return webhook


@app.get("/incidents/webhooks")
def list_incident_webhooks(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_incidents")
    _require_workspace_scope(user, workspace_id)
    return WebhookRepository.list_by_workspace(workspace_id)


@app.put("/incidents/webhooks/{webhook_id}")
def update_incident_webhook(webhook_id: str, payload: dict, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_incident_automation")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    webhook = WebhookRepository.get_by_id(webhook_id)
    if not webhook or webhook.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    if payload.get("url") and not payload["url"].startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Webhook URL must start with http:// or https://.")
    if payload.get("secret"):
        payload["secret_masked"] = mask_secret(payload["secret"])
    updated = WebhookRepository.update(webhook_id, payload)
    log_audit_event("incident_webhook_updated", "webhook", webhook_id, updated["name"], "success", "Medium", "Incident webhook updated.", user=user, workspace=workspace)
    return updated


@app.delete("/incidents/webhooks/{webhook_id}")
def delete_incident_webhook(webhook_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_incident_automation")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    webhook = WebhookRepository.get_by_id(webhook_id)
    if not webhook or webhook.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    WebhookRepository.delete(webhook_id)
    log_audit_event("incident_webhook_deleted", "webhook", webhook_id, webhook["name"], "success", "High", "Incident webhook deleted.", user=user, workspace=workspace)
    return {"status": "ok", "message": "Webhook deleted successfully."}


@app.post("/incidents/webhooks/{webhook_id}/test")
def test_incident_webhook(webhook_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_incident_automation")
    _require_workspace_scope(user, workspace_id)
    webhook = WebhookRepository.get_by_id(webhook_id)
    if not webhook or webhook.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    return send_test_webhook(webhook)


@app.get("/incidents/notification-logs")
def list_incident_notification_logs(workspace_id: str = Query(...), limit: int = Query(100), user: dict = Depends(require_auth)):
    check_permission(user, "view_incidents")
    _require_workspace_scope(user, workspace_id)
    return NotificationDeliveryRepository.list_by_workspace(workspace_id, min(max(limit, 1), 500))


@app.post("/incidents/escalation-rules")
def create_escalation_rule(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_incident_automation")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    now = utc_now()
    rule = EscalationRuleRepository.create({
        "rule_id": str(uuid4()),
        "workspace_id": workspace_id,
        "name": payload.get("name", "Incident escalation rule"),
        "enabled": payload.get("enabled", True),
        "severity": payload.get("severity", "Critical"),
        "status_filter": payload.get("status_filter", "open"),
        "escalate_after_minutes": int(payload.get("escalate_after_minutes", 60)),
        "target_role": payload.get("target_role", "admin"),
        "target_user_id": payload.get("target_user_id", ""),
        "webhook_enabled": payload.get("webhook_enabled", True),
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
    })
    log_audit_event("incident_escalation_rule_created", "escalation_rule", rule["rule_id"], rule["name"], "success", "Medium", "Incident escalation rule created.", user=user, workspace=workspace)
    return rule


@app.get("/incidents/escalation-rules")
def list_escalation_rules(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_incidents")
    _require_workspace_scope(user, workspace_id)
    return EscalationRuleRepository.list_by_workspace(workspace_id)


@app.put("/incidents/escalation-rules/{rule_id}")
def update_escalation_rule(rule_id: str, payload: dict, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_incident_automation")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    rule = EscalationRuleRepository.get_by_id(rule_id)
    if not rule or rule.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="Escalation rule not found.")
    updated = EscalationRuleRepository.update(rule_id, payload)
    log_audit_event("incident_escalation_rule_updated", "escalation_rule", rule_id, updated["name"], "success", "Medium", "Incident escalation rule updated.", user=user, workspace=workspace)
    return updated


@app.delete("/incidents/escalation-rules/{rule_id}")
def delete_escalation_rule(rule_id: str, workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "manage_incident_automation")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    rule = EscalationRuleRepository.get_by_id(rule_id)
    if not rule or rule.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="Escalation rule not found.")
    EscalationRuleRepository.delete(rule_id)
    log_audit_event("incident_escalation_rule_deleted", "escalation_rule", rule_id, rule["name"], "success", "High", "Incident escalation rule deleted.", user=user, workspace=workspace)
    return {"status": "ok", "message": "Escalation rule deleted successfully."}


@app.post("/incidents/escalations/check")
def check_incident_escalations(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_incident_automation")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    result = check_escalations(workspace_id, user)
    log_audit_event("incident_escalations_checked", "incident", resource_name="Incident escalations", status="success", severity="Medium", message="Incident escalations checked.", user=user, workspace=workspace, metadata=result)
    return result


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str, user: dict = Depends(require_auth)):
    incident = _incident_or_404(incident_id, user)
    return {
        "incident": incident,
        "comments": IncidentCommentRepository.list_by_incident(incident_id),
        "timeline": IncidentTimelineRepository.list_by_incident(incident_id),
    }


@app.put("/incidents/{incident_id}/status")
def set_incident_status(incident_id: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_incidents")
    incident = _incident_or_404(incident_id, user)
    status = payload.get("status", "")
    if status not in {"open", "triaged", "in_progress", "escalated", "resolved", "closed"}:
        raise HTTPException(status_code=400, detail="Invalid incident status.")
    updated = update_incident_status(incident, status, user)
    log_audit_event("incident_status_updated", "incident", incident_id, updated["title"], "success", updated["severity"], f"Incident status updated to {status}.", user=user, workspace=get_workspace(updated["workspace_id"]))
    return updated


@app.put("/incidents/{incident_id}/assign")
def assign_incident_endpoint(incident_id: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_incidents")
    incident = _incident_or_404(incident_id, user)
    updated = assign_incident(incident, payload.get("assigned_to", ""), user)
    log_audit_event("incident_assigned", "incident", incident_id, updated["title"], "success", updated["severity"], "Incident assignment updated.", user=user, workspace=get_workspace(updated["workspace_id"]))
    return updated


@app.post("/incidents/{incident_id}/comments")
def add_incident_comment(incident_id: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_incidents")
    incident = _incident_or_404(incident_id, user)
    comment_text = payload.get("comment_text", "").strip()
    if not comment_text:
        raise HTTPException(status_code=400, detail="Comment text is required.")
    comment = add_comment(incident, comment_text, user)
    log_audit_event("incident_comment_added", "incident", incident_id, incident["title"], "success", incident["severity"], "Incident comment added.", user=user, workspace=get_workspace(incident["workspace_id"]))
    return comment


@app.delete("/incidents/{incident_id}")
def delete_incident_endpoint(incident_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "delete_incidents")
    incident = _incident_or_404(incident_id, user)
    IncidentRepository.delete(incident_id)
    log_audit_event("incident_deleted", "incident", incident_id, incident["title"], "success", "High", "Incident deleted.", user=user, workspace=get_workspace(incident["workspace_id"]))
    return {"status": "ok", "message": "Incident deleted successfully."}


@app.get("/incidents/{incident_id}/export-markdown")
def export_incident_markdown(incident_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "view_incidents")
    incident = _incident_or_404(incident_id, user)
    content = incident_to_markdown(incident, IncidentCommentRepository.list_by_incident(incident_id), IncidentTimelineRepository.list_by_incident(incident_id))
    log_audit_event("incident_exported", "incident", incident_id, incident["title"], "success", "Info", "Incident markdown exported.", user=user, workspace=get_workspace(incident["workspace_id"]))
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=driftguard-incident-{incident_id[:8]}.md"},
    )


def _integration_or_404(integration_id: str, user: dict) -> dict:
    check_permission(user, "view_integrations")
    integration = ExternalIntegrationRepository.get_by_id(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found.")
    _require_workspace_scope(user, integration["workspace_id"])
    return integration


@app.post("/integrations")
def create_external_integration(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_integrations")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    try:
        integration = create_integration(payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_audit_event("integration_created", "external_integration", integration["integration_id"], integration["name"], "success", "Medium", "External integration created.", user=user, workspace=workspace, metadata={"integration_type": integration["integration_type"], "mode": integration["mode"]})
    return integration


@app.get("/integrations")
def list_external_integration_settings(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_integrations")
    _require_workspace_scope(user, workspace_id)
    return list_external_integrations(workspace_id)


@app.get("/integrations/sync-records")
def get_external_sync_records(workspace_id: str = Query(...), integration_id: str = Query(""), source_type: str = Query(""), status: str = Query(""), action: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "view_integrations")
    _require_workspace_scope(user, workspace_id)
    return list_external_sync_records(workspace_id, {"integration_id": integration_id, "source_type": source_type, "status": status, "action": action})


@app.get("/integrations/linked-resources")
def get_external_linked_resources(workspace_id: str = Query(...), source_type: str = Query(""), source_id: str = Query(""), integration_type: str = Query(""), user: dict = Depends(require_auth)):
    check_permission(user, "view_integrations")
    _require_workspace_scope(user, workspace_id)
    return ExternalLinkedResourceRepository.list_by_workspace(workspace_id, {"source_type": source_type, "source_id": source_id, "integration_type": integration_type})


@app.get("/integrations/health-summary")
def get_external_integration_health_summary(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_integrations")
    _require_workspace_scope(user, workspace_id)
    return get_integration_health_summary(workspace_id)


@app.get("/integrations/mock-items")
def get_mock_external_items(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_integrations")
    _require_workspace_scope(user, workspace_id)
    return MockExternalTicketRepository.list_by_workspace(workspace_id)


@app.get("/integrations/{integration_id}")
def get_external_integration(integration_id: str, user: dict = Depends(require_auth)):
    return _integration_or_404(integration_id, user)


@app.put("/integrations/{integration_id}")
def update_external_integration(integration_id: str, payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_integrations")
    integration = _integration_or_404(integration_id, user)
    if payload.get("integration_type") and payload["integration_type"] not in {"jira", "github_issues", "slack", "teams", "generic_webhook"}:
        raise HTTPException(status_code=400, detail="Invalid integration_type.")
    if payload.get("mode") and payload["mode"] not in {"mock", "live"}:
        raise HTTPException(status_code=400, detail="Invalid integration mode.")
    if payload.get("secret"):
        payload["secret_masked"] = mask_secret(str(payload["secret"]))
    updated = ExternalIntegrationRepository.update(integration_id, payload)
    log_audit_event("integration_updated", "external_integration", integration_id, updated["name"], "success", "Medium", "External integration updated.", user=user, workspace=get_workspace(integration["workspace_id"]))
    return updated


@app.delete("/integrations/{integration_id}")
def delete_external_integration(integration_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "delete_integrations")
    integration = _integration_or_404(integration_id, user)
    ExternalIntegrationRepository.delete(integration_id)
    log_audit_event("integration_deleted", "external_integration", integration_id, integration["name"], "success", "High", "External integration deleted.", user=user, workspace=get_workspace(integration["workspace_id"]))
    return {"status": "ok", "message": "Integration deleted successfully."}


@app.post("/integrations/{integration_id}/test")
def test_external_integration(integration_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_integrations")
    integration = _integration_or_404(integration_id, user)
    try:
        result = test_integration(integration_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit_status = "success" if result["result"].get("success") else "failed"
    log_audit_event("integration_tested", "external_integration", integration_id, integration["name"], audit_status, "Medium", "External integration tested.", user=user, workspace=get_workspace(integration["workspace_id"]), metadata={"result": result["result"]})
    return result


@app.post("/integrations/{integration_id}/incident/{incident_id}/sync")
def sync_incident_external_endpoint(integration_id: str, incident_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_integrations")
    integration = _integration_or_404(integration_id, user)
    incident = _incident_or_404(incident_id, user)
    if incident["workspace_id"] != integration["workspace_id"]:
        raise HTTPException(status_code=400, detail="Incident and integration must belong to the same workspace.")
    log_audit_event("integration_sync_started", "external_integration", integration_id, integration["name"], "success", "Medium", "External incident sync started.", user=user, workspace=get_workspace(integration["workspace_id"]), metadata={"incident_id": incident_id})
    try:
        result = sync_incident_to_external(integration_id, incident_id, user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if result["result"].get("success"):
        action = "external_issue_created" if integration["integration_type"] == "github_issues" else "external_notification_sent" if integration["integration_type"] not in {"jira", "github_issues"} else "external_ticket_created"
        log_audit_event("integration_sync_success", "external_integration", integration_id, integration["name"], "success", "Medium", "External incident sync succeeded.", user=user, workspace=get_workspace(integration["workspace_id"]), metadata=result["result"])
        log_audit_event(action, "external_resource", result["result"].get("external_id", ""), integration["name"], "success", "Medium", "External resource created.", user=user, workspace=get_workspace(integration["workspace_id"]), metadata={"incident_id": incident_id})
    else:
        log_audit_event("integration_sync_failed", "external_integration", integration_id, integration["name"], "failed", "High", "External incident sync failed.", user=user, workspace=get_workspace(integration["workspace_id"]), metadata=result["result"])
    return result


@app.post("/integrations/{integration_id}/incident/{incident_id}/notify")
def notify_incident_external_endpoint(integration_id: str, incident_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "manage_integrations")
    integration = _integration_or_404(integration_id, user)
    incident = _incident_or_404(incident_id, user)
    if incident["workspace_id"] != integration["workspace_id"]:
        raise HTTPException(status_code=400, detail="Incident and integration must belong to the same workspace.")
    try:
        result = send_incident_notification(integration_id, incident_id, user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit_status = "success" if result["result"].get("success") else "failed"
    log_audit_event("external_notification_sent", "external_integration", integration_id, integration["name"], audit_status, "Medium", "External notification sent." if audit_status == "success" else "External notification failed.", user=user, workspace=get_workspace(integration["workspace_id"]), metadata=result["result"])
    return result


@app.get("/executive/metrics")
def executive_metrics(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_executive")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    metrics = collect_executive_metrics(workspace_id)
    log_audit_event("executive_metrics_viewed", "executive", resource_name="Executive Metrics", status="success", severity="Info", message="Executive metrics viewed.", user=user, workspace=workspace)
    return metrics


@app.post("/executive/roi")
def executive_roi(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "view_executive")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    metrics = collect_executive_metrics(workspace_id)
    roi = calculate_roi(metrics, payload.get("assumptions", {}))
    log_audit_event("executive_roi_calculated", "executive", resource_name="Executive ROI", status="success", severity="Info", message="Executive ROI calculated.", user=user, workspace=workspace, metadata={"estimated_total_value": roi["estimated_total_value"]})
    return roi


@app.post("/executive/report")
def generate_executive_report(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "generate_executive_reports")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    settings = get_privacy_settings(workspace_id)
    redact = settings.get("privacy_mode_enabled", True) and settings.get("redact_exports", True)
    report = build_executive_report(workspace_id, user.get("user_id", ""), payload.get("assumptions", {}), redact=redact)
    saved = ExecutiveReportRepository.create({
        "report_id": str(uuid4()),
        "workspace_id": workspace_id,
        "title": report["title"],
        "report": report,
        "created_by": user.get("user_id", ""),
        "created_at": report["created_at"],
    })
    log_audit_event("executive_report_generated", "executive_report", saved["report_id"], saved["title"], "success", "Medium", "Executive report generated.", user=user, workspace=workspace)
    return saved


@app.get("/executive/reports")
def list_executive_reports(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_executive")
    _require_workspace_scope(user, workspace_id)
    return ExecutiveReportRepository.list_by_workspace(workspace_id)


def _executive_report_or_404(report_id: str, user: dict) -> dict:
    check_permission(user, "view_executive")
    report = ExecutiveReportRepository.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Executive report not found.")
    _require_workspace_scope(user, report["workspace_id"])
    return report


@app.get("/executive/reports/{report_id}")
def get_executive_report(report_id: str, user: dict = Depends(require_auth)):
    return _executive_report_or_404(report_id, user)


@app.get("/executive/reports/{report_id}/export-markdown")
def export_executive_report(report_id: str, user: dict = Depends(require_auth)):
    saved = _executive_report_or_404(report_id, user)
    content = export_executive_report_markdown(saved.get("report", {}))
    log_audit_event("executive_report_exported", "executive_report", report_id, saved["title"], "success", "Info", "Executive report exported.", user=user, workspace=get_workspace(saved["workspace_id"]))
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=driftguard-executive-report-{report_id[:8]}.md"},
    )


@app.get("/demo/scenarios")
def demo_scenarios(user: dict = Depends(require_auth)):
    check_permission(user, "view_executive")
    return get_demo_scenarios()


@app.post("/demo/enable")
def enable_demo(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_demo_mode")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    try:
        state = enable_demo_mode(workspace_id, payload.get("scenario_name", "Payment API Drift Demo"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_audit_event("demo_mode_enabled", "demo_mode", resource_name=state["scenario_name"], status="success", severity="Medium", message="Demo mode enabled.", user=user, workspace=workspace)
    return state


@app.post("/demo/disable")
def disable_demo(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_demo_mode")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    state = disable_demo_mode(workspace_id)
    log_audit_event("demo_mode_disabled", "demo_mode", resource_name=state.get("scenario_name", ""), status="success", severity="Medium", message="Demo mode disabled.", user=user, workspace=workspace)
    return state


@app.get("/demo/state")
def demo_state(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_executive")
    _require_workspace_scope(user, workspace_id)
    return get_demo_state(workspace_id)


@app.post("/demo/advance-step")
def demo_advance_step(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_demo_mode")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    state = advance_demo_step(workspace_id)
    log_audit_event("demo_step_advanced", "demo_mode", resource_name=state.get("scenario_name", ""), status="success", severity="Info", message="Demo step advanced.", user=user, workspace=workspace, metadata={"current_step": state.get("current_step")})
    return state


@app.post("/demo/reset")
def demo_reset(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "reset_demo_data")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    state = reset_demo_data(workspace_id)
    log_audit_event("demo_data_reset", "demo_mode", resource_name="Demo Data", status="success", severity="High", message="Demo state reset without deleting user data.", user=user, workspace=workspace)
    return state


@app.post("/demo/seed-executive-demo")
def demo_seed_executive(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "manage_demo_mode")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    result = seed_executive_demo_data(workspace_id, user)
    log_audit_event("executive_demo_seeded", "demo_mode", resource_name="Executive Demo", status="success", severity="Medium", message="Executive demo data seeded.", user=user, workspace=workspace)
    return result


@app.post("/validation/run-real-dataset")
def validation_run_real_dataset(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "run_validation")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    log_audit_event("validation_run_started", "validation", resource_name=payload.get("name", "Real Dataset Validation"), status="success", severity="Info", message="Real dataset validation started.", user=user, workspace=workspace)
    try:
        result = run_real_dataset_validation(workspace_id, payload.get("dataset_id", ""), user.get("user_id", ""), payload.get("name", "Real Dataset Validation"))
    except Exception as exc:
        log_audit_event("validation_run_failed", "validation", status="failed", severity="High", message=str(exc), user=user, workspace=workspace)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_audit_event("validation_run_completed", "validation", result["validation_id"], result["name"], "success", "Medium", "Validation run completed.", user=user, workspace=workspace)
    return result


@app.post("/validation/run-full-system")
def validation_run_full_system(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "run_validation")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    result = run_full_system_validation(workspace_id, user.get("user_id", ""), payload.get("name", "Full DriftGuard System Validation"))
    log_audit_event("validation_run_completed", "validation", result["validation_id"], result["name"], "success", "Medium", "Full system validation completed.", user=user, workspace=workspace)
    return result


@app.post("/validation/run-demo-scenario")
def validation_run_demo_scenario(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "run_validation")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    result = run_demo_scenario_validation(workspace_id, payload.get("scenario_name", "Payment API Drift Demo"), user.get("user_id", ""))
    log_audit_event("validation_run_completed", "validation", result["validation_id"], result["name"], "success", "Medium", "Demo scenario validation completed.", user=user, workspace=workspace)
    return result


@app.get("/validation/runs")
def validation_runs(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_validation")
    _require_workspace_scope(user, workspace_id)
    return ValidationRunRepository.list_by_workspace(workspace_id)


def _validation_or_404(validation_id: str, user: dict) -> dict:
    check_permission(user, "view_validation")
    run = ValidationRunRepository.get_by_id(validation_id)
    if not run:
        raise HTTPException(status_code=404, detail="Validation run not found.")
    _require_workspace_scope(user, run["workspace_id"])
    run["steps"] = ValidationStepResultRepository.list_by_validation(validation_id)
    run["chart_data"] = build_chart_data(run.get("metrics", {}))
    return run


@app.get("/validation/runs/{validation_id}")
def validation_run_detail(validation_id: str, user: dict = Depends(require_auth)):
    return _validation_or_404(validation_id, user)


@app.delete("/validation/runs/{validation_id}")
def delete_validation_run(validation_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "delete_validation")
    run = _validation_or_404(validation_id, user)
    ValidationRunRepository.delete(validation_id)
    return {"status": "ok", "message": "Validation run deleted.", "validation_id": run["validation_id"]}


@app.post("/validation/runs/{validation_id}/research-report")
def validation_research_report(validation_id: str, user: dict = Depends(require_auth)):
    check_permission(user, "run_validation")
    run = _validation_or_404(validation_id, user)
    report = build_research_report(run["workspace_id"], validation_id)
    saved = save_research_report(run["workspace_id"], validation_id, report)
    log_audit_event("research_report_generated", "research_result", saved["research_result_id"], saved["title"], "success", "Medium", "Research report generated.", user=user, workspace=get_workspace(run["workspace_id"]))
    return saved


@app.get("/validation/runs/{validation_id}/research-report/export-markdown")
def export_validation_research_report(validation_id: str, user: dict = Depends(require_auth)):
    run = _validation_or_404(validation_id, user)
    report = build_research_report(run["workspace_id"], validation_id)
    log_audit_event("research_report_exported", "validation", validation_id, run["name"], "success", "Info", "Research report exported.", user=user, workspace=get_workspace(run["workspace_id"]))
    return Response(content=export_research_report_markdown(report), media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=driftguard-research-report-{validation_id[:8]}.md"})


@app.get("/validation/runs/{validation_id}/export-json")
def export_validation_json(validation_id: str, user: dict = Depends(require_auth)):
    run = _validation_or_404(validation_id, user)
    log_audit_event("validation_results_exported", "validation", validation_id, run["name"], "success", "Info", "Validation JSON exported.", user=user, workspace=get_workspace(run["workspace_id"]), metadata={"format": "json"})
    return Response(content=json.dumps(run, indent=2), media_type="application/json", headers={"Content-Disposition": f"attachment; filename=driftguard-validation-{validation_id[:8]}.json"})


@app.get("/validation/runs/{validation_id}/export-csv")
def export_validation_csv(validation_id: str, user: dict = Depends(require_auth)):
    run = _validation_or_404(validation_id, user)
    rows = ["section,metric,value"]
    for section, values in (run.get("metrics") or {}).items():
        if isinstance(values, dict):
            for key, value in values.items():
                rows.append(f"{section},{key},{value}")
    log_audit_event("validation_results_exported", "validation", validation_id, run["name"], "success", "Info", "Validation CSV exported.", user=user, workspace=get_workspace(run["workspace_id"]), metadata={"format": "csv"})
    return Response(content="\n".join(rows) + "\n", media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=driftguard-validation-{validation_id[:8]}.csv"})


@app.post("/validation/baseline-comparison")
def validation_baseline_comparison(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "run_validation")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    result = compare_baselines(workspace_id, payload.get("dataset_id", ""))
    log_audit_event("baseline_comparison_run", "validation", resource_name="Baseline Comparison", status="success", severity="Info", message="Baseline comparison run.", user=user, workspace=workspace)
    return result


@app.post("/validation/ablation-study")
def validation_ablation_study(payload: dict, user: dict = Depends(require_auth)):
    check_permission(user, "run_validation")
    workspace_id = payload.get("workspace_id", "")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    result = run_ablation_study(workspace_id, payload.get("dataset_id", ""), user.get("user_id", ""))
    log_audit_event("ablation_study_run", "validation", resource_name="Ablation Study", status="success", severity="Info", message="Ablation study run.", user=user, workspace=workspace)
    return result


@app.get("/validation/demo-readiness")
def validation_demo_readiness(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_validation")
    workspace = get_workspace(workspace_id)
    _require_workspace_scope(user, workspace_id)
    result = validate_demo_flow(workspace_id)
    log_audit_event("demo_readiness_checked", "validation", resource_name="Demo Readiness", status="success", severity="Info", message="Demo readiness checked.", user=user, workspace=workspace, metadata={"score": result["score"]})
    return result


@app.get("/validation/research-results")
def validation_research_results(workspace_id: str = Query(...), user: dict = Depends(require_auth)):
    check_permission(user, "view_validation")
    _require_workspace_scope(user, workspace_id)
    return ResearchResultRepository.list_by_workspace(workspace_id)
