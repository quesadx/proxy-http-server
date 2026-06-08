"""HTTPS CONNECT tunnel — establishes TCP tunnel and performs bidirectional byte relay using select()."""

import io
import select
import socket

from src.config import CONNECT_TIMEOUT


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
            return

        # Send success response
        wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        wfile.flush()

        # ------------------------------------------------------------------
        # 3. Configure sockets for non-blocking I/O
        # ------------------------------------------------------------------
        client_sock.setblocking(False)
        target_sock.setblocking(False)

        # ------------------------------------------------------------------
        # 4. Bidirectional relay via select.select() (Pitfall 2: avoid deadlock)
        # ------------------------------------------------------------------
        sockets = [client_sock, target_sock]
        while True:
            readable, _, exceptional = select.select(sockets, [], sockets, 30.0)
            if exceptional:
                break
            if not readable:
                # Timeout — both sides idle, keep polling
                continue

            for sock in readable:
                other = target_sock if sock is client_sock else client_sock
                try:
                    data = sock.recv(4096)
                    if not data:
                        # Connection closed by peer
                        return
                    other.sendall(data)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    return

    finally:
        # ------------------------------------------------------------------
        # 5. Cleanup (Pitfall 3: connection leaks)
        # ------------------------------------------------------------------
        if target_sock is not None:
            try:
                target_sock.close()
            except OSError:
                pass
        # NOTE: client_sock is NOT closed here — StreamRequestHandler manages it.
