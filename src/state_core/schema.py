"""Pydantic event schemas for all state.* event types.

Event taxonomy (28+ events across 9 aggregates) defined per
ARCHITECTURE.md section 5.3. Every model uses extra="forbid" for strictness.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from ulid import ULID

# -- Type literals ----------------------------------------------------------------

Mode = Literal["build", "teach", "kernel"]
"""Execution mode discriminator -- every event carries exactly one."""

# Canonical mode sets — single source of truth for all modules.
# Import these rather than defining independent local copies.
PERSISTABLE_MODES: frozenset[str] = frozenset({"build", "teach", "both"})
"""Modes that can be stored in ``.state/mode.json`` (``kernel`` is internal-only)."""

RUNTIME_MODES: frozenset[str] = frozenset({"build", "teach", "kernel"})
"""Modes valid for CLI filtering and event-mode values (``both`` is config-only)."""

ALL_RECOGNISED_MODES: frozenset[str] = PERSISTABLE_MODES | RUNTIME_MODES
"""Union of persistable and runtime modes — used by header-validation middleware."""

AggregateType = Literal[
    "arc",
    "phase",
    "slice",
    "step",
    "concept",
    "drill",
    "decision",
    "auth",
    "mode",
    "provider",  # Phase 028: cost accounting
    "scheduler",
]
"""Aggregate discriminator -- maps events to their owning aggregate."""

# Arc
ARC_EVENT_TYPES = Literal[
    "state.arc.created",
    "state.arc.retired",
    "state.arc.updated",
]

# Phase
PHASE_EVENT_TYPES = Literal[
    "state.phase.planned",
    "state.phase.started",
    "state.phase.verified",
    "state.phase.completed",
]

# Slice
SLICE_EVENT_TYPES = Literal[
    "state.slice.planned",
    "state.slice.worktree_ready",
    "state.slice.shipped",
    "state.slice.reverted",
]

# Step (10 events -- richest aggregate)
STEP_EVENT_TYPES = Literal[
    "state.step.discussed",
    "state.step.planned",
    "state.step.executed",
    "state.step.verify_started",
    "state.step.verify_passed",
    "state.step.verify_failed",
    "state.step.advanced",
    "state.step.blocked",
    "state.step.snapshotted",
    "state.step.reverted",
]

# Concept
CONCEPT_EVENT_TYPES = Literal[
    "state.concept.introduced",
    "state.concept.observed",
    "state.concept.drilled",
    "state.concept.mastered",
    "state.concept.reviewed",
]

# Drill
DRILL_EVENT_TYPES = Literal[
    "state.drill.prepared",
    "state.drill.submitted",
    "state.drill.graded",
]

# Single-event aggregates
MODE_EVENT_TYPES = Literal["state.mode.activated"]
DECISION_EVENT_TYPES = Literal["state.decision.asked", "state.decision.made"]
AUTH_EVENT_TYPES = Literal[
    "state.auth.refreshed",
    "state.auth.rotated",
    "state.auth.imported",
]

# Provider
PROVIDER_EVENT_TYPES = Literal[
    "state.provider.request",
    "state.provider.response",
]

# Scheduler
SCHEDULER_EVENT_TYPES = Literal[
    "state.scheduler.priority_inversion",
    "state.scheduler.deadlock",
]

# -- Configuration models (non-event, for file I/O) -------------------------------

class ModeConfig(BaseModel):
    """Persisted mode configuration from ``.state/mode.json``.

    Only ``build``, ``teach``, and ``both`` are storable modes.
    ``kernel`` is an internal-only mode (valid in ``Mode`` literal for
    event routing but NOT persistable to ``mode.json``).

    Unlike the frozen data-payload models below, this model is NOT frozen
    — it represents a read-write configuration file.
    """

    model_config = ConfigDict(extra="forbid")

    mode: Literal["build", "teach", "both"]


def validate_mode_config(data: dict[str, object]) -> ModeConfig:
    """Validate and return a ``ModeConfig`` from raw dict data.

    Args:
        data: Raw dict to validate (e.g. ``{"mode": "build"}``).

    Returns:
        A validated ``ModeConfig`` instance.

    Raises:
        ValueError: If *data* is invalid (missing ``mode`` key,
                    unsupported mode value, or extra fields present).
    """
    try:
        return ModeConfig(**data)
    except ValidationError as exc:
        raise ValueError(f"Invalid mode config: {exc}") from exc


# -- ULID validation -------------------------------------------------------------

_ULID_PATTERN = re.compile(r"^[0-7][0-9A-Za-z]{25}$")
"""Crockford base32 ULID: 26 chars, first char in [0-7] (timestamp msb)."""


def _validate_ulid(v: str) -> str:
    """Validate that v is a well-formed ULID string."""
    if not _ULID_PATTERN.match(v):
        raise ValueError(f"Invalid ULID: {v!r}. Expected 26-char Crockford base32 (first char 0-7).")
    return v


# -- EventEnvelope (generic, serialization-oriented) ------------------------------


class EventEnvelope(BaseModel):
    """Generic event envelope -- used for serialization and generic reads.

    All fields are optional with defaults so the model can be constructed
    incrementally. For type-safe construction, use the aggregate-specific
    models (ArcEvent, PhaseEvent, etc.) defined below.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = ""
    """ULID -- validated via field_validator when non-empty."""

    seq: int = 0
    """Per-aggregate monotonic sequence number."""

    aggregate_type: AggregateType = "arc"
    """Which aggregate this event belongs to."""

    aggregate_id: str = ""
    """ID of the aggregate instance (e.g. arc-01, step-17.3)."""

    type: str = ""
    """Event type string, e.g. 'state.step.verify_passed'."""

    data: dict[str, Any] = {}
    """Event-specific payload. Use typed models for shape-safe access."""

    ts: str = ""
    """ISO 8601 timestamp of event occurrence."""

    mode: Mode = "kernel"
    """Execution mode: build, teach, or kernel (cross-mode)."""

    @field_validator("id")
    @classmethod
    def _check_ulid(cls, v: str) -> str:
        """Validate ULID format if id is non-empty."""
        if v:
            return _validate_ulid(v)
        return v


