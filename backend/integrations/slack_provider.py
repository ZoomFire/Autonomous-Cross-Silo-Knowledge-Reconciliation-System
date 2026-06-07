from .base import BaseIntegrationProvider, provider_response
from .http_utils import post_json


class SlackIntegrationProvider(BaseIntegrationProvider):
    def test_connection(self, config: dict) -> dict:
        if not config.get("webhook_url"):
            return provider_response(False, error="Slack live integration is not configured. Use mock mode or provide webhook_url.")
        return provider_response(True, external_status="healthy")

    def create_external_item(self, payload: dict, config: dict) -> dict:
        return self.send_notification(payload, config)

    def send_notification(self, payload: dict, config: dict) -> dict:
        if not config.get("webhook_url"):
            return provider_response(False, error="Slack live integration is not configured. Use mock mode or provide webhook_url.")
        result = post_json(config["webhook_url"], {"text": payload.get("message") or payload.get("title", "DriftGuard incident")})
        if not result["success"]:
            return provider_response(False, response=result, error=result.get("error") or result.get("text") or "Slack webhook request failed.")
        return provider_response(True, "SLACK-LIVE", "", "sent", result)
