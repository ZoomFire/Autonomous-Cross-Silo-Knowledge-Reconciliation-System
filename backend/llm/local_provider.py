from agent.report_builder import build_agent_report
from claim_extractor import build_truth_triangle, extract_claims, extract_entity
from drift_detector import detect_drift
from models import AnalysisRequest
from root_cause_analyzer import analyze_case

from .base_provider import BaseLLMProvider


class LocalRuleBasedProvider(BaseLLMProvider):
    provider_name = "local"
    model_name = "local-rule-engine"

    def generate(self, prompt: str, task_type: str, config: dict) -> dict:
        context = config.get("input_context", {}) or {}
        handlers = {
            "claim_extraction": self._claim_extraction,
            "contradiction_detection": self._contradiction_detection,
            "root_cause_analysis": self._root_cause_analysis,
            "fix_recommendation": self._fix_recommendation,
            "rag_answer": self._rag_answer,
            "agent_report": self._agent_report,
            "severity_classification": self._severity_classification,
            "drift_type_classification": self._drift_type_classification,
        }
        handler = handlers.get(task_type)
        if not handler:
            return self._response(task_type, success=False, error=f"Unsupported local task type: {task_type}")
        output = handler(context)
        return self._response(task_type, output, raw_text=str(output), success=True)

    def _analysis(self, context: dict) -> tuple[list, object]:
        request = AnalysisRequest(
            documentation=context.get("documentation", ""),
            code=context.get("code", ""),
            jira=context.get("jira", ""),
            commit=context.get("commit", ""),
            logs=context.get("logs", ""),
            database_config=context.get("database_config", ""),
        )
        entity = extract_entity([request.documentation, request.code, request.jira, request.commit, request.logs, request.database_config])
        claims = extract_claims(request, entity)
        return claims, detect_drift(build_truth_triangle(claims), entity)

    def _claim_extraction(self, context: dict) -> dict:
        request = AnalysisRequest(
            documentation=context.get("content", context.get("documentation", "")),
            code=context.get("code", ""),
            jira=context.get("jira", ""),
            commit=context.get("commit", ""),
            logs=context.get("logs", ""),
            database_config=context.get("database_config", ""),
        )
        entity = extract_entity([request.documentation, request.code, request.jira, request.commit, request.logs, request.database_config])
        claims = extract_claims(request, entity)
        return {"claims": [claim.model_dump() for claim in claims], "entity": entity}

    def _contradiction_detection(self, context: dict) -> dict:
        claims, report = self._analysis(context)
        label = "no_contradiction" if report.drift_type == "No Drift" else "contradiction"
        if report.recommended_action == "Manual review required":
            label = "uncertain"
        return {
            "label": label,
            "drift_type": report.drift_type,
            "severity": report.severity,
            "explanation": report.summary,
            "evidence": report.evidence,
            "confidence_score": report.confidence_score,
            "claim_count": len(claims),
        }

    def _root_cause_analysis(self, context: dict) -> dict:
        case_result = context.get("case_result") or {
            "case_id": context.get("case_id", "LOCAL-001"),
            "title": context.get("title", "Hybrid reasoning case"),
            "predicted_label": context.get("label", "uncertain"),
            "predicted_drift_type": context.get("drift_type", "Unknown"),
            "predicted_severity": context.get("severity", "Medium"),
            "mismatch_reason": context.get("explanation", "Local rules found possible drift signals."),
            "evidence_sources": context.get("evidence_sources", []),
            "input": context,
        }
        result = analyze_case(case_result)
        return {
            "root_cause_category": result.get("root_cause_category", "Unknown"),
            "responsible_source": result.get("responsible_source", "unknown"),
            "recommended_fix": result.get("recommended_fix", ""),
            "priority_level": result.get("priority_level", "Medium"),
            "suggested_owner": result.get("suggested_owner", "Triage Team"),
            "risk_impact": result.get("risk_impact", ""),
        }

    def _fix_recommendation(self, context: dict) -> dict:
        root = self._root_cause_analysis(context)
        return {
            "recommended_fix": root.get("recommended_fix", "Review conflicting evidence and align the source of truth."),
            "priority_level": root.get("priority_level", "Medium"),
            "suggested_owner": root.get("suggested_owner", "Triage Team"),
        }

    def _rag_answer(self, context: dict) -> dict:
        evidence = context.get("evidence", []) or []
        severity = context.get("severity_hint") or ("High" if any("production" in str(item).lower() for item in evidence) else "Medium")
        return {
            "executive_summary": context.get("short_answer", "Local reasoning reviewed retrieved evidence."),
            "risk_level": severity if severity in {"Critical", "High", "Medium", "Low"} else "Unknown",
            "recommended_actions": context.get("recommended_next_steps", ["Review retrieved evidence and run dataset evaluation if drift is suspected."]),
            "evidence_summary": context.get("evidence_summary", ""),
        }

    def _agent_report(self, context: dict) -> dict:
        return build_agent_report(context.get("goal", "Agent investigation"), context.get("step_outputs", {}))

    def _severity_classification(self, context: dict) -> dict:
        text = " ".join(str(value) for value in context.values()).lower()
        severity = "Critical" if any(token in text for token in ["critical", "security", "customer outage"]) else "High" if any(token in text for token in ["production", "403", "500", "failure"]) else "Medium" if "drift" in text else "Low"
        return {"severity": severity, "explanation": "Severity was classified by local keyword and drift signal rules."}

    def _drift_type_classification(self, context: dict) -> dict:
        output = self._contradiction_detection(context)
        return {"drift_type": output.get("drift_type", "Unknown"), "explanation": output.get("explanation", "")}

