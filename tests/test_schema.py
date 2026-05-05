"""Comprehensive tests for state_core.schema event types.

Covers: all 29 data models, all 29 typed event classes, discriminated
unions, ULID validation, extra="forbid", mode field, deterministic
construction.

Requires: pytest, pytest-asyncio (event loop not needed -- all sync).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from src.state_core.schema import (
    AnyStateEvent,
    ModeConfig,
    validate_mode_config,
    validate_subtree_path,
    ArcCreatedData,
    ArcCreatedEvent,
    ArcRetiredData,
    ArcRetiredEvent,
    ArcUpdatedData,
    ArcUpdatedEvent,
    AuthRefreshedData,
    AuthRefreshedEvent,
    AuthRotatedData,
    AuthRotatedEvent,
    ConceptDrilledData,
    ConceptDrilledEvent,
    ConceptIntroducedData,
    ConceptIntroducedEvent,
    ConceptMasteredData,
    ConceptMasteredEvent,
    ConceptObservedData,
    ConceptObservedEvent,
    ConceptReviewedData,
    ConceptReviewedEvent,
    DecisionAskedData,
    DecisionAskedEvent,
    DecisionMadeData,
    DecisionMadeEvent,
    DrillGradedData,
    DrillGradedEvent,
    DrillPreparedData,
    DrillPreparedEvent,
    DrillSubmittedData,
    DrillSubmittedEvent,
    EventEnvelope,
    ModeActivatedData,
    ModeActivatedEvent,
    PhaseCompletedData,
    PhaseCompletedEvent,
    PhasePlannedData,
    PhasePlannedEvent,
    PhaseStartedData,
    PhaseStartedEvent,
    PhaseVerifiedData,
    PhaseVerifiedEvent,
    SlicePlannedData,
    SlicePlannedEvent,
    SliceRevertedData,
    SliceRevertedEvent,
    SliceShippedData,
    SliceShippedEvent,
    SliceWorktreeReadyData,
    SliceWorktreeReadyEvent,
    StepAdvancedData,
    StepAdvancedEvent,
    StepBlockedData,
    StepBlockedEvent,
    StepDiscussedData,
    StepDiscussedEvent,
    StepExecutedData,
    StepExecutedEvent,
    StepPlannedData,
    StepPlannedEvent,
    StepRevertedData,
    StepRevertedEvent,
    StepSnapshottedData,
    StepSnapshottedEvent,
    StepVerifyFailedData,
    StepVerifyFailedEvent,
    StepVerifyPassedData,
    StepVerifyPassedEvent,
    StepVerifyStartedData,
    StepVerifyStartedEvent,
    build_event,
)

# -- Test fixtures --------------------------------------------------------------------

VALID_ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
"""A valid ULID for testing."""

INVALID_ULID = "not-a-ulid"


def make_envelope_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return standard EventEnvelope construction kwargs."""
    kwargs: dict[str, Any] = {
        "id": VALID_ULID,
        "seq": 1,
        "aggregate_id": "arc-01",
        "ts": "2026-04-23T00:00:00Z",
        "mode": "build",
    }
    kwargs.update(overrides)
    return kwargs


# -- EventEnvelope tests ---------------------------------------------------------------


class TestEventEnvelope:
    """Tests for the base EventEnvelope model."""

    def test_default_construction(self) -> None:
        """All fields have sensible defaults."""
        e = EventEnvelope()
        assert e.id == ""
        assert e.seq == 0
        assert e.aggregate_type == "arc"
        assert e.type == ""
        assert e.data == {}
        assert e.ts == ""
        assert e.mode == "kernel"

    def test_ulid_validation_valid(self) -> None:
        """Valid ULID passes validation."""
        e = EventEnvelope(id=VALID_ULID)
        assert e.id == VALID_ULID

    def test_ulid_validation_invalid(self) -> None:
        """Invalid ULID raises ValidationError."""
        with pytest.raises(ValidationError):
            EventEnvelope(id=INVALID_ULID)

    def test_ulid_empty_string_allowed(self) -> None:
        """Empty string id passes ULID validation (not yet assigned)."""
        e = EventEnvelope(id="")
        assert e.id == ""

    def test_extra_forbid(self) -> None:
        """Envelope rejects unknown fields."""
        with pytest.raises(ValidationError):
            EventEnvelope(nonexistent_field="value")  # type: ignore[call-arg]

    def test_mode_literals(self) -> None:
        """All three mode values are accepted."""
        for mode in ("build", "teach", "kernel"):
            e = EventEnvelope(mode=mode)  # type: ignore[arg-type]
            assert e.mode == mode

    def test_mode_rejects_invalid(self) -> None:
        """Invalid mode value raises ValidationError."""
        with pytest.raises(ValidationError):
            EventEnvelope(mode="invalid")  # type: ignore[arg-type]

    def test_aggregate_type_literals(self) -> None:
        """All nine aggregate types are accepted."""
        for agg in ("arc", "phase", "slice", "step", "concept", "drill", "decision", "auth", "mode"):
            e = EventEnvelope(aggregate_type=agg)  # type: ignore[arg-type]
            assert e.aggregate_type == agg


