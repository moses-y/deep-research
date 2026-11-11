"""
CHALLENGE operation - tests an assumption or claim against its opposite.

Each target is challenged once. The challenge is stored as a COUNTERPOINT node
linked to the target, and the target's metadata records a rating: "solid",
"questionable" or "flawed". The prompt is the one the Socratic recipe uses.
"""

from typing import Any

from ...recipes.socratic import CHALLENGE_PROMPT
from ..graph import KnowledgeGraph
from ..node import EpistemicStatus, Node, NodeRelation, NodeType
from ..operation import (
    BaseOperation,
    OperationResult,
    OperationSpec,
    OperationType,
)
from .base import get_model_from_context, get_provider_from_context

RATINGS = ("flawed", "solid", "questionable")
DEFAULT_RATING = "questionable"


class ChallengeOperation(BaseOperation):
    """Challenges an assumption or claim and rates how well it holds."""

    @property
    def spec(self) -> OperationSpec:
        return OperationSpec(
            operation_type=OperationType.CHALLENGE,
            input_types=[NodeType.ASSUMPTION, NodeType.CLAIM],
            output_types=[NodeType.COUNTERPOINT],
            required_status=[EpistemicStatus.UNKNOWN, EpistemicStatus.PROPOSED],
            resulting_status=EpistemicStatus.CHALLENGED,
            requires_model=True,
            can_spawn=True,
        )

    async def _execute_impl(
        self,
        graph: KnowledgeGraph,
        nodes: list[Node],
        context: dict[str, Any],
    ) -> OperationResult:
        """Execute the challenge on target nodes."""
        model = get_model_from_context(context)
        provider = get_provider_from_context(context)

        created_nodes: list[Node] = []

        for node in nodes:
            raw_output = await provider.generate(
                CHALLENGE_PROMPT.format(assumption=node.content),
                model.model,
            )
            rating = self._parse_rating(raw_output)

            counterpoint = Node(
                node_type=NodeType.COUNTERPOINT,
                status=EpistemicStatus.PROPOSED,
                content=raw_output,
                depth=node.depth + 1,
                created_by=f"challenge:{model}",
                model=str(model),
                metadata={"rating": rating},
            )
            counterpoint.add_edge(node.id, NodeRelation.PARENT)
            counterpoint.add_edge(node.id, NodeRelation.CHALLENGES)
            node.add_edge(counterpoint.id, NodeRelation.CHILD)

            node.metadata["rating"] = rating
            created_nodes.append(counterpoint)

        return OperationResult(
            success=True,
            created_nodes=created_nodes,
            modified_nodes=[n.id for n in nodes],
            metadata={"challenges": len(created_nodes)},
        )

    @staticmethod
    def _parse_rating(raw_output: str) -> str:
        """Read the "RATING:" line. Output without a clear rating counts as questionable."""
        for line in raw_output.split("\n"):
            line = line.strip()
            if line.lower().startswith("rating:"):
                value = line.split(":", 1)[1].lower()
                for rating in RATINGS:
                    if rating in value:
                        return rating
        return DEFAULT_RATING
