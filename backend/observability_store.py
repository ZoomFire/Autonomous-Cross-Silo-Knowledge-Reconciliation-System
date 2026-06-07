import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from security_utils import redact_sensitive_text


OBSERVABILITY_DIR = Path(__file__).resolve().parent / "storage" / "observability"
REQUEST_METRICS_FILE = OBSERVABILITY_DIR / "request_metrics.json"
ERROR_EVENTS_FILE = OBSERVABILITY_DIR / "error_events.json"
MAX_REQUEST_METRICS = 1000
MAX_ERROR_EVENTS = 1000
SLOW_THRESHOLD_MS = 1000


def ensure_observability_dir():
    OBSERVABILITY_DIR.mkdir(parents=True, exist_ok=True)
    for path in [REQUEST_METRICS_FILE, ERROR_EVENTS_FILE]:
        if not path.exists():
            _write_list(path, [])


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_list(path: Path) -> list[dict]:
    ensure_observability_dir()
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_list(path: Path, payload: list[dict]):
    OBSERVABILITY_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def save_request_metric(metric: dict) -> dict:
    payload = {
        "request_id": metric.get("request_id", ""),
        "timestamp": metric.get("timestamp") or utc_now(),
        "method": metric.get("method", ""),
        "path": metric.get("path", ""),
        "status_code": int(metric.get("status_code") or 0),
        "duration_ms": round(float(metric.get("duration_ms") or 0), 2),
        "user_id": metric.get("user_id") or "anonymous",
        "workspace_id": metric.get("workspace_id") or "none",
        "slow": bool(metric.get("duration_ms", 0) > SLOW_THRESHOLD_MS),
    }
    metrics = _read_list(REQUEST_METRICS_FILE)
    metrics.append(payload)
    _write_list(REQUEST_METRICS_FILE, metrics[-MAX_REQUEST_METRICS:])
    return payload


def save_error_event(event: dict) -> dict:
    payload = {
        "error_id": event.get("error_id") or str(uuid4()),
        "request_id": event.get("request_id", ""),
        "timestamp": event.get("timestamp") or utc_now(),
        "path": event.get("path", ""),
        "method": event.get("method", ""),
        "status_code": int(event.get("status_code") or 500),
        "message": redact_sensitive_text(event.get("message") or "Internal server error"),
        "error_type": event.get("error_type") or "Exception",
        "user_id": event.get("user_id") or "anonymous",
    }
    events = _read_list(ERROR_EVENTS_FILE)
    events.append(payload)
    _write_list(ERROR_EVENTS_FILE, events[-MAX_ERROR_EVENTS:])
    return payload


def list_request_metrics(filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    metrics = _read_list(REQUEST_METRICS_FILE)
    path_filter = filters.get("path", "")
    status_code = filters.get("status_code", "")
    slow_only = filters.get("slow_only", False)
    if path_filter:
        metrics = [item for item in metrics if path_filter.lower() in item.get("path", "").lower()]
    if status_code:
        metrics = [item for item in metrics if str(item.get("status_code", "")) == str(status_code)]
    if slow_only:
        metrics = [item for item in metrics if item.get("slow") or item.get("duration_ms", 0) > SLOW_THRESHOLD_MS]
    return sorted(metrics, key=lambda item: item.get("timestamp", ""), reverse=True)


def list_error_events() -> list[dict]:
    return sorted(_read_list(ERROR_EVENTS_FILE), key=lambda item: item.get("timestamp", ""), reverse=True)


def _distribution(items: list[dict], key: str) -> dict:
    return dict(Counter(str(item.get(key, "unknown") or "unknown") for item in items))


def _top_slow_endpoints(metrics: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for item in metrics:
        grouped[(item.get("path", ""), item.get("method", ""))].append(float(item.get("duration_ms") or 0))
    rows = [
        {
            "path": path,
            "method": method,
            "average_duration_ms": round(sum(values) / len(values), 2),
            "count": len(values),
        }
        for (path, method), values in grouped.items()
    ]
    return sorted(rows, key=lambda item: item["average_duration_ms"], reverse=True)[:10]


def _top_error_endpoints(metrics: list[dict]) -> list[dict]:
    grouped: Counter[tuple[str, str]] = Counter()
    for item in metrics:
        if int(item.get("status_code") or 0) >= 400:
            grouped[(item.get("path", ""), item.get("method", ""))] += 1
    return [
        {"path": path, "method": method, "count": count}
        for (path, method), count in grouped.most_common(10)
    ]


def build_observability_summary() -> dict:
    metrics = _read_list(REQUEST_METRICS_FILE)
    errors = list_error_events()
    total = len(metrics)
    error_requests = sum(1 for item in metrics if int(item.get("status_code") or 0) >= 400)
    average_duration = round(sum(float(item.get("duration_ms") or 0) for item in metrics) / total, 2) if total else 0
    return {
        "total_requests": total,
        "success_requests": sum(1 for item in metrics if 200 <= int(item.get("status_code") or 0) < 400),
        "error_requests": error_requests,
        "average_duration_ms": average_duration,
        "slow_requests": sum(1 for item in metrics if item.get("slow") or float(item.get("duration_ms") or 0) > SLOW_THRESHOLD_MS),
        "top_slow_endpoints": _top_slow_endpoints(metrics),
        "top_error_endpoints": _top_error_endpoints(metrics),
        "recent_errors": errors[:10],
        "status_code_distribution": _distribution(metrics, "status_code"),
        "method_distribution": _distribution(metrics, "method"),
    }


def build_performance_health() -> dict:
    summary = build_observability_summary()
    total = summary["total_requests"]
    error_rate = round((summary["error_requests"] / total) * 100, 2) if total else 0
    recommendations = []
    if summary["average_duration_ms"] > 500:
        recommendations.append("Review endpoints with elevated average latency.")
    if summary["slow_requests"]:
        recommendations.append("Inspect slow endpoint trends and optimize heavy workflows.")
    if error_rate > 5:
        recommendations.append("Investigate error-prone endpoints and recent backend exceptions.")
    return {
        "status": "healthy" if error_rate <= 5 and summary["average_duration_ms"] <= 1000 else "degraded",
        "average_duration_ms": summary["average_duration_ms"],
        "slow_request_count": summary["slow_requests"],
        "error_rate": error_rate,
        "recommendations": recommendations or ["Performance is within expected limits."],
    }
