"""Regression harness for P0-16: TaskGroup CancelledError swallow detection.

Tests exercise nested asyncio.TaskGroup cancellation scenarios and verify
the scheduler watchdog (SwallowedCancelledError) fails loud when CancelledError
would otherwise be silently swallowed.

Python 3.12 note: Direct CancelledError from a coroutine is filtered by
TaskGroup (task.cancelled() → True, skipped by _aexit). However,
CancelledError embedded inside a BaseExceptionGroup passes through
because the outer task's exception is the group (not CancelledError),
so task.cancelled() returns False. The watchdog inspects these groups.
"""

from __future__ import annotations

import asyncio

import pytest

from src.state_core.scheduler import (
    DAGScheduler,
    Edge,
    Node,
    SwallowedCancelledError,
)


def _make_cancel_group() -> BaseExceptionGroup:
    """Create a BaseExceptionGroup containing a CancelledError.

    Simulates what happens when a nested TaskGroup propagates a
    CancelledError through its BaseExceptionGroup mechanism.
    """
    return BaseExceptionGroup("nested", [asyncio.CancelledError()])


def _make_mixed_group() -> BaseExceptionGroup:
    """Create a BaseExceptionGroup containing CancelledError + ValueError.

    Simulates a nested TaskGroup where one task raised CancelledError
    and another raised ValueError.
    """
    return BaseExceptionGroup(
        "nested",
        [asyncio.CancelledError(), ValueError("inner error")],
    )


class TestWatchdog:
    """Watchdog regression tests — P0-16 CancelledError swallow detection."""

    @pytest.mark.asyncio
    async def test_cancelled_error_in_base_exception_group(self) -> None:
        """2 Slices: one raises BaseExceptionGroup with CancelledError inside.

        Slice 1 executor raises a BaseExceptionGroup containing CancelledError.
        Slice 2 executor succeeds normally. The watchdog detects the CancelledError
        embedded in the exception group and raises SwallowedCancelledError.

        This is the P0-16 defence: CancelledError buried in an exception group
        tree would be silently ignored by ExceptionGroup-only handlers. The
        watchdog's recursive inspection catches it.
        """
        recorded: list[str] = []

        async def conditional_exec(node: Node) -> None:
            recorded.append(node.id)
            if "slice-1" in node.id:
                raise _make_cancel_group()

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=conditional_exec)

        s1 = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )
        s2 = Node(
            id="arc-1/phase-1/slice-2/step-1", kind="step", status="idle"
        )

        with pytest.raises(SwallowedCancelledError):
            await scheduler.tick([s1, s2], [])

    @pytest.mark.asyncio
    async def test_cancelled_error_in_mixed_group(self) -> None:
        """2 Slices: one raises ValueError, one raises group with CancelledError.

        Slice 1 raises ValueError. Slice 2 raises BaseExceptionGroup containing
        CancelledError. Both land in the outer TaskGroup's exception group.
        The watchdog finds the CancelledError nested inside slice 2's group.
        """
        async def conditional_exec(node: Node) -> None:
            if "slice-1" in node.id:
                raise ValueError("boom from slice 1")
            else:
                raise _make_mixed_group()

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=conditional_exec)

        s1 = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )
        s2 = Node(
            id="arc-1/phase-1/slice-2/step-1", kind="step", status="idle"
        )

        with pytest.raises(SwallowedCancelledError):
            await scheduler.tick([s1, s2], [])

    @pytest.mark.asyncio
    async def test_no_false_positives_normal_completion(self) -> None:
        """2 Slices, both succeed → no exception, all IDs returned."""
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
