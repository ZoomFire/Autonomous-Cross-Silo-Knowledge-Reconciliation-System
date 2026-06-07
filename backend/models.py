from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    documentation: str
    code: str
    jira: str
    commit: str
    logs: str
    database_config: str


class Claim(BaseModel):
    claim_id: str
    source: str
    entity: str
    claim_type: str
    claim_text: str
    confidence_score: float
    evidence: str


class TruthTriangle(BaseModel):
    requirement_view: list[Claim]
    implementation_view: list[Claim]
    runtime_view: list[Claim]


class DriftReport(BaseModel):
    drift_id: str
    entity: str
    summary: str
    drift_type: str
    severity: str
    confidence_score: float
    evidence: list[str]
    recommended_action: str
    status: str


class AnalysisResponse(BaseModel):
    claims: list[Claim]
    truth_triangle: TruthTriangle
    drift_report: DriftReport


class HistoryReport(BaseModel):
    id: int
    drift_id: str
    entity: str
    summary: str
    drift_type: str
    severity: str
    confidence_score: float
    recommended_action: str
    status: str
    created_at: str


class DatasetCase(BaseModel):
    case_id: str
    title: str
    documentation: str
    code: str
    jira: str
    commit: str
    logs: str
    database_config: str
    expected_label: str
    expected_drift_type: str
    expected_severity: str


class DatasetCaseResult(BaseModel):
    case_id: str
    title: str
    expected_label: str
    predicted_label: str
    expected_drift_type: str
    predicted_drift_type: str
    expected_severity: str
    predicted_severity: str
    is_correct_label: bool
    is_correct_drift_type: bool
    is_correct_severity: bool
    overall_correct: bool
    confidence_score: float
    explanation: str
    mismatch_reason: str
    evidence_sources: list[str]
    input: dict[str, str] = {}
    passed: bool
    summary: str


class DatasetQualityReport(BaseModel):
    total_cases: int
    valid_cases: int
    invalid_cases: int
    missing_field_warnings: list[str]
    empty_field_warnings: list[str]
    label_distribution: dict[str, int]
    drift_type_distribution: dict[str, int]
    severity_distribution: dict[str, int]
    quality_score: int


class DatasetEvaluationResponse(BaseModel):
    dataset_quality_report: DatasetQualityReport
    confusion_matrix: dict[str, dict[str, dict[str, int]]]
    summary_insights: list[str]
    total_cases: int
    correct_cases: int
    incorrect_cases: int
    passed: int
    failed: int
    accuracy: float
    label_accuracy: float
    drift_type_accuracy: float
    severity_accuracy: float
    contradiction_cases: int
    no_drift_cases: int
    manual_review_cases: int
    results: list[DatasetCaseResult]


class CaseFeedbackRequest(BaseModel):
    evaluation_id: str
    dataset_id: str
    case_id: str
    original_expected_label: str
    original_predicted_label: str
    corrected_label: str
    original_expected_drift_type: str
    original_predicted_drift_type: str
    corrected_drift_type: str
    original_expected_severity: str
    original_predicted_severity: str
    corrected_severity: str
    review_status: str
    reviewer_notes: str = ""
    correction_reason: str = ""


class CaseFeedbackResponse(CaseFeedbackRequest):
    feedback_id: str
    created_at: str
    updated_at: str
    is_prediction_correct_after_review: bool


class FeedbackSummaryResponse(BaseModel):
    evaluation_id: str
    total_cases: int
    reviewed_cases: int
    unreviewed_cases: int
    corrected_cases: int
    confirmed_correct_cases: int
    most_common_correction_type: str
    corrected_label_distribution: dict[str, int]
    corrected_drift_type_distribution: dict[str, int]
    corrected_severity_distribution: dict[str, int]
    human_review_completion_percentage: float


class CorrectedDatasetExportResponse(BaseModel):
    evaluation_id: str
    total_cases: int
    corrected_cases: int
    cases: list[DatasetCase]


class TrainingDatasetResponse(BaseModel):
    evaluation_id: str
    total_items: int
    items: list[dict]
