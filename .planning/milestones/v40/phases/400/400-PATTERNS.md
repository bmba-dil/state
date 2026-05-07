# Phase 400: Tier Definitions & State Machines - Pattern Map

**Mapped:** 2026-05-06
**Files analyzed:** 9 (specification documents)
**Analogs found:** 9 / 9 (all matched to codebase patterns)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `specs/TIER-ARC.md` | tier-spec | static-definition | `src/state_core/schema.py` ArcCreatedData (lines 287-291) + `ARCHITECTURE.md` §1.1 (lines 45-73) | exact |
| `specs/TIER-STAGE.md` | tier-spec | static-definition | `src/state_core/schema.py` PhasePlannedData (lines 303-307) + `ARCHITECTURE.md` §1.2 (lines 75-105) | exact |
| `specs/TIER-SLICE.md` | tier-spec | static-definition | `src/state_core/schema.py` SlicePlannedData (lines 325-329) + `ARCHITECTURE.md` §1.3 (lines 107-146) | exact |
| `specs/TIER-STEP.md` | tier-spec | static-definition | `src/state_build/kernel.py` StepMachine (lines 1-15) + `ARCHITECTURE.md` §1.4 (lines 148-206) | exact |
| `specs/FSM-TABLES.md` | transition-table | static-definition | `ARCHITECTURE.md` §1 guard descriptions (lines 68-71, 100-103, 139-144, 197-204) + RESEARCH.md table format (lines 334-343) | role-match |
| `specs/EVENT-TAXONOMY.md` | event-catalog | static-definition | `src/state_core/schema.py` event type Literals (lines 65-137) + data payload models (lines 287-585) | exact |
| `specs/COMPOSITE-CASCADE.md` | cascade-spec | static-definition | `ARCHITECTURE.md` §2.2 composite event flow (lines 221-246) + `src/state_core/projector.py` handler registration (lines 28-45) | role-match |
| `specs/FRONTMATTER-SCHEMAS.md` | schema-design | static-definition | `src/state_core/schema.py` event data payload models (lines 287-585) + RESEARCH.md pydantic example (lines 469-492) | exact |
| `specs/DESC-SEMANTICS.md` | semantics-spec | static-definition | `src/state_core/scheduler.py` Edge model (lines 15-33) + `src/state_core/projector.py` blocked handler (lines 187-199) | partial-match |

## Pattern Assignments

### `specs/TIER-ARC.md` (tier-specification, static-definition)

**Analog:** `src/state_core/schema.py` Arc aggregate definitions (lines 45-70, 287-291) + `ARCHITECTURE.md` §1.1 (lines 45-73)

**Pydantic schema pattern** (schema.py lines 287-291):
```python
# Source: src/state_core/schema.py:287-291 — existing ArcCreatedData
# Pattern: ConfigDict(extra="forbid", frozen=True) — apply to all frontmatter schemas
class ArcCreatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str
    goal: str
```

**Aggregate type & event type pattern** (schema.py lines 50-70):
```python
# Source: src/state_core/schema.py:50-70
# Pattern: AggregateType Literal includes all tier discriminators
AggregateType = Literal[
    "arc",
    "phase",   # NOTE: will become "stage" per D-01 rename (v41+ code migration)
    "slice",
    "step",
    ...
]

# Arc event types (3 defined)
ARC_EVENT_TYPES = Literal[
    "state.arc.created",
    "state.arc.retired",
    "state.arc.updated",
]
```

