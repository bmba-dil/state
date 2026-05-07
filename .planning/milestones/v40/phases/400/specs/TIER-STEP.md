# Tier Specification: Step

## Role in Hierarchy

Step is the **smallest unit of work** in the four-tier hierarchy — a single design→plan→run→verify
cycle. Each Step represents one coherent task that can be completed within a single agent session.
Steps are the only tier that owns the full workflow cycle; all higher tiers (Slice, Stage, Arc)
are scoping and verification containers.

**Critical:** Steps are NOT scheduler-dispatched (D-11). They run SERIALLY within a single agent
session. The agent is responsible for: organizing work, delegating to subagents (if needed),
synthesizing work, moving to next steps, finalizing work, and initiating verification. The
scheduler dispatches Slices; within a Slice, the agent sequences Steps.

Steps are markdown FILES (`step1PLAN.md`, `step2PLAN.md`...) within the parent Slice folder —
NOT subdirectories (D-04). The Slice is the terminal container. Steps do NOT have their
own directories or their own `depends_on` field — intra-Slice ordering is the agent's
responsibility (D-11). Step-level state is tracked via the event store (SQLite authoritative)
and projected into the parent Slice's STATE.md.

**Sub-step support (v41+):** Steps CAN contain sub-steps (1.1, 1.2, 1.3) within a single file.
Sub-step parallelism is an agent-internal decision — no scheduler involvement. This is a v41+
harness concern, documented here for design contract completeness.

## State Machine

```
                    ┌─────────┐
     created        │  idle   │
   ───────────────► │         │─────────────────────────────────────────────┐
                    └────┬────┘                                             │
                         │ state.step.designed                              │
                         │ guard: agent invokes design                      │
                         ▼                                                  │
                    ┌───────────┐                                           │
              ┌────►│ designing │                                           │
              │     │           │                                           │
              │     └─────┬─────┘                                           │
              │           │ state.step.planned                              │
              │           │ guard: DESIGN.md completed                      │
              │           ▼                                                  │
              │     ┌──────────┐                                            │
              │     │ planning │◄── state.step.planned                       │
              │     │          │    guard: design skipped (simple work)      │
              │     └────┬─────┘    (idle → planning direct path)            │
              │          │ state.step.ran                                    │
              │          │ guard: PLAN.md completed                          │
              │          ▼                                                   │
              │     ┌───────────┐                                            │
              │     │  running  │◄──────────────────────────────┐           │
              │     │           │                               │           │
              │     └─────┬─────┘                               │           │
              │           │ state.step.verify_started            │           │
              │           │ guard: all sub-steps complete        │           │
              │           ▼                                      │           │
              │     ┌───────────┐                                │           │
              │     │ verifying │────────────────────────────────┤           │
              │     │           │ state.step.verify_failed       │           │
              │     └──┬───┬────┘ guard: fix needed, loop back   │           │
              │        │   │                                     │           │
              │  pass  │   │ fail                                │           │
              │        ▼   └─────────────────────────────────────┘           │
              │     ┌──────────┐                                            │
              │     │   done   │                                            │
              │     │          │                                            │
              │     └──────────┘                                            │
              │                                                              │
              │     state.step.blocked                                       │
              │     guard: blocked_reason set                                │
              │     ▼                                                        │
              │ ┌──────────────┐                                            │
              │ │   blocked    │                                            │
              │ │              │                                            │
              │ └──────┬───────┘                                            │
              │        │ state.step.unblocked                                │
              │        │ guard: blocking condition resolved (D-15)           │
              │        └────────────────────────────────────────────────────┘
              │
              │ state.step.abandoned
              │ guard: explicit abandon
              ▼
        ┌──────────────┐
        │  abandoned   │
        │              │
        └──────────────┘

  Step is the ONLY tier with a count limit. The number of Steps per Slice is bounded by
  the context token limit of a single agent session. When planning a Slice, the Stage
  estimates how many Steps can fully execute end-to-end within the available context window,
  and that becomes the Slice's Step count. This means Stages with broad CRIT.md scope
  naturally produce many Slices, each with a manageable number of Steps.

  Forward states: idle, designing, planning, running, verifying, done = 6
  Exit states: blocked, abandoned = 2
  Total states: 8 (the Step machine's internal state count; distinct from Step-per-Slice count)

  Key design decisions:
  - "designing" (NOT "discussing") per D-03
  - "running" (NOT "executing") per D-03
  - idle → designing: agent invokes design (default path)
  - idle → planning: design skipped by agent for simple work (direct path)
  - verifying → running: verify failed, loop back for fixes
  - blocked → running: blocking condition resolved, resume (D-15)
```

