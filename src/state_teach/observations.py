"""Structured observation models for teach-mode adaptive learning.

Every observation has a ``kind`` discriminator and ``extra="forbid"``
— no freeform text observations are accepted. This enforces MCP-T-05.

Follows the Phase 002 discriminated union pattern:
``Annotated[Union[...], Field(discriminator="kind")]``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Observation(BaseModel):
    """Base model for structured observations — discriminator anchor.

    Sub-models set their own ``kind: Literal[...]`` to enable the
    ``AnyObservation`` discriminated union. This base class is NOT
    directly constructable with meaningful data; use a sub-model.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: str


class SkillGapObservation(Observation):
    """Observation of a missing skill or prerequisite.

    The ``confidence`` field tracks how certain the observing agent is
    about this gap. Defaults to 1.0 (certain) for direct evidence.
    """

    kind: Literal["skill_gap"] = "skill_gap"
    skill: str
    """The missing skill or concept (e.g. 'Python typing', 'async/await')."""
    evidence: str
    """Specific behavioral evidence supporting this observation."""
    confidence: float = 1.0
    """Agent confidence in this observation (0.0–1.0). Default 1.0."""


class LearningStyleObservation(Observation):
    """Observation of a preferred learning modality.

    The ``style`` field captures the modality category:
    'visual', 'auditory', 'kinesthetic', 'reading/writing'.
    """

    kind: Literal["learning_style"] = "learning_style"
    style: str
    """Preferred learning modality (visual/auditory/kinesthetic/reading-writing)."""
    evidence: str
    """Behavioral evidence supporting this style classification."""
    confidence: float = 1.0
    """Agent confidence in this observation (0.0–1.0). Default 1.0."""


class ProgressObservation(Observation):
    """Observation of a mastery milestone reached.

    ``mastery_level`` is a float in [0.0, 1.0] representing estimated
    mastery probability for the concept.
    """

    kind: Literal["progress"] = "progress"
    milestone: str
    """Milestone label (e.g. 'first_compile', 'completed_module')."""
    concept_id: str
    """Concept ID this milestone relates to."""
    mastery_level: float
    """Estimated mastery probability [0.0, 1.0]."""


class ErrorPatternObservation(Observation):
    """Observation of a recurring error pattern.

    ``frequency`` tracks how many times the pattern was observed.
    Defaults to 1 for a single occurrence.
    """

    kind: Literal["error_pattern"] = "error_pattern"
    pattern: str
    """Description of the recurring error (e.g. 'off-by-one in loops')."""
    frequency: int = 1
    """Number of times this pattern was observed. Default 1."""
    context: str
    """Context in which the error occurred (e.g. 'binary search implementation')."""


class EngagementObservation(Observation):
    """Observation of learner engagement/attention level.

    ``duration_minutes`` is optional — set when the observation covers
    a specific time window. None when engagement is assessed qualitatively.
    """

    kind: Literal["engagement"] = "engagement"
    level: str
    """Engagement level descriptor (e.g. 'high', 'medium', 'low')."""
    evidence: str
    """Behavioral evidence supporting this engagement assessment."""
    duration_minutes: int | None = None
    """Duration of observed session in minutes. None if qualitative."""


# ── Discriminated union ────────────────────────────────────
# Follows the Phase 002 pattern:
#   AnyStateEvent = Annotated[Union[...], Field(discriminator="type")]

AnyObservation = Annotated[
    SkillGapObservation
    | LearningStyleObservation
    | ProgressObservation
    | ErrorPatternObservation
    | EngagementObservation,
    Field(discriminator="kind"),
]
"""Discriminated union of all observation kinds.
Use ``TypeAdapter(AnyObservation).validate_python(data)`` to parse
raw dicts into the correct sub-model based on the ``kind`` field.
"""
