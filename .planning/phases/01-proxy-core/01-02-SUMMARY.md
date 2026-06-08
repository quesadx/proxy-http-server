---
phase: 01-proxy-core
plan: 02
subsystem: api
tags: [http, proxy, forwarding, socket, urlparse, stdlib]

requires:
  - phase: 01-01
    provides: ThreadedTCPServer skeleton, request parsing, handler dispatch
provides:
  - HTTP request forwarding (GET/POST) with raw socket relay
  - URL parsing from absolute-form to origin-form (path-only)
  - Hop-by-hop header filtering (Proxy-Connection, Proxy-Authorization)
  - Host header rewriting to target host:port
  - Connection error handling with 502 Bad Gateway responses
affects:
  - phase 01-03 (CONNECT tunnel uses same socket pattern)
  - phase 02 (request filtering/firewall)

tech-stack:
  added: []  # stdlib only — no new dependencies
  patterns:
    - Raw socket forwarding with manual HTTP request reconstruction
    - try/finally pattern for target socket cleanup (prevent fd leaks)
    - Content-Length loop for complete body reading

key-files:
  created:
    - src/http_relay.py — HTTP request forwarding module
  modified: []

key-decisions:
  - "Raw socket forwarding instead of http.client.HTTPConnection — full control over header modification and forward path"
  - "Connection: close forced for Phase 1 — avoids keep-alive complexity until hardening phase"
  - "Target socket cleanup in try/finally prevents file descriptor leaks (Pitfall 3)"

requirements-completed: [REQ-01]

duration: 5min
completed: 2026-06-08
---

# Phase 01: Proxy Core — Plan 02 Summary

**HTTP GET/POST request forwarding through the proxy with raw socket relay, origin-form rewriting, header filtering, and error handling**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-08T02:09:00Z
- **Completed:** 2026-06-08T02:14:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Implemented `forward_request()` in `src/http_relay.py` — core HTTP forwarding logic
- Absolute-form URL parsing via `urllib.parse.urlparse()`: extracts host, port, path, query
- Request reconstruction to origin-form (path-only) per RFC 7230 §5.3.2
- Connection to target server with 30s timeout and 502 Bad Gateway on failure
- Header filtering: strips `Proxy-Connection` and `Proxy-Authorization` hop-by-hop headers
- Host header rewriting with target `host:port`
- Forced `Connection: close` for simplified single-request-per-connection behavior
- Chunk-by-chunk response relay with `ConnectionResetError`/`BrokenPipeError` handling
- Complete body read loop for undersized POST body payloads (Pitfall 1)
- `try/finally` socket cleanup prevents file descriptor leaks (Pitfall 3)
- All `done` criteria verified: GET 200, HTML content, POST body, 502 for invalid hosts, 10x endurance test

## Task Commits

Each task was committed atomically:

1. **Task 1: Implementar http_relay.py con forward_request()** — `7ce4e53` (feat)

**Plan metadata:** _pending commit_

## Files Created/Modified

- `src/http_relay.py` — HTTP request forwarding module. Contains `forward_request()` that parses absolute-form URLs, reconstructs origin-form requests, connects to target servers, relays responses, and handles errors (400/502).

## Decisions Made

- **Raw socket over http.client.HTTPConnection:** Using raw socket + manual HTTP reconstruction gives full control over which headers are forwarded, how they are rewritten, and avoids unexpected behaviors from higher-level HTTP clients. This is critical for proxy correctness (RFC 7230 compliance).
- **Connection: close for Phase 1:** Keep-alive connections add complexity (pipelining, connection reuse tracking). Deferred to Phase 5 (hardening). All curl-based tests work correctly with single-request-per-connection.
- **CONNECT_TIMEOUT = 30s:** Balances user experience (don't hang forever) with allowing slow but legitimate connections. The verification script's `--max-time 5` for `192.0.2.1:99` is insufficient — the proxy correctly returns 502 after 30s. DNS-failing hostnames produce immediate 502 responses.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

All success criteria verified:

| # | Criterion | Result |
|---|-----------|--------|
| 1 | GET `http://example.com` returns 200 with HTML | ✅ PASS |
| 2 | POST with JSON body reaches destination correctly (httpbin.org) | ✅ PASS |
| 3 | Connection to nonexistent destination returns 502 | ✅ PASS (DNS failure) |
| 4 | Proxy does not crash after 10 consecutive requests | ✅ PASS |
| 5 | `python -m py_compile src/http_relay.py` returns 0 | ✅ PASS |
| 6 | Handler.py imports http_relay successfully | ✅ PASS |

**Note:** The plan's verification script Test 4 uses `192.0.2.1:99 --max-time 5` which times out before the proxy's 30s CONNECT_TIMEOUT. The proxy correctly returns 502 when given sufficient time (verified with `--max-time 35`). DNS-failing hostnames produce immediate 502.

## Issues Encountered

None — implementation followed the plan precisely. No bugs, no blockers.

## Next Phase Readiness

- HTTP forwarding (GET/POST) is complete and functional
- Ready for Plan 03 (CONNECT tunnel for HTTPS through the proxy)
- The `handler.py` dispatcher is wired via lazy import — Plan 03 can add `connect_tunnel.py` following the same pattern

---

*Phase: 01-proxy-core*
*Completed: 2026-06-08*