## State Transition Table

| From | To | Event Trigger | Guard Condition |
|------|----|---------------|-----------------|
| `idle` | `designing` | `state.step.designed` | Step created, agent invokes design |
| `designing` | `planning` | `state.step.planned` | DESIGN.md completed |
| `idle` | `planning` | `state.step.planned` | Design skipped by agent (simple work, no research needed) |
| `planning` | `running` | `state.step.ran` | PLAN.md completed |
| `running` | `verifying` | `state.step.verify_started` | All sub-steps complete |
| `verifying` | `done` | `state.step.verify_passed` | VERIFICATION.md passes |
| `verifying` | `running` | `state.step.verify_failed` | Fix needed; loop back to running |
| `*` | `blocked` | `state.step.blocked` | `blocked_reason` set in frontmatter |
| `blocked` | `running` | `state.step.unblocked` | Blocking condition resolved; resume running (D-15) |
| `*` | `abandoned` | `state.step.abandoned` | Explicit abandon command |

**Design skip path:** Steps for simple work (e.g., "add a type annotation", "fix a typo") can skip the `designing` state entirely by transitioning directly from `idle` → `planning`. This is an agent decision — the agent determines whether design is needed.

**Verify loop:** If verification fails (`state.step.verify_failed`), the Step loops back to `running` for fixes, then re-enters `verifying`. This loop can repeat until verification passes.

**Blocked semantics (D-15):** A blocked Step stays blocked indefinitely until its blocking condition resolves. The `blocked_reason` in frontmatter documents what blocked it. When unblocked, the Step resumes at `running` (not its prior state) because the agent needs to re-establish execution context.

## Owned Artifacts

Step tracking files (`step1PLAN.md` through `stepNPLAN.md`) live in the parent Slice folder per
D-04. The Step itself has NO dedicated directory. Step-level data is tracked via the event store
(SQLite authoritative) and projected into the parent Slice's STATE.md.

| Artifact | Purpose | Schema Owner |
|----------|---------|--------------|
| stepNPLAN.md | Run-tracking file for a single Step — flat markdown file in parent Slice folder. Contains step_number, title, goal, plan_summary, verification_criteria as frontmatter. Generated by the run phase | Agent |

**What the Step does NOT own:**
- No dedicated directory (Steps are flat files per D-04)
- No STATE.md (Step state is projected into parent Slice STATE.md)
- No DESIGN.md or VERIFICATION.md of its own (these are Slice-level artifacts per D-06)
- No `depends_on` field (Steps run serial within agent session per D-11)

## Frontmatter Fields

| Field | Type | Owner | Required | Description |
|-------|------|-------|----------|-------------|
| `step_number` | `int` | Agent | Yes | Sequential Step number within the parent Slice. No leading zeros per D-01. Example: `1`, `5`, `12` |
| `title` | `str` | Agent | Yes | Human-readable name for the Step. Example: "Implement JWT token verification" |
| `goal` | `str` | Agent | Yes | One-line outcome describing what this Step delivers |
| `plan_summary` | `str` | Agent | Yes | Brief summary of the plan (how the Step will be executed) |
| `verification_criteria` | `list[str]` | Agent | Yes | Criteria that must pass for this Step to be `done` |
| `status` | `Literal["idle", "designing", "planning", "running", "verifying", "done", "blocked", "abandoned"]` | Projector | Yes | Current state, computed from event stream. Uses D-03 renamed values. Default: `"idle"` |
| `completed_at` | `str \| None` | Projector | No | ISO 8601 timestamp when Step reached `done`. Default: `null` |
| `blocked_reason` | `str \| None` | Agent | No | Reason the Step is blocked (D-15). Agent writes when entering `blocked`. Default: `null` |

**Field ownership note:** Every field is classified EXACTLY ONCE as Agent or Projector. Agent never writes projector-owned fields (`status`, `completed_at`). Projector never writes agent-owned fields (`step_number`, `title`, `goal`, `plan_summary`, `verification_criteria`, `blocked_reason`).

**ID format:** `step-{n}` — dash-prefix, lowercase prefix, no leading zeros per D-01. Example: `step-5`. Steps do NOT get slugs — they are terminal units identified by number within their parent Slice.

