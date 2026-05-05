"""Hot state container — in-memory pydantic model tracking active session state.

Synced from daemon SSE events on worker attach and kept up-to-date
as events stream in.  Provides a single source of truth for the
worker's view of the current state machine position.

Consumed by:
- Version handshake (Phase 064) — reports current mode
- Hook event forwarding (Phase 063) — includes slice/step context
- Session teardown (Phase 065) — flushes in-progress state
"""

from __future__ import annotations

import structlog
from pydantic import BaseModel

log = structlog.get_logger(__name__)


class HotState(BaseModel):
    """In-memory snapshot of the active session state.

    All fields default to ``None`` — the daemon populates them as
    events are received via the SSE bridge (Phase 061).
    """

    active_slice_id: str | None = None
    active_step_id: str | None = None
    current_mode: str | None = None
    in_progress_drill: str | None = None

    def apply_event(self, event: dict[str, object]) -> None:
        """Mutate this state based on an SSE event payload.

        The *event* dict is expected to contain an ``event_type`` key
        and optionally a ``data`` sub-dict.  Unknown event types are
        logged at debug level and silently ignored.
        """
        event_type = str(event.get("event_type", ""))

        if event_type.startswith("slice."):
            self._apply_slice_event(event_type, event)
        elif event_type.startswith("step."):
            self._apply_step_event(event_type, event)
        elif event_type.startswith("mode."):
            self._apply_mode_event(event_type, event)
        elif event_type.startswith("drill."):
            self._apply_drill_event(event_type, event)
        else:
            log.debug("hot_state.unknown_event_type", event_type=event_type)

    def _apply_slice_event(self, event_type: str, event: dict[str, object]) -> None:
        data = _event_data(event)
        if event_type == "slice.planned":
            slice_id = str(data.get("slice_id", ""))
            if slice_id:
                self.active_slice_id = slice_id
                log.info(
                    "hot_state.slice_active",
                    slice_id=slice_id,
                )
        elif event_type == "slice.shipped":
            self.active_slice_id = None
            log.info("hot_state.slice_cleared")

    def _apply_step_event(self, event_type: str, event: dict[str, object]) -> None:
        data = _event_data(event)
        step_id = str(data.get("step_id", ""))
        if not step_id:
            return

        self.active_step_id = step_id
        log.info(
            "hot_state.step_updated",
            step_id=step_id,
            event_type=event_type,
        )

    def _apply_mode_event(self, event_type: str, event: dict[str, object]) -> None:
        if event_type == "mode.activated":
            data = _event_data(event)
            mode = str(data.get("mode", ""))
            if mode:
                self.current_mode = mode
                log.info("hot_state.mode_activated", mode=mode)

    def _apply_drill_event(self, event_type: str, event: dict[str, object]) -> None:
        data = _event_data(event)
        if event_type == "drill.prepared":
            drill_id = str(data.get("drill_id", ""))
            if drill_id:
                self.in_progress_drill = drill_id
                log.info("hot_state.drill_active", drill_id=drill_id)
        elif event_type == "drill.submitted":
            self.in_progress_drill = None
            log.info("hot_state.drill_cleared")


def _event_data(event: dict[str, object]) -> dict[str, object]:
    """Extract the ``data`` sub-dict from an event payload.

    Returns an empty dict if ``data`` is missing or not a dict.
    """
    data = event.get("data")
    if isinstance(data, dict):
        return data  # type: ignore[return-value]
    return {}
