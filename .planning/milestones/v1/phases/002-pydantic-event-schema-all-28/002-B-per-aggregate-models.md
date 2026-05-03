---
phase: 002
plan: B
type: auto
autonomous: true
wave: 2
depends_on:
  - phase-002-plan-A
files_modified:
  - src/state_core/schema.py
requirements:
  - EVT-05
  - EVT-08
---

<objective>
Define per-aggregate event data models and discriminated union types for all 9 aggregates (29 event data models total). Each aggregate gets typed data payload models plus a discriminated union that resolves the correct data type based on the `type` field. This enables type-safe event construction and pattern matching throughout the codebase.
</objective>

<read_first>
  - /Users/tmac/Projects/state/.planning/milestones/v1/phases/002-pydantic-event-schema-all-28/CONTEXT.md (event taxonomy, payload shapes table, ULID conventions)
  - /Users/tmac/Projects/state/src/state_core/schema.py (current state after Plan A — EventEnvelope, type literals)
  - /Users/tmac/Projects/state/.planning/research/ARCHITECTURE.md (§5.3 event taxonomy, §8.2 frontmatter shapes, §11.3 SQLite schema)
</read_first>

---

### Task 1: Define per-event data payload models for all 9 aggregates

<action>
Append the following code to `src/state_core/schema.py` (after the `EventEnvelope` class, before any trailing newline). This defines 29 typed data models — one per event type — each with `extra="forbid"`.

Insert this block after the `EventEnvelope` class definition (after line ~78 of the new file):

```python
# ── Per-aggregate event data payloads ─────────────────────────────────────
# Each model corresponds to exactly one event type's 'data' field.
# All use extra="forbid" and are frozen for hashability.

# Arc
class ArcCreatedData(BaseModel):
    """Payload for state.arc.created."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str
    goal: str


class ArcRetiredData(BaseModel):
    """Payload for state.arc.retired."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str


class ArcUpdatedData(BaseModel):
    """Payload for state.arc.updated."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    changed_fields: list[str]


# Phase
class PhasePlannedData(BaseModel):
    """Payload for state.phase.planned."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    phase_number: int
    title: str
    goal: str


class PhaseStartedData(BaseModel):
    """Payload for state.phase.started."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    pass  # no payload data beyond common envelope fields


class PhaseVerifiedData(BaseModel):
    """Payload for state.phase.verified."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    passed: bool
    summary: str


class PhaseCompletedData(BaseModel):
    """Payload for state.phase.completed."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    passed: bool


# Slice
class SlicePlannedData(BaseModel):
    """Payload for state.slice.planned."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    slice_number: int
    title: str
    goal: str


class SliceWorktreeReadyData(BaseModel):
    """Payload for state.slice.worktree_ready."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    worktree_name: str
    branch: str
    dir: str


class SliceShippedData(BaseModel):
    """Payload for state.slice.shipped."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_hash: str


class SliceRevertedData(BaseModel):
    """Payload for state.slice.reverted."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str


# Step (10 event types — richest aggregate)
class StepDiscussedData(BaseModel):
    """Payload for state.step.discussed."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    approach_summary: str


class StepPlannedData(BaseModel):
    """Payload for state.step.planned."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    goal: str
    verify_contract: list[dict[str, Any]]


class StepExecutedData(BaseModel):
    """Payload for state.step.executed."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    changes_summary: str


class StepVerifyStartedData(BaseModel):
    """Payload for state.step.verify_started."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    contract: list[dict[str, Any]]


class StepVerifyPassedData(BaseModel):
    """Payload for state.step.verify_passed."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    duration_ms: int


class StepVerifyFailedData(BaseModel):
    """Payload for state.step.verify_failed."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str
    details: str


class StepAdvancedData(BaseModel):
    """Payload for state.step.advanced."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    new_state: str


class StepBlockedData(BaseModel):
    """Payload for state.step.blocked."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str


class StepSnapshottedData(BaseModel):
    """Payload for state.step.snapshotted."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_hash: str
    tier: str


class StepRevertedData(BaseModel):
    """Payload for state.step.reverted."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_hash: str
    reason: str


# Concept
class ConceptIntroducedData(BaseModel):
    """Payload for state.concept.introduced."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    concept_id: str
    name: str
    prerequisites: list[str]


class ConceptObservedData(BaseModel):
    """Payload for state.concept.observed."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    observation: str
    classification: str


class ConceptDrilledData(BaseModel):
    """Payload for state.concept.drilled."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    score: float
    items_attempted: int


class ConceptMasteredData(BaseModel):
    """Payload for state.concept.mastered."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    mastery_probability: float


class ConceptReviewedData(BaseModel):
    """Payload for state.concept.reviewed."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    mastery_delta: float


# Drill
class DrillPreparedData(BaseModel):
    """Payload for state.drill.prepared."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    question_count: int


class DrillSubmittedData(BaseModel):
    """Payload for state.drill.submitted."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    answers: list[dict[str, Any]]


class DrillGradedData(BaseModel):
    """Payload for state.drill.graded."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    score: float
    max_score: float


# Single-event aggregates (no discriminator union needed — flat envelope is sufficient)
class ModeActivatedData(BaseModel):
    """Payload for state.mode.activated."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode_value: str


class DecisionAskedData(BaseModel):
    """Payload for state.decision.asked."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    question: str
    options: list[dict[str, Any]]


class DecisionMadeData(BaseModel):
    """Payload for state.decision.made."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    answer: str
    reason: str


class AuthRefreshedData(BaseModel):
    """Payload for state.auth.refreshed."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str
    outcome: str


class AuthRotatedData(BaseModel):
    """Payload for state.auth.rotated."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str
    index: int
```
</action>

