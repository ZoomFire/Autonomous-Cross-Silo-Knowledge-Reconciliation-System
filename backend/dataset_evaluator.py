import json
from pathlib import Path

from claim_extractor import build_truth_triangle, extract_claims, extract_entity
from drift_detector import detect_drift
from models import (
    AnalysisRequest,
    DatasetCase,
    DatasetCaseResult,
    DatasetEvaluationResponse,
    DatasetQualityReport,
)


DATASET_PATH = Path(__file__).resolve().parent / "sample_dataset.json"

COMPATIBLE_DRIFT_TYPES = {
    ("Documentation Drift", "Configuration Drift"),
    ("Configuration Drift", "Documentation Drift"),
    ("Implementation Drift", "Security Drift"),
    ("Security Drift", "Implementation Drift"),
    ("Operational Drift", "Security Drift"),
    ("Security Drift", "Operational Drift"),
}

DATASET_FIELDS = [
    "case_id",
    "title",
    "documentation",
    "code",
    "jira",
    "commit",
    "logs",
    "database_config",
    "expected_label",
    "expected_drift_type",
    "expected_severity",
]


def load_sample_dataset() -> list[DatasetCase]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Sample dataset not found at {DATASET_PATH}")

    with DATASET_PATH.open("r", encoding="utf-8") as dataset_file:
        raw_cases = json.load(dataset_file)

    return [DatasetCase(**case) for case in raw_cases]


def is_drift_type_compatible(expected: str, predicted: str) -> bool:
    return expected == predicted or (expected, predicted) in COMPATIBLE_DRIFT_TYPES


