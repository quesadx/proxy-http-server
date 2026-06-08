# Phase 1: Núcleo del Proxy HTTP — Research

**Researched:** 2026-06-08
**Domain:** HTTP proxy server — TCP concurrency, HTTP parsing, HTTPS tunneling
**Confidence:** HIGH

## Summary

This phase builds the core HTTP proxy server. The proxy listens on `localhost:8080`, accepts concurrent TCP connections, parses HTTP requests (GET, POST, CONNECT), forwards them to target servers, and relays responses back. Standard library only — no external dependencies.

**Key architectural decision:** Use `socketserver.ThreadingMixIn` + `TCPServer` for concurrent connection handling. This is Python's blessed pattern for threaded TCP servers, used by `http.server.ThreadingHTTPServer` internally. For HTTP request parsing, use raw `socket` operations with manual HTTP parsing (request line + headers) — `http.server.BaseHTTPRequestHandler` is designed for *serving* HTTP, not *proxying* it, and does not support CONNECT or URL-based forwarding.

**CONNECT tunnel:** Requires `select.select()` for bidirectional byte relay between client and target — sequential read-write does not work because both sides may send data simultaneously during TLS handshake.

**Primary recommendation:** Build a `ThreadingTCPServer` subclass with a custom `StreamRequestHandler` that dispatches between HTTP forwarding (GET/POST) and CONNECT tunneling. Three plans: (1) TCP server skeleton with threading, (2) HTTP forward handler, (3) CONNECT tunnel handler.

## User Constraints (from CONTEXT.md)

*No CONTEXT.md exists — user chose to continue without discuss-phase. No locked decisions. All choices are at the agent's discretion within project requirements.*

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-01 | Proxy HTTP funcional — servidor TCP concurrente que parsea requests HTTP, reenvía, y soporta CONNECT para HTTPS | Fully addressed. ThreadingTCPServer for concurrency, raw socket parsing for HTTP, select-based relay for CONNECT tunnel. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TCP connection accept | Proxy Server | — | The proxy itself is the server; no upstream tier owns this |
| HTTP request parsing | Proxy Server | — | Raw socket → manual parsing; no offloading possible |
| HTTP request forwarding | Proxy Server | Target Server | Proxy connects to target, forwards modified request |
| HTTPS CONNECT tunneling | Proxy Server | Target Server | Proxy establishes TCP tunnel, relays bytes bidirectionally |
| Concurrency management | Proxy Server | OS (thread scheduler) | threading + socketserver manage thread pool; OS schedules |
| Configuration (port, host) | Proxy Server | — | Simple constants in config.py |

## Standard Stack

### Core

