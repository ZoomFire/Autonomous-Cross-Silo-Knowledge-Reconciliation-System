from uuid import uuid4

from connector_store import utc_now
from database.repositories import HybridAnalysisRepository, ReasoningTraceRepository
from logger import logger

from .gemini_provider import GeminiProvider
from .local_provider import LocalRuleBasedProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .output_validator import validate_llm_output
from .prompt_manager import get_default_prompt_templates, render_prompt


PROVIDERS = {
    "local": LocalRuleBasedProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
    "custom": OpenAIProvider,
}


def _provider(name: str):
    return PROVIDERS.get(name, LocalRuleBasedProvider)()


def _prompt(task_type: str, context: dict) -> str:
    template = next((item for item in get_default_prompt_templates() if item["task_type"] == task_type), None)
    if not template:
        return str(context)
    return render_prompt(template["template_text"], {**context, "context": context, "evidence": context.get("evidence", ""), "step_outputs": context.get("step_outputs", {})})


def _input_summary(context: dict) -> str:
    text = " ".join(str(value) for value in (context or {}).values())
    return text[:500]


def _compare(local_output: dict, llm_output: dict) -> dict:
    differences = []
    label_match = local_output.get("label") == llm_output.get("label") if ("label" in local_output or "label" in llm_output) else True
    severity_match = local_output.get("severity") == llm_output.get("severity") if ("severity" in local_output or "severity" in llm_output) else True
    drift_type_match = local_output.get("drift_type") == llm_output.get("drift_type") if ("drift_type" in local_output or "drift_type" in llm_output) else True
    if not label_match:
        differences.append(f"Local label {local_output.get('label')}, LLM label {llm_output.get('label')}")
    if not severity_match:
        differences.append(f"Local severity {local_output.get('severity')}, LLM severity {llm_output.get('severity')}")
    if not drift_type_match:
        differences.append(f"Local drift type {local_output.get('drift_type')}, LLM drift type {llm_output.get('drift_type')}")
    agreement = label_match and severity_match and drift_type_match
    return {
        "agreement": agreement,
        "label_match": label_match,
        "severity_match": severity_match,
        "drift_type_match": drift_type_match,
        "differences": differences,
        "final_decision_reason": "Local and LLM outputs agree." if agreement else "Outputs disagreed, so final output was marked uncertain or conservatively adjusted.",
    }