# -- Data model tests ------------------------------------------------------------------


class TestArcDataModels:
    """Tests for Arc aggregate data models."""

    def test_arc_created_data(self) -> None:
        d = ArcCreatedData(title="Foundation", goal="Build the core")
        assert d.title == "Foundation"
        assert d.goal == "Build the core"
        with pytest.raises(ValidationError):
            ArcCreatedData(title="Only", goal="", extra="bad")  # type: ignore[call-arg]

    def test_arc_retired_data(self) -> None:
        d = ArcRetiredData(reason="Superseded by v2")
        assert d.reason == "Superseded by v2"

    def test_arc_updated_data(self) -> None:
        d = ArcUpdatedData(changed_fields=["goal", "title"])
        assert "goal" in d.changed_fields


class TestPhaseDataModels:
    """Tests for Phase aggregate data models."""

    def test_phase_planned_data(self) -> None:
        d = PhasePlannedData(phase_number=5, title="Auth", goal="Implement auth")
        assert d.phase_number == 5

    def test_phase_started_data_empty(self) -> None:
        """PhaseStartedData has no required fields beyond the empty model."""
        d = PhaseStartedData()
        assert isinstance(d, PhaseStartedData)

    def test_phase_verified_data(self) -> None:
        d = PhaseVerifiedData(passed=True, summary="All checks OK")
        assert d.passed is True

    def test_phase_completed_data(self) -> None:
        d = PhaseCompletedData(passed=True)
        assert d.passed is True


class TestStepDataModels:
    """Tests for Step aggregate data models (richest aggregate -- 10 events)."""

    def test_step_discussed_data(self) -> None:
        d = StepDiscussedData(approach_summary="Use asyncio gather")
        assert "gather" in d.approach_summary

    def test_step_planned_data(self) -> None:
        d = StepPlannedData(
            goal="Write the writer",
            verify_contract=[{"type": "tests", "cmd": "pytest"}],
        )
        assert d.verify_contract[0]["type"] == "tests"

    def test_step_executed_data(self) -> None:
        d = StepExecutedData(changes_summary="Created events.py")
        assert d.changes_summary == "Created events.py"

    def test_step_verify_started_data(self) -> None:
        d = StepVerifyStartedData(contract=[{"type": "lint"}])
        assert len(d.contract) == 1

    def test_step_verify_passed_data(self) -> None:
        d = StepVerifyPassedData(duration_ms=150)
        assert d.duration_ms == 150

    def test_step_verify_failed_data(self) -> None:
        d = StepVerifyFailedData(reason="Linting error", details="Line 42: bad indent")
        assert "Line 42" in d.details

    def test_step_advanced_data(self) -> None:
        d = StepAdvancedData(new_state="executing")
        assert d.new_state == "executing"

    def test_step_blocked_data(self) -> None:
        d = StepBlockedData(reason="Waiting for API key")
        assert d.reason == "Waiting for API key"

    def test_step_snapshotted_data(self) -> None:
        d = StepSnapshottedData(snapshot_hash="abc123", tier="step")
        assert d.tier == "step"

    def test_step_reverted_data(self) -> None:
        d = StepRevertedData(snapshot_hash="abc123", reason="Test failed")
        assert d.snapshot_hash == "abc123"


class TestConceptDataModels:
    """Tests for Concept aggregate data models."""

    def test_concept_introduced_data(self) -> None:
        d = ConceptIntroducedData(
            concept_id="variables", name="Variables", prerequisites=[]
        )
        assert d.name == "Variables"

    def test_concept_observed_data(self) -> None:
        d = ConceptObservedData(observation="User defined x=5", classification="correct")
        assert d.classification == "correct"

    def test_concept_drilled_data(self) -> None:
        d = ConceptDrilledData(score=0.85, items_attempted=10)
        assert d.score == 0.85

    def test_concept_mastered_data(self) -> None:
        d = ConceptMasteredData(mastery_probability=0.92)
        assert d.mastery_probability == 0.92

    def test_concept_reviewed_data(self) -> None:
        d = ConceptReviewedData(mastery_delta=0.05)
        assert d.mastery_delta == 0.05