def _distribution(values: list[str]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for value in values:
        key = value or "Unknown"
        distribution[key] = distribution.get(key, 0) + 1
    return distribution


def validate_dataset_quality(cases: list[DatasetCase]) -> DatasetQualityReport:
    missing_field_warnings: list[str] = []
    empty_field_warnings: list[str] = []

    for dataset_case in cases:
        case_data = dataset_case.model_dump()
        for field in DATASET_FIELDS:
            if field not in case_data:
                missing_field_warnings.append(f"{dataset_case.case_id}: missing {field}")
            elif isinstance(case_data[field], str) and not case_data[field].strip():
                empty_field_warnings.append(f"{dataset_case.case_id}: empty {field}")

    label_distribution = _distribution([case.expected_label for case in cases])
    drift_type_distribution = _distribution([case.expected_drift_type for case in cases])
    severity_distribution = _distribution([case.expected_severity for case in cases])

    quality_score = 100
    quality_score -= 5 * len(empty_field_warnings)
    if len(cases) < 3:
        quality_score -= 10
    if len(label_distribution) == 1 and cases:
        quality_score -= 10
    if len(severity_distribution) == 1 and cases:
        quality_score -= 10

    return DatasetQualityReport(
        total_cases=len(cases),
        valid_cases=len(cases),
        invalid_cases=0,
        missing_field_warnings=missing_field_warnings,
        empty_field_warnings=empty_field_warnings,
        label_distribution=label_distribution,
        drift_type_distribution=drift_type_distribution,
        severity_distribution=severity_distribution,
        quality_score=max(0, quality_score),
    )


def _predict_label(drift_type: str, recommended_action: str, confidence_score: float, claim_count: int, entity: str) -> str:
    if recommended_action == "Manual review required":
        return "manual_review"
    if entity == "unknown_entity":
        return "manual_review"
    if drift_type != "No Drift":
        return "manual_review" if confidence_score <= 0.65 else "contradiction"
    if claim_count < 2:
        return "manual_review"
    return "match"


def _analyze_case(dataset_case: DatasetCase):
    request = AnalysisRequest(
        documentation=dataset_case.documentation,
        code=dataset_case.code,
        jira=dataset_case.jira,
        commit=dataset_case.commit,
        logs=dataset_case.logs,
        database_config=dataset_case.database_config,
    )
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
    predicted_label = _predict_label(
        drift_report.drift_type,
        drift_report.recommended_action,
        drift_report.confidence_score,
        len(claims),
        entity,
    )
    return claims, drift_report, predicted_label


def evaluate_single_case(dataset_case: DatasetCase) -> DatasetCaseResult:
    try:
        claims, drift_report, predicted_label = _analyze_case(dataset_case)
        label_matches = predicted_label == dataset_case.expected_label
        drift_type_matches = dataset_case.expected_drift_type == drift_report.drift_type
        severity_matches = dataset_case.expected_severity == drift_report.severity
        passed = label_matches and drift_type_matches and severity_matches
        evidence_sources = sorted({claim.source for claim in claims})
        summary = (
            f"Predicted {predicted_label} from {len(claims)} claims. "
            f"Detector returned {drift_report.drift_type} with {drift_report.severity} severity."
        )
        explanation = (
            f"The evaluator extracted {len(claims)} claims from "
            f"{', '.join(evidence_sources) if evidence_sources else 'no evidence sources'} and produced "
            f"{predicted_label}, {drift_report.drift_type}, {drift_report.severity}."
        )
        mismatch_reason = _build_mismatch_reason(
            dataset_case,
            predicted_label,
            drift_report.drift_type,
            drift_report.severity,
            label_matches,
            drift_type_matches,
            severity_matches,
        )
        return DatasetCaseResult(
            case_id=dataset_case.case_id,
            title=dataset_case.title,
            expected_label=dataset_case.expected_label,
            predicted_label=predicted_label,
            expected_drift_type=dataset_case.expected_drift_type,
            predicted_drift_type=drift_report.drift_type,
            expected_severity=dataset_case.expected_severity,
            predicted_severity=drift_report.severity,
            is_correct_label=label_matches,
            is_correct_drift_type=drift_type_matches,
            is_correct_severity=severity_matches,
            overall_correct=passed,
            confidence_score=drift_report.confidence_score,
            explanation=explanation,
            mismatch_reason=mismatch_reason,
            evidence_sources=evidence_sources,
            input={
                "documentation": dataset_case.documentation,
                "code": dataset_case.code,
                "jira": dataset_case.jira,
                "commit": dataset_case.commit,
                "logs": dataset_case.logs,
                "database_config": dataset_case.database_config,
            },
            passed=passed,
            summary=summary,
        )
    except Exception as exc:
        return DatasetCaseResult(
            case_id=dataset_case.case_id,
            title=dataset_case.title,
            expected_label=dataset_case.expected_label,
            predicted_label="evaluation_error",
            expected_drift_type=dataset_case.expected_drift_type,
            predicted_drift_type="Evaluation Error",
            expected_severity=dataset_case.expected_severity,
            predicted_severity="Evaluation Error",
            is_correct_label=False,
            is_correct_drift_type=False,
            is_correct_severity=False,
            overall_correct=False,
            confidence_score=0.0,
            explanation="The evaluator could not complete this case.",
            mismatch_reason=f"Evaluation failed for this case: {exc}",
            evidence_sources=[],
            input={
                "documentation": dataset_case.documentation,
                "code": dataset_case.code,
                "jira": dataset_case.jira,
                "commit": dataset_case.commit,
                "logs": dataset_case.logs,
                "database_config": dataset_case.database_config,
            },
            passed=False,
            summary=f"Evaluation failed for this case: {exc}",
        )


def _build_mismatch_reason(
    dataset_case: DatasetCase,
    predicted_label: str,
    predicted_drift_type: str,
    predicted_severity: str,
    label_matches: bool,
    drift_type_matches: bool,
    severity_matches: bool,
) -> str:
    reasons: list[str] = []
    if not label_matches:
        reasons.append(f"Expected label was {dataset_case.expected_label} but predicted {predicted_label}.")
    if not drift_type_matches:
        compatible_note = ""
        if is_drift_type_compatible(dataset_case.expected_drift_type, predicted_drift_type):
            compatible_note = " The predicted drift type is compatible, but not an exact Level 2.2 match."
        reasons.append(
            f"Expected drift type was {dataset_case.expected_drift_type} but predicted {predicted_drift_type}.{compatible_note}"
        )
    if not severity_matches:
        reasons.append(
            f"Expected severity was {dataset_case.expected_severity} but predicted {predicted_severity}."
        )
    return " ".join(reasons) if reasons else "No mismatch detected."


def build_confusion_matrix(results: list[DatasetCaseResult]) -> dict[str, dict[str, dict[str, int]]]:
    matrix = {"labels": {}, "severity": {}, "drift_type": {}}

    def add(section: str, expected: str, predicted: str):
        expected_key = expected or "Unknown"
        predicted_key = predicted or "Unknown"
        matrix[section].setdefault(expected_key, {})
        matrix[section][expected_key][predicted_key] = matrix[section][expected_key].get(predicted_key, 0) + 1

    for result in results:
        add("labels", result.expected_label, result.predicted_label)
        add("severity", result.expected_severity, result.predicted_severity)
        add("drift_type", result.expected_drift_type, result.predicted_drift_type)

    return matrix


def _accuracy(correct_count: int, total_count: int) -> float:
    return round((correct_count / total_count) * 100, 2) if total_count else 0.0


def generate_summary_insights(
    results: list[DatasetCaseResult],
    dataset_quality_report: DatasetQualityReport,
    confusion_matrix: dict[str, dict[str, dict[str, int]]],
) -> list[str]:
    total_cases = len(results)
    label_accuracy = _accuracy(sum(result.is_correct_label for result in results), total_cases)
    drift_accuracy = _accuracy(sum(result.is_correct_drift_type for result in results), total_cases)
    severity_accuracy = _accuracy(sum(result.is_correct_severity for result in results), total_cases)
    insights: list[str] = []

    if label_accuracy >= 85:
        insights.append("Model performs well on label classification across this dataset.")
    else:
        insights.append("Model struggles with contradiction versus no-drift label classification.")

    if severity_accuracy < label_accuracy:
        insights.append("Most remaining risk is in severity classification rather than basic drift detection.")
    if drift_accuracy < label_accuracy:
        insights.append("Drift type classification is less reliable than label classification for this dataset.")

    if dataset_quality_report.quality_score >= 80:
        insights.append("Dataset quality is good, with enough signal for useful evaluation.")
    else:
        insights.append("Dataset quality needs improvement; add more complete and diverse cases.")

    if len(dataset_quality_report.drift_type_distribution) < 3:
        insights.append("More diverse drift types are recommended for stronger benchmark coverage.")

    severity_matrix = confusion_matrix.get("severity", {})
    critical_predictions = severity_matrix.get("Critical", {})
    if any(predicted != "Critical" and count > 0 for predicted, count in critical_predictions.items()):
        insights.append("Critical severity cases are sometimes predicted as a lower severity.")

    return insights


def evaluate_dataset_cases(dataset_cases: list[DatasetCase]) -> DatasetEvaluationResponse:
    results = [evaluate_single_case(dataset_case) for dataset_case in dataset_cases]

    quality_report = validate_dataset_quality(dataset_cases)
    confusion_matrix = build_confusion_matrix(results)
    summary_insights = generate_summary_insights(results, quality_report, confusion_matrix)
    passed_count = sum(1 for result in results if result.overall_correct)
    total_cases = len(results)
    label_correct = sum(1 for result in results if result.is_correct_label)
    drift_correct = sum(1 for result in results if result.is_correct_drift_type)
    severity_correct = sum(1 for result in results if result.is_correct_severity)

    return DatasetEvaluationResponse(
        dataset_quality_report=quality_report,
        confusion_matrix=confusion_matrix,
        summary_insights=summary_insights,
        total_cases=total_cases,
        correct_cases=passed_count,
        incorrect_cases=total_cases - passed_count,
        passed=passed_count,
        failed=total_cases - passed_count,
        accuracy=_accuracy(passed_count, total_cases),
        label_accuracy=_accuracy(label_correct, total_cases),
        drift_type_accuracy=_accuracy(drift_correct, total_cases),
        severity_accuracy=_accuracy(severity_correct, total_cases),
        contradiction_cases=sum(1 for case in dataset_cases if case.expected_label == "contradiction"),
        no_drift_cases=sum(1 for case in dataset_cases if case.expected_label == "match"),
        manual_review_cases=sum(1 for case in dataset_cases if case.expected_label == "manual_review"),
        results=results,
    )


def evaluate_dataset() -> DatasetEvaluationResponse:
    return evaluate_dataset_cases(load_sample_dataset())


def evaluation_to_markdown(evaluation: DatasetEvaluationResponse) -> str:
    def distribution_to_text(distribution: dict[str, int]) -> str:
        return ", ".join(f"{key}: {value}" for key, value in distribution.items()) or "None"

    def matrix_to_markdown(title: str, matrix: dict[str, dict[str, int]]) -> list[str]:
        columns = sorted({predicted for row in matrix.values() for predicted in row.keys()})
        lines = [f"### {title}"]
        if not matrix or not columns:
            lines.append("No matrix data available.")
            return lines
        lines.append("| Expected | " + " | ".join(columns) + " |")
        lines.append("| --- | " + " | ".join("---" for _ in columns) + " |")
        for expected, predictions in sorted(matrix.items()):
            values = [str(predictions.get(column, 0)) for column in columns]
            lines.append("| " + expected + " | " + " | ".join(values) + " |")
        return lines

    quality = evaluation.dataset_quality_report
    lines = [
        "# DriftGuard AI Dataset Evaluation Report",
        "",
        "## Summary",
        f"- Total cases: {evaluation.total_cases}",
        f"- Correct cases: {evaluation.correct_cases}",
        f"- Incorrect cases: {evaluation.incorrect_cases}",
        f"- Accuracy: {evaluation.accuracy}%",
        f"- Label accuracy: {evaluation.label_accuracy}%",
        f"- Drift type accuracy: {evaluation.drift_type_accuracy}%",
        f"- Severity accuracy: {evaluation.severity_accuracy}%",
        "",
        "## Dataset Quality Report",
        f"- Quality score: {quality.quality_score}",
        f"- Total cases: {quality.total_cases}",
        f"- Label distribution: {distribution_to_text(quality.label_distribution)}",
        f"- Drift type distribution: {distribution_to_text(quality.drift_type_distribution)}",
        f"- Severity distribution: {distribution_to_text(quality.severity_distribution)}",
        "",
        "## Summary Insights",
    ]
    lines.extend(f"- {insight}" for insight in evaluation.summary_insights)
    lines.extend(["", "## Confusion Matrix"])
    lines.extend(matrix_to_markdown("Label Confusion Matrix", evaluation.confusion_matrix.get("labels", {})))
    lines.append("")
    lines.extend(matrix_to_markdown("Drift Type Confusion Matrix", evaluation.confusion_matrix.get("drift_type", {})))
    lines.append("")
    lines.extend(matrix_to_markdown("Severity Confusion Matrix", evaluation.confusion_matrix.get("severity", {})))
    lines.extend(["", "## Case Results"])

    for result in evaluation.results:
        lines.extend(
            [
                f"### {result.case_id} - {result.title}",
                f"- Expected label: {result.expected_label}",
                f"- Predicted label: {result.predicted_label}",
                f"- Expected drift type: {result.expected_drift_type}",
                f"- Predicted drift type: {result.predicted_drift_type}",
                f"- Expected severity: {result.expected_severity}",
                f"- Predicted severity: {result.predicted_severity}",
                f"- Overall correct: {result.overall_correct}",
                f"- Confidence score: {result.confidence_score}",
                f"- Explanation: {result.explanation}",
                f"- Mismatch reason: {result.mismatch_reason}",
                f"- Evidence sources: {', '.join(result.evidence_sources) if result.evidence_sources else 'None'}",
                "",
            ]
        )

    return "\n".join(lines)
