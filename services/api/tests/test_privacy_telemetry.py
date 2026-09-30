"""
KrishiNet-BRICS - Privacy in Telemetry & Log Sanitization Test Suite.
Verifies that no raw phone numbers, high-precision GPS coordinates, bearer tokens,
or raw image payloads leak into structured logs, audit trails, or OpenTelemetry traces.
"""

import json
import logging
from io import StringIO
import pytest
from app.core.logging import JSONFormatter, PrivacyScrubber


def test_privacy_scrubber_phone_numbers():
    """Verifies that international and domestic phone numbers are sanitized."""
    test_cases = [
        ("Incoming WhatsApp message from +919876543210 received", "[PHONE_REDACTED]"),
        ("SMS notification sent to +5511999998888 for field alert", "[PHONE_REDACTED]"),
        ("Contact farmer at +27-82-123-4567 regarding frost risk", "[PHONE_REDACTED]"),
        ("Direct call initiated to (020) 2567-8901 for support", "[PHONE_REDACTED]"),
    ]

    for raw, expected_token in test_cases:
        scrubbed = PrivacyScrubber.scrub(raw)
        assert expected_token in scrubbed
        assert "+919876543210" not in scrubbed
        assert "+5511999998888" not in scrubbed
        assert "+27-82-123-4567" not in scrubbed


def test_privacy_scrubber_bearer_tokens_and_secrets():
    """Verifies that authorization headers, JWTs, and API keys are redacted."""
    raw_log = (
        "Request failed: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0 "
        "and api_key='sk-live-9823472938472938472938' was rejected."
    )
    scrubbed = PrivacyScrubber.scrub(raw_log)

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed
    assert "sk-live-9823472938472938472938" not in scrubbed
    assert "[TOKEN_REDACTED]" in scrubbed


def test_privacy_scrubber_high_precision_gps():
    """Verifies that high-precision GPS coordinates (>2 decimal places) are redacted to preserve farm sovereignty."""
    raw_log = "Field centroid resolved at 18.5204303, 73.8567437 for soil survey"
    scrubbed = PrivacyScrubber.scrub(raw_log)

    assert "18.5204303, 73.8567437" not in scrubbed
    assert "[COORDINATES_REDACTED]" in scrubbed


def test_privacy_scrubber_image_payloads():
    """Verifies that raw image byte strings or base64 data URIs are not emitted to log streams."""
    base64_img = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/" + ("A" * 150)
    raw_log = f"Inbound image payload: {base64_img}"
    scrubbed = PrivacyScrubber.scrub(raw_log)

    assert "data:image/jpeg;base64" not in scrubbed
    assert "[IMAGE_PAYLOAD_REDACTED]" in scrubbed


def test_json_formatter_structured_log_output():
    """
    Simulates logging pipeline and verifies that JSONFormatter produces valid JSON
    with all sensitive farmer PII and telemetry patterns scrubbed.
    """
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())

    test_logger = logging.getLogger("test.privacy.telemetry")
    test_logger.setLevel(logging.INFO)
    test_logger.handlers = [handler]
    test_logger.propagate = False

    # Emit message with mixed sensitive data
    sensitive_msg = (
        "Farmer +919876543210 dispatched advisory for coordinates 19.123456, 78.987654 "
        "using Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token"
    )
    test_logger.info(sensitive_msg)

    log_output = stream.getvalue().strip()
    assert len(log_output) > 0

    # Parse JSON
    parsed = json.loads(log_output)
    assert parsed["level"] == "INFO"
    assert parsed["name"] == "test.privacy.telemetry"

    # Verify no raw PII in output
    assert "+919876543210" not in parsed["message"]
    assert "19.123456, 78.987654" not in parsed["message"]
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in parsed["message"]

    # Verify replacement tokens are present
    assert "[PHONE_REDACTED]" in parsed["message"]
    assert "[COORDINATES_REDACTED]" in parsed["message"]
    assert "[TOKEN_REDACTED]" in parsed["message"]
