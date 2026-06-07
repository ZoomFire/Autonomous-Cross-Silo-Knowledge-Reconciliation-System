import re
from datetime import datetime, timezone
from uuid import uuid4


STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "are", "was", "were", "will", "can",
    "into", "have", "has", "had", "not", "but", "you", "our", "their", "your", "when", "where",
    "what", "why", "how", "is", "to", "of", "in", "on", "a", "an", "as", "by", "or", "it",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def extract_keywords(text: str, limit: int = 20) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9_/-]+", (text or "").lower())
    counts: dict[str, int] = {}
    for word in words:
        if len(word) < 3 or word in STOPWORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]]


def build_chunks_for_source(source: dict) -> list[dict]:
    chunks = []
    for index, chunk in enumerate(chunk_text(source.get("content_text", ""))):
        chunks.append({
            "chunk_id": str(uuid4()),
            "workspace_id": source.get("workspace_id", ""),
            "source_id": source.get("source_id", ""),
            "connector_id": source.get("connector_id", ""),
            "source_type": source.get("source_type", "unknown"),
            "source_name": source.get("source_name", ""),
            "chunk_index": index,
            "chunk_text": chunk,
            "token_count": len(chunk.split()),
            "keywords": extract_keywords(chunk),
            "metadata": {
                "source_path": source.get("source_path", ""),
                "source_url": source.get("source_url", ""),
                **(source.get("metadata", {}) or {}),
            },
            "created_at": _now(),
        })
    return chunks

