"""HTTP request forwarding — parses proxy requests, forwards to target server, relays response."""

import io
import socket
import urllib.parse

from src.config import BUFFER_SIZE, CONNECT_TIMEOUT
from src.stats import proxy_stats


def forward_request(
    client_sock: socket.socket,
    wfile: io.BufferedWriter,
    request_line: str,
    headers: dict,
    body: bytes,
) -> bytes | None:
    """Forward an HTTP proxy request (GET/POST) to the target server and relay the response.

    Parses the absolute-form URL from the request line (e.g.
    ``GET http://example.com/path HTTP/1.1``), connects to the target server,
    rewrites the request to origin-form (path-only), forwards it, and relays
    the response chunk-by-chunk back to the client.

    Returns the raw response bytes if successful, or None on error.

    Args:
        client_sock: Client TCP socket (used for additional body reads if the
                     initial ``Content-Length``-based read was incomplete).
        wfile: Buffered writer to the client socket.
        request_line: Raw HTTP request line (absolute-form).
        headers: Dictionary of lowercase header names to values.
        body: Already-read request body bytes (may be incomplete).
    """
    # ------------------------------------------------------------------
    # 1. Parse request line
    # ------------------------------------------------------------------
    parts = request_line.split()
    if len(parts) < 3:
        wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        wfile.flush()
        return None

    method, full_url, http_version = parts
    parsed = urllib.parse.urlparse(full_url)

    # Pitfall 5: absolute-form vs origin-form — validate hostname exists
    if parsed.hostname is None:
        wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        wfile.flush()
        return None

    host = parsed.hostname
    port = parsed.port or 80
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    # ------------------------------------------------------------------
    # 2. Ensure full body is read (Pitfall 1)
    # ------------------------------------------------------------------
    content_length = int(headers.get("content-length", "0"))
    if body and len(body) < content_length:
        remaining = content_length - len(body)
        client_sock.settimeout(CONNECT_TIMEOUT)
        try:
            while remaining > 0:
                chunk = client_sock.recv(min(BUFFER_SIZE, remaining))
                if not chunk:
                    break
                body += chunk
                remaining -= len(chunk)
        except (socket.timeout, OSError):
            pass

    # ------------------------------------------------------------------
    # 3. Connect to target server (with 502 on failure)
    # ------------------------------------------------------------------
    target_sock = None
    try:
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.settimeout(CONNECT_TIMEOUT)
        try:
            target_sock.connect((host, port))
        except (socket.gaierror, ConnectionRefusedError, socket.timeout, OSError):
            wfile.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            wfile.flush()
            proxy_stats.record_domain(host)
            proxy_stats.record_status(502)
            return None

        # ------------------------------------------------------------------
        # 4. Reconstruct request in origin-form (path-only)
        # ------------------------------------------------------------------
        new_request_line = f"{method} {path} {http_version}\r\n"

        header_lines: list[str] = []
        for key, value in headers.items():
            key_lower = key.lower()
            # Skip hop-by-hop proxy headers
            if key_lower in ("proxy-connection", "proxy-authorization"):
                continue
            # Skip original host header — will be rewritten below
            if key_lower == "host":
                continue
            header_lines.append(f"{key}: {value}")

        # Rewrite Host header with the target host:port
        header_lines.append(f"Host: {host}:{port}")
        # Force Connection: close for simplicity (Phase 1, Pitfall 4)
        header_lines.append("Connection: close")

        headers_str = "\r\n".join(header_lines) + "\r\n\r\n"

        # ------------------------------------------------------------------
        # 5. Send request to target
        # ------------------------------------------------------------------
        target_sock.sendall(
            new_request_line.encode("utf-8")
            + headers_str.encode("utf-8")
            + body
        )

        # ------------------------------------------------------------------
        # 6. Relay response chunk-by-chunk to client (buffer for caching)
        # ------------------------------------------------------------------
        response_data = b""
        while True:
            try:
                data = target_sock.recv(BUFFER_SIZE)
                if not data:
                    break  # EOF — target closed connection
                response_data += data
                wfile.write(data)
                wfile.flush()
            except (ConnectionResetError, BrokenPipeError, OSError):
                break

        proxy_stats.record_domain(host)
        proxy_stats.record_status(200)
        return response_data

    finally:
        # ------------------------------------------------------------------
        # 7. Cleanup — close target socket (Pitfall 3: connection leaks)
        # ------------------------------------------------------------------
        if target_sock is not None:
            try:
                target_sock.close()
            except OSError:
                pass
        # NOTE: client_sock is NOT closed here — StreamRequestHandler manages it.
