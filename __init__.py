from __future__ import annotations


def register(ctx) -> None:
    from .cli import tempo_command, register_cli
    from .tempo_tools import (
        TEMPO_REQUEST_SCHEMA,
        TEMPO_WALLET_STATUS_SCHEMA,
        check_tempo_requirements,
        handle_tempo_request,
        handle_tempo_wallet_status,
    )

    ctx.register_tool(
        name="tempo_wallet_status",
        toolset="tempo_payments",
        schema=TEMPO_WALLET_STATUS_SCHEMA,
        handler=handle_tempo_wallet_status,
        check_fn=check_tempo_requirements,
        description="Inspect the connected Tempo Wallet identity without spending funds.",
        emoji="👛",
    )
    ctx.register_tool(
        name="tempo_request",
        toolset="tempo_payments",
        schema=TEMPO_REQUEST_SCHEMA,
        handler=handle_tempo_request,
        check_fn=check_tempo_requirements,
        description="Make an MPP-aware HTTP request through Tempo Wallet, previewing payment by default.",
        emoji="💳",
    )
    ctx.register_cli_command(
        name="tempo",
        help="Tempo Wallet setup and MPP payment utilities",
        setup_fn=register_cli,
        handler_fn=tempo_command,
        description="Connect a Tempo Wallet and make payment-aware HTTP 402 requests.",
    )
