from uuid import uuid4

from models import Claim, DriftReport, TruthTriangle


CRITICAL_ENTITY_TERMS = ["payment", "refund", "admin", "auth", "login", "user", "profile"]
SECURITY_TERMS = ["authentication", "admin access", "authentication failed", "unauthorized"]


def has_claim(claims: list[Claim], text_fragment: str) -> bool:
    fragment = text_fragment.lower()
    return any(fragment in claim.claim_text.lower() for claim in claims)


def sources_supporting(claims: list[Claim], text_fragments: list[str]) -> list[Claim]:
    fragments = [fragment.lower() for fragment in text_fragments]
    return [
        claim
        for claim in claims
        if any(fragment in claim.claim_text.lower() for fragment in fragments)
    ]


def _first_match(claims: list[Claim], source: str, text_fragment: str) -> bool:
    return any(claim.source == source and text_fragment.lower() in claim.claim_text.lower() for claim in claims)


def _severity(entity: str, supporting_claims: list[Claim], has_public_internal_mismatch: bool, has_runtime_or_database_mismatch: bool) -> str:
    claim_text = " ".join(claim.claim_text.lower() for claim in supporting_claims)
    if any(term in entity.lower() for term in CRITICAL_ENTITY_TERMS) or any(term in claim_text for term in SECURITY_TERMS):
        return "Critical"
    if has_public_internal_mismatch:
        return "High"
    if has_runtime_or_database_mismatch:
        return "Medium"
    return "Low"


def _confidence(supporting_claims: list[Claim]) -> float:
    count = len({claim.claim_id for claim in supporting_claims})
    if count >= 4:
        return 0.95
    if count == 3:
        return 0.90
    if count == 2:
        return 0.85
    return 0.65


def _recommended_action(drift_type: str, severity: str) -> str:
    if drift_type == "Documentation Drift":
        return "Generate documentation update PR"
    if drift_type == "Implementation Drift":
        return "Create Jira ticket for engineering review"
    if drift_type == "Operational Drift":
        return "Notify engineering team immediately" if severity == "Critical" else "Create Jira ticket for engineering review"
    if drift_type == "Configuration Drift":
        return "Update database or feature flag configuration"
    if drift_type == "No Drift":
        return "No action required"
    return "Manual review required"


def _classify_drift(sources: set[str]) -> str:
    if "Confluence" in sources and ("GitHub" in sources or "Commit" in sources):
        return "Documentation Drift"
    if "Jira" in sources and ("GitHub" in sources or "Commit" in sources):
        return "Implementation Drift"
    if "Logs" in sources:
        return "Operational Drift"
    if "Database" in sources:
        return "Configuration Drift"
    return "Security Drift"


def _has_database_config_mismatch(supporting_claims: list[Claim]) -> bool:
    claim_text = " ".join(claim.claim_text.lower() for claim in supporting_claims)
    has_database_claim = any(claim.source == "Database" for claim in supporting_claims)
    has_public_signal = "endpoint is public" in claim_text or "feature is customer-facing" in claim_text
    has_internal_config = "database config says internal" in claim_text
    has_public_config = "database config says public" in claim_text
    has_internal_implementation = (
        "endpoint is internal-only" in claim_text
        or "access was changed to internal-only" in claim_text
        or "endpoint requires admin access" in claim_text
    )
    has_disabled_feature = "feature is disabled" in claim_text

    return has_database_claim and (
        (has_internal_config and has_public_signal and not has_internal_implementation)
        or (has_public_config and has_internal_implementation)
        or (has_disabled_feature and has_public_signal)
    )


def _build_drift_report(entity: str, supporting_claims: list[Claim], drift_type: str) -> DriftReport:
    sources = {claim.source for claim in supporting_claims}
    text = " ".join(claim.claim_text.lower() for claim in supporting_claims)
    public_internal_mismatch = "public" in text and ("internal-only" in text or "internal" in text)
    runtime_or_database_mismatch = bool({"Logs", "Database"} & sources)
    severity = _severity(entity, supporting_claims, public_internal_mismatch, runtime_or_database_mismatch)
    confidence_score = _confidence(supporting_claims)
    summary = (
        f"Architectural drift detected for {entity}. Requirement sources indicate the endpoint is public "
        "or customer-facing, but implementation/runtime sources indicate restricted access or access failure."
    )
    evidence = [f"{claim.source}: {claim.claim_text} ({claim.evidence})" for claim in supporting_claims]
    return DriftReport(
        drift_id=f"DRIFT-{uuid4().hex[:8].upper()}",
        entity=entity,
        summary=summary,
        drift_type=drift_type,
        severity=severity,
        confidence_score=confidence_score,
        evidence=evidence,
        recommended_action=_recommended_action(drift_type, severity),
        status="Open",
    )


