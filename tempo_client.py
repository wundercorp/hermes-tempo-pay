from __future__ import annotations

import ipaddress
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

INSTALLER_URL = "https://tempo.xyz/install"
MAX_INSTALLER_BYTES = 2 * 1024 * 1024
MAX_CAPTURE_CHARS = 30000
DEFAULT_TIMEOUT_SECONDS = 120
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 300
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}
ALLOWED_PAYMENT_INTENTS = {"auto", "charge", "session"}


class TempoError(RuntimeError):
    pass


@dataclass(frozen=True)
class TempoCommandResult:
    returncode: int
    stdout: str
    stderr: str


def _bounded_text(value: str) -> str:
    if len(value) <= MAX_CAPTURE_CHARS:
        return value
    return value[:MAX_CAPTURE_CHARS] + "\n… [truncated]"


def find_tempo_binary() -> str | None:
    discovered = shutil.which("tempo")
    if discovered:
        return discovered

    home = Path.home()
    candidates = (
        home / ".tempo" / "bin" / "tempo",
        home / ".local" / "bin" / "tempo",
        home / "bin" / "tempo",
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def check_tempo_available() -> tuple[bool, str]:
    binary = find_tempo_binary()
    if binary:
        return True, f"Tempo CLI available at {binary}"
    return False, "Tempo CLI is not installed. Run: hermes tempo setup --install"


def _is_loopback_host(hostname: str) -> bool:
    normalized = hostname.strip().lower()
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def validate_request_url(url: str) -> str:
    candidate = str(url or "").strip()
    if not candidate:
        raise TempoError("url is required")

    parsed = urlsplit(candidate)
    if parsed.username is not None or parsed.password is not None:
        raise TempoError("URLs containing embedded credentials are not allowed")
    if not parsed.hostname:
        raise TempoError("url must include a hostname")
    if parsed.scheme == "https":
        return candidate
    if parsed.scheme == "http" and _is_loopback_host(parsed.hostname):
        return candidate
    raise TempoError("tempo_request requires HTTPS, except for loopback HTTP during local development")


def normalize_timeout_seconds(value: Any) -> int:
    if value is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout_seconds = int(value)
    except (TypeError, ValueError) as exc:
        raise TempoError("timeout_seconds must be an integer") from exc
    if timeout_seconds < MIN_TIMEOUT_SECONDS or timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise TempoError(
            f"timeout_seconds must be between {MIN_TIMEOUT_SECONDS} and {MAX_TIMEOUT_SECONDS}"
        )
    return timeout_seconds


def build_request_command(
    tempo_binary: str,
    *,
    url: str,
    method: str = "GET",
    json_body: Any = None,
    payment_intent: str = "auto",
    dry_run: bool = True,
) -> list[str]:
    validated_url = validate_request_url(url)
    normalized_method = str(method or "GET").strip().upper()
    if normalized_method not in ALLOWED_METHODS:
        raise TempoError(f"method must be one of: {', '.join(sorted(ALLOWED_METHODS))}")

    normalized_payment_intent = str(payment_intent or "auto").strip().lower()
    if normalized_payment_intent not in ALLOWED_PAYMENT_INTENTS:
        raise TempoError("payment_intent must be one of: auto, charge, session")

    command = [tempo_binary, "request"]
    if dry_run:
        command.append("--dry-run")
    if normalized_method != "GET":
        command.extend(["-X", normalized_method])
    if normalized_payment_intent != "auto":
        command.extend(["--payment-intent", normalized_payment_intent])
    if json_body is not None:
        command.extend([
            "--json",
            json.dumps(json_body, ensure_ascii=False, separators=(",", ":")),
        ])
    command.append(validated_url)
    return command


def run_captured(command: list[str], *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> TempoCommandResult:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise TempoError(f"Tempo command timed out after {timeout_seconds} seconds") from exc
    except OSError as exc:
        raise TempoError(f"Could not execute Tempo CLI: {exc}") from exc

    return TempoCommandResult(
        returncode=completed.returncode,
        stdout=_bounded_text(completed.stdout or ""),
        stderr=_bounded_text(completed.stderr or ""),
    )


def run_interactive(command: list[str]) -> int:
    try:
        completed = subprocess.run(command, check=False)
    except OSError as exc:
        raise TempoError(f"Could not execute Tempo CLI: {exc}") from exc
    return completed.returncode


def wallet_status(*, timeout_seconds: int = 30) -> TempoCommandResult:
    tempo_binary = find_tempo_binary()
    if not tempo_binary:
        raise TempoError("Tempo CLI is not installed. Run: hermes tempo setup --install")
    return run_captured([tempo_binary, "wallet", "whoami"], timeout_seconds=timeout_seconds)


def wallet_is_connected() -> bool:
    try:
        return wallet_status(timeout_seconds=20).returncode == 0
    except TempoError:
        return False


def install_tempo_launcher() -> None:
    if os.name == "nt":
        raise TempoError("The official Tempo Wallet CLI currently ships Linux and macOS binaries. Use WSL on Windows.")

    request = urllib.request.Request(
        INSTALLER_URL,
        headers={"User-Agent": "hermes-tempo-pay/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            installer = response.read(MAX_INSTALLER_BYTES + 1)
    except Exception as exc:
        raise TempoError(f"Could not download the official Tempo installer: {exc}") from exc

    if not installer:
        raise TempoError("The official Tempo installer returned an empty response")
    if len(installer) > MAX_INSTALLER_BYTES:
        raise TempoError("The official Tempo installer was unexpectedly large; refusing to execute it")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="tempo-install-", suffix=".sh", delete=False) as handle:
            handle.write(installer)
            temporary_path = handle.name
        returncode = run_interactive(["/bin/bash", temporary_path])
        if returncode != 0:
            raise TempoError(f"Tempo installer exited with status {returncode}")
    finally:
        if temporary_path:
            try:
                Path(temporary_path).unlink()
            except OSError:
                pass