# -- Per-aggregate event data payloads -------------------------------------------
# Each model corresponds to exactly one event type's 'data' field.
# All use extra="forbid" and are frozen for hashability.


class ArcCreatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str
    goal: str


class ArcRetiredData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str


class ArcUpdatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    changed_fields: list[str]


class PhasePlannedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    phase_number: int
    title: str
    goal: str


class PhaseStartedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PhaseVerifiedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    passed: bool
    summary: str


class PhaseCompletedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    passed: bool


class SlicePlannedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    slice_number: int
    title: str
    goal: str


class SliceWorktreeReadyData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    worktree_name: str
    branch: str
    dir: str


class SliceShippedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_hash: str


class SliceRevertedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str


class StepDiscussedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    approach_summary: str


class StepPlannedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    goal: str
    verify_contract: list[dict[str, Any]]


class StepExecutedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    changes_summary: str


class StepVerifyStartedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    contract: list[dict[str, Any]]


class StepVerifyPassedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    duration_ms: int


class StepVerifyFailedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str
    details: str


class StepAdvancedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    new_state: str


class StepBlockedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str


class StepSnapshottedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_hash: str
    tier: str


class StepRevertedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_hash: str
    reason: str


class ConceptIntroducedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    concept_id: str
    name: str
    prerequisites: list[str]


class ConceptObservedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    observation: str
    classification: str


class ConceptDrilledData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    score: float
    items_attempted: int


class ConceptMasteredData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mastery_probability: float


class ConceptReviewedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mastery_delta: float


class DrillPreparedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    question_count: int


class DrillSubmittedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    answers: list[dict[str, Any]]


class DrillGradedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    score: float
    max_score: float


class ModeActivatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode_value: str


class DecisionAskedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    question: str
    options: list[dict[str, Any]]


class DecisionMadeData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    answer: str
    reason: str


class AuthRefreshedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str
    outcome: str


class AuthRotatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str
    index: int


