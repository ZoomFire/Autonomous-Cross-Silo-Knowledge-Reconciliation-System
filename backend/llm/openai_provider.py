from .base_provider import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    model_name = "openai-optional"

    def generate(self, prompt: str, task_type: str, config: dict) -> dict:
        if not config.get("runtime_api_key"):
            return self._response(task_type, success=False, error="OpenAI provider is not configured. Falling back to local reasoning.")
        return self._response(task_type, success=False, error="OpenAI SDK integration is optional and not installed in this MVP. Falling back to local reasoning.")