**Specification document structure** — follow ARCHITECTURE.md §1 pattern (lines 45-73):
```markdown
# Source: ARCHITECTURE.md:45-73 — §1.1 Arc State Machine
# Pattern: Role → State Machine diagram → Events list → Transition guards → Aggregate ID

## Role in Hierarchy
[One-paragraph definition of Arc's role in the four-tier system]

## State Machine
[ASCII/Mermaid diagram showing all states and transitions]

## Events
- `state.arc.created` → arc aggregate enters `planned`
- `state.arc.retired` → arc transitions to `shipped`
- `state.arc.updated` → frontmatter/scope change

## Transition Guards
- `planned → in_progress`: at least one child Stage is `planned`
- `in_progress → auditing`: ALL child Stages are `shipped`
- `auditing → shipped`: manual ship action, ARC-SUMMARY.md produced
- `* → abandoned`: explicit abandon command

## Owned Artifacts
| Artifact | Purpose | Schema Owner |
|----------|---------|-------------|
| CRIT.md  | Must-have criteria | Agent |
| MAP.md   | Arc roadmap | Agent |
| ARC.md   | Arc definition + frontmatter | Agent |
| STATE.md | State projection | Projector |

## Frontmatter Fields
[Table with id, title, status, goal, success_criteria, stage_ids, depends_on...]
```

**Arc state budget:** ≤4 forward states (planned, in_progress, auditing, shipped — per D-17/D-18; abandoned is exit state, excluded from budget count). FSM-06 says Arc max 3 — resolve during planning per RESEARCH.md Open Question Q1.

---

### `specs/TIER-STAGE.md` (tier-specification, static-definition)

**Analog:** `src/state_core/schema.py` Phase aggregate definitions (lines 72-78, 303-322) + `ARCHITECTURE.md` §1.2 (lines 75-105)

**CRITICAL: Phase→Stage Rename (D-01):** This spec document uses "Stage" terminology. The existing codebase uses `state.phase.*` event type strings and `PhasePlannedData` class names. The spec documents use `state.stage.*` as forward-looking design contract. A migration table maps old→new names. Actual code migration is v41+.

**Pydantic schema pattern** (schema.py lines 303-307):
```python
# Source: src/state_core/schema.py:303-307 — existing PhasePlannedData
# Pattern: ConfigDict(extra="forbid", frozen=True) for event data payloads
# RENAME TARGET: PhasePlannedData → StagePlannedData (v41+)
class PhasePlannedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    phase_number: int       # → stage_number (post-rename)
    title: str
    goal: str
```

**Event type pattern** (schema.py lines 72-78):
```python
# Source: src/state_core/schema.py:72-78
# Pattern: 4 event types for Phase (→Stage post-rename)
PHASE_EVENT_TYPES = Literal[
    "state.phase.planned",      # → state.stage.planned (post-rename)
    "state.phase.started",      # → state.stage.started
    "state.phase.verified",     # → state.stage.verified
    "state.phase.completed",    # → state.stage.completed
]
```

**Stage states per D-17:** `planned → in_progress → verified → shipped | abandoned` (≤4 forward states; abandoned is exit state).

**Key integration:** The projector currently has `phase_id` fields in Slice cache rows (projector.py line 242). After rename, these become `stage_id`. The spec must note this migration path.

---

### `specs/TIER-SLICE.md` (tier-specification, static-definition)

**Analog:** `src/state_core/schema.py` Slice event types (lines 80-86) + `ARCHITECTURE.md` §1.3 (lines 107-146)

**Event type pattern** (schema.py lines 80-86):
```python
# Source: src/state_core/schema.py:80-86 — existing Slice event types (4 total)
SLICE_EVENT_TYPES = Literal[
    "state.slice.planned",
    "state.slice.worktree_ready",
    "state.slice.shipped",
    "state.slice.reverted",
]
```

**Projector slice handler pattern** (projector.py lines 234-296):
```python
# Source: src/state_core/projector.py:235-248
# Pattern: @_register_handler decorator, handler fn returns cache row dict
# Each handler maps event_type → state transition + frontmatter merge
@_register_handler("state.slice.planned")
def _handle_slice_planned(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": current.get("id", "") if current else "",
        "phase_id": data.get("phase_id", ...),  # → stage_id post-rename
        "state": "planned",                    # state from event
        "worktree_dir": current.get("worktree_dir") if current else None,
        "worktree_branch": current.get("worktree_branch") if current else None,
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }
```

**Slice cache table columns** (projector.py lines 407-410):
```python
# Source: src/state_core/projector.py:407-410
_SLICE_COLUMNS: tuple[str, ...] = (
    "id", "phase_id", "state", "worktree_dir", "worktree_branch",
    "frontmatter", "updated_at",
)
# NOTE: phase_id → stage_id post-rename (v41+)
```