class TestDrillDataModels:
    """Tests for Drill aggregate data models."""

    def test_drill_prepared_data(self) -> None:
        d = DrillPreparedData(question_count=5)
        assert d.question_count == 5

    def test_drill_submitted_data(self) -> None:
        d = DrillSubmittedData(answers=[{"q": 1, "a": "x"}])
        assert len(d.answers) == 1

    def test_drill_graded_data(self) -> None:
        d = DrillGradedData(score=4.0, max_score=5.0)
        assert d.score == 4.0


class TestModeDecisionAuthDataModels:
    """Tests for Mode, Decision, and Auth aggregate data models."""

    def test_mode_activated_data_old_mode_new_mode(self) -> None:
        """ModeActivatedData accepts old_mode and new_mode fields."""
        d = ModeActivatedData(old_mode="build", new_mode="teach")
        assert d.old_mode == "build"
        assert d.new_mode == "teach"

    def test_mode_activated_data_rejects_mode_value(self) -> None:
        """ModeActivatedData rejects the old mode_value field name."""
        with pytest.raises(ValidationError):
            ModeActivatedData(mode_value="build")

    def test_mode_activated_data_rejects_extra_fields(self) -> None:
        """ModeActivatedData with extra=forbid rejects unknown fields."""
        with pytest.raises(ValidationError):
            ModeActivatedData(
                old_mode="build", new_mode="teach", extra_field=1
            )

    def test_decision_asked_data(self) -> None:
        d = DecisionAskedData(
            question="Which approach?",
            options=[{"label": "A", "desc": "Fast"}, {"label": "B", "desc": "Safe"}],
        )
        assert len(d.options) == 2

    def test_decision_made_data(self) -> None:
        d = DecisionMadeData(answer="A", reason="Faster iteration")
        assert d.answer == "A"

    def test_auth_refreshed_data(self) -> None:
        d = AuthRefreshedData(provider="anthropic", outcome="ok")
        assert d.outcome == "ok"

    def test_auth_rotated_data(self) -> None:
        d = AuthRotatedData(provider="anthropic", index=2)
        assert d.index == 2

    def test_all_data_models_reject_extra(self) -> None:
        """Every data model enforces extra='forbid'."""
        for model_cls, kwargs in [
            (ArcCreatedData, {"title": "T", "goal": "G"}),
            (ArcRetiredData, {"reason": "R"}),
            (ArcUpdatedData, {"changed_fields": ["a"]}),
            (PhasePlannedData, {"phase_number": 1, "title": "T", "goal": "G"}),
            (PhaseStartedData, {}),
            (PhaseVerifiedData, {"passed": True, "summary": "S"}),
            (PhaseCompletedData, {"passed": True}),
            (SlicePlannedData, {"slice_number": 1, "title": "T", "goal": "G"}),
            (SliceWorktreeReadyData, {"worktree_name": "w", "branch": "b", "dir": "/x"}),
            (SliceShippedData, {"snapshot_hash": "abc"}),
            (SliceRevertedData, {"reason": "R"}),
            (StepDiscussedData, {"approach_summary": "S"}),
            (StepPlannedData, {"goal": "G", "verify_contract": []}),
            (StepExecutedData, {"changes_summary": "S"}),
            (StepVerifyStartedData, {"contract": []}),
            (StepVerifyPassedData, {"duration_ms": 1}),
            (StepVerifyFailedData, {"reason": "R", "details": "D"}),
            (StepAdvancedData, {"new_state": "s"}),
            (StepBlockedData, {"reason": "R"}),
            (StepSnapshottedData, {"snapshot_hash": "h", "tier": "t"}),
            (StepRevertedData, {"snapshot_hash": "h", "reason": "R"}),
            (ConceptIntroducedData, {"concept_id": "c", "name": "N", "prerequisites": []}),
            (ConceptObservedData, {"observation": "O", "classification": "C"}),
            (ConceptDrilledData, {"score": 0.5, "items_attempted": 1}),
            (ConceptMasteredData, {"mastery_probability": 0.9}),
            (ConceptReviewedData, {"mastery_delta": 0.1}),
            (DrillPreparedData, {"question_count": 1}),
            (DrillSubmittedData, {"answers": []}),
            (DrillGradedData, {"score": 1.0, "max_score": 1.0}),
            (ModeActivatedData, {"old_mode": "build", "new_mode": "build"}),
            (DecisionAskedData, {"question": "Q", "options": []}),
            (DecisionMadeData, {"answer": "A", "reason": "R"}),
            (AuthRefreshedData, {"provider": "p", "outcome": "ok"}),
            (AuthRotatedData, {"provider": "p", "index": 0}),
        ]:
            obj = model_cls(**kwargs)
            with pytest.raises(ValidationError):
                model_cls(**kwargs, stray_field="should_fail")  # type: ignore[call-arg]
            assert obj is not None


