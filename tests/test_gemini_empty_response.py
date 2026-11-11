"""An empty answer from the Gemini CLI is an error, never an answer.

Measured on the stored runs of December 2025: 120 of 754 Gemini Flash leaf
answers were empty and every one was recorded as complete. The Claude provider
already raises EmptyResponseError for the same case.
"""

import subprocess

import pytest

from deep_research.exceptions import EmptyResponseError
from deep_research.providers import gemini as gemini_module
from deep_research.providers.gemini import GeminiProvider


def _fake_run(stdout: str):
    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    return run


@pytest.mark.parametrize("stdout", ["", "   \n", "[STARTUP] loading\nLoaded cached credentials\n"])
def test_empty_cli_output_raises(monkeypatch, stdout):
    monkeypatch.setattr(gemini_module, "_find_gemini_cmd", lambda: "gemini")
    monkeypatch.setattr(gemini_module.subprocess, "run", _fake_run(stdout))
    with pytest.raises(EmptyResponseError):
        GeminiProvider()._call_gemini_cli("a question", "gemini-3-flash-preview")


def test_real_output_is_returned(monkeypatch):
    monkeypatch.setattr(gemini_module, "_find_gemini_cmd", lambda: "gemini")
    monkeypatch.setattr(gemini_module.subprocess, "run", _fake_run("[STARTUP] x\nAn answer.\n"))
    assert GeminiProvider()._call_gemini_cli("a question", "gemini-3-flash-preview") == "An answer."
