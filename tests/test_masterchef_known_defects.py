"""Regression tests for four defects found in the MasterChef path on 2026-11-11.

Each test states the behaviour the code should have. They were first committed
as strict expected failures and each was shown failing before its fix. No model
call is made.
"""

import pytest

from deep_research.core import MasterChef, recursive_research_strategy, socratic_strategy
from deep_research.core.operation import OperationRegistry


@pytest.fixture(scope="module")
def registry():
    MasterChef()  # registers built-in strategies and operations
    return OperationRegistry.instance()


def test_every_operation_of_the_socratic_strategy_is_registered(registry):
    missing = [
        (phase.name, op.value)
        for phase in socratic_strategy().phases
        for op in phase.operations
        if registry.create(op) is None
    ]
    assert missing == []


def test_every_operation_of_the_recursive_strategy_is_registered(registry):
    """Control: the same check passes for the strategy that does work."""
    missing = [
        (phase.name, op.value)
        for phase in recursive_research_strategy().phases
        for op in phase.operations
        if registry.create(op) is None
    ]
    assert missing == []


def test_max_depth_changes_the_recursive_strategy():
    shallow = recursive_research_strategy(max_depth=1).to_dict()
    deep = recursive_research_strategy(max_depth=4).to_dict()
    assert shallow != deep


def test_every_phase_targets_only_types_its_operations_accept(registry):
    from deep_research.core import perspective_strategy

    refused = [
        (phase.name, op.value, target.value)
        for strategy in (recursive_research_strategy(), perspective_strategy())
        for phase in strategy.phases
        for op in phase.operations
        if registry.create(op) is not None
        for target in phase.target_types
        if target not in registry.create(op).spec.input_types
    ]
    assert refused == []


def test_delegation_leaves_the_parent_graph_current():
    import asyncio

    from deep_research.core.graph import KnowledgeGraph
    from deep_research.core.node import NodeType, question
    from deep_research.core.strategy import Phase, PhaseType, Strategy, StrategyMetadata

    chef = MasterChef()
    empty = Strategy(
        metadata=StrategyMetadata(name="empty-for-test", description="no phases"),
        goals=[],
        phases=[],
    )
    chef._strategy_registry.register(empty)
    parent = KnowledgeGraph(question="Parent?")
    parent.add(question("Parent?", depth=0))
    chef._current_graph = parent
    phase = Phase(
        name="delegate",
        phase_type=PhaseType.DELEGATE,
        target_types=[NodeType.QUESTION],
        delegate_to="empty-for-test",
    )

    asyncio.run(chef._execute_delegation(phase, {}))

    assert chef._current_graph is parent
