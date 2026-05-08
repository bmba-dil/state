# Tier Specification: Slice

## Role in Hierarchy

Slice is the **terminal container tier** — the work unit that gets its own worktree and is the
finest-grained scheduler-dispatched unit. One Slice maps to one coherent unit of work
(e.g., "add JWT auth", "migrate to litellm 2.0"). The Slice folder is the on-disk container
for ALL workflow artifacts: DESIGN.md, RESEARCH.md, step1PLAN.md through stepNPLAN.md,
VERIFICATION.md, SUMMARY.md, and STATE.md.

**Critical:** Steps are markdown FILES (`step1PLAN.md`, `step2PLAN.md`...) within the Slice
folder — NOT subdirectories (D-04). The Slice folder is the terminal container; no further
directory nesting for Steps. Steps CAN contain sub-steps (1.1, 1.2, 1.3) within a single file,
but this is a v41+ harness concern. The Slice is the last tier with its own worktree and
directory — everything below it is flat files.

Slices depend on other Slices within the SAME Stage only (D-10 — same-parent-only constraint).
Decimal insertions (slice-12.1, slice-12.2) are supported at the Slice level per D-16.

## State Machine

```
                         ┌─────────────┐
         created         │   planned   │────────────────────────────────────────┐
       ────────────────► │             │                                        │
                         └──────┬──────┘                                        │
                                │ state.slice.worktree_ready                     │ state.slice.deferred
                                │ guard: worktree bootstrap completes            │ guard: deferred_reason set (D-14)
                                ▼                                                ▼
                         ┌────────────────┐                              ┌──────────────┐
                         │ worktree_ready │                              │   deferred   │
                         │                │                              │              │
                         └───────┬────────┘                              └──────┬───────┘
                                 │ state.slice.started                          │
                                 │ guard: ≥1 child Step is idle                 │ state.slice.undeferred
                                 ▼                                               │ guard: manual un-defer
                         ┌─────────────┐                                        │
                         │ in_progress │◄───────────────────────────────────────┘
                         │             │
                         └──────┬──────┘──────────────────────────────┐
                                │ state.slice.shipped                   │ state.slice.reverted
                                │ guard: ALL child Steps are done +     │ guard: explicit revert command
                                │ VERIFICATION.md passes                │ (worktree destroy + rebuild)
                                ▼                                       ▼
                         ┌─────────────┐                        ┌──────────────┐
                         │   shipped   │                        │   reverted   │
                         │             │                        │              │
                         └─────────────┘                        └──────┬───────┘
                                                                      │
  ┌──────────────┐                                                    │ state.slice.worktree_ready
  │   blocked    │◄── state.slice.blocked (abandon-cascade D-13)       │ guard: worktree rebuild
  │              │                                                    ▼
  └──────┬───────┘                                             ┌─────────────┐
         │                                                     │   planned   │
         │ state.slice.unblocked                                │             │
         │ guard: dep resolved, unblock                        └─────────────┘
         ▼
  (back to prior state)

  Forward states: planned, worktree_ready, in_progress, shipped = 4
  Alternative/exit states: reverted, blocked, deferred

  Slices are limitless — there is no cap on the number of Slices per Stage. Each
  Slice scope is determined by its parent Stage's CRIT.md.

  The only count constraint at the Slice level is the number of child Steps:
  a Slice is planned to contain only enough Steps to fill the context token limit
  of a single agent session end-to-end. Each Stage plans its Slices accordingly,
  producing a potentially large number of Slices depending on the Stage's CRIT scope.

  Blocked entered via: (1) abandon-cascade from dependency Slice (D-13)
                       (2) explicit block with blocked_reason in frontmatter
  Reverted: terminal alternative — worktree destroyed, Slice returns to planned
  Deferred: soft-done — dependents unblock with deferred_dep flag (D-14)
```

## State Transition Table

