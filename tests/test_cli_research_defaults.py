"""`deep-research research "question"` must run with no optional flag given."""

from types import SimpleNamespace

from typer.testing import CliRunner

from deep_research import cli
from deep_research.settings import settings

runner = CliRunner()


def _stub_run(monkeypatch, tmp_path):
    """Replace the orchestrator, the key check and the audit so no model is called."""
    seen = {}

    class FakeOrchestrator:
        def __init__(self, config):
            seen["config"] = config
            self.agents_dir = tmp_path / "agents"

        async def run(self):
            return "done"

    monkeypatch.setattr(cli, "Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(cli, "validate_api_keys_for_config", lambda config: None)
    monkeypatch.setattr(cli, "audit_run", lambda run_dir: SimpleNamespace())
    monkeypatch.setattr(cli, "format_report", lambda report: "audit")
    return seen


def test_research_runs_without_the_parallel_flag(monkeypatch, tmp_path):
    seen = _stub_run(monkeypatch, tmp_path)
    result = runner.invoke(
        cli.app, ["research", "-o", str(tmp_path / "run"), "What is 17 times 23?"]
    )
    assert result.exit_code == 0, result.output
    assert seen["config"].max_parallel == settings.max_parallel
    assert seen["config"].thorough_explore is False
    assert seen["config"].synthesize is False


def test_research_still_refuses_a_parallel_value_out_of_range(monkeypatch, tmp_path):
    _stub_run(monkeypatch, tmp_path)
    result = runner.invoke(
        cli.app, ["research", "-p", "0", "-o", str(tmp_path / "run"), "What is 17 times 23?"]
    )
    assert result.exit_code == 1
    assert "Parallel" in result.output


def test_thorough_flag_reaches_the_config(monkeypatch, tmp_path):
    seen = _stub_run(monkeypatch, tmp_path)
    result = runner.invoke(
        cli.app,
        [
            "research",
            "--thorough",
            "-p",
            "2",
            "-o",
            str(tmp_path / "run"),
            "What makes good coffee?",
        ],
    )
    assert result.exit_code == 0, result.output
    assert seen["config"].thorough_explore is True
    assert seen["config"].max_parallel == 2


def test_synthesize_flag_reaches_the_config(monkeypatch, tmp_path):
    seen = _stub_run(monkeypatch, tmp_path)
    result = runner.invoke(
        cli.app,
        ["research", "--synthesize", "-o", str(tmp_path / "run"), "What makes good coffee?"],
    )
    assert result.exit_code == 0, result.output
    assert seen["config"].synthesize is True
