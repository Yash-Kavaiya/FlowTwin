"""Evidence-linked event history: in memory, mirrored to an append-only JSONL file."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


class EventLog:
    def __init__(self, path: Path | None = None, keep: int = 2000):
        self.path = path
        self.keep = keep
        self.items: list[dict] = []
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, kind: str, **fields) -> dict:
        event = {"event_id": uuid.uuid4().hex[:12], "server_time": time.time(), "kind": kind}
        event.update({k: v for k, v in fields.items() if v is not None})
        self.items.append(event)
        del self.items[:-self.keep]
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        return event

    def recent(self, limit: int) -> list[dict]:
        return self.items[-limit:]
