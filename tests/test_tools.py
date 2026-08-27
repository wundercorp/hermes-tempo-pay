from __future__ import annotations

import json

from hermes_tempo_payments import tempo_tools
from hermes_tempo_payments.tempo_client import TempoCommandResult


def test_tempo_request_defaults_to_preview(monkeypatch):
    monkeypatch.setattr(tempo_tools, "find_tempo_binary", lambda: "/usr/bin/tempo")
    captured = {}

    def fake_run(command, timeout_seconds):
        captured["command"] = command
        captured["timeout_seconds"] = timeout_seconds
        return TempoCommandResult(returncode=0, stdout="preview", stderr="")

    monkeypatch.setattr(tempo_tools, "run_captured", fake_run)
    result = json.loads(tempo_tools.handle_tempo_request({"url": "https://example.com"}))

    assert result["success"] is True
    assert result["mode"] == "preview"
    assert result["payment_allowed"] is False
    assert "--dry-run" in captured["command"]


def test_tempo_request_pay_mode_removes_dry_run(monkeypatch):
    monkeypatch.setattr(tempo_tools, "find_tempo_binary", lambda: "/usr/bin/tempo")
    captured = {}

    def fake_run(command, timeout_seconds):
        captured["command"] = command
        return TempoCommandResult(returncode=0, stdout="paid", stderr="")

    monkeypatch.setattr(tempo_tools, "run_captured", fake_run)
    result = json.loads(
        tempo_tools.handle_tempo_request({"url": "https://example.com", "mode": "pay"})
    )

    assert result["success"] is True
    assert result["mode"] == "pay"
    assert result["payment_allowed"] is True
    assert "--dry-run" not in captured["command"]


def test_tempo_request_missing_cli_has_setup_hint(monkeypatch):
    monkeypatch.setattr(tempo_tools, "find_tempo_binary", lambda: None)
    result = json.loads(tempo_tools.handle_tempo_request({"url": "https://example.com"}))

    assert "error" in result
    assert result["setup_command"] == "hermes tempo setup --install"
