import base64

from .base import BaseIntegrationProvider, provider_response
from .http_utils import post_json


class JiraIntegrationProvider(BaseIntegrationProvider):
    def _missing(self, config: dict) -> list[str]:
        return [key for key in ["base_url", "project_key", "email", "api_token"] if not config.get(key)]

    def test_connection(self, config: dict) -> dict:
        missing = self._missing(config)
        if missing:
            return provider_response(False, error="Jira live integration is not configured. Use mock mode or provide credentials.")
        return provider_response(True, external_status="healthy", response={"project_key": config.get("project_key")})

    def create_external_item(self, payload: dict, config: dict) -> dict:
        missing = self._missing(config)
        if missing:
            return provider_response(False, error="Jira live integration is not configured. Use mock mode or provide credentials.")
        url = config["base_url"].rstrip("/") + "/rest/api/3/issue"
        auth = base64.b64encode(f"{config['email']}:{config['api_token']}".encode("utf-8")).decode("ascii")
        body = {
            "fields": {
                "project": {"key": config["project_key"]},
                "summary": payload.get("title", "DriftGuard incident"),
                "description": payload.get("description", ""),
                "issuetype": {"name": "Task"},
            }
        }
        result = post_json(url, body, {"Authorization": f"Basic {auth}"})
        if not result["success"]:
            return provider_response(False, response=result, error=result.get("error") or result.get("text") or "Jira request failed.")
        external_id = payload.get("external_id") or "JIRA-LIVE"
        return provider_response(True, external_id, config["base_url"].rstrip("/") + "/browse/" + external_id, "Open", result)

    def send_notification(self, payload: dict, config: dict) -> dict:
        return self.create_external_item(payload, config)