No external packages. All standard library:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `socketserver` | stdlib (3.13) | TCP server with threading mixin | Blessed pattern for concurrent TCP servers in Python |
| `socket` | stdlib (3.13) | Raw TCP connections, CONNECT tunnel relay | Required for low-level network operations |
| `threading` | stdlib (3.13) | Per-connection thread management | Used implicitly by ThreadingMixIn; also for Lock objects |
| `select` | stdlib (3.13) | Bidirectional I/O multiplexing for CONNECT tunnel | Required for non-blocking two-way relay |
| `urllib.parse` | stdlib (3.13) | URL parsing for proxy requests | Parse full URL in request line into host/path |
| `http.client` | stdlib (3.13) | HTTP response parsing helper | `HTTPResponse` for reading server responses |
| `io` | stdlib (3.13) | Buffered I/O for HTTP header parsing | `BufferedReader` wrapping socket |
| `logging` | stdlib (3.13) | Request/error logging | Standard Python logging |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ssl` | stdlib (3.13) | TLS context (future phases) | Phase 2+ for SNI extraction |
| `errno` | stdlib (3.13) | Socket error code constants | Connection error handling (ECONNRESET, etc.) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `socketserver.ThreadingMixIn` + `TCPServer` | Raw `socket` + `threading.Thread` | Raw approach gives more control but duplicates what socketserver does. Mixin is standard Python pattern. |
| `socketserver.ThreadingMixIn` + `TCPServer` | `asyncio.start_server` | Async is more efficient for many connections but adds complexity. Threading is simpler and fine for proxy scale. |
| Manual HTTP parsing | `http.server.BaseHTTPRequestHandler` | `BaseHTTPRequestHandler` parses requests for *serving* (path only), not proxying (full URL). It does not support CONNECT. Manual parsing is required. |
| Raw `socket` for HTTP forwarding | `http.client.HTTPConnection` | `HTTPConnection` handles request formatting and response parsing automatically, which reduces boilerplate. However, raw socket gives full control over header modification. |

**Installation:**

```bash
# No external packages needed for Phase 1. Standard library only.
```

**Version verification:** Python 3.13.13 confirmed available. All stdlib modules verified (`socket`, `select`, `threading`, `socketserver`, `http.client`, `urllib.parse`, `ssl`, `io`, `logging`).

## Package Legitimacy Audit

No external packages required for Phase 1. The project constraint explicitly states "standard library only for proxy." All capabilities use Python stdlib modules.

## Architecture Patterns

### System Architecture Diagram

```
┌──────────┐     TCP connect     ┌──────────────────────┐     TCP connect     ┌──────────────┐
│  Client   │ ──────────────────> │   Proxy Server       │ ──────────────────> │  Target       │
│ (Browser) │     :8080           │   localhost:8080      │    :80 / :443       │  Server       │
└──────────┘                     └──────────────────────┘                     └──────────────┘
       │                                │                                              │
       │                                │                                              │
       │  ┌────────────────────────────┐│                                              │
       │  │ ThreadingTCPServer         ││                                              │
       │  │  ├─ accept()              ││                                              │
       │  │  ├─ spawn thread          ││                                              │
       │  │  └─ ProxyRequestHandler   ││                                              │
       │  │       ├─ handle()         ││                                              │
       │  │       │  ├─ read request  ││                                              │
       │  │       │  │  ├─ GET/POST  ──┼──── forward_request() ──────────────────────>│
       │  │       │  │  │              ││  (modify request line, fix Host header)     │
       │  │       │  │  │              ││       │                                     │
       │  │       │  │  │              ││  <──── response back ───────────────────────│
       │  │       │  │  │              ││  relay response to client                   │
       │  │       │  │  │              ││                                              │
       │  │       │  │  └─ CONNECT    ──┼──── connect to target ───────────────────>  │
       │  │       │  │                 ││  send "200 Connection Established"           │
       │  │       │  │                 ││  ┌──────────────────────┐                   │
       │  │       │  │                 ││  │ select.select() loop │                   │
       │  │       │  │                 ││  │ - client→target relay│                   │
       │  │       │  │                 ││  │ - target→client relay│                   │
       │  │       │  │                 ││  └──────────────────────┘                   │
       │  │       │  └─ close sockets  ││                                              │
```

**Flow:**
1. Client connects to proxy on `localhost:8080`
2. `ThreadingTCPServer.accept()` receives connection, spawns handler thread
3. Handler reads HTTP request from client
4. **GET/POST:** Parse URL → connect to target → modify request (strip full URL, fix Host) → forward → relay response
5. **CONNECT:** Connect to target → send `200 Connection Established` → `select.select()` loop relays bytes bidirectionally until one side closes
6. Cleanup: close client socket and target socket

### Recommended Project Structure

```
src/
├── proxy.py          # Entry point — ThreadingTCPServer setup, main()
├── config.py          # Configuration constants (HOST, PORT)
├── handler.py         # ProxyRequestHandler — request dispatching logic
├── http_relay.py      # HTTP forward: parse request, connect, forward, relay
├── connect_tunnel.py  # CONNECT tunnel: establish TCP tunnel, select loop
├── cache.py           # Placeholder for Phase 4
├── filter.py          # Placeholder for Phase 2
├── logger.py          # Placeholder for Phase 3
└── monitor.py         # Placeholder for Phase 3
```

*Note: Existing stub files (`cache.py`, `filter.py`, `logger.py`, `monitor.py`) from Phase 0 bootstrap remain as placeholders. Phase 1 only modifies `proxy.py`, `config.py`, and adds `handler.py`, `http_relay.py`, `connect_tunnel.py`.*

### Pattern 1: ThreadingTCPServer with Custom Handler

**What:** Use `socketserver.ThreadingMixIn` + `TCPServer` to create a concurrent TCP server. The mixin spawns a new thread per connection automatically.

**When to use:** Any TCP server that needs concurrent connection handling. This is the standard pattern in Python stdlib for threaded servers.

**Example:**
```python
# Source: Python docs — socketserver asynchronous mixins example
# [VERIFIED: docs.python.org/3/library/socketserver.html]

