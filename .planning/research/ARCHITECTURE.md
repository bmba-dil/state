# Build Hierarchy & Artifact System Architecture

**Project:** `state` — v40 Design-Phase Milestone
**Domain:** Four-tier product hierarchy (Arc → Phase → Slice → Step) integration with event-sourced state machine engine
**Researched:** 2026-05-06
**Confidence:** HIGH on event-store integration (code read directly); HIGH on scheduler/worktree integration (code read directly); MEDIUM on TUI visualization patterns (inferred from plugin structure); MEDIUM on MCP tool scoping (design choice)

---

## 0. Executive Summary

This document defines the **four-tier product hierarchy** and how it integrates with every existing subsystem in `state`. The hierarchy (Arc → Phase → Slice → Step) replaces GSD's two-tier milestone→phase model with a richer decomposition that separates scope, concurrency, and the discuss/plan/execute/verify cycle into distinct tiers.

**The fundamental insight:** each tier is a **CQRS aggregate** with its own event types, state machine, projection, and on-disk artifacts. State flows upward: Step outcomes aggregate into Slice rollups, Slice rollups aggregate into Phase verification, Phase completion rolls into Arc retirement. The event store is the only source of truth at every tier.

### Integration Points

| Subsystem | How Hierarchy Integrates | What Changes |
|-----------|------------------------|--------------|
| **Event Store** (`events.py`) | Each tier is an aggregate; tier transitions emit typed events with aggregate cascade (e.g., `state.step.done` → daemon emits `state.slice.step_completed`) | New Arc/Phase/Slice aggregate types; composite events for rollup |
| **CQRS Projector** (`projector.py`) | New projection handlers for arc/phase; projector rebuilds STATE.md files at each tier from events | `Arc` and `Phase` cache tables; STATE.md file projection (new) |
| **DAG Scheduler** (`scheduler.py`) | Slices are the concurrency unit (existing); `depends_on` edges from SLICE.md frontmatter fed to scheduler; Arc/Phase nodes are scheduling containers | Scheduler already reads Step-level edges; extend to Slice-level edges and cross-Phase dependencies |
| **Worktree** (`worktree.py`) | Per-Slice worktree (existing); one worktree per Slice, Steps execute serially within the Slice's worktree | No structural change; hierarchy clarifies ownership |
| **On-Disk Layout** (`.state/build/`) | Hierarchical mirror: `arcs/{arc-id}/phases/{phase-id}/slices/{slice-id}/steps/{step-id}/` | Full redesign from flat current layout to nested tiers |
| **MCP Tools** (`state-build`) | Tools scoped to tiers: Arc tools (roadmap, retire), Phase tools (verify-phase, audit-phase), Slice tools (ship-slice, revert-slice), Step tools (discuss, plan, execute, verify) | Tool naming convention `state_build__{tier}_{action}` |
| **TUI** (`@state/opencode-plugin`) | Hierarchy tree in sidebar; DAG viewer shows all four tiers; statusline shows active path | Hierarchical rendering with expand/collapse per tier |
| **STATE.md Consistency** | Projector rebuilds STATE.md at every tier from event stream — agents NEVER write STATE.md directly | New projector output; health validation detects drift |

### Critical Design Decisions

1. **Arc/Phase/Slice/Step are four independent CQRS aggregates**, not a single hierarchical document. Each has its own event stream (`aggregate_id = arc-01`, `aggregate_id = arc-01/phase-03`, etc.). Cross-tier relationships are encoded in event data (e.g., `state.phase.planned` carries `arc_id`).

2. **The daemon emits composite events for cross-tier rollup.** When the last Step in a Slice reaches DONE, the daemon emits `state.slice.step_completed`. When the last Slice in a Phase reaches VERIFIED, the daemon emits `state.phase.slices_verified`. No agent code computes rollup — it's all projector-driven.

3. **STATE.md at every tier is a projector artifact, not agent-written.** On daemon startup, the projector replays all events and rebuilds every STATE.md from scratch. Agents write STEP.md, PLAN.md, VERIFY.md — the projector writes STATE.md. This eliminates the GSD problem where agents miss updating tracking files.

4. **Slices are the concurrency unit (unchanged).** Steps within a Slice execute serially within the Slice's worktree. Multiple Slices run concurrently across different worktrees, capped by `concurrency_cap`.

5. **`depends_on` edges exist at both Slice and Step levels.** Slice-level edges define cross-Slice DAG within a Phase. Step-level edges define serial ordering within a Slice. Cross-Phase Slice dependencies are supported via fully-qualified Slice IDs.

---

## 1. Tier Definitions & State Machines

### 1.1 Arc State Machine

An Arc is a feature block / project branch containing many Phases. Think "the auth system" or "the plugin framework." It is the coarsest scoping container.

```
States:  planned → in_progress → shipped | abandoned

  ┌──────────┐  create   ┌─────────────┐  last-phase-shipped  ┌──────────┐
  │  planned  │─────────►│ in_progress  │───────────────────►│  shipped  │
  └──────────┘           └─────────────┘                      └──────────┘
       │                       │
       │  abandon               │  abandon
       ▼                       ▼
  ┌──────────────┐
  │  abandoned   │
  └──────────────┘
```

**Events:**
- `state.arc.created` → arc aggregate enters `planned`
- `state.arc.retired` → arc transitions to `shipped` (when all phases complete)
- `state.arc.updated` → frontmatter/scope change while in `planned` or `in_progress`

**Transition guards:**
- `planned → in_progress`: at least one child Phase is `planned`
- `in_progress → shipped`: ALL child Phases are `shipped`
- `* → abandoned`: explicit abandon command; all in-progress Phases also abandoned

**Arc aggregate ID:** `arc-{id}` (e.g., `arc-01`, `arc-auth`)

### 1.2 Phase State Machine

A Phase owns multiple Slices and defines success criteria at the milestone level.

```
States:  planned → in_progress → verified → shipped | abandoned

  ┌──────────┐  start   ┌─────────────┐  slices-verified  ┌──────────┐  complete  ┌──────────┐
  │  planned  │────────►│ in_progress  │─────────────────►│ verified  │──────────►│  shipped  │
  └──────────┘          └─────────────┘                    └──────────┘            └──────────┘
       │                       │                                │
       │  abandon               │  abandon                       │  abandon
       ▼                       ▼                                ▼
  ┌──────────────┐
  │  abandoned   │
  └──────────────┘
```

