"""Structured logs: one JSON object per line (SPECS S13.5, NFR-6, NFR-8).

Every line has ``ts``, ``level``, ``session_id``, ``node`` and ``event``; model
calls add ``role``, ``latency_ms``, ``input_tokens`` and ``output_tokens``.
Logs never contain keys, raw headers or prompts: callers log only these
fields, and a filter replaces any configured key value that slips into a
message with ``[redacted]``.
"""

import json
import logging
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

LOGGER_NAME = "blueprint"
FIELDS = (
    "session_id",
    "node",
    "event",
    "role",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "usage_estimated",
    "ttft_ms",
    "export_ms",
    "kind",
    "status",
    "attempt",
    "code",
)

logger = logging.getLogger(LOGGER_NAME)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "session_id": getattr(record, "session_id", None),
            "node": getattr(record, "node", None),
            "event": getattr(record, "event", None) or record.name,
        }
        for field in FIELDS[3:]:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value
        message = record.getMessage()
        if message:
            entry["message"] = message
        if record.exc_info and record.exc_info[1] is not None:
            entry["error"] = f"{type(record.exc_info[1]).__name__}: {record.exc_info[1]}"
        return json.dumps(entry, default=str)


class RedactSecrets(logging.Filter):
    """Replaces configured secret values anywhere in a record with [redacted]."""

    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        self.secrets = sorted({s for s in secrets if s}, key=len, reverse=True)

    def _clean(self, text: str) -> str:
        for secret in self.secrets:
            text = text.replace(secret, "[redacted]")
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if self.secrets:
            record.msg = self._clean(record.getMessage())
            record.args = None
            if record.exc_info and record.exc_info[1] is not None:
                exc = record.exc_info[1]
                record.exc_info = None
                record.msg = f"{record.msg} ({type(exc).__name__}: {self._clean(str(exc))})".strip()
        return True


def configure(
    secrets: Iterable[str], level: int = logging.INFO, stream: Any = None
) -> logging.Handler:
    """Send the app's and uvicorn's logs to stdout as JSON lines, with secrets redacted."""
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactSecrets(secrets))
    for name in (LOGGER_NAME, "uvicorn", "uvicorn.error", "uvicorn.access"):
        target = logging.getLogger(name)
        target.handlers = [handler]
        target.setLevel(level)
        target.propagate = False
    return handler


def log_event(
    event: str,
    *,
    session_id: str | None = None,
    node: str | None = None,
    level: int = logging.INFO,
    message: str = "",
    **fields: Any,
) -> None:
    logger.log(
        level, message, extra={"event": event, "session_id": session_id, "node": node, **fields}
    )
