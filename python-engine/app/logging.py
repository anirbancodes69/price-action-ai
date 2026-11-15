"""JSON logging with mandatory secret redaction (docs/engineering/06_ERROR_HANDLING_AND_LOGGING.md §4-5)."""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEY = re.compile(
    r"(pass(word)?|secret|token|authorization|cookie|api[_-]?key|request_token|access_token)", re.I
)
REDACTED = "[REDACTED]"
_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message"}


def redact(value: Any) -> Any:
    """Recursively replace values whose key looks sensitive."""
    if isinstance(value, dict):
        return {k: REDACTED if SENSITIVE_KEY.search(str(k)) else redact(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "service": self.service,
            "event": record.getMessage(),
            "logger": record.name,
        }
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        payload.update(redact(extra))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(service: str, level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
