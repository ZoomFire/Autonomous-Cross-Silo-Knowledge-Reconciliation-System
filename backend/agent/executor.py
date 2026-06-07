from uuid import uuid4

from agent.report_builder import build_agent_report
from connector_store import get_source, list_sources, utc_now
from connectors.dataset_case_builder import build_dataset_cases_from_sources
from database.repositories import AgentRunRepository, AgentStepRepository, WorkspaceRepository
from dataset_evaluator import evaluate_dataset_cases
from dataset_store import save_dataset, save_evaluation_result
from drift_timeline import build_evaluation_timeline
from impact_graph import build_evaluation_impact_graph
from models import DatasetCase
from rag.search_service import search_workspace_sources
from root_cause_analyzer import build_root_cause_report


OPTIONAL_TOOLS = {
    "dataset_generation",
    "dataset_evaluation",
    "root_cause_analysis",
    "timeline_generation",
    "impact_graph_generation",
    "monitoring_recommendation",
}


def _skip(message: str) -> dict:
    return {"status": "skipped", "message": message}


def _source_ids_from_evidence(search_output: dict) -> list[str]:
    ids = []
    for item in search_output.get("answer", {}).get("evidence", []):
        source_id = item.get("source_id")
        if source_id and source_id not in ids:
            ids.append(source_id)
    return ids


def _load_sources(source_ids: list[str]) -> list[dict]:
    sources = []
    for source_id in source_ids:
        source = get_source(source_id)
        if source:
            sources.append(source)
    return sources


def _summarize_output(output: dict) -> dict:
    if "answer" in output:
        answer = output["answer"]
        return {
            "query_id": answer.get("query_id", ""),
            "possible_drift": answer.get("possible_drift", False),
            "evidence_count": len(answer.get("evidence", [])),
            "short_answer": answer.get("short_answer", ""),
        }
    if "dataset" in output:
        return {"dataset_id": output["dataset"].get("dataset_id", ""), "total_cases": output["dataset"].get("total_cases", 0)}
    if "evaluation" in output:
        return {"evaluation_id": output.get("evaluation_id", ""), "accuracy": output["evaluation"].get("accuracy", 0), "total_cases": output["evaluation"].get("total_cases", 0)}
    if "root_cause" in output:
        return {"drift_cases": output["root_cause"].get("drift_cases", 0), "high_priority_cases": output["root_cause"].get("high_priority_cases", 0)}
    if "timeline" in output:
        return {"total_events": output["timeline"].get("total_events", 0)}
    if "impact_graph" in output:
        return {"total_nodes": output["impact_graph"].get("total_nodes", 0), "total_edges": output["impact_graph"].get("total_edges", 0)}
    if "report" in output:
        return {"risk_level": output["report"].get("risk_level", "Unknown"), "status": output["report"].get("status", "completed")}
    return output