import socketserver
import threading

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = str(self.request.recv(1024), 'ascii')
        cur_thread = threading.current_thread()
        response = bytes("{}: {}".format(cur_thread.name, data), 'ascii')
        self.request.sendall(response)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    HOST, PORT = "localhost", 8080
    with ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler) as server:
        server.serve_forever()
```

### Pattern 2: HTTP Request Parsing for Proxy

**What:** Clients send absolute-form request URLs to proxies (e.g., `GET http://example.com/path HTTP/1.1`). The proxy must parse the full URL, then forward to the target with just the path (`GET /path HTTP/1.1`).

**When to use:** Always for HTTP proxy forwarding. Standard proxy behavior per RFC 7230 §5.3.2.

**Example:**
```python
# Source: RFC 7230 §5.3.2, proxy implementation pattern
# [VERIFIED: docs.python.org/3/library/urllib.parse.html]

from urllib.parse import urlparse

def parse_proxy_request(request_data: bytes):
    """Parse an HTTP proxy request. Returns (method, host, port, path, headers, body)."""
    request_text = request_data.decode('utf-8', errors='replace')
    lines = request_text.split('\r\n')
    
    # Parse request line: "GET http://example.com/path HTTP/1.1"
    method, full_url, http_version = lines[0].strip().split()
    parsed = urlparse(full_url)
    
    host = parsed.hostname
    port = parsed.port or (443 if method == 'CONNECT' else 80)
    path = parsed.path if parsed.path else '/'
    if parsed.query:
        path += '?' + parsed.query
    
    # Parse headers
    headers = {}
    body_start = 0
    for i, line in enumerate(lines[1:], 1):
        if line == '':
            body_start = i + 1
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()
    
    body = '\r\n'.join(lines[body_start:]) if body_start > 0 else ''
    
    return method, host, port, path, headers, body
```

### Pattern 3: CONNECT Tunnel — Bidirectional Relay with select()

**What:** After establishing a TCP connection to the target server and sending `200 Connection Established`, the proxy must relay raw bytes in both directions simultaneously. Using `select.select()` on both sockets allows reading from whichever socket has data available.

**When to use:** Required for HTTPS CONNECT tunneling. Sequential read-write (read from client, write to server, read from server, write to client) will deadlock because the client may send data while waiting for server response (TLS handshake is simultaneous).

**Example:**
```python
# Source: Python select module docs, CONNECT tunnel pattern
# [VERIFIED: docs.python.org/3/library/select.html]

import select

def tunnel_data(client_sock, target_sock):
    """Relay data bidirectionally between client and target until one closes."""
    sockets = [client_sock, target_sock]
    try:
        while True:
            readable, _, exceptional = select.select(sockets, [], sockets, 30.0)
            if exceptional:
                break
            if not readable:
                # Timeout — both sides idle, keep waiting
                continue
            for sock in readable:
                other = target_sock if sock is client_sock else client_sock
                try:
                    data = sock.recv(4096)
                    if not data:
                        return  # Connection closed
                    other.sendall(data)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    return
    finally:
        for sock in sockets:
            try:
                sock.close()
            except OSError:
                pass
```

### Anti-Patterns to Avoid

- **Sequential CONNECT relay:** Reading from client first, then writing to target, then reading from target, then writing to client. This deadlocks during TLS handshake. Always use `select.select()` for bidirectional relay.
- **Single recv() for POST body:** POST/PUT requests may have bodies larger than one `recv()`. Read `Content-Length` header and loop until all bytes received.
- **Sharing sockets between threads without locks:** Each handler thread gets its own socket pair (client + target). Only shared mutable state (connection counters, stats) needs locks.
- **Using http.server.BaseHTTPRequestHandler for proxy:** This class is designed for *serving* HTTP resources, not proxying. It expects path-only requests and does not support CONNECT.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TCP server with threading | Raw accept() loop + thread spawn | `socketserver.ThreadingMixIn` + `TCPServer` | Stdlib handles socket lifecycle, thread management, shutdown coordination |
| I/O multiplexing for CONNECT | Custom poll/epoll wrapper | `select.select()` | Built-in, cross-platform, proven pattern for bidirectional relay |
| URL parsing | Manual split on '/' and ':' | `urllib.parse.urlparse()` | Correctly handles edge cases (auth, query strings, IPv6, default ports) |
| Configuration management | argparse in this phase | Python constants in `config.py` | Phase 5 adds CLI args; keep it simple now |

