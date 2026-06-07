import re

from .chunker import extract_keywords


SOURCE_TYPE_BOOSTS = {
    "documentation": ["docs", "documentation", "spec", "api", "public", "requirement"],
    "code": ["code", "function", "class", "decorator", "implementation", "route"],
    "jira": ["ticket", "jira", "requirement", "story", "issue"],
    "logs": ["error", "log", "failing", "failure", "exception", "timeout", "403", "500"],
    "database_config": ["config", "flag", "enabled", "disabled", "database", "internal", "public"],
    "commit": ["commit", "changed", "diff", "merge"],
}

COMPONENT_KEYWORDS = ["payment", "refund", "transaction", "login", "auth", "jwt", "session", "user", "profile", "order", "checkout", "inventory", "notification"]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_/-]+", (text or "").lower())


def score_chunk(query: str, chunk: dict) -> tuple[float, list[str]]:
    query_terms = [term for term in _tokens(query) if len(term) >= 2]
    chunk_text = (chunk.get("chunk_text", "") or "").lower()
    chunk_keywords = set(chunk.get("keywords", []) or extract_keywords(chunk_text))
    matched = []
    score = 0.0

    for term in query_terms:
        if term in chunk_keywords or term in chunk_text.split():
            score += 10
            matched.append(term)
        elif len(term) >= 4 and term in chunk_text:
            score += 4
            matched.append(term)

    source_type = chunk.get("source_type", "unknown")
    for boosted_type, hints in SOURCE_TYPE_BOOSTS.items():
        if source_type == boosted_type and any(hint in query.lower() for hint in hints):
            score += 5 if boosted_type in {"logs", "database_config"} else 3

    if any(keyword in query.lower() and keyword in chunk_text for keyword in COMPONENT_KEYWORDS):
        score += 5

    return score, sorted(set(matched))


def retrieve_relevant_chunks(query: str, chunks: list[dict], source_types: list[str] | None = None, top_k: int = 8) -> list[dict]:
    allowed = set(source_types or [])
    ranked = []
    for chunk in chunks:
        if allowed and chunk.get("source_type") not in allowed:
            continue
        score, matched = score_chunk(query, chunk)
        if score <= 0:
            continue
        ranked.append({
            "chunk_id": chunk.get("chunk_id", ""),
            "source_id": chunk.get("source_id", ""),
            "connector_id": chunk.get("connector_id", ""),
            "source_type": chunk.get("source_type", "unknown"),
            "source_name": chunk.get("source_name", ""),
            "chunk_text": chunk.get("chunk_text", ""),
            "score": round(score, 2),
            "matched_keywords": matched,
            "metadata": chunk.get("metadata", {}),
        })
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[: max(1, top_k)]

