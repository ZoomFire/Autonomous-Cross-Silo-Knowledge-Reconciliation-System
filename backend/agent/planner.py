DATASET_TERMS = {"drift", "contradiction", "evaluate", "report", "analyze"}
EVALUATION_TERMS = {"drift", "contradiction", "evaluate", "severity", "report"}
ROOT_CAUSE_TERMS = {"why", "root cause", "cause", "failing", "failure", "problem", "report"}
TIMELINE_TERMS = {"when", "timeline", "history", "introduced", "evolution", "report"}
IMPACT_TERMS = {"impact", "affected", "component", "risk", "dependency", "report"}
MONITORING_TERMS = {"monitor", "alert", "production", "critical"}


def _contains_any(goal: str, terms: set[str]) -> bool:
    return any(term in goal for term in terms)


def _step(index: int, step_name: str, tool_name: str, input_data: dict | None = None) -> dict:
    return {
        "step_index": index,
        "step_name": step_name,
        "tool_name": tool_name,
        "status": "pending",
        "input": input_data or {},
    }


def create_agent_plan(goal: str, workspace_id: str) -> list[dict]:
    """Build a deterministic local plan from the user's high-level goal."""
    normalized_goal = (goal or "").strip().lower()
    full_report = "full report" in normalized_goal
    steps: list[tuple[str, str]] = [("Search Evidence", "rag_search")]

    if full_report or _contains_any(normalized_goal, DATASET_TERMS):
        steps.append(("Generate Dataset", "dataset_generation"))
    if full_report or _contains_any(normalized_goal, EVALUATION_TERMS):
        steps.append(("Run Evaluation", "dataset_evaluation"))
    if full_report or _contains_any(normalized_goal, ROOT_CAUSE_TERMS):
        steps.append(("Analyze Root Cause", "root_cause_analysis"))
    if full_report or _contains_any(normalized_goal, TIMELINE_TERMS):
        steps.append(("Build Drift Timeline", "timeline_generation"))
    if full_report or _contains_any(normalized_goal, IMPACT_TERMS):
        steps.append(("Build Impact Graph", "impact_graph_generation"))
    if full_report or _contains_any(normalized_goal, MONITORING_TERMS):
        steps.append(("Build Monitoring Recommendation", "monitoring_recommendation"))

    steps.append(("Generate Final Report", "agent_report"))
    return [
        _step(index, name, tool, {"workspace_id": workspace_id, "goal": goal} if index == 1 else {})
        for index, (name, tool) in enumerate(steps, start=1)
    ]

