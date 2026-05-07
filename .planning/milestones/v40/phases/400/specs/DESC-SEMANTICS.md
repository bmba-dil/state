# Descope and Block Semantics

> **Authoritative reference for hierarchy descope, abandon, defer, blocked, and decimal insertion rules.**
> Consumed by: Phase 401 (ART-03 immutability rules, REF-04 broken reference handling). v41+ scheduler dependency resolution and projector cascade logic.

## Overview

The four-tier hierarchy handles work that stops being active through three distinct mechanisms: **abandonment** (permanent exit with cascade-to-blocked dependents), **deferment** (temporary pause with soft-done treatment for dependents), and **blocking** (indefinite pause with no timeout, resolved when dependencies are satisfied or deferred). A fourth mechanism, **decimal insertion**, handles mid-stream gap-closure without renumbering existing work. These semantics encode the D-13, D-14, D-15, and D-16 locked decisions as formal rules, creating a deterministic framework for how the hierarchy responds to structural changes.

## Abandon Cascade (D-13)

### Trigger

When a Slice or stage is explicitly abandoned via the `/state-abandon` command or a `state.{tier}.abandoned` event. Abandonment is a permanent exit — there is no forward path from `abandoned`. Applies to Slice, Stage, and Arc tiers. Steps are also abandonable but have no cascade (Step is the leaf tier).

### Cascade Rules

#### 1. When a Slice Is Abandoned

- **Slice state:** Slice transitions to `abandoned` state — terminal, no forward path, no re-entry.
- **Dependent Slices:** ALL Slices that `depends_on[{id: "slice-X", edge: "blocks"}]` this Slice are automatically marked `blocked` with `blocked_reason: "Dependency slice-X abandoned"`. This is a cascade to `blocked`, not `abandoned` — the dependents are NOT auto-abandoned.
- **Child Steps:** Slice's child Steps are NOT auto-abandoned. They remain in their current state. Steps persist for audit trail; the agent decides whether to abandon them individually.
- **Worktree:** Slice's worktree is NOT destroyed on abandon — preserved for forensics. The worktree directory and its branch remain intact under `.state/build/arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/`.
- **Data edges:** Dependents with `edge: "data"` on the abandoned Slice are blocked — data edges require actual artifacts, and the abandoned Slice will never produce them.
- **Soft edges:** Dependents with `edge: "soft"` on the abandoned Slice are unblocked — soft edges are advisory only.

#### 2. When a Stage Is Abandoned

- **Stage state:** Stage transitions to `abandoned` state.
- **Child Slices:** ALL child Slices transition to `blocked` (NOT abandoned — manual resolution required for each). The `blocked_reason` is set to `"Parent stage-{n} abandoned"`.
- **Dependent Stages:** ALL Stages within the SAME Arc that `depends_on` this Stage transition to `blocked` with `blocked_reason: "Dependency stage-{n} abandoned"`. Same-parent-only constraint (D-10) bounds the dependency graph to within the Arc.
- **Arc:** Arc continues processing other Stages — an abandoned Stage does not block Arc advancement. The Arc's composite `in_progress` state is recomputed by the projector to exclude the abandoned Stage.
- **Data edges between Slices:** Slices with `data` edges on Slices in the abandoned Stage are `blocked` — artifact sources are gone.

#### 3. When an Arc Is Abandoned

- **Arc state:** Arc transitions to `abandoned` state.
- **Child Stages:** ALL child Stages transition to `abandoned` — direct parent cascade. The projector marks all Stage aggregates as `abandoned`.
- **Grandchild Slices:** ALL Slices within those Stages transition to `blocked` (grandchild cascade stops at Slice level). `blocked_reason: "Parent arc-{n} abandoned"`.
- **No cross-Arc cascade:** D-10 same-parent-only constraint means no other Arc can depend on this Arc. Cross-Arc deps are a deferred idea (v42+).
- **Step-level:** Steps within the abandoned Arc's Slices remain in their current state — no auto-abandon. Agent decides individually.

### No Auto-Cascade-Abandon

The cascade **always stops at `blocked`** — never auto-abandons dependents. This is defense-in-depth against cascading failures: a single abandon action cannot silently destroy dependent work. The user must explicitly:

1. **Manually abandon** each blocked dependent (one at a time), OR
2. **Defer the blocker** via D-14 deferment, which unblocks dependents with a `deferred_dep` flag, OR
3. **Re-plan to remove the dependency** by editing the `depends_on` frontmatter field to drop the abandoned dependency edge.

Each blocked dependent is surfaced to the user in STATE.md projections and DAG visualizations, ensuring no work is silently stalled.

### Blocked Reason Format

`blocked_reason` is a frontmatter field (string, projector- or agent-written) that documents why a Slice or Step is blocked. Standard formats:

| Format | Source | Example |
|--------|--------|---------|
| `"Dependency {id} abandoned"` | Abandon cascade (automatic) | `"Dependency slice-12 abandoned"` |
| `"Dependency {id} not yet shipped"` | Standard blocking (unresolved dep) | `"Dependency slice-14 not yet shipped"` |
| `"External condition: {description}"` | Manual block (agent-provided) | `"External condition: waiting for API key rotation from security team"` |

The `blocked_reason` is persisted in frontmatter for cross-session survival and is displayed in STATE.md projections. It is cleared when the Slice/Step is unblocked, but the reason is preserved in the event store as `state.{tier}.unblocked` event data for audit trail.

### Cascade Summary Table