class AuthImportedData(BaseModel):
    """Payload for state.auth.imported events emitted by Phase 021 importer.

    Contract (P0-14 / AUTH-11): NEVER carries secret bytes. The three
    fields below are the COMPLETE schema -- adding access/refresh/key/
    expires would violate the secret-leak prevention contract owned by
    this phase. Phase 020 redactor is the SECOND defense layer; this
    payload contract is the FIRST.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    provider_id: str
    """Stable provider identifier (e.g., 'anthropic', 'openrouter')."""

    source: Literal["opencode"] = "opencode"
    """Origin of the imported credential. Currently only opencode; future
    sources (gsd-pi, raw env file, ...) extend this Literal."""

    cred_kind: Literal["oauth", "api_key"]
    """Variant of the imported credential. Mirrors the discriminator on
    state_core.auth.base.Credential."""


class ProviderRequestData(BaseModel):
    """Payload for state.provider.request events (pre-call).

    Emitted by ProviderCostEmitter before each inference call.
    request_id (ULID) correlates this event to its response event.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    model: str
    """litellm model string or Anthropic model ID (e.g. 'claude-sonnet-4-6')."""
    scope_type: str
    """Scope level: 'step' | 'slice' | 'phase' | 'arc'."""
    scope_id: str
    """Scope instance ID, e.g. 'step-17.3' or 'arc-01'."""
    request_id: str
    """ULID -- correlates this request event to the matching response event."""
    prompt_tokens_estimate: int | None = None
    """Optional pre-call token estimate. None when not available."""


class ProviderResponseData(BaseModel):
    """Payload for state.provider.response events (post-call).

    Emitted by ProviderCostEmitter after each completed (or failed) inference call.
    cost_usd is None -- not 0.0 -- when the model is not in litellm's cost map.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    model: str
    scope_type: str
    scope_id: str
    request_id: str
    """Same ULID as ProviderRequestData -- the correlation key."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float | None
    """None when model is not in litellm cost map. Never 0.0 for unknown models."""
    latency_ms: int
    """Wall-clock duration of the inference call in milliseconds (time.monotonic)."""
    cache_read_tokens: int = 0
    """Cache read hits: usage._cache_read_input_tokens (litellm) or cache_read_input_tokens (Anthropic SDK)."""
    cache_creation_tokens: int = 0
    """Cache writes: usage._cache_creation_input_tokens (litellm) or cache_creation_input_tokens (Anthropic SDK)."""
    error: str | None = None
    """Exception type name, set only on failed calls (e.g. 'ProviderTransientError'). None on success."""


class SchedulerPriorityInversionData(BaseModel):
    """Payload for state.scheduler.priority_inversion events.

    Emitted when a critical-path node is blocked only on soft edges.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    node_id: str
    """The DAG node ID (e.g. 'arc-1/phase-1/slice-3/step-2') that is soft-blocked."""
    soft_edges: list[str]
    """Source node IDs of unfulfilled soft edges blocking this node."""
    critical_path: bool
    """Always True — detection only fires for critical-path nodes."""


class SchedulerDeadlockData(BaseModel):
    """Payload for state.scheduler.deadlock events.

    Emitted when all in-progress nodes are blocked on missing/descoped
    predecessors with no dispatchable work remaining.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    deadlocked_nodes: list[str]
    """Node IDs of in-progress nodes that cannot complete."""
    missing_predecessors: list[str]
    """Predecessor node IDs referenced by edges but not in the node registry."""
    descoped_predecessors: list[str]
    """Predecessor node IDs with status 'failed' or 'blocked' (descoped/unreachable)."""


# -- Typed event models (discriminated unions) ------------------------------------


class ArcCreatedEvent(EventEnvelope):
    type: Literal["state.arc.created"] = "state.arc.created"
    aggregate_type: Literal["arc"] = "arc"
    data: ArcCreatedData  # type: ignore[assignment]


class ArcRetiredEvent(EventEnvelope):
    type: Literal["state.arc.retired"] = "state.arc.retired"
    aggregate_type: Literal["arc"] = "arc"
    data: ArcRetiredData  # type: ignore[assignment]


class ArcUpdatedEvent(EventEnvelope):
    type: Literal["state.arc.updated"] = "state.arc.updated"
    aggregate_type: Literal["arc"] = "arc"
    data: ArcUpdatedData  # type: ignore[assignment]