# -- Typed event construction tests ----------------------------------------------------


def _build_event(event_cls: type, data_obj: Any, **type_overrides: Any) -> Any:
    """Helper to construct a typed event with standard envelope kwargs."""
    kwargs = make_envelope_kwargs(aggregate_id="test-id", **type_overrides)
    return event_cls(data=data_obj, **kwargs)


class TestTypedEvents:
    """Tests for typed event construction for all 9 aggregates."""

    @pytest.mark.parametrize(
        "event_cls, data_obj, type_str, agg_type",
        [
            (ArcCreatedEvent, ArcCreatedData(title="T", goal="G"), "state.arc.created", "arc"),
            (ArcRetiredEvent, ArcRetiredData(reason="R"), "state.arc.retired", "arc"),
            (ArcUpdatedEvent, ArcUpdatedData(changed_fields=["x"]), "state.arc.updated", "arc"),
            (PhasePlannedEvent, PhasePlannedData(phase_number=1, title="T", goal="G"), "state.phase.planned", "phase"),
            (PhaseStartedEvent, PhaseStartedData(), "state.phase.started", "phase"),
            (PhaseVerifiedEvent, PhaseVerifiedData(passed=True, summary="S"), "state.phase.verified", "phase"),
            (PhaseCompletedEvent, PhaseCompletedData(passed=True), "state.phase.completed", "phase"),
            (SlicePlannedEvent, SlicePlannedData(slice_number=1, title="T", goal="G"), "state.slice.planned", "slice"),
            (SliceWorktreeReadyEvent, SliceWorktreeReadyData(
                worktree_name="w", branch="b", dir="/x",
            ), "state.slice.worktree_ready", "slice"),
            (SliceShippedEvent, SliceShippedData(snapshot_hash="abc"), "state.slice.shipped", "slice"),
            (SliceRevertedEvent, SliceRevertedData(reason="R"), "state.slice.reverted", "slice"),
            (StepDiscussedEvent, StepDiscussedData(approach_summary="S"), "state.step.discussed", "step"),
            (StepPlannedEvent, StepPlannedData(goal="G", verify_contract=[]), "state.step.planned", "step"),
            (StepExecutedEvent, StepExecutedData(changes_summary="S"), "state.step.executed", "step"),
            (StepVerifyStartedEvent, StepVerifyStartedData(contract=[]), "state.step.verify_started", "step"),
            (StepVerifyPassedEvent, StepVerifyPassedData(duration_ms=1), "state.step.verify_passed", "step"),
            (StepVerifyFailedEvent, StepVerifyFailedData(reason="R", details="D"), "state.step.verify_failed", "step"),
            (StepAdvancedEvent, StepAdvancedData(new_state="s"), "state.step.advanced", "step"),
            (StepBlockedEvent, StepBlockedData(reason="R"), "state.step.blocked", "step"),
            (StepSnapshottedEvent, StepSnapshottedData(snapshot_hash="h", tier="t"), "state.step.snapshotted", "step"),
            (StepRevertedEvent, StepRevertedData(snapshot_hash="h", reason="R"), "state.step.reverted", "step"),
            (ConceptIntroducedEvent, ConceptIntroducedData(
                concept_id="c", name="N", prerequisites=[],
            ), "state.concept.introduced", "concept"),
            (ConceptObservedEvent, ConceptObservedData(
                observation="O", classification="C",
            ), "state.concept.observed", "concept"),
            (ConceptDrilledEvent, ConceptDrilledData(score=0.5, items_attempted=1), "state.concept.drilled", "concept"),
            (ConceptMasteredEvent, ConceptMasteredData(mastery_probability=0.9), "state.concept.mastered", "concept"),
            (ConceptReviewedEvent, ConceptReviewedData(mastery_delta=0.1), "state.concept.reviewed", "concept"),
            (DrillPreparedEvent, DrillPreparedData(question_count=1), "state.drill.prepared", "drill"),
            (DrillSubmittedEvent, DrillSubmittedData(answers=[]), "state.drill.submitted", "drill"),
            (DrillGradedEvent, DrillGradedData(score=1.0, max_score=1.0), "state.drill.graded", "drill"),
            (ModeActivatedEvent, ModeActivatedData(old_mode="kernel", new_mode="build"), "state.mode.activated", "mode"),
            (DecisionAskedEvent, DecisionAskedData(question="Q", options=[]), "state.decision.asked", "decision"),
            (DecisionMadeEvent, DecisionMadeData(answer="A", reason="R"), "state.decision.made", "decision"),
            (AuthRefreshedEvent, AuthRefreshedData(provider="p", outcome="ok"), "state.auth.refreshed", "auth"),
            (AuthRotatedEvent, AuthRotatedData(provider="p", index=0), "state.auth.rotated", "auth"),
        ],
    )
    def test_event_construction(self, event_cls: type, data_obj: Any, type_str: str, agg_type: str) -> None:
        """Every typed event can be constructed and carries correct literals."""
        e = _build_event(event_cls, data_obj)
        assert e.type == type_str, f"{event_cls.__name__}: expected type={type_str!r}, got {e.type!r}"
        assert e.aggregate_type == agg_type, f"{event_cls.__name__}: expected aggregate_type={agg_type!r}"
        assert e.data == data_obj
        assert e.id == VALID_ULID
        assert e.mode == "build"

    def test_event_rejects_mismatched_type(self) -> None:
        """Setting wrong type literal for event class raises ValidationError."""
        with pytest.raises(ValidationError):
            ArcCreatedEvent(
                **make_envelope_kwargs(),
                type="state.arc.retired",  # wrong! should be state.arc.created
                data=ArcCreatedData(title="T", goal="G"),
            )

    def test_event_rejects_wrong_data_type(self) -> None:
        """Providing wrong data model type raises ValidationError."""
        with pytest.raises(ValidationError):
            ArcCreatedEvent(
                **make_envelope_kwargs(),
                data=PhasePlannedData(phase_number=1, title="T", goal="G"),  # wrong data type!
            )


