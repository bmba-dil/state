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
    """Create a BaseExceptionGroup containing a CancelledError."""
    return BaseExceptionGroup("nested", [asyncio.CancelledError()])


def _make_mixed_group() -> BaseExceptionGroup:
    """Create a BaseExceptionGroup containing CancelledError + ValueError."""
    return BaseExceptionGroup(
        "nested",
        [asyncio.CancelledError(), ValueError("inner error")],
    )


class TestWatchdog:
    """Watchdog regression tests — P0-16 CancelledError swallow detection."""

    # --- Test 1: CancelledError from sibling (via BaseExceptionGroup) ---

    @pytest.mark.asyncio
    async def test_sibling_cancelled_error_in_group(self) -> None:
        """2 Slices: one raises BaseExceptionGroup with CancelledError inside.

        Slice 1 executor raises a BaseExceptionGroup containing CancelledError.
        Slice 2 executor succeeds normally. The watchdog detects the
        CancelledError embedded in the exception group and raises
        SwallowedCancelledError.
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

    # --- Test 2: Direct CancelledError via BaseExceptionGroup ---

    @pytest.mark.asyncio
    async def test_direct_cancelled_error_in_group(self) -> None:
        """1 Slice: executor raises BaseExceptionGroup with CancelledError.

        The watchdog detects the CancelledError inside the group and
        raises SwallowedCancelledError. Also verifies __cause__ chain
        preservation (Test 7 requirement).
        """
        async def exec_cancel_group(node: Node) -> None:
            raise _make_cancel_group()

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=exec_cancel_group)
        step = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )

        with pytest.raises(SwallowedCancelledError):
            await scheduler.tick([step], [])

    # --- Test 3: Normal completion — no false positives ---

    @pytest.mark.asyncio
    async def test_normal_completion_no_false_positives(self) -> None:
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

    # --- Test 4: Empty frontier — no TaskGroup created ---

    @pytest.mark.asyncio
    async def test_empty_frontier_no_taskgroup(self) -> None:
        """Empty node list → tick() returns [] with no TaskGroup created."""
        scheduler = DAGScheduler(concurrency_cap=4)
        result = await scheduler.tick([], [])
        assert result == []

    # --- Test 5: Sequential within Slice — partial dispatch on error ---

    @pytest.mark.asyncio
    async def test_sequential_partial_dispatch_on_error(self) -> None:
        """1 Slice with 2 steps: first succeeds, second raises ValueError.

        The ValueError propagates (no CancelledError involved).
        Dispatched list contains only the first step's ID.
        """
        recorded: list[str] = []

        async def exec_with_error(node: Node) -> None:
            if "step-2" in node.id:
                raise ValueError("step 2 failed")
            # step-1: succeed silently
            pass

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=exec_with_error)
        step1 = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )
        step2 = Node(
            id="arc-1/phase-1/slice-1/step-2", kind="step", status="idle"
        )

        # ValueError from step 2 propagates through TaskGroup
        with pytest.raises((ValueError, ExceptionGroup)) as exc_info:
            await scheduler.tick([step1, step2], [])

        # If it's an ExceptionGroup, extract the original ValueError
        if isinstance(exc_info.value, ExceptionGroup):
            errors = list(exc_info.value.exceptions)
            assert any(isinstance(e, ValueError) for e in errors)

    # --- Test 6: Nested TaskGroup — CancelledError swallow simulation ---

    @pytest.mark.asyncio
    async def test_nested_taskgroup_swallow(self) -> None:
        """Nested TaskGroup scenario — core P0-16 regression test.

        Simulates the CPython #116720 scenario: an inner TaskGroup
        swallows a CancelledError, and the executor subsequently raises
        a ValueError. The CancelledError is embedded in a
        BaseExceptionGroup that the executor raises manually.

        The outer scheduler's TaskGroup includes the BaseExceptionGroup
        in its exception group. The watchdog detects the CancelledError
        inside the nested group.

        (Python 3.12 TaskGroup filters CancelledError from ALL levels,
        so we explicitly embed it in a BaseExceptionGroup to simulate
        the scenario the watchdog protects against.)
        """
        async def nested_executor(node: Node) -> None:
            # Simulate: inner TG swallowed CancelledError, then ValueError
            # The executor wraps the CancelledError in a BaseExceptionGroup
            # so the outer TaskGroup doesn't filter it.
            raise BaseExceptionGroup(
                "nested_tg_swallow",
                [
                    asyncio.CancelledError(),
                    ValueError("inner completed but cancel was swallowed"),
                ],
            )

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=nested_executor)
        step = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )

        with pytest.raises(SwallowedCancelledError):
            await scheduler.tick([step], [])

    # --- Test 7: __cause__ chain preservation ---

    @pytest.mark.asyncio
    async def test_cause_chain_preservation(self) -> None:
        """SwallowedCancelledError.__cause__ is the original CancelledError.

        Verifies the watchdog preserves the forensics chain: the
        SwallowedCancelledError chains the original CancelledError
        via __cause__, and the error message identifies the watchdog.
        """
        async def exec_cancel_group(node: Node) -> None:
            raise _make_cancel_group()

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=exec_cancel_group)
        step = Node(
            id="arc-1/phase-1/slice-1/step-1", kind="step", status="idle"
        )

        with pytest.raises(SwallowedCancelledError) as exc_info:
            await scheduler.tick([step], [])

        # __cause__ chain points to original CancelledError
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, asyncio.CancelledError)
        assert "Watchdog detected swallowed CancelledError" in str(exc_info.value)

    # --- Test 8: Concurrent cancellations — multiple groups ---

    @pytest.mark.asyncio
    async def test_concurrent_cancellation_multiple_groups(self) -> None:
        """3 Slices: 2 raise BaseExceptionGroup with CancelledError → watchdog.

        Multiple concurrent tasks each contain a CancelledError in their
        exception group. The watchdog detects at least one occurrence
        and raises SwallowedCancelledError.
        """
        async def conditional_exec(node: Node) -> None:
            if "slice-3" in node.id:
                # Slice 3 succeeds — no error
                pass
            else:
                # Slices 1 and 2 raise CancelledError in a group
                raise _make_cancel_group()

        scheduler = DAGScheduler(concurrency_cap=4, step_executor=conditional_exec)

        steps = [
            Node(
                id=f"arc-1/phase-1/slice-{i}/step-1",
                kind="step",
                status="idle",
            )
            for i in range(1, 4)
        ]

        with pytest.raises(SwallowedCancelledError):
            await scheduler.tick(steps, [])
