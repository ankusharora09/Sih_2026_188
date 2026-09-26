"""Simple structured logging utilities.

Uses the standard ``logging`` module with a JSON formatter. The logger is
available as ``logger`` and is attached to FastAPI via middleware to inject a
``request_id`` for each request.
"""

import logging
import uuid
import json
from typing import Any

from fastapi import Request

# Configure the root logger – can be overridden by the application settings.
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("sih2026")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Build a dict with selected attributes.
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Include any extra fields passed via the ``extra`` argument.
        if record.__dict__.get("extra"):
            log_record.update(record.__dict__["extra"])
        return json.dumps(log_record)

# Apply JSON formatter to the default handler.
for handler in logger.handlers:
    handler.setFormatter(JSONFormatter())


def get_request_id(request: Request) -> str:
    """Return an existing request‑id header or generate a new UUID.
    """
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))
