from __future__ import annotations

import hermes_tempo_payments


class FakeContext:
    def __init__(self):
        self.tools = []
        self.commands = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_cli_command(self, **kwargs):
        self.commands.append(kwargs)


def test_plugin_registers_two_tools_and_tempo_cli():
    context = FakeContext()
    hermes_tempo_payments.register(context)

    assert [tool["name"] for tool in context.tools] == ["tempo_wallet_status", "tempo_request"]
    assert all(tool["toolset"] == "tempo_payments" for tool in context.tools)
    assert [command["name"] for command in context.commands] == ["tempo"]