**Slice states per D-17:** `planned → worktree_ready → in_progress → shipped | reverted | blocked` (≤4 forward states). Blocked is entered via abandon-cascade (D-13), not a forward-progression state. Reverted is a terminal alternative.

**Slice is the terminal container (D-04):** Steps are flat FILES within the Slice folder, not subdirectories. The Slice folder holds ALL step files plus DESIGN.md, RESEARCH.md, VERIFICATION.md, SUMMARY.md.

---

### `specs/TIER-STEP.md` (tier-specification, static-definition)

**Analog:** `src/state_build/kernel.py` StepMachine skeleton (lines 1-15) + `src/state_core/schema.py` Step event types (lines 88-100)

**StepMachine skeleton** (kernel.py lines 1-15):
```python
# Source: src/state_build/kernel.py:1-15 — existing StepMachine skeleton
# Pattern: Literal state type + class with on_event method signature
StepState = Literal[
    "idle", "discussing", "planning", "executing",
    "verifying", "done", "blocked", "abandoned"
]

class StepMachine:
    """Finite state machine for a single Step's lifecycle."""
    state: StepState = "idle"

    async def on_event(self, event_type: str, data: dict) -> None: ...
```

**Step event types — RENAMED per D-03** (schema.py lines 88-100):
```python
# Source: src/state_core/schema.py:88-100 — existing Step event types
# D-03 renames: "discussed" → "designed", "executed" → "run"
STEP_EVENT_TYPES = Literal[
    "state.step.discussed",      # → state.step.designed (post-rename)
    "state.step.planned",        # unchanged
    "state.step.executed",       # → state.step.ran (post-rename)
    "state.step.verify_started",  # → state.step.verify_started
    "state.step.verify_passed",  # unchanged
    "state.step.verify_failed",  # unchanged
    "state.step.advanced",       # composite state advancement
    "state.step.blocked",
    "state.step.snapshotted",
    "state.step.reverted",
]
```

**D-03 rename mapping for Step events (in-spec design contract):**
| Existing event type | Post-rename event type | Reason |
|--------------------|------------------------|--------|
| `state.step.discussed` | `state.step.designed` | "discuss" → "design" |
| `state.step.executed` | `state.step.ran` | "execute" → "run" |
| `state.step.verify_started` | `state.step.verify_started` | unchanged |
| `state.step.verify_passed` | `state.step.verify_passed` | unchanged |
| `state.step.verify_failed` | `state.step.verify_failed` | unchanged |

**Step FSM rename:** The StepMachine states (kernel.py line 7) `discussing→designing`, `executing→running` per D-03. New StepState Literal post-rename:
```python
StepState = Literal[
    "idle", "designing", "planning", "running",
    "verifying", "done", "blocked", "abandoned"
]
```

**Step projector handler pattern — rename target** (projector.py lines 82-94):
```python
# Source: src/state_core/projector.py:82-94
# RENAME TARGET: state → "designing" (not "discussing")
@_register_handler("state.step.discussed")
def _handle_step_discussed(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": data.get("slice_id", ...),
        "state": "discussing",  # → "designing" post-rename
        "title": data.get("approach_summary", ...),
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }
```

**Step states per D-17:** `idle → designing → planning → running → verifying → done | blocked | abandoned` (≤8 total states including blocked/abandoned exit states).

**Steps are NOT scheduler-dispatched (D-11):** Steps run within one agent session. The agent manages work, delegates to subagents, and moves between steps serially.

---

### `specs/FSM-TABLES.md` (transition-table, static-definition)

**Analog:** ARCHITECTURE.md §1 transition guard descriptions + RESEARCH.md table format

**ARCHITECTURE.md guard pattern** (ARCHITECTURE.md lines 68-71 for Arc):
```markdown
# Source: ARCHITECTURE.md:68-71
**Transition guards:**
- `planned → in_progress`: at least one child Stage is `planned`
- `in_progress → auditing`: ALL child Stages are `shipped`
- `auditing → shipped`: manual ship action, ARC-SUMMARY.md produced
- `* → abandoned`: explicit abandon command
```

