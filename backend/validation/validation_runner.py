from datetime import datetime, timezone
from uuid import uuid4

from database.repositories import DatasetRepository, EvaluationRepository, IncidentRepository, ValidationRunRepository, ValidationStepResultRepository
from dataset_evaluator import evaluate_dataset_cases
from executive.report_builder import build_executive_report
from incidents.incident_service import create_incident
from models import DatasetCase
from root_cause_analyzer import build_root_cause_report
from drift_timeline import build_evaluation_timeline
from impact_graph import build_evaluation_impact_graph

from .chart_data_builder import build_chart_data
from .metrics_aggregator import aggregate_validation_metrics


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _step(validation_id: str, workspace_id: str, name: str, status: str, output: dict | None = None, metrics: dict | None = None, error: str = "") -> dict:
    now = utc_now()
    return ValidationStepResultRepository.create({
        "step_result_id": str(uuid4()),
        "validation_id": validation_id,
        "workspace_id": workspace_id,
        "step_name": name,
        "status": status,
        "output": output or {},
        "metrics": metrics or {},
        "error_message": error,
        "started_at": now,
        "completed_at": now,
    })


def _save_run(validation_id: str, workspace_id: str, name: str, validation_type: str, status: str, user_id: str, dataset_id: str = "", scenario_name: str = "", summary: dict | None = None, metrics: dict | None = None, report: dict | None = None, started_at: str | None = None) -> dict:
    return ValidationRunRepository.create({
        "validation_id": validation_id,
        "workspace_id": workspace_id,
        "name": name,
        "validation_type": validation_type,
        "status": status,
        "dataset_id": dataset_id,
        "scenario_name": scenario_name,
        "started_by": user_id,
        "started_at": started_at or utc_now(),
        "completed_at": utc_now(),
        "summary": summary or {},
        "metrics": metrics or {},
        "report": report or {},
    })


def _normalize_dataset_cases(cases: list[dict | DatasetCase]) -> list[DatasetCase]:
    return [case if isinstance(case, DatasetCase) else DatasetCase(**case) for case in cases]


