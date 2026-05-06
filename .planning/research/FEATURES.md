# Feature Landscape — Build Hierarchy & Artifact System Architecture

**Domain:** Multi-tier product hierarchy system (Arc → Phase → Slice → Step) for agentic state-machine workflow engine
**Researched:** 2026-05-06
**Confidence:** HIGH on hierarchy patterns (studied GSD, Jira, Azure DevOps, Linear); HIGH on state's existing architecture (read ARCHITECTURE.md, HANDOFF.md, schema.py directly); MEDIUM on optimal decimal-insertion strategy (tradeoffs explored, final answer needs discuss-phase)

---

## Executive Summary

Every multi-tier project management system (Jira, Azure DevOps, Linear, GSD) converges on a four-level hierarchy: **Initiative/Arc → Epic/Phase → Story/Slice → Task/Step**. What distinguishes good from great is not the number of tiers but (a) whether state tracking files are **projections of an event store** rather than agent-written, (b) whether cross-references are **typed edges with guard validation** rather than free-text, (c) whether the naming convention supports **stable identity across renames** via a unique machine-sortable key, and (d) whether the artifact catalog is **canonical (one source of truth)** rather than scattered conventions.

State's four-tier hierarchy (Arc → Phase → Slice → Step) maps cleanly onto industry systems but introduces two novel patterns: **projector-built STATE.md at every tier** (never agent-written, rebuildable from events) and **typed DAG edges** (`blocks`, `soft`, `data`) that the scheduler consumes directly.

The biggest anti-pattern studied across all systems: **agent-written tracking files that drift from ground truth**. Azure DevOps avoids this (work items are the database); Jira avoids it (Jira IS the database); Linear avoids it (Linear IS the database). GSD partially suffers from it (STATE.md is agent-written, with verify.cjs health checks as mitigation). State eliminates it: STATE.md is a projector output, and the event store is authoritative.

---

## 1. Table Stakes (Features Every Tier Must Support)

Features users expect. Missing = product feels incomplete. Every tier in the hierarchy must satisfy these.

### 1.1 Tier Identity & Lifecycle

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Unique stable ID per item** | All systems use machine-sortable IDs that survive title changes (Azure DevOps: integer, Jira: PROJECT-123, Linear: TEAM-123) | Low | Already designed: ARC.md/PASE.md/SLICE.md/STEP.md have `id` fields |
| **Human-readable title/slug** | Users navigate by name, not ID | Low | Separate from machine ID; slug derived from title, ID is canonical |
| **State machine per tier** | Every system tracks work through lifecycle states | Med | Already designed: Arc (planned→in_progress→shipped\|abandoned), Phase (planned→in_progress→verified→shipped\|abandoned), Slice (planned→worktree_ready→in_progress→shipped\|reverted), Step (idle→discussing→planning→executing→verifying→done\|blocked\|abandoned) |
| **Event-driven state transitions** | State changes must be auditable and replayable | Med | Already designed: 28+ event types with per-aggregate sequences |
| **Frontmatter/metadata schema** | Every artifact needs validated structured data | Low | Already designed: pydantic models with `extra="forbid"` |
| **Parent pointer** | Every child must reference its parent tier | Low | ARC.md→phases[], PHASE.md→arc_id, SLICE.md→phase_id, STEP.md→slice_id |

### 1.2 Dependencies & Ordering

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Typed dependency edges** | Not all dependencies are hard blocks; some are advisory, some are artifact-producing | Med | Already designed: `blocks` (hard), `soft` (suggested), `data` (artifact-producing) |
| **DAG validation (no cycles)** | Cyclic dependencies deadlock the scheduler; must reject on insert | Med | Already designed: full DFS cycle check on edge insert |
| **Descoped-dependency resolution** | When a dependency is descoped/abandoned, dependents must know | High | What happens when Slice A `blocks` depends on Slice B that gets abandoned? Options: cascade-abandon, assume-satisfied with explicit flag, or block-and-surface. Discuss-phase decision. |
| **Cross-tier dependencies** | Can an Arc depend on another Arc? Can a Slice depend on a Slice in a different Phase? | High | Already flagged as gray-area question in HANDOFF.md. Azure DevOps: Epics CAN have parents (nested Epics). Linear: Issues can parent across projects. Jira: Epics can link to other Epics. |

### 1.3 State Tracking & Visibility

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Per-tier status rollup** | Parent tier status must aggregate child statuses | Med | Phase STATE.md shows Slice completion percentage; Arc STATE.md shows Phase rollup; all projector-driven |
| **Blocked-item visibility** | Users need to see what's blocked and why | Low | Already designed: BLOCKED state with `blocked_reason` field |
| **Progress indicators** | Completion %, Steps done/total, Slices shipped/total | Low | Projector derives from event stream |
| **Ordered child lists** | Parent artifacts must list children in dependency (not alphabetical) order | Low | phases[], slices[], steps[] arrays in frontmatter are dependency-ordered |