| From | To | Event Trigger | Guard Condition |
|------|----|---------------|-----------------|
| `planned` | `worktree_ready` | `state.slice.worktree_ready` | Worktree bootstrap completes (git worktree create) |
| `worktree_ready` | `in_progress` | `state.slice.started` | ≥1 child Step is `idle` |
| `in_progress` | `shipped` | `state.slice.shipped` | ALL child Steps are `done` + VERIFICATION.md passes (D-19 composite) |
| `planned` | `deferred` | `state.slice.deferred` | `deferred_reason` set in frontmatter (D-14) |
| `deferred` | `planned` | `state.slice.undeferred` | Manual un-defer command |
| `*` | `reverted` | `state.slice.reverted` | Explicit revert command; worktree destroyed + rebuilt → planned |
| `reverted` | `planned` | `state.slice.worktree_ready` | Worktree rebuild completes (after revert destroys old worktree) |
| `*` | `blocked` | `state.slice.blocked` | Contains `blocked_reason` in frontmatter. Entered via abandon-cascade (D-13) or explicit block |
| `blocked` | `in_progress` | `state.slice.unblocked` | Blocking dependency resolved; unblocked (D-15) |
| `in_progress` → `*` | `blocked` | `state.slice.blocked` | Abandon-cascade: a dependency Slice was abandoned (D-13) |

**Deferment semantics (D-14):** When a Slice is `deferred`, its dependents treat it as soft-done — they unblock and proceed with a `deferred_dep` flag. The `deferred_reason` frontmatter field documents why the Slice was deferred. The deferred Slice itself can later be `undeferred` back to `planned`.

**Blocked semantics (D-15):** Blocked state has NO timeout. A Slice stays blocked indefinitely until its dependencies resolve or the user defers the blocker. The `blocked_reason` in frontmatter explains the blocking condition.

**Composite state note (D-19):** The Slice `shipped` state is entered when the projector detects ALL child Steps are `done` AND the Slice's VERIFICATION.md passes. This is a composite condition checked by the projector — the Slice does not automatically ship just because its Steps are done.

## Owned Artifacts

| Artifact | Purpose | Schema Owner |
|----------|---------|--------------|
| SLICE.md | Slice definition document with frontmatter fields (id, title, goal, success_criteria, stage_id, depends_on) | Agent |
| DESIGN.md | Design phase output — explores the problem space and proposes approach (D-03, D-06) | Agent |
| RESEARCH.md | Research phase output — evaluates libraries, patterns, and alternatives (D-06) | Agent |
| step1PLAN.md | Run-tracking file for Step 1 — flat file within Slice folder, NOT subdirectory (D-04) | Agent |
| step2PLAN.md | Run-tracking file for Step 2 | Agent |
| ... | ... | Agent |
| stepNPLAN.md | Run-tracking file for Step N | Agent |
| VERIFICATION.md | Verify phase output — test results, UAT pass/fail, verification evidence | Agent |
| SUMMARY.md | Summary phase output — plan completion documentation, decisions, deviations | Agent |
| STATE.md | State projection rebuilt by the projector from event store — current status, Step counts, worktree info, timestamps | Projector |

**Optional sub-flow artifacts (v41+):**
| Artifact | Purpose | Schema Owner |
|----------|---------|--------------|
| REVIEW.md | Code review sub-flow output | Agent |
| LOCK-IN.md | Lock-in sub-flow output (finalized scope) | Agent |
| SHIP.md | Ship sub-flow output (release checklist) | Agent |

**Workflow order (D-06):** design → research → run (generates step1PLAN.md..stepNPLAN.md) → verify → summary → optional review/lock-in/ship sub-flows.

**Step file naming:** `step1PLAN.md`, `step2PLAN.md`, ... `stepNPLAN.md` — no zero-padding, matches D-01 no-leading-zeros convention. Each step tracking file is a flat markdown file within the Slice folder. Steps never have their own subdirectory.

## Frontmatter Fields