def _run_tool(tool_name: str, run: dict, step_outputs: dict) -> dict:
    workspace_id = run["workspace_id"]
    goal = run["goal"]

    if tool_name == "rag_search":
        answer = search_workspace_sources(workspace_id, goal, [], 10, run.get("user_id", ""))
        if not answer.get("evidence"):
            raise ValueError("No search evidence was found. Rebuild the search index or import sources first.")
        return {"answer": answer}

    if tool_name == "dataset_generation":
        source_ids = _source_ids_from_evidence(step_outputs.get("rag_search", {}))
        if not source_ids:
            return _skip("No source IDs were found in retrieved evidence.")
        sources = _load_sources(source_ids)
        if not sources:
            return _skip("Retrieved source IDs could not be loaded.")
        cases = build_dataset_cases_from_sources(sources)
        if not cases:
            return _skip("No dataset cases could be generated from retrieved sources.")
        dataset = save_dataset(
            cases,
            "agent-generated-from-evidence.json",
            "Agent Generated Dataset",
            f"Generated for agent goal: {goal}",
            "1.0",
            workspace_id,
        )
        return {"dataset": dataset, "source_ids": source_ids, "cases": [case.model_dump() for case in cases]}

    if tool_name == "dataset_evaluation":
        dataset_output = step_outputs.get("dataset_generation", {})
        if dataset_output.get("status") == "skipped" or not dataset_output.get("cases"):
            return _skip("Dataset evaluation skipped because no generated dataset is available.")
        cases = [DatasetCase(**case) for case in dataset_output.get("cases", [])]
        evaluation = evaluate_dataset_cases(cases)
        dataset = dataset_output.get("dataset", {})
        saved = save_evaluation_result(evaluation, dataset.get("dataset_id", "agent_generated"), dataset.get("name", "Agent Generated Dataset"), workspace_id)
        return {"evaluation_id": saved["evaluation_id"], "evaluation": evaluation.model_dump()}

    if tool_name == "root_cause_analysis":
        evaluation = step_outputs.get("dataset_evaluation", {}).get("evaluation")
        if evaluation:
            return {"root_cause": build_root_cause_report(evaluation, step_outputs["dataset_evaluation"].get("evaluation_id", "agent"))}
        search = step_outputs.get("rag_search", {}).get("answer", {})
        return {
            "root_cause": {
                "evaluation_id": "",
                "total_cases": 0,
                "drift_cases": 1 if search.get("possible_drift") else 0,
                "cases": [{
                    "case_id": "SEARCH-HINT",
                    "title": goal,
                    "root_cause_category": search.get("possible_drift_type", "Unknown"),
                    "suggested_owner": "Triage Team",
                    "recommended_fix": "Review the retrieved evidence and generate a dataset for deeper analysis.",
                }],
            }
        }

    if tool_name == "timeline_generation":
        evaluation = step_outputs.get("dataset_evaluation", {}).get("evaluation")
        if not evaluation:
            return _skip("Timeline generation skipped because no evaluation is available.")
        return {"timeline": build_evaluation_timeline(evaluation, step_outputs["dataset_evaluation"].get("evaluation_id", "agent"))}

    if tool_name == "impact_graph_generation":
        evaluation = step_outputs.get("dataset_evaluation", {}).get("evaluation")
        if not evaluation:
            return _skip("Impact graph generation skipped because no evaluation is available.")
        return {"impact_graph": build_evaluation_impact_graph(evaluation, step_outputs["dataset_evaluation"].get("evaluation_id", "agent"))}

    if tool_name == "monitoring_recommendation":
        risk = step_outputs.get("root_cause_analysis", {}).get("root_cause", {})
        high_count = risk.get("critical_priority_cases", 0) + risk.get("high_priority_cases", 0)
        return {
            "should_create_rule": high_count > 0 or any(word in goal.lower() for word in ["production", "critical", "alert"]),
            "suggested_thresholds": {"critical_cases": 1, "high_cases": 3, "accuracy_below": 85},
            "target_component": "goal-derived component",
            "message": "Create a monitoring rule if this workflow maps to production or high-severity drift.",
        }

    if tool_name == "agent_report":
        return {"report": build_agent_report(goal, step_outputs)}

    return _skip(f"Unsupported tool {tool_name}.")


def execute_agent_run(run_id: str) -> dict:
    run = AgentRunRepository.get_by_id(run_id)
    if not run:
        raise ValueError("Invalid run_id.")
    if not WorkspaceRepository.get_by_id(run.get("workspace_id", "")):
        AgentRunRepository.update_status(run_id, "failed", completed=True)
        raise ValueError("Workspace not found.")
    if not list_sources(run["workspace_id"]):
        AgentRunRepository.update_status(run_id, "failed", completed=True)
        raise ValueError("No imported sources found. Please import sources using Connectors first.")

    AgentRunRepository.update_status(run_id, "running")
    step_outputs: dict[str, dict] = {}
    failed_optional = False
    failed_critical = False

    for step in AgentStepRepository.list_by_run(run_id):
        tool_name = step["tool_name"]
        AgentStepRepository.update_status(step["step_id"], "running")
        try:
            output = _run_tool(tool_name, run, step_outputs)
            status = "skipped" if output.get("status") == "skipped" else "completed"
            output["summary"] = _summarize_output(output)
            AgentStepRepository.update_output(step["step_id"], output, status)
            step_outputs[tool_name] = output.get("report") if tool_name == "agent_report" else output
        except Exception as exc:
            AgentStepRepository.update_error(step["step_id"], str(exc))
            if tool_name in OPTIONAL_TOOLS:
                failed_optional = True
                continue
            failed_critical = True
            break

    report_output = step_outputs.get("agent_report")
    if not report_output:
        report_output = build_agent_report(run["goal"], step_outputs)
        step_outputs["agent_report"] = report_output

    status = "failed" if failed_critical else "partial" if failed_optional else "completed"
    report_output["status"] = status
    AgentRunRepository.update_final_report(run_id, report_output, status)
    return {
        "run": AgentRunRepository.get_by_id(run_id),
        "steps": AgentStepRepository.list_by_run(run_id),
        "final_report": report_output,
    }


def create_run_with_steps(workspace_id: str, user_id: str, goal: str, plan: list[dict]) -> dict:
    run = AgentRunRepository.create({
        "run_id": str(uuid4()),
        "workspace_id": workspace_id,
        "user_id": user_id,
        "goal": goal,
        "status": "planned",
        "plan": plan,
        "final_report": {},
        "created_at": utc_now(),
    })
    for step in plan:
        AgentStepRepository.create({
            "step_id": str(uuid4()),
            "run_id": run["run_id"],
            "workspace_id": workspace_id,
            "step_index": step["step_index"],
            "step_name": step["step_name"],
            "tool_name": step["tool_name"],
            "status": "pending",
            "input": step.get("input", {}),
        })
    return run
