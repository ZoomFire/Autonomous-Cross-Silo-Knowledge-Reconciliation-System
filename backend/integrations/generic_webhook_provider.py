from .base import BaseIntegrationProvider, provider_response
from .http_utils import post_json


class GenericWebhookIntegrationProvider(BaseIntegrationProvider):
    def test_connection(self, config: dict) -> dict:
        if not config.get("webhook_url"):
            return provider_response(False, error="Generic webhook live integration is not configured. Use mock mode or provide webhook_url.")
        return provider_response(True, external_status="healthy")

    def create_external_item(self, payload: dict, config: dict) -> dict:
        return self.send_notification(payload, config)

    def send_notification(self, payload: dict, config: dict) -> dict:
        if not config.get("webhook_url"):
            return provider_response(False, error="Generic webhook live integration is not configured. Use mock mode or provide webhook_url.")
        result = post_json(config["webhook_url"], payload)
        if not result["success"]:
            return provider_response(False, response=result, error=result.get("error") or result.get("text") or "Generic webhook request failed.")
        return provider_response(True, "WEBHOOK-LIVE", config.get("webhook_url", ""), "sent", result)
