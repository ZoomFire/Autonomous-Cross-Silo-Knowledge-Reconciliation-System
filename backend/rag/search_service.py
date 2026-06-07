from datetime import datetime, timezone
from uuid import uuid4

from connector_store import get_source, list_sources
from rag.answer_generator import generate_answer
from rag.chunker import build_chunks_for_source
from rag.retriever import retrieve_relevant_chunks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunk_repo():
    from database.repositories import SourceChunkRepository

    return SourceChunkRepository


def _query_repo():
    from database.repositories import SearchQueryRepository

    return SearchQueryRepository


def index_source(source: dict) -> list[dict]:
    repo = _chunk_repo()
    repo.delete_by_source(source.get("source_id", ""))
    chunks = build_chunks_for_source(source)
    return repo.bulk_create(chunks)


def index_sources_for_workspace(workspace_id: str) -> dict:
    sources = [get_source(source["source_id"]) for source in list_sources(workspace_id)]
    sources = [source for source in sources if source]
    chunks_created = 0
    for source in sources:
        chunks_created += len(index_source(source))
    return {
        "workspace_id": workspace_id,
        "sources_indexed": len(sources),
        "chunks_created": chunks_created,
        "status": "completed",
    }


def index_imported_sources(sources: list[dict]) -> dict:
    chunks_created = 0
    for source in sources:
        chunks_created += len(index_source(source))
    return {"sources_indexed": len(sources), "chunks_created": chunks_created, "status": "completed"}


def search_workspace_sources(workspace_id: str, query: str, source_types: list[str] | None = None, top_k: int = 8, user_id: str | None = None) -> dict:
    chunks = _chunk_repo().search_by_workspace(workspace_id, source_types)
    retrieved = retrieve_relevant_chunks(query, chunks, source_types, top_k)
    answer = generate_answer(query, retrieved)
    query_id = str(uuid4())
    answer["query_id"] = query_id
    _query_repo().save_query({
        "query_id": query_id,
        "workspace_id": workspace_id,
        "user_id": user_id or "",
        "query_text": query,
        "filters": {"source_types": source_types or [], "top_k": top_k},
        "answer": answer,
        "created_at": _now(),
    })
    return answer


def export_answer_markdown(search_query: dict) -> str:
    answer = search_query.get("answer", {})
    lines = [
        "# DriftGuard AI Search Answer",
        "",
        "## Query",
        search_query.get("query_text", answer.get("query", "")),
        "",
        "## Short Answer",
        answer.get("short_answer", ""),
        "",
        "## Confidence",
        str(answer.get("confidence_score", 0)),
        "",
        "## Possible Drift",
        f"- Possible drift: {answer.get('possible_drift', False)}",
        f"- Drift type: {answer.get('possible_drift_type', 'None')}",
        f"- Severity hint: {answer.get('severity_hint', 'Low')}",
        "",
        "## Evidence Summary",
        answer.get("evidence_summary", ""),
        "",
        "## Evidence",
    ]
    for index, item in enumerate(answer.get("evidence", []), start=1):
        lines.extend([
            "",
            f"### Evidence {index}",
            f"- Source: {item.get('source_name', '')}",
            f"- Source type: {item.get('source_type', '')}",
            f"- Score: {item.get('score', 0)}",
            f"- Matched keywords: {', '.join(item.get('matched_keywords', []))}",
            "- Text:",
            "",
            item.get("chunk_text", ""),
        ])
    lines.extend(["", "## Recommended Next Steps"])
    for index, step in enumerate(answer.get("recommended_next_steps", []), start=1):
        lines.append(f"{index}. {step}")
    return "\n".join(lines)
