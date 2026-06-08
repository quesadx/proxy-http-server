"""HTTP Proxy — entry point and connection handling."""

import logging
import socketserver
import sys
from pathlib import Path


class ThreadedProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    from src.config import PROXY_HOST, PROXY_PORT
    from src.handler import ProxyRequestHandler

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
    )

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
