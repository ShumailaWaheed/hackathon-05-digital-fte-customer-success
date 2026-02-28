"""Structured JSON logging middleware for FastAPI.

Outputs structured JSON logs to stdout per FR-036.
Fields: timestamp, level, service, ticket_id, channel, step, duration_ms, message.
"""

import json
import logging
import sys
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for container-native log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "service": getattr(record, "service", "api"),
            "message": record.getMessage(),
        }
        # Optional fields from extra
        for field in ("ticket_id", "channel", "step", "duration_ms", "customer_id"):
            val = getattr(record, field, None)
            if val is not None:
                log_data[field] = val

        if record.exc_info and record.exc_info[1]:
            log_data["error"] = str(record.exc_info[1])
            log_data["traceback"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON formatter to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        logger = logging.getLogger("api.request")
        logger.info(
            "%s %s → %d (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "service": "api",
                "step": "http_request",
                "duration_ms": duration_ms,
            },
        )
        return response
