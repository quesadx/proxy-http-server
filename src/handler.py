"""HTTP proxy request handler — parses requests and dispatches to specialized handlers."""

import logging
import socket
import socketserver
import time

from src.cache import proxy_cache, CacheEntry
from src.config import MAX_HEADER_SIZE
from src.logger import proxy_logger
from src.stats import proxy_stats


class ProxyRequestHandler(socketserver.StreamRequestHandler):
    """Handles each proxy connection in its own thread.

    Reads the HTTP request line, headers, and body, then dispatches to
    handle_http (GET/POST) or handle_connect (CONNECT) via lazy imports.
    """

    MAX_HEADER_SIZE = MAX_HEADER_SIZE

    def handle(self):
        start_time = time.time()
        status = 200
        method = "GET"
        request_line = ""
        self._blocked = False
        self._cached = False
        proxy_stats.incr_active()
        client_ip = self.client_address[0]
        proxy_stats.incr_client(client_ip)
        try:
            request_line = self.rfile.readline()
            if not request_line:
                return
            request_line = request_line.decode("utf-8", errors="replace").strip()
            if not request_line:
                return

            method = request_line.split(" ")[0].upper()

            # Read headers
            self.headers = {}
            while True:
                line = self.rfile.readline()
                if line == b"\r\n" or not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if ":" in decoded:
                    key, value = decoded.split(":", 1)
                    self.headers[key.strip().lower()] = value.strip()

            # Read body if present (non-CONNECT only)
            body = b""
            content_length = int(self.headers.get("content-length", "0"))
            if content_length > 0:
                body = self.rfile.read(content_length)

            if method == "CONNECT":
                self.handle_connect(request_line)
            else:
                self.handle_http(request_line, dict(self.headers), body)
        except (socket.timeout, ConnectionResetError, BrokenPipeError, OSError) as e:
            status = 502
            logging.warning(f"Connection error handling request: {e}")
        except Exception as e:
            status = 502
            logging.error(f"Unexpected error handling request: {e}", exc_info=True)
        finally:
            duration = time.time() - start_time
            headers = getattr(self, 'headers', {})
            host = headers.get("host", "").split(":")[0]
            path = request_line.split(b" ")[1] if b" " in request_line else ""
            response_size = getattr(self, '_response_size', 0)
            proxy_stats.decr_active()
            blocked = getattr(self, '_blocked', False)
            proxy_stats.incr_request(blocked=blocked)
            proxy_stats.record_domain(host or "unknown")
            proxy_stats.record_status(status)
            proxy_logger.log({
                "client_ip": client_ip,
                "method": method,
                "host": host,
                "path": path,
                "status": status,
                "duration": round(duration, 3),
                "blocked": blocked,
                "cache_hit": getattr(self, '_cached', False),
                "response_size": response_size,
            })

    def handle_http(self, request_line, headers, body):
        """Forward HTTP GET/POST requests with domain and keyword filtering and caching."""
        from src.filter import blocklist, BLOCK_PAGE

        host = headers.get("host", "").split(":")[0]
        full_url = request_line.split(b" ")[1] if b" " in request_line else ""

        if host and blocklist.is_blocked(host):
            self._blocked = True
            response = BLOCK_PAGE.format(domain=host)
            self.wfile.write(response.encode("utf-8"))
            self.wfile.flush()
            self._response_size = len(response)
            proxy_stats.add_transfer_bytes(self._response_size)
            return

        if full_url and blocklist.has_blocked_keyword(full_url):
            self._blocked = True
            response = BLOCK_PAGE.format(domain="keyword bloqueado")
            self.wfile.write(response.encode("utf-8"))
            self.wfile.flush()
            self._response_size = len(response)
            proxy_stats.add_transfer_bytes(self._response_size)
            return

        method = request_line.split(" ")[0].upper()
        path = request_line.split(b" ")[1] if b" " in request_line else "/"
        cache_key = f"{host}:{path}"

        cached = proxy_cache.get(cache_key)
        if cached is not None:
            proxy_stats.incr_cache_hit()
            self._cached = True
            response_bytes = (
                cached.status_line.encode("utf-8")
                + b"\r\n"
                + cached.headers.encode("utf-8")
                + b"\r\n\r\n"
                + cached.body
            )
            self.wfile.write(response_bytes)
            self.wfile.flush()
            self._response_size = len(response_bytes)
            proxy_stats.add_transfer_bytes(self._response_size)
            return

        proxy_stats.incr_cache_miss()

        from src.http_relay import forward_request  # noqa: F401

        response_data = forward_request(self.request, self.wfile, request_line, headers, body)

        if response_data is not None:
            self._response_size = len(response_data)
            if method == "GET":
                crlf = response_data.find(b"\r\n\r\n")
                if crlf != -1:
                    status_line = response_data[:response_data.index(b"\r\n")].decode("utf-8", errors="replace")
                    if "200" in status_line:
                        header_bytes = response_data[:crlf]
                        body_bytes = response_data[crlf + 4:]
                        header_str = header_bytes.decode("utf-8", errors="replace")
                        entry = CacheEntry(
                            status_line=status_line,
                            headers=header_str,
                            body=body_bytes,
                        )
                        proxy_cache.set(cache_key, entry)

    def handle_connect(self, request_line):
        """Establish HTTPS CONNECT tunnel via lazy import from connect_tunnel."""
        from src.connect_tunnel import tunnel_connect

        tunnel_connect(self.request, self.wfile, request_line)