<acceptance_criteria>
  - `uv run python3 -c "from src.state_core.schema import ArcCreatedData; d = ArcCreatedData(title='Test', goal='Learn'); print(d.title)"` prints `Test`.
  - `uv run python3 -c "from src.state_core.schema import StepVerifyPassedData; d = StepVerifyPassedData(duration_ms=150); print(d.duration_ms)"` prints `150`.
  - `uv run python3 -c "from src.state_core.schema import ConceptMasteredData; d = ConceptMasteredData(mastery_probability=0.85); print(d.mastery_probability)"` prints `0.85`.
  - `uv run python3 -c "from src.state_core.schema import PhaseStartedData; d = PhaseStartedData(); print('ok')"` succeeds (no-arg model with empty payload).
  - Every model rejects extra fields via `extra="forbid"`.
  - All 29 data model classes exist: `grep -c "class.*Data(BaseModel)" src/state_core/schema.py` returns 29.
</acceptance_criteria>

---

### Task 2: Define discriminated union types for each aggregate

<action>
Append the following block to `src/state_core/schema.py` after the data models (inserted by Task 1). This defines typed event classes per aggregate using Pydantic v2 discriminated unions with the `type` field as discriminator.

```python
# ── Typed event models (discriminated unions) ─────────────────────────────
# Each aggregate group defines a discriminated union of event models.
# The discriminator is the 'type' field (Literal).
# Use Annotated[Union[...], Field(discriminator="type")] per Pydantic v2 docs.
#
# Pattern: Each event model inherits EventEnvelope fields (flat),
# overrides 'type' as a Literal default, and 'data' as the typed payload.


# Arc events
class ArcCreatedEvent(EventEnvelope):
    type: Literal["state.arc.created"] = "state.arc.created"  # type: ignore[assignment]
    aggregate_type: Literal["arc"] = "arc"  # type: ignore[assignment]
    data: ArcCreatedData


class ArcRetiredEvent(EventEnvelope):
    type: Literal["state.arc.retired"] = "state.arc.retired"  # type: ignore[assignment]
    aggregate_type: Literal["arc"] = "arc"  # type: ignore[assignment]
    data: ArcRetiredData


class ArcUpdatedEvent(EventEnvelope):
    type: Literal["state.arc.updated"] = "state.arc.updated"  # type: ignore[assignment]
    aggregate_type: Literal["arc"] = "arc"  # type: ignore[assignment]
    data: ArcUpdatedData


# Phase events
class PhasePlannedEvent(EventEnvelope):
    type: Literal["state.phase.planned"] = "state.phase.planned"  # type: ignore[assignment]
    aggregate_type: Literal["phase"] = "phase"  # type: ignore[assignment]
    data: PhasePlannedData


class PhaseStartedEvent(EventEnvelope):
    type: Literal["state.phase.started"] = "state.phase.started"  # type: ignore[assignment]
    aggregate_type: Literal["phase"] = "phase"  # type: ignore[assignment]
    data: PhaseStartedData


class PhaseVerifiedEvent(EventEnvelope):
    type: Literal["state.phase.verified"] = "state.phase.verified"  # type: ignore[assignment]
    aggregate_type: Literal["phase"] = "phase"  # type: ignore[assignment]
    data: PhaseVerifiedData


class PhaseCompletedEvent(EventEnvelope):
    type: Literal["state.phase.completed"] = "state.phase.completed"  # type: ignore[assignment]
    aggregate_type: Literal["phase"] = "phase"  # type: ignore[assignment]
    data: PhaseCompletedData


# Slice events
class SlicePlannedEvent(EventEnvelope):
    type: Literal["state.slice.planned"] = "state.slice.planned"  # type: ignore[assignment]
    aggregate_type: Literal["slice"] = "slice"  # type: ignore[assignment]
    data: SlicePlannedData


class SliceWorktreeReadyEvent(EventEnvelope):
    type: Literal["state.slice.worktree_ready"] = "state.slice.worktree_ready"  # type: ignore[assignment]
    aggregate_type: Literal["slice"] = "slice"  # type: ignore[assignment]
    data: SliceWorktreeReadyData


class SliceShippedEvent(EventEnvelope):
    type: Literal["state.slice.shipped"] = "state.slice.shipped"  # type: ignore[assignment]
    aggregate_type: Literal["slice"] = "slice"  # type: ignore[assignment]
    data: SliceShippedData


class SliceRevertedEvent(EventEnvelope):
    type: Literal["state.slice.reverted"] = "state.slice.reverted"  # type: ignore[assignment]
    aggregate_type: Literal["slice"] = "slice"  # type: ignore[assignment]
    data: SliceRevertedData


# Step events (10 event types)
class StepDiscussedEvent(EventEnvelope):
    type: Literal["state.step.discussed"] = "state.step.discussed"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepDiscussedData


class StepPlannedEvent(EventEnvelope):
    type: Literal["state.step.planned"] = "state.step.planned"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepPlannedData


class StepExecutedEvent(EventEnvelope):
    type: Literal["state.step.executed"] = "state.step.executed"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepExecutedData


class StepVerifyStartedEvent(EventEnvelope):
    type: Literal["state.step.verify_started"] = "state.step.verify_started"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepVerifyStartedData


class StepVerifyPassedEvent(EventEnvelope):
    type: Literal["state.step.verify_passed"] = "state.step.verify_passed"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepVerifyPassedData


class StepVerifyFailedEvent(EventEnvelope):
    type: Literal["state.step.verify_failed"] = "state.step.verify_failed"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepVerifyFailedData


class StepAdvancedEvent(EventEnvelope):
    type: Literal["state.step.advanced"] = "state.step.advanced"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepAdvancedData


class StepBlockedEvent(EventEnvelope):
    type: Literal["state.step.blocked"] = "state.step.blocked"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepBlockedData


class StepSnapshottedEvent(EventEnvelope):
    type: Literal["state.step.snapshotted"] = "state.step.snapshotted"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepSnapshottedData


class StepRevertedEvent(EventEnvelope):
    type: Literal["state.step.reverted"] = "state.step.reverted"  # type: ignore[assignment]
    aggregate_type: Literal["step"] = "step"  # type: ignore[assignment]
    data: StepRevertedData


# Concept events
class ConceptIntroducedEvent(EventEnvelope):
    type: Literal["state.concept.introduced"] = "state.concept.introduced"  # type: ignore[assignment]
    aggregate_type: Literal["concept"] = "concept"  # type: ignore[assignment]
    data: ConceptIntroducedData


class ConceptObservedEvent(EventEnvelope):
    type: Literal["state.concept.observed"] = "state.concept.observed"  # type: ignore[assignment]
    aggregate_type: Literal["concept"] = "concept"  # type: ignore[assignment]
    data: ConceptObservedData


class ConceptDrilledEvent(EventEnvelope):
    type: Literal["state.concept.drilled"] = "state.concept.drilled"  # type: ignore[assignment]
    aggregate_type: Literal["concept"] = "concept"  # type: ignore[assignment]
    data: ConceptDrilledData


class ConceptMasteredEvent(EventEnvelope):
    type: Literal["state.concept.mastered"] = "state.concept.mastered"  # type: ignore[assignment]
    aggregate_type: Literal["concept"] = "concept"  # type: ignore[assignment]
    data: ConceptMasteredData


class ConceptReviewedEvent(EventEnvelope):
    type: Literal["state.concept.reviewed"] = "state.concept.reviewed"  # type: ignore[assignment]
    aggregate_type: Literal["concept"] = "concept"  # type: ignore[assignment]
    data: ConceptReviewedData


# Drill events
class DrillPreparedEvent(EventEnvelope):
    type: Literal["state.drill.prepared"] = "state.drill.prepared"  # type: ignore[assignment]
    aggregate_type: Literal["drill"] = "drill"  # type: ignore[assignment]
    data: DrillPreparedData


class DrillSubmittedEvent(EventEnvelope):
    type: Literal["state.drill.submitted"] = "state.drill.submitted"  # type: ignore[assignment]
    aggregate_type: Literal["drill"] = "drill"  # type: ignore[assignment]
    data: DrillSubmittedData


class DrillGradedEvent(EventEnvelope):
    type: Literal["state.drill.graded"] = "state.drill.graded"  # type: ignore[assignment]
    aggregate_type: Literal["drill"] = "drill"  # type: ignore[assignment]
    data: DrillGradedData


# Mode event (single)
class ModeActivatedEvent(EventEnvelope):
    type: Literal["state.mode.activated"] = "state.mode.activated"  # type: ignore[assignment]
    aggregate_type: Literal["mode"] = "mode"  # type: ignore[assignment]
    data: ModeActivatedData


# Decision events
class DecisionAskedEvent(EventEnvelope):
    type: Literal["state.decision.asked"] = "state.decision.asked"  # type: ignore[assignment]
    aggregate_type: Literal["decision"] = "decision"  # type: ignore[assignment]
    data: DecisionAskedData


class DecisionMadeEvent(EventEnvelope):
    type: Literal["state.decision.made"] = "state.decision.made"  # type: ignore[assignment]
    aggregate_type: Literal["decision"] = "decision"  # type: ignore[assignment]
    data: DecisionMadeData


# Auth events
class AuthRefreshedEvent(EventEnvelope):
    type: Literal["state.auth.refreshed"] = "state.auth.refreshed"  # type: ignore[assignment]
    aggregate_type: Literal["auth"] = "auth"  # type: ignore[assignment]
    data: AuthRefreshedData


class AuthRotatedEvent(EventEnvelope):
    type: Literal["state.auth.rotated"] = "state.auth.rotated"  # type: ignore[assignment]
    aggregate_type: Literal["auth"] = "auth"  # type: ignore[assignment]
    data: AuthRotatedData
```
</action>

