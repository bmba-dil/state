"""Pydantic models for Arc/Phase/Slice/Step/Concept event types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EventEnvelope(BaseModel):
    """Base event envelope with ULID id and ISO8601 timestamp."""

    model_config = ConfigDict(extra="forbid")
    id: str = ""
    type: str = ""
    ts: str = ""
    data: dict = {}
