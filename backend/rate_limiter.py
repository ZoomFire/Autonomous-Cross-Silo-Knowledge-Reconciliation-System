from collections import defaultdict, deque
from time import time

from fastapi import HTTPException

from audit_store import log_audit_event
from config import RATE_LIMIT_ENABLED


_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, limit: int, window_seconds: int, user: dict | None = None):
    if not RATE_LIMIT_ENABLED:
        return
    now = time()
    bucket = _BUCKETS[key]
    while bucket and bucket[0] <= now - window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        log_audit_event(
            "rate_limit_exceeded",
            "security",
            resource_name=key,
            status="denied",
            severity="Medium",
            message="Rate limit exceeded.",
            user=user,
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    bucket.append(now)


def reset_rate_limits():
    _BUCKETS.clear()
