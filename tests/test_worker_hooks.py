"""Tests for state_worker.hooks — HookQueue buffer and flush (Phase 065)."""

from __future__ import annotations

from unittest import mock

import pytest

from src.state_worker.hooks import HookQueue


class TestHookQueueEnqueue:
    """Enqueue and count tracking."""

    def test_empty_queue_has_zero_count(self) -> None:
        q = HookQueue()
        assert q.flush_count == 0

    def test_enqueue_increments_count(self) -> None:
        q = HookQueue()
        q.enqueue("step.created", {"step": 1})
        assert q.flush_count == 1

    def test_enqueue_multiple(self) -> None:
        q = HookQueue()
        q.enqueue("a", {"n": 1})
        q.enqueue("b", {"n": 2})
        q.enqueue("c", {"n": 3})
        assert q.flush_count == 3


class TestHookQueueFlush:
    """Flush behavior with mocked forward_hook."""

    async def test_flush_empty_queue_returns_zero(self) -> None:
        q = HookQueue()
        result = await q.flush_pending("/tmp/fake.sock")
        assert result == 0

    async def test_flush_clears_queue_after_flush(self) -> None:
        q = HookQueue()
        q.enqueue("test.hook", {"key": "value"})

        with mock.patch(
            "src.state_worker.hooks.forward_hook", return_value=True
        ) as mock_fwd:
            result = await q.flush_pending("/tmp/fake.sock")

        assert result == 1
        assert q.flush_count == 0

    async def test_flush_forwards_all_events(self) -> None:
        q = HookQueue()
        q.enqueue("hook.one", {"a": 1})
        q.enqueue("hook.two", {"b": 2})
        q.enqueue("hook.three", {"c": 3})

        forwarded: list[tuple[str, dict[str, object]]] = []

        async def mock_forward(hook_name, payload, socket_path, **kwargs):
            forwarded.append((hook_name, payload))
            return True

        with mock.patch(
            "src.state_worker.hooks.forward_hook", side_effect=mock_forward
        ):
            result = await q.flush_pending("/tmp/fake.sock")

        assert result == 3
        assert len(forwarded) == 3
        assert forwarded[0] == ("hook.one", {"a": 1})
        assert forwarded[1] == ("hook.two", {"b": 2})
        assert forwarded[2] == ("hook.three", {"c": 3})

    async def test_flush_counts_success_and_failure(self) -> None:
        q = HookQueue()
        q.enqueue("good", {})
        q.enqueue("bad", {})
        q.enqueue("good2", {})

        call_count = 0

        async def mock_forward(hook_name, payload, socket_path, **kwargs):
            nonlocal call_count
            call_count += 1
            return hook_name.startswith("good")

        with mock.patch(
            "src.state_worker.hooks.forward_hook", side_effect=mock_forward
        ):
            result = await q.flush_pending("/tmp/fake.sock")

        assert result == 2
        assert call_count == 3
        assert q.flush_count == 0

    async def test_flush_best_effort_on_failure(self) -> None:
        """Even if all hooks fail, queue is still cleared (best-effort)."""
        q = HookQueue()
        q.enqueue("fail1", {})
        q.enqueue("fail2", {})

        with mock.patch(
            "src.state_worker.hooks.forward_hook", return_value=False
        ):
            result = await q.flush_pending("/tmp/fake.sock")

        assert result == 0
        assert q.flush_count == 0
