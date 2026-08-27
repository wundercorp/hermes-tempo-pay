from __future__ import annotations

import pytest

from hermes_tempo_payments.tempo_client import TempoError, build_request_command, validate_request_url


def test_https_url_is_allowed():
    assert validate_request_url("https://example.com/resource") == "https://example.com/resource"


def test_loopback_http_is_allowed():
    assert validate_request_url("http://127.0.0.1:8080/resource") == "http://127.0.0.1:8080/resource"
    assert validate_request_url("http://localhost:8080/resource") == "http://localhost:8080/resource"


def test_remote_http_is_rejected():
    with pytest.raises(TempoError):
        validate_request_url("http://example.com/resource")


def test_embedded_credentials_are_rejected():
    with pytest.raises(TempoError):
        validate_request_url("https://user:secret@example.com/resource")


def test_preview_request_builds_dry_run_command():
    command = build_request_command(
        "/usr/bin/tempo",
        url="https://example.com/resource",
        method="POST",
        json_body={"input": "hello"},
        payment_intent="session",
        dry_run=True,
    )
    assert command == [
        "/usr/bin/tempo",
        "request",
        "--dry-run",
        "-X",
        "POST",
        "--payment-intent",
        "session",
        "--json",
        '{"input":"hello"}',
        "https://example.com/resource",
    ]


def test_pay_request_does_not_add_dry_run():
    command = build_request_command(
        "/usr/bin/tempo",
        url="https://example.com/resource",
        dry_run=False,
    )
    assert "--dry-run" not in command
