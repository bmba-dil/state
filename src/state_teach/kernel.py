"""Kolb-cycle state machine: CE->RO->AC->AE for concept teaching."""

from __future__ import annotations

from typing import Literal

KolbStage = Literal["CE", "RO", "AC", "AE", "MASTERED", "REVIEW"]


class KolbMachine:
    """Finite state machine for the Kolb experiential learning cycle."""

    stage: KolbStage = "CE"

    async def on_event(self, event_type: str, data: dict) -> None: ...