<acceptance_criteria>
  - `uv run python3 -c "from src.state_core.schema import ArcCreatedEvent, ArcCreatedData; e = ArcCreatedEvent(id='01ARZ3NDEKTSV4RRFFQ69G5FAV', aggregate_id='arc-01', type='state.arc.created', data=ArcCreatedData(title='Test', goal='Learn'), ts='2026-04-23T00:00:00Z', mode='build'); print(e.type, e.data.title)"` prints `state.arc.created Test`.
  - `uv run python3 -c "from src.state_core.schema import StepVerifyPassedEvent, StepVerifyPassedData; e = StepVerifyPassedEvent(id='01ARZ3NDEKTSV4RRFFQ69G5FAV', aggregate_id='step-17.3', data=StepVerifyPassedData(duration_ms=150), ts='2026-04-23T00:00:00Z', mode='build'); print(e.data.duration_ms)"` prints `150`.
  - `grep -c "class.*Event(EventEnvelope)" src/state_core/schema.py` returns at least 28 (accounting for all event types; some single-event aggregates need 1 each).
  - `ruff check src/state_core/schema.py --no-cache` exits 0.
</acceptance_criteria>

---

### Task 3: Define top-level `StateEvent` discriminated union and aggregate union aliases

<action>
Append the following block at the very end of `src/state_core/schema.py`. This creates the aggregate-level discriminated unions (`ArcEvent`, `PhaseEvent`, etc.) and a top-level `StateEvent` union that covers all typed events.