def run_real_dataset_validation(workspace_id: str, dataset_id: str, user_id: str, name: str = "Real Dataset Validation", validation_type: str = "real_dataset", scenario_name: str = "") -> dict:
    validation_id = str(uuid4())
    started = utc_now()
    steps = []
    dataset = DatasetRepository.get_by_id(dataset_id)
    if not dataset:
        run = _save_run(validation_id, workspace_id, name, validation_type, "failed", user_id, dataset_id=dataset_id, scenario_name=scenario_name, summary={"error": "Dataset not found."}, started_at=started)
        steps.append(_step(validation_id, workspace_id, "Load dataset", "failed", error="Dataset not found."))
        return {**run, "steps": steps}
    dataset_cases = _normalize_dataset_cases(dataset.get("cases", []))
    steps.append(_step(validation_id, workspace_id, "Load dataset", "completed", {"case_count": len(dataset_cases)}))
    evaluation = evaluate_dataset_cases(dataset_cases)
    eval_payload = {
        "evaluation_id": str(uuid4()),
        "workspace_id": workspace_id,
        "dataset_id": dataset_id,
        "dataset_name": dataset.get("metadata", {}).get("name", "Validation dataset"),
        "total_cases": evaluation.total_cases,
        "accuracy": evaluation.accuracy,
        "label_accuracy": evaluation.label_accuracy,
        "drift_type_accuracy": evaluation.drift_type_accuracy,
        "severity_accuracy": evaluation.severity_accuracy,
        "quality_score": evaluation.dataset_quality_report.quality_score,
        "result": evaluation.model_dump(),
        "created_at": utc_now(),
    }
    EvaluationRepository.create(eval_payload)
    steps.append(_step(validation_id, workspace_id, "Run dataset evaluation", "completed", eval_payload, {"accuracy": evaluation.accuracy}))
    root_cause = build_root_cause_report(evaluation.model_dump(), validation_id)
    timeline = build_evaluation_timeline(evaluation.model_dump(), validation_id)
    impact = build_evaluation_impact_graph(evaluation.model_dump(), validation_id)
    steps.append(_step(validation_id, workspace_id, "Generate root cause report", "completed", root_cause))
    steps.append(_step(validation_id, workspace_id, "Generate drift timeline", "completed", timeline))
    steps.append(_step(validation_id, workspace_id, "Generate impact graph", "completed", impact))
    created_incidents = 0
    for case in evaluation.results:
        if case.predicted_severity in {"Critical", "High"}:
            create_incident({
                "workspace_id": workspace_id,
                "title": f"Validation drift: {case.title}",
                "description": case.reason,
                "severity": case.predicted_severity,
                "source_type": "validation",
                "source_id": validation_id,
                "metadata": {"demo": True, "validation_id": validation_id},
            }, {"user_id": user_id})
            created_incidents += 1
    steps.append(_step(validation_id, workspace_id, "Create incidents for high-risk drift", "completed", {"incidents_created": created_incidents}))
    executive_report = build_executive_report(workspace_id, user_id)
    outputs = {"workspace_id": workspace_id, "evaluation": eval_payload, "root_cause": root_cause, "timeline": timeline, "impact_graph": impact, "incidents_created": created_incidents, "executive_report": executive_report}
    metrics = aggregate_validation_metrics(outputs)
    chart_data = build_chart_data(metrics)
    report = {"outputs": outputs, "chart_data": chart_data}
    summary = {"accuracy": evaluation.accuracy, "drift_cases": metrics["drift"]["total_drift_cases"], "incidents_created": created_incidents, "estimated_total_value": metrics["business"]["estimated_total_value"]}
    run = _save_run(
        validation_id,
        workspace_id,
        name,
        validation_type,
        "completed",
        user_id,
        dataset_id=dataset_id,
        scenario_name=scenario_name,
        summary=summary,
        metrics=metrics,
        report=report,
        started_at=started,
    )
    return {**run, "steps": steps, "chart_data": chart_data}


def run_full_system_validation(workspace_id: str, user_id: str, name: str = "Full DriftGuard System Validation") -> dict:
    validation_id = str(uuid4())
    started = utc_now()
    datasets = DatasetRepository.list(workspace_id)
    steps = [_step(validation_id, workspace_id, "Check datasets", "completed" if datasets else "partial", {"datasets": len(datasets)})]
    if datasets:
        return run_real_dataset_validation(workspace_id, datasets[0]["dataset_id"], user_id, name, validation_type="full_system")
    executive_report = build_executive_report(workspace_id, user_id)
    outputs = {"workspace_id": workspace_id, "executive_report": executive_report}
    metrics = aggregate_validation_metrics(outputs)
    chart_data = build_chart_data(metrics)
    summary = {"message": "Full system validation completed partially because no dataset is available.", "estimated_total_value": metrics["business"]["estimated_total_value"]}
    run = _save_run(validation_id, workspace_id, name, "full_system", "partial", user_id, summary=summary, metrics=metrics, report={"chart_data": chart_data}, started_at=started)
    return {**run, "steps": steps, "chart_data": chart_data}


def run_demo_scenario_validation(workspace_id: str, scenario_name: str, user_id: str) -> dict:
    datasets = DatasetRepository.list(workspace_id)
    if datasets:
        return run_real_dataset_validation(workspace_id, datasets[0]["dataset_id"], user_id, f"{scenario_name} Validation", validation_type="demo_scenario", scenario_name=scenario_name)
    result = run_full_system_validation(workspace_id, user_id, f"{scenario_name} Validation")
    return _save_run(
        result["validation_id"],
        workspace_id,
        result["name"],
        "demo_scenario",
        result["status"],
        user_id,
        scenario_name=scenario_name,
        summary=result.get("summary", {}),
        metrics=result.get("metrics", {}),
        report=result.get("report", {}),
        started_at=result.get("started_at"),
    )
