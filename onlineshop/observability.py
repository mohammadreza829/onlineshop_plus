"""JSON logs and request correlation without tokens, query strings or OTP values."""

import contextvars
import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime

from django.conf import settings

request_id = contextvars.ContextVar("request_id", default=None)


def redact(value):
    value = str(value)
    for secret in (settings.SECRET_KEY, settings.SMS_IR_API_KEY, settings.SIMPLE_JWT["SIGNING_KEY"]):
        if secret and len(secret) >= 8:
            value = value.replace(secret, "[REDACTED]")
    value = re.sub(r"(rediss?://)[^/@\s]*:[^/@\s]+@", r"\1[REDACTED]@", value)
    value = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", value, flags=re.I)
    value = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", "[JWT]", value)
    value = re.sub(r"(?<!\d)09\d{9}(?!\d)", "[PHONE]", value)
    value = re.sub(r"(?<!\w)\d{6}(?!\w)", "[SIX_DIGIT_VALUE]", value)
    return value


class JSONFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "request_id": request_id.get(),
        }
        for field in ("status_code", "duration_ms", "method", "path", "dependency", "task_id"):
            if hasattr(record, field):
                value = getattr(record, field)
                payload[field] = redact(value) if isinstance(value, str) else value
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "")
        try:
            correlation = str(uuid.UUID(supplied)) if len(supplied) <= 36 else str(uuid.uuid4())
        except (ValueError, AttributeError):
            correlation = str(uuid.uuid4())
        token = request_id.set(correlation)
        started = time.monotonic()
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = correlation
            logging.getLogger("onlineshop.http").info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                },
            )
            return response
        finally:
            request_id.reset(token)