```python
# ── Aggregate discriminated unions ─────────────────────────────────────────
# Each union uses the 'type' field as discriminator (Pydantic v2).
# These can be used for type-safe pattern matching on event streams.

from typing import Annotated, Union

from pydantic import Field

ArcEvent = Annotated[
    Union[ArcCreatedEvent, ArcRetiredEvent, ArcUpdatedEvent],
    Field(discriminator="type"),
]
"""Discriminated union of all Arc events."""

PhaseEvent = Annotated[
    Union[PhasePlannedEvent, PhaseStartedEvent, PhaseVerifiedEvent, PhaseCompletedEvent],
    Field(discriminator="type"),
]
"""Discriminated union of all Phase events."""

SliceEvent = Annotated[
    Union[SlicePlannedEvent, SliceWorktreeReadyEvent, SliceShippedEvent, SliceRevertedEvent],
    Field(discriminator="type"),
]
"""Discriminated union of all Slice events."""

StepEvent = Annotated[
    Union[
        StepDiscussedEvent,
        StepPlannedEvent,
        StepExecutedEvent,
        StepVerifyStartedEvent,
        StepVerifyPassedEvent,
        StepVerifyFailedEvent,
        StepAdvancedEvent,
        StepBlockedEvent,
        StepSnapshottedEvent,
        StepRevertedEvent,
    ],
    Field(discriminator="type"),
]
"""Discriminated union of all Step events (10 variants)."""

ConceptEvent = Annotated[
    Union[
        ConceptIntroducedEvent,
        ConceptObservedEvent,
        ConceptDrilledEvent,
        ConceptMasteredEvent,
        ConceptReviewedEvent,
    ],
    Field(discriminator="type"),
]
"""Discriminated union of all Concept events."""

DrillEvent = Annotated[
    Union[DrillPreparedEvent, DrillSubmittedEvent, DrillGradedEvent],
    Field(discriminator="type"),
]
"""Discriminated union of all Drill events."""

DecisionEvent = Annotated[
    Union[DecisionAskedEvent, DecisionMadeEvent],
    Field(discriminator="type"),
]
"""Discriminated union of all Decision events."""

AuthEvent = Annotated[
    Union[AuthRefreshedEvent, AuthRotatedEvent],
    Field(discriminator="type"),
]
"""Discriminated union of all Auth events."""

ModeEvent = ModeActivatedEvent
"""Single-event aggregate — no union needed, direct type alias."""

# ── Top-level event union ──────────────────────────────────────────────────

# Union of all aggregate-unioned event types plus the generic EventEnvelope.
# Use this for event stream processing.
AnyStateEvent = Annotated[
    Union[
        ArcEvent,
        PhaseEvent,
        SliceEvent,
        StepEvent,
        ConceptEvent,
        DrillEvent,
        DecisionEvent,
        AuthEvent,
        ModeEvent,
    ],
    Field(discriminator="type"),
]
"""Top-level discriminated union of every typed state event."""
```

