from datetime import datetime, timezone
from uuid import uuid4

from database.repositories import (
    ExternalIntegrationRepository,
    ExternalLinkedResourceRepository,
    ExternalSyncRecordRepository,
    IncidentRepository,
    MockExternalTicketRepository,
)
from incidents.incident_service import add_timeline_event
from privacy_store import get_privacy_settings
from security_utils import mask_secret, sanitize_metadata

from .generic_webhook_provider import GenericWebhookIntegrationProvider
from .github_provider import GitHubIssuesIntegrationProvider
from .jira_provider import JiraIntegrationProvider
from .mock_provider import EXTERNAL_TYPE_BY_INTEGRATION, MockIntegrationProvider
from .slack_provider import SlackIntegrationProvider
from .teams_provider import TeamsIntegrationProvider
from .templates import (
    build_generic_webhook_payload,
    build_github_issue_payload,
    build_jira_ticket_payload,
    build_slack_message_payload,
    build_teams_message_payload,
)


SUPPORTED_INTEGRATION_TYPES = {"jira", "github_issues", "slack", "teams", "generic_webhook"}
TICKET_INTEGRATIONS = {"jira", "github_issues"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _secret_mask(payload: dict) -> str:
    values = []
    for key, value in (payload.get("config") or {}).items():
        if any(term in key.lower() for term in ["token", "secret", "password", "api_key"]):
            values.append(mask_secret(str(value)))
    if payload.get("secret"):
        values.append(mask_secret(str(payload["secret"])))
    return ", ".join(value for value in values if value)


def create_integration(payload: dict, user: dict) -> dict:
    integration_type = payload.get("integration_type", "")
    if integration_type not in SUPPORTED_INTEGRATION_TYPES:
        raise ValueError("Invalid integration_type.")
    mode = payload.get("mode", "mock")
    if mode not in {"mock", "live"}:
        raise ValueError("Invalid integration mode.")
    now = utc_now()
    return ExternalIntegrationRepository.create({
        "integration_id": str(uuid4()),
        "workspace_id": payload.get("workspace_id", ""),
        "name": payload.get("name", "External integration"),
        "integration_type": integration_type,
        "mode": mode,
        "enabled": payload.get("enabled", True),
        "config": payload.get("config", {}),
        "secret_masked": _secret_mask(payload),
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
    })


def list_integrations(workspace_id: str) -> list[dict]:
    return ExternalIntegrationRepository.list_by_workspace(workspace_id)


def _provider_for(integration: dict):
    if integration.get("mode") == "mock":
        return MockIntegrationProvider()
    return {
        "jira": JiraIntegrationProvider(),
        "github_issues": GitHubIssuesIntegrationProvider(),
        "slack": SlackIntegrationProvider(),
        "teams": TeamsIntegrationProvider(),
        "generic_webhook": GenericWebhookIntegrationProvider(),
    }.get(integration.get("integration_type"), GenericWebhookIntegrationProvider())


def _provider_config(integration: dict) -> dict:
    config = dict(integration.get("config") or {})
    config["integration_type"] = integration.get("integration_type", "")
    config["mode"] = integration.get("mode", "mock")
    return config


def _build_payload(integration_type: str, incident: dict) -> dict:
    builders = {
        "jira": build_jira_ticket_payload,
        "github_issues": build_github_issue_payload,
        "slack": build_slack_message_payload,
        "teams": build_teams_message_payload,
        "generic_webhook": build_generic_webhook_payload,
    }
    return builders.get(integration_type, build_generic_webhook_payload)(incident)


def _redact_if_needed(workspace_id: str, payload: dict) -> dict:
    settings = get_privacy_settings(workspace_id)
    if settings.get("privacy_mode_enabled", True) and settings.get("redact_exports", True):
        return sanitize_metadata(payload)
    return payload


def _sync_record(integration: dict, incident: dict | None, action: str, request_payload: dict, result: dict) -> dict:
    status = "success" if result.get("success") else "failed"
    return ExternalSyncRecordRepository.create({
        "sync_record_id": str(uuid4()),
        "workspace_id": integration.get("workspace_id", ""),
        "integration_id": integration.get("integration_id", ""),
        "integration_type": integration.get("integration_type", ""),
        "source_type": "incident" if incident else "integration",
        "source_id": incident.get("incident_id", "") if incident else integration.get("integration_id", ""),
        "action": action,
        "status": status,
        "request_payload": request_payload,
        "response_payload": result.get("response", {}),
        "external_id": result.get("external_id", ""),
        "external_url": result.get("external_url", ""),
        "error_message": result.get("error") or "",
        "created_at": utc_now(),
    })


def _create_mock_item(integration: dict, incident: dict, result: dict) -> dict | None:
    if integration.get("mode") != "mock" or not result.get("success"):
        return None
    external_type = EXTERNAL_TYPE_BY_INTEGRATION.get(integration.get("integration_type", ""), "webhook_event")
    return MockExternalTicketRepository.create({
        "mock_id": str(uuid4()),
        "workspace_id": integration["workspace_id"],
        "integration_id": integration["integration_id"],
        "external_type": external_type,
        "title": incident.get("title", ""),
        "description": incident.get("description", ""),
        "severity": incident.get("severity", ""),
        "status": result.get("external_status", "Open"),
        "source_type": "incident",
        "source_id": incident.get("incident_id", ""),
        "external_id": result.get("external_id", ""),
        "external_url": result.get("external_url", ""),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })


def create_linked_resource(integration: dict, incident: dict, result: dict) -> dict:
    external_type = EXTERNAL_TYPE_BY_INTEGRATION.get(integration.get("integration_type", ""), "webhook_event")
    return ExternalLinkedResourceRepository.create({
        "linked_resource_id": str(uuid4()),
        "workspace_id": integration["workspace_id"],
        "integration_id": integration["integration_id"],
        "source_type": "incident",
        "source_id": incident["incident_id"],
        "external_type": external_type,
        "external_id": result.get("external_id", ""),
        "external_url": result.get("external_url", ""),
        "external_status": result.get("external_status", ""),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })


def test_integration(integration_id: str) -> dict:
    integration = ExternalIntegrationRepository.get_unmasked_by_id(integration_id)
    if not integration:
        raise ValueError("Integration not found.")
    provider = _provider_for(integration)
    result = provider.test_connection(_provider_config(integration))
    ExternalIntegrationRepository.update(integration_id, {
        "last_health_check_at": utc_now(),
        "last_health_status": "healthy" if result.get("success") else "error",
    })
    record = _sync_record(integration, None, "health_check", {"integration_id": integration_id}, result)
    return {"result": result, "sync_record": record, "integration": ExternalIntegrationRepository.get_by_id(integration_id)}


def sync_incident_to_external(integration_id: str, incident_id: str, user: dict, notify_only: bool = False) -> dict:
    integration = ExternalIntegrationRepository.get_unmasked_by_id(integration_id)
    if not integration:
        raise ValueError("Integration not found.")
    if not integration.get("enabled", True):
        result = {"success": False, "response": {}, "error": "Integration is disabled.", "external_id": "", "external_url": "", "external_status": "skipped"}
        record = _sync_record(integration, {"incident_id": incident_id}, "send_message" if notify_only else "create_ticket", {}, result)
        return {"result": result, "sync_record": record}
    incident = IncidentRepository.get_by_id(incident_id)
    if not incident:
        raise ValueError("Incident not found.")
    payload = _redact_if_needed(integration["workspace_id"], _build_payload(integration["integration_type"], incident))
    provider = _provider_for(integration)
    action = "send_message" if notify_only or integration["integration_type"] not in TICKET_INTEGRATIONS else ("create_issue" if integration["integration_type"] == "github_issues" else "create_ticket")
    result = provider.send_notification(payload, _provider_config(integration)) if action == "send_message" else provider.create_external_item(payload, _provider_config(integration))
    record = _sync_record(integration, incident, action, payload, result)
    linked_resource = None
    mock_item = None
    if result.get("success"):
        linked_resource = create_linked_resource(integration, incident, result)
        mock_item = _create_mock_item(integration, incident, result)
        add_timeline_event(incident, "external_sync_success", user.get("user_id", ""), f"Synced to {integration['name']} as {result.get('external_id', '')}.", {"integration_id": integration_id, "external_url": result.get("external_url", "")})
    else:
        add_timeline_event(incident, "external_sync_failed", user.get("user_id", ""), f"External sync failed for {integration['name']}.", {"integration_id": integration_id, "error": result.get("error", "")})
    return {"result": result, "sync_record": record, "linked_resource": linked_resource, "mock_item": mock_item}


def send_incident_notification(integration_id: str, incident_id: str, user: dict) -> dict:
    return sync_incident_to_external(integration_id, incident_id, user, notify_only=True)


def list_sync_records(workspace_id: str, filters: dict | None = None) -> list[dict]:
    return ExternalSyncRecordRepository.list_by_workspace(workspace_id, filters or {})


def get_integration_health_summary(workspace_id: str) -> dict:
    integrations = ExternalIntegrationRepository.list_by_workspace(workspace_id)
    return {
        "total_integrations": len(integrations),
        "enabled_integrations": sum(1 for item in integrations if item.get("enabled")),
        "healthy_integrations": sum(1 for item in integrations if item.get("last_health_status") == "healthy"),
        "error_integrations": sum(1 for item in integrations if item.get("last_health_status") == "error"),
        "mock_integrations": sum(1 for item in integrations if item.get("mode") == "mock"),
        "live_integrations": sum(1 for item in integrations if item.get("mode") == "live"),
        "recent_sync_failures": ExternalSyncRecordRepository.recent_failures_count(workspace_id),
    }
