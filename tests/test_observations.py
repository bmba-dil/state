"""Tests for state_teach.observations — structured Observation model with kind discriminator.

Covers: all 5 observation kinds, extra="forbid", discriminator routing,
freeform rejection, optional field defaults.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

# Import the observation models (will fail until implemented — RED phase)
from src.state_teach.observations import (
    AnyObservation,
    SkillGapObservation,
    LearningStyleObservation,
    ProgressObservation,
    ErrorPatternObservation,
    EngagementObservation,
)


# ── Valid construction ─────────────────────────────────────


def test_skill_gap_valid():
    """Skill gap observation with required fields only."""
    obs = SkillGapObservation(
        kind="skill_gap",
        skill="Python typing",
        evidence="Learner wrote `x: str = 5` without error",
    )
    assert obs.kind == "skill_gap"
    assert obs.skill == "Python typing"
    assert obs.confidence == 1.0  # default


def test_skill_gap_explicit_confidence():
    """Skill gap with explicit confidence override."""
    obs = SkillGapObservation(
        kind="skill_gap",
        skill="async/await",
        evidence="Uses threading for I/O-bound work",
        confidence=0.7,
    )
    assert obs.confidence == 0.7


def test_learning_style_valid():
    """Learning style observation with required fields."""
    obs = LearningStyleObservation(
        kind="learning_style",
        style="visual",
        evidence="Asks for diagrams before code examples in 3/3 sessions",
    )
    assert obs.kind == "learning_style"
    assert obs.style == "visual"
    assert obs.confidence == 1.0


def test_progress_valid():
    """Progress milestone observation."""
    obs = ProgressObservation(
        kind="progress",
        milestone="first_compile",
        concept_id="rust-borrow-checker",
        mastery_level=0.65,
    )
    assert obs.kind == "progress"
    assert obs.milestone == "first_compile"
    assert obs.mastery_level == 0.65


def test_error_pattern_valid():
    """Error pattern observation with required fields."""
    obs = ErrorPatternObservation(
        kind="error_pattern",
        pattern="off-by-one in loops",
        context="While implementing binary search in Python",
    )
    assert obs.kind == "error_pattern"
    assert obs.frequency == 1  # default


def test_error_pattern_explicit_frequency():
    """Error pattern with explicit frequency."""
    obs = ErrorPatternObservation(
        kind="error_pattern",
        pattern="forgets .await on coroutine",
        frequency=7,
        context="Throughout async Rust module",
    )
    assert obs.frequency == 7


def test_engagement_valid():
    """Engagement observation with required fields."""
    obs = EngagementObservation(
        kind="engagement",
        level="high",
        evidence="Completed 3 drills back-to-back without prompts",
    )
    assert obs.kind == "engagement"
    assert obs.level == "high"
    assert obs.duration_minutes is None  # default


def test_engagement_with_duration():
    """Engagement observation with explicit duration."""
    obs = EngagementObservation(
        kind="engagement",
        level="medium",
        evidence="Responded to 7/10 prompts within 60s",
        duration_minutes=45,
    )
    assert obs.duration_minutes == 45


# ── extra="forbid" enforcement ──────────────────────────────


def test_extra_forbid_skill_gap():
    """Unknown fields must raise ValidationError."""
    with pytest.raises(ValidationError):
        SkillGapObservation(
            kind="skill_gap",
            skill="foo",
            evidence="bar",
            unknown_field="intruder",
        )


def test_extra_forbid_learning_style():
    """Unknown fields rejected on learning_style."""
    with pytest.raises(ValidationError):
        LearningStyleObservation(
            kind="learning_style",
            style="auditory",
            evidence="Prefers verbal explanation",
            extra_data="should not be here",
        )


def test_extra_forbid_progress():
    """Unknown fields rejected on progress."""
    with pytest.raises(ValidationError):
        ProgressObservation(
            kind="progress",
            milestone="done",
            concept_id="c1",
            mastery_level=0.5,
            notes="freeform text not allowed",
        )


def test_extra_forbid_error_pattern():
    """Unknown fields rejected on error_pattern."""
    with pytest.raises(ValidationError):
        ErrorPatternObservation(
            kind="error_pattern",
            pattern="p",
            context="c",
            severity="high",  # not a defined field
        )


def test_extra_forbid_engagement():
    """Unknown fields rejected on engagement."""
    with pytest.raises(ValidationError):
        EngagementObservation(
            kind="engagement",
            level="low",
            evidence="e",
            mood="bored",  # not a defined field
        )


# ── Discriminator routing ───────────────────────────────────


def _validate_any(data: dict) -> None:
    """Helper: validate data through the AnyObservation union."""
    adapter = TypeAdapter(AnyObservation)
    adapter.validate_python(data)


def test_discriminator_routes_skill_gap():
    """kind='skill_gap' routes to SkillGapObservation."""
    _validate_any({
        "kind": "skill_gap",
        "skill": "Python closures",
        "evidence": "Cannot explain nonlocal vs global",
    })


def test_discriminator_routes_learning_style():
    """kind='learning_style' routes to LearningStyleObservation."""
    _validate_any({
        "kind": "learning_style",
        "style": "kinesthetic",
        "evidence": "Learner takes notes by retyping examples",
    })


def test_discriminator_routes_progress():
    """kind='progress' routes to ProgressObservation."""
    _validate_any({
        "kind": "progress",
        "milestone": "completed_module",
        "concept_id": "async-python",
        "mastery_level": 0.9,
    })


def test_discriminator_routes_error_pattern():
    """kind='error_pattern' routes to ErrorPatternObservation."""
    _validate_any({
        "kind": "error_pattern",
        "pattern": "missing type annotation on public function",
        "context": "Writing library code in TypeScript",
    })


def test_discriminator_routes_engagement():
    """kind='engagement' routes to EngagementObservation."""
    _validate_any({
        "kind": "engagement",
        "level": "medium",
        "evidence": "Needs prompting after 5 min idle",
        "duration_minutes": 30,
    })


# ── Freeform rejection ─────────────────────────────────────


def test_unknown_kind_rejected():
    """Unknown kind value must be rejected by the union validator."""
    with pytest.raises(ValidationError):
        _validate_any({
            "kind": "freeform_note",
            "text": "Learner seems to struggle with recursion",
        })


def test_missing_kind_rejected():
    """Missing kind field must be rejected."""
    with pytest.raises(ValidationError):
        _validate_any({
            "skill": "something",
            "evidence": "something else",
        })


def test_kind_is_literal_string():
    """kind field values are validated as Literal strings, not arbitrary."""
    with pytest.raises(ValidationError):
        _validate_any({
            "kind": "",
            "skill": "x",
            "evidence": "y",
        })


# ── Immutability ────────────────────────────────────────────


def test_frozen_models_are_immutable():
    """All observation models should be frozen (immutable)."""
    obs = SkillGapObservation(
        kind="skill_gap",
        skill="testing",
        evidence="good test coverage",
    )
    with pytest.raises(Exception):
        obs.skill = "changed"  # type: ignore[misc]


# ── Serialization round-trip ────────────────────────────────


def test_skill_gap_round_trip():
    """Observation survives model_dump -> model_validate round-trip."""
    original = SkillGapObservation(
        kind="skill_gap",
        skill="error handling",
        evidence="Uses bare except: in 4/5 functions",
        confidence=0.85,
    )
    dumped = original.model_dump()
    reloaded = SkillGapObservation.model_validate(dumped)
    assert reloaded == original


def test_all_kinds_round_trip_via_union():
    """Every observation kind survives round-trip through AnyObservation."""
    test_cases = [
        {
            "kind": "skill_gap",
            "skill": "testing",
            "evidence": "evidence",
        },
        {
            "kind": "learning_style",
            "style": "visual",
            "evidence": "evidence",
        },
        {
            "kind": "progress",
            "milestone": "m1",
            "concept_id": "c1",
            "mastery_level": 0.5,
        },
        {
            "kind": "error_pattern",
            "pattern": "p",
            "context": "c",
        },
        {
            "kind": "engagement",
            "level": "medium",
            "evidence": "e",
        },
    ]

    adapter = TypeAdapter(AnyObservation)
    for data in test_cases:
        obs = adapter.validate_python(data)
        assert obs.kind == data["kind"]
        # round-trip through model_dump and re-validate
        reloaded = adapter.validate_python(obs.model_dump())
        assert reloaded == obs
