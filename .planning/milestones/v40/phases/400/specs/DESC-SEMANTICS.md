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

## Blocked State Mechanics (D-15, FSM-05)

### Entry Conditions

A Slice or Step enters `blocked` state when any of these conditions are met:

1. **Abandon cascade (D-13):** A dependency was abandoned → automatic `blocked` transition. The projector sets `blocked_reason: "Dependency {source_id} abandoned"`. This is the most common entry path.

2. **Unresolved dependency:** A `blocks`-edge dependency (`depends_on[{id: "slice-X", edge: "blocks"}]`) is not yet `shipped`. The scheduler checks all dependency states when dispatching and marks dependents as `blocked` until the blocker ships.

3. **Data-edge unmet:** A `data`-edge dependency (`depends_on[{id: "slice-X", edge: "data"}]`) hasn't produced its required artifacts. Data edges are hard — the dependent literally needs the source's output files.

4. **External condition:** Agent manually blocks a Slice or Step via `state.slice.blocked` or `state.step.blocked` event, providing a `blocked_reason` describing the external blocker (e.g., "waiting for API key rotation," "blocked on upstream dependency outside the hierarchy").

### Blocked Reason Storage

`blocked_reason` is a projector-owned frontmatter field (`str | None`) that documents why a unit is blocked:

- **Set when:** `state.{tier}.blocked` event fires. The projector writes the reason into the frontmatter projection.
- **Source of value:**
  - For **abandon-cascade:** the projector auto-generates `"Dependency {source_id} abandoned"`.
  - For **manual blocks:** the agent provides the description in the event data; the projector stores it verbatim.
- **Cleared when:** `state.{tier}.unblocked` event fires. The projector sets `blocked_reason` to `null`.
- **Historical trail:** Even after clearing, the block reason is preserved in the event store as part of the `state.{tier}.unblocked` event data. Frontmatter shows current state; event store preserves history.
- **Persistence:** Persisted in frontmatter for cross-session survival. The projector rebuilds `blocked_reason` on every daemon restart from the event stream.

### No Timeout Rule (D-15)

The `blocked` state has **NO timeout.** A Slice or Step stays blocked:

- **Indefinitely** until its dependencies resolve by reaching `shipped`.
- **Until the user defers the blocker** (D-14), which treats the dependency as soft-done for `blocks` edges.
- **Until the user re-plans** to remove the dependency from the `depends_on` frontmatter field.
- **Across daemon restarts** — `blocked_reason` is persisted in frontmatter and the state is recomputed from the immutable event stream on startup.
- **The user may shelve the project** for an undetermined time — blocked work waits patiently without any timeout-driven state transition.

This is a deliberate design choice: human/agent work is not a CI pipeline. Dependencies may take days, weeks, or months to resolve. A timeout would force arbitrary decisions (auto-abandon? auto-defer?) that should be made by the human, not the scheduler.

### Unblock Detection

The projector detects unblocking through reactive event processing:

- **Trigger:** On every child state change event (`state.slice.shipped`, `state.slice.deferred`, `state.step.done`), the projector re-evaluates all blocked dependents.
- **Blocks-edge resolution:** If the blocking dependency transitions to `shipped`, the projector emits `state.slice.unblocked` (or `state.step.unblocked`). The tier transitions: `blocked → in_progress` for Slice or `blocked → planning` for Step. `blocked_reason` is cleared.
- **Deferred dependency (D-14):**
  - For `blocks` edges: unblock with `deferred_deps: ["slice-X"]` flag set on the dependent.
  - For `data` edges: remain `blocked` — data requires actual artifacts that a deferred source hasn't produced.
  - For `soft` edges: unblock (soft was advisory anyway; no blocking in the first place).
- **Re-evaluation scope:** The projector only re-evaluates direct dependents of the changed unit. It does not traverse the full dependency graph on every event — this is a local check bounded by the `depends_on` frontmatter fields of siblings.

### Blocked State Audit