def detect_drift(truth_triangle: TruthTriangle, entity: str) -> DriftReport:
    req = truth_triangle.requirement_view
    impl = truth_triangle.implementation_view
    runtime = truth_triangle.runtime_view
    all_claims = req + impl + runtime
    matched: list[Claim] = []

    def add_matches(claims: list[Claim], fragments: list[str]):
        for claim in sources_supporting(claims, fragments):
            if claim.claim_id not in {existing.claim_id for existing in matched}:
                matched.append(claim)

    if (
        (has_claim(req, "Endpoint is public") or has_claim(req, "Feature is customer-facing"))
        and (has_claim(impl, "Endpoint is internal-only") or has_claim(impl, "Access was changed to internal-only"))
    ):
        add_matches(req, ["Endpoint is public", "Feature is customer-facing"])
        add_matches(impl, ["Endpoint is internal-only", "Access was changed to internal-only"])

    if (
        (has_claim(req, "Endpoint is public") or has_claim(req, "Feature is customer-facing"))
        and has_claim(impl, "Endpoint requires admin access")
    ):
        add_matches(req, ["Endpoint is public", "Feature is customer-facing"])
        add_matches(impl, ["Endpoint requires admin access"])

    if (
        (has_claim(req, "Endpoint is public") or has_claim(req, "Feature is customer-facing"))
        and (has_claim(runtime, "Users cannot access endpoint") or has_claim(runtime, "Authentication failed"))
    ):
        add_matches(req, ["Endpoint is public", "Feature is customer-facing"])
        add_matches(runtime, ["Users cannot access endpoint", "Authentication failed"])

    if has_claim(req, "Endpoint is public") and has_claim(runtime, "Database config says internal"):
        add_matches(req, ["Endpoint is public"])
        add_matches(runtime, ["Database config says internal"])

    if (
        has_claim(req, "Endpoint does not require authentication")
        and (has_claim(impl, "Endpoint requires authentication") or has_claim(impl, "Authentication was added"))
    ):
        add_matches(req, ["Endpoint does not require authentication"])
        add_matches(impl, ["Endpoint requires authentication", "Authentication was added"])

    if has_claim(impl, "Endpoint is public") and has_claim(runtime, "Database config says internal"):
        add_matches(impl, ["Endpoint is public"])
        add_matches(runtime, ["Database config says internal"])

    if (
        (has_claim(impl, "Endpoint is internal-only") or has_claim(impl, "Access was changed to internal-only"))
        and has_claim(runtime, "Database config says public")
    ):
        add_matches(impl, ["Endpoint is internal-only", "Access was changed to internal-only"])
        add_matches(runtime, ["Database config says public"])

    if _first_match(all_claims, "Jira", "Feature is customer-facing") and _first_match(all_claims, "Database", "Feature is disabled"):
        add_matches(req, ["Feature is customer-facing"])
        add_matches(runtime, ["Feature is disabled"])

    if _first_match(all_claims, "Jira", "Feature is customer-facing") and _first_match(all_claims, "Logs", "Endpoint has server error"):
        add_matches(req, ["Feature is customer-facing"])
        add_matches(runtime, ["Endpoint has server error"])

    if _first_match(all_claims, "Commit", "Access was changed to internal-only") and _first_match(all_claims, "Confluence", "Endpoint is public"):
        add_matches(impl, ["Access was changed to internal-only"])
        add_matches(req, ["Endpoint is public"])

    if not matched:
        return DriftReport(
            drift_id=f"DRIFT-{uuid4().hex[:8].upper()}",
            entity=entity,
            summary="No architectural drift detected. Requirement, implementation, and runtime signals appear aligned.",
            drift_type="No Drift",
            severity="None",
            confidence_score=0.00,
            evidence=[],
            recommended_action="No action required",
            status="Closed",
        )

    drift_type = "Configuration Drift" if _has_database_config_mismatch(matched) else _classify_drift({claim.source for claim in matched})
    return _build_drift_report(entity, matched, drift_type)