**RESEARCH.md tabular format** (RESEARCH.md lines 334-343):
```markdown
# Source: RESEARCH.md:334-343 — State Transition Table pattern
## Stage State Transition Table

| From | To | Event Trigger | Guard Condition | Budget Check |
|------|----|---------------|-----------------|-------------|
| planned | in_progress | state.stage.started | ≥1 child Slice is worktree_ready | ≤4 states |
| in_progress | verified | state.stage.slices_verified | ALL child Slices are shipped | ≤4 states |
| verified | shipped | state.stage.completed | stage-completed command with passed: true | ≤4 states |
| * | abandoned | state.stage.abandoned | Explicit abandon command | — |
```

**Budget enforcement pattern** (per D-17 + FSM-06):
| Tier | Forward States | Exit States | Budget |
|------|---------------|-------------|--------|
| Arc | 4 (planned, in_progress, auditing, shipped) | 1 (abandoned) | ≤4 forward |
| Stage | 4 (planned, in_progress, verified, shipped) | 1 (abandoned) | ≤4 |
| Slice | 4 (planned, worktree_ready, in_progress, shipped) | 2 (reverted, blocked) | ≤4 forward |
| Step | 6 (idle, designing, planning, running, verifying, done) | 2 (blocked, abandoned) | ≤8 total |

**D-17/D-19 note:** Composite states (e.g., Stage "in_progress" computed from child Slice activity) are projector-computed, NOT explicit machine states. The FSM tables document only discrete machine states. The composite state computation is documented in COMPOSITE-CASCADE.md.

---

### `specs/EVENT-TAXONOMY.md` (event-catalog, static-definition)

**Analog:** `src/state_core/schema.py` event type Literals (lines 65-137) + event data payload models (lines 287-585)

**Canonical event type structure** (schema.py lines 65-70, 73-78, 81-86, 89-100):
```python
# Source: src/state_core/schema.py:65-137 — existing event type taxonomy
# Pattern: per-aggregate Literal unions, grouped by aggregate

# Arc (3 events)
ARC_EVENT_TYPES = Literal[
    "state.arc.created",
    "state.arc.retired",
    "state.arc.updated",
]

# Phase (4 events → Stage post-rename)
PHASE_EVENT_TYPES = Literal[
    "state.phase.planned",
    "state.phase.started",
    "state.phase.verified",
    "state.phase.completed",
]

# Slice (4 events)
SLICE_EVENT_TYPES = Literal[
    "state.slice.planned",
    "state.slice.worktree_ready",
    "state.slice.shipped",
    "state.slice.reverted",
]

# Step (10 events)
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
```

**Event data payload pattern** (schema.py lines 287-585):
```python
# Source: src/state_core/schema.py:287-291 — all 34+ models follow this
# Pattern: BaseModel, ConfigDict(extra="forbid", frozen=True)
# Every model = exactly one event type's 'data' field
class ArcCreatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str
    goal: str
```

**D-01 Rename: Phase→Stage event type mapping (design contract):**
| Existing Event (schema.py) | Post-Rename Event (spec) | Aggregate ID |
|---|---|---|
| `state.phase.planned` | `state.stage.planned` | stage-{n} not phase-{n} |
| `state.phase.started` | `state.stage.started` | stage-{n} |
| `state.phase.verified` | `state.stage.verified` | stage-{n} |
| `state.phase.completed` | `state.stage.completed` | stage-{n} |
| PhasePlannedData | StagePlannedData | `stage_number` not `phase_number` |
| PhaseStartedData | StageStartedData | unchanged fields |
| PhaseVerifiedData | StageVerifiedData | unchanged fields |
| PhaseCompletedData | StageCompletedData | unchanged fields |

**Build-mode event prefixes** (schema.py lines 45-48):
```python
# Source: src/state_core/schema.py:45-48
# Event taxonomy must respect mode isolation
BUILD_ONLY_EVENT_PREFIXES: frozenset[str] = frozenset(
    {"state.arc.", "state.phase.", "state.slice.", "state.step."}
)
# Post-rename: state.phase. → state.stage. (v41+ migration)
```

