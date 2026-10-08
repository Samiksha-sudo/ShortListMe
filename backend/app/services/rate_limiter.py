import time
from collections import defaultdict, deque

# In-memory, per process (same trade-off as login_limiter): move to Redis if the API is scaled out.
_hits: dict[str, deque[float]] = defaultdict(deque)


def check(key: str, limit: int, window_seconds: int) -> int:
    """Record a hit. Returns 0 if allowed, else the seconds until the oldest hit leaves the window."""
    now = time.monotonic()
    q = _hits[key]
    while q and q[0] <= now - window_seconds:
        q.popleft()
    if len(q) >= limit:
        return max(1, int(q[0] + window_seconds - now) + 1)
    q.append(now)
    return 0


def clear_all() -> None:
    _hits.clear()
