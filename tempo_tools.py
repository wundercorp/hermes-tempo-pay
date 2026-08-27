from __future__ import annotations

from typing import Any

from tools.registry import tool_error, tool_result

from .tempo_client import (
    TempoError,
    build_request_command,
    check_tempo_available,
    find_tempo_binary,
    normalize_timeout_seconds,
    run_captured,
    wallet_status,
)

TEMPO_WALLET_STATUS_SCHEMA = {
    "name": "tempo_wallet_status",
    "description": "Check whether Tempo Wallet is connected and show the current wallet identity. This tool never initiates a payment.",
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

TEMPO_REQUEST_SCHEMA = {
    "name": "tempo_request",
    "description": "Make an HTTP request using Tempo Wallet's MPP-aware client. mode='preview' is the default and uses --dry-run so no payment is made. mode='pay' may spend real funds if the endpoint returns a compatible MPP HTTP 402 challenge. This is MPP, not generic Coinbase x402 compatibility.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "HTTPS endpoint to request. Loopback HTTP is allowed for local development.",
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"],
                "default": "GET",
            },
            "json_body": {
                "description": "Optional JSON body passed to Tempo Wallet with --json.",
            },
            "payment_intent": {
                "type": "string",
                "enum": ["auto", "charge", "session"],
                "default": "auto",
                "description": "Tempo payment intent. auto prefers a reusable session when offered.",
            },
            "mode": {
                "type": "string",
                "enum": ["preview", "pay"],
                "default": "preview",
                "description": "preview performs a dry run and cannot pay. pay allows Tempo Wallet to satisfy a compatible 402 challenge.",
            },
            "timeout_seconds": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
                "default": 120,
            },
        },
        "required": ["url"],
        "additionalProperties": False,
    },
}


def check_tempo_requirements() -> tuple[bool, str]:
    return check_tempo_available()


def _command_failure_message(stderr: str, stdout: str, returncode: int) -> str:
    detail = stderr.strip() or stdout.strip()
    if detail:
        return f"Tempo CLI exited with status {returncode}: {detail}"
    return f"Tempo CLI exited with status {returncode}"


def handle_tempo_wallet_status(args: dict, **kwargs: Any) -> str:
    try:
        result = wallet_status()
    except TempoError as exc:
        return tool_error(str(exc), setup_command="hermes tempo setup")

    if result.returncode != 0:
        return tool_error(
            _command_failure_message(result.stderr, result.stdout, result.returncode),
            connected=False,
            setup_command="hermes tempo setup",
        )
    return tool_result(
        success=True,
        connected=True,
        wallet=result.stdout.strip(),
    )


def handle_tempo_request(args: dict, **kwargs: Any) -> str:
    tempo_binary = find_tempo_binary()
    if not tempo_binary:
        return tool_error(
            "Tempo CLI is not installed",
            setup_command="hermes tempo setup --install",
        )

    mode = str(args.get("mode") or "preview").strip().lower()
    if mode not in {"preview", "pay"}:
        return tool_error("mode must be one of: preview, pay")

    try:
        timeout_seconds = normalize_timeout_seconds(args.get("timeout_seconds"))
        command = build_request_command(
            tempo_binary,
            url=str(args.get("url") or ""),
            method=str(args.get("method") or "GET"),
            json_body=args.get("json_body"),
            payment_intent=str(args.get("payment_intent") or "auto"),
            dry_run=mode == "preview",
        )
        result = run_captured(command, timeout_seconds=timeout_seconds)
    except TempoError as exc:
        return tool_error(str(exc))

    if result.returncode != 0:
        return tool_error(
            _command_failure_message(result.stderr, result.stdout, result.returncode),
            mode=mode,
            payment_allowed=mode == "pay",
            returncode=result.returncode,
        )

    return tool_result(
        success=True,
        mode=mode,
        payment_allowed=mode == "pay",
        output=result.stdout.strip(),
        diagnostics=result.stderr.strip(),
    )