### 1.4 Artifact Discovery & Navigation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Path-based discovery** | Artifacts must be findable by convention (path = identity) | Low | `.state/build/arcs/{arc-id}/phases/{phase-id}/slices/{slice-id}/steps/{step-id}/` |
| **ID-based lookup** | Reverse index: given an ID, find its path | Low | Projector maintains ID→path mapping table in SQLite |
| **Frontmatter-based search** | Query artifacts by frontmatter fields (status, owner, tag) | Low | SQLite projection enables this natively |
| **Parent-chain navigation** | Walk from Step → Slice → Phase → Arc trivially | Low | Each artifact stores its parent ID in frontmatter |

---

## 2. Differentiators (Features That Make the Hierarchy Great)

These features distinguish a good hierarchy from a great one. Most are already designed in state's architecture; all others are design decisions for this milestone.

### 2.1 Projector-Built State (Anti-Drift Architecture)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **STATE.md is a projector output, never agent-written** | Eliminates the #1 tracking problem: agents forget to update STATE.md, causing drift between filesystem and ground truth | Med | Already designed. Daemon's CQRS projector rebuilds STATE.md from events.sqlite on every state change. Agents NEVER write STATE.md directly. |
| **Replay-to-rebuild** | On daemon startup or health check, replay all events to rebuild every STATE.md — they are throwaway projections | Med | Already designed. This is how Azure DevOps/Jira/Linear work (their DB is truth). State extends this to file-based artifacts. |
| **Consistency validation** | A `validate_consistency` function detects when filesystem state diverges from event-store state | Low | GSD precedent: verify.cjs's 19 warning codes. State extends this to four tiers. |
| **Health checks at every tier** | Verify: does ARC.md's `status` field match the Arc projection? Are all referenced child IDs valid? | Med | GSD precedent: W011 consistency checks. State needs per-tier equivalents. |

### 2.2 Typed Dependency DAG

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **`blocks` (hard) edges** | Target must be DONE before dependent can start. Scheduler enforces. | Low | Already designed |
| **`soft` (suggested) edges** | Target SHOULD be done first but scheduler may override. Human judgment escape hatch. | Low | Already designed |
| **`data` (artifact-producing) edges** | Target produces artifacts this step consumes. Hard DAG edge + copies artifact path. | Low | Already designed |
| **Edge insert rejects cycles** | Full DFS cycle check on every edge insert prevents scheduling deadlocks | Low | Already designed |
| **Descope-aware scheduler** | When a node is abandoned/descoped, dependents are surfaced rather than silently blocked forever | High | Discuss-phase decision: cascade-abandon vs assume-satisfied vs block-and-surface |

### 2.3 Stable Identity with Decimal Insertions

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Machine-sortable primary key** | IDs that sort in creation order, survive renames, and support decimal gap-closure inserts | Med | GSD precedent: phase 022.1, 022.2 for gap-closure. State needs this at Slice and Step levels. |
| **Human-readable slug (secondary)** | Slugs derived from titles for readability in paths and displays | Low | e.g., `auth-oauth-migration` — changes when title changes; ID never changes |
| **ID-based references, slug-based display** | Cross-references use IDs (stable), UI shows slugs (readable) | Low | This is how every major system works: Azure DevOps #12345, Jira PROJ-123, Linear ENG-123 |
| **Decimal insertions without renumbering** | Insert work between 003 and 004 as 003.1, not renumber 004→005 | Med | GSD precedent. State extends to Slice level (Phase decimal) and possibly Step level. Discuss-phase: what's the max depth? (003.1.2? Or flat?) |

### 2.4 Immutability by Tier

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **ARC.md immutable while child Phases are in_progress** | Prevents scope creep that invalidates in-flight work | Med | Discuss-phase decision. Jira allows epic scope changes mid-sprint (team pain). Linear allows project scope changes. Azure DevOps warns but doesn't block. |
| **STEP.md plan immutable after execute begins** | The plan is the contract; changing it mid-execution invalidates verification | Low | Already partially designed (STEP.md frontmatter includes verify_contract) |
| **Snapshot-before-mutation** | When an immutable artifact must change, snapshot the current version first | Low | Already designed: Step snapshots at execute/verify entry |
| **Versioned artifacts** | Some artifacts may need version history (e.g., ARC.md evolves across milestones) | Med | Not yet designed. Options: git history (free, implicit), explicit version field, or snapshot references |

### 2.5 Canonical Artifact Catalog

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Single registry of every recognized artifact** | One source of truth for "what files exist in this system" — prevents scattered conventions | Med | GSD precedent: artifacts.cjs (10 exact-match + 2 pattern-match entries). State needs per-tier expansion. |
| **Schema validation on read** | Every artifact read validates against its pydantic model; rejects malformed frontmatter | Low | Already designed: `extra="forbid"` pydantic models |
| **Discovery by path convention + registry** | Two lookup methods: walk the filesystem tree OR query the SQLite projection | Low | Filesystem is the primary layout; SQLite is the fast index |
| **Template-based creation** | New artifacts generated from validated templates, not empty files | Low | `.state/build/templates/` directory with ARC.md.tmpl, PHASE.md.tmpl, etc. |

