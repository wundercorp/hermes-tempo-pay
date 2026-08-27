from __future__ import annotations

import argparse
import sys

from .tempo_client import (
    TempoError,
    build_request_command,
    find_tempo_binary,
    install_tempo_launcher,
    run_interactive,
    wallet_is_connected,
    wallet_status,
)


def register_cli(parser: argparse.ArgumentParser) -> None:
    subcommands = parser.add_subparsers(dest="tempo_command")

    setup_parser = subcommands.add_parser("setup", help="Install Tempo Wallet if requested and connect a wallet")
    setup_parser.add_argument(
        "--install",
        action="store_true",
        help="Download and execute the official installer from https://tempo.xyz/install when Tempo is missing",
    )
    setup_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Use Tempo's remote-host login flow instead of opening a browser locally",
    )
    setup_parser.add_argument(
        "--fund",
        action="store_true",
        help="Launch Tempo Wallet's funding flow after login",
    )

    subcommands.add_parser("status", help="Show the connected Tempo Wallet identity")

    fund_parser = subcommands.add_parser("fund", help="Launch Tempo Wallet's funding flow")
    fund_parser.add_argument("--no-browser", action="store_true")

    request_parser = subcommands.add_parser("request", help="Make a payment-aware MPP HTTP request")
    request_parser.add_argument("url")
    request_parser.add_argument("-X", "--request", dest="method", default="GET")
    request_parser.add_argument("--json", dest="json_body", default=None)
    request_parser.add_argument("--payment-intent", choices=("auto", "charge", "session"), default="auto")
    request_parser.add_argument("--pay", action="store_true", help="Allow payment. Without this flag the request is a dry-run preview.")

    parser.set_defaults(func=tempo_command)


def _print_status() -> int:
    try:
        result = wallet_status()
    except TempoError as exc:
        print(f"tempo: {exc}", file=sys.stderr)
        return 1
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
    return result.returncode


def _cmd_setup(args: argparse.Namespace) -> int:
    tempo_binary = find_tempo_binary()
    if not tempo_binary:
        if not args.install:
            print("Tempo Wallet CLI is not installed.")
            print("Run 'hermes tempo setup --install' to use the official Tempo installer, or install it yourself:")
            print("  curl -fsSL https://tempo.xyz/install | bash")
            return 1
        print("Installing the official Tempo launcher from https://tempo.xyz/install ...")
        try:
            install_tempo_launcher()
        except TempoError as exc:
            print(f"tempo setup: {exc}", file=sys.stderr)
            return 1
        tempo_binary = find_tempo_binary()
        if not tempo_binary:
            print("Tempo installed, but the launcher is not visible on PATH yet.", file=sys.stderr)
            print("Open a new shell or add the Tempo install directory to PATH, then rerun 'hermes tempo setup'.", file=sys.stderr)
            return 1

    if wallet_is_connected():
        print("Tempo Wallet is already connected.")
    else:
        login_command = [tempo_binary, "wallet", "login"]
        if args.no_browser:
            login_command.append("--no-browser")
        print("Starting Tempo Wallet authorization. Your passkey/root key stays in Tempo Wallet; Hermes receives no root private key.")
        try:
            returncode = run_interactive(login_command)
        except TempoError as exc:
            print(f"tempo setup: {exc}", file=sys.stderr)
            return 1
        if returncode != 0:
            print(f"Tempo Wallet login exited with status {returncode}.", file=sys.stderr)
            return returncode

    print()
    status_code = _print_status()
    if status_code != 0:
        print("Tempo Wallet did not report a connected wallet after login.", file=sys.stderr)
        return status_code

    if args.fund:
        fund_command = [tempo_binary, "wallet", "fund"]
        if args.no_browser:
            fund_command.append("--no-browser")
        try:
            return run_interactive(fund_command)
        except TempoError as exc:
            print(f"tempo setup: {exc}", file=sys.stderr)
            return 1

    print()
    print("Ready. Preview a paid endpoint with:")
    print("  hermes tempo request https://example.mpp.tempo.xyz/v1/resource")
    print("Then add --pay only when you want Tempo Wallet to satisfy a compatible MPP 402 challenge.")
    print("Fund the wallet when needed with: hermes tempo fund")
    return 0


def _cmd_fund(args: argparse.Namespace) -> int:
    tempo_binary = find_tempo_binary()
    if not tempo_binary:
        print("Tempo CLI is not installed. Run: hermes tempo setup --install", file=sys.stderr)
        return 1
    command = [tempo_binary, "wallet", "fund"]
    if args.no_browser:
        command.append("--no-browser")
    try:
        return run_interactive(command)
    except TempoError as exc:
        print(f"tempo fund: {exc}", file=sys.stderr)
        return 1


def _cmd_request(args: argparse.Namespace) -> int:
    tempo_binary = find_tempo_binary()
    if not tempo_binary:
        print("Tempo CLI is not installed. Run: hermes tempo setup --install", file=sys.stderr)
        return 1

    json_body = None
    if args.json_body is not None:
        import json
        try:
            json_body = json.loads(args.json_body)
        except json.JSONDecodeError as exc:
            print(f"tempo request: --json must contain valid JSON: {exc}", file=sys.stderr)
            return 2

    try:
        command = build_request_command(
            tempo_binary,
            url=args.url,
            method=args.method,
            json_body=json_body,
            payment_intent=args.payment_intent,
            dry_run=not args.pay,
        )
        return run_interactive(command)
    except TempoError as exc:
        print(f"tempo request: {exc}", file=sys.stderr)
        return 1


def tempo_command(args: argparse.Namespace) -> int:
    subcommand = getattr(args, "tempo_command", None)
    if not subcommand:
        print("usage: hermes tempo {setup,status,fund,request}")
        return 2
    if subcommand == "setup":
        return _cmd_setup(args)
    if subcommand == "status":
        return _print_status()
    if subcommand == "fund":
        return _cmd_fund(args)
    if subcommand == "request":
        return _cmd_request(args)
    print(f"unknown Tempo subcommand: {subcommand}", file=sys.stderr)
    return 2
