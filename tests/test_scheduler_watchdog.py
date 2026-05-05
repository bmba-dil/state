"""Regression harness for P0-16: TaskGroup CancelledError swallow detection.

Tests exercise nested asyncio.TaskGroup cancellation scenarios and verify
the scheduler watchdog (SwallowedCancelledError) fails loud when CancelledError
would otherwise be silently swallowed.
"""

from __future__ import annotations

import asyncio

import pytest

from src.state_core.scheduler import (
    DAGScheduler,
    Edge,
    Node,
)


class TestWatchdog:
    """Watchdog regression tests — P0-16 CancelledError swallow detection."""

    # --- RED phase tests (must FAIL before GREEN implementation) ---

    @pytest.mark.asyncio
    async def test_sibling_cancelled_error_detected(self) -> None:
        """2 Slices, one raises ValueError → sibling cancelled → SwallowedCancelledError."""
        # Setup: 2 Slices, each with 1 step.
        # First Slice's executor raises ValueError("boom")
        # Second Slice sleeps briefly — will be cancelled by TaskGroup
        # when first Slice errors.

        slice1_executed = False
        slice2_cancelled = False

        async def exec_raise(node: Node) -> None:
            nonlocal slice1_executed
            slice1_executed = True
            raise ValueError("boom from slice 1")

        async def exec_sleep(node: Node) -> None:
            nonlocal slice2_cancelled
            try:
                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                slice2_cancelled = True
                raise

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=exec_raise)

        s1 = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )
        s2 = Node(
            id="arc-1/phase-1/slice-2/step-1", kind="step", status="idle"
        )

        # After GREEN: this will raise SwallowedCancelledError (from cancelled sibling)
        # In RED phase: ValueError or ExceptionGroup is raised, but NOT SwallowedCancelledError
        # We expect SwallowedCancelledError AFTER the GREEN implementation
        from src.state_core.scheduler import SwallowedCancelledError
        with pytest.raises(SwallowedCancelledError):
            await scheduler.tick([s1, s2], [])

    @pytest.mark.asyncio
    async def test_direct_cancelled_error_raises(self) -> None:
        """Step executor raises CancelledError → watchdog raises SwallowedCancelledError."""
        async def exec_cancel(node: Node) -> None:
            raise asyncio.CancelledError()

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=exec_cancel)
        step = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )

        from src.state_core.scheduler import SwallowedCancelledError
        with pytest.raises(SwallowedCancelledError):
            await scheduler.tick([step], [])

    @pytest.mark.asyncio
    async def test_no_false_positives_normal_completion(self) -> None:
        """2 Slices, both succeed → no exception raised, both IDs returned."""
        recorded: list[str] = []

        async def record(node: Node) -> None:
            recorded.append(node.id)

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=record)
        s1 = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )
        s2 = Node(
            id="arc-1/phase-1/slice-2/step-1", kind="step", status="idle"
        )

        result = await scheduler.tick([s1, s2], [])
        assert set(result) == {
            "arc-1/phase-1/slice-1/step-1",
            "arc-1/phase-1/slice-2/step-1",
        }