# -- Discriminated union tests ---------------------------------------------------------


class TestDiscriminatedUnions:
    """Tests for Pydantic v2 discriminated union resolution."""

    def _parse(self, raw: dict[str, Any]) -> Any:
        """Parse a raw dict through AnyStateEvent TypeAdapter."""
        ta = TypeAdapter(AnyStateEvent)
        return ta.validate_python(raw)

    def test_arc_created_resolution(self) -> None:
        result = self._parse({
            "id": VALID_ULID,
            "seq": 1,
            "aggregate_type": "arc",
            "aggregate_id": "arc-01",
            "type": "state.arc.created",
            "data": {"title": "Foundation", "goal": "Build"},
            "ts": "2026-04-23T00:00:00Z",
            "mode": "build",
        })
        assert isinstance(result, ArcCreatedEvent)
        assert result.data.title == "Foundation"

    def test_step_verify_passed_resolution(self) -> None:
        result = self._parse({
            "id": VALID_ULID,
            "seq": 5,
            "aggregate_type": "step",
            "aggregate_id": "step-17.3",
            "type": "state.step.verify_passed",
            "data": {"duration_ms": 150},
            "ts": "2026-04-23T00:00:00Z",
            "mode": "build",
        })
        assert isinstance(result, StepVerifyPassedEvent)
        assert result.data.duration_ms == 150

    def test_concept_mastered_resolution(self) -> None:
        result = self._parse({
            "id": VALID_ULID,
            "seq": 10,
            "aggregate_type": "concept",
            "aggregate_id": "variables",
            "type": "state.concept.mastered",
            "data": {"mastery_probability": 0.92},
            "ts": "2026-04-23T00:00:00Z",
            "mode": "teach",
        })
        assert isinstance(result, ConceptMasteredEvent)
        assert result.data.mastery_probability == 0.92

    def test_invalid_type_rejected(self) -> None:
        """Unknown event type string raises ValidationError."""
        with pytest.raises(ValidationError):
            self._parse({
                "id": VALID_ULID,
                "seq": 1,
                "aggregate_type": "arc",
                "aggregate_id": "arc-01",
                "type": "state.nonexistent.event",
                "data": {},
                "ts": "2026-04-23T00:00:00Z",
                "mode": "build",
            })

    def test_serialize_event_envelope_and_back(self) -> None:
        """Round-trip: construct typed event -> serialize to dict -> parse back."""
        import json

        original = ArcCreatedEvent(
            **make_envelope_kwargs(aggregate_id="arc-01"),
            data=ArcCreatedData(title="Test", goal="Learn"),
        )
        serialized = json.loads(original.model_dump_json())
        parsed = self._parse(serialized)
        assert isinstance(parsed, ArcCreatedEvent)
        assert parsed.data.title == "Test"