Note: the `import` statements for `Annotated`, `Union`, and `Field` should be at the top of the module. If they're already imported from Pydantic, add `Annotated` and `Union` to the imports. Update the import block at the top of `schema.py` to include them:

Replace:
```python
from typing import Any, Literal
```
With:
```python
from typing import Annotated, Any, Literal, Union
```
</action>

<acceptance_criteria>
  - `uv run python3 -c "from src.state_core.schema import ArcEvent, PhaseEvent, StepEvent, ConceptEvent, DrillEvent, AuthEvent, DecisionEvent, ModeEvent, AnyStateEvent; print('All unions OK')"` succeeds.
  - `uv run python3 -c "
from src.state_core.schema import AnyStateEvent, ArcCreatedEvent, ArcCreatedData
import json
# Simulate parsing a JSON event
from pydantic import TypeAdapter
ta = TypeAdapter(AnyStateEvent)
raw = {'id': '01ARZ3NDEKTSV4RRFFQ69G5FAV', 'seq': 1, 'aggregate_type': 'arc', 'aggregate_id': 'arc-01', 'type': 'state.arc.created', 'data': {'title': 'T', 'goal': 'G'}, 'ts': '2026-04-23T00:00:00Z', 'mode': 'build'}
result = ta.validate_python(raw)
print(type(result).__name__, result.type)
"` prints `ArcCreatedEvent state.arc.created` (Pydantic discriminator resolves the correct subclass).
  - `ruff check src/state_core/schema.py --no-cache` exits 0.
