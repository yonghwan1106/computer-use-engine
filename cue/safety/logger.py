"""CUE audit logger — JSON Lines compliance trail for all agent actions."""

from __future__ import annotations

import atexit
import json
import time
from pathlib import Path
from typing import Any, Optional


class AuditLogger:
    """Append-only JSONL audit logger."""

    def __init__(self, path: str = "cue_audit.jsonl", enabled: bool = True) -> None:
        self.enabled = enabled
        self.path = Path(path)
        self._file = None
        atexit.register(self.close)

    def _ensure_open(self):
        if self._file is None and self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.path, "a", encoding="utf-8")

    def log(
        self,
        tool: str,
        params: dict[str, Any],
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Write one audit record."""
        if not self.enabled:
            return

        record = {
            "ts": time.time(),
            "tool": tool,
            "params": params,
        }
        if result is not None:
            record["result"] = result[:500]  # Truncate long results
        if error is not None:
            record["error"] = error
        if duration_ms is not None:
            record["duration_ms"] = round(duration_ms, 2)

        self._ensure_open()
        if self._file is None:
            return
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()

    def close(self) -> None:
        """Close the log file."""
        if self._file is not None:
            self._file.close()
            self._file = None