---

## 3. Anti-Features (Things That Look Useful But Create Maintenance Burden)

Features to explicitly NOT build.

### 3.1 Agent-Written Tracking Files

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Agents writing STATE.md directly** | GSD's #1 drift problem: agents mutate STATE.md, verifier catches drift later, reconciliation is manual | STATE.md is a projector output, rebuilt from events on every state change. Agents emit events; projector updates STATE.md. |
| **Agents manually updating completion percentages** | Error-prone, forgettable, always drifts | Projector computes: `completed_steps / total_steps` from event stream |
| **Agents updating cross-reference lists** | Maintaining `phases: [...]` in ARC.md manually when phases are added/removed | Projector auto-updates parent frontmatter when child events fire (e.g., `state.phase.created` → ARC.md `phases` array auto-updated) |

### 3.2 Arbitrary Graph Linking

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Free-form "relates to" links** | Hard to validate, hard to reason about, creates unmaintainable webs | Typed edges only: `blocks`, `soft`, `data`. If you need "relates to," tag it instead. |
| **Bidirectional edges** | Synchronization burden: add A→B, must also add B→A or detect inconsistency | Edges are directional only. Query reverse edges from the DAG graph projection. |
| **Cross-mode edges** | Build Slice depending on a Teach concept — architecturally invalid per mode isolation | Mode isolation is physical; cross-mode edges are rejected at schema validation |

### 3.3 Deeply Nested Insertions

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Unbounded decimal depth (003.1.2.4)** | Becomes unreadable; renumbering becomes a tree operation | Cap at one decimal layer: `003.1`. For deeper reorg, create a new Phase/Slice. |
| **Auto-renumbering on insert** | Invalidates every existing reference to renumbered items | Decimal insertions append (003.1, 003.2) without renumbering subsequent items. Original 004 stays 004. |
| **Semantic overload in IDs** | Encoding Arc+Phase+Slice+Step into a single ID string (e.g., "A3-P7-S2-S4") — breaks if Slice moves between Phases | Store relationships in frontmatter fields (`arc_id`, `phase_id`), not encoded in the ID. ID is a unique key, not a path. |

### 3.4 Mixed Update Mechanisms

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Some fields agent-written, some projector-written** | Race conditions, inconsistency, confusion about who owns what | Clear ownership: frontmatter fields are either `agent_owned` (title, goal, goal_criteria) or `projector_owned` (status, completed_at, phases[], slices[], steps[]). Never mixed within a field. |
| **Filesystem + event store both as source of truth** | Dual-write without clear authority leads to split-brain | events.sqlite is authoritative. Filesystem artifacts (ARC.md, etc.) are projections. Validator enforces consistency; on mismatch, event store wins. |
| **Manual state manipulation commands** | `state set-phase-status 7 shipped` bypasses the event stream, creates unverifiable state | State changes only through event emission: `state.phase.completed`. No direct-field mutation CLI. |

### 3.5 Over-Engineering the First Tier

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Five tiers** | Every additional tier doubles cross-reference complexity, state projection surface, and agent confusion about "where do I put this?" | Four tiers are proven: Jira (Theme→Epic→Story→Subtask), Azure DevOps (Epic→Feature→PBI→Task), Linear (Project→Milestone→Issue→Sub-issue). Arc→Phase→Slice→Step is the right scope. |
| **Generic "container" tier** | A tier that's "just for grouping" without its own state machine, artifacts, or events becomes dead weight | Every tier owns at minimum: a state machine, one artifact file (ARC.md/PHASE.md/etc.), a STATE.md projection, events, and a parent pointer. If a tier can't justify all five, it doesn't earn its place. |
| **Dynamic tier creation** | Letting users define custom tiers at runtime creates infinite validation surface | Four fixed tiers. Extensibility through frontmatter fields, not new tiers. |

---

## 4. Cross-Referencing Patterns

How artifacts reference each other across tiers.

### 4.1 Recommended Pattern: ID-Based with Path Lookup

**Every cross-reference stores the target's unique ID, not its path or title.** The ID survives renames and moves.

```
ARC.md:
  phases: [phase-001, phase-002, phase-003]    # IDs, not slugs

PHASE.md:
  arc_id: arc-001                                # parent reference
  slices: [slice-001, slice-002]                 # child IDs

SLICE.md:
  phase_id: phase-001
  steps: [step-001, step-002]
  depends_on:                                    # DAG edges
    - id: slice-003                              # target ID
      kind: blocks                                # edge type

STEP.md:
  slice_id: slice-001
  depends_on:
    - id: step-002                                # target ID
      kind: data                                   # edge type
      artifact_path: src/module/output.py         # what artifact is consumed
```