</acceptance_criteria>

---

<verification>
1. **All data models importable:** `uv run python3 -c "from src.state_core.schema import *; print('All OK')"`
2. **Data model count:** `grep 'class.*Data(BaseModel)' src/state_core/schema.py | wc -l` = 29.
3. **Typed event class count:** `grep 'class.*Event(EventEnvelope)' src/state_core/schema.py | wc -l` = 29 (one per data model — PhaseStarted has an empty data model).
4. **Discriminated union resolution:** Create a JSON dict with type "state.arc.created" and validate it with `TypeAdapter(AnyStateEvent)` — result should be `ArcCreatedEvent`.
5. **Type safety:** `uv run python3 -c "
from src.state_core.schema import ArcCreatedEvent, ArcCreatedData
try:
    ArcCreatedEvent(id='01ARZ3NDEKTSV4RRFFQ69G5FAV', aggregate_id='arc-01', data=ArcCreatedData(title='T', goal='G'), ts='now', mode='build', type='state.arc.retired')
    print('ERROR: wrong type accepted')
except Exception as e:
    print(f'Type safety OK: {type(e).__name__}')
"`
6. **ruff clean, mypy clean.**
</verification>

<must_haves>
- **29 per-event data models** (one per event type, all with `extra="forbid"` and `frozen=True`)
- **29 typed event classes** inheriting from `EventEnvelope` with overridden `type`, `aggregate_type`, and `data` fields
- **Per-aggregate discriminated unions** (`ArcEvent`, `PhaseEvent`, `SliceEvent`, `StepEvent`, `ConceptEvent`, `DrillEvent`, `DecisionEvent`, `AuthEvent`, `ModeEvent`)
- **Top-level `AnyStateEvent`** union — single discriminated union covering all typed events
- **Discriminator resolution** works via Pydantic's `TypeAdapter`
- All imports clean, ruff clean, mypy clean
</must_haves>
