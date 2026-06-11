"""Proxy configuration constants."""

PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8080
BUFFER_SIZE = 65536
CONNECT_TIMEOUT = 30  # seconds
MAX_HEADER_SIZE = 65536  # max header bytes to prevent memory DoS
LOG_FILE = "logs/proxy.log"
LOG_FORMAT = "jsonl"
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 8081
CACHE_TTL = 60       # seconds before cache entry expires
CACHE_MAX_SIZE = 100  # max entries before FIFO eviction
BLOCKLIST_FILE = "config/blocked_domains.txt"
