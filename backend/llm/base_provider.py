class BaseLLMProvider:
    provider_name = "base"
    model_name = "unknown"

    def generate(self, prompt: str, task_type: str, config: dict) -> dict:
        raise NotImplementedError

    def _response(self, task_type: str, output: dict | None = None, raw_text: str = "", success: bool = True, error: str | None = None) -> dict:
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "task_type": task_type,
            "output": output or {},
            "raw_text": raw_text,
            "success": success,
            "error": error,
        }

