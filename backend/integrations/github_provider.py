from .base import BaseIntegrationProvider, provider_response
from .http_utils import post_json


class GitHubIssuesIntegrationProvider(BaseIntegrationProvider):
    def _missing(self, config: dict) -> list[str]:
        return [key for key in ["repo_owner", "repo_name", "token"] if not config.get(key)]

    def test_connection(self, config: dict) -> dict:
        if self._missing(config):
            return provider_response(False, error="GitHub live integration is not configured. Use mock mode or provide repo_owner, repo_name, and token.")
        return provider_response(True, external_status="healthy", response={"repo": f"{config['repo_owner']}/{config['repo_name']}"})

    def create_external_item(self, payload: dict, config: dict) -> dict:
        if self._missing(config):
            return provider_response(False, error="GitHub live integration is not configured. Use mock mode or provide repo_owner, repo_name, and token.")
        url = f"https://api.github.com/repos/{config['repo_owner']}/{config['repo_name']}/issues"
        body = {"title": payload.get("title", "DriftGuard incident"), "body": payload.get("description", "")}
        result = post_json(url, body, {"Authorization": f"Bearer {config['token']}", "Accept": "application/vnd.github+json"})
        if not result["success"]:
            return provider_response(False, response=result, error=result.get("error") or result.get("text") or "GitHub issue request failed.")
        external_id = payload.get("external_id") or "GH-LIVE"
        external_url = f"https://github.com/{config['repo_owner']}/{config['repo_name']}/issues"
        return provider_response(True, external_id, external_url, "Open", result)

    def send_notification(self, payload: dict, config: dict) -> dict:
        return self.create_external_item(payload, config)
