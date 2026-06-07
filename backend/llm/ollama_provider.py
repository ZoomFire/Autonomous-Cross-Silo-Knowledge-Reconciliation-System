import json
import urllib.error
import urllib.request

from .base_provider import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    provider_name = "ollama"
    model_name = "ollama-local"

    def generate(self, prompt: str, task_type: str, config: dict) -> dict:
        endpoint = (config.get("ollama_endpoint") or "").rstrip("/")
        model = config.get("model_name") or "llama3"
        self.model_name = model
        if not endpoint:
            return self._response(task_type, success=False, error="Ollama provider is not configured. Falling back to local reasoning.")
        try:
            request = urllib.request.Request(
                f"{endpoint}/api/generate",
                data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            raw_text = payload.get("response", "")
            return self._response(task_type, {"raw_response": raw_text}, raw_text=raw_text, success=True)
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return self._response(task_type, success=False, error=f"Ollama request failed. Falling back to local reasoning. {exc}")