- **Frontmatter:** `blocked_reason` persists in frontmatter even after unblock is cleared — the reason is recorded in the `state.{tier}.unblocked` event data for the historical trail.
- **STATE.md projection:** The projector displays all currently blocked Slices with their `blocked_reason` in the STATE.md inventory section. This surfaces stalled work to the user.
- **DAG visualization:** Blocked nodes are rendered with a distinct visual treatment (e.g., orange border, clock icon) in the DAG viewer.
- **Event store:** Every `state.{tier}.blocked` and `state.{tier}.unblocked` event is an immutable record in SQLite. Full audit trail is replayable.

### Tier-Specific Blocked Behavior

| Tier | Can Be Blocked? | How Entered | How Exited | Blocks Children? |
|------|----------------|-------------|------------|-----------------|
| Arc | No | N/A — Arc has no blockable dependencies (D-10: same-parent, root tier has no siblings to depend on) | N/A | N/A |
| Stage | No | N/A — Stage transitions to `abandoned` directly (D-13 arc-level cascade). Stage itself does not have a `blocked` state in its FSM. | N/A | Abandoned Stage → child Slices transition to `blocked` |
| Slice | Yes | 1. Dependency abandon (auto, D-13) 2. Manual block (agent command) 3. Dependency not yet shipped (scheduler) 4. `data`-edge unmet | `blocked → in_progress` (unblock) — returns to prior active state | Blocked Slice → child Steps remain in current state (not auto-blocked). Steps continue to be tracked but the Slice worktree is idle. |
| Step | Yes | 1. Manual block (agent command) 2. External condition (agent describes in `blocked_reason`) | `blocked → planning` (unblock) — re-enters planning because agent needs to re-establish execution context | Blocked Step → sibling Steps unaffected (Steps run serial, agent handles). No cascade to peers. |

**Design note:** The restricted scope (only Slice and Step tiers can be blocked) keeps the state space manageable. Arc and Stage are scoping/aggregation containers — blocking them would cascade unnecessarily when the actual blocking unit is always a Slice or Step dependency.

## Decimal Insertion Protocol (D-16, FSM-04)

### Purpose

Gap-closure and unexpected problems: insert work mid-stream without renumbering the entire parent container. Decimal insertions fill gaps between existing sequential IDs, preserving the immutability of already-assigned IDs. This is the primary mechanism for handling "we missed something" without triggering a cascade of ID renumbering.

### Supported Format

- **Single decimal level:** `slice-12.1`, `slice-12.2`, `slice-12.354`. One decimal dot only.
- **No cap on the decimal number:** Practical limit ~999 but not enforced in schema validation. The decimal part is an integer — not a semantic version or sub-version.
- **Prefix preserved:** `slice-` prefix is always present per D-01. Decimal does not change the prefix convention.
- **Zero handling:** Leading zeros in the integer part are prohibited (`slice-012` invalid per D-01). Leading zeros in the decimal part are technically valid but not preferred: `slice-12.01` works but `slice-12.1` is the canonical form.

### Prohibited Format

- **Double decimals:** `slice-12.1.2` — REJECTED at schema validation. The regex enforces single decimal level only (`^\d+(\.\d+)?$` after prefix).
- **No leading zeros in integer part:** `slice-012` invalid — matches D-01 no-leading-zeros rule.
- **Empty decimal:** `slice-12.` (trailing dot) — invalid. Decimal part is required when dot is present.

### Insertion Rules

1. **Same-parent only:** Decimal inserts share the same parent as the gap they fill. `slice-12.1` has the same parent Stage as `slice-12` and `slice-13`. Cross-parent insertion is not allowed — a new Slice in a different Stage gets its own sequential ID in that Stage's namespace.

2. **No renumbering:** Existing IDs are immutable. Adding `slice-12.1` does NOT change `slice-13` to `slice-14`. The decimal fills the gap, leaving all other IDs untouched. This is a critical property: renaming IDs would break all existing references (frontmatter `depends_on`, index.json entries, event store aggregate IDs, worktree paths).

3. **Sequencing:** Decimal inserts are sequenced BETWEEN the base ID and the next integer. `slice-12.1` logically precedes `slice-13` but follows `slice-12`. The scheduler treats decimals as interleaved within the integer sequence:
   ```
   slice-12 → slice-12.1 → slice-12.2 → slice-13 → slice-13.1 → slice-14
   ```
   Topological sort respects this ordering when dependencies exist between these Slices.