# -- Mode filter tests -----------------------------------------------------------------


class TestModeFilter:
    """Events carry mode discriminator for filtering."""

    def test_mode_present_on_all_events(self) -> None:
        """Every typed event has a mode field."""
        e = StepVerifyPassedEvent(
            **make_envelope_kwargs(aggregate_id="step-1"),
            data=StepVerifyPassedData(duration_ms=100),
        )
        assert hasattr(e, "mode")
        assert e.mode in ("build", "teach", "kernel")

    def test_mode_filter_by_literal(self) -> None:
        """Events can be filtered by mode."""
        events = [
            ArcCreatedEvent(
                **make_envelope_kwargs(aggregate_id="a1", mode=m),  # type: ignore[arg-type]
                data=ArcCreatedData(title="T", goal="G"),
            )
            for m in ("build", "teach", "kernel")
        ]
        build_events = [e for e in events if e.mode == "build"]
        assert len(build_events) == 1
        assert build_events[0].mode == "build"

    def test_mode_field_required_for_envelope(self) -> None:
        """Mode is always set; defaults to 'kernel'."""
        e = EventEnvelope()
        assert e.mode == "kernel"


# -- Determinism tests -----------------------------------------------------------------


class TestDeterminism:
    """Event payloads must be deterministic -- no randomness or datetime.now()."""

    def test_event_construction_is_deterministic(self) -> None:
        """Same inputs produce identical events."""
        e1 = ArcCreatedEvent(
            id=VALID_ULID, seq=1, aggregate_id="arc-01",
            type="state.arc.created", aggregate_type="arc",
            data=ArcCreatedData(title="T", goal="G"),
            ts="2026-04-23T00:00:00Z", mode="build",
        )
        e2 = ArcCreatedEvent(
            id=VALID_ULID, seq=1, aggregate_id="arc-01",
            type="state.arc.created", aggregate_type="arc",
            data=ArcCreatedData(title="T", goal="G"),
            ts="2026-04-23T00:00:00Z", mode="build",
        )
        assert e1.model_dump_json() == e2.model_dump_json()

    def test_no_random_defaults_in_data_models(self) -> None:
        """Data model defaults don't introduce randomness."""
        d = ArcCreatedData(title="Fixed", goal="Test")
        assert d.model_dump() == {"title": "Fixed", "goal": "Test"}


# -- Edge cases ------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for edge conditions."""

    def test_empty_data_dict_in_envelope(self) -> None:
        """EventEnvelope accepts empty data dict."""
        e = EventEnvelope(data={})
        assert e.data == {}

    def test_nested_data_in_envelope(self) -> None:
        """EventEnvelope data field accepts nested dicts."""
        e = EventEnvelope(data={"nested": {"key": "val"}})
        assert e.data["nested"]["key"] == "val"

    def test_zero_seq(self) -> None:
        """seq=0 is valid (first event in a stream)."""
        e = EventEnvelope(seq=0)
        assert e.seq == 0

    def test_negative_seq(self) -> None:
        """Negative seq is allowed by schema (runtime enforcement in writer)."""
        e = EventEnvelope(seq=-1)
        assert e.seq == -1

    def test_long_ts_format(self) -> None:
        """ISO 8601 with timezone offset is accepted as string."""
        e = EventEnvelope(ts="2026-04-23T12:00:00+00:00")
        assert "+00:00" in e.ts

    def test_all_modes_on_data_models(self) -> None:
        """Mode='kernel' events should carry correct discriminator."""
        e = EventEnvelope(mode="kernel")
        assert e.mode == "kernel"


# -- Factory helper tests ---------------------------------------------------------------


