# CONTEXT: Phase 002 — Pydantic event schema for all 28+ event types

**Status:** Locked (decisions captured below are NON-NEGOTIABLE for this phase)

---

## Phase Scope

Define `EventEnvelope` and every `state.*` event with `extra="forbid"`, including aggregate discriminator, ULID IDs, per-aggregate seq, and mode filter field. All schemas live in `src/state_core/schema.py`.

## Requirements

- **EVT-05**: Pydantic event schemas with `extra="forbid"` for every event type
- **EVT-08**: Every event carries `mode: build|teach|kernel` for filtering

## Locked Decisions

### Event Modeling
- **Approach:** Discriminated union (Pydantic v2 tagged unions with `Literal` discriminators). Each aggregate group has its own typed event union.
- **EventEnvelope:** Flat `BaseModel` with all common fields + untyped `data: dict` — used for serialization/generic access
- **Typed events:** Separate per-aggregate models with typed `data` fields and `Literal` type discriminators — used for type-safe construction/consumption
- **No BaseModel inheritance across discriminator variants** — each event model is flat to keep discriminated union clean

### ULID
- **Dependency:** Add `python-ulid>=3.0` to `pyproject.toml`
- **Validation:** ULID format (26-char Crockford base32) validated via Pydantic `field_validator` on `EventEnvelope.id`
- **Generation:** Deferred to Phase 004 (writer). Schema validates ULID format but doesn't generate ULIDs.

### Mode Silos
- `state_build` and `state_teach` stay independent — only `state_core.schema` is modified here
- Events are shared across modes via `mode` discriminator field

### Plan Split (3 plans)

| Plan | Wave | Focus | Depends on |
|------|------|-------|------------|
| **A** | 1 | EventEnvelope + type literals + ULID validation + `python-ulid` dep | 001 |
| **B** | 2 | Per-aggregate event data models + discriminated unions | A |
| **C** | 3 | Tests + event factory helper | B |

### Event Taxonomy (from ARCHITECTURE.md §5.3)

All 28+ events grouped by aggregate:

| Aggregate | Events |
|-----------|--------|
| Arc | `state.arc.created`, `state.arc.retired`, `state.arc.updated` |
| Phase | `state.phase.planned`, `state.phase.started`, `state.phase.verified`, `state.phase.completed` |
| Slice | `state.slice.planned`, `state.slice.worktree_ready`, `state.slice.shipped`, `state.slice.reverted` |
| Step | `state.step.discussed`, `state.step.planned`, `state.step.executed`, `state.step.verify_started`, `state.step.verify_passed`, `state.step.verify_failed`, `state.step.advanced`, `state.step.blocked`, `state.step.snapshotted`, `state.step.reverted` |
| Concept | `state.concept.introduced`, `state.concept.observed`, `state.concept.drilled`, `state.concept.mastered`, `state.concept.reviewed` |
| Drill | `state.drill.prepared`, `state.drill.submitted`, `state.drill.graded` |
| Mode | `state.mode.activated` |
| Decision | `state.decision.asked`, `state.decision.made` |
| Auth | `state.auth.refreshed`, `state.auth.rotated` |

### Event Payload Shapes

Each event carries specific data. Research-grounded shapes (from ARCHITECTURE.md §5.3, §8.2, §11.3):

| Event Type | Data fields |
|---|---|
| `state.arc.created` | `title`, `goal` |
| `state.arc.retired` | `reason` |
| `state.arc.updated` | `changed_fields: list[str]` |
| `state.phase.planned` | `phase_number`, `title`, `goal` |
| `state.phase.started` | `timestamp_utc` |
| `state.phase.verified` | `passed: bool`, `summary` |
| `state.phase.completed` | `passed: bool` |
| `state.slice.planned` | `slice_number`, `title`, `goal` |
| `state.slice.worktree_ready` | `worktree_name`, `branch`, `dir` |
| `state.slice.shipped` | `snapshot_hash` |
| `state.slice.reverted` | `reason` |
| `state.step.discussed` | `approach_summary` |
| `state.step.planned` | `goal`, `verify_contract: list[dict]` |
| `state.step.executed` | `changes_summary` |
| `state.step.verify_started` | `contract: list[dict]` |
| `state.step.verify_passed` | `duration_ms: int` |
| `state.step.verify_failed` | `reason`, `details` |
| `state.step.advanced` | `new_state` |
| `state.step.blocked` | `reason` |
| `state.step.snapshotted` | `snapshot_hash`, `tier` |
| `state.step.reverted` | `snapshot_hash`, `reason` |
| `state.concept.introduced` | `concept_id`, `name`, `prerequisites: list[str]` |
| `state.concept.observed` | `observation`, `classification: str` |
| `state.concept.drilled` | `score: float`, `items_attempted: int` |
| `state.concept.mastered` | `mastery_probability: float` |
| `state.concept.reviewed` | `mastery_delta: float` |
| `state.drill.prepared` | `question_count: int` |
| `state.drill.submitted` | `answers: list[dict]` |
| `state.drill.graded` | `score: float`, `max_score: float` |
| `state.mode.activated` | `mode_value: str` |
| `state.decision.asked` | `question`, `options: list[dict]` |
| `state.decision.made` | `answer`, `reason` |
| `state.auth.refreshed` | `provider`, `outcome: str` |
| `state.auth.rotated` | `provider`, `index: int` |

### Code Conventions
- Every `.py` file: `from __future__ import annotations` at top
- All Pydantic models: `model_config = ConfigDict(extra="forbid")`
- Type annotations on all fields, even stubs
- ULID regex: `^[0-7][0-9A-Za-z]{25}$` (Crockford base32, first char 0-7)
- `Mode` type: `Literal["build", "teach", "kernel"]`
- No randomness or `datetime.now()` in schema code — events must be deterministic

## Research Sources Used
- `.planning/research/ARCHITECTURE.md` — §5.2 (event shape), §5.3 (event taxonomy), §8.2 (frontmatter schemas), §11.3 (SQLite schema)
- `.planning/research/STACK.md` — dependency management
- `.planning/milestones/v1/ROADMAP.md` — Phase 002 scope and requirements EVT-05, EVT-08