| Action | Tier Affected | Child Effect | Dependent Effect | Worktree |
|--------|-------------|-------------|-----------------|----------|
| Abandon Slice | Slice → `abandoned` | Steps: unchanged | `blocks`-edge Slices → `blocked`; `data`-edge Slices → `blocked`; `soft`-edge Slices → unblocked | Preserved (forensics) |
| Abandon Stage | Stage → `abandoned` | Slices → `blocked` | Same-Arc Stages → `blocked`; cross-Stage Slice deps → `blocked` | All child worktrees preserved |
| Abandon Arc | Arc → `abandoned` | Stages → `abandoned` | Slices (grandchildren) → `blocked`; no cross-Arc cascade | All worktrees preserved |
| Abandon Step | Step → `abandoned` | None (leaf) | None (Steps have no dependents per D-11) | N/A (Step has no worktree) |

## Deferment Strategy (D-14)

### Purpose

Deferment is intentional descoping: "I will come back to this later." Unlike abandon (permanent exit with cascade-to-blocked), deferment preserves the work for future re-activation and allows dependents to proceed. Deferment replaces abandon for intentional descoping when the work is still valuable but not immediately needed.

### Entry

- **Event:** Slice status set to `deferred` via `state.slice.deferred` event.
- **Required field:** `deferred_reason` must be set in frontmatter (free-text, human-written by agent). This field documents why the Slice was deferred.
- **Available from:** `planned` state only. A Slice cannot be deferred from `in_progress` or `shipped`.
  - Slices mid-work (`in_progress`) must be **reverted** first (which destroys the worktree and returns to `planned`), then deferred.
  - Slices already `shipped` cannot be deferred — shipped work is permanently done.
- **Worktree:** If the Slice is in `planned` state (no worktree yet), deferment has no worktree impact. If the Slice was reverted-then-deferred, the worktree was already destroyed during revert.

### Effect on Dependents

#### Blocks-Edge Dependents (edge: "blocks")

Slices that `depends_on[{id: "slice-X", edge: "blocks"}]` a deferred Slice:

- **ARE unblocked** — the deferred Slice is treated as "soft-done."
- **Proceed with a `deferred_dep` flag** in frontmatter: `deferred_deps: ["slice-X"]`. This is a projector-owned field that accumulates deferred dependency IDs.
- The `deferred_dep` flag is **informational** — it does NOT block shipping. The dependent Slice can fully ship with deferred dependencies.
- The scheduler treats deferred deps as **satisfied** for topological ordering. The dependent Slice's `blocked` status is cleared and it transitions to its prior state.

#### Soft-Edge Dependents (edge: "soft")

When dependency has `edge: "soft"` (advisory) and the source Slice is deferred:

- Dependent is already unblocked (soft edges never block).
- The scheduler **may promote** the dependent to earlier execution in the topological order since the advisory constraint is relaxed.
- `deferred_dep` flag is still set in frontmatter for audit trail: `deferred_deps: ["slice-X"]`.
- The soft edge is effectively dropped from the scheduling constraint set for this dependency.

#### Data-Edge Dependents (edge: "data")

When dependency has `edge: "data"` (artifact-producing) and the source Slice is deferred:

- **Dependent CANNOT proceed** — data edges require actual artifact output from the source.
- Dependent **remains `blocked`** until the source is un-deferred and produces its artifacts.
- **Rationale:** "data" edges are hard because the target literally needs the source's files. A deferred Slice has produced no artifacts. Letting the dependent proceed would create broken artifact references.
- The `deferred_dep` flag is NOT set for data edges — the dependency is not satisfied.
- This is a critical integrity guard: deferment cannot bypass artifact requirements.

### Reactivation (Un-Defer)

Deferred Slices can be re-activated:

- **Event:** `state.slice.undeferred` — transitions Slice from `deferred` back to `planned`.
- **`deferred_reason` cleared:** The frontmatter field is set to `null`.
- **Dependents updated:** The projector removes this Slice's ID from all dependents' `deferred_deps` lists.
- **Blocked dependents re-evaluated:** Slices that were `blocked` due to this deferment (data-edge dependents) are re-checked — but they remain `blocked` until the un-deferred Slice actually produces artifacts.
- **Scheduler notified:** The scheduler re-evaluates the topological ordering to account for the now-active dependency.
- **Worktree:** If the Slice was deferred from `planned` (no worktree existed), un-defer has no worktree impact. The Slice proceeds normally to `worktree_ready` when bootstrapped.

### Defer vs Abandon Decision Table

| Criterion | Abandon | Defer |
|-----------|---------|-------|
| Permanence | Permanent exit — no re-entry | Temporary pause — re-activatable |
| Cascade on Dependents | `blocks`-edge dependents → `blocked` | `blocks`-edge dependents → unblocked with `deferred_dep` flag |
| Data-Edge Dependents | `data`-edge dependents → `blocked` | `data`-edge dependents → remain `blocked` (artifacts required) |
| Soft-Edge Dependents | `soft`-edge dependents → unblocked | `soft`-edge dependents → unblocked, scheduler may promote |
| Re-entry Path | Impossible — terminal state | Via `state.slice.undeferred` → `planned` |
| Worktree | Preserved (forensics only) | Preserved (for re-activation) or not yet created |
| Frontmatter Fields | `blocked_reason` on dependents | `deferred_reason` on source, `deferred_deps` on dependents |
| Audit Trail | Abandon event in event store | Defer + un-defer events in event store |
| Use Case | "This work is wrong, discard it" | "This work is right, just not now" |