**Taxonomy document structure** (derived from schema.py organization):
```markdown
# Per-aggregate event listing with trigger conditions
## Arc Events (3 existing)
| Event Type | Trigger | State Transition | Data Fields |
|---|---|---|---|
| state.arc.created | /state-new arc | None → planned | title, goal |
| state.arc.retired | /state-ship-arc | auditing → shipped | reason |
```

---

### `specs/COMPOSITE-CASCADE.md` (cascade-spec, static-definition)

**Analog:** `ARCHITECTURE.md` §2.2 composite event flow (lines 221-246) + `src/state_core/projector.py` handler registration (lines 28-45)

**ARCHITECTURE.md composite cascade description** (ARCHITECTURE.md lines 221-246):
```python
# Source: ARCHITECTURE.md:225-238 — pseudocode for composite event emission
async def on_step_advanced(event: StepEvent):
    """Check if all Steps in the parent Slice are done."""
    slice_id = extract_slice_id(event.aggregate_id)
    steps = await store.read_stream(slice_id + "/step-")
    all_done = all_step_states_are_done(steps)
    if all_done:
        await store.append(
            aggregate_type="slice",
            aggregate_id=slice_id,
            event_type="state.slice.steps_completed",
            data={"last_step_id": event.aggregate_id},
            mode="build",
        )
```

**Cascade chain** (ARCHITECTURE.md lines 242-246):
```
# Source: ARCHITECTURE.md:242-246
# Pattern: each tier's terminal events cascade upward
Step: done → daemon checks: last Step in Slice? → emits state.slice.steps_completed
Slice: shipped → daemon checks: last Slice in Stage? → emits state.stage.slices_verified
Stage: shipped → daemon checks: last Stage in Arc? → emits state.arc.retired
```

**Projector handler registration pattern** (projector.py lines 28-45):
```python
# Source: src/state_core/projector.py:28-45
# Pattern: decorator-based registration; HANDLERS dict maps event_type → handler fn
_HandlerFn: type = Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]

HANDLERS: dict[str, _HandlerFn] = {}

def _register_handler(event_type: str) -> Callable[[_HandlerFn], _HandlerFn]:
    def decorator(fn: _HandlerFn) -> _HandlerFn:
        HANDLERS[event_type] = fn
        return fn
    return decorator
```

**Projector cache table routing** (projector.py lines 462-488):
```python
# Source: src/state_core/projector.py:462-515 — rebuild_all routing
# Pattern: aggregate_type → in-memory dict → cache table write
# New: Arc and Stage aggregates need equivalent routing
if aggregate_type == "step":
    target = steps_state
elif aggregate_type == "slice":
    target = slices_state
elif aggregate_type == "concept":
    target = concepts_state
# DESIGN GAP: no arc or phase/stage routing — Phase 400 must spec these
```

**Composite event contract per D-19:** Composite states are projector-computed from child states, NOT explicit machine states. Each composite event is a separate `append()` — no nested transactions. On daemon startup, projector rebuilds all STATE.md projections from the event stream.

---

### `specs/FRONTMATTER-SCHEMAS.md` (schema-design, static-definition)

**Analog:** `src/state_core/schema.py` event data payload models (lines 287-585) + RESEARCH.md pydantic example (lines 469-492)

**Canonical pydantic v2 pattern** (schema.py lines 287-291, replicated across 34+ models):
```python
# Source: src/state_core/schema.py:287-291 — canonical pattern for ALL models
# Pattern: ConfigDict(extra="forbid", frozen=True) — used on all 34+ data payloads
from pydantic import BaseModel, ConfigDict

class ArcCreatedData(BaseModel):
    """Event data for state.arc.created — DESIGN CONTRACT (v41+ runtime)."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str
    goal: str
```