| Field | Type | Owner | Required | Description |
|-------|------|-------|----------|-------------|
| `id` | `str` | Agent | Yes | Slice identifier: `slice-{n}` — dash-prefix, no leading zeros per D-01. Example: `slice-12` |
| `title` | `str` | Agent | Yes | Human-readable name. Example: "Anthropic OAuth Byte-for-Byte" |
| `goal` | `str` | Agent | Yes | One-line outcome describing what the Slice delivers |
| `success_criteria` | `list[str]` | Agent | Yes | Measurable outcomes that define Slice completion |
| `stage_id` | `str` | Agent | Yes | Parent Stage identifier. Example: `"stage-22"`. Links Slice to its parent Stage. Every Slice belongs to exactly ONE Stage |
| `depends_on` | `list[dict]` | Agent | No | Dependency edges to sibling Slices within the SAME Stage (D-10 same-parent-only). Format per D-12: `[{id: "slice-10", edge: "blocks"}, {id: "slice-11", edge: "soft"}]`. Edge types: `blocks`, `soft`, `data`. Default: `[]` |
| `status` | `Literal["planned", "worktree_ready", "in_progress", "shipped", "reverted", "blocked", "deferred"]` | Projector | Yes | Current state, computed from event stream. Default: `"planned"` |
| `step_count` | `int` | Projector | No | Number of child Steps. Default: `0` |
| `completed_step_count` | `int` | Projector | No | Number of child Steps in `done` state. Default: `0` |
| `worktree_dir` | `str \| None` | Projector | No | Absolute path to the Slice's git worktree directory. Set at `worktree_ready` transition. Default: `null` |
| `worktree_branch` | `str \| None` | Projector | No | Git branch name for the Slice's worktree. Set at `worktree_ready` transition. Default: `null` |
| `completed_at` | `str \| None` | Projector | No | ISO 8601 timestamp when Slice reached `shipped`. Default: `null` |
| `deferred_reason` | `str \| None` | Agent | No | Reason the Slice was deferred (D-14). Agent writes when deferring. Default: `null` |

**Field ownership note:** Every field is classified EXACTLY ONCE as Agent or Projector. Agent never writes projector-owned fields (`status`, `step_count`, `completed_step_count`, `worktree_dir`, `worktree_branch`, `completed_at`). Projector never writes agent-owned fields (`id`, `title`, `goal`, `success_criteria`, `stage_id`, `depends_on`, `deferred_reason`). The `depends_on` field uses the key `edge` (not `kind`) per D-12.

**ID format:** `slice-{n}` — dash-prefix, lowercase prefix, no leading zeros (D-01). Slugs for display: `slice-{n}-{slug}` (D-02). ID resolution works with or without the slug. Example: `slice-12-anthropic-oauth/` directory — `slice-12` is the stable ID.

**Decimal insertions (D-16):** Single decimal level supported: `slice-12.1`, `slice-12.354`. No cap on the decimal number. No double decimals (`12.1.2` rejected). Used for gap-closure and unexpected problems without renumbering existing Slices.

## Events

| Event Type | Trigger | State Transition | Description |
|-----------|---------|------------------|-------------|
| `state.slice.created` | `/state-new slice` | none → `planned` | Slice aggregate created, enters initial state |
| `state.slice.worktree_ready` | Worktree bootstrap completes | `planned` → `worktree_ready` | Git worktree created, ready for work |
| `state.slice.started` | Agent begins work on first Step | `worktree_ready` → `in_progress` | ≥1 child Step is `idle` |
| `state.slice.shipped` | All Steps done + VERIFICATION.md passes | `in_progress` → `shipped` | Composite check (D-19): ALL Steps `done` + verification passes |
| `state.slice.reverted` | Explicit revert command | `*` → `reverted` | Worktree destroyed; Slice returns to planned state on rebuild |
| `state.slice.blocked` | Abandon-cascade (D-13) or explicit block | `*` → `blocked` | `blocked_reason` set in frontmatter; dependent Slices blocked |
| `state.slice.unblocked` | Blocking dependency resolved | `blocked` → `in_progress` | Slice resumes from prior state (D-15) |
| `state.slice.deferred` | Manual defer command | `planned` → `deferred` | `deferred_reason` set; dependents unblock with `deferred_dep` flag (D-14) |
| `state.slice.undeferred` | Manual un-defer command | `deferred` → `planned` | Slice returns to planned; dependents re-evaluated |
| `state.slice.updated` | Agent edits SLICE.md frontmatter | — (no state change) | Frontmatter or scope update, does not change state |