def _choose_final(local_output: dict, llm_output: dict, comparison: dict, context: dict) -> dict:
    if not llm_output:
        return local_output
    final = dict(local_output if comparison.get("agreement") else {**local_output, "label": "uncertain"})
    severity_rank = {"None": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    local_severity = local_output.get("severity") or local_output.get("risk_level") or "None"
    llm_severity = llm_output.get("severity") or llm_output.get("risk_level") or "None"
    text = " ".join(str(value) for value in context.values()).lower()
    if any(token in text for token in ["production", "customer", "security", "critical"]) and severity_rank.get(llm_severity, 0) > severity_rank.get(local_severity, 0):
        final["severity"] = llm_severity
        final["risk_level"] = llm_severity
        comparison["final_decision_reason"] = "Severity upgraded due to production/customer/security evidence."
    return final


def run_hybrid_reasoning(workspace_id, user_id, task_type, input_context, reasoning_mode="local_only", provider="local", runtime_api_key=None):
    input_context = input_context or {}
    prompt = _prompt(task_type, input_context)
    local_response = {}
    llm_response = {}
    local_validation = {}
    llm_validation = {}
    comparison = {}
    final_output = {}
    status = "completed"
    error_message = ""

    try:
        if reasoning_mode in {"local_only", "hybrid"}:
            local_response = LocalRuleBasedProvider().generate(prompt, task_type, {"input_context": input_context})
            local_validation = validate_llm_output(task_type, local_response.get("output", {}))

        if reasoning_mode in {"llm_only", "hybrid"}:
            llm_response = _provider(provider).generate(prompt, task_type, {"input_context": input_context, "runtime_api_key": runtime_api_key, "model_name": input_context.get("model_name"), **input_context.get("provider_config", {})})
            llm_validation = validate_llm_output(task_type, llm_response.get("output", {})) if llm_response.get("success") else {"valid": False, "missing_fields": [], "warnings": [llm_response.get("error", "")], "normalized_output": {}}
            if not llm_response.get("success"):
                logger.warning("LLM provider fallback for provider=%s task=%s error=%s", provider, task_type, llm_response.get("error"))

        if reasoning_mode == "local_only":
            final_output = local_validation.get("normalized_output", local_response.get("output", {}))
            validation = local_validation
        elif reasoning_mode == "llm_only":
            validation = llm_validation
            if not llm_response.get("success") or not llm_validation.get("valid"):
                status = "failed"
                error_message = llm_response.get("error") or "LLM output did not pass validation."
            final_output = llm_validation.get("normalized_output", {})
        else:
            local_output = local_validation.get("normalized_output", local_response.get("output", {}))
            llm_output = llm_validation.get("normalized_output", {}) if llm_response.get("success") else {}
            comparison = _compare(local_output, llm_output) if llm_output else {"agreement": False, "differences": [llm_response.get("error", "LLM output unavailable.")], "final_decision_reason": "LLM failed, so local output was used."}
            final_output = _choose_final(local_output, llm_output, comparison, input_context)
            validation = validate_llm_output(task_type, final_output)
    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        final_output = {}
        validation = {"valid": False, "missing_fields": [], "warnings": [], "normalized_output": {}}

    trace = ReasoningTraceRepository.create({
        "trace_id": str(uuid4()),
        "workspace_id": workspace_id,
        "user_id": user_id,
        "task_type": task_type,
        "reasoning_mode": reasoning_mode,
        "provider": provider,
        "input_summary": _input_summary(input_context),
        "local_output": local_response,
        "llm_output": llm_response,
        "final_output": final_output,
        "validation_result": validation,
        "status": status,
        "error_message": error_message,
        "created_at": utc_now(),
    })

    result = None
    if reasoning_mode == "hybrid":
        result = HybridAnalysisRepository.create({
            "result_id": str(uuid4()),
            "workspace_id": workspace_id,
            "trace_id": trace["trace_id"],
            "task_type": task_type,
            "source_context": input_context,
            "local_result": local_response,
            "llm_result": llm_response,
            "comparison": comparison,
            "final_result": final_output,
            "approved_by_user": False,
            "approval_status": "pending",
            "created_at": utc_now(),
        })

    return {
        "trace_id": trace["trace_id"],
        "result_id": result.get("result_id", "") if result else "",
        "final_output": final_output,
        "comparison": comparison,
        "validation": validation,
        "reasoning_mode": reasoning_mode,
        "provider": provider,
        "status": status,
        "error_message": error_message,
        "local_output": local_response,
        "llm_output": llm_response,
    }


def reasoning_trace_to_markdown(trace: dict) -> str:
    import json

    lines = [
        "# DriftGuard AI Hybrid Reasoning Trace",
        "",
        f"- Task type: {trace.get('task_type', '')}",
        f"- Reasoning mode: {trace.get('reasoning_mode', '')}",
        f"- Provider: {trace.get('provider', '')}",
        f"- Status: {trace.get('status', '')}",
        "",
        "## Local Output",
        "```json",
        json.dumps(trace.get("local_output", {}), indent=2),
        "```",
        "",
        "## LLM Output",
        "```json",
        json.dumps(trace.get("llm_output", {}), indent=2),
        "```",
        "",
        "## Final Output",
        "```json",
        json.dumps(trace.get("final_output", {}), indent=2),
        "```",
        "",
        "## Validation Result",
        "```json",
        json.dumps(trace.get("validation_result", {}), indent=2),
        "```",
    ]
    return "\n".join(lines)
