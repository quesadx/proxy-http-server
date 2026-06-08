# Plan 02-01: Domain Blocklist Loader with Hot-Reload — Summary

## Status
✓ **Complete** — 2 tasks executed

## What was built

### src/filter.py — Full filter module

**`BLOCK_PAGE` constant** — HTTP 403 HTML response with `{domain}` format placeholder in Spanish.

**`Blocklist` class** (`src/filter.py:31`):
- `Blocklist.__init__(filepath)` — loads blocklist from file, starts daemon watcher thread
- `Blocklist._load()` — parses `blocked_domains.txt`, skips `#` comments and blank lines, thread-safe under `threading.Lock`
- `Blocklist._start_watcher()` — daemon thread polling `os.path.getmtime()` every 2 seconds, hot-reloads on change
- `Blocklist.is_blocked(domain)` — exact match + `fnmatch.fnmatch` wildcard matching, thread-safe

**`extract_sni(data: bytes) -> str | None`** (`src/filter.py:101`):
- Parses TLS ClientHello raw bytes per RFC 8446 §4.1.2 and RFC 6066 §3
- Handles truncated/malformed input gracefully → returns None
- Accepts `bytes`, not socket — separates I/O from parsing

**Module-level singleton** (`src/filter.py:146`):
- `blocklist = Blocklist()` — pre-configured instance referencing `config/blocked_domains.txt`

## Verification results
- `python -m py_compile src/filter.py` → OK
- `blocklist.is_blocked('facebook.com')` → True
- `blocklist.is_blocked('example.com')` → False
- `blocklist.is_blocked('ads.google.com')` → True
- `BLOCK_PAGE` contains `{domain}` and `403`
- `extract_sni(b'')` → None (graceful empty data)
- `extract_sni(b'\x16\x03\x03' + b'\x00' * 100)` → None (graceful truncated)
- All symbols importable: `Blocklist`, `BLOCK_PAGE`, `extract_sni`, `blocklist`

## Files changed
- **src/filter.py** — replaced 1-line stub with full 147-line module