**Non-frozen frontmatter model pattern** (schema.py lines 141-154):
```python
# Source: src/state_core/schema.py:141-154 — ModeConfig for read-write config
# Pattern: extra="forbid" without frozen=True for mutable documents
class ModeConfig(BaseModel):
    """Persisted mode configuration — NOT frozen (read-write)."""
    model_config = ConfigDict(extra="forbid")
    mode: Literal["build", "teach", "both"]
```

**Frontmatter schema design contract pattern** (RESEARCH.md lines 469-492):
```python
# Source: RESEARCH.md:469-492 — derived from schema.py conventions
from pydantic import BaseModel, ConfigDict
from typing import Literal

class StageFrontmatter(BaseModel):
    """Design contract for STAGE.md frontmatter — v41+ runtime validation."""
    model_config = ConfigDict(extra="forbid")

    # ── Agent-owned fields (written by /state-new stage, /state-design stage) ──
    id: str                              # "arc-01/stage-03"
    title: str                           # "OAuth Provider Migration"
    goal: str                            # One-line outcome
    success_criteria: list[str]          # Measurable outcomes
    arc_id: str                          # Parent Arc ID
    depends_on: list[dict[str, str]] = []  # [{id: "stage-02", edge: "blocks"}]

    # ── Projector-owned fields (written by daemon projector, NEVER by agent) ──
    status: Literal["planned", "in_progress", "verified", "shipped", "abandoned"] = "planned"
    slice_count: int = 0
    shipped_slice_count: int = 0
    completed_at: str | None = None
```

**Field ownership rule (TIER-07):**
- Every field is classified EXACTLY ONCE as agent-owned OR projector-owned
- Agent-owned: id, title, goal, success_criteria, arc_id, depends_on
- Projector-owned: status, slice_count, shipped_slice_count, completed_at
- NEVER mixed within a field — no "agent writes initial value, projector mutates"

**D-01 Rename pattern for frontmatter models:**
| Existing Model (schema.py) | Post-Rename Model (spec) |
|---|---|
| `PhasePlannedData` | `StagePlannedData` |
| `PhaseStartedData` | `StageStartedData` |
| `PhaseVerifiedData` | `StageVerifiedData` |
| `PhaseCompletedData` | `StageCompletedData` |
| `phase_number` field | `stage_number` field |
| `phase_id` field (in Slice) | `stage_id` field |

**Aggregate ID encoding pattern** (from schema.py aggregate_id values):
```python
# Pattern: hierarchical slash-delimited IDs per ARCHITECTURE.md §2.3
# Arc:    "arc-{n}"                         eg "arc-01"
# Stage:  "arc-{n}/stage-{n}"               eg "arc-01/stage-03"
# Slice:  "arc-{n}/stage-{n}/slice-{n}"     eg "arc-01/stage-03/slice-12"
# Step:   "arc-{n}/stage-{n}/slice-{n}/step-{n}"  eg "arc-01/stage-03/slice-12/step-004"
```

---

### `specs/DESC-SEMANTICS.md` (semantics-spec, static-definition)

**Analog:** `src/state_core/scheduler.py` Edge model (lines 15-33) + `src/state_core/projector.py` blocked handler (lines 187-199) + D-13/D-14/D-15 decisions

**Edge type model** (scheduler.py lines 15-33):
```python
# Source: src/state_core/scheduler.py:15-33 — authoritative edge type definitions
EdgeKind = Literal["blocks", "soft", "data"]
"""Edge dependency kind:
- blocks: hard prerequisite — target cannot start until source completes.
- soft: advisory — scheduler may override (e.g. for critical-path promotion).
- data: data-flow dependency — target needs source's output artifacts."""

class Edge(BaseModel):
    """A directed dependency edge between two DAG nodes."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_node: str
    target_node: str
    kind: EdgeKind
```

**Blocked state handler** (projector.py lines 187-199):
```python
# Source: src/state_core/projector.py:187-199
# Pattern: blocked state sets state → "blocked", stores reason in frontmatter
@_register_handler("state.step.blocked")
def _handle_step_blocked(
    current: dict[str, Any] | None, data: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": current.get("id", "") if current else "",
        "slice_id": current.get("slice_id", "") if current else "",
        "state": "blocked",
        "title": current.get("title", "") if current else "",
        "frontmatter": _merge_frontmatter(current, data),
        "updated_at": current.get("updated_at", "") if current else "",
    }
```

