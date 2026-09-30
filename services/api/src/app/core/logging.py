import json
import logging
import re
import sys
from typing import Any, Dict

try:
    from opentelemetry import trace
except ImportError:
    trace = None


class PrivacyScrubber:
    """Sanitizes sensitive farmer PII, telemetry coordinates, tokens, and image payloads from logs."""

    # High-precision coordinates (lat/long with >=3 decimals, optional prefix)
    GPS_REGEX = re.compile(
        r'(?:(?:lat(?:itude)?|centroid_lat)[\s:=]+)?(-?\d{1,3}\.\d{3,10})'
        r'(?:,\s*|\s+(?:and\s+)?(?:lon(?:gitude)?|centroid_lon)[\s:=]+)'
        r'(-?\d{1,3}\.\d{3,10})',
        re.IGNORECASE,
    )
    # JWT / Bearer tokens / API secrets
    TOKEN_REGEX = re.compile(
        r'(Bearer\s+[A-Za-z0-9\-._~+/]+=*)|((?:api[_-]?key|secret|token|password|auth)[\s:=]+["\']?([a-zA-Z0-9_\-]{16,})["\']?)',
        re.IGNORECASE,
    )
    # Base64 image payloads or binary chunks
    IMAGE_BASE64_REGEX = re.compile(r'(data:image\/[a-zA-Z]+;base64,[A-Za-z0-9+/=]{20,})|([A-Za-z0-9+/]{120,}={0,2})')
    # Phone number pattern: requiring either a leading + or standard hyphen/space separated groups of digits (not decimals)
    PHONE_REGEX = re.compile(r'(\+\d{1,4}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5}\b')

    @classmethod
    def scrub(cls, text: str) -> str:
        if not text or not isinstance(text, str):
            return text

        # 1. Redact image bytes / large base64 chunks
        text = cls.IMAGE_BASE64_REGEX.sub("[IMAGE_PAYLOAD_REDACTED]", text)
        # 2. Redact Bearer / API tokens
        text = cls.TOKEN_REGEX.sub("[TOKEN_REDACTED]", text)
        # 3. Redact high-precision GPS coordinates (BEFORE phone numbers so decimals aren't matched as phones)
        text = cls.GPS_REGEX.sub("[COORDINATES_REDACTED]", text)
        # 4. Redact raw phone numbers (minimum 8 digits, avoid float dot decimals)
        def _replace_phone(m):
            matched = m.group(0)
            digits = re.sub(r'\D', '', matched)
            if len(digits) >= 8 and not re.search(r'\d+\.\d{3,}', matched):
                return "[PHONE_REDACTED]"
            return matched

        text = cls.PHONE_REGEX.sub(_replace_phone, text)

        return text


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON including request_id, trace_id, and privacy scrubbing."""

    def format(self, record: logging.LogRecord) -> str:
        raw_msg = record.getMessage()
        scrubbed_msg = PrivacyScrubber.scrub(raw_msg)

        log_payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": scrubbed_msg,
        }

        # Attach request_id if available in record
        if hasattr(record, "request_id"):
            log_payload["request_id"] = PrivacyScrubber.scrub(str(getattr(record, "request_id")))

        # OpenTelemetry Trace Context integration
        if trace:
            current_span = trace.get_current_span()
            if current_span and current_span.get_span_context().is_valid:
                ctx = current_span.get_span_context()
                log_payload["trace_id"] = format(ctx.trace_id, "032x")
                log_payload["span_id"] = format(ctx.span_id, "016x")

        if record.exc_info:
            exc_str = self.formatException(record.exc_info)
            log_payload["exception"] = PrivacyScrubber.scrub(exc_str)

        return json.dumps(log_payload)


def setup_logging(log_level: str = "INFO") -> None:
    """Configures root logger with JSONFormatter for production readiness."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("krishinet.api")
