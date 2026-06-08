---
phase: 01-proxy-core
plan: 03
subsystem: proxy-core
tags: https, connect-tunnel, select, bidirectional-relay, socket
requires:
  - phase: 01-proxy-core
    provides: ThreadingTCPServer skeleton, HTTP forward handler, config constants
provides:
  - HTTPS CONNECT tunnel with bidirectional relay via select.select()
  - 502 Bad Gateway on connection failure
  - Connection leak prevention via try/finally cleanup
  - Non-blocking socket management for select()
affects: [01-proxy-core]

tech-stack:
  added: []
  patterns:
    - "CONNECT tunnel with select.select() for bidirectional byte relay"
    - "try/finally for socket lifecycle management"
    - "Non-blocking socket setup for I/O multiplexing"

key-files:
  created:
    - src/connect_tunnel.py
  modified: []

key-decisions:
  - "4096-byte recv buffer (common relay size, avoids excessive fragmentation)"
  - "30-second select timeout (keep polling on idle, do not close on inactivity)"
  - "client_sock left open on tunnel exit (StreamRequestHandler manages lifecycle)"
  - "target_sock always closed in finally block (no leaks)"

patterns-established:
  - "Module per protocol feature: connect_tunnel.py for CONNECT, http_relay.py for GET/POST"
  - "try/except/ValueError for port parsing with 400 Bad Request response"
  - "try/except for connection errors with 502 Bad Gateway response"
  - "select timeout continues polling (no timeout = close behavior)"

requirements-completed: [REQ-01]

duration: 4 min
completed: 2026-06-08
---

# Phase 01 Proxy Core — Plan 03: CONNECT Tunnel Summary

**HTTPS CONNECT tunnel with `select.select()` bidirectional relay — handles TLS handshake without deadlock, returns 502 on connection failure**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-08T08:15:00Z (approx)
- **Completed:** 2026-06-08T08:19:10Z
- **Tasks:** 1
- **Files modified:** 1 (created)

## Accomplishments

- Created `src/connect_tunnel.py` with `tunnel_connect()` function
- Parses `CONNECT host:port HTTP/1.1` request line with validation
- Establishes TCP connection to target server with configurable timeout
- Returns `200 Connection Established` on success, `502 Bad Gateway` on failure
- Uses `select.select()` for bidirectional relay (avoids TLS deadlock, Pitfall 2)
- Non-blocking sockets for `select()` I/O multiplexing compatibility
- Proper cleanup in `try/finally` — closes target socket without leaks (Pitfall 3)
- Client socket lifecycle managed by `StreamRequestHandler` (not closed by tunnel)
- Graceful handling of `ConnectionResetError`, `BrokenPipeError`, `OSError`
- Validated with 10 concurrent HTTPS connections through the proxy

## Task Commits

Each task was committed atomically:

1. **Task 1: Implementar connect_tunnel.py con tunnel_connect()** - `835d9c3` (feat)

## Files Created/Modified

- `src/connect_tunnel.py` — CONNECT tunnel module (105 lines):
  - `tunnel_connect(client_sock, wfile, request_line)` — main tunnel function
  - Request line parsing with `400 Bad Request` on invalid format
  - TCP connect to target with `502 Bad Gateway` on failure
  - `select.select()` bidirectional relay loop
  - Socket cleanup in `finally` block
  - All socket operations wrapped in `try/except OSError`

## Decisions Made

- **4096-byte recv buffer:** Appropriate size for relay — avoids excessive fragmentation common with smaller buffers, while keeping per-chunk memory low compared to 64k.
- **30-second select timeout:** Keeps polling when both sides are idle. Does NOT close the tunnel on timeout — only on connection errors or EOF.
- **client_sock NOT closed:** StreamRequestHandler manages the client socket lifecycle. Closing it in the tunnel would cause double-close issues.
- **target_sock always closed in finally:** Guarantees no file descriptor leaks regardless of how the relay loop exits (EOF, error, exception).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Curl `%{http_code}` doesn't propagate 502 for CONNECT failures:** Curl returns `000` as the HTTP code when an HTTPS CONNECT tunnel fails at the proxy level (the tunnel was never established, so there's no target HTTP response to report). The proxy correctly sends `HTTP/1.1 502 Bad Gateway` — verified via curl's verbose output which shows `* CONNECT tunnel failed, response 502`. This is a curl behavior limitation, not a proxy bug.

## Known Stubs

None - all functionality fully implemented and verified.

## Threat Flags

None — no new security-relevant surface introduced beyond the planned CONNECT tunnel.

## Next Phase Readiness

- CONNECT tunnel fully functional for HTTPS proxying
- Module structure matches architecture diagram from research
- Ready for Phase 2 (filtros) or Phase 3 (logging y monitoreo)

## Self-Check: PASSED

- ✅ `src/connect_tunnel.py` exists on disk
- ✅ `.planning/phases/01-proxy-core/01-03-SUMMARY.md` exists on disk
- ✅ `835d9c3` feat commit in history
- ✅ `9b832be` docs commit in history
- ✅ Module compiles: `python -m py_compile src/connect_tunnel.py` returns 0
- ✅ Handler imports connect_tunnel: lazy import resolves correctly
- ✅ HTTPS CONNECT returns 200: `curl -x http://localhost:8080 https://example.com` returns 200 + content
- ✅ Bad Gateway returns 502: proxy sends `HTTP/1.1 502 Bad Gateway` for nonexistent domains
- ✅ 10 concurrent HTTPS connections complete without error
- ✅ Proxy does not crash after tests

---

*Phase: 01-proxy-core*
*Completed: 2026-06-08*
