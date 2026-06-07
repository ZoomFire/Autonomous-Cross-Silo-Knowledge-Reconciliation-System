from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, Text

from .db import Base


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drift_id = Column(Text)
    entity = Column(Text)
    summary = Column(Text)
    drift_type = Column(Text)
    severity = Column(Text)
    confidence_score = Column(Float)
    recommended_action = Column(Text)
    status = Column(Text)
    evidence = Column(Text)
    created_at = Column(Text)


class User(Base):
    __tablename__ = "users"

    user_id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    salt = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    created_at = Column(Text)
    updated_at = Column(Text)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(Text)
    last_failed_login_at = Column(Text)
    last_login_at = Column(Text)


class Session(Base):
    __tablename__ = "sessions"

    token = Column(Text, primary_key=True)
    user_id = Column(Text, ForeignKey("users.user_id"))
    created_at = Column(Text)
    expires_at = Column(Text)


class Workspace(Base):
    __tablename__ = "workspaces"

    workspace_id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    created_by = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Text, index=True)
    user_id = Column(Text, index=True)
    role = Column(Text)
    created_at = Column(Text)


class Dataset(Base):
    __tablename__ = "datasets"

    dataset_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    filename = Column(Text)
    description = Column(Text)
    version = Column(Text)
    total_cases = Column(Integer)
    quality_score = Column(Float)
    metadata_json = Column(Text)
    cases_json = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class Evaluation(Base):
    __tablename__ = "evaluations"

    evaluation_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    dataset_id = Column(Text, index=True)
    dataset_name = Column(Text)
    total_cases = Column(Integer)
    accuracy = Column(Float)
    label_accuracy = Column(Float)
    drift_type_accuracy = Column(Float)
    severity_accuracy = Column(Float)
    quality_score = Column(Float)
    result_json = Column(Text)
    created_at = Column(Text)


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    evaluation_id = Column(Text, index=True)
    dataset_id = Column(Text)
    case_id = Column(Text)
    corrected_label = Column(Text)
    corrected_drift_type = Column(Text)
    corrected_severity = Column(Text)
    review_status = Column(Text)
    reviewer_notes = Column(Text)
    correction_reason = Column(Text)
    feedback_json = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class MonitoringRule(Base):
    __tablename__ = "monitoring_rules"

    rule_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    dataset_id = Column(Text, index=True)
    name = Column(Text)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    thresholds_json = Column(Text)
    alert_settings_json = Column(Text)
    rule_json = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    run_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    rule_id = Column(Text, index=True)
    dataset_id = Column(Text, index=True)
    dataset_name = Column(Text)
    status = Column(Text)
    evaluation_id = Column(Text)
    accuracy = Column(Float)
    critical_cases = Column(Integer)
    high_cases = Column(Integer)
    average_priority_score = Column(Float)
    alerts_created = Column(Integer)
    summary = Column(Text)
    run_json = Column(Text)
    created_at = Column(Text)


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    rule_id = Column(Text, index=True)
    run_id = Column(Text, index=True)
    dataset_id = Column(Text, index=True)
    dataset_name = Column(Text)
    status = Column(Text)
    alert_type = Column(Text)
    severity = Column(Text)
    title = Column(Text)
    message = Column(Text)
    metric_name = Column(Text)
    actual_value = Column(Float)
    threshold_value = Column(Float)
    recommended_action = Column(Text)
    related_evaluation_id = Column(Text)
    related_cases_json = Column(Text)
    alert_json = Column(Text)
    created_at = Column(Text)


class Connector(Base):
    __tablename__ = "connectors"

    connector_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    connector_type = Column(Text, index=True)
    status = Column(Text, index=True)
    config_json = Column(Text)
    created_by = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)
    last_sync_at = Column(Text)


class ImportedSource(Base):
    __tablename__ = "imported_sources"

    source_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    connector_id = Column(Text, index=True)
    source_type = Column(Text, index=True)
    source_name = Column(Text)
    source_path = Column(Text)
    source_url = Column(Text)
    content_text = Column(Text)
    content_hash = Column(Text, index=True)
    metadata_json = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class ConnectorSyncRun(Base):
    __tablename__ = "connector_sync_runs"

    sync_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    connector_id = Column(Text, index=True)
    connector_type = Column(Text)
    status = Column(Text, index=True)
    started_at = Column(Text)
    completed_at = Column(Text)
    files_imported = Column(Integer)
    files_skipped = Column(Integer)
    errors_json = Column(Text)
    summary = Column(Text)