**Key insight:** The proxy core requires no external packages. Every capability needed (TCP server, concurrency, HTTP parsing, URL parsing, I/O multiplexing) is available in Python's standard library. This is intentional — the project specification requires stdlib-only for the proxy core.

## Common Pitfalls

### Pitfall 1: Incomplete POST Body Reading

**What goes wrong:** For POST requests with body (form data, JSON, file upload), calling `recv()` once only gets a partial body. The proxy forwards a truncated request.

**Why it happens:** TCP is a stream protocol. `recv(4096)` returns *up to* 4096 bytes, not exactly 4096. A POST body may arrive in multiple TCP segments.

**How to avoid:** Parse `Content-Length` header from the request, then keep calling `recv()` in a loop until all `Content-Length` bytes are received (or connection closes). For chunked transfer encoding, parse chunked format.

**Warning signs:** Server receives malformed POST data, truncated JSON, or hangs waiting for more data.

### Pitfall 2: CONNECT Tunnel Deadlock

**What goes wrong:** After sending `200 Connection Established`, the proxy reads from client, writes to target, reads from target, writes to client — and hangs.

**Why it happens:** During TLS handshake, both client and server send data simultaneously. Sequential read-write means the proxy reads from client (gets ClientHello), writes to target, then tries to read from target. But the target may not have sent data yet — it's waiting for more data from client first.

**How to avoid:** Use `select.select()` on both sockets simultaneously. Read from whichever socket has data available, write to the other. Never block on a single socket when both directions need relaying.

**Warning signs:** CONNECT request succeeds with `200`, but browser shows "waiting for tunnel" indefinitely.

### Pitfall 3: Connection Leaks

**What goes wrong:** After a request completes or errors, client sockets or target sockets remain open. Eventually the proxy runs out of file descriptors.

**Why it happens:** Exception in the handler skips cleanup code. `try/finally` blocks are omitted for socket close operations.

**How to avoid:** Always use `try/finally` (or context managers with `contextlib.closing()`) to ensure both client and target sockets are closed in all code paths, including exception handlers.

**Warning signs:** Proxy works for a few requests, then stops accepting new connections. `lsof` shows many CLOSE_WAIT sockets.

### Pitfall 4: Missing Connection Header Handling

**What goes wrong:** Client sends `Connection: keep-alive`, proxy forwards request and keeps target socket open expecting another request. But the proxy is handling one request per connection.

**Why it happens:** The proxy doesn't modify or add `Connection` headers. If it keeps the socket open, the next client request on the same connection won't be handled correctly.

**How to avoid:** For Phase 1, add `Proxy-Connection: close` or handle each connection as single-request. In the forwarded request, set `Connection: close` to ensure target server closes after response. HTTP/1.1 persistent connections can be supported, but add significant complexity.

**Warning signs:** Client reuses connection for a second request that gets mixed with first request's response.

### Pitfall 5: Absolute-Form vs Origin-Form URL Confusion

**What goes wrong:** Proxy receives a request with a path-only URL (`GET /path HTTP/1.1`) instead of absolute-form (`GET http://example.com/path HTTP/1.1`), and fails to parse it.

**Why it happens:** Some clients or intermediate proxies send requests without the full URL. The proxy may be receiving its own forwarded request from a parent proxy.

**How to avoid:** Check if the request line contains a full URL (starts with `http://` or `https://`). If not, it's an origin-form request — read the `Host` header to determine the target. This also applies to CONNECT (always absolute-form: `CONNECT host:port HTTP/1.1`).

**Warning signs:** `urlparse` returns `hostname=None` for a path-only request, causing `AttributeError`.

## Code Examples

### Basic Threaded Proxy Server Skeleton

