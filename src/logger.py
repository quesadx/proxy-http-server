"""Thread-safe JSONL request logger."""

import json
import threading
import time
from pathlib import Path


class ProxyLogger:
    """Thread-safe logger writing JSONL or CSV to a file."""

    CSV_HEADER = "timestamp,method,host,path,status,duration,blocked,cache_hit"

    def __init__(self, filepath: str = "logs/proxy.log", fmt: str = "jsonl"):
        self._filepath = Path(filepath)
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._fmt = fmt
        self._header_written = False
        self._file = open(self._filepath, "a", encoding="utf-8")

    def reconfigure(self, filepath: str | None = None, fmt: str | None = None) -> None:
        """Reopen log file with new path and/or format. Thread-safe."""
        with self._lock:
            if filepath is not None:
                self._filepath = Path(filepath)
                self._filepath.parent.mkdir(parents=True, exist_ok=True)
            if fmt is not None:
                self._fmt = fmt
            self._file.close()
            self._file = open(self._filepath, "a", encoding="utf-8")
            self._header_written = False

    def close(self) -> None:
        """Close the log file. Thread-safe."""
        with self._lock:
            self._file.close()

    def log(self, entry: dict) -> None:
        """Write one log line. Thread-safe. Supports jsonl and csv formats."""
        entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        if self._fmt == "csv":
            ordered_keys = ["timestamp", "method", "host", "path", "status", "duration", "blocked", "cache_hit"]
            line = ",".join(str(entry.get(k, "")) for k in ordered_keys) + "\n"
        else:
            line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            if self._fmt == "csv" and not self._header_written:
                if self._file.tell() == 0:
                    self._file.write(self.CSV_HEADER + "\n")
                self._header_written = True
            self._file.write(line)
            self._file.flush()


proxy_logger = ProxyLogger()
