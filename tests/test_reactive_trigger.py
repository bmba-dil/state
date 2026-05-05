"""Tests for ReactiveTrigger — event-driven DAG scheduler activation.

Covers: event-type filtering, async tick dispatch, dag_provider injection,
        custom watched_events, multiple rapid events, and missing-key safety.

Requires: pytest, pytest-asyncio.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from src.state_core.reactive import ReactiveTrigger
from src.state_core.scheduler import DAGScheduler, Edge, Node


# -- Inline mock scheduler -------------------------------------------------------


class _RecordScheduler:
    """Records tick() calls for verification — lightweight alternative to mocking."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[Node], list[Edge]]] = []

    async def tick(self, nodes: list[Node], edges: list[Edge]) -> list[str]:
        self.calls.append((nodes, edges))
        return []


# -- Helper to create a dag_provider ---------------------------------------------


def _make_dag_provider(
    nodes: list[Node] | None = None,
    edges: list[Edge] | None = None,
    record: list[tuple[list[Node], list[Edge]]] | None = None,
) -> Callable[[], tuple[list[Node], list[Edge]]]:
    """Return a dag_provider callable that returns (nodes, edges)
    and optionally records each invocation."""
    def provider() -> tuple[list[Node], list[Edge]]:
        if record is not None:
            record.append((nodes or [], edges or []))
        return nodes or [], edges or []
    return provider


# -- Tests -----------------------------------------------------------------------


class TestReactiveTrigger:
    """Tests for ReactiveTrigger event filtering and tick dispatch."""

    # ------------------------------------------------------------------
    # Tests 1-3: Watched event types trigger tick()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_on_event_step_advanced_triggers_tick(self) -> None:
        """on_event with 'state.step.advanced' → tick() is scheduled."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
        )

        trigger.on_event({"type": "state.step.advanced"})
        await asyncio.sleep(0)  # let scheduled task run

        assert len(scheduler.calls) == 1

    @pytest.mark.asyncio
    async def test_on_event_slice_worktree_ready_triggers_tick(self) -> None:
        """on_event with 'state.slice.worktree_ready' → tick() scheduled."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
        )

        trigger.on_event({"type": "state.slice.worktree_ready"})
        await asyncio.sleep(0)

        assert len(scheduler.calls) == 1

    @pytest.mark.asyncio
    async def test_on_event_phase_planned_triggers_tick(self) -> None:
        """on_event with 'state.phase.planned' → tick() scheduled."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
        )

        trigger.on_event({"type": "state.phase.planned"})
        await asyncio.sleep(0)

        assert len(scheduler.calls) == 1

    # ------------------------------------------------------------------
    # Test 4: Non-watched event types do NOT trigger tick()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_on_event_non_watched_does_not_trigger_tick(self) -> None:
        """on_event with 'state.step.discussed' (not watched) → no tick()."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
        )

        trigger.on_event({"type": "state.step.discussed"})
        await asyncio.sleep(0)

        assert len(scheduler.calls) == 0

    # ------------------------------------------------------------------
    # Test 5: dag_provider is called and its output passed to tick()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_dag_provider_called_and_output_passed_to_tick(self) -> None:
        """dag_provider() is invoked and its (nodes, edges) are passed to tick()."""
        scheduler = _RecordScheduler()
        n1 = Node(id="step-1", kind="step", status="idle")
        e1 = Edge(source_node="step-0", target_node="step-1", kind="blocks")
        provider_calls: list[tuple[list[Node], list[Edge]]] = []
        provider = _make_dag_provider(
            nodes=[n1],
            edges=[e1],
            record=provider_calls,
        )
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
        )

        trigger.on_event({"type": "state.step.advanced"})
        await asyncio.sleep(0)

        assert len(provider_calls) == 1
        assert len(scheduler.calls) == 1
        # tick() received the nodes/edges from dag_provider
        assert scheduler.calls[0][0] == [n1]
        assert scheduler.calls[0][1] == [e1]

    # ------------------------------------------------------------------
    # Test 6: Custom watched_events set works correctly
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_custom_watched_events_only_responds_to_those(self) -> None:
        """Custom watched_events={only 'state.step.advanced'} filters correctly."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
            watched_events=frozenset(["state.step.advanced"]),
        )

        # Watched event → triggers tick
        trigger.on_event({"type": "state.step.advanced"})
        await asyncio.sleep(0)
        assert len(scheduler.calls) == 1

        # Non-watched event → no tick
        trigger.on_event({"type": "state.slice.worktree_ready"})
        await asyncio.sleep(0)
        assert len(scheduler.calls) == 1  # still 1

    # ------------------------------------------------------------------
    # Test 7: Multiple rapid on_event calls each dispatch independent tick tasks
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_multiple_rapid_events_each_dispatch_tick(self) -> None:
        """Multiple rapid on_event() calls each dispatch an independent tick task."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
        )

        # Fire three events rapidly (no await between them)
        trigger.on_event({"type": "state.step.advanced"})
        trigger.on_event({"type": "state.slice.worktree_ready"})
        trigger.on_event({"type": "state.phase.planned"})
        await asyncio.sleep(0)  # let all tasks run

        assert len(scheduler.calls) == 3

    # ------------------------------------------------------------------
    # Test 8: Missing 'type' key handled gracefully (no crash)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_on_event_missing_type_key_no_crash(self) -> None:
        """on_event with an empty dict (no 'type' key) does not crash."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
        )

        # Should not raise — no 'type' key
        trigger.on_event({})
        await asyncio.sleep(0)

        assert len(scheduler.calls) == 0

    # ------------------------------------------------------------------
    # Property: watched_events
    # ------------------------------------------------------------------

    def test_default_watched_events(self) -> None:
        """Default watched_events is the expected frozenset of three event types."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
        )

        expected = frozenset([
            "state.step.advanced",
            "state.slice.worktree_ready",
            "state.phase.planned",
        ])
        assert trigger.watched_events == expected

    def test_custom_watched_events_stored(self) -> None:
        """Custom watched_events frozenset is stored and returned by property."""
        scheduler = _RecordScheduler()
        provider = _make_dag_provider()
        custom = frozenset(["state.step.advanced"])
        trigger = ReactiveTrigger(
            scheduler=scheduler,  # type: ignore[arg-type]
            dag_provider=provider,
            watched_events=custom,
        )

        assert trigger.watched_events == custom