class PhasePlannedEvent(EventEnvelope):
    type: Literal["state.phase.planned"] = "state.phase.planned"
    aggregate_type: Literal["phase"] = "phase"
    data: PhasePlannedData  # type: ignore[assignment]


class PhaseStartedEvent(EventEnvelope):
    type: Literal["state.phase.started"] = "state.phase.started"
    aggregate_type: Literal["phase"] = "phase"
    data: PhaseStartedData  # type: ignore[assignment]


class PhaseVerifiedEvent(EventEnvelope):
    type: Literal["state.phase.verified"] = "state.phase.verified"
    aggregate_type: Literal["phase"] = "phase"
    data: PhaseVerifiedData  # type: ignore[assignment]


class PhaseCompletedEvent(EventEnvelope):
    type: Literal["state.phase.completed"] = "state.phase.completed"
    aggregate_type: Literal["phase"] = "phase"
    data: PhaseCompletedData  # type: ignore[assignment]


class SlicePlannedEvent(EventEnvelope):
    type: Literal["state.slice.planned"] = "state.slice.planned"
    aggregate_type: Literal["slice"] = "slice"
    data: SlicePlannedData  # type: ignore[assignment]


class SliceWorktreeReadyEvent(EventEnvelope):
    type: Literal["state.slice.worktree_ready"] = "state.slice.worktree_ready"
    aggregate_type: Literal["slice"] = "slice"
    data: SliceWorktreeReadyData  # type: ignore[assignment]


class SliceShippedEvent(EventEnvelope):
    type: Literal["state.slice.shipped"] = "state.slice.shipped"
    aggregate_type: Literal["slice"] = "slice"
    data: SliceShippedData  # type: ignore[assignment]


class SliceRevertedEvent(EventEnvelope):
    type: Literal["state.slice.reverted"] = "state.slice.reverted"
    aggregate_type: Literal["slice"] = "slice"
    data: SliceRevertedData  # type: ignore[assignment]


class StepDiscussedEvent(EventEnvelope):
    type: Literal["state.step.discussed"] = "state.step.discussed"
    aggregate_type: Literal["step"] = "step"
    data: StepDiscussedData  # type: ignore[assignment]


class StepPlannedEvent(EventEnvelope):
    type: Literal["state.step.planned"] = "state.step.planned"
    aggregate_type: Literal["step"] = "step"
    data: StepPlannedData  # type: ignore[assignment]


class StepExecutedEvent(EventEnvelope):
    type: Literal["state.step.executed"] = "state.step.executed"
    aggregate_type: Literal["step"] = "step"
    data: StepExecutedData  # type: ignore[assignment]


class StepVerifyStartedEvent(EventEnvelope):
    type: Literal["state.step.verify_started"] = "state.step.verify_started"
    aggregate_type: Literal["step"] = "step"
    data: StepVerifyStartedData  # type: ignore[assignment]


class StepVerifyPassedEvent(EventEnvelope):
    type: Literal["state.step.verify_passed"] = "state.step.verify_passed"
    aggregate_type: Literal["step"] = "step"
    data: StepVerifyPassedData  # type: ignore[assignment]


class StepVerifyFailedEvent(EventEnvelope):
    type: Literal["state.step.verify_failed"] = "state.step.verify_failed"
    aggregate_type: Literal["step"] = "step"
    data: StepVerifyFailedData  # type: ignore[assignment]


class StepAdvancedEvent(EventEnvelope):
    type: Literal["state.step.advanced"] = "state.step.advanced"
    aggregate_type: Literal["step"] = "step"
    data: StepAdvancedData  # type: ignore[assignment]


class StepBlockedEvent(EventEnvelope):
    type: Literal["state.step.blocked"] = "state.step.blocked"
    aggregate_type: Literal["step"] = "step"
    data: StepBlockedData  # type: ignore[assignment]


class StepSnapshottedEvent(EventEnvelope):
    type: Literal["state.step.snapshotted"] = "state.step.snapshotted"
    aggregate_type: Literal["step"] = "step"
    data: StepSnapshottedData  # type: ignore[assignment]


