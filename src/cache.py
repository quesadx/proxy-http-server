"""In-memory HTTP response cache with TTL and FIFO eviction."""

import threading
import time
from dataclasses import dataclass, field

from src.config import CACHE_TTL, CACHE_MAX_SIZE


@dataclass
class CacheEntry:
    """A cached HTTP response with metadata."""

    status_line: str
    headers: str
    body: bytes
    created_at: float = field(default_factory=time.time)


class ProxyCache:
    """In-memory HTTP response cache with TTL expiry and FIFO eviction.

    Thread-safe via threading.Lock. Only cacheable responses
    (GET 200) should be stored.
    """

    def __init__(self, ttl: int = 60, max_size: int = 100):
        self._ttl = ttl
        self._max_size = max_size
        self._lock = threading.Lock()
        self._data: dict[str, CacheEntry] = {}
        self._insert_order: list[str] = []

    def get(self, key: str) -> CacheEntry | None:
        """Return cached entry if fresh, None if missing or expired."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if time.time() - entry.created_at > self._ttl:
                del self._data[key]
                self._remove_order(key)
                return None
            return entry

    def set(self, key: str, entry: CacheEntry) -> None:
        """Store entry under key. Evict oldest if at capacity."""
        with self._lock:
            if key in self._data:
                self._remove_order(key)
            elif len(self._data) >= self._max_size:
                oldest = self._insert_order.pop(0)
                del self._data[oldest]
            self._data[key] = entry
            self._insert_order.append(key)

    def _remove_order(self, key: str) -> None:
        try:
            self._insert_order.remove(key)
        except ValueError:
            pass


proxy_cache = ProxyCache(ttl=CACHE_TTL, max_size=CACHE_MAX_SIZE)
