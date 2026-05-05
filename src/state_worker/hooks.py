"""Hook event buffering and flush for worker session teardown (Phase 065).

Collects hook events received from the plugin shim during a session and
flushes them to the daemon on shutdown with best-effort forwarding.
"""

from __future__ import annotations

import structlog

from state_worker.bridge import forward_hook

log = structlog.get_logger(__name__)


class HookQueue:
    """Buffer for hook events pending forward to the daemon.

    During a session the plugin shim enqueues hook events (e.g. step
    transitions, user actions).  On shutdown, :meth:`flush_pending`
    forwards every buffered event using :func:`forward_hook` before
    the worker disconnects from the daemon.
    """

    def __init__(self) -> None:
        self._pending: list[tuple[str, dict[str, object]]] = []

    def enqueue(self, hook_name: str, payload: dict[str, object]) -> None:
        """Add a hook event to the pending queue."""
        self._pending.append((hook_name, payload))

    @property
    def flush_count(self) -> int:
        """Number of events waiting to be flushed."""
        return len(self._pending)

    async def flush_pending(self, socket_path: str) -> int:
        """Forward all pending events to the daemon and clear the queue.

        Returns:
            Number of events successfully forwarded.
        """
        if not self._pending:
            return 0

        log.debug(
            "worker.hooks.flush_start",
            pending_count=len(self._pending),
        )

        succeeded = 0
        for hook_name, payload in self._pending:
            ok = await forward_hook(
                hook_name=hook_name,
                payload=payload,
                socket_path=socket_path,
            )
            if ok:
                succeeded += 1
            else:
                log.warning(
                    "worker.hooks.flush_failed",
                    hook=hook_name,
                )

        log.info(
            "worker.hooks.flush_done",
            total=len(self._pending),
            succeeded=succeeded,
            failed=len(self._pending) - succeeded,
        )
        self._pending.clear()
        return succeeded
