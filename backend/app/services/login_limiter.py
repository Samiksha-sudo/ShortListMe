import time
from collections import defaultdict, deque

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60

# In-memory, per process: enough for a single API instance. Move to the DB or Redis if the API is scaled out.
_failures: dict[str, deque[float]] = defaultdict(deque)


def _recent(key: str) -> deque[float]:
    q = _failures[key]
    cutoff = time.monotonic() - WINDOW_SECONDS
    while q and q[0] < cutoff:
        q.popleft()
    return q


def is_blocked(key: str) -> bool:
    return len(_recent(key)) >= MAX_FAILURES


def record_failure(key: str) -> None:
    _recent(key).append(time.monotonic())


def reset(key: str) -> None:
    _failures.pop(key, None)


def clear_all() -> None:
    _failures.clear()
