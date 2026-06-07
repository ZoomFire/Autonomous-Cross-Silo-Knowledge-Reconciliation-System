class BaseIntegrationProvider:
    def test_connection(self, config: dict) -> dict:
        raise NotImplementedError

    def create_external_item(self, payload: dict, config: dict) -> dict:
        raise NotImplementedError

    def send_notification(self, payload: dict, config: dict) -> dict:
        raise NotImplementedError


def provider_response(success: bool, external_id: str = "", external_url: str = "", external_status: str = "open", response: dict | None = None, error: str | None = None) -> dict:
    return {
        "success": success,
        "external_id": external_id,
        "external_url": external_url,
        "external_status": external_status,
        "response": response or {},
        "error": error,
    }
