---
phase: 002
plan: A
type: auto
autonomous: true
wave: 1
depends_on:
  - phase-001-plan-B
files_modified:
  - pyproject.toml
  - src/state_core/schema.py
requirements:
  - EVT-05
  - EVT-08
---

<objective>
Create the foundation for Phase 002's event schema system: add `python-ulid` dependency, define type literals (`Mode`, `AggregateType`, event type unions), implement the base `EventEnvelope` model with ULID field validation via Pydantic v2's `field_validator`, and establish the discriminated-union scaffolding. This plan produces the building blocks that Plan B (per-aggregate models) and Plan C (tests + factories) depend on.
</objective>

<read_first>
  - /Users/tmac/Projects/state/.planning/milestones/v1/phases/002-pydantic-event-schema-all-28/CONTEXT.md
  - /Users/tmac/Projects/state/pyproject.toml (current dependency list, build backend choice)
  - /Users/tmac/Projects/state/src/state_core/schema.py (existing EventEnvelope stub from Phase 001)
  - /Users/tmac/Projects/state/.planning/research/ARCHITECTURE.md (§5.2 event shape, §5.3 event taxonomy)
</read_first>

---

### Task 1: Add `python-ulid>=3.0` to pyproject.toml

<action>
Edit `pyproject.toml` to insert `"python-ulid>=3.0"` into the `[project] dependencies` list, maintaining alphabetical order:

The current dependencies list (lines 5-25) has 19 entries. Insert `"python-ulid>=3.0"` between `"pluggy>=1.6.0"` and `"pygit2>=1.19.2"` so the list remains alphabetical.

Desired edited section (lines 5-25 → lines 5-26 with the insertion):

```
dependencies = [
    "mcp>=1.27.0",
    "litellm>=1.80.0",
    "anthropic>=0.80.0",
    "httpx>=0.28.1",
    "pydantic>=2.13.2",
    "pydantic-settings>=2.7",
    "orjson>=3.11.8",
    "aiosqlite>=0.22.1",
    "filelock>=3.20.3",
    "pluggy>=1.6.0",
    "python-ulid>=3.0",
    "pygit2>=1.19.2",
    "google-auth>=2.35",
    "google-auth-oauthlib>=1.2",
    "google-genai>=0.9",
    "openai>=1.60",
    "cryptography>=43.0",
    "structlog>=25.1",
    "rich>=13.9",
    "typer>=0.15",
]
```

After editing, run `uv sync` to install the new dependency.
</action>

<acceptance_criteria>
  - `grep -c "python-ulid" pyproject.toml` returns at least 1.
  - `grep "python-ulid" pyproject.toml` shows `"python-ulid>=3.0"`.
  - `uv run python3 -c "import ulid; print(ulid.__version__)"` succeeds and prints a version ≥ 3.0.
  - Total dependency count before insertion was 19; after insertion is 20.
</acceptance_criteria>

---

### Task 2: Define type literals and `EventEnvelope` base model

<action>
Replace the entire content of `src/state_core/schema.py` with the following implementation. The existing file has a bare-bones `EventEnvelope` with 4 fields — replace it with the full type system.

```python
"""Pydantic event schemas for all state.* event types.

Event taxonomy (28+ events across 9 aggregates) defined per
ARCHITECTURE.md §5.3. Every model uses extra="forbid" for strictness.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

# ── Type literals ──────────────────────────────────────────────────────────

Mode = Literal["build", "teach", "kernel"]
"""Execution mode discriminator — every event carries exactly one."""

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
]
"""Aggregate discriminator — maps events to their owning aggregate."""

# ── Event type literals (one union per aggregate) ─────────────────────────

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

# Step (10 events — richest aggregate)
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
AUTH_EVENT_TYPES = Literal["state.auth.refreshed", "state.auth.rotated"]

# ── ULID validation ───────────────────────────────────────────────────────

_ULID_PATTERN = re.compile(r"^[0-7][0-9A-Za-z]{25}$")
"""Crockford base32 ULID: 26 chars, first char in [0-7] (timestamp msb)."""


def _validate_ulid(v: str) -> str:
    """Validate that *v* is a well-formed ULID string."""
    if not _ULID_PATTERN.match(v):
        raise ValueError(
            f"Invalid ULID: {v!r}. Expected 26-char Crockford base32 "
            f"(first char 0-7)."
        )
    return v


# ── EventEnvelope (generic, serialization-oriented) ──────────────────────

class EventEnvelope(BaseModel):
    """Generic event envelope — used for serialization and generic reads.

    All fields are optional with defaults so the model can be constructed
    incrementally. For type-safe construction, use the aggregate-specific
    models (ArcEvent, PhaseEvent, etc.) defined below.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = ""
    """ULID — validated via field_validator when non-empty."""

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
```

Verification steps after write:
- `uv run python3 -c "from src.state_core.schema import EventEnvelope, Mode, AggregateType; print('OK')"` succeeds.
- `uv run python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(); print(type(e.data).__name__)"` prints `dict`.
- `uv run python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(id='01ARZ3NDEKTSV4RRFFQ69G5FAV'); print(e.id)"` prints the ULID (valid).
- `uv run python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(id='invalid'); print('should have failed')"` raises `ValidationError`.
- `uv run python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(extra_field='x'); print('should have failed')"` raises `ValidationError` (extra="forbid").
</action>

<acceptance_criteria>
  - `uv run python3 -c "from src.state_core.schema import EventEnvelope"` succeeds.
  - `uv run python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(); assert e.mode == 'kernel'"` passes.
  - `uv run python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(id='01ARZ3NDEKTSV4RRFFQ69G5FAV'); assert e.id == '01ARZ3NDEKTSV4RRFFQ69G5FAV'"` passes.
  - `uv run python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(id='x'); print('no error')"` raises `ValidationError` (exit code 1).
  - `uv run python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(bad_field='x'); print('no error')"` raises `ValidationError` (exit code 1).
  - `uv run python3 -c "from src.state_core.schema import Mode; from typing import get_args; assert 'build' in get_args(Mode)"` passes.
  - `ruff check src/state_core/schema.py --no-cache` exits 0.
</acceptance_criteria>

---

<verification>
1. `uv run python3 -c "from src.state_core.schema import *; print('All exports OK')"` — all names importable.
2. `uv run python3 -c "
from src.state_core.schema import EventEnvelope
# Valid ULID
e = EventEnvelope(id='01ARZ3NDEKTSV4RRFFQ69G5FAV', type='test.event', mode='build')
assert e.mode == 'build'
assert e.aggregate_type == 'arc'
assert e.data == {}
print('Envelope construction OK')
"` — construction works with all defaults.
3. `uv run python3 -c "
from src.state_core.schema import EventEnvelope
try:
    EventEnvelope(id='BAD')
    print('ERROR: should have raised')
except Exception as e:
    print(f'ULID rejection OK: {type(e).__name__}')
"` — bad ULID correctly rejected.
4. `ruff check src/state_core/schema.py --no-cache` — clean.
5. `uv run mypy src/state_core/schema.py --strict` — no type errors.
</verification>

<must_haves>
- **`python-ulid>=3.0`** added to `pyproject.toml` dependencies
- **`Mode`**, **`AggregateType`**, and all per-aggregate event type literals defined
- **`EventEnvelope`** with 8 fields: `id`, `seq`, `aggregate_type`, `aggregate_id`, `type`, `data`, `ts`, `mode`
- **ULID validation** on `id` field (26-char Crockford base32, first char 0-7)
- **`extra="forbid"`** enforced on `EventEnvelope`
- All imports work, ruff clean, mypy clean
</must_haves>
