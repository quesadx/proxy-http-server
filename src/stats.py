"""Thread-safe in-memory metrics aggregation for proxy monitoring."""

import threading
from collections import Counter


class ProxyStats:
    """Thread-safe in-memory metrics aggregation."""

    def __init__(self):
        self._lock = threading.Lock()
        self.total_requests = 0
        self.blocked_requests = 0
        self.allowed_requests = 0
        self.active_connections = 0
        self.domain_counts: Counter = Counter()
        self.status_counts: Counter = Counter()
        self.cache_hits = 0
        self.cache_misses = 0
        self.bytes_transferred = 0
        self.client_counts: Counter = Counter()

    def incr_request(self, blocked: bool = False) -> None:
        with self._lock:
            self.total_requests += 1
            if blocked:
                self.blocked_requests += 1
            else:
                self.allowed_requests += 1

    def record_domain(self, domain: str) -> None:
        with self._lock:
            self.domain_counts[domain] += 1

    def record_status(self, status: int) -> None:
        with self._lock:
            self.status_counts[status] += 1

    def incr_cache_hit(self) -> None:
        with self._lock:
            self.cache_hits += 1

    def incr_cache_miss(self) -> None:
        with self._lock:
            self.cache_misses += 1

    def incr_active(self) -> None:
        with self._lock:
            self.active_connections += 1

    def decr_active(self) -> None:
        with self._lock:
            self.active_connections -= 1

    def add_transfer_bytes(self, n: int) -> None:
        with self._lock:
            self.bytes_transferred += n

    def incr_client(self, ip: str) -> None:
        with self._lock:
            self.client_counts[ip] += 1

    def get_snapshot(self) -> dict:
        with self._lock:
            total_cache = self.cache_hits + self.cache_misses
            total = self.total_requests or 1
            return {
                "total_requests": self.total_requests,
                "blocked_requests": self.blocked_requests,
                "allowed_requests": self.allowed_requests,
                "blocked_pct": round(self.blocked_requests / total * 100, 1),
                "allowed_pct": round(self.allowed_requests / total * 100, 1),
                "active_connections": self.active_connections,
                "top_domains": self.domain_counts.most_common(5),
                "status_codes": dict(self.status_counts.most_common()),
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "hit_rate": round(
                    self.cache_hits / total_cache * 100, 1
                ) if total_cache > 0 else 0.0,
                "bytes_transferred": self.bytes_transferred,
                "clients": dict(self.client_counts.most_common()),
                "active_clients": len(self.client_counts),
            }


proxy_stats = ProxyStats()