class StepRevertedEvent(EventEnvelope):
    type: Literal["state.step.reverted"] = "state.step.reverted"
    aggregate_type: Literal["step"] = "step"
    data: StepRevertedData  # type: ignore[assignment]


class ConceptIntroducedEvent(EventEnvelope):
    type: Literal["state.concept.introduced"] = "state.concept.introduced"
    aggregate_type: Literal["concept"] = "concept"
    data: ConceptIntroducedData  # type: ignore[assignment]


class ConceptObservedEvent(EventEnvelope):
    type: Literal["state.concept.observed"] = "state.concept.observed"
    aggregate_type: Literal["concept"] = "concept"
    data: ConceptObservedData  # type: ignore[assignment]


class ConceptDrilledEvent(EventEnvelope):
    type: Literal["state.concept.drilled"] = "state.concept.drilled"
    aggregate_type: Literal["concept"] = "concept"
    data: ConceptDrilledData  # type: ignore[assignment]


class ConceptMasteredEvent(EventEnvelope):
    type: Literal["state.concept.mastered"] = "state.concept.mastered"
    aggregate_type: Literal["concept"] = "concept"
    data: ConceptMasteredData  # type: ignore[assignment]


class ConceptReviewedEvent(EventEnvelope):
    type: Literal["state.concept.reviewed"] = "state.concept.reviewed"
    aggregate_type: Literal["concept"] = "concept"
    data: ConceptReviewedData  # type: ignore[assignment]


class DrillPreparedEvent(EventEnvelope):
    type: Literal["state.drill.prepared"] = "state.drill.prepared"
    aggregate_type: Literal["drill"] = "drill"
    data: DrillPreparedData  # type: ignore[assignment]


class DrillSubmittedEvent(EventEnvelope):
    type: Literal["state.drill.submitted"] = "state.drill.submitted"
    aggregate_type: Literal["drill"] = "drill"
    data: DrillSubmittedData  # type: ignore[assignment]


class DrillGradedEvent(EventEnvelope):
    type: Literal["state.drill.graded"] = "state.drill.graded"
    aggregate_type: Literal["drill"] = "drill"
    data: DrillGradedData  # type: ignore[assignment]


class ModeActivatedEvent(EventEnvelope):
    type: Literal["state.mode.activated"] = "state.mode.activated"
    aggregate_type: Literal["mode"] = "mode"
    data: ModeActivatedData  # type: ignore[assignment]


class DecisionAskedEvent(EventEnvelope):
    type: Literal["state.decision.asked"] = "state.decision.asked"
    aggregate_type: Literal["decision"] = "decision"
    data: DecisionAskedData  # type: ignore[assignment]


class DecisionMadeEvent(EventEnvelope):
    type: Literal["state.decision.made"] = "state.decision.made"
    aggregate_type: Literal["decision"] = "decision"
    data: DecisionMadeData  # type: ignore[assignment]


class AuthRefreshedEvent(EventEnvelope):
    type: Literal["state.auth.refreshed"] = "state.auth.refreshed"
    aggregate_type: Literal["auth"] = "auth"
    data: AuthRefreshedData  # type: ignore[assignment]


class AuthRotatedEvent(EventEnvelope):
    type: Literal["state.auth.rotated"] = "state.auth.rotated"
    aggregate_type: Literal["auth"] = "auth"
    data: AuthRotatedData  # type: ignore[assignment]


class AuthImportedEvent(EventEnvelope):
    type: Literal["state.auth.imported"] = "state.auth.imported"
    aggregate_type: Literal["auth"] = "auth"
    data: AuthImportedData  # type: ignore[assignment]


class SchedulerPriorityInversionEvent(EventEnvelope):
    type: Literal["state.scheduler.priority_inversion"] = "state.scheduler.priority_inversion"
    aggregate_type: Literal["scheduler"] = "scheduler"
    data: SchedulerPriorityInversionData  # type: ignore[assignment]


class SchedulerDeadlockEvent(EventEnvelope):
    type: Literal["state.scheduler.deadlock"] = "state.scheduler.deadlock"
    aggregate_type: Literal["scheduler"] = "scheduler"
    data: SchedulerDeadlockData  # type: ignore[assignment]


