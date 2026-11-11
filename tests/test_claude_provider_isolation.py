"""The Claude CLI call must not inherit the user's own settings.

Measured Nov 2026 on one machine: the same one-sentence question cost 15,040
context tokens through the provider's command and 697 with user and local
settings switched off. Every leaf of a tree paid that, and every leaf read the
user's private instruction file.
"""

import asyncio

from deep_research.providers import claude as claude_module
from deep_research.providers.base import ProviderOptions
from deep_research.providers.claude import ClaudeProvider


class _FakeProcess:
    returncode = 0

    async def communicate(self, input=None):
        return b"An answer.", b""


def _captured_command(monkeypatch) -> list[str]:
    seen: list[str] = []

    async def fake_shell(cmd, **kwargs):
        seen.extend(cmd.split())
        return _FakeProcess()

    async def fake_exec(*cmd, **kwargs):
        seen.extend(cmd)
        return _FakeProcess()

    monkeypatch.setattr(claude_module, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(claude_module, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(asyncio, "create_subprocess_shell", fake_shell)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    answer = asyncio.run(
        ClaudeProvider().generate(
            "A question?", "haiku", ProviderOptions(system_prompt="Be brief.")
        )
    )
    assert answer == "An answer."
    return seen


def test_command_switches_off_user_and_local_settings(monkeypatch):
    cmd = _captured_command(monkeypatch)

    assert "--setting-sources" in cmd
    assert cmd[cmd.index("--setting-sources") + 1] == "project"


def test_command_keeps_the_single_turn_no_tools_shape(monkeypatch):
    cmd = _captured_command(monkeypatch)

    assert cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--max-turns") + 1] == "1"
    assert "--system-prompt-file" in cmd