### 4.2 Resolution Chain

1. **At read time:** Load artifact → parse frontmatter → resolve IDs via projector's ID→path index → verify target exists and is valid
2. **At write time (artifact creation):** Schema validator rejects unknown IDs, descoped IDs (with explicit flag override), and cross-mode IDs
3. **At verification time:** Resolve all depends_on chains, verify all `blocks`/`data` targets are DONE, surface any broken references

### 4.3 What Happens When References Break

| Scenario | Behavior |
|----------|----------|
| **Target deleted** | Validator surfaces broken reference; parent artifact flagged with `health: broken_refs`; does not auto-delete the reference |
| **Target renamed** | ID-based references unaffected (ID is stable); path lookup updated by projector |
| **Target descoped** | Scheduler detects, surfaces dependents; avoid option presented (see §2.2) |
| **Target moved to different parent** | ID-based references unaffected; parent pointer updated in frontmatter |
| **Cross-mode reference attempted** | Schema validation rejects at creation time |

### 4.4 Comparison: Parent-Child vs Graph-Based

| Approach | Pros | Cons | State's Choice |
|----------|------|------|---------------|
| **Pure parent-child (tree)** | Simple to reason about, trivial path lookup, easy verification | No cross-branch dependencies, limits scheduling parallelism | Used for structural hierarchy (Arc→Phase→Slice→Step containment) |
| **Pure graph (DAG)** | Maximum expressiveness, models real dependencies, enables scheduler | Harder to verify, orphan detection complex, can produce unmaintainable webs | Used for `depends_on` edges (within and across branches) |
| **Hybrid (tree + typed DAG)** | Structural hierarchy is a tree (one parent per node); execution ordering is a DAG across the tree | More complex implementation | **State's choice.** Hierarchy = tree (parent pointer), scheduling = DAG (depends_on edges). Best of both. |

This hybrid matches how Azure DevOps works (tree structure for area path, link types for cross-item dependencies) and how Linear works (parent/child for hierarchy, blocking for dependencies). Pure trees are too limiting; pure graphs are too chaotic. State's hybrid: tree for ownership, DAG for ordering.

---

## 5. Naming Conventions

### 5.1 ID Formats

| Tier | ID Format | Example | Rationale |
|------|-----------|---------|-----------|
| **Arc** | `arc-{seq}` | `arc-001` | Flat namespace, 3-digit zero-padded for sortability. Arc count is small (15-30). |
| **Phase** | `phase-{arc_seq}-{seq}` | `phase-001-003` | Arc-prefixed for readability but NOT required for uniqueness (phase_seq alone is unique). The prefix is display-only; the canonical key is `phase_seq`. |
| **Slice** | `slice-{phase_seq}-{seq}` | `slice-003-012` | Phase-prefixed display; canonical key is `slice_seq`. |
| **Step** | `step-{slice_seq}-{seq}` | `step-012-004` | Slice-prefixed display; canonical key is `step_seq`. |

**Key decision: IDs are globally unique monotonic integers per tier, NOT compound keys.** The display format includes parent context for human readability, but internal references use the integer key. This is the Jira model (PROJ-123 is display; 123 is the key).

Alternative considered: UUID-based IDs. Rejected because they're unreadable in artifact files, un-sortable by creation order, and the project is single-user (no distributed ID generation needed).

### 5.2 Decimal Insertions

| Level | Format | Example | Rules |
|-------|--------|---------|-------|
| **Phase gap-closure** | `phase-{arc_seq}-{seq}.{decimal}` | `phase-001-003.1` | One decimal layer. Insert between 003 and 004. Original 004 stays 004. |
| **Slice gap-closure** | `slice-{phase_seq}-{seq}.{decimal}` | `slice-003-012.1` | Same pattern. |
| **Step gap-closure** | NOT SUPPORTED at Step level | — | Steps are serial within a Slice. If you need to insert a Step, add it at the end with a `depends_on` that places it correctly. The Step-level serial execution model doesn't benefit from decimal insertion (unlike GSD, where all plans run as a flat list). |

**When to insert vs. append:**
- Insert (decimal): gap-closure work that logically belongs between existing items
- Append: new forward work; just add at end

### 5.3 Directory Naming

| Tier | Directory | Example |
|------|-----------|---------|
| **Arc** | `.state/build/arcs/{arc-slug}/` | `.state/build/arcs/auth-system-overhaul/` |
| **Phase** | `.../phases/{phase-slug}/` | `.../phases/oauth-provider-migration/` |
| **Slice** | `.../slices/{slice-slug}/` | `.../slices/anthropic-oauth-flow/` |
| **Step** | `.../steps/{step-id}/` | `.../steps/step-004/` |

