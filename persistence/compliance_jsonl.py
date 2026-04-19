"""Append-only JSONL audit trail for compliance export (DPDP-oriented).

Stores hashed identifiers and tier decisions; optional truncated text when policy allows.
"""

from __future__ import annotations

import json
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


class ComplianceJSONLLogger:
    """Thread-safe append-only logger."""

    def __init__(self, path: str = "data/compliance_audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, record: Dict[str, Any]) -> None:
        row = dict(record)
        row.setdefault("ts", datetime.now(timezone.utc).isoformat())
        line = json.dumps(row, ensure_ascii=False, default=str) + "\n"
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line)

    def read_last(self, max_lines: int = 5000) -> List[Dict[str, Any]]:
        """Read up to max_lines from end of file (best-effort for large files)."""
        if not self.path.exists():
            return []
        max_lines = max(1, min(max_lines, 100_000))
        with self._lock:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-max_lines:]
        out: List[Dict[str, Any]] = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        return out

    def iter_lines(self) -> Iterator[str]:
        with self._lock:
            if not self.path.exists():
                return
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    yield line


def sha256_text(text: str, max_chars: int = 4096) -> str:
    sample = text[:max_chars] if text else ""
    return hashlib.sha256(sample.encode("utf-8", errors="replace")).hexdigest()