**Events:**
- `state.phase.planned` → phase aggregate created, carries `arc_id`
- `state.phase.started` → first Slice transitions to `in_progress`
- `state.phase.slices_verified` → ALL child Slices are `shipped` (composite event, daemon-emitted)
- `state.phase.verified` → manual verify-rollup passes (goes beyond Slice verification: cross-Slice integration, UAT, documentation)
- `state.phase.completed` → phase transitions to `shipped`

**Transition guards:**
- `planned → in_progress`: at least one child Slice is `worktree_ready`
- `in_progress → verified`: ALL child Slices are `shipped`
- `verified → shipped`: `state.phase.verified` event with `passed: true`

**Phase aggregate ID:** `{arc-id}/phase-{n}` (e.g., `arc-01/phase-03`) — hierarchical ID encodes parent Arc.

### 1.3 Slice State Machine

A Slice is the concurrency unit. One worktree per Slice. Owns multiple Steps (executed serially within the worktree).

```
States:  planned → worktree_ready → in_progress → shipped | reverted

  ┌──────────┐  worktree-create  ┌────────────────┐  first-step  ┌─────────────┐
  │  planned  │─────────────────►│ worktree_ready  │────────────►│ in_progress  │
  └──────────┘                   └────────────────┘              └─────────────┘
                                                                       │
                                                              all-steps-done
                                                                       │
                                                                       ▼
                                                                 ┌──────────┐  ship  ┌──────────────┐
                                                                 │  verified │──────►│   shipped    │
                                                                 └──────────┘       └──────────────┘
                                                                       │
                                                                       │ revert
                                                                       ▼
                                                                 ┌──────────────┐
                                                                 │   reverted   │
                                                                 └──────────────┘
```

**Events:**
- `state.slice.planned` → Slice defined with its Step list
- `state.slice.worktree_ready` → daemon created worktree (opencode HTTP or pygit2)
- `state.slice.steps_completed` → ALL child Steps are `done` (composite event)
- `state.slice.shipped` → worktree merged, snapshot tagged
- `state.slice.reverted` → Slice worktree reset to last snapshot

**Transition guards:**
- `planned → worktree_ready`: worktree created successfully
- `worktree_ready → in_progress`: first Step dispatched
- `in_progress → verified`: ALL child Steps are `done`
- `verified → shipped`: explicit ship command succeeds
- `* → reverted`: explicit revert command; worktree preserved

**Slice aggregate ID:** `{arc-id}/phase-{n}/slice-{n}` (e.g., `arc-01/phase-03/slice-12`)

### 1.4 Step State Machine (existing, extended)

The Step is the only tier that runs the full discuss → plan → execute → verify cycle. Steps within a Slice execute serially.

```
States:  idle → discussing → planning → executing → verifying → done | blocked | abandoned

  ┌──────┐  start   ┌────────────┐  plan-accepted  ┌──────────┐  execute   ┌───────────┐
  │ idle  │────────►│ discussing │───────────────►│ planning │──────────►│ executing │
  └──────┘          └────────────┘                 └──────────┘            └───────────┘
                         │                                                        │
                         │ skip-to-plan                                           │ verify-start
                         ▼                                                        ▼
                    ┌──────────┐                                            ┌───────────┐
                    │ planning │                                            │ verifying │
                    └──────────┘                                            └───────────┘
                                                                              │       │
                                                                     pass ◄───┘       └──► fail
                                                                      │                  │
                                                                      ▼                  │
                                                                ┌──────────┐    ┌───────────┐
                                                                │   done   │    │ executing │
                                                                └──────────┘    └───────────┘
                                                                      │
                                                                      │ blocked
                                                                      ▼
                                                                ┌──────────┐  unblock  ┌───────────┐
                                                                │ blocked  │──────────►│ executing │
                                                                └──────────┘            └───────────┘
                                                                      │
                                                                      │ abandon
                                                                      ▼
                                                                ┌──────────────┐
                                                                │  abandoned   │
                                                                └──────────────┘
```

**Events (10 existing, unchanged):**
- `state.step.discussed` — approach decided
- `state.step.planned` — STEP.md with verify_contract written
- `state.step.executed` — code changes made
- `state.step.verify_started` — verifier invoked
- `state.step.verify_passed` — verification succeeded
- `state.step.verify_failed` — verification failed, returns to executing
- `state.step.advanced` — generic state advancement
- `state.step.blocked` — blocked on external condition
- `state.step.snapshotted` — snapshot taken
- `state.step.reverted` — reverted to prior snapshot

**Transition guards:**
- `discussing → planning`: DISCUSS.md written, approach decided
- `planning → executing`: PLAN.md written, verify_contract defined
- `executing → verifying`: explicitly triggered by user/agent
- `verifying → done`: all verify_contract items pass
- `verifying → executing`: at least one verify_contract item fails
- `* → blocked`: explicit block (e.g., depends_on predecessor failed)
- `blocked → executing`: predecessor completed or manual unblock

**Step aggregate ID:** `{arc-id}/phase-{n}/slice-{n}/step-{n}` (e.g., `arc-01/phase-03/slice-12/step-004`)

---

## 2. Event Store Integration

### 2.1 Aggregate Types (extending existing schema)

Current `schema.py` defines `AggregateType = Literal["arc", "phase", "slice", "step", ...]`. The four tiers already exist as aggregate discriminators. What changes:

1. **Arc and Phase aggregates gain cache tables** (currently only `steps`, `slices`, `concepts` are cached — see `projector.py:31`).
2. **Composite events for cross-tier rollup** — daemon listens for terminal per-aggregate events and emits parent-tier composite events.
3. **Event data payloads carry parent IDs** — every event's `data` dict includes the parent aggregate ID so projectors can maintain the hierarchy mapping.

### 2.2 Composite Event Flow

When a Step reaches `done` (terminal state), the daemon's post-commit callback checks if this was the last Step in its Slice. If so, it emits a composite event:

```python
# Pseudocode — daemon-side event handler
async def on_step_advanced(event: StepEvent):
    """Check if all Steps in the parent Slice are done."""
    slice_id = extract_slice_id(event.aggregate_id)  # "arc-01/phase-03/slice-12"
    steps = await store.read_stream(slice_id + "/step-")  # read all step events
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

The same cascade applies upward:
- **Step → Slice:** Last Step done → `state.slice.steps_completed`
- **Slice → Phase:** Last Slice shipped → `state.phase.slices_verified`
- **Phase → Arc:** Last Phase shipped → `state.arc.retired`

This is **NOT** a synchronous nested write. Each composite event is a separate `append()` call, so the event store remains append-only and deterministic. The cascade is triggered by post-commit callbacks registered via `store.add_post_commit_callback()`.

### 2.3 Event Data Payload Extension

Existing payload models (e.g., `PhasePlannedData`, `SlicePlannedData`) need parent ID fields:

| Event Data Model | New Field | Type | Purpose |
|-----------------|-----------|------|---------|
| `PhasePlannedData` | `arc_id` | `str` | Parent Arc aggregate ID |
| `SlicePlannedData` | `phase_id` | `str` | Parent Phase aggregate ID |
| `StepPlannedData` | `slice_id` | `str` | Parent Slice aggregate ID |

These already exist in the current codebase for Slice and Step events (e.g., `slice_id` in Step handlers), but Arc/Phase events lack explicit parenting. The hierarchical aggregate ID encoding (`arc-01/phase-03/...`) makes parent extraction trivial via string parsing, but an explicit field is clearer for queries.

**Decision: Use hierarchical aggregate IDs with slash-delimited encoding.** The parent is always a prefix:
- `arc-01/phase-03/slice-12/step-004` → parent Slice is `arc-01/phase-03/slice-12`
- `arc-01/phase-03/slice-12` → parent Phase is `arc-01/phase-03`
- `arc-01/phase-03` → parent Arc is `arc-01`

This avoids storing redundant parent IDs in every event and makes aggregate stream queries trivial (read all events where `aggregate_id LIKE 'arc-01/phase-03/%'`).

---

## 3. CQRS Projector Integration

### 3.1 New Cache Tables

The projector currently maintains three cache tables: `steps`, `slices`, `concepts`. We add:

```sql
-- Arc cache (new)
CREATE TABLE arcs (
    id TEXT PRIMARY KEY,            -- e.g., 'arc-01'
    state TEXT NOT NULL,            -- planned | in_progress | shipped | abandoned
    title TEXT NOT NULL,
    goal TEXT NOT NULL,
    frontmatter TEXT NOT NULL,      -- JSON dump of ARC.md frontmatter
    phase_count INTEGER NOT NULL DEFAULT 0,
    shipped_phase_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

-- Phase cache (new)
CREATE TABLE phases (
    id TEXT PRIMARY KEY,            -- e.g., 'arc-01/phase-03'
    arc_id TEXT NOT NULL,
    state TEXT NOT NULL,            -- planned | in_progress | verified | shipped | abandoned
    title TEXT NOT NULL,
    goal TEXT NOT NULL,
    frontmatter TEXT NOT NULL,      -- JSON dump of PHASE.md frontmatter
    slice_count INTEGER NOT NULL DEFAULT 0,
    shipped_slice_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_phases_arc ON phases(arc_id);
```

The existing `slices` cache table is extended with `arc_id` (derivable from `phase_id`, but denormalized for query convenience).

### 3.2 New Projection Handlers

Handlers for Arc and Phase aggregate events:

```python
@_register_handler("state.arc.created")
def _handle_arc_created(current, data):
    return {
        "id": data.get("arc_id", ""),
        "state": "planned",
        "title": data.get("title", ""),
        "goal": data.get("goal", ""),
        "frontmatter": _merge_frontmatter(current, data),
        "phase_count": data.get("phase_count", 0),
        "shipped_phase_count": 0,
        "updated_at": "",
    }

@_register_handler("state.arc.retired")
def _handle_arc_retired(current, data):
    return {**current, "state": "shipped", "frontmatter": _merge_frontmatter(current, data)} if current else {}

@_register_handler("state.phase.planned")
def _handle_phase_planned(current, data):
    return {
        "id": data.get("phase_id", ""),
        "arc_id": data.get("arc_id", ""),
        "state": "planned",
        "title": data.get("title", ""),
        "goal": data.get("goal", ""),
        "frontmatter": _merge_frontmatter(current, data),
        "slice_count": data.get("slice_count", 0),
        "shipped_slice_count": 0,
        "updated_at": "",
    }

# ... handlers for state.phase.started, state.phase.slices_verified,
#     state.phase.verified, state.phase.completed
```

### 3.3 STATE.md File Projection (New)

The projector's `rebuild_all()` method currently only writes to SQLite cache tables. We add a **file projection** step that writes STATE.md files to the on-disk hierarchy:

```python
async def rebuild_state_files(self) -> dict[str, str]:
    """Rebuild STATE.md files at every tier from cache tables.
    
    Called after rebuild_all(). Reads from arcs/phases/slices/steps
    cache tables and writes STATE.md files to the filesystem
    hierarchy. Returns dict of path -> content for audit.
    """
    # Read all arcs from cache
    arcs = await self._read_table("arcs")
    written = {}
    for arc in arcs:
        arc_dir = Path(f".state/build/arcs/{arc['id']}")
        arc_dir.mkdir(parents=True, exist_ok=True)
        state_content = self._render_state_md(arc, "arc")
        (arc_dir / "STATE.md").write_text(state_content)
        written[str(arc_dir / "STATE.md")] = state_content

        # Read phases for this arc
        phases = await self._read_table("phases", where=f"arc_id = '{arc['id']}'")
        for phase in phases:
            phase_dir = arc_dir / "phases" / phase['id'].split('/')[-1]
            phase_dir.mkdir(parents=True, exist_ok=True)
            state_content = self._render_state_md(phase, "phase")
            (phase_dir / "STATE.md").write_text(state_content)
            # ... recurse into slices and steps
    
    return written

def _render_state_md(self, row: dict, tier: str) -> str:
    """Render a STATE.md file from a cache row."""
    fm = json.loads(row.get("frontmatter", "{}"))
    return f"""# STATE: {row['id']}
**Tier:** {tier}
**Status:** {row['state']}
**Updated:** {row['updated_at']}
"""
```

**Key invariant:** STATE.md files are throwaway projections. On daemon startup, `rebuild_state_files()` wipes and rewrites every STATE.md from the event store. Agents NEVER write STATE.md — they write the artifact files (ARC.md, PHASE.md, SLICE.md, STEP.md, PLAN.md, VERIFY.md) and the daemon's projector handles STATE.md.

### 3.4 Consistency Validation

A `validate_consistency()` function (akin to GSD's `verify.cjs`) detects drift between filesystem STATE.md and event-store state:

```python
async def validate_consistency() -> list[ConsistencyWarning]:
    """Compare STATE.md files against projector output.
    
    Returns empty list when consistent. Each warning carries:
    - tier: arc|phase|slice|step
    - path: filesystem path
    - event_state: state derived from events
    - file_state: state read from STATE.md
    - severity: critical|warning|info
    """
```

Detection triggers on daemon startup and on-demand via `state build health`.

---

## 4. DAG Scheduler Integration

### 4.1 Scheduler Architecture (Existing, Extended)

The DAG scheduler (`scheduler.py`) already operates on `Node` objects with `kind: Literal["arc", "phase", "slice", "step"]` and `status`. The hierarchy integration requires:

1. **Nodes at all four tiers registered with the scheduler.** The scheduler's `NodeRegistry` already supports all four `kind` values.
2. **Slice-level `depends_on` edges fed to the scheduler** alongside existing Step-level edges.
3. **Cross-Phase Slice dependencies** via fully-qualified Slice IDs.

### 4.2 Edge Extraction from Frontmatter

The scheduler reads `depends_on` from artifact frontmatter and converts them to `Edge` objects. This extraction happens at two levels:

**Slice-level dependencies** (from SLICE.md frontmatter):
```yaml
# SLICE.md frontmatter
id: arc-01/phase-03/slice-12
depends_on:
  - id: arc-01/phase-03/slice-11   # same Phase, prior Slice
    kind: blocks
  - id: arc-01/phase-02/slice-07   # cross-Phase dependency
    kind: data
```

**Step-level dependencies** (from STEP.md frontmatter, existing):
```yaml
# STEP.md frontmatter
id: arc-01/phase-03/slice-12/step-004
depends_on:
  - id: arc-01/phase-03/slice-12/step-003
    kind: blocks
  - id: arc-01/phase-03/slice-12/step-002
    kind: data
```

### 4.3 Scheduler Tick with Four Tiers

The `DAGScheduler.tick()` method already computes a frontier, groups by Slice, and dispatches. The hierarchy change means:

1. **The frontier includes Slice nodes** — not just Step nodes. When all predecessor Slices are done, the Slice itself enters the frontier.
2. **Slice dispatch triggers worktree creation** — the executor for a Slice node calls `WorktreeService.create()`, then dispatches its Steps serially.
3. **Step nodes within a Slice are dispatched serially** — existing `_run_slice()` behavior, unchanged.

```python
async def tick_with_hierarchy(self, nodes: list[Node], edges: list[Edge]) -> list[str]:
    """Extended tick that handles Slice-level scheduling.
    
    1. Compute frontier (may include Slice nodes with no blocking predecessors).
    2. For each Slice in frontier:
       a. If worktree not yet created → create worktree → mark worktree_ready
       b. If worktree ready → compute Step frontier within Slice → dispatch Steps serially
    3. Return dispatched IDs.
    """
    ready = frontier(nodes, edges)
    
    # Separate Slice nodes from Step nodes
    slice_nodes = [n for n in ready if n.kind == "slice"]
    step_nodes = [n for n in ready if n.kind == "step"]
    
    # For each Slice, ensure worktree exists, then run Steps serially
    for sl_node in slice_nodes:
        if sl_node.status == "idle":
            await self._create_worktree(sl_node)
        
        # Get all Steps within this Slice
        slice_steps = [
            n for n in step_nodes
            if n.id.startswith(_slice_key(sl_node.id))
        ]
        # Sort Steps within Slice
        slice_steps.sort(key=lambda n: _parse_sort_key(n.id))
        
        # Dispatch Steps serially within the Slice's worktree
        await self._run_slice_steps(slice_steps, sl_node.id)
```

### 4.4 Depends-On Edge Kinds (Unchanged)

| Kind | Semantics | Scheduler Behavior |
|------|-----------|-------------------|
| `blocks` | Hard prerequisite — target cannot start until source is DONE | Blocking edge; included in frontier calculation |
| `soft` | Advisory — scheduler may override for critical-path promotion | NOT blocking; used only for priority inversion detection |
| `data` | Data-flow dependency — target needs source's output artifacts | Blocking edge (same as `blocks`); plus artifact-path propagation |

---

## 5. Worktree Integration

### 5.1 Per-Slice Worktree (Existing, Unchanged)

The existing model remains: one git worktree per Slice. The `WorktreeService` protocol already supports this. The hierarchy clarifies the mapping:

| Tier | Worktree? | Why |
|------|-----------|-----|
| Arc | No | Scoping container; no code changes directly owned by an Arc |
| Phase | No | Scoping container; no code changes directly owned by a Phase |
| **Slice** | **Yes** | Concurrency unit; each Slice gets one worktree |
| Step | No (uses Slice's worktree) | Steps run serially within the Slice's worktree, scoped by `shell.env` hook |

### 5.2 Worktree Naming Convention

Worktrees follow the hierarchical ID:

```
Worktree name:   arc-01/phase-03/slice-12
Branch:          state/arc-01/phase-03/slice-12
On-disk path:    .state/build/arcs/arc-01/phases/phase-03/slices/slice-12/worktree/
```

The worktree is created when the Slice transitions from `planned` to `worktree_ready`. The daemon's scheduler dispatches worktree creation:

1. Scheduler picks unblocked Slice → calls `WorktreeService.create(name, branch)`
2. Worktree creation succeeds → daemon emits `state.slice.worktree_ready` with path/branch
3. Plugin's `shell.env` hook sets `STATE_WORKTREE` to the worktree path
4. All LLM tool calls (edit, bash, read) are scoped to the worktree path via `tool.execute.before` hook

### 5.3 Step Serialization Within Slice

Steps within a Slice execute **serially** within the Slice's single worktree. This is enforced by:
1. Scheduler dispatches only one Step per Slice at a time
2. `tool.execute.before` hook rejects writes outside the active worktree

If a Slice needs true parallel Steps, they must be separate Slices (different worktrees, concurrent execution).

---

## 6. On-Disk Directory Layout

### 6.1 Complete `.state/build/` Tree

```
.state/build/
├── arcs/
│   └── {arc-id}/                      # e.g., arc-01, arc-auth
│       ├── ARC.md                     # Arc definition + frontmatter
│       ├── STATE.md                   # Projector-rebuilt state projection
│       ├── DECISIONS.md               # Arc-level gray-area decisions
│       └── phases/
│           └── {phase-id}/            # e.g., phase-03
│               ├── PHASE.md           # Phase definition + frontmatter
│               ├── STATE.md           # Projector-rebuilt state projection
│               ├── DECISIONS.md       # Phase-level gray-area decisions
│               └── slices/
│                   └── {slice-id}/    # e.g., slice-12
│                       ├── SLICE.md   # Slice definition + frontmatter
│                       ├── STATE.md   # Projector-rebuilt state projection
│                       ├── worktree/  # Git worktree (not committed)
│                       ├── snapshots/ # Content-addressed Step snapshots
│                       └── steps/
│                           └── {step-id}/ # e.g., step-004
│                               ├── STEP.md      # Step definition + verify_contract
│                               ├── DISCUSS.md   # Discuss-phase output
│                               ├── PLAN.md      # Plan-phase output
│                               ├── VERIFY.md    # Verify-phase output
│                               └── EXECUTE.log  # Structured execution log
├── templates/                         # Artifact templates
│   ├── ARC.md.tmpl
│   ├── PHASE.md.tmpl
│   ├── SLICE.md.tmpl
│   └── STEP.md.tmpl
├── skills/                            # Build-mode skills (opencode auto-discovers)
├── config/                            # Build-mode configuration
│   └── profiles.toml                  # Model profiles, concurrency caps
├── intel/                             # Codebase intelligence
├── codebase/                          # Codebase mapping
├── graph/                             # Knowledge graph
├── decisions/                         # Cross-tier decision log (global)
├── patterns/                          # Pattern library
└── index.json                         # Artifact registry (machine-readable index)
```

### 6.2 Directory Naming Conventions

| Tier | Directory Name | Example | Format |
|------|---------------|---------|--------|
| Arc | `{arc-id}` | `arc-01`, `arc-auth` | `{prefix}-{slug}` |
| Phase | `{phase-id}` | `phase-03` | `phase-{n}` (within arc context) |
| Slice | `{slice-id}` | `slice-12` | `slice-{n}` (within phase context) |
| Step | `{step-id}` | `step-004` | `step-{n:03d}` (within slice context) |

**ID schemes (decision needed — see §9):**

**Option A: Sequential per-parent (recommended)**
- Arc IDs: user-chosen slug + sequential number (`arc-01`, `arc-02-a`)
- Phase IDs: sequential within Arc (`phase-01`, `phase-02`) → full ID: `arc-01/phase-02`
- Slice IDs: sequential within Phase (`slice-01`, `slice-02`) → full ID: `arc-01/phase-02/slice-01`
- Step IDs: sequential within Slice (`step-001`, `step-002`) → full ID: `arc-01/phase-02/slice-01/step-001`

**Advantages:** Predictable ordering; easy to scan; gap-closure inserts use decimal (`step-003.1`).

**Option B: UUID-based**
- Every tier gets a UUID → full ID: `01JQ...`
- **Disadvantage:** Hard to scan; loses ordering; no meaningful grouping.

**Recommendation: Option A (sequential per-parent).** Decimal insertion (`step-003.1`, `step-003.2`) handled at the Step level for gap-closure within a Slice. Slice-level decimal insertion (`slice-12.1`) for cross-Slice gap closure within a Phase. No decimal insertion at Arc or Phase — those tiers are pre-planned.

### 6.3 Artifact Registry (`index.json`)

A machine-readable index at `.state/build/index.json` maps every artifact to its path, tier, and state. Rebuilt by the projector alongside STATE.md:

```json
{
  "arcs": {
    "arc-01": {
      "path": "arcs/arc-01/",
      "state": "in_progress",
      "phases": ["phase-01", "phase-02", "phase-03"]
    }
  },
  "phases": {
    "arc-01/phase-03": {
      "path": "arcs/arc-01/phases/phase-03/",
      "state": "in_progress",
      "arc_id": "arc-01",
      "slices": ["slice-11", "slice-12"]
    }
  }
}
```

---

## 7. Artifact Catalog

### 7.1 Complete Artifact Table

| Artifact | Tier | Creator | Updates | Schema (Pydantic) | Cross-References |
|----------|------|---------|---------|-------------------|-----------------|
| **ARC.md** | Arc | `state build arc new` | Agent | `ArcFrontmatter` | References other arcs via `depends_on` |
| **ARC-STATE.md** | Arc | Projector (auto) | Projector (auto) | `ArcStateProjection` | Derived from `state.arc.*` events |
| **PHASE.md** | Phase | `state build phase new` | Agent | `PhaseFrontmatter` | References parent Arc, child Slices |
| **PHASE-STATE.md** | Phase | Projector (auto) | Projector (auto) | `PhaseStateProjection` | Derived from `state.phase.*` events |
| **SLICE.md** | Slice | `state build slice new` | Agent | `SliceFrontmatter` | References parent Phase, `depends_on` edges |
| **SLICE-STATE.md** | Slice | Projector (auto) | Projector (auto) | `SliceStateProjection` | Derived from `state.slice.*` events |
| **STEP.md** | Step | `state build step plan` | Agent | `StepFrontmatter` | References parent Slice, `depends_on` edges |
| **DISCUSS.md** | Step | `state build step discuss` | Agent | (Freetext markdown) | References STEP.md goal |
| **PLAN.md** | Step | `state build step plan` | Agent | (Freetext markdown) | References STEP.md `verify_contract` |
| **VERIFY.md** | Step | `state build step verify` | Agent/Verifier | `VerifyResult` | References PLAN.md must-haves |
| **EXECUTE.log** | Step | `state build step execute` | Agent (structured) | `ExecuteLog` | Per-subtask commit hashes |
| **DECISIONS.md** | Arc/Phase | `state build decision record` | Agent | `GrayAreaDecision` | References the Arc/Phase + question |
| **index.json** | Root | Projector (auto) | Projector (auto) | `ArtifactIndex` | All artifact paths + states |

### 7.2 Frontmatter Specifications

**ARC.md:**
```yaml
# Required
id: arc-01                           # Unique Arc identifier
title: "Auth System Overhaul"        # Human-readable name
status: in_progress                  # planned | in_progress | shipped | abandoned
goal: "Provide authentication..."    # One-line outcome
success_criteria:                    # Measurable outcomes
  - "All five auth methods ship day one"
  - "OAuth refresh survives process crash"

# Optional
depends_on: []                       # Other Arc IDs (cross-Arc dependency)
phases:                              # Planned Phase list (may evolve)
  - phase-01                         # Phase ID within this Arc
  - phase-02
opencode_surface:                    # Required per PROJECT.md
  - packages/opencode/src/sync/
  - packages/opencode/src/storage/
model_profile:                       # Default model for this Arc
  provider: anthropic
  model: claude-sonnet-4-6
```

**PHASE.md:**
```yaml
# Required
id: arc-01/phase-03
title: "OAuth Provider Migration"
status: in_progress                  # planned | in_progress | verified | shipped | abandoned
goal: "Migrate all OAuth providers..."
success_criteria:
  - "All provider refresh tests pass"
  - "Token rotation survives SIGTERM"

# Optional
arc_id: arc-01                       # Parent Arc (redundant but explicit)
slices:                              # Planned Slice list
  - slice-11
  - slice-12
  - slice-13
verify_rollup:                       # Cross-Slice verification criteria
  - type: integration
    description: "End-to-end OAuth flow with all providers"
depends_on: []                       # Other Phase IDs (rare — cross-Arc Phase dependency)
```

**SLICE.md:**
```yaml
# Required
id: arc-01/phase-03/slice-12
title: "Anthropic OAuth Implementation"
status: planned                      # planned | worktree_ready | in_progress | shipped | reverted
goal: "Implement Anthropic OAuth stealth flow"

# Optional
phase_id: arc-01/phase-03            # Parent Phase
worktree:
  name: arc-01/phase-03/slice-12
  branch: state/arc-01/phase-03/slice-12
steps:
  - step-001                         # Step 1: discuss-approach
  - step-002                         # Step 2: plan-implementation
  - step-003                         # Step 3: execute-oauth-flow
  - step-004                         # Step 4: verify-stealth-headers
depends_on:
  - id: arc-01/phase-03/slice-11     # Prior Slice must be done
    kind: blocks
snapshot_ref: null                   # Set at ship time
```

**STEP.md:**
```yaml
# Required
id: arc-01/phase-03/slice-12/step-004
title: "Verify Stealth Headers"
state: idle                          # idle | discussing | planning | executing | verifying | done | blocked | abandoned
goal: "Verify Anthropic OAuth stealth headers match claude-oauth.md byte-for-byte"

# Optional
slice_id: arc-01/phase-03/slice-12
verify_contract:                     # What must pass for this Step to be "done"
  - type: tests
    cmd: "pytest tests/auth/test_anthropic_oauth.py -k stealth_headers"
    severity: error
    allow: 0
  - type: header_capture
    spec: "state-inputs/claude-oauth.md"
    field: "headers"
depends_on:
  - id: arc-01/phase-03/slice-12/step-003
    kind: blocks                    # Must complete execute-oauth-flow first
model_profile:
  provider: anthropic
  model: claude-sonnet-4-6
  temperature: 0.2                  # Low-temp for verification
  thinking: { enabled: false }
snapshots:
  pre_execute: null                 # Set when entering executing
  pre_verify: null                  # Set when entering verifying
cost_cap: 0.50                      # Max USD spend for this Step
```

---

## 8. Cross-Referencing Rules

### 8.1 Reference Format

All cross-references use **fully-qualified hierarchical IDs with slash-delimited paths**. This is the unambiguous reference format:

| Reference Type | Format | Example |
|---------------|--------|---------|
| Arc reference | `arc-{id}` | `arc-auth` |
| Phase reference | `arc-{id}/phase-{n}` | `arc-01/phase-03` |
| Slice reference | `arc-{id}/phase-{n}/slice-{n}` | `arc-01/phase-03/slice-12` |
| Step reference | `arc-{id}/phase-{n}/slice-{n}/step-{n:03d}` | `arc-01/phase-03/slice-12/step-004` |
| File path | `arcs/{arc-id}/phases/{phase-id}/slices/{slice-id}/steps/{step-id}/{file}` | `arcs/arc-01/phases/phase-03/slices/slice-12/steps/step-004/STEP.md` |

### 8.2 Reference Resolution

**Parent resolution** (child → parent):
- STEP.md → parent Slice: extract prefix up to last `/` from Step ID
- SLICE.md → parent Phase: extract prefix up to last `/` from Slice ID
- PHASE.md → parent Arc: extract prefix up to last `/` from Phase ID

**Child resolution** (parent → children):
- ARC.md → child Phases: prefix `arc-{id}/phase-` + list from frontmatter `phases` field
- PHASE.md → child Slices: prefix `phase-id/slice-` + list from frontmatter `slices` field
- SLICE.md → child Steps: prefix `slice-id/step-` + list from frontmatter `steps` field

**Cross-reference validation on write:**
1. Every `depends_on.id` must resolve to an existing artifact (Arc, Phase, Slice, or Step).
2. Every parent reference must exist before a child can be created.
3. Broken references (deleted target) trigger a health warning from `validate_consistency()`.

### 8.3 What Happens on Broken References

| Scenario | Detection | Resolution |
|----------|-----------|------------|
| `depends_on` target deleted | `validate_consistency()` warns | Agent must update `depends_on` or restore target |
| Parent Phase deleted, child Slice remains | `validate_consistency()` warns (orphan Slice) | Orphaned Slices flagged for review or adoption |
| STEP.md references a deleted PLAN.md | `validate_consistency()` warns | Agent must re-plan or update reference |
| STATE.md diverges from event store | `validate_consistency()` critical | `state build repair` triggers projector rebuild |

---

## 9. Naming Conventions

### 9.1 ID Formats

| Tier | Format | Example | Collision Domain | Insertion |
|------|--------|---------|-----------------|-----------|
| Arc | `{prefix}-{n}` or `{prefix}-{slug}` | `arc-01`, `arc-auth` | Global (project root) | No insertion — pre-planned |
| Phase | `phase-{n:02d}` | `phase-03` | Per Arc | No insertion — pre-planned |
| Slice | `slice-{n:02d}` | `slice-12` | Per Phase | Decimal: `slice-12.1` |
| Step | `step-{n:03d}` | `step-004` | Per Slice | Decimal: `step-003.1` |

**Decimal insertion rules** (gap-closure):
- `slice-12.1` — inserted between `slice-12` and `slice-13`
- `step-003.1` — inserted between `step-003` and `step-004`
- Decimal sort order: `12 < 12.1 < 12.2 < 13`
- Maximum one decimal level (no `step-003.1.1`)

### 9.2 File Naming

All artifact files use UPPERCASE names for the primary artifact at each tier:
- `ARC.md`, `PHASE.md`, `SLICE.md`, `STEP.md` — canonical definitions
- `STATE.md` — projector-rebuilt at every tier
- `DISCUSS.md`, `PLAN.md`, `VERIFY.md` — Step-phase outputs
- `EXECUTE.log` — structured execution log

Templates use `.tmpl` extension: `ARC.md.tmpl`, `PHASE.md.tmpl`, etc.

### 9.3 Path Construction

```python
def arc_dir(arc_id: str) -> Path:
    return Path(f".state/build/arcs/{arc_id}/")

def phase_dir(arc_id: str, phase_num: int) -> Path:
    return Path(f".state/build/arcs/{arc_id}/phases/phase-{phase_num:02d}/")

def slice_dir(arc_id: str, phase_num: int, slice_num: int) -> Path:
    return Path(f".state/build/arcs/{arc_id}/phases/phase-{phase_num:02d}/slices/slice-{slice_num:02d}/")

def step_dir(arc_id: str, phase_num: int, slice_num: int, step_num: int) -> Path:
    return Path(f".state/build/arcs/{arc_id}/phases/phase-{phase_num:02d}/slices/slice-{slice_num:02d}/steps/step-{step_num:03d}/")
```

---

## 10. MCP Tool Scoping

### 10.1 Tool Naming Convention

Tools in `state-build` MCP server follow the pattern `state_build__{tier}_{action}`:

| Tier | Tool Prefix | Example Tools |
|------|-----------|---------------|
| Arc | `state_build__arc_` | `arc_new`, `arc_plan`, `arc_retire`, `arc_roadmap` |
| Phase | `state_build__phase_` | `phase_new`, `phase_plan`, `phase_start`, `phase_verify`, `phase_complete` |
| Slice | `state_build__slice_` | `slice_new`, `slice_plan`, `slice_ship`, `slice_revert`, `slice_snapshot` |
| Step | `state_build__step_` | `step_discuss`, `step_plan`, `step_execute`, `step_verify`, `step_advance`, `step_block`, `step_snapshot`, `step_revert` |
| Cross-tier | `state_build__` (no tier prefix) | `dag_show`, `progress`, `stats`, `health`, `forensics`, `decision_record`, `intel`, `map_codebase` |

### 10.2 Tier Scoping

Each tool validates the current scope before executing:

```python
def validate_tier_scope(requested_tier: str, current_context: dict) -> None:
    """Ensure the tool is being called at the right tier.
    
    Example: state_build__step_plan must be called when a Step is active.
    Calling it without an active Step context raises an error.
    """
    if requested_tier == "step" and not current_context.get("active_step_id"):
        raise TierScopeError("No active Step. Use 'state build step select <id>' first.")
```

- **Arc tools** require an Arc to be selected (or create one).
- **Phase tools** require a parent Arc context.
- **Slice tools** require a parent Phase context.
- **Step tools** require a parent Slice context.

### 10.3 Context Propagation

The active context (Arc/Phase/Slice/Step IDs) is propagated through:
1. `shell.env` hook sets `STATE_ARC_ID`, `STATE_PHASE_ID`, `STATE_SLICE_ID`, `STATE_STEP_ID`
2. `experimental.chat.system.transform` hook prepends the active hierarchy path to the system prompt
3. MCP tools read context from daemon HTTP (`GET /context/active`) if env vars are absent

---

## 11. TUI Integration

### 11.1 Hierarchy Visualization (Sidebar)

The plugin's `sidebar_content` slot renders the four-tier tree:

```
┌─ Arcs ──────────────────────────┐
│ ✓ arc-01: Kernel & Event Store   │
│ ▶ arc-02: Auth System            │
│   ✓ phase-01: OAuth Providers    │
│   ○ phase-02: Token Refresh      │
│ ▶ arc-03: Provider Routing       │
└──────────────────────────────────┘
```

Each tier is expandable/collapsible. Status icons:
- `✓` (green) — shipped
- `●` (blue) — in_progress / executing
- `○` (gray) — planned / idle
- `⚠` (yellow) — blocked
- `✗` (red) — abandoned / failed

### 11.2 DAG Viewer (Existing, Extended)

The existing DAG viewer (`state.dag`) route renders all four tiers with hierarchical grouping:

```
arc-01 ──────────────► arc-02 ──────────────► arc-03
 │                      │                      │
 ├─ phase-01 ──► phase-02                     │
 │    │                                       │
 │    ├─ slice-11 ──► slice-12               │
 │    │    │            │                     │
 │    │    ├─ step-001   ├─ step-001         │
 │    │    ├─ step-002   ├─ step-002         │
 │    │    └─ step-003   └─ step-003         │
 │    │                                       │
 │    └─ slice-13                            │
 │                                           │
 └─ phase-02 ─────────────────────────────────┘
```

### 11.3 Statusline

The statusline (`sidebar_footer` slot) shows:
```
build | arc-02:auth | phase-01:oauth | slice-12:anthropic | step-004:verify | DONE
```

---

## 12. Tracking File Consistency Model

### 12.1 The Golden Rule

> **STATE.md at every tier is a projector output, NEVER agent-written.**

The daemon's CQRS projector (`projector.py`) owns STATE.md. On every event append, the projector updates the relevant cache table (SQLite) AND optionally triggers a STATE.md file rewrite. On daemon startup, `rebuild_all()` wipes and rewrites EVERY STATE.md file from the event stream.

### 12.2 Agent Writes vs Projector Writes

| File | Written By | When | Content |
|------|-----------|------|---------|
| ARC.md | Agent (`state build arc new`) | Creation + manual update | Scope, goal, success criteria |
| PHASE.md | Agent (`state build phase new`) | Creation + manual update | Goal, slices, verify_rollup |
| SLICE.md | Agent (`state build slice new`) | Creation + manual update | Goal, steps, depends_on |
| STEP.md | Agent (`state build step plan`) | Creation + manual update | Goal, verify_contract, depends_on |
| DISCUSS.md | Agent (`state build step discuss`) | Discuss phase output | Gray-area decisions, approach |
| PLAN.md | Agent (`state build step plan`) | Plan phase output | Task decomposition, test plan |
| VERIFY.md | Agent/Verifier (`state build step verify`) | Verify phase output | Pass/fail + evidence |
| **STATE.md** | **Projector (daemon)** | **Every event append + startup** | **State projection from events** |
| EXECUTE.log | Agent (structured) | Execute phase | Per-subtask commit hashes |
| index.json | Projector (daemon) | Same as STATE.md | Machine-readable artifact index |

### 12.3 Health Validation

```python
async def validate_consistency() -> list[ConsistencyWarning]:
    """Validate that STATE.md files reflect event-store truth.
    
    Checks:
    1. Every STATE.md exists at its expected path
    2. STATE.md status matches the event-derived state
    3. No orphaned artifacts (files without events)
    4. No phantom artifacts (events without files)
    5. Parent-child counts match (e.g., ARC.md says 3 phases, events show 3 phases)
    """
```

Run on daemon startup and on-demand via `state build health`.

---

## 13. Open Design Questions

These are deliberately left open for the discuss-phase (v40 HANDOFF.md §"Key Questions for Discuss-Phase"):

1. **Arc → Phase dependency:** Can an Arc contain Phases that depend on Phases in another Arc? (Recommendation: YES — cross-Arc Phase dependencies via fully-qualified IDs. This enables "Arc A provides foundation that Arc B's Phase builds on.")

2. **Arc planning depth:** Is ARC.md just a list of Phases with goals, or does it include the dependency graph between Phases? (Recommendation: ARC.md lists Phases + goals + `depends_on` for cross-Arc edges. The Phase-level DAG lives in each PHASE.md's `slices` + `depends_on` fields.)

3. **Phase planning depth:** Does PHASE.md include the DAG of Slices? (Recommendation: YES — `slices` lists all Slices, `depends_on` edges live in each SLICE.md. The Phase plan is the union of its Slice DAGs.)

4. **Slice dependency DAG boundary:** Can Slices depend on Slices in other Phases? (Recommendation: YES — fully-qualified Slice IDs. This enables cross-Phase integration.)

5. **Step serialization:** Always serial within a Slice? (Recommendation: YES. If parallel Steps needed, split into separate Slices. This is the cleanest model and matches the worktree-per-Slice design.)

6. **Decimal insertions:** Supported at Slice and Step level. (Recommendation: YES — `slice-12.1` and `step-003.1`. No decimal at Arc/Phase.)

7. **STATE.md at every tier:** Yes — all four tiers. (Recommendation: YES. Storage is negligible; utility for health validation is high. The projector rebuilds all STATE.md files in <1 second for a typical project of 100+ Phases.)

8. **Artifact immutability:** STEP.md immutable after execution begins? (Recommendation: `verify_contract` is immutable after execution begins. Goal and description can be updated. ARC.md/PHASE.md/SLICE.md can be updated at any time; the projector will reflect changes in STATE.md.)

9. **Naming style:** Sequential numeric IDs with decimal insertion. (Recommendation: `arc-{n}`, `phase-{n:02d}`, `slice-{n:02d}`, `step-{n:03d}`. Human-readable slugs can be added as a `title` field, not the ID.)

10. **Cross-reference format:** Hierarchical slash-delimited IDs. (Recommendation: `arc-01/phase-03/slice-12/step-004` — unambiguous, machine-parseable, human-scannable.)

---

## 14. Sources

### Primary (code read directly)

- `src/state_core/schema.py` — 34+ event types, aggregate definitions, mode enforcement
- `src/state_core/projector.py` — CQRS projection engine (19 handlers, 3 cache tables)
- `src/state_core/events.py` — Event store API (append, read_stream, post-commit callbacks)
- `src/state_build/kernel.py` — StepMachine skeleton (existing states)
- `src/state_core/scheduler.py` — DAG scheduler (frontier, topo_sort, cycle detection, priority inversion, deadlock detection)
- `src/state_core/worktree.py` — WorktreeService protocol
- `.planning/PROJECT.md` — Cardinal rules, constraints, decisions
- `.planning/milestones/v40/HANDOFF.md` — Milestone scope, key questions, artifact catalog template
- `.planning/research/ARCHITECTURE.md` — Existing architecture (6 components, 9 hooks, 28+ events)
- `.planning/research/SCHEDULER_ARCHITECTURE.md` — (if exists — DAG details)

### GSD patterns studied

- `state-inputs/get-shit-done/bin/lib/artifacts.cjs` — Artifact registry pattern (exact-match + pattern-match)
- `state-inputs/get-shit-done/bin/lib/state.cjs` — STATE.md operations
- `state-inputs/get-shit-done/bin/lib/verify.cjs` — Health check patterns (19 warning codes)
- `state-inputs/get-shit-done/bin/lib/frontmatter.cjs` — YAML frontmatter handling

### Architecture principles

- CQRS/Event Sourcing pattern — Greg Young, "CQRS Documents"
- Aggregate design — Vaughn Vernon, "Implementing Domain-Driven Design" (aggregate boundaries per tier)
- Projection pattern — SQLite cache tables as read-optimized projections of event stream
