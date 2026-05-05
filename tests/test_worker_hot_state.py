"""Tests for state_worker.hot_state — state container and event application."""

from __future__ import annotations

import pytest

from src.state_worker.hot_state import HotState


class TestHotStateInitial:
    """HotState initial state — all fields default to None."""

    def test_defaults_all_none(self) -> None:
        state = HotState()
        assert state.active_slice_id is None
        assert state.active_step_id is None
        assert state.current_mode is None
        assert state.in_progress_drill is None


class TestHotStateApply:
    """HotState.apply_event for each event category."""

    def test_slice_planned_sets_active_slice(self) -> None:
        state = HotState()
        state.apply_event({
            "event_type": "slice.planned",
            "data": {"slice_id": "slice-abc"},
        })
        assert state.active_slice_id == "slice-abc"

    def test_slice_shipped_clears_active_slice(self) -> None:
        state = HotState()
        state.active_slice_id = "slice-abc"
        state.apply_event({"event_type": "slice.shipped", "data": {}})
        assert state.active_slice_id is None

    def test_step_event_sets_active_step(self) -> None:
        state = HotState()
        state.apply_event({
            "event_type": "step.planned",
            "data": {"step_id": "step-001"},
        })
        assert state.active_step_id == "step-001"

    def test_step_blocked_keeps_step(self) -> None:
        state = HotState()
        state.apply_event({
            "event_type": "step.blocked",
            "data": {"step_id": "step-blocked", "reason": "dep"},
        })
        assert state.active_step_id == "step-blocked"

    def test_mode_activated_sets_current_mode(self) -> None:
        state = HotState()
        state.apply_event({
            "event_type": "mode.activated",
            "data": {"mode": "build"},
        })
        assert state.current_mode == "build"

    def test_drill_prepared_sets_drill(self) -> None:
        state = HotState()
        state.apply_event({
            "event_type": "drill.prepared",
            "data": {"drill_id": "drill-101"},
        })
        assert state.in_progress_drill == "drill-101"

    def test_drill_submitted_clears_drill(self) -> None:
        state = HotState()
        state.in_progress_drill = "drill-101"
        state.apply_event({"event_type": "drill.submitted", "data": {}})
        assert state.in_progress_drill is None

    def test_unknown_event_type_noop(self) -> None:
        state = HotState()
        state.apply_event({"event_type": "unknown.whatever", "data": {"x": 1}})
        assert state.active_slice_id is None
        assert state.active_step_id is None
        assert state.current_mode is None

    def test_no_data_field_handled(self) -> None:
        state = HotState()
        state.apply_event({"event_type": "slice.planned"})
        assert state.active_slice_id is None


class TestHotStateSequential:
    """Multiple events in sequence."""

    def test_full_session_lifecycle(self) -> None:
        state = HotState()

        # Mode activated
        state.apply_event({
            "event_type": "mode.activated",
            "data": {"mode": "build"},
        })
        assert state.current_mode == "build"

        # Slice planned
        state.apply_event({
            "event_type": "slice.planned",
            "data": {"slice_id": "s1"},
        })
        assert state.active_slice_id == "s1"

        # Step started
        state.apply_event({
            "event_type": "step.planned",
            "data": {"step_id": "step-1"},
        })
        assert state.active_step_id == "step-1"

        # Drill active
        state.apply_event({
            "event_type": "drill.prepared",
            "data": {"drill_id": "d1"},
        })
        assert state.in_progress_drill == "d1"

        # Drill done
        state.apply_event({"event_type": "drill.submitted", "data": {}})
        assert state.in_progress_drill is None

        # Slice shipped
        state.apply_event({"event_type": "slice.shipped", "data": {}})
        assert state.active_slice_id is None

    def test_mode_switch(self) -> None:
        state = HotState()
        state.apply_event({
            "event_type": "mode.activated",
            "data": {"mode": "build"},
        })
        state.apply_event({
            "event_type": "mode.activated",
            "data": {"mode": "teach"},
        })
        assert state.current_mode == "teach"
