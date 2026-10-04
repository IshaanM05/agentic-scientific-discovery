"""Append-only Run Ledger (design 6.2): one JSON line per event.

Every agent action, tool call, policy decision and result is recorded with
input/output hashes so any decision can be replayed and audited.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from pathlib import Path

from .. import __version__


def _h(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]


class Ledger:
    def __init__(self, path: Path | None = None, keep_in_memory: bool = True):
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = [] if keep_in_memory else None
        self._lock = threading.Lock()
        self.session_id = uuid.uuid4().hex[:8]

    def log(self, agent: str, action: str, target_id: str | None = None, inputs=None, outputs=None,
            policy: dict | None = None, cost_units: float = 0.0, **extra) -> dict:
        ev = {
            "ts": round(time.time(), 4),
            "session": self.session_id,
            "event_id": uuid.uuid4().hex[:10],
            "agent": agent,
            "action": action,
            "target_id": target_id,
            "inputs_hash": _h(inputs) if inputs is not None else None,
            "outputs_hash": _h(outputs) if outputs is not None else None,
            "inputs": inputs,
            "outputs": outputs,
            "policy": policy,
            "cost_units": cost_units,
            "code_version": __version__,
            **extra,
        }
        with self._lock:
            if self.events is not None:
                self.events.append(ev)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(ev, default=str) + "\n")
        return ev

    def for_target(self, target_id: str) -> list[dict]:
        return [e for e in (self.events or []) if e.get("target_id") == target_id]