**Abandon/Defer/Blocked semantics (from D-13/D-14/D-15):**

| Semantics | Derived From | Behavior |
|-----------|-------------|----------|
| Abandon cascade | D-13 | When Slice abandoned → dependents auto-marked BLOCKED. No auto-abandon cascade. User resolves manually. |
| Deferment | D-14 | `status: deferred` + `deferred_reason` frontmatter. Dependents unblock with `deferred_dep` flag (soft-done). |
| No-timeout blocked | D-15 | Blocked state persists indefinitely until deps resolve or user defers blocker. |
| Same-parent only | D-10 | `depends_on` edges are bounded per-parent (Stage deps within same Arc, Slice deps within same Stage). |
| Edge type: blocks | D-12 | Hard prerequisite. Scheduler blocks until source complete. |
| Edge type: soft | D-12 | Advisory ordering. Scheduler may override for critical path. |
| Edge type: data | D-12 | Artifact-producing. Hard edge + artifact path copy. |

**Decimal insertion protocol (D-16):**
```python
# Pattern: single decimal level, no cap on decimal number
# Valid:   slice-12, slice-12.1, slice-12.354
# Invalid: slice-12.1.2 (double decimal — rejected)
# No renumbering: existing IDs immutable; decimals fill gaps without renumbering
```

**Node status model for DAG** (scheduler.py lines 35-46):
```python
# Source: src/state_core/scheduler.py:35-46
# Pattern: node statuses include "blocked" and "failed" for descope states
class Node(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    kind: Literal["arc", "phase", "slice", "step"]
    # Post-rename: "phase" → "stage" in kind Literal
    status: Literal["idle", "pending", "in_progress", "done", "blocked", "failed"] = "idle"
```

---

## Shared Patterns

### pydantic `extra="forbid"` Convention

**Source:** `src/state_core/schema.py` — all 34+ event data payload models use `ConfigDict(extra="forbid")`

**Apply to:** ALL frontmatter schema definitions in FRONTMATTER-SCHEMAS.md and every tier spec's Schema section

```python
# Canonical pattern from schema.py:287-289
from pydantic import BaseModel, ConfigDict

class ArcCreatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)  # frozen for event payloads
    title: str
    goal: str
```

**Frozen vs non-frozen:**
- Event data payloads: `ConfigDict(extra="forbid", frozen=True)` — immutable after construction
- Frontmatter schemas: `ConfigDict(extra="forbid")` — NO frozen, mutable by agent/projector

**Pattern note:** For frontmatter models (FRONTMATTER-SCHEMAS.md), use `extra="forbid"` WITHOUT `frozen=True` because the validation is at parse-time but the models represent documents that may be modified.

### Literal Type Pattern for State Enums

**Source:** `src/state_build/kernel.py` line 7 + `src/state_core/schema.py` line 19

**Apply to:** ALL state/status fields in tier specifications and frontmatter schemas

```python
# Source: kernel.py:7 — StepState as Literal union
StepState = Literal["idle", "discussing", "planning", "executing", "verifying", "done", "blocked", "abandoned"]

# Post-rename target:
StepState = Literal["idle", "designing", "planning", "running", "verifying", "done", "blocked", "abandoned"]
```

### Projector Handler Registration Pattern

**Source:** `src/state_core/projector.py` lines 28-45

**Apply to:** COMPOSITE-CASCADE.md (for defining new Arc/Stage handlers) and EVENT-TAXONOMY.md (for mapping events to projection handlers)

```python
# Source: projector.py:28-45 — @_register_handler decorator
_HandlerFn: type = Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]

HANDLERS: dict[str, _HandlerFn] = {}

def _register_handler(event_type: str) -> Callable[[_HandlerFn], _HandlerFn]:
    def decorator(fn: _HandlerFn) -> _HandlerFn:
        HANDLERS[event_type] = fn
        return fn
    return decorator
```