## Cross-Tier Relationships

- **Parent of:** Steps — tracked as flat files (step1PLAN.md..stepNPLAN.md) within the Slice folder. The Slice is the terminal container; Steps have no directories (D-04).
- **Sibling of:** Other Slices within the SAME Stage — dependencies via `depends_on` frontmatter field with edge types per D-12. Same-parent-only constraint (D-10): Slices can only depend on sibling Slices in the same Stage.
- **Child of:** ONE Stage (parent). Every Slice belongs to exactly one Stage, identified by `stage_id` in frontmatter.
- **ID format:** `slice-{n}` (D-01). Example: `slice-12`
- **Slug format:** `slice-{n}-{slug}` (D-02). Example: `slice-12-anthropic-oauth/`
- **Decimal IDs:** `slice-{n}.{d}` (D-16). Example: `slice-12.1`
- **Aggregate ID (internal):** `arc-{n}/stage-{n}/slice-{n}` — hierarchical, slash-delimited. Example: `arc-45/stage-22/slice-12`
- **Directory path:** `.state/build/arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/` containing SLICE.md, DESIGN.md, RESEARCH.md, step1PLAN.md..stepNPLAN.md, VERIFICATION.md, SUMMARY.md, STATE.md, and the git worktree
- **Worktree:** One per Slice, created at the `worktree_ready` transition. The worktree lives in the Slice directory and is used for all Step execution within the Slice.

---

## v41 Amendment

**Amended:** Phase 402 (v41 milestone — Slice-Cycle & Context Window Spec)
**Cause:** SLC-07 — Slice-owns-cycle correction; v40 cycle-ownership ambiguity is resolved canonically in v41.
**Canonical successor:** [`.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md)

### Prior model (v40)

TIER-SLICE.md (v40) defined Slice as the terminal container tier and listed DESIGN.md / RESEARCH.md / step1PLAN.md..stepNPLAN.md / VERIFICATION.md / SUMMARY.md as owned artifacts under a `Workflow order (D-06): design → research → run → verify → summary` shape. Cycle ownership between Slice and Step was implicit — v40 D-04 already constrained Steps to flat files, but no doc explicitly said the four-stage cycle is owned by Slice.

### Canonical model (v41)

Slice owns the four-stage cycle: **design-slice → research-slice → run-slice → verify-slice**. Step is a leaf artifact (`stepNPLAN.md`, `stepNSUMMARY.md`) consumed by run-slice. The Slice cycle terms and the canonical Slice folder layout (with producer-stage mapping) are defined in [`SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md). The v41 vocabulary table reconciles v41 REQUIREMENTS' `discuss-slice/plan-slice/execute-slice` to the canonical `design-slice/research-slice/run-slice/verify-slice` terms.

### Effect on this document

TIER-SLICE.md's `## State Machine`, `## Owned Artifacts`, and `## Frontmatter Fields` sections remain authoritative for Slice FSM and frontmatter shape. The `Workflow order (D-06)` line is forward-pointed to SLICE-CYCLE.md for the canonical four-stage terminology and per-stage owner/inputs/outputs.

### Mode isolation

All v41-introduced events remain build-mode only (`state.slice.*`, `compaction.*` prefixes). Teach-mode harness is v47 scope.

*Original v40 spec text above this amendment block is untouched. This amendment is a published correction, appended per Phase 402 convention (no in-line strikethroughs).*
