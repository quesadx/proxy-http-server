"""Thread-safe JSONL request logger."""

import json
import threading
import time
from pathlib import Path


class ProxyLogger:
    """Thread-safe logger writing JSONL to a file."""

    def __init__(self, filepath: str = "logs/proxy.log"):
        self._filepath = Path(filepath)
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._file = open(self._filepath, "a", encoding="utf-8")

    def log(self, entry: dict) -> None:
        """Write one JSON object as a single line. Thread-safe."""
        entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            self._file.write(line)
            self._file.flush()


proxy_logger = ProxyLogger()