class GeneratedDatasetCase(Base):
    __tablename__ = "generated_dataset_cases"

    generated_case_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    source_ids_json = Column(Text)
    case_json = Column(Text)
    created_at = Column(Text)
    created_by = Column(Text)


class BenchmarkDataset(Base):
    __tablename__ = "benchmark_datasets"

    benchmark_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    dataset_type = Column(Text, index=True)
    description = Column(Text)
    source_name = Column(Text)
    source_url = Column(Text)
    status = Column(Text, index=True)
    total_examples = Column(Integer)
    imported_examples = Column(Integer)
    created_by = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class BenchmarkImportRun(Base):
    __tablename__ = "benchmark_import_runs"

    import_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    benchmark_id = Column(Text, index=True)
    dataset_type = Column(Text, index=True)
    status = Column(Text, index=True)
    started_at = Column(Text)
    completed_at = Column(Text)
    examples_processed = Column(Integer)
    examples_imported = Column(Integer)
    examples_skipped = Column(Integer)
    errors_json = Column(Text)
    summary = Column(Text)


class BenchmarkExample(Base):
    __tablename__ = "benchmark_examples"

    example_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    benchmark_id = Column(Text, index=True)
    dataset_type = Column(Text, index=True)
    original_id = Column(Text)
    input_json = Column(Text)
    target_json = Column(Text)
    driftguard_case_json = Column(Text)
    split = Column(Text, index=True)
    quality_score = Column(Float)
    metadata_json = Column(Text)
    created_at = Column(Text)


class TrainingDatasetExport(Base):
    __tablename__ = "training_dataset_exports"

    export_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    description = Column(Text)
    format = Column(Text)
    total_examples = Column(Integer)
    train_count = Column(Integer)
    validation_count = Column(Integer)
    test_count = Column(Integer)
    included_dataset_types_json = Column(Text)
    export_path = Column(Text)
    created_by = Column(Text)
    created_at = Column(Text)


class ModelExperiment(Base):
    __tablename__ = "model_experiments"

    experiment_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    task_type = Column(Text, index=True)
    model_type = Column(Text, index=True)
    dataset_source = Column(Text)
    training_export_id = Column(Text, index=True)
    benchmark_ids_json = Column(Text)
    status = Column(Text, index=True)
    total_examples = Column(Integer)
    train_count = Column(Integer)
    validation_count = Column(Integer)
    test_count = Column(Integer)
    accuracy = Column(Float)
    precision_macro = Column(Float)
    recall_macro = Column(Float)
    f1_macro = Column(Float)
    confusion_matrix_json = Column(Text)
    label_distribution_json = Column(Text)
    metrics_json = Column(Text)
    training_log_json = Column(Text)
    created_by = Column(Text)
    created_at = Column(Text)
    completed_at = Column(Text)


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"

    artifact_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    experiment_id = Column(Text, index=True)
    model_path = Column(Text)
    vectorizer_path = Column(Text)
    metadata_path = Column(Text)
    model_type = Column(Text, index=True)
    task_type = Column(Text, index=True)
    created_at = Column(Text)


class DeployedModel(Base):
    __tablename__ = "deployed_models"

    deployed_model_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    task_type = Column(Text, index=True)
    experiment_id = Column(Text, index=True)
    artifact_id = Column(Text, index=True)
    model_type = Column(Text)
    status = Column(Text, index=True)
    deployed_by = Column(Text)
    deployed_at = Column(Text)


class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    title = Column(Text)
    description = Column(Text)
    severity = Column(Text, index=True)
    status = Column(Text, index=True)
    source_type = Column(Text, index=True)
    source_id = Column(Text, index=True)
    related_alert_id = Column(Text, index=True)
    related_evaluation_id = Column(Text, index=True)
    related_model_experiment_id = Column(Text, index=True)
    related_active_learning_item_id = Column(Text, index=True)
    assigned_to = Column(Text, index=True)
    created_by = Column(Text, index=True)
    sla_due_at = Column(Text)
    resolved_at = Column(Text)
    closed_at = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)
    metadata_json = Column(Text)


