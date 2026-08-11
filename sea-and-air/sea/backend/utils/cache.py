"""A minimal in-memory TTL cache. The sea vertical has no database, no
Redis, and no existing caching layer to plug into (see Phase 0/9 of the
integration plan) -- introducing either purely to cache a short-lived
container lookup would be infrastructure the project doesn't need yet.
This is process-local and lost on restart, which is fine for its purpose:
absorbing a user double-submitting or refreshing the same query, not
serving as a durable store.
"""

import time
from dataclasses import dataclass
from threading import Lock
from typing import Generic, TypeVar

V = TypeVar("V")


@dataclass
class _Entry(Generic[V]):
    value: V
    expires_at: float


class TTLCache(Generic[V]):
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, _Entry[V]] = {}
        self._lock = Lock()

    def get(self, key: str) -> V | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.monotonic():
                del self._entries[key]
                return None
            return entry.value

    def set(self, key: str, value: V) -> None:
        with self._lock:
            self._entries[key] = _Entry(value=value, expires_at=time.monotonic() + self._ttl_seconds)
