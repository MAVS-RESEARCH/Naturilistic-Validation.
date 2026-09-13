"""Deterministic structured console events for phase orchestration."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, TextIO


@dataclass(frozen=True)
class StructuredConsole:
    """Expose a console.log interface that writes one canonical JSON object per line."""

    stream: TextIO = sys.stdout

    def log(self, event: str, **fields: Any) -> None:
        if not event or not isinstance(event, str):
            raise ValueError("event must be a non-empty string")
        record = {"event": event, **fields}
        self.stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        self.stream.flush()


console = StructuredConsole()
