# Plan 02-03: HTTPS SNI Extraction and Filtering — Summary

## Status
✓ **Complete** — 2 tasks executed

## What was built

### Modified `src/connect_tunnel.py:49`

**`tunnel_connect()`** gained two-stage filtering:

**Stage 1 — CONNECT host check** (before connecting to target, `connect_tunnel.py:49`):
- Imports `blocklist`, `BLOCK_PAGE`, `extract_sni` from `src.filter`
- Checks `blocklist.is_blocked(host)` after host/port parsing
- If blocked: writes `BLOCK_PAGE.format(domain=host)` as HTTP 403 response, returns immediately
- No connection attempt to blocked target hosts

**Stage 2 — SNI check** (after 200 response, before relay loop, `connect_tunnel.py:76`):
- Reads raw TLS ClientHello bytes from client socket with 5-second timeout
- Parses SNI via `extract_sni(clienthello_bytes)` (handles malformed/truncated → None)
- If SNI is blocked: closes target socket silently (client sees connection reset)
- If SNI is allowed or absent: forwards ClientHello to target via `target_sock.sendall(clienthello_bytes)` before entering relay loop
- Pitfall 3 (ClientHello re-injection) avoided by forwarding bytes before relay
- Pitfall 1 (ClientHello not yet available) handled by 5-second timeout

## Verification results
- `python -m py_compile src/connect_tunnel.py` → OK
- `python -c "from src.connect_tunnel import tunnel_connect"` → OK
- Raw CONNECT to blocked domain → `HTTP/1.1 403 Forbidden` with block page ✓
- `curl -x http://localhost:8080 https://example.com/` → 200 ✓
- `curl -x http://localhost:8080 https://twitter.com/` → 000 (connection reset, SNI blocked) ✓

## Files changed
- **src/connect_tunnel.py** — added two-stage filtering (CONNECT host + SNI)
