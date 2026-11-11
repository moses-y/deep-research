"""The run audit reads agent files and reports what a run never says about itself."""

from pathlib import Path

from deep_research.audit import audit_run, format_report

LONG = "A researched answer. " * 30


def _agent(
    agents: Path, name: str, question: str, *, status="COMPLETE", proposed=(), response=None
):
    text = f"# Agent {name}\n**Status: {status}**\n\n## Question\n{question}\n"
    if proposed:
        text += (
            "\n## Exploration\nSome reasoning.\n" + "\n".join(f"Q: {q}" for q in proposed) + "\n"
        )
    if response is not None:
        text += f"\n## Response\n{response}\n"
    (agents / f"{name}.md").write_text(text, encoding="utf-8")


def _run(tmp_path: Path) -> Path:
    agents = tmp_path / "agents"
    agents.mkdir()
    return agents


def test_clean_run_has_no_findings(tmp_path):
    agents = _run(tmp_path)
    _agent(agents, "d0-001-opus", "Root?", proposed=["First?", "Second?"])
    _agent(agents, "d1-002-haiku", "First?", response=LONG)
    _agent(agents, "d1-003-haiku", "Second?", response=LONG)

    report = audit_run(tmp_path)

    assert report.clean
    assert (report.agents, report.parents, report.leaves) == (3, 1, 2)
    assert (report.proposed, report.children, report.fan_out) == (2, 2, [2])
    assert "clean" in format_report(report)


def test_proposed_sub_question_without_a_file_is_reported(tmp_path):
    agents = _run(tmp_path)
    _agent(agents, "d0-001-opus", "Root?", proposed=["First?", "Second?", "Third?"])
    _agent(agents, "d1-002-haiku", "First?", response=LONG)
    _agent(agents, "d1-003-haiku", "Third?", response=LONG)

    report = audit_run(tmp_path)

    assert report.proposed_without_file == [("d0-001-opus.md", "Second?")]
    assert not report.clean


def test_empty_and_short_answers_are_reported_even_when_marked_complete(tmp_path):
    agents = _run(tmp_path)
    _agent(agents, "d0-001-opus", "Root?", proposed=["First?", "Second?", "Third?"])
    _agent(agents, "d1-002-flash", "First?", response="")
    _agent(agents, "d1-003-flash", "Second?", response="Too short.")
    _agent(agents, "d1-004-haiku", "Third?", response=LONG)

    report = audit_run(tmp_path)

    assert report.empty_answers == ["d1-002-flash.md"]
    assert report.short_answers == ["d1-003-flash.md"]
    assert report.findings == 2


def test_agent_that_did_not_finish_is_reported(tmp_path):
    agents = _run(tmp_path)
    _agent(agents, "d0-001-opus", "Root?", proposed=["First?"])
    _agent(agents, "d1-002-haiku", "First?", status="FAILED", response=LONG)

    assert audit_run(tmp_path).not_complete == [("d1-002-haiku.md", "FAILED")]


def test_a_folder_with_no_agent_files_is_unknown_not_clean(tmp_path):
    report = audit_run(tmp_path)

    assert report.agents == 0
    assert not report.clean
    assert "UNKNOWN" in format_report(report)
