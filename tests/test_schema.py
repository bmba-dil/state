"""Smoke tests for state_core.schema."""

from __future__ import annotations

import pytest

from src.state_core.schema import EventEnvelope


def test_event_envelope_extra_forbid() -> None:
    e = EventEnvelope(id="test-id", type="test.event", ts="2026-04-23T00:00:00Z", data={"key": "val"})
    assert e.id == "test-id"
    assert e.type == "test.event"
    with pytest.raises(ValueError):
        EventEnvelope(id="x", type="y", ts="z", extra_field="should_fail")  # type: ignore[call-arg]
