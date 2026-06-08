"""HTTP proxy request handler — parses requests and dispatches to specialized handlers."""

import socketserver

from src.config import MAX_HEADER_SIZE


class ProxyRequestHandler(socketserver.StreamRequestHandler):
    """Handles each proxy connection in its own thread.

    Reads the HTTP request line, headers, and body, then dispatches to
    handle_http (GET/POST) or handle_connect (CONNECT) via lazy imports.
    """

    MAX_HEADER_SIZE = MAX_HEADER_SIZE

    def handle(self):
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

    def handle_http(self, request_line, headers, body):
        """Forward HTTP GET/POST requests via lazy import from http_relay."""
        from http_relay import forward_request  # noqa: F401

        forward_request(self.request, self.wfile, request_line, headers, body)

    def handle_connect(self, request_line):
        """Establish HTTPS CONNECT tunnel via lazy import from connect_tunnel."""
        from connect_tunnel import tunnel_connect  # noqa: F401

        tunnel_connect(self.request, self.wfile, request_line)