class IncidentComment(Base):
    __tablename__ = "incident_comments"

    comment_id = Column(Text, primary_key=True)
    incident_id = Column(Text, index=True)
    workspace_id = Column(Text, index=True)
    user_id = Column(Text, index=True)
    comment_text = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class IncidentTimelineEvent(Base):
    __tablename__ = "incident_timeline_events"

    timeline_event_id = Column(Text, primary_key=True)
    incident_id = Column(Text, index=True)
    workspace_id = Column(Text, index=True)
    event_type = Column(Text, index=True)
    actor_user_id = Column(Text, index=True)
    message = Column(Text)
    metadata_json = Column(Text)
    created_at = Column(Text)


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    webhook_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    url = Column(Text)
    event_types_json = Column(Text)
    enabled = Column(Boolean, default=True)
    secret_masked = Column(Text)
    created_by = Column(Text, index=True)
    created_at = Column(Text)
    updated_at = Column(Text)


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    template_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    event_type = Column(Text, index=True)
    subject_template = Column(Text)
    body_template = Column(Text)
    created_by = Column(Text, index=True)
    created_at = Column(Text)
    updated_at = Column(Text)


class NotificationDeliveryLog(Base):
    __tablename__ = "notification_delivery_logs"

    delivery_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    webhook_id = Column(Text, index=True)
    incident_id = Column(Text, index=True)
    event_type = Column(Text, index=True)
    status = Column(Text, index=True)
    request_payload_json = Column(Text)
    response_status_code = Column(Integer)
    response_text = Column(Text)
    error_message = Column(Text)
    created_at = Column(Text)


class EscalationRule(Base):
    __tablename__ = "escalation_rules"

    rule_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    enabled = Column(Boolean, default=True)
    severity = Column(Text, index=True)
    status_filter = Column(Text, index=True)
    escalate_after_minutes = Column(Integer)
    target_role = Column(Text)
    target_user_id = Column(Text, index=True)
    webhook_enabled = Column(Boolean, default=True)
    created_by = Column(Text, index=True)
    created_at = Column(Text)
    updated_at = Column(Text)


class ExternalIntegration(Base):
    __tablename__ = "external_integrations"

    integration_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    integration_type = Column(Text, index=True)
    mode = Column(Text, index=True)
    enabled = Column(Boolean, default=True)
    config_json = Column(Text)
    secret_masked = Column(Text)
    created_by = Column(Text, index=True)
    created_at = Column(Text)
    updated_at = Column(Text)
    last_health_check_at = Column(Text)
    last_health_status = Column(Text, index=True)


class ExternalSyncRecord(Base):
    __tablename__ = "external_sync_records"

    sync_record_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    integration_id = Column(Text, index=True)
    integration_type = Column(Text, index=True)
    source_type = Column(Text, index=True)
    source_id = Column(Text, index=True)
    action = Column(Text, index=True)
    status = Column(Text, index=True)
    request_payload_json = Column(Text)
    response_payload_json = Column(Text)
    external_id = Column(Text, index=True)
    external_url = Column(Text)
    error_message = Column(Text)
    created_at = Column(Text)


class ExternalLinkedResource(Base):
    __tablename__ = "external_linked_resources"

    linked_resource_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    integration_id = Column(Text, index=True)
    source_type = Column(Text, index=True)
    source_id = Column(Text, index=True)
    external_type = Column(Text, index=True)
    external_id = Column(Text, index=True)
    external_url = Column(Text)
    external_status = Column(Text, index=True)
    created_at = Column(Text)
    updated_at = Column(Text)


class MockExternalTicket(Base):
    __tablename__ = "mock_external_tickets"

    mock_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    integration_id = Column(Text, index=True)
    external_type = Column(Text, index=True)
    title = Column(Text)
    description = Column(Text)
    severity = Column(Text, index=True)
    status = Column(Text, index=True)
    source_type = Column(Text, index=True)
    source_id = Column(Text, index=True)
    external_id = Column(Text, index=True)
    external_url = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class ExecutiveReport(Base):
    __tablename__ = "executive_reports"

    report_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    title = Column(Text)
    report_json = Column(Text)
    created_by = Column(Text, index=True)
    created_at = Column(Text)


class DemoModeState(Base):
    __tablename__ = "demo_mode_state"

    demo_state_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    enabled = Column(Boolean, default=False)
    scenario_name = Column(Text)
    current_step = Column(Integer)
    completed_steps_json = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    validation_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    validation_type = Column(Text, index=True)
    status = Column(Text, index=True)
    dataset_id = Column(Text, index=True)
    scenario_name = Column(Text)
    started_by = Column(Text, index=True)
    started_at = Column(Text)
    completed_at = Column(Text)
    summary_json = Column(Text)
    metrics_json = Column(Text)
    report_json = Column(Text)


