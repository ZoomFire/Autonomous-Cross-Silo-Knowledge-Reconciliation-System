import re
from typing import Iterable

from models import AnalysisRequest, Claim, TruthTriangle


SOURCE_GROUPS = {
    "Confluence": "requirement_view",
    "Jira": "requirement_view",
    "GitHub": "implementation_view",
    "Commit": "implementation_view",
    "Logs": "runtime_view",
    "Database": "runtime_view",
}


def extract_entity(texts: Iterable[str]) -> str:
    combined_text = "\n".join(texts)
    pattern = r"(?<![\w.-])/(?:api|auth|v1|v2|admin)(?:/[A-Za-z0-9._~:-]+)*"
    matches = re.findall(pattern, combined_text)
    return matches[0] if matches else "unknown_entity"


def _contains(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def is_internal_only_context(text: str) -> bool:
    normalized = text.lower()
    public_access_phrases = [
        "without internal permissions",
        "without special internal permissions",
        "does not require internal permissions",
        "no internal permissions required",
        "without internal approval",
        "can be accessed by customers",
    ]
    restricted_access_phrases = [
        "internal-only",
        "internal only",
        "for internal users only",
        "only internal users",
        "restricted to internal users",
        "available only internally",
        "not public",
        "private endpoint",
    ]

    if any(phrase in normalized for phrase in public_access_phrases):
        return False
    return any(phrase in normalized for phrase in restricted_access_phrases)


def _is_jira_internal_only_context(text: str) -> bool:
    return _contains(
        text,
        [
            "internal-only",
            "internal only",
            "admin only",
            "restricted",
            "not customer-facing",
            "not public",
        ],
    )


def _make_claim(
    claim_number: int,
    source: str,
    entity: str,
    claim_type: str,
    claim_text: str,
    confidence_score: float,
    evidence: str,
) -> Claim:
    return Claim(
        claim_id=f"CLM-{claim_number:03d}",
        source=source,
        entity=entity,
        claim_type=claim_type,
        claim_text=claim_text,
        confidence_score=confidence_score,
        evidence=evidence,
    )


def extract_claims(request: AnalysisRequest, entity: str) -> list[Claim]:
    claims: list[Claim] = []

    def add(source, claim_type, claim_text, confidence_score, evidence):
        claims.append(
            _make_claim(
                len(claims) + 1,
                source,
                entity,
                claim_type,
                claim_text,
                confidence_score,
                evidence,
            )
        )

    documentation = request.documentation
    code = request.code
    jira = request.jira
    commit = request.commit
    logs = request.logs
    database_config = request.database_config

    if _contains(documentation, ["public"]):
        add("Confluence", "API Access", "Endpoint is public", 0.90, "Matched keyword: public")
    if is_internal_only_context(documentation):
        add("Confluence", "API Access", "Endpoint is internal-only", 0.90, "Matched internal access keyword")
    if _contains(documentation, ["authentication required", "login required", "requires authentication"]):
        add("Confluence", "Authentication", "Endpoint requires authentication", 0.88, "Matched authentication keyword")
    if _contains(documentation, ["no authentication", "without login", "does not require authentication"]):
        add("Confluence", "Authentication", "Endpoint does not require authentication", 0.88, "Matched no-auth keyword")

    if _contains(code, ["@internal_only", "internal_only", "internalOnly", "private_route"]):
        add("GitHub", "API Access", "Endpoint is internal-only", 0.95, "Internal-only decorator or function found")
    if _contains(code, ["@public", "public_route", "allow_anonymous", "anonymous_allowed"]):
        add("GitHub", "API Access", "Endpoint is public", 0.95, "Public route decorator or keyword found")
    if _contains(code, ["@login_required", "auth_required", "jwt_required", "verify_token", "require_auth", "authenticate"]):
        add("GitHub", "Authentication", "Endpoint requires authentication", 0.95, "Authentication decorator or function found")
    if _contains(code, ["@admin_required", "admin_required", "role_required('admin')"]):
        add("GitHub", "Authorization", "Endpoint requires admin access", 0.95, "Admin authorization rule found")

    if _contains(jira, ["customer", "public", "user-facing", "customer-facing", "ready for production"]):
        add("Jira", "Requirement", "Feature is customer-facing", 0.87, "Customer-facing requirement keyword found")
    if _is_jira_internal_only_context(jira):
        add("Jira", "Requirement", "Feature is internal-only", 0.87, "Internal-only requirement keyword found")
    if _contains(jira, ["bug", "failing", "blocked", "not working"]):
        add("Jira", "Feature Status", "Feature has unresolved issue", 0.85, "Issue status keyword found")

    if _contains(commit, ["added authentication", "added auth", "jwt", "login required", "auth required"]):
        add("Commit", "Code Change", "Authentication was added", 0.88, "Authentication change keyword found")
    if _contains(commit, ["internal-only", "internal only", "restricted access", "security compliance", "made private"]):
        add("Commit", "Code Change", "Access was changed to internal-only", 0.88, "Internal access change keyword found")
    if _contains(commit, ["public access", "made public", "allow customers"]):
        add("Commit", "Code Change", "Access was changed to public", 0.88, "Public access change keyword found")
    if _contains(commit, ["docs updated", "updated documentation", "confluence updated"]):
        add("Commit", "Documentation Change", "Documentation was updated", 0.82, "Documentation update keyword found")

    if _contains(logs, ["403", "Forbidden", "Unauthorized"]):
        add("Logs", "Runtime Behavior", "Users cannot access endpoint", 0.92, "Access denied log found")
    if _contains(logs, ["401"]):
        add("Logs", "Runtime Behavior", "Authentication failed", 0.92, "401 authentication failure found")
    if _contains(logs, ["500", "Internal Server Error", "server error"]):
        add("Logs", "Runtime Behavior", "Endpoint has server error", 0.90, "Server error log found")
    if _contains(logs, ["200 OK", "success", "request completed"]):
        add("Logs", "Runtime Behavior", "Endpoint is working successfully", 0.85, "Successful request log found")

    if _contains(database_config, ["access_type=internal", "access_type: internal", "access=internal", "visibility=internal"]):
        add("Database", "Configuration", "Database config says internal", 0.93, "Internal access config found")
    if _contains(database_config, ["access_type=public", "access_type: public", "access=public", "visibility=public"]):
        add("Database", "Configuration", "Database config says public", 0.93, "Public access config found")
    if _contains(database_config, ["feature_enabled=false", "enabled=false", "is_enabled=false"]):
        add("Database", "Configuration", "Feature is disabled", 0.93, "Feature disabled config found")
    if _contains(database_config, ["feature_enabled=true", "enabled=true", "is_enabled=true"]):
        add("Database", "Configuration", "Feature is enabled", 0.93, "Feature enabled config found")

    return claims


def build_truth_triangle(claims: list[Claim]) -> TruthTriangle:
    return TruthTriangle(
        requirement_view=[claim for claim in claims if SOURCE_GROUPS.get(claim.source) == "requirement_view"],
        implementation_view=[claim for claim in claims if SOURCE_GROUPS.get(claim.source) == "implementation_view"],
        runtime_view=[claim for claim in claims if SOURCE_GROUPS.get(claim.source) == "runtime_view"],
    )