class ProviderRequestEvent(EventEnvelope):
    type: Literal["state.provider.request"] = "state.provider.request"
    aggregate_type: Literal["provider"] = "provider"
    data: ProviderRequestData  # type: ignore[assignment]


class ProviderResponseEvent(EventEnvelope):
    type: Literal["state.provider.response"] = "state.provider.response"
    aggregate_type: Literal["provider"] = "provider"
    data: ProviderResponseData  # type: ignore[assignment]


# -- Aggregate discriminated unions ------------------------------------------------


ArcEvent = Annotated[
    ArcCreatedEvent | ArcRetiredEvent | ArcUpdatedEvent,
    Field(discriminator="type"),
]

PhaseEvent = Annotated[
    PhasePlannedEvent | PhaseStartedEvent | PhaseVerifiedEvent | PhaseCompletedEvent,
    Field(discriminator="type"),
]

SliceEvent = Annotated[
    SlicePlannedEvent | SliceWorktreeReadyEvent | SliceShippedEvent | SliceRevertedEvent,
    Field(discriminator="type"),
]

StepEvent = Annotated[
    StepDiscussedEvent
    | StepPlannedEvent
    | StepExecutedEvent
    | StepVerifyStartedEvent
    | StepVerifyPassedEvent
    | StepVerifyFailedEvent
    | StepAdvancedEvent
    | StepBlockedEvent
    | StepSnapshottedEvent
    | StepRevertedEvent,
    Field(discriminator="type"),
]

ConceptEvent = Annotated[
    ConceptIntroducedEvent | ConceptObservedEvent | ConceptDrilledEvent | ConceptMasteredEvent | ConceptReviewedEvent,
    Field(discriminator="type"),
]

DrillEvent = Annotated[
    DrillPreparedEvent | DrillSubmittedEvent | DrillGradedEvent,
    Field(discriminator="type"),
]

DecisionEvent = Annotated[
    DecisionAskedEvent | DecisionMadeEvent,
    Field(discriminator="type"),
]

AuthEvent = Annotated[
    AuthRefreshedEvent | AuthRotatedEvent | AuthImportedEvent,
    Field(discriminator="type"),
]

ModeEvent = ModeActivatedEvent

SchedulerEvent = Annotated[
    SchedulerPriorityInversionEvent | SchedulerDeadlockEvent,
    Field(discriminator="type"),
]

ProviderEvent = Annotated[
    ProviderRequestEvent | ProviderResponseEvent,
    Field(discriminator="type"),
]

AnyStateEvent = Annotated[
    ArcEvent | PhaseEvent | SliceEvent | StepEvent | ConceptEvent | DrillEvent | DecisionEvent | AuthEvent | ModeEvent | ProviderEvent | SchedulerEvent,
    Field(discriminator="type"),
]

# ── Event factory ──────────────────────────────────────────────────────────
# Provides ergonomic construction helpers for typed events.


def build_event[T: EventEnvelope](
    event_cls: type[T],
    aggregate_id: str,
    data: object,
    *,
    mode: Mode = "kernel",
    seq: int = 0,
    ts: str | None = None,
    id_: str | None = None,
) -> T:
    """Construct a typed event with auto-generated ULID and timestamp.

    Args:
        event_cls: The typed event class to construct (e.g. ArcCreatedEvent).
        aggregate_id: ID of the aggregate instance this event belongs to.
        data: The typed data payload (e.g. ArcCreatedData).
        mode: Execution mode (build, teach, or kernel).
        seq: Per-aggregate sequence number (default 0 -- writer assigns).
        ts: ISO 8601 timestamp. If None, defaults to a fixed epoch string
            for determinism. Callers should pass explicit timestamps
            during production use.
        id_: ULID for the event. If None, auto-generated.

    Returns:
        An instance of *event_cls*.
    """
    if id_ is None:
        id_ = str(ULID())
    if ts is None:
        ts = "2026-01-01T00:00:00Z"

    kwargs: dict[str, Any] = {
        "id": id_,
        "seq": seq,
        "aggregate_id": aggregate_id,
        "data": data,
        "ts": ts,
        "mode": mode,
    }
    return event_cls(**kwargs)
