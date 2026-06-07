import re
from copy import deepcopy


SECRET_PATTERNS = [
    ("github_token", re.compile(r"ghp_[A-Za-z0-9_]{8,}")),
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._\-]{12,}", re.IGNORECASE)),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----")),
    ("database_url", re.compile(r"\b(?:postgres|postgresql|mysql|mongodb|redis|sqlite)://[^\s'\"<>]+", re.IGNORECASE)),
    ("password", re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*([^\s'\"&]+)")),
    ("secret", re.compile(r"(?i)\b(secret|api[_-]?key|token)\s*[:=]\s*([^\s'\"&]+)")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"\b(?:\+?\d[\d .-]{8,}\d)\b")),
]


def mask_secret(value: str) -> str:
    value = str(value or "")
    if len(value) <= 8:
        return "****"
    if value.startswith("ghp_") and len(value) > 8:
        return f"ghp_****{value[-4:]}"
    return f"{value[:4]}...{value[-4:]}"


def detect_sensitive_data(text: str) -> dict:
    text = str(text or "")
    findings = []
    for finding_type, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(2) if finding_type in {"password", "secret"} and match.lastindex else match.group(0)
            findings.append({"type": finding_type, "matched_preview": mask_secret(raw) if finding_type not in {"email", "phone"} else _redacted_preview(finding_type)})
    return {"has_sensitive_data": bool(findings), "findings": findings[:20]}


def _redacted_preview(finding_type: str) -> str:
    return "[REDACTED_EMAIL]" if finding_type == "email" else "[REDACTED_PHONE]"


def redact_sensitive_text(text: str) -> str:
    text = str(text or "")
    replacements = {
        "email": "[REDACTED_EMAIL]",
        "phone": "[REDACTED_PHONE]",
        "bearer_token": "[REDACTED_TOKEN]",
    }
    for finding_type, pattern in SECRET_PATTERNS:
        replacement = replacements.get(finding_type, "[REDACTED_SECRET]")
        if finding_type in {"password", "secret"}:
            text = pattern.sub(lambda match: f"{match.group(1)}={replacement}", text)
        else:
            text = pattern.sub(replacement, text)
    return text


def sanitize_metadata(metadata):
    if isinstance(metadata, dict):
        cleaned = {}
        for key, value in metadata.items():
            lowered = str(key).lower()
            if any(term in lowered for term in ["password", "secret", "token", "api_key", "access_key"]):
                cleaned[key] = mask_secret(value)
            elif isinstance(value, str):
                cleaned[key] = redact_sensitive_text(value)
            else:
                cleaned[key] = sanitize_metadata(value)
        return cleaned
    if isinstance(metadata, list):
        return [sanitize_metadata(item) for item in metadata]
    if isinstance(metadata, str):
        return redact_sensitive_text(metadata)
    return deepcopy(metadata)
