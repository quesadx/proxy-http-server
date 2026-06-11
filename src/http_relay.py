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
    parts = request_line.split()
    if len(parts) < 3:
        try:
            wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        return None

    method, full_url, http_version = parts
    parsed = urllib.parse.urlparse(full_url)

    if parsed.hostname is None:
        try:
            wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        return None

    host = parsed.hostname
    port = parsed.port or 80
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

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

    target_sock = None
    try:
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.settimeout(CONNECT_TIMEOUT)
        try:
            target_sock.connect((host, port))
        except (socket.gaierror, ConnectionRefusedError, socket.timeout, OSError):
            try:
                wfile.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            proxy_stats.record_domain(host)
            proxy_stats.record_status(502)
            return None

        new_request_line = f"{method} {path} {http_version}\r\n"

        header_lines: list[str] = []
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in ("proxy-connection", "proxy-authorization"):
                continue
            if key_lower == "host":
                continue
            header_lines.append(f"{key}: {value}")

        header_lines.append(f"Host: {host}:{port}")
        header_lines.append("Connection: close")

        headers_str = "\r\n".join(header_lines) + "\r\n\r\n"

        target_sock.sendall(
            new_request_line.encode("utf-8")
            + headers_str.encode("utf-8")
            + body
        )

        response_data = b""
        while True:
            try:
                data = target_sock.recv(BUFFER_SIZE)
                if not data:
                    break
                response_data += data
                wfile.write(data)
                wfile.flush()
            except (ConnectionResetError, BrokenPipeError, OSError):
                break

        proxy_stats.record_domain(host)
        proxy_stats.record_status(200)
        proxy_stats.add_transfer_bytes(len(response_data))
        return response_data

    finally:
        if target_sock is not None:
            try:
                target_sock.close()
            except OSError:
                pass