class ValidationStepResult(Base):
    __tablename__ = "validation_step_results"

    step_result_id = Column(Text, primary_key=True)
    validation_id = Column(Text, index=True)
    workspace_id = Column(Text, index=True)
    step_name = Column(Text)
    status = Column(Text, index=True)
    input_json = Column(Text)
    output_json = Column(Text)
    metrics_json = Column(Text)
    error_message = Column(Text)
    started_at = Column(Text)
    completed_at = Column(Text)


class ResearchResult(Base):
    __tablename__ = "research_results"

    research_result_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    validation_id = Column(Text, index=True)
    result_type = Column(Text, index=True)
    title = Column(Text)
    result_json = Column(Text)
    created_at = Column(Text)


class AblationStudyResult(Base):
    __tablename__ = "ablation_study_results"

    ablation_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    validation_id = Column(Text, index=True)
    experiment_name = Column(Text)
    configuration_name = Column(Text)
    enabled_modules_json = Column(Text)
    disabled_modules_json = Column(Text)
    metrics_json = Column(Text)
    created_at = Column(Text)


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    chunk_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    source_id = Column(Text, index=True)
    connector_id = Column(Text, index=True)
    source_type = Column(Text, index=True)
    source_name = Column(Text)
    chunk_index = Column(Integer)
    chunk_text = Column(Text)
    token_count = Column(Integer)
    keywords_json = Column(Text)
    metadata_json = Column(Text)
    created_at = Column(Text)


class SearchQuery(Base):
    __tablename__ = "search_queries"

    query_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    user_id = Column(Text, index=True)
    query_text = Column(Text)
    filters_json = Column(Text)
    answer_json = Column(Text)
    created_at = Column(Text)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    run_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    user_id = Column(Text, index=True)
    goal = Column(Text)
    status = Column(Text, index=True)
    plan_json = Column(Text)
    final_report_json = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)
    completed_at = Column(Text)


class AgentStep(Base):
    __tablename__ = "agent_steps"

    step_id = Column(Text, primary_key=True)
    run_id = Column(Text, index=True)
    workspace_id = Column(Text, index=True)
    step_index = Column(Integer)
    step_name = Column(Text)
    tool_name = Column(Text)
    status = Column(Text, index=True)
    input_json = Column(Text)
    output_json = Column(Text)
    error_message = Column(Text)
    started_at = Column(Text)
    completed_at = Column(Text)


class LLMSettings(Base):
    __tablename__ = "llm_settings"

    settings_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    provider = Column(Text, index=True)
    model_name = Column(Text)
    reasoning_mode = Column(Text, index=True)
    api_key_masked = Column(Text)
    config_json = Column(Text)
    enabled = Column(Boolean, default=True)
    created_at = Column(Text)
    updated_at = Column(Text)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    template_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    name = Column(Text)
    task_type = Column(Text, index=True)
    template_text = Column(Text)
    variables_json = Column(Text)
    created_by = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)


class ReasoningTrace(Base):
    __tablename__ = "reasoning_traces"

    trace_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    user_id = Column(Text, index=True)
    task_type = Column(Text, index=True)
    reasoning_mode = Column(Text, index=True)
    provider = Column(Text, index=True)
    input_summary = Column(Text)
    local_output_json = Column(Text)
    llm_output_json = Column(Text)
    final_output_json = Column(Text)
    validation_result_json = Column(Text)
    status = Column(Text, index=True)
    error_message = Column(Text)
    created_at = Column(Text)


class HybridAnalysisResult(Base):
    __tablename__ = "hybrid_analysis_results"

    result_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    trace_id = Column(Text, index=True)
    task_type = Column(Text, index=True)
    source_context_json = Column(Text)
    local_result_json = Column(Text)
    llm_result_json = Column(Text)
    comparison_json = Column(Text)
    final_result_json = Column(Text)
    approved_by_user = Column(Boolean, default=False)
    approval_status = Column(Text, index=True)
    created_at = Column(Text)
    updated_at = Column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_id = Column(Text, primary_key=True)
    workspace_id = Column(Text, index=True)
    workspace_name = Column(Text)
    user_id = Column(Text, index=True)
    user_name = Column(Text)
    user_email = Column(Text)
    user_role = Column(Text)
    action = Column(Text, index=True)
    resource_type = Column(Text, index=True)
    resource_id = Column(Text)
    resource_name = Column(Text)
    status = Column(Text, index=True)
    severity = Column(Text, index=True)
    message = Column(Text)
    metadata_json = Column(Text)
    created_at = Column(Text)
