from database.repositories import AgentRunRepository, DatasetRepository, EvaluationRepository, ExecutiveReportRepository, ExternalIntegrationRepository, ImportedSourceRepository, IncidentRepository, WorkspaceRepository


def validate_demo_flow(workspace_id: str) -> dict:
    checks = []

    def add(name: str, passed: bool, details: str):
        checks.append({"name": name, "passed": passed, "details": details})

    workspace = WorkspaceRepository.get_by_id(workspace_id)
    datasets = DatasetRepository.list(workspace_id)
    evaluations = EvaluationRepository.list(workspace_id)
    sources = ImportedSourceRepository.list_by_workspace(workspace_id)
    incidents = IncidentRepository.list_by_workspace(workspace_id)
    reports = ExecutiveReportRepository.list_by_workspace(workspace_id)
    integrations = ExternalIntegrationRepository.list_by_workspace(workspace_id)
    agents = AgentRunRepository.list_by_workspace(workspace_id)
    add("Workspace exists", bool(workspace), "Workspace found" if workspace else "Workspace missing")
    add("Demo or real sources available", bool(sources), f"{len(sources)} sources found")
    add("Dataset available", bool(datasets), f"{len(datasets)} datasets found")
    add("Evaluation available", bool(evaluations), f"{len(evaluations)} evaluations found")
    add("RAG index available", bool(sources), "Sources can be indexed for RAG" if sources else "No sources to index")
    add("Agent run available", bool(agents), f"{len(agents)} agent runs found")
    add("Incident available", bool(incidents), f"{len(incidents)} incidents found")
    add("Executive report available", bool(reports), f"{len(reports)} executive reports found")
    add("Mock integration available", any(item.get("mode") == "mock" for item in integrations), f"{len(integrations)} integrations found")
    missing = [item["name"] for item in checks if not item["passed"]]
    score = max(0, 100 - len(missing) * 10)
    return {
        "ready_for_demo": score >= 80,
        "score": score,
        "checks": checks,
        "missing_items": missing,
        "recommendations": [f"Add or run: {item}" for item in missing] or ["Demo flow is ready."],
    }
