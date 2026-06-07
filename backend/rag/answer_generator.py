SOURCE_TYPES = ["documentation", "code", "jira", "logs", "database_config", "commit"]


def _contains_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in words)


def _coverage(chunks: list[dict]) -> dict[str, int]:
    return {source_type: sum(1 for chunk in chunks if chunk.get("source_type") == source_type) for source_type in SOURCE_TYPES}


def _severity(text: str) -> str:
    if _contains_any(text, ["production", "customer", "403", "500", "failure", "outage", "security"]):
        return "Critical"
    if _contains_any(text, ["error", "disabled", "forbidden", "timeout"]):
        return "High"
    if _contains_any(text, ["mismatch", "inconsistent", "deprecated"]):
        return "Medium"
    return "Low"


def _drift_type(chunks: list[dict]) -> tuple[bool, str]:
    by_type = {source_type: " ".join(chunk.get("chunk_text", "").lower() for chunk in chunks if chunk.get("source_type") == source_type) for source_type in SOURCE_TYPES}
    docs_public = _contains_any(by_type["documentation"], ["public", "enabled", "working", "customer-facing", "customer"])
    docs_restricted = _contains_any(by_type["documentation"], ["internal", "disabled", "requires authentication"])
    jira_public = _contains_any(by_type["jira"], ["customer", "public", "ready", "requirement"])
    code_restricted = _contains_any(by_type["code"], ["internal_only", "private", "admin_required", "auth_required", "login_required"])
    code_public = _contains_any(by_type["code"], ["public", "allow_anonymous", "@public"])
    logs_error = _contains_any(by_type["logs"], ["403", "500", "error", "failure", "forbidden", "timeout"])
    config_restricted = _contains_any(by_type["database_config"], ["disabled", "feature_enabled=false", "access_type=internal", "visibility=internal"])

    if docs_public and (code_restricted or logs_error or config_restricted):
        return True, "Documentation Drift"
    if jira_public and (code_restricted or logs_error or config_restricted):
        return True, "Ticket Drift"
    if logs_error and (docs_public or code_public):
        return True, "Runtime Drift"
    if config_restricted and docs_public:
        return True, "Configuration Drift"
    if docs_restricted and code_public:
        return True, "Implementation Drift"
    return False, "None"


def generate_answer(query: str, retrieved_chunks: list[dict]) -> dict:
    combined = " ".join(chunk.get("chunk_text", "") for chunk in retrieved_chunks)
    coverage = _coverage(retrieved_chunks)
    possible_drift, drift_type = _drift_type(retrieved_chunks)
    top_score = retrieved_chunks[0]["score"] if retrieved_chunks else 0
    confidence = 0.3 + (0.1 * sum(1 for count in coverage.values() if count)) + (0.1 if top_score >= 20 else 0) + (0.2 if possible_drift else 0)
    confidence = max(0, min(1, round(confidence, 2)))
    severity = _severity(combined)

    if not retrieved_chunks:
        short_answer = "No strong evidence was found in the current search index."
        summary = "Try rebuilding the search index or broadening source type filters."
    elif possible_drift:
        short_answer = f"Relevant evidence suggests possible {drift_type.lower()} for this question."
        summary = "The retrieved evidence spans multiple source types and contains signals that may disagree."
    else:
        short_answer = "Relevant evidence was found, but no clear drift pattern was detected."
        summary = "The answer is based on the highest-scoring imported source chunks."

    next_steps = [
        "Review documentation and code behavior for the same endpoint.",
        "Check latest commit related to this source.",
        "Run dataset generation and evaluation for this component.",
    ]
    if severity == "Critical":
        next_steps.append("Create monitoring rule if this is a critical production flow.")

    return {
        "query": query,
        "short_answer": short_answer,
        "confidence_score": confidence,
        "evidence_summary": summary,
        "possible_drift": possible_drift,
        "possible_drift_type": drift_type,
        "severity_hint": severity,
        "source_coverage": coverage,
        "evidence": retrieved_chunks,
        "recommended_next_steps": next_steps,
    }

