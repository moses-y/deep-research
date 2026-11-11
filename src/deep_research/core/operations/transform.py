"""
TRANSFORM operation - turns a question into the deeper question beneath it.

The target's challenged assumptions (ASSUMPTION children, rated by the
CHALLENGE operation) are shown to the model, which names the question that
remains once the flawed ones are removed. That question becomes a new QUESTION
node. The target is marked EXHAUSTED either way, so a phase that deepens
EXPLORED questions does not pick it up again. The prompt is the one the
Socratic recipe uses.
"""

from typing import Any

from ...recipes.socratic import DEEPER_PROMPT
from ..graph import KnowledgeGraph
from ..node import EpistemicStatus, Node, NodeRelation, NodeType
from ..operation import (
    BaseOperation,
    OperationResult,
    OperationSpec,
    OperationType,
)
from .base import get_model_from_context, get_provider_from_context


class TransformOperation(BaseOperation):
    """Derives the deeper question beneath a question from its challenged assumptions."""

    @property
    def spec(self) -> OperationSpec:
        return OperationSpec(
            operation_type=OperationType.TRANSFORM,
            input_types=[NodeType.QUESTION],
            output_types=[NodeType.QUESTION],
            required_status=[EpistemicStatus.EXPLORED],
            resulting_status=EpistemicStatus.EXHAUSTED,
            requires_model=True,
            can_spawn=True,
        )

    async def _execute_impl(
        self,
        graph: KnowledgeGraph,
        nodes: list[Node],
        context: dict[str, Any],
    ) -> OperationResult:
        """Execute the transformation on target nodes."""
        model = get_model_from_context(context)
        provider = get_provider_from_context(context)

        created_nodes: list[Node] = []

        for node in nodes:
            assumptions = [
                child
                for child in graph.children_of(node.id)
                if child.node_type == NodeType.ASSUMPTION
            ]
            if not assumptions:
                # Nothing was challenged, so there is nothing to derive a deeper question from.
                continue

            listing = "\n".join(
                f"- {a.content} ({a.metadata.get('rating', 'unrated')})" for a in assumptions
            )
            raw_output = await provider.generate(
                DEEPER_PROMPT.format(question=node.content, assumptions=listing),
                model.model,
            )

            deeper = self._parse_deeper(raw_output)
            if not deeper or deeper == node.content:
                continue

            deeper_node = Node(
                node_type=NodeType.QUESTION,
                status=EpistemicStatus.UNKNOWN,
                content=deeper,
                depth=node.depth + 1,
                created_by=f"transform:{model}",
                model=str(model),
            )
            deeper_node.add_edge(node.id, NodeRelation.PARENT)
            node.add_edge(deeper_node.id, NodeRelation.TRANSFORMS_TO)
            created_nodes.append(deeper_node)

        return OperationResult(
            success=True,
            created_nodes=created_nodes,
            modified_nodes=[n.id for n in nodes],
            metadata={"questions_created": len(created_nodes)},
        )

    @staticmethod
    def _parse_deeper(raw_output: str) -> str | None:
        """Read the "DEEPER:" line."""
        for line in raw_output.split("\n"):
            line = line.strip()
            if line.startswith("DEEPER:"):
                return line.split(":", 1)[1].strip() or None
        return None