**Status values use D-03 renamed states:** `idle`, `designing` (was `discussing`), `planning`, `running` (was `executing`), `verifying`, `done`, `blocked`, `abandoned`.

## Events

| Event Type | Trigger | State Transition | Description |
|-----------|---------|------------------|-------------|
| `state.step.created` | Run phase generates Step tracking file | none → `idle` | Step aggregate created, enters initial state |
| `state.step.designed` | Agent completes design for the Step | `idle` → `designing` | Design phase initiated for this Step |
| `state.step.planned` | DESIGN.md completed (or design skipped) | `designing` → `planning` or `idle` → `planning` | Plan ready for execution |
| `state.step.ran` | PLAN.md completed, agent begins running | `planning` → `running` | Step execution begins |
| `state.step.verify_started` | All sub-steps complete | `running` → `verifying` | Verification phase initiated |
| `state.step.verify_passed` | VERIFICATION.md passes | `verifying` → `done` | Step complete — all criteria satisfied |
| `state.step.verify_failed` | Verification fails | `verifying` → `running` | Loop back for fixes |
| `state.step.advanced` | Composite advancement signal | — (no direct state change) | Notifies scheduler of progress (D-19 composite) |
| `state.step.blocked` | External condition blocks Step | `*` → `blocked` | `blocked_reason` set in frontmatter |
| `state.step.unblocked` | Blocking condition resolved | `blocked` → `running` | Step resumes execution (D-15) |
| `state.step.abandoned` | Explicit abandon command | `*` → `abandoned` | Step descoped — terminal exit |

### Event Name Migration (D-03 rename)

| Pre-Rename (existing code) | Post-Rename (v40 design) | Notes |
|---|---|---|
| `state.step.discussed` | `state.step.designed` | "discuss" → "design" per D-03 |
| `state.step.planned` | `state.step.planned` | Unchanged |
| `state.step.executed` | `state.step.ran` | "execute" → "run" per D-03 |
| `state.step.verify_started` | `state.step.verify_started` | Unchanged |
| `state.step.verify_passed` | `state.step.verify_passed` | Unchanged |
| `state.step.verify_failed` | `state.step.verify_failed` | Unchanged |
| `state.step.advanced` | `state.step.advanced` | Unchanged |
| `state.step.blocked` | `state.step.blocked` | Unchanged |
| `state.step.snapshotted` | `state.step.snapshotted` | Unchanged (snapshot events unchanged by rename) |
| `state.step.reverted` | `state.step.reverted` | Unchanged (revert events unchanged by rename) |
| `StepDiscussedData` (class) | `StepDesignedData` | Class rename (v41+) |
| `StepExecutedData` (class) | `StepRanData` | Class rename (v41+) |
| `"discussing"` (StepState) | `"designing"` | State rename in StepMachine (v41+) |
| `"executing"` (StepState) | `"running"` | State rename in StepMachine (v41+) |

Existing code in `src/state_core/schema.py` defines `STEP_EVENT_TYPES` with `state.step.discussed` and `state.step.executed` literals. The `StepMachine` skeleton in `src/state_build/kernel.py` uses `"discussing"` and `"executing"` states. Migration to the renamed states and events is a design contract documented here but implemented in v41+.

## Cross-Tier Relationships

- **Parent of:** None — Step is the leaf tier. It has no children.
- **Sibling of:** Steps within the same Slice run SERIALLY — not in parallel (D-11). The agent sequences Steps, so there are no Step-to-Step dependency edges. Steps do NOT have a `depends_on` field; intra-Slice ordering is the agent's responsibility.
- **Child of:** ONE Slice (parent). Every Step belongs to exactly one Slice. The Step tracking file lives in the parent Slice folder.
- **ID format:** `step-{n}` — dash-prefix, no leading zeros (D-01). Example: `step-5`. Steps do NOT get slugs (terminal unit).
- **Aggregate ID (internal):** `arc-{n}/stage-{n}/slice-{n}/step-{n}` — hierarchical, slash-delimited. Example: `arc-45/stage-22/slice-12/step-5`
- **File path:** `.state/build/arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/step{n}PLAN.md` — flat file within the parent Slice directory (D-04)
- **Scheduler relationship:** Steps are NOT dispatched by the scheduler (D-11). The scheduler dispatches Slices; the agent manages Steps within the Slice session. Step events (`state.step.advanced`) notify the scheduler of progress for composite state computation (D-19), but do not trigger scheduler dispatch.
