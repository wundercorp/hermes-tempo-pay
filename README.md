# Hermes Tempo Payments

Standalone Hermes plugin for onboarding a Tempo Wallet and giving Hermes agents a payment-aware HTTP tool backed by the official Tempo Wallet CLI.

## What it does

- `hermes tempo setup` connects a Tempo Wallet using Tempo's passkey authorization flow.
- `hermes tempo setup --no-browser` supports a Hermes host running on a remote machine.
- `hermes tempo setup --install` can explicitly run Tempo's official installer when the CLI is missing.
- `tempo_wallet_status` lets the agent inspect the connected wallet without spending.
- `tempo_request` lets the agent call paid HTTP endpoints through `tempo request`.
- Agent requests default to `mode="preview"`, which maps to `tempo request --dry-run` and does not pay.
- `mode="pay"` is required before the agent may let Tempo Wallet satisfy a compatible payment challenge.

## Protocol note: MPP vs x402

Tempo Wallet's current CLI handles HTTP `402 Payment Required` using Machine Payments Protocol (MPP). It is not a generic implementation of Coinbase's x402 wire protocol. An endpoint that only supports x402 and does not advertise a compatible MPP challenge will not become payable merely by installing this plugin.

The integration intentionally says "MPP" and "HTTP 402" in its tool descriptions so Hermes does not overstate interoperability.

## Security model

This plugin never reads or stores a root private key. Wallet authorization is delegated to the official Tempo Wallet CLI. Tempo's wallet flow uses passkey authorization and stores a restricted access/session key locally for subsequent signing.

`tempo_request` also enforces these guardrails before invoking Tempo:

- HTTPS is required for remote endpoints.
- Plain HTTP is only accepted for loopback development addresses.
- URLs with embedded credentials are rejected.
- Payment is preview-only unless `mode="pay"` is explicitly selected.
- Command output and errors are bounded before they are returned to the Hermes model context.
- Subprocesses use argument arrays and never invoke a shell.

Wallet-side spending limits remain the hard boundary. Only fund or authorize an amount you are prepared for the agent to spend.

## Install

This repository is structured as a Hermes standalone plugin because Hermes' contribution guidelines require third-party product integrations to ship outside core.

After publishing this directory to GitHub:

```bash
hermes plugins install wundercorp/hermes-tempo-pay --enable
```

For a local checkout during development, use the plugin install mechanism supported by your Hermes build or copy/symlink the directory under `~/.hermes/plugins/tempo_payments` and enable the plugin.

## Onboard a wallet

If Tempo Wallet is already installed:

```bash
hermes tempo setup
```

If Hermes runs on a remote host:

```bash
hermes tempo setup --no-browser
```

If Tempo Wallet is not installed and you want the plugin to execute Tempo's official installer explicitly:

```bash
hermes tempo setup --install
```

Install + remote-host login:

```bash
hermes tempo setup --install --no-browser
```

Fund after connecting:

```bash
hermes tempo fund
```

## Preview and pay from the CLI

Preview only:

```bash
hermes tempo request https://example.mpp.tempo.xyz/v1/resource
```

Allow payment:

```bash
hermes tempo request --pay https://example.mpp.tempo.xyz/v1/resource
```

POST JSON while still previewing:

```bash
hermes tempo request -X POST --json '{"input":"hello"}' https://service.mpp.tempo.xyz/v1/stream
```

## Agent tool

A normal first call should look conceptually like:

```json
{
  "url": "https://example.mpp.tempo.xyz/v1/resource",
  "mode": "preview"
}
```

After inspecting the preview, the agent can make a separate call with:

```json
{
  "url": "https://example.mpp.tempo.xyz/v1/resource",
  "mode": "pay"
}
```

For a POST:

```json
{
  "url": "https://service.mpp.tempo.xyz/v1/stream",
  "method": "POST",
  "json_body": {
    "input": "hello"
  },
  "payment_intent": "session",
  "mode": "preview"
}
```

## Development

Run the standalone tests against a Hermes checkout:

```bash
PYTHONPATH=/path/to/hermes-agent python -m pytest -q --import-mode=importlib tests
```