4. **Multiple inserts:** Multiple decimals can fill the same gap: `slice-12.1`, `slice-12.2`, `slice-12.3` all between `slice-12` and `slice-13`. The projector sequences them by decimal value: `12.1 < 12.2 < 12.3 < 13`.

5. **Depends on decimals:** Dependents can reference decimal IDs normally in their `depends_on` frontmatter: `depends_on: [{id: "slice-12.1", edge: "blocks"}]`. Decimal IDs are first-class — they participate in all dependency resolution, cascade logic, and scheduling identically to integer IDs. No special casing.

### Applies To

| Tier | Decimal Support | Rationale |
|------|----------------|-----------|
| Arc | No | Too coarse; if you need to insert an Arc, create a new one at the end. Arc-level decimal inserts would indicate a planning failure, not a gap-closure. |
| Stage | Yes | Gap-closure at Stage level (e.g., missed auth provider integration, unexpected infrastructure dependency). Enables inserting a Stage without renumbering the entire Arc. |
| Slice | Yes | **Primary use case** — gap-closure and unexpected problem Slices. Most decimal insertions happen at the Slice level because Slices are the finest-grained dispatched work unit. |
| Step | Yes | Sub-steps (`step-1.1`, `step-1.2`) within a single step file. Agent-managed — the agent decides to decompose a Step into sub-steps. This is a v41+ harness concern but the ID format is designed here. |

### Structural Reorganization Threshold

When should the user create a **new** Slice/Stage at the end of the container versus inserting a decimal in a gap?

| Scenario | Recommended Approach | Rationale |
|----------|---------------------|-----------|
| Gap of 1-2 missing Slices, tightly related to existing work | **Insert decimal** (e.g., `slice-12.1`) | Keeping the insertion at the gap location maintains logical ordering and dependency clarity |
| Gap of ≥3 missing Slices | **Create new Slices at end of Stage** | Large gaps indicate structural reorganization is needed; inserting many decimals clutters the ID space |
| Gap spans multiple Stages with different concerns | **Create new Stage after existing** | A new Stage groups the new work under its own scoping container |
| Single unexpected problem discovered mid-execution | **Insert decimal** | One-off gap closure; decimal is exactly designed for this case |
| Missing foundational dependency discovered during planning | **Insert decimal** (before dependents) | Ensures the dependency ordering is correct in the DAG; all dependent Slices reference the correct prerequisite |

**Threshold is advisory, not enforced:** The user decides. The protocol supports either approach. The threshold provides guidance for when to reach for decimals vs. when structural reorganization is the cleaner path.

### ID Validation Regex

Each tier has a specific regex for ID validation. Decimal support is optional (via `(\.\d+)?` group):

```
Regex patterns (after prefix: arc-, stage-, slice-, step-):

Arc:    ^arc-\d+$
Stage:  ^stage-\d+(\.\d+)?$      # decimal optional
Slice:  ^slice-\d+(\.\d+)?$      # decimal optional
Step:   ^step-\d+(\.\d+)?$       # decimal optional (sub-steps)
```

**Single decimal level only:** Two decimal dots (e.g., `slice-12.1.2`) are rejected at schema validation. The `(\.\d+)?` group matches zero or one decimal segments — attempting to match two dots fails the regex.

**Schema enforcement:** Frontmatter schema validation (pydantic with `extra="forbid"`) enforces ID format at document creation time. Invalid IDs are rejected before any event is emitted or any directory is created.

### Index.json Resolution

Decimal IDs resolve via `index.json` the same way integer IDs do — no special resolution logic:

```json
{
  "slice-12.1": "arcs/arc-07/stages/stage-03/slices/slice-12-oauth-debug/",
  "slice-12.2": "arcs/arc-07/stages/stage-03/slices/slice-12-token-refresh-fix/"
}
```

**Key properties:**
- Decimal IDs are first-class keys in index.json — they are not sub-entries of the integer ID.
- Path resolution uses the full decimal ID as the lookup key; no parsing of the decimal component is needed at resolution time.
- The directory slug (e.g., `slice-12-oauth-debug/`) uses the decimal ID's integer part for the slug — the decimal part identifies the insertion point, not the directory name.
- index.json handles all IDs uniformly — there is no code path difference between integer and decimal ID resolution. This keeps the resolver simple and avoids special-casing.