class TestBuildEvent:
    """Tests for the build_event() factory function."""

    def test_build_arc_created(self) -> None:
        e = build_event(
            ArcCreatedEvent, "arc-01",
            ArcCreatedData(title="Test Arc", goal="Test the arc factory"),
            mode="build",
        )
        assert isinstance(e, ArcCreatedEvent)
        assert e.aggregate_id == "arc-01"
        assert e.data.title == "Test Arc"
        assert e.mode == "build"
        assert len(e.id) == 26  # ULID

    def test_build_step_verify_passed(self) -> None:
        e = build_event(
            StepVerifyPassedEvent, "step-17.3",
            StepVerifyPassedData(duration_ms=250),
            mode="build",
        )
        assert isinstance(e, StepVerifyPassedEvent)
        assert e.data.duration_ms == 250
        assert e.seq == 0

    def test_build_custom_ulid(self) -> None:
        """Explicit id_ override."""
        custom_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        e = build_event(
            ArcCreatedEvent, "arc-01",
            ArcCreatedData(title="T", goal="G"),
            mode="build",
            id_=custom_id,
        )
        assert e.id == custom_id

    def test_build_custom_seq(self) -> None:
        e = build_event(
            ArcCreatedEvent, "arc-01",
            ArcCreatedData(title="T", goal="G"),
            mode="build",
            seq=42,
        )
        assert e.seq == 42

    def test_build_custom_timestamp(self) -> None:
        e = build_event(
            ArcCreatedEvent, "arc-01",
            ArcCreatedData(title="T", goal="G"),
            mode="build",
            ts="2026-06-01T12:00:00Z",
        )
        assert e.ts == "2026-06-01T12:00:00Z"

    def test_build_unique_ulids(self) -> None:
        """Each call generates a unique ULID."""
        e1 = build_event(
            ArcCreatedEvent, "arc-01",
            ArcCreatedData(title="T", goal="G"),
            mode="build",
        )
        e2 = build_event(
            ArcCreatedEvent, "arc-01",
            ArcCreatedData(title="T", goal="G"),
            mode="build",
        )
        assert e1.id != e2.id

    def test_build_defaults_to_kernel_mode(self) -> None:
        e = build_event(
            ArcCreatedEvent, "arc-01",
            ArcCreatedData(title="T", goal="G"),
        )
        assert e.mode == "kernel"

    def test_build_teach_mode(self) -> None:
        e = build_event(
            ConceptMasteredEvent, "variables",
            ConceptMasteredData(mastery_probability=0.9),
            mode="teach",
        )
        assert e.mode == "teach"
        assert e.aggregate_type == "concept"


# -- ModeConfig + validator tests ------------------------------------------------------

class TestModeConfig:
    """Tests for ModeConfig model — persisted mode configuration."""

    def test_construct_valid_build(self) -> None:
        """ModeConfig(mode='build') succeeds."""
        cfg = ModeConfig(mode="build")
        assert cfg.mode == "build"

    def test_construct_valid_teach(self) -> None:
        """ModeConfig(mode='teach') succeeds."""
        cfg = ModeConfig(mode="teach")
        assert cfg.mode == "teach"

    def test_construct_valid_both(self) -> None:
        """ModeConfig(mode='both') succeeds."""
        cfg = ModeConfig(mode="both")
        assert cfg.mode == "both"

    def test_rejects_invalid_mode(self) -> None:
        """ModeConfig(mode='invalid') raises ValidationError."""
        with pytest.raises(ValidationError):
            ModeConfig(mode="invalid")  # type: ignore[arg-type]

    def test_rejects_kernel(self) -> None:
        """ModeConfig(mode='kernel') raises ValidationError — kernel not persistable."""
        with pytest.raises(ValidationError):
            ModeConfig(mode="kernel")  # type: ignore[arg-type]

    def test_rejects_missing_mode(self) -> None:
        """ModeConfig() raises ValidationError — mode field is required."""
        with pytest.raises(ValidationError):
            ModeConfig()  # type: ignore[call-arg]

    def test_rejects_extra_field(self) -> None:
        """ModeConfig(mode='build', extra='x') raises ValidationError."""
        with pytest.raises(ValidationError):
            ModeConfig(mode="build", extra="x")  # type: ignore[call-arg]


