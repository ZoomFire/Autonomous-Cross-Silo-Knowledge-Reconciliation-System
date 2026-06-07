from .base_provider import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"
    model_name = "gemini-optional"

    def generate(self, prompt: str, task_type: str, config: dict) -> dict:
        if not config.get("runtime_api_key"):
            return self._response(task_type, success=False, error="Gemini provider is not configured. Falling back to local reasoning.")
        return self._response(task_type, success=False, error="Gemini SDK integration is optional and not installed in this MVP. Falling back to local reasoning.")

