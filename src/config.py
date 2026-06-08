"""Proxy configuration constants."""

PROXY_HOST = "localhost"
PROXY_PORT = 8080
BUFFER_SIZE = 65536
CONNECT_TIMEOUT = 30  # seconds
MAX_HEADER_SIZE = 65536  # max header bytes to prevent memory DoS
LOG_FILE = "logs/proxy.log"
LOG_FORMAT = "jsonl"
DASHBOARD_HOST = "localhost"
DASHBOARD_PORT = 8081
CACHE_TTL = 60       # seconds before cache entry expires
CACHE_MAX_SIZE = 100  # max entries before FIFO eviction