class TestValidateModeConfig:
    """Tests for validate_mode_config() standalone validator."""

    def test_returns_mode_config_on_valid(self) -> None:
        """validate_mode_config returns a ModeConfig instance on valid input."""
        result = validate_mode_config({"mode": "build"})
        assert isinstance(result, ModeConfig)
        assert result.mode == "build"

    def test_raises_value_error_on_invalid(self) -> None:
        """validate_mode_config raises ValueError (not ValidationError) on bad mode."""
        with pytest.raises(ValueError, match="Invalid mode config"):
            validate_mode_config({"mode": "invalid"})

    def test_raises_value_error_on_missing(self) -> None:
        """validate_mode_config raises ValueError when mode key is missing."""
        with pytest.raises(ValueError, match="Invalid mode config"):
            validate_mode_config({})

    def test_raises_value_error_on_extra(self) -> None:
        """validate_mode_config raises ValueError on extra fields."""
        with pytest.raises(ValueError, match="Invalid mode config"):
            validate_mode_config({"mode": "build", "x": 1})


# -- validate_subtree_path tests -------------------------------------------------------


class TestValidateSubtreePath:
    """validate_subtree_path() — subtree boundary enforcement."""

    def test_build_path_allowed_in_build_mode(self) -> None:
        """validate_subtree_path('.state/build/foo.json', 'build') does NOT raise."""
        validate_subtree_path(".state/build/foo.json", "build")

    def test_build_path_rejected_in_teach_mode(self) -> None:
        """validate_subtree_path('.state/build/foo.json', 'teach') raises ValueError."""
        with pytest.raises(ValueError, match=r"(?=.*teach)(?=.*build)"):
            validate_subtree_path(".state/build/foo.json", "teach")

    def test_teach_path_allowed_in_teach_mode(self) -> None:
        """validate_subtree_path('.state/teach/bar.json', 'teach') does NOT raise."""
        validate_subtree_path(".state/teach/bar.json", "teach")

    def test_teach_path_rejected_in_build_mode(self) -> None:
        """validate_subtree_path('.state/teach/bar.json', 'build') raises ValueError."""
        with pytest.raises(ValueError, match=r"(?=.*build)(?=.*teach)"):
            validate_subtree_path(".state/teach/bar.json", "build")

    def test_shared_root_events_allowed_in_build(self) -> None:
        """validate_subtree_path('.state/events.sqlite', 'build') does NOT raise (shared root)."""
        validate_subtree_path(".state/events.sqlite", "build")

    def test_shared_root_modejson_allowed_in_teach(self) -> None:
        """validate_subtree_path('.state/mode.json', 'teach') does NOT raise (shared root)."""
        validate_subtree_path(".state/mode.json", "teach")

    def test_build_path_allowed_in_both_mode(self) -> None:
        """validate_subtree_path('.state/build/', 'both') does NOT raise."""
        validate_subtree_path(".state/build/", "both")

    def test_teach_path_allowed_in_both_mode(self) -> None:
        """validate_subtree_path('.state/teach/', 'both') does NOT raise."""
        validate_subtree_path(".state/teach/", "both")

    def test_path_input_allowed(self) -> None:
        """validate_subtree_path(Path('.state/build/x'), 'build') does NOT raise."""
        from pathlib import Path
        validate_subtree_path(Path(".state/build/x"), "build")

    def test_exact_dir_name_rejected(self) -> None:
        """validate_subtree_path('.state/build', 'teach') raises ValueError (exact dir name)."""
        with pytest.raises(ValueError, match=r"(?=.*teach)(?=.*build)"):
            validate_subtree_path(".state/build", "teach")


# -- Smoke and import tests ------------------------------------------------------------

class TestImports:
    """Schema module imports cleanly and exposes expected names."""

    def test_all_data_models_exist(self) -> None:
        """Confirm 29 data model classes exist in module."""
        import src.state_core.schema as mod
        data_models = [n for n in dir(mod) if n.endswith("Data") and n != "Data"]
        assert len(data_models) >= 29, f"Expected >=29 Data models, found {len(data_models)}"

    def test_all_typed_events_exist(self) -> None:
        """Confirm 29 typed event classes exist."""
        import src.state_core.schema as mod
        events = [n for n in dir(mod) if n.endswith("Event") and n != "EventEnvelope"]
        assert len(events) >= 29, f"Expected >=29 Event classes, found {len(events)}"

    def test_discriminated_union_names_exist(self) -> None:
        """All aggregate union aliases are importable."""
        from src.state_core.schema import (
            AnyStateEvent,
        )
        assert AnyStateEvent is not None

    def test_module_docstring_present(self) -> None:
        """Schema module has a docstring."""
        import src.state_core.schema as mod
        assert mod.__doc__
