"""Audit a finished run from its agent files.

Reads the markdown files a run leaves in ``<run>/agents`` and reports what the
run itself never says: sub-questions that were proposed and have no agent file,
answers that came back empty, agents that did not finish, and how wide each
node fanned out. Standard library only, no model call.

Why it exists: a mechanical read of 27 stored runs (Nov 2026) found 112 empty
answers recorded as complete and about 185 agent files overwritten by a number
collision, none of it visible in any run's own output.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

EMPTY_UNDER = 1  # characters: an answer with nothing in it
SHORT_UNDER = 300  # characters: too short to be a researched answer

_NAME = re.compile(r"d(\d+)-(\d+)-(.+)\.md$")
_STATUS = re.compile(r"\*\*Status:\s*([A-Z_]+)")
_QUESTION = re.compile(r"## Question\s*\n(.*?)(?=\n## |\Z)", re.S)
_EXPLORATION = re.compile(
    r"## Exploration\s*\n(.*?)(?=\n## Children Results|\n## Research Findings|\n## Synthesis|\n## Response|\Z)",
    re.S,
)
_RESPONSE = re.compile(r"## Response\s*\n(.*)\Z", re.S)


@dataclass
class AgentRecord:
    """What one agent file says."""

    name: str
    depth: int
    status: str
    question: str
    proposed: list[str]
    response: str

    @property
    def is_parent(self) -> bool:
        return bool(self.proposed)


@dataclass
class AuditReport:
    """The findings of one audit."""

    run_dir: Path
    agents: int = 0
    parents: int = 0
    leaves: int = 0
    proposed: int = 0
    children: int = 0
    proposed_without_file: list[tuple[str, str]] = field(default_factory=list)
    empty_answers: list[str] = field(default_factory=list)
    short_answers: list[str] = field(default_factory=list)
    not_complete: list[tuple[str, str]] = field(default_factory=list)
    fan_out: list[int] = field(default_factory=list)

    @property
    def findings(self) -> int:
        """How many things a reader should look at."""
        return (
            len(self.proposed_without_file)
            + len(self.empty_answers)
            + len(self.short_answers)
            + len(self.not_complete)
        )

    @property
    def clean(self) -> bool:
        return self.agents > 0 and self.findings == 0


def parse_agent_file(path: Path) -> AgentRecord:
    """Read one agent file written by the orchestrator or the bash script."""
    text = path.read_text(encoding="utf-8", errors="replace")
    name = _NAME.match(path.name)
    status = _STATUS.search(text)
    question = _QUESTION.search(text)
    exploration = _EXPLORATION.search(text)
    response = _RESPONSE.search(text)
    proposed = [
        line.strip()[3:].strip()
        for line in (exploration.group(1) if exploration else "").split("\n")
        if line.strip().startswith("Q: ") and line.strip()[3:].strip()
    ]
    return AgentRecord(
        name=path.name,
        depth=int(name.group(1)) if name else -1,
        status=status.group(1) if status else "UNKNOWN",
        question=question.group(1).strip() if question else "",
        proposed=proposed,
        response=response.group(1).strip() if response else "",
    )


def audit_run(run_dir: Path) -> AuditReport:
    """Audit the run in ``run_dir`` (the folder that holds ``agents/``)."""
    run_dir = Path(run_dir)
    report = AuditReport(run_dir=run_dir)
    records = [parse_agent_file(p) for p in sorted((run_dir / "agents").glob("*.md"))]
    report.agents = len(records)
    questions_with_file = {r.question for r in records if r.depth >= 1}

    for record in records:
        if record.status != "COMPLETE":
            report.not_complete.append((record.name, record.status))
        if record.depth >= 1:
            report.children += 1
        if record.is_parent:
            report.parents += 1
            report.proposed += len(record.proposed)
            report.fan_out.append(len(record.proposed))
            for question in record.proposed:
                if question not in questions_with_file:
                    report.proposed_without_file.append((record.name, question))
        elif record.depth >= 1:
            report.leaves += 1
            if len(record.response) < EMPTY_UNDER:
                report.empty_answers.append(record.name)
            elif len(record.response) < SHORT_UNDER:
                report.short_answers.append(record.name)
    return report


def format_report(report: AuditReport, limit: int = 10) -> str:
    """The report as plain text, one finding per line."""
    lines = [f"Audit of {report.run_dir}"]
    if report.agents == 0:
        lines.append("  no agent files found: nothing to audit (UNKNOWN, not clean)")
        return "\n".join(lines)

    lines.append(
        f"  agents {report.agents}: {report.parents} decomposed, {report.leaves} answered; "
        f"{report.proposed} sub-questions proposed, {report.children} child files"
    )
    if report.fan_out:
        lines.append(
            f"  fan-out per decomposing node: median {statistics.median(report.fan_out):g}, "
            f"largest {max(report.fan_out)}"
        )

    def section(title: str, items: list[str]) -> None:
        if not items:
            return
        lines.append(f"  {title}: {len(items)}")
        lines.extend(f"    {item}" for item in items[:limit])
        if len(items) > limit:
            lines.append(f"    ... and {len(items) - limit} more")

    section(
        "proposed sub-questions with no agent file",
        [f"{parent}: {question[:90]}" for parent, question in report.proposed_without_file],
    )
    section("empty answers", report.empty_answers)
    section(f"answers under {SHORT_UNDER} characters", report.short_answers)
    section("agents not complete", [f"{name}: {status}" for name, status in report.not_complete])
    lines.append("  clean" if report.clean else f"  {report.findings} findings")
    return "\n".join(lines)