### CQRS Cache Table Column Pattern

**Source:** `src/state_core/projector.py` lines 404-414

**Apply to:** COMPOSITE-CASCADE.md (defining new Arc/Stage cache table columns)

```python
# Source: projector.py:404-414 — existing 3 cache table column definitions
# Pattern: tuple of column names, matching handler return dict keys
_STEP_COLUMNS = ("id", "slice_id", "state", "title", "frontmatter", "updated_at")
_SLICE_COLUMNS = ("id", "phase_id", "state", "worktree_dir", "worktree_branch", "frontmatter", "updated_at")
_CONCEPT_COLUMNS = ("id", "subject_id", "learner_id", "mastery_probability", "scaffold_level", "bloom_level", "frontmatter", "last_drilled_at", "updated_at")

# Phase 400 design contract — new cache tables to spec:
_ARC_COLUMNS = ("id", "state", "title", "frontmatter", "updated_at")
# post-rename: "id", "state", "title", "frontmatter", "updated_at"
_STAGE_COLUMNS = ("id", "arc_id", "state", "title", "frontmatter", "updated_at")
```

### Mode Isolation Pattern

**Source:** `src/state_core/schema.py` lines 42-48

**Apply to:** EVENT-TAXONOMY.md (ensuring build-mode event prefixes are documented correctly)

```python
# Source: schema.py:42-48 — mode-aware event routing
BUILD_ONLY_EVENT_PREFIXES: frozenset[str] = frozenset(
    {"state.arc.", "state.phase.", "state.slice.", "state.step."}
)
# Post-rename: state.phase. → state.stage.
```

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

*None.* All 9 specification documents map to concrete codebase analogs. The primary challenge is handling the D-01 (Phase→Stage) and D-03 (discuss→design, execute→run) renames: the spec documents use forward-looking terminology while referencing existing code that uses pre-rename identifiers.

## Metadata

**Analog search scope:**
- `src/state_core/schema.py` — aggregate types, event type Literals, event data payload models
- `src/state_core/projector.py` — CQRS handler registration, cache table routing, blocked state pattern
- `src/state_build/kernel.py` — StepMachine skeleton, StepState Literal
- `src/state_core/scheduler.py` — Edge model, EdgeKind Literal, Node status model
- `.planning/research/ARCHITECTURE.md` — tier definitions, state machine diagrams, composite cascade

**Files scanned:** 5 codebase files + 1 architecture doc
**Pattern extraction date:** 2026-05-06

### Rename Migration Patterns (cross-cutting)

**D-01 Phase→Stage rename** affects every specification document and every codebase reference:

| Pattern Category | Pre-Rename (existing code) | Post-Rename (Phase 400 spec) |
|-----------------|---------------------------|------------------------------|
| Aggregate type literal | `"phase"` | `"stage"` |
| Event type prefix | `state.phase.*` | `state.stage.*` |
| Data model classes | `PhasePlannedData`, `PhaseStartedData`, etc. | `StagePlannedData`, `StageStartedData`, etc. |
| Cache table | `slices.phase_id` column | `slices.stage_id` column |
| Node kind | `Literal["phase"]` | `Literal["stage"]` |
| Artifact file | `PHASE.md` | `STAGE.md` |
| Directory | `phases/` | `stages/` |
| Field name | `phase_number` | `stage_number` |

**D-03 discuss→design, execute→run renames** affect Step tier only:

| Pattern Category | Pre-Rename (existing code) | Post-Rename (Phase 400 spec) |
|-----------------|---------------------------|------------------------------|
| Step state | `"discussing"` | `"designing"` |
| Step state | `"executing"` | `"running"` |
| Event type | `state.step.discussed` | `state.step.designed` |
| Event type | `state.step.executed` | `state.step.ran` |
| Data model | `StepDiscussedData` | `StepDesignedData` |
| Data model | `StepExecutedData` | `StepRanData` |
| Artifact | `DISCUSS.md` | `DESIGN.md` |
| Artifact | `EXECUTE.log` | `RUN.log` |