```python
# Source: Python docs — socketserver example adapted for proxy
# [VERIFIED: docs.python.org/3/library/socketserver.html]

import socketserver
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class ProxyRequestHandler(socketserver.StreamRequestHandler):
    """Handles each proxy connection in its own thread."""
    
    def handle(self):
        """Main entry point for handling a proxy connection."""
        try:
            # Read the initial request line and headers
            request_line = self.rfile.readline().decode('utf-8').strip()
            if not request_line:
                return
            
            method = request_line.split(' ')[0].upper()
            
            if method == 'CONNECT':
                self.handle_connect(request_line)
            else:
                self.handle_http(request_line)
        except Exception as e:
            logging.error(f"Error handling request: {e}")
        finally:
            # Connection cleanup happens automatically when handle() returns
            pass
    
    def handle_http(self, request_line):
        """Forward HTTP GET/POST requests."""
        # Read headers
        headers = {}
        while True:
            line = self.rfile.readline().decode('utf-8').strip()
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Parse target URL from request line
        from urllib.parse import urlparse
        parts = request_line.split()
        if len(parts) < 3:
            return
        _, full_url, http_version = parts
        parsed = urlparse(full_url)
        
        target_host = parsed.hostname
        target_port = parsed.port or 80
        target_path = parsed.path or '/'
        if parsed.query:
            target_path += '?' + parsed.query
        
        # Read body if present
        content_length = int(headers.get('content-length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Connect to target
        import socket
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.settimeout(30)
        try:
            target_sock.connect((target_host, target_port))
            
            # Rebuild request with origin-form (path only)
            new_request = f"{parts[0]} {target_path} {http_version}\r\n"
            for key, value in headers.items():
                if key.lower() == 'host':
                    new_request += f"Host: {target_host}:{target_port}\r\n"
                elif key.lower() not in ('proxy-connection', 'proxy-authorization'):
                    new_request += f"{key}: {value}\r\n"
            new_request += "\r\n"
            
            target_sock.sendall(new_request.encode() + body)
            
            # Relay response back to client
            while True:
                data = target_sock.recv(65536)
                if not data:
                    break
                self.wfile.write(data)
                self.wfile.flush()
        finally:
            target_sock.close()
    
    def handle_connect(self, request_line):
        """Establish HTTPS CONNECT tunnel."""
        import socket
        import select
        
        # Parse host:port
        parts = request_line.split()
        if len(parts) < 2:
            return
        target = parts[1]
        target_host, target_port_str = target.split(':')
        target_port = int(target_port_str)
        
        # Connect to target server
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.settimeout(30)
        try:
            target_sock.connect((target_host, target_port))
            # Send success response
            self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self.wfile.flush()
        except Exception as e:
            self.wfile.write(f"HTTP/1.1 502 Bad Gateway\r\n\r\n".encode())
            self.wfile.flush()
            target_sock.close()
            return
        
        # Bidirectional relay
        self.request.setblocking(0)
        target_sock.setblocking(0)
        
        try:
            while True:
                readable, _, exceptional = select.select(
                    [self.request, target_sock], [], [self.request, target_sock], 30.0
                )
                if exceptional:
                    break
                if not readable:
                    continue  # timeout, keep polling
                for sock in readable:
                    other = target_sock if sock is self.request else self.request
                    try:
                        data = sock.recv(4096)
                        if not data:
                            return
                        other.sendall(data)
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        return
        finally:
            target_sock.close()


class ThreadedProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    HOST, PORT = "localhost", 8080
    with ThreadedProxyServer((HOST, PORT), ProxyRequestHandler) as server:
        logging.info(f"Proxy server running on {HOST}:{PORT}")
        server.serve_forever()
```

### Config Module Pattern

```python
# Source: Python standard practice
# [VERIFIED: N/A — standard config pattern]

# config.py
"""Proxy configuration constants."""

PROXY_HOST = "localhost"
PROXY_PORT = 8080
BUFFER_SIZE = 65536
CONNECT_TIMEOUT = 30  # seconds
MAX_HEADER_SIZE = 65536  # max header bytes to prevent memory DoS
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncore` (deprecated) | `asyncio` / `socketserver.ThreadingMixIn` | Python 3.6+ (asyncore removed in 3.12) | Projects should not use asyncore (removed in Python 3.12) |
| Single-threaded proxies | Multi-threaded / async proxies | Always best practice | Production proxies need concurrency |
| `httplib` (Python 2) | `http.client` (Python 3) | Python 3.0 | All proxy code uses Python 3 imports |

