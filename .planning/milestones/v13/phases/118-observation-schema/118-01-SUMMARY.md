---
phase: 118
plan: 01
subsystem: state_teach
tags: [observation, schema, pydantic, discriminator, structured-data]
requires:
  - phase-002 (Pydantic event schema — discriminated union pattern)
provides:
  - AnyObservation discriminated union (5 kinds)
  - Structured observation enforcement (extra="forbid")
  - observation_record tool data model
affects:
  - phase-119 (drill prompt token cap — may reference Observation)
  - future teach-mode observation recording/mental model
tech-stack:
  added: []
  patterns:
    - Pydantic v2 discriminated unions with Annotated[Union[...], Field(discriminator="kind")]
    - ConfigDict(extra="forbid", frozen=True) for strict data models
    - Literal discriminators for type-safe sub-model routing
key-files:
  created:
    - src/state_teach/observations.py (Observation model, 5 kinds, AnyObservation union)
    - tests/test_observations.py (24 tests covering construction, forbid, routing, freeze, serialization)
  modified: []
key-decisions:
  - "Placed Observation model in src/state_teach/ (not state_core) — observations are teach-mode specific, not shared infrastructure"
  - "Used `kind` as discriminator (not `type`) to avoid collision with event type field in state_core.schema"
  - "Five observation kinds: skill_gap, learning_style, progress, error_pattern, engagement — covers the AOL adaptive learning domain"
  - "Followed Phase 002 discriminated union pattern exactly: Annotated[Union[...], Field(discriminator=...)]"
  - "Confidence field defaults to 1.0 (certain) — agents that observe with less certainty must explicitly set lower values"
patterns-established:
  - "Application-layer Pydantic models in state_teach follow same extra=forbid + frozen=True convention as state_core event schemas"
  - "Discriminator field name should be domain-appropriate (kind for observations, type for events)"
requirements-completed:
  - MCP-T-05
metrics:
  duration: 246s
  completed: 2026-05-06
---

# Phase 118 Plan 01: Observation Schema Summary

**One-liner:** Pydantic `Observation` model with `kind` discriminator, `extra="forbid"`, enforcing structured-only observations for teach-mode adaptive learning.

## Implementation

Created `src/state_teach/observations.py` with five structured observation kinds and a discriminated union, following the Phase 002 pattern. The `kind` field acts as a discriminated union discriminator — only known `kind` values are accepted, and each routes to a type-specific sub-model with validated fields.

### Observation Kinds

| Kind | Fields | Purpose |
|------|--------|---------|
| `skill_gap` | `skill`, `evidence`, `confidence` | Missing prerequisite or skill observed |
| `learning_style` | `style`, `evidence`, `confidence` | Preferred learning modality |
| `progress` | `milestone`, `concept_id`, `mastery_level` | Mastery milestone reached |
| `error_pattern` | `pattern`, `frequency`, `context` | Recurring error pattern |
| `engagement` | `level`, `evidence`, `duration_minutes` | Attention/engagement assessment |

### Enforcements

- **`extra="forbid"`** on all sub-models — no unknown fields accepted
- **`frozen=True`** — observations are immutable once created
- **Discriminated union** — `AnyObservation` rejects unknown `kind` values at parse time
- **No freeform escape hatch** — no base `Observation` with arbitrary text field

## Test Coverage

24 tests in `tests/test_observations.py`:

- 8 valid construction tests (all 5 kinds + optional/override fields)
- 5 `extra="forbid"` rejection tests (one per kind)
- 5 discriminator routing tests (union validates correct sub-model)
- 3 freeform rejection tests (unknown kind, missing kind, empty kind)
- 1 frozen immutability test
- 2 serialization round-trip tests (individual + union)

## Deviations from Plan

None — plan executed exactly as written (TDD: RED → GREEN, no refactor needed).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `6ca4639` — `test(118-observation-schema): add failing tests for Observation model (RED)` | ✓ |
| GREEN | `c6c1468` — `feat(118-observation-schema): implement structured Observation model with kind discriminator` | ✓ |
| REFACTOR | N/A — clean implementation, no refactor needed | ✓ |

## Self-Check

- [x] `src/state_teach/observations.py` exists (124 lines)
- [x] `tests/test_observations.py` exists (332 lines)
- [x] All 24 tests pass
- [x] Import lint passes (20/20, no cross-mode violations)
- [x] RED commit `6ca4639` verified
- [x] GREEN commit `c6c1468` verified
