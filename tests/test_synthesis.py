"""The synthesis step: which prompt it uses, and when the CLI path runs it.

The default synthesis prompt asks for a direct answer that keeps the specific findings. The earlier
prompt (connections, tensions, nuance) stays available as ``connect=True``. On the CLI path a node
writes a synthesis only when ``synthesize`` is set; without it the node returns the exploration and
every child's answer in full.
"""

import asyncio

import pytest

from deep_research import orchestrator as orchestrator_module
from deep_research.exceptions import EmptyResponseError
from deep_research.models import ModelSpec, ResearchConfig
from deep_research.orchestrator import Orchestrator
from deep_research.providers import base as provider_base
from deep_research.providers.base import Provider, ProviderOptions


class RecordingProvider(Provider):
    """Captures the system prompt of each call and replays scripted replies."""

    def __init__(self, replies=None):
        self.replies = list(replies or [])
        self.system_prompts = []

    @property
    def name(self) -> str:
        return "recording"

    async def generate(self, prompt, model, options: ProviderOptions | None = None):
        self.system_prompts.append(options.system_prompt if options else None)
        return self.replies.pop(0) if self.replies else "reply"


def test_default_synthesis_prompt_asks_to_keep_the_findings():
    provider = RecordingProvider()
    asyncio.run(provider.synthesize("What makes good coffee?", "Use 93 C water.", "opus"))
    (prompt,) = provider.system_prompts
    assert "What makes good coffee?" in prompt
    assert "Use 93 C water." in prompt
    assert "Keep every specific finding" in prompt
    assert "Draw connections" not in prompt


def test_connect_synthesis_uses_the_earlier_prompt():
    provider = RecordingProvider()
    asyncio.run(provider.synthesize("Q?", "findings", "opus", connect=True))
    (prompt,) = provider.system_prompts
    assert prompt == provider_base.SYNTHESIZE_PROMPT_CONNECT.format(
        QUESTION="Q?", RESULTS="findings"
    )
    assert "Draw connections between findings" in prompt


def _run_root(tmp_path, monkeypatch, provider, **config_kwargs):
    monkeypatch.setattr(orchestrator_module, "get_provider_for_model", lambda model: provider)
    config = ResearchConfig(
        question="What makes good coffee?",
        orchestrator=ModelSpec.parse("opus"),
        researcher=ModelSpec.parse("haiku"),
        max_depth=2,
        max_parallel=1,
        output_dir=tmp_path / "run",
        **config_kwargs,
    )
    orch = Orchestrator(config)
    answer = asyncio.run(orch.process_question(config.question, config.orchestrator))
    return orch, answer


EXPLORE_REPLY = "Q: Which water temperature?\nQ: Which grind size?"


def test_without_synthesize_the_node_returns_every_child_answer_and_makes_no_extra_call(
    tmp_path, monkeypatch
):
    provider = RecordingProvider(replies=[EXPLORE_REPLY, "93 C.", "Medium."])
    orch, answer = _run_root(tmp_path, monkeypatch, provider)
    assert len(provider.system_prompts) == 3, "explore and two leaves, no synthesis call"
    assert "93 C." in answer and "Medium." in answer
    root = next(s for s in orch._agents.values() if s.config.depth == 0)
    assert root.synthesis is None


def test_with_synthesize_the_node_answers_from_its_children(tmp_path, monkeypatch):
    provider = RecordingProvider(
        replies=[EXPLORE_REPLY, "93 C.", "Medium.", "Brew at 93 C with a medium grind."]
    )
    orch, answer = _run_root(tmp_path, monkeypatch, provider, synthesize=True)
    assert answer == "Brew at 93 C with a medium grind."
    assert len(provider.system_prompts) == 4
    synthesis_prompt = provider.system_prompts[-1]
    assert "Which water temperature?" in synthesis_prompt
    assert "93 C." in synthesis_prompt and "Medium." in synthesis_prompt
    root = next(s for s in orch._agents.values() if s.config.depth == 0)
    assert root.synthesis == "Brew at 93 C with a medium grind."
    report = (orch.agents_dir / f"{root.config.agent_id}-opus.md").read_text(encoding="utf-8")
    assert "## Children Results" in report and "93 C." in report
    assert "## Synthesis\nBrew at 93 C with a medium grind." in report


def test_an_empty_synthesis_is_refused(tmp_path, monkeypatch):
    provider = RecordingProvider(replies=[EXPLORE_REPLY, "93 C.", "Medium.", "   "])
    with pytest.raises(EmptyResponseError):
        _run_root(tmp_path, monkeypatch, provider, synthesize=True)