**Deprecated/outdated:**
- `asyncore` module: Removed in Python 3.12. Do not use.
- Python 2 `httplib`: Not available in Python 3. Use `http.client`.
- `threading.Thread` with manual accept loop: Use `socketserver.ThreadingMixIn` instead.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Project uses `localhost:8080` as default proxy address | Standard Stack | Trivial — config constant change |
| A2 | No authentication is required for the proxy in Phase 1 | Architecture | Proxy works but without auth — acceptable for dev/edu project |
| A3 | HTTP/1.1 persistent connections are not required for Phase 1 | Code Examples | Missing performance optimization but functionally complete |
| A4 | POST body reading via Content-Length is sufficient (no chunked encoding handling needed for Phase 1) | Common Pitfalls | Some POST requests may fail if server uses chunked encoding in request |

## Open Questions

1. **Should we handle HTTP/1.1 persistent connections (Connection: keep-alive)?**
   - What we know: The proxy currently closes after one request. Browsers may attempt to reuse connections.
   - What's unclear: Whether the demo/test scenario will use connection reuse. Phase 1 success criteria use individual requests via curl.
   - Recommendation: Defer to Phase 5 (hardening). Keep single-request-per-connection for now.

2. **Should we support IPv6 target addresses?**
   - What we know: The socket code currently uses `AF_INET` (IPv4 only).
   - What's unclear: Whether IPv6 is needed for any demo targets.
   - Recommendation: Add IPv6 support if needed. Use `socket.getaddrinfo()` for resolution instead of hardcoded `AF_INET`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Proxy runtime | ✓ | 3.13.13 | — |
| `socket` module | TCP connections | ✓ | stdlib | — |
| `socketserver` module | TCP server | ✓ | stdlib | — |
| `threading` module | Concurrency | ✓ | stdlib | — |
| `select` module | CONNECT tunnel | ✓ | stdlib | — |
| `urllib.parse` | URL parsing | ✓ | stdlib | — |
| `http.client` | HTTP utilities | ✓ | stdlib | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

*Skipped — workflow.nyquist_validation is explicitly false in .planning/config.json.*

## Security Domain

*Skipped — security_enforcement is explicitly false in .planning/config.json. No authentication, encryption, or access control is required for Phase 1 of this educational proxy project.*

## Sources

### Primary (HIGH confidence)
- [Python 3.14.5 docs: `socketserver` module](https://docs.python.org/3/library/socketserver.html) — ThreadingMixIn pattern, TCPServer, StreamRequestHandler, examples
- [Python 3.14.5 docs: `select` module](https://docs.python.org/3/library/select.html) — `select.select()` for I/O multiplexing in CONNECT tunnel
- [Python 3.14.5 docs: `urllib.parse`](https://docs.python.org/3/library/urllib.parse.html) — `urlparse()` for URL parsing
- [Python 3.14.5 docs: `threading` module](https://docs.python.org/3/library/threading.html) — Lock objects, thread safety patterns
- [Python 3.14.5 docs: `http.server` module](https://docs.python.org/3/library/http.server.html) — ThreadingHTTPServer (confirms mixing pattern)
- [RFC 7230 §5.3.2](https://datatracker.ietf.org/doc/html/rfc7230#section-5.3.2) — Absolute-form request URI for proxies
- [RFC 9110 §9.3.6](https://datatracker.ietf.org/doc/html/rfc9110#section-9.3.6) — CONNECT method specification

### Secondary (MEDIUM confidence)
- [W3Tutorials (2026-02): Simple Python HTTP Proxy](https://www.w3tutorials.net/blog/seriously-simple-python-http-proxy/) — Verified pattern for request line parsing, Host header modification
- [Python CPython source: Lib/http/server.py](https://github.com/python/cpython/blob/main/Lib/http/server.py) — Reference implementation confirms ThreadingHTTPServer uses same socketserver pattern

### Tertiary (LOW confidence)
- [Stack Overflow: CONNECT method proxy server socket](https://stackoverflow.com/questions/28495938/how-do-i-respond-to-a-connect-method-request-in-a-proxy-server-using-socket-in) — CONNECT tunnel pattern with select.select()
- [Runebook: HTTP CONNECT RFC 9110](https://runebook.dev/en/docs/http/rfc9110/section-9.3.6) — CONNECT method details

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All stdlib, verified on Python 3.13.13
- Architecture: HIGH — `socketserver.ThreadingMixIn` is the standard Python pattern
- Pitfalls: HIGH — Well-documented from production proxy experience and community patterns

**Research date:** 2026-06-08
**Valid until:** 2026-08-01 (stable stdlib — no version churn risk)
