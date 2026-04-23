"""Step state machine: idle->discussing->planning->executing->verifying->done."""

from __future__ import annotations

from typing import Literal

StepState = Literal["idle", "discussing", "planning", "executing", "verifying", "done", "blocked", "abandoned"]


class StepMachine:
    """Finite state machine for a single Step's lifecycle."""

    state: StepState = "idle"

    async def on_event(self, event_type: str, data: dict) -> None: ...
