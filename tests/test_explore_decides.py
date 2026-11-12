"""The explore step decides: answer directly when the question is atomic, list sub-questions otherwise.

The default explore prompt gives the node that decision. A reply with no ``Q:`` lines is the node's own
answer, and an ``ANSWER:`` marker at its start is not part of the answer. ``thorough`` keeps the earlier
prompt, which always lists every angle.
"""

import asyncio

import pytest

from deep_research import orchestrator as orchestrator_module
from deep_research.exceptions import EmptyResponseError
from deep_research.models import DIRECT_ANSWER_MARKER, ExplorationResult, ModelSpec, ResearchConfig
from deep_research.orchestrator import Orchestrator
from deep_research.providers import base as provider_base
from deep_research.providers.base import EXPLORE_PROMPT, Provider, ProviderOptions


class RecordingProvider(Provider):
    """Captures the system prompt of each call and replays scripted replies."""

    def __init__(self, replies=None):
        self.replies = list(replies or [])
        self.system_prompts = []
        self.calls = []

    @property
    def name(self) -> str:
        return "recording"

    async def generate(self, prompt, model, options: ProviderOptions | None = None):
        self.system_prompts.append(options.system_prompt if options else None)
        self.calls.append(prompt)
        return self.replies.pop(0) if self.replies else "reply"


def test_direct_answer_strips_the_marker():
    result = ExplorationResult.from_output(
        "ANSWER: Canberra is the capital.\nIt replaced Melbourne in 1927."
    )
    assert result.questions == []
    assert result.direct_answer == "Canberra is the capital.\nIt replaced Melbourne in 1927."


def test_direct_answer_without_marker_is_kept_whole():
    result = ExplorationResult.from_output("  Canberra.  ")
    assert result.questions == []
    assert result.direct_answer == "Canberra."


def test_sub_questions_mean_no_direct_answer():
    result = ExplorationResult.from_output("Q: What is X?\nQ: What is Y?")
    assert [q.question for q in result.questions] == ["What is X?", "What is Y?"]
    assert result.direct_answer is None


def test_default_explore_prompt_gives_the_node_the_decision():
    provider = RecordingProvider()
    asyncio.run(provider.explore("What is 17 times 23?", "opus"))
    assert provider.system_prompts == [EXPLORE_PROMPT]
    assert f'start your reply with "{DIRECT_ANSWER_MARKER}"' in EXPLORE_PROMPT
    assert "List only angles that need separate work" in EXPLORE_PROMPT


def test_thorough_explore_uses_the_earlier_prompt():
    provider = RecordingProvider()
    asyncio.run(provider.explore("What makes a startup successful?", "opus", thorough=True))
    assert provider.system_prompts == [provider_base.EXPLORE_PROMPT_THOROUGH]
    assert "Be thorough. Do not stop at obvious angles." in provider_base.EXPLORE_PROMPT_THOROUGH
    assert "ANSWER:" not in provider_base.EXPLORE_PROMPT_THOROUGH


def _run_root(tmp_path, monkeypatch, provider, **config_kwargs):
    monkeypatch.setattr(orchestrator_module, "get_provider_for_model", lambda model: provider)
    config = ResearchConfig(
        question="What is the capital of Australia?",
        orchestrator=ModelSpec.parse("opus"),
        researcher=ModelSpec.parse("haiku"),
        max_depth=3,
        output_dir=tmp_path / "run",
        **config_kwargs,
    )
    orch = Orchestrator(config)
    answer = asyncio.run(orch.process_question(config.question, config.orchestrator))
    return orch, answer


def test_orchestrator_returns_a_direct_answer_without_the_marker_or_children(tmp_path, monkeypatch):
    provider = RecordingProvider(replies=["ANSWER: Canberra."])
    orch, answer = _run_root(tmp_path, monkeypatch, provider)
    assert answer == "Canberra."
    assert len(provider.calls) == 1, "a direct answer must not spawn children or a synthesis"
    assert len(orch._agents) == 1
    state = next(iter(orch._agents.values()))
    assert state.response == "Canberra."


def test_orchestrator_passes_the_thorough_choice_to_the_provider(tmp_path, monkeypatch):
    provider = RecordingProvider(replies=["ANSWER: Canberra."])
    _run_root(tmp_path, monkeypatch, provider, thorough_explore=True)
    assert provider.system_prompts[0] == provider_base.EXPLORE_PROMPT_THOROUGH


def test_orchestrator_refuses_an_empty_direct_answer(tmp_path, monkeypatch):
    provider = RecordingProvider(replies=["ANSWER:   "])
    with pytest.raises(EmptyResponseError):
        _run_root(tmp_path, monkeypatch, provider)
