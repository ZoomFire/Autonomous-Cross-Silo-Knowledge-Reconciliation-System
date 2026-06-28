import json
import os
import urllib.error
import urllib.request

from .base_provider import BaseLLMProvider


GROK_SYSTEM_PROMPT = (
    "You are an enterprise architecture reconciliation agent. Analyze the following sources: "
    "documentation, code, Jira ticket, commit message, system logs, and database config. Extract key claims, "
    "compare them, detect contradictions, identify architectural drift, classify drift type, assign severity, "
    "estimate confidence, and suggest corrective actions. Return the result in structured JSON."
)


class GrokProvider(BaseLLMProvider):
    provider_name = "grok"
    model_name = "grok-4-latest"

    def generate(self, prompt: str, task_type: str, config: dict) -> dict:
        api_key = (config.get("runtime_api_key") or os.getenv("XAI_API_KEY") or "").strip()
        if not api_key:
            return self._response(
                task_type,
                success=False,
                error="Grok/xAI API key is required. Provide a runtime key or set XAI_API_KEY.",
            )

        model = config.get("model_name") or self.model_name
        self.model_name = model
        context = config.get("input_context", {}) or {}
        user_prompt = self._build_user_prompt(context, prompt)

        request_body = {
            "model": model,
            "messages": [
                {"role": "system", "content": GROK_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        try:
            request = urllib.request.Request(
                "https://api.x.ai/v1/chat/completions",
                data=json.dumps(request_body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            raw_text = self._extract_text(payload)
            parsed = self._parse_json(raw_text)
            output = self._normalize_output(parsed)
            return self._response(task_type, output=output, raw_text=raw_text, success=True)
        except urllib.error.HTTPError as exc:
            return self._response(task_type, success=False, error=self._http_error_message(exc))
        except TimeoutError:
            return self._response(task_type, success=False, error="Grok request timed out. Falling back to local reasoning.")
        except urllib.error.URLError as exc:
            reason = str(getattr(exc, "reason", "") or exc)
            if "timed out" in reason.lower():
                return self._response(task_type, success=False, error="Grok request timed out. Falling back to local reasoning.")
            return self._response(task_type, success=False, error="Grok API is unavailable. Falling back to local reasoning.")
        except json.JSONDecodeError:
            return self._response(task_type, success=False, error="Grok returned invalid JSON. Falling back to local reasoning.")
        except OSError:
            return self._response(task_type, success=False, error="Grok request failed. Falling back to local reasoning.")

    def _build_user_prompt(self, context: dict, fallback_prompt: str) -> str:
        fields = {
            "documentation": context.get("documentation", ""),
            "code": context.get("code", ""),
            "jira": context.get("jira", ""),
            "commit": context.get("commit", ""),
            "logs": context.get("logs", ""),
            "database_config": context.get("database_config", ""),
        }
        if not any(str(value).strip() for value in fields.values()):
            return fallback_prompt
        return "\n\n".join(f"{name}:\n{value}" for name, value in fields.items())

    def _extract_text(self, payload: dict) -> str:
        choices = payload.get("choices") or []
        if not choices:
            raise json.JSONDecodeError("missing choices", "", 0)
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            return "\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
        return str(content)

    def _parse_json(self, raw_text: str) -> dict:
        cleaned = (raw_text or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("response was not an object", cleaned, 0)
        return parsed

    def _normalize_output(self, parsed: dict) -> dict:
        drift_types = parsed.get("drift_types") or []
        if isinstance(drift_types, str):
            drift_types = [drift_types]
        contradictions = parsed.get("contradictions") or []
        extracted_claims = parsed.get("extracted_claims") or []
        suggested_actions = parsed.get("suggested_actions") or []
        severity = parsed.get("severity") or "None"
        summary = parsed.get("summary") or ""
        drift_detected = bool(parsed.get("drift_detected"))
        confidence = parsed.get("confidence", parsed.get("confidence_score", 0))

        return {
            **parsed,
            "drift_detected": drift_detected,
            "summary": summary,
            "extracted_claims": extracted_claims if isinstance(extracted_claims, list) else [],
            "contradictions": contradictions if isinstance(contradictions, list) else [],
            "drift_types": drift_types,
            "severity": severity,
            "confidence": confidence,
            "suggested_actions": suggested_actions if isinstance(suggested_actions, list) else [str(suggested_actions)],
            "label": "contradiction" if drift_detected else "no_contradiction",
            "drift_type": ", ".join(drift_types) if drift_types else "No Drift",
            "explanation": summary,
            "evidence": contradictions if contradictions else extracted_claims,
            "confidence_score": confidence,
        }

    def _http_error_message(self, exc: urllib.error.HTTPError) -> str:
        if exc.code in {401, 403}:
            return "Invalid Grok/xAI API key or insufficient API access. Falling back to local reasoning."
        if exc.code == 429:
            return "Grok API rate limit reached. Falling back to local reasoning."
        if 500 <= exc.code < 600:
            return "Grok API is unavailable. Falling back to local reasoning."
        return "Grok request failed. Falling back to local reasoning."
