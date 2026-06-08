"""HTTPS CONNECT tunnel — establishes TCP tunnel and performs bidirectional byte relay using select()."""

import io
import select
import socket
import time

from src.config import CONNECT_TIMEOUT
from src.logger import proxy_logger


def tunnel_connect(
    client_sock: socket.socket,
    wfile: io.BufferedWriter,
    request_line: str,
) -> None:
    """Establish an HTTPS CONNECT tunnel to the target server.

    Parses the ``CONNECT host:port HTTP/1.1`` request line, connects to the
    target server, responds with ``200 Connection Established``, then relays
    bytes bidirectionally using ``select.select()`` until one side closes.

    Args:
        client_sock: Client TCP socket (used for relay, NOT closed here).
        wfile: Buffered writer to the client socket (for status responses).
        request_line: Raw CONNECT request line (e.g. ``CONNECT example.com:443 HTTP/1.1``).
    """
    start_time = time.time()
    outcome = None  # tracked for logging in finally

    # ------------------------------------------------------------------
    # 1. Parse target from request line
    # ------------------------------------------------------------------
    parts = request_line.split()
    if len(parts) < 2:
        wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        wfile.flush()
        return

    target = parts[1]
    if ":" not in target:
        wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        wfile.flush()
        return

    host, port_str = target.rsplit(":", 1)
    try:
        target_port = int(port_str)
    except ValueError:
        wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        wfile.flush()
        return

    # Phase 2: Check CONNECT host against blocklist before connecting
    from src.filter import blocklist, BLOCK_PAGE, extract_sni

    if blocklist.is_blocked(host):
        response = BLOCK_PAGE.format(domain=host)
        wfile.write(response.encode("utf-8"))
        wfile.flush()
        proxy_logger.log({
            "method": "CONNECT",
            "host": host,
            "path": f"{host}:{target_port}",
            "status": 403,
            "duration": round(time.time() - start_time, 3),
            "blocked": True,
            "reason": "connect_host_blocked",
        })
        return

    target_sock = None
    try:
        # ------------------------------------------------------------------
        # 2. Connect to target server
        # ------------------------------------------------------------------
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.settimeout(CONNECT_TIMEOUT)
        try:
            target_sock.connect((host, target_port))
        except (socket.gaierror, ConnectionRefusedError, OSError, socket.timeout):
            wfile.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            wfile.flush()
            proxy_logger.log({
                "method": "CONNECT",
                "host": host,
                "path": f"{host}:{target_port}",
                "status": 502,
                "duration": round(time.time() - start_time, 3),
                "blocked": False,
                "reason": "connection_failed",
            })
            return

        # Send success response
        wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        wfile.flush()

        # Phase 2: Read ClientHello and check SNI
        clienthello_bytes = None
        try:
            client_sock.settimeout(5.0)
            clienthello_bytes = client_sock.recv(4096)
        except (socket.timeout, OSError):
            pass  # No ClientHello - allow through (CONNECT host already cleared)

        if clienthello_bytes:
            sni = extract_sni(clienthello_bytes)
            if sni and blocklist.is_blocked(sni):
                target_sock.close()
                proxy_logger.log({
                    "method": "CONNECT",
                    "host": sni,
                    "path": f"{host}:{target_port}",
                    "status": 403,
                    "duration": round(time.time() - start_time, 3),
                    "blocked": True,
                    "reason": "sni_blocked",
                })
                return
            target_sock.sendall(clienthello_bytes)

        # ------------------------------------------------------------------
        # 3. Configure sockets for non-blocking I/O
        # ------------------------------------------------------------------
        client_sock.setblocking(False)
        target_sock.setblocking(False)

        # ------------------------------------------------------------------
        # 4. Bidirectional relay via select.select()
        # ------------------------------------------------------------------
        sockets = [client_sock, target_sock]
        while True:
            readable, _, exceptional = select.select(sockets, [], sockets, 30.0)
            if exceptional:
                break
            if not readable:
                continue

            for sock in readable:
                other = target_sock if sock is client_sock else client_sock
                try:
                    data = sock.recv(4096)
                    if not data:
                        outcome = "success"
                        return
                    other.sendall(data)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    outcome = "success"
                    return

    finally:
        if outcome == "success":
            proxy_logger.log({
                "method": "CONNECT",
                "host": host,
                "path": f"{host}:{target_port}",
                "status": 200,
                "duration": round(time.time() - start_time, 3),
                "blocked": False,
            })
        if target_sock is not None:
            try:
                target_sock.close()
            except OSError:
                pass
