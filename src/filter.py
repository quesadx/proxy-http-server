"""Domain and keyword filtering — blocklist with hot-reload and SNI extraction."""

import fnmatch
import os
import struct
import threading
import time
from pathlib import Path


BLOCK_PAGE = (
    "HTTP/1.1 403 Forbidden\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Connection: close\r\n"
    "\r\n"
    "<!DOCTYPE html>\n"
    "<html lang='es'>\n"
    "<head><meta charset='utf-8'>\n"
    "<title>Acceso Bloqueado</title></head>\n"
    "<body>\n"
    "<h1>403 Forbidden</h1>\n"
    "<p>El dominio <strong>{domain}</strong> ha sido bloqueado por el proxy.</p>\n"
    "<hr>\n"
    "<p>EIF208 - Redes, Universidad Nacional (UNA)</p>\n"
    "</body>\n"
    "</html>\n"
)


class Blocklist:
    """Thread-safe, hot-reloadable domain and keyword blocklist."""

    POLL_INTERVAL = 2  # seconds

    def __init__(self, filepath: str = "config/blocked_domains.txt",
                 keyword_filepath: str = "config/blocked_keywords.txt"):
        self._filepath = Path(filepath)
        self._keyword_filepath = Path(keyword_filepath)
        self._lock = threading.Lock()
        self._domains: set[str] = set()
        self._keywords: set[str] = set()
        self._last_mtime: float = 0.0
        self._last_keyword_mtime: float = 0.0
        self._load()
        self._load_keywords()
        self._start_watcher()

    def _load(self) -> None:
        """Parse blocklist file into a set of domain patterns."""
        domains: set[str] = set()
        try:
            text = self._filepath.read_text(encoding="utf-8")
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                domains.add(line.lower())
        except FileNotFoundError:
            pass  # No file -> no blocked domains

        with self._lock:
            self._domains = domains

    def _load_keywords(self) -> None:
        """Parse keyword blocklist file into a set of keywords."""
        keywords: set[str] = set()
        try:
            text = self._keyword_filepath.read_text(encoding="utf-8")
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                keywords.add(line.lower())
        except FileNotFoundError:
            pass

        with self._lock:
            self._keywords = keywords

    def _start_watcher(self) -> None:
        """Start daemon thread for file polling (domains + keywords)."""
        def _watcher():
            while True:
                time.sleep(self.POLL_INTERVAL)
                try:
                    mtime = os.path.getmtime(self._filepath)
                except OSError:
                    mtime = self._last_mtime
                if mtime != self._last_mtime:
                    self._last_mtime = mtime
                    self._load()
                try:
                    kw_mtime = os.path.getmtime(self._keyword_filepath)
                except OSError:
                    kw_mtime = self._last_keyword_mtime
                if kw_mtime != self._last_keyword_mtime:
                    self._last_keyword_mtime = kw_mtime
                    self._load_keywords()

        thread = threading.Thread(target=_watcher, daemon=True)
        thread.start()

    def is_blocked(self, domain: str) -> bool:
        """Return True if domain matches any blocked pattern."""
        domain = domain.lower()
        with self._lock:
            if domain in self._domains:
                return True
            for pattern in self._domains:
                if fnmatch.fnmatch(domain, pattern):
                    return True
        return False

    def has_blocked_keyword(self, url: str) -> bool:
        """Return True if URL contains any blocked keyword."""
        url = url.lower()
        with self._lock:
            for kw in self._keywords:
                if kw in url:
                    return True
        return False


def extract_sni(data: bytes) -> str | None:
    """Extract SNI hostname from raw TLS ClientHello bytes."""
    if len(data) < 5 or data[0] != 0x16:
        return None
    if len(data) < 43:
        return None

    pos = 43
    session_id_len = data[pos]
    pos += 1 + session_id_len
    if pos + 2 > len(data):
        return None

    cipher_len = struct.unpack("!H", data[pos:pos + 2])[0]
    pos += 2 + cipher_len
    if pos + 1 > len(data):
        return None

    comp_len = data[pos]
    pos += 1 + comp_len
    if pos + 2 > len(data):
        return None

    ext_total_len = struct.unpack("!H", data[pos:pos + 2])[0]
    pos += 2
    ext_end = pos + ext_total_len
    if ext_end > len(data):
        ext_end = len(data)

    while pos + 4 <= ext_end:
        ext_type = struct.unpack("!H", data[pos:pos + 2])[0]
        ext_len = struct.unpack("!H", data[pos + 2:pos + 4])[0]
        pos += 4
        if pos + ext_len > ext_end:
            break
        if ext_type == 0x0000:  # server_name
            sni_start = pos + 3
            if sni_start + 2 > pos + ext_len:
                break
            name_len = struct.unpack("!H", data[sni_start:sni_start + 2])[0]
            sni_start += 2
            if sni_start + name_len <= pos + ext_len:
                return data[sni_start:sni_start + name_len].decode("utf-8", errors="replace").lower()
        pos += ext_len

    return None


blocklist = Blocklist()
