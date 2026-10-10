"""Bounded, redacted per-run Codex event audit. Never persist raw model output."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
import time


_SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")


def _event_name(value):
    """Only persist short protocol identifiers, never arbitrary event payloads."""
    return value if isinstance(value, str) and _SAFE_NAME.fullmatch(value) else "<invalid>"


class DiagnosticLog:
    MAX_EVENTS = 10000

    def __init__(self, output):
        self.output = Path(output)
        self.path = None
        self.stream = None
        self.started_at = time.monotonic()
        self.count = 0

    def __enter__(self):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        # Exclusive create: never truncate a previous attempt, including failures.
        for _ in range(5):
            path = self.output / f"apf-diagnostic-{stamp}-{secrets.token_hex(4)}.jsonl"
            try:
                self.stream = path.open("x", encoding="utf-8", newline="\n")
                break
            except FileExistsError:
                continue
        else:
            raise FileExistsError("无法创建唯一 APF 诊断日志")
        self.path = path
        self._write({"record": "run.started", "schema": 1})
        return self

    def _write(self, fields):
        data = {"elapsed_ms": round((time.monotonic() - self.started_at) * 1000)}
        data.update(fields)
        self.stream.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.stream.flush()

    def event(self, event):
        self.count += 1
        if self.count > self.MAX_EVENTS:
            if self.count == self.MAX_EVENTS + 1:
                self._write({"record": "events.truncated", "limit": self.MAX_EVENTS})
            return
        kind = _event_name(event.get("type"))
        data = {"record": "codex.event", "event_type": kind}
        if kind in ("item.started", "item.updated", "item.completed"):
            item = event.get("item")
            data["item_type"] = _event_name(item.get("type")) if isinstance(item, dict) else "<invalid>"
        self._write(data)

    def __exit__(self, exc_type, exc, tb):
        if self.stream is not None:
            try:
                result = {"record": "run.finished", "status": "success" if exc_type is None else "failed"}
                if exc_type is not None:
                    # Class name comes from local Python code, not Codex text.
                    result["failure_class"] = exc_type.__name__
                self._write(result)
            finally:
                self.stream.close()
