"""HTTP Proxy — entry point and connection handling."""

import argparse
import logging
import signal
import socket as sock
import socketserver
import sys
from pathlib import Path


class ThreadedProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments, overriding config defaults."""
    parser = argparse.ArgumentParser(
        description="HTTP Proxy con Filtrado y Monitoreo — EIF208 UNA",
    )
    parser.add_argument(
        "--host", type=str, default=None,
        help="Proxy listen host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Proxy listen port (default: 8080)",
    )
    parser.add_argument(
        "--dashboard-host", type=str, default=None,
        help="Dashboard listen host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--dashboard-port", type=int, default=None,
        help="Dashboard listen port (default: 8081)",
    )
    parser.add_argument(
        "--blocklist", type=str, default=None,
        help="Path to domain blocklist file (default: config/blocked_domains.txt)",
    )
    parser.add_argument(
        "--log-file", type=str, default=None,
        help="Path to log file (default: logs/proxy.log)",
    )
    parser.add_argument(
        "--log-format", type=str, choices=["jsonl", "csv"], default=None,
        help="Log format (default: jsonl)",
    )
    parser.add_argument(
        "--cache-ttl", type=int, default=None,
        help="Cache TTL in seconds (default: 60)",
    )
    parser.add_argument(
        "--cache-max-size", type=int, default=None,
        help="Max cache entries (default: 100)",
    )
    return parser.parse_args(argv)


def _handle_signal(signum, frame):
    """Handle SIGTERM/SIGINT by raising KeyboardInterrupt for graceful shutdown."""
    logging.info(f"Received signal {signum}, shutting down...")
    raise KeyboardInterrupt


def main():
    args = parse_args()

    import src.config
    if args.host is not None:
        src.config.PROXY_HOST = args.host
    if args.port is not None:
        src.config.PROXY_PORT = args.port
    if args.dashboard_host is not None:
        src.config.DASHBOARD_HOST = args.dashboard_host
    if args.dashboard_port is not None:
        src.config.DASHBOARD_PORT = args.dashboard_port
    if args.blocklist is not None:
        src.config.BLOCKLIST_FILE = args.blocklist
    if args.log_file is not None:
        src.config.LOG_FILE = args.log_file
    if args.log_format is not None:
        src.config.LOG_FORMAT = args.log_format
    if args.cache_ttl is not None:
        src.config.CACHE_TTL = args.cache_ttl
    if args.cache_max_size is not None:
        src.config.CACHE_MAX_SIZE = args.cache_max_size

    sock.setdefaulttimeout(src.config.CONNECT_TIMEOUT)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    if args.blocklist is not None:
        from src.filter import blocklist
        blocklist._filepath = Path(args.blocklist)
        blocklist._load()

    if args.log_file is not None or args.log_format is not None:
        from src.logger import proxy_logger
        proxy_logger.reconfigure(
            filepath=args.log_file or src.config.LOG_FILE,
            fmt=args.log_format or src.config.LOG_FORMAT,
        )

    from src.config import PROXY_HOST, PROXY_PORT, DASHBOARD_HOST, DASHBOARD_PORT
    from src.handler import ProxyRequestHandler

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
    )

    try:
        from src.monitor import start_dashboard
        start_dashboard(host=DASHBOARD_HOST, port=DASHBOARD_PORT)
        logging.info(f"Dashboard available at http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    except ImportError:
        logging.warning("Flask not available — dashboard disabled")

    try:
        with ThreadedProxyServer(
            (PROXY_HOST, PROXY_PORT), ProxyRequestHandler
        ) as server:
            logging.info(f"Proxy server running on {PROXY_HOST}:{PROXY_PORT}")
            server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Proxy server shutting down...")


if __name__ == "__main__":
    # Ensure project root is importable when running src/proxy.py directly
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
