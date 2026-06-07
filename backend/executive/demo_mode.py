from datetime import datetime, timezone
from uuid import uuid4

from database.repositories import DemoModeRepository
from incidents.incident_service import create_incident
from integrations.integration_service import create_integration, sync_incident_to_external


SCENARIOS = {
    "Payment API Drift Demo": [
        "Import demo sources",
        "Run RAG search",
        "Generate dataset",
        "Run evaluation",
        "Generate root cause",
        "Create incident",
        "Sync to mock Jira",
        "Export executive report",
    ],
    "Model Monitoring Demo": ["Review deployed model", "Run monitoring check", "Open model alert", "Create incident", "Review executive risk"],
    "Security Incident Demo": ["Review security summary", "Create security incident", "Escalate incident", "Export executive report"],
    "Executive ROI Demo": ["Open Executive page", "Calculate ROI", "Generate report", "Export markdown"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_demo_scenarios() -> list[dict]:
    return [{"name": name, "steps": steps} for name, steps in SCENARIOS.items()]


def _state_payload(workspace_id: str, enabled: bool, scenario_name: str = "", current_step: int = 0, completed_steps: list[str] | None = None) -> dict:
    return {
        "demo_state_id": str(uuid4()),
        "workspace_id": workspace_id,
        "enabled": enabled,
        "scenario_name": scenario_name,
        "current_step": current_step,
        "completed_steps": completed_steps or [],
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def enable_demo_mode(workspace_id: str, scenario_name: str) -> dict:
    if scenario_name not in SCENARIOS:
        raise ValueError("Unknown demo scenario.")
    return DemoModeRepository.upsert(_state_payload(workspace_id, True, scenario_name, 0, []))


def disable_demo_mode(workspace_id: str) -> dict:
    current = DemoModeRepository.get_by_workspace(workspace_id) or {}
    return DemoModeRepository.upsert(_state_payload(workspace_id, False, current.get("scenario_name", ""), current.get("current_step", 0), current.get("completed_steps", [])))


def get_demo_state(workspace_id: str) -> dict:
    return DemoModeRepository.get_by_workspace(workspace_id) or _state_payload(workspace_id, False)


def advance_demo_step(workspace_id: str) -> dict:
    state = get_demo_state(workspace_id)
    scenario = state.get("scenario_name") or "Payment API Drift Demo"
    steps = SCENARIOS.get(scenario, [])
    current = min(int(state.get("current_step", 0) or 0), len(steps))
    completed = list(state.get("completed_steps", []))
    if current < len(steps) and steps[current] not in completed:
        completed.append(steps[current])
    return DemoModeRepository.upsert(_state_payload(workspace_id, True, scenario, min(current + 1, len(steps)), completed))


def reset_demo_data(workspace_id: str) -> dict:
    return DemoModeRepository.upsert(_state_payload(workspace_id, False, "", 0, ["Demo state reset. User data was not deleted."]))


def seed_executive_demo_data(workspace_id: str, user: dict) -> dict:
    integration = create_integration({
        "workspace_id": workspace_id,
        "name": "Executive Demo Jira Mock",
        "integration_type": "jira",
        "mode": "mock",
        "enabled": True,
        "config": {"project_key": "DG"},
    }, user)
    incident = create_incident({
        "workspace_id": workspace_id,
        "title": "Demo critical payment API drift",
        "description": "Demo data: checkout documentation and implementation no longer agree on payment retry behavior.",
        "severity": "Critical",
        "source_type": "demo",
        "metadata": {"demo": True},
    }, user)
    sync = sync_incident_to_external(integration["integration_id"], incident["incident_id"], user)
    state = enable_demo_mode(workspace_id, "Executive ROI Demo")
    return {"integration": integration, "incident": incident, "sync": sync, "demo_state": state}
