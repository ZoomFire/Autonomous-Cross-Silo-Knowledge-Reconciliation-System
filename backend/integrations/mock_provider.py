from database.repositories import MockExternalTicketRepository

from .base import BaseIntegrationProvider, provider_response


PREFIX_BY_TYPE = {
    "jira": "MOCK-JIRA",
    "github_issues": "MOCK-GH",
    "slack": "MOCK-SLACK",
    "teams": "MOCK-TEAMS",
    "generic_webhook": "MOCK-WEBHOOK",
}


EXTERNAL_TYPE_BY_INTEGRATION = {
    "jira": "jira_ticket",
    "github_issues": "github_issue",
    "slack": "slack_message",
    "teams": "teams_message",
    "generic_webhook": "webhook_event",
}


class MockIntegrationProvider(BaseIntegrationProvider):
    def _next_external_id(self, workspace_id: str, integration_type: str) -> str:
        external_type = EXTERNAL_TYPE_BY_INTEGRATION.get(integration_type, "webhook_event")
        count = MockExternalTicketRepository.count_by_workspace_and_type(workspace_id, external_type) + 1
        return f"{PREFIX_BY_TYPE.get(integration_type, 'MOCK-EXT')}-{count:03d}"

    def test_connection(self, config: dict) -> dict:
        integration_type = config.get("integration_type", "generic_webhook")
        return provider_response(True, f"{PREFIX_BY_TYPE.get(integration_type, 'MOCK-EXT')}-TEST", "http://localhost/mock/external/test", "healthy", {"mode": "mock"})

    def create_external_item(self, payload: dict, config: dict) -> dict:
        integration_type = config.get("integration_type", "jira")
        external_id = self._next_external_id(payload.get("workspace_id", ""), integration_type)
        return provider_response(True, external_id, f"http://localhost/mock/external/{external_id}", "Open", {"mock": True, "payload": payload})

    def send_notification(self, payload: dict, config: dict) -> dict:
        integration_type = config.get("integration_type", "slack")
        external_id = self._next_external_id(payload.get("workspace_id", ""), integration_type)
        return provider_response(True, external_id, f"http://localhost/mock/external/{external_id}", "sent", {"mock": True, "payload": payload})