**Slug generation:** lowercase, hyphens, max 60 chars, derived from title on creation. Slugs CAN change when titles change (they're display-only). Cross-references use IDs, not slugs.

**Why slugs for Arc/Phase/Slice but IDs for Steps?** Arc/Phase/Slice directories are few and browsed by humans. Steps are numerous (hundreds) and only accessed programmatically or via the projector ID→path index.

### 5.4 File Naming

| File | Location | Schema |
|------|----------|--------|
| `ARC.md` | `arcs/{arc-slug}/` | ArcDefinition |
| `PHASE.md` | `arcs/{arc-slug}/phases/{phase-slug}/` | PhaseDefinition |
| `SLICE.md` | `arcs/{arc-slug}/phases/{phase-slug}/slices/{slice-slug}/` | SliceDefinition |
| `STEP.md` | `.../steps/{step-id}/` | StepDefinition |
| `STATE.md` | Every tier directory | TierState (projection) |
| `DISCUSS.md` | `.../steps/{step-id}/` | DiscussRecord |
| `PLAN.md` | `.../steps/{step-id}/` | PlanRecord |
| `VERIFY.md` | `.../steps/{step-id}/` | VerifyRecord |
| `EXECUTE.log` | `.../steps/{step-id}/` | ExecuteLog (structured, not free-form) |
| `DECISIONS.md` | Arc/Phase directories | DecisionLog |
| `SNAPSHOT.json` | `.../steps/{step-id}/` | SnapshotManifest |

Files with stable names (ARC.md, STATE.md, STEP.md, etc.) are discovered by convention — no registry lookup needed. The canonical artifact registry validates that the expected files exist and have correct schemas.

### 5.5 MARKER Convention

Inherited from GSD: every artifact file includes an HTML comment marker that identifies the artifact type and ID. This survives format changes and provides a machine-readable identity signal independent of filename or path.

```markdown
<!-- state:artifact:type=arc id=arc-001 -->
```

Purpose: GSD's `gsd-doc-writer` uses markers to locate and update artifacts across renames. State inherits this for the same reason.

---

## 6. State Machines Mapped to Artifact Lifecycles

### 6.1 Arc State Machine

```
States: planned → in_progress → shipped | abandoned

Events:
  arc.created         → planned
  arc.started         → in_progress
  arc.completed       → shipped
  arc.abandoned       → abandoned

Transitions:
  planned ──arc.started──▶ in_progress
  planned ──arc.abandoned──▶ abandoned
  in_progress ──arc.completed──▶ shipped
  in_progress ──arc.abandoned──▶ abandoned
  in_progress ──arc.replanned──▶ planned          (scope change)

Guards:
  arc.started requires: at least 1 child phase exists
  arc.completed requires: all child phases are shipped or abandoned
  arc.abandoned requires: all in_progress phases are first abandoned or completed
```

**Arc is a container.** It aggregates Phases. It has no execution logic of its own — its state is purely the rollup of its children.

### 6.2 Phase State Machine

```
States: planned → in_progress → verified → shipped | abandoned

Events:
  phase.planned       → planned
  phase.started       → in_progress
  phase.verified      → verified
  phase.completed     → shipped
  phase.abandoned     → abandoned

Transitions:
  planned ──phase.started──▶ in_progress
  planned ──phase.abandoned──▶ abandoned
  in_progress ──phase.verified──▶ verified
  in_progress ──phase.abandoned──▶ abandoned
  verified ──phase.completed──▶ shipped
  verified ──phase.failed_verification──▶ in_progress

Guards:
  phase.started requires: at least 1 child slice is planned
  phase.verified requires: all child slices are shipped or reverted, AND verify_rollup passes
  phase.completed requires: phase.verified + all success criteria met
```

**Phase sits between container and executor.** It owns verification criteria. The `verified` state is a gate between "slices built" and "phase complete" — this is where rollup verifiers run.

### 6.3 Slice State Machine

```
States: planned → worktree_ready → in_progress → shipped | reverted

Events:
  slice.planned       → planned
  slice.worktree_ready → worktree_ready
  slice.shipped       → shipped
  slice.reverted      → reverted

Transitions:
  planned ──slice.worktree_ready──▶ worktree_ready
  worktree_ready ──slice.started──▶ in_progress
  in_progress ──slice.shipped──▶ shipped
  in_progress ──slice.reverted──▶ reverted
  reverted ──slice.replanned──▶ planned

Guards:
  slice.worktree_ready requires: worktree created and bootstrapped successfully
  slice.started requires: all depends_on blocks/data targets are DONE
  slice.shipped requires: all child steps are DONE or abandoned, AND worktree merged to primary
  slice.reverted requires: snapshot exists for revert target
```

**Slice is the concurrency unit.** One worktree per Slice. Slices can run in parallel. Reverting a Slice reverts all its Steps (prefix revert within the Slice).

### 6.4 Step State Machine

```
States: idle → discussing → planning → executing → verifying → done | blocked | abandoned

Events (10 types):
  step.created        → idle
  step.discussed      → discussing
  step.planned        → planning
  step.executed       → executing
  step.verify_started → verifying
  step.verify_passed  → done
  step.verify_failed  → executing        (back to fix)
  step.blocked        → blocked
  step.unblocked      → executing        (resume)
  step.abandoned      → abandoned

Transitions:
  idle ──step.discussed──▶ discussing
  idle ──step.abandoned──▶ abandoned
  discussing ──step.planned──▶ planning
  discussing ──step.blocked──▶ blocked
  planning ──step.executed──▶ executing
  planning ──step.blocked──▶ blocked
  executing ──step.verify_started──▶ verifying
  executing ──step.blocked──▶ blocked
  verifying ──step.verify_passed──▶ done          (→ emit step.advanced → scheduler)
  verifying ──step.verify_failed──▶ executing     (retry loop)
  blocked ──step.unblocked──▶ executing
  any ──step.abandoned──▶ abandoned

Guards:
  step.executed requires: all depends_on blocks/data targets are DONE
  step.verify_started requires: execute completed, snapshot taken
  step.verify_passed requires: verify_contract all pass
  step.verify_failed: max retries configurable (default: 3); exceeds → auto-blocked

Snapshots:
  - pre_execute: taken when entering executing
  - pre_verify: taken when entering verifying
```

**Step is the only tier that runs the full discuss→plan→execute→verify cycle.** Arc/Phase/Slice are scoping containers; Step is the worker. Steps within a Slice run **serially** (concurrent Steps within one Slice would conflict on the same worktree).

### 6.5 Cross-Tier State Consistency

| Rule | Enforcement |
|------|-------------|
| Arc can't be `shipped` if any child Phase is `in_progress` | Guard on `arc.completed` |
| Phase can't be `verified` if any child Slice is `in_progress` | Guard on `phase.verified` |
| Slice can't be `shipped` if any child Step is not `done` or `abandoned` | Guard on `slice.shipped` |
| Abandoned parent cascades to children | On `arc.abandoned`: auto-abandon all non-shipped Phases. On `phase.abandoned`: auto-abandon all non-shipped Slices. On `slice.abandoned`: auto-abandon all non-done Steps. |
| Shipped child counts toward parent completion | Projector recalculates parent progress on every child state change |

---

## 7. Artifact Catalog

### 7.1 Complete Artifact Inventory

| Artifact | Tier | Creator | Writer | Schema | Cross-Refs | Update Trigger |
|----------|------|---------|--------|--------|------------|----------------|
| **ARC.md** | Arc | `new-arc` command | Agent (frontmatter), Projector (status) | ArcDefinition | phases[], depends_on[] | On phase.created, phase.shipped, arc.started/completed |
| **PHASE.md** | Phase | `new-phase` command | Agent (frontmatter), Projector (status) | PhaseDefinition | arc_id, slices[], depends_on[] | On slice.created, slice.shipped, phase.started |
| **SLICE.md** | Slice | `new-slice` command | Agent (frontmatter), Projector (status) | SliceDefinition | phase_id, steps[], depends_on[], worktree | On step.advanced, slice.shipped/reverted |
| **STEP.md** | Step | `plan-step` command | Agent (frontmatter), Projector (status) | StepDefinition | slice_id, depends_on[], snapshot_refs | On step.advanced, step.blocked/unblocked |
| **STATE.md** | All tiers | Projector (daemon) | **Projector only** | TierState (projection) | N/A (derived from events) | On every event for that aggregate |
| **DISCUSS.md** | Step | `discuss-step` command | Agent | DiscussRecord | step_id | On step.discussed |
| **PLAN.md** | Step | `plan-step` command | Agent | PlanRecord | step_id, references DISCUSS.md decisions | On step.planned |
| **VERIFY.md** | Step | `verify-step` command | Agent | VerifyRecord | step_id, references PLAN.md must-haves | On step.verify_passed/failed |
| **EXECUTE.log** | Step | `execute-step` command | Subagent (structured) | ExecuteLog | step_id, task_ids, commit SHAs | On each subtask completion during execute |
| **DECISIONS.md** | Arc, Phase | Gray-area dialog | Agent | DecisionLog | arc_id or phase_id, decision IDs | On state.decision.made |
| **SNAPSHOT.json** | Step, Slice | Snapshot service | Daemon (programmatic) | SnapshotManifest | step_id/slice_id, git SHA | On snapshot taken |
| **WORKTREE.lock** | Slice | Worktree service | Daemon (programmatic) | WorktreeLock | slice_id, pid, start_time_ns | On worktree create/destroy |

### 7.2 Schema Ownership

| Field Ownership | Examples | Rationale |
|-----------------|----------|-----------|
| **Agent-owned** (manual) | title, goal, success_criteria, verify_contract, depends_on, opencode_surface | These define intent. Only the agent knows what it meant to build. |
| **Projector-owned** (automatic) | status, created_at, updated_at, completed_at, phases[], slices[], steps[], snapshot_ref, progress_pct | These are derivable from the event stream. Never agent-written. |
| **Hybrid** (agent sets initial, projector updates) | depends_on (agent declares edges; projector resolves target statuses); worktree (agent requests; projector tracks lifecycle) | Some fields start agent-owned but are kept consistent by the projector. |

**Validation rule:** On artifact save, if a projector-owned field has been modified by the agent, the save is rejected. The agent CANNOT write `status: shipped` directly — only the projector can advance state by processing events.

### 7.3 Cross-Reference Fields Per Artifact

| Artifact | Cross-Reference Fields |
|----------|----------------------|
| **ARC.md** | `phases: [phase_id, ...]` — child phases<br>`depends_on: [{id: arc_id, kind: blocks\|soft}, ...]` — cross-Arc dependencies |
| **PHASE.md** | `arc_id: arc_id` — parent<br>`slices: [slice_id, ...]` — children<br>`depends_on: [{id: phase_id, kind: blocks\|soft}, ...]` — cross-Phase dependencies |
| **SLICE.md** | `phase_id: phase_id` — parent<br>`steps: [step_id, ...]` — children<br>`depends_on: [{id: slice_id, kind: blocks\|soft\|data, artifact_path: str?}, ...]` — DAG edges |
| **STEP.md** | `slice_id: slice_id` — parent<br>`depends_on: [{id: step_id, kind: blocks\|soft\|data, artifact_path: str?}, ...]` — DAG edges |

---

## 8. On-Disk Layout

```
.state/build/
├── arcs/
│   └── {arc-slug}/                          # e.g., auth-system-overhaul
│       ├── ARC.md                           # arc definition + frontmatter
│       ├── STATE.md                         # arc-level state projection
│       ├── DECISIONS.md                     # gray-area decisions scoped to this arc
│       └── phases/
│           └── {phase-slug}/                # e.g., oauth-provider-migration
│               ├── PHASE.md                 # phase definition + frontmatter
│               ├── STATE.md                 # phase-level state projection
│               ├── DECISIONS.md             # gray-area decisions scoped to this phase
│               └── slices/
│                   └── {slice-slug}/        # e.g., anthropic-oauth-flow
│                       ├── SLICE.md         # slice definition + frontmatter
│                       ├── STATE.md         # slice-level state projection
│                       ├── steps/
│                       │   └── {step-id}/   # e.g., step-001
│                       │       ├── STEP.md       # step definition + goal
│                       │       ├── STATE.md       # step-level state projection
│                       │       ├── DISCUSS.md     # discuss-phase output
│                       │       ├── PLAN.md        # plan-phase output
│                       │       ├── VERIFY.md      # verify-phase output
│                       │       ├── EXECUTE.log    # structured execution log
│                       │       └── SNAPSHOT.json  # snapshot manifest
│                       ├── worktree/              # git worktree (not committed, under .gitignore)
│                       └── snapshots/             # content-addressed step/slice snapshots
├── intel/              ← codebase intelligence (parallel with GSD)
├── codebase/           ← codebase mapping (parallel with GSD)
├── graph/              ← knowledge graph (parallel with GSD)
├── decisions/          ← global decision log (cross-Arc)
├── patterns/           ← pattern library
├── skills/             ← build-mode skills (opencode auto-discovers)
├── templates/          ← artifact templates (ARC.md.tmpl, PHASE.md.tmpl, etc.)
└── config/             ← build-mode configuration
```

**Design principles:**
1. **Hierarchy mirrored in directory tree.** Walking the filesystem shows the structure.
2. **Stable file names at leaf level.** ARC.md, PHASE.md, SLICE.md, STATE.md are always in predictable locations.
3. **ID-based step directories.** Steps are numerous; using step-001 is more stable than slug-based (slugs change when titles change).
4. **Worktree outside committed tree.** `.gitignore` excludes `worktree/` and `snapshots/` directories.
5. **STATE.md at every level.** Not just Arc/Phase. Even Step-level STATE.md exists for consistency validation.

---

## 9. Tracking File Consistency Model

### 9.1 The Golden Rule

> **STATE.md is exclusively a projector output. Agents NEVER write STATE.md. The event store (events.sqlite) is the source of truth.**

### 9.2 How It Works

```
Agent emits event (e.g., state.step.verify_passed)
  → Daemon appends to events.sqlite (seq++)
  → Projector recomputes the Step's STATE.md
  → Projector recomputes the Slice's STATE.md (step count, completion %)
  → Projector recomputes the Phase's STATE.md (slice rollup)
  → Projector recomputes the Arc's STATE.md (phase rollup)
  → Daemon emits SyncEvent → TUI re-renders
```

### 9.3 Rebuild

On daemon startup or explicit `state build rebuild-projections`:
```
1. Delete all STATE.md files in .state/build/
2. Replay all events from events.sqlite
3. Projector rebuilds every STATE.md from scratch
4. Verify that filesystem ARC.md/PHASE.md/etc. match event-derived state
5. Report any inconsistencies
```

STATE.md files are throwaway — they can be deleted and rebuilt at any time without data loss. This is the key insight from CQRS: projections are cheap to rebuild; the event log is expensive to lose.

### 9.4 Consistency Validator

A `state build validate-consistency` command (inspired by GSD's verify.cjs health checks) runs cross-tier validation:

| Check | What It Validates | Severity |
|-------|-------------------|----------|
| **W001: state-drift** | STATE.md status field matches event-store-derived status for every aggregate | ERROR |
| **W002: orphan-children** | Every Phase has a valid parent Arc; every Slice has a valid parent Phase; every Step has a valid parent Slice | ERROR |
| **W003: broken-refs** | Every depends_on target ID resolves to an existing artifact | ERROR |
| **W004: cycle-detected** | No cycles exist in the dependency DAG | ERROR |
| **W005: stale-state** | STATE.md last_updated is newer than the last event for that aggregate (someone edited it manually) | ERROR |
| **W006: missing-artifact** | Every artifact in the canonical catalog exists on disk | WARNING |
| **W007: extra-file** | Files exist in the hierarchy tree that aren't in the canonical artifact catalog | WARNING |
| **W008: cross-mode-ref** | A build artifact references a teach artifact (or vice versa) | ERROR |
| **W009: frontmatter-schema** | Every artifact's frontmatter validates against its pydantic schema | ERROR |
| **W010: projector-miss** | An event was emitted but the projector didn't update the corresponding STATE.md | ERROR |
| **W011: descoped-blocker** | A `blocks` edge points to an abandoned/descoped target without assume-satisfied flag | WARNING |
| **W012: duplicate-id** | Two artifacts share the same canonical ID (should be impossible but check anyway) | ERROR |
| **W013: parent-child-mismatch** | An artifact's parent_id in frontmatter doesn't match its filesystem location | WARNING |
| **W014: snapshot-orphan** | Snapshot exists for a Step/Slice that no longer exists in the hierarchy | WARNING |
| **W015: worktree-leak** | Worktree directory exists for a Slice in shipped/reverted state | WARNING |

---

## 10. MVP Recommendation

For this design-phase milestone (v40), prioritize defining:

### Must-Specify (Phase 1)
1. **Tier state machines** — full Arc/Phase/Slice/Step FSMs with all transitions, guards, and events
2. **Artifact catalog** — every file, its schema, owner (agent vs projector), cross-references
3. **Naming conventions** — ID format, directory naming, file naming, slug generation rules
4. **On-disk layout** — complete directory tree with every file accounted for
5. **Cross-referencing rules** — ID-based with path lookup, broken-reference handling

### Should-Specify (Phase 2)
6. **STATE.md projection schemas** — what every tier's STATE.md contains
7. **Consistency validator** — full warning code catalog with detection logic
8. **Artifact immutability rules** — what's immutable when, snapshot-before-mutation protocol
9. **Decimal insertion protocol** — exact rules for when and how to insert

### Defer (future design spikes)
- Agent harness design (v41)
- Quality pipeline design (v42)
- GSD command porting (v43)
- Teach-mode equivalents (v46)
- Rust DB design (v44)

---

## 11. Sources

| Source | Confidence | Notes |
|--------|------------|-------|
| `.planning/milestones/v40/HANDOFF.md` | HIGH | Primary requirements document; all 7 output sections specified |
| `.planning/research/ARCHITECTURE.md` §5, §8 | HIGH | Event taxonomy and Step state machine already partially designed |
| `.planning/PROJECT.md` | HIGH | Cardinal rules, constraints, existing capabilities |
| `state-inputs/get-shit-done/bin/lib/artifacts.cjs` (via HANDOFF.md) | MEDIUM | GSD artifact registry pattern (10 exact-match + 2 pattern-match); HANDOFF.md describes structure |
| `state-inputs/get-shit-done/bin/lib/verify.cjs` (via HANDOFF.md) | MEDIUM | GSD health checks (19 warning codes); HANDOFF.md describes pattern |
| Atlassian / Jira Documentation (webfetch) | HIGH | Epic→Story→Task hierarchy, workflow states, link types |
| Azure DevOps Documentation (webfetch) | HIGH | Epic→Feature→PBI→Task hierarchy, work item states, area/iteration paths |
| Linear Documentation (attempted, 404) | LOW | Project→Cycle→Issue hierarchy inferred from training data + community knowledge |
| `src/state_core/schema.py` (via HANDOFF.md reference) | HIGH | 34+ event types, aggregate definitions — the existing schema this design must extend |
| `src/state_core/projector.py` (via HANDOFF.md reference) | HIGH | CQRS projection engine (19 handlers, 3 cache tables) — already exists |
