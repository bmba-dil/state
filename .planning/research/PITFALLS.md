# Pitfalls Research — Build Hierarchy & Artifact System Architecture

**Domain:** Multi-tier product hierarchy for agentic workflow engine (Arc → Phase → Slice → Step)
**Researched:** 2026-05-06
**Confidence:** HIGH on event-sourcing/cross-referencing patterns (Azure CQRS + UML HSM formalisms); HIGH on GSD coupling (direct experience from v1-v13 implementation); MEDIUM on naming convention drift (patterns inferred from large-scale project post-mortems); MEDIUM on frontmatter schema bloat (no dedicated literature — synthesized from YAML best practices + pydantic `extra="forbid"` experience)

---

## Critical Pitfalls

### Pitfall 1: Hierarchy Over-Engineering — Too Many Tiers, Too Many States

**What goes wrong:**
The four tiers (Arc → Phase → Slice → Step) each get a full-blown state machine with 6-8 states each, plus sub-states ("planned_with_dependencies_resolved", "in_progress_with_snapshots_pending"). Every tier gets its own `STATE.md`, its own events, its own projector handlers, its own verifier. The resulting combinatorial explosion creates more state transitions than the system actually needs — 50+ states across 4 tiers where 12-15 meaningful states would suffice.

**Why it happens:**
Harel statecharts and UML HSMs formalize hierarchical state nesting as a best practice, and the temptation is to apply it uniformly. When each tier feels "important" (it is!), the natural impulse is to model it as fully as the richest tier (Step). The existing Step FSM already has 8 states + transitions; copying that pattern to Arc/Phase/Slice produces 4 × 8 = 32 states plus cross-tier transitions, guards, and event deferral. Wikipedia explicitly warns about the "state and transition explosion" phenomenon — HSMs were invented to *counter* this, not to justify it.

**How to avoid:**
**Tier states must vary by complexity.** The Step tier justifies 8 states because it runs the full discuss→plan→execute→verify cycle. Arc, Phase, and Slice are scoping/coordination containers — they need far fewer states:

| Tier | Maximum states | Justification |
|------|---------------|---------------|
| Step | 8 (idle/discussing/planning/executing/verifying/done/blocked/abandoned) | Full cycle tier |
| Slice | 4 (planned/worktree_ready/in_progress/shipped_reverted) | Worktree lifecycle only |
| Phase | 4 (planned/in_progress/verified/shipped_abandoned) | Rollup aggregation only |
| Arc | 3 (planned/in_progress/shipped_abandoned) | Scoping container only |

**No substates at Arc/Phase/Slice.** If you find yourself wanting a substate (e.g., "planned_with_dependencies_resolved"), that's a signal that the dependency DAG should handle it, not the state machine. The scheduler already knows which Slices are unblocked — don't replicate that knowledge in the Slice state machine.

**No `STATE.md` at every tier.** STATE.md files are CQRS projections from the event store. Only create them at tiers where a human or agent needs to read a rollup. Step, Slice, and Phase are likely candidates; Arc is questionable (its STATE.md would just be "X% of phases done" — the dashboard already shows this).

**Warning signs:**
- You're designing a state transition diagram for Arc and it has more than 5 boxes
- Someone asks "can a Phase be in the 'partially verified' state?"
- The event taxonomy grows beyond the existing 28+ event types because "Arc needs a `state.arc.substep_planned` event" 
- You're writing guard conditions that reference *other tiers'* states

**Phase to address:** v40 (design) — lock tier state counts in the tier definitions themselves. v14 (implementation) — the Step FSM implementation must not exceed 8 states.

---

### Pitfall 2: Under-Specified Cross-Referencing — Orphan Artifacts

**What goes wrong:**
A SLICE.md references `phase_id: auth-oauth-migration`, but someone renames the Phase directory from `auth-oauth-migration` to `auth-oauth-v2`. The reference breaks silently. The Slice is now orphaned — it exists on disk but no Phase claims it, no scheduler picks it up, no verifier checks it. Orphan artifacts accumulate, the `validate_consistency` health check fires warnings that nobody reads, and eventually a `state stats` command returns wrong numbers because it can't resolve half the references.

**Why it happens:**
Cross-referencing in file-based systems is always eventual — there's no database foreign key to enforce referential integrity. GSD's current `verify.cjs` has 19 warning codes explicitly for this problem (drift between STATE.md, ROADMAP.md, REQUIREMENTS.md, and filesystem). The HANDOFF.md acknowledges this: "agents easily miss updating tracking files." When references are by ID string (not content hash or UUID), renames and moves break them silently.

**How to avoid:**
**Three-tier defense for cross-references:**

1. **UUIDs as canonical IDs, slugs as display names.** Every Arc/Phase/Slice/Step gets a ULID (already used in `events.sqlite`). The ULID is the canonical reference. The human-readable slug is a display convenience. `SLICE.md` frontmatter stores `phase_id: 01JQXYZ...` (the ULID), not `phase_id: auth-oauth-migration` (the slug). Renaming a slug never breaks references.

2. **Content-addressable cross-references for artifacts (not just IDs).** When STEP.md references another step via `depends_on`, include a content hash of the target artifact at the time of reference creation. At verification time, the verifier checks: "Is this hash still the current content? If not, flag a stale-reference warning." This catches drift that UUIDs alone miss (e.g., the target STEP.md was rewritten to remove the capability this step depends on).

3. **`validate_consistency` as a daemon health check, run on every state change.** Not a manual CLI command. When any event advances a Step/Slice/Phase/Arc, the daemon's post-commit hook runs a lightweight consistency scan: "Do all `depends_on` targets still exist? Do all parent-child relationships resolve? Are any artifacts orphaned?" Broken references become `state.reference.broken` events that trigger TUI toasts immediately — not silent warnings in a log file.

**Cross-reference schema (add to tier definitions):**
```yaml
# Every reference in any artifact frontmatter must conform to:
ref:
  id: "01JQXYZ..."          # ULID (canonical, never changes)
  slug: "auth-oauth-migration"  # display slug (may change)
  content_hash: "sha256:abc..." # pinned at reference-creation time
  kind: "parent | blocks | soft | data"  # relationship type
```

**Warning signs:**
- Any frontmatter field that stores another artifact's slug as its sole identifier
- A rename operation that doesn't also update all back-references
- `state stats` output that disagrees with `ls .state/build/arcs/ | wc -l`
- The health check fires more than 3 warnings within a single session

**Phase to address:** v40 (design) — define the cross-reference schema and UUID generation rules. v14 (implementation) — implement `validate_consistency` in the daemon post-commit hook. v42 (quality pipeline) — the verifier must check cross-reference integrity as a gate.

---

### Pitfall 3: Inconsistent State Machine Behavior Across Tiers

**What goes wrong:**
The Step FSM has a `BLOCKED` state with an explicit `unblock` transition and a guard condition: "cannot unblock if any `blocks`-kind dependency is still not DONE." The Slice FSM has no `BLOCKED` state at all — a blocked Slice is modelled as "still in `in_progress` but its only Step is blocked." Now two different tiers model "blocked" differently: Step has an explicit state, Slice uses implicit state-through-child-state. When the scheduler asks "is this Slice blocked?", it must either query the Slice state (which says `in_progress`) or recurse into Steps (which says one is `BLOCKED`). Worse: what happens when the Arc has 3 Phases, 2 are `shipped`, 1 is `in_progress` with a blocked Slice? Is the Arc blocked? The answer depends on which tier you ask.

**Why it happens:**
UML state machines formalize hierarchical state nesting, but they assume a parent explicitly enters/exits substates. In an event-sourced system where tiers advance independently in response to their own events, the parent doesn't "enter" the child's state — it projects it. When each tier's FSM is designed independently (as it should be for separation of concerns), the interaction semantics aren't codified. The Wikipedia article on UML HSMs explicitly notes this: "orthogonal regions would be only approximately orthogonal (i.e., not truly independent)" — our tiers are the same problem.

**How to avoid:**
**Define explicit, enumerated "composite state" rules for each parent-child pair:**

| Parent | Child | Composite rule |
|--------|-------|---------------|
| Arc | Phase | Arc is `in_progress` if ANY Phase is `in_progress`; Arc is `shipped` if ALL Phases are `shipped`; Arc is `abandoned` if ALL Phases are `abandoned` |
| Phase | Slice | Phase is `in_progress` if ANY Slice is `in_progress`; Phase is `shipped` if ALL Slices are `shipped`; Phase is `verified` if ALL Slices are `shipped` AND the Phase-level verifier passes |
| Slice | Step | Slice is `in_progress` if ANY Step is in `{executing, verifying}`; Slice is `blocked` (implicit) if ALL non-done Steps are `blocked`; Slice is `shipped` if ALL Steps are `done` |

**These rules must be in the projector, not the FSM.** The projector (CQRS read-side) recomputes parent state from child events. The parent FSM (command-side) never transitions based on child state — the projector writes the parent's STATE.md and cache table, and the scheduler reads that. This keeps the command-side FSMs simple (each tier only transitions on its own events) while the read-side handles the aggregation.

**No tier should have a `BLOCKED` state if a child tier already has one.** Step has `BLOCKED`. Slice does not need `BLOCKED` — the projector computes "Slice is effectively blocked" from Step states. Don't replicate state semantics across tiers.

**Warning signs:**
- Two tiers have the same state name with different semantics (e.g., `in_progress` means "agent is working" for Step but "at least one child is working" for Slice)
- A tier's FSM transition guard references another tier's state directly (e.g., "Slice can advance to `shipped` only if Phase is `in_progress`")
- The scheduler must traverse the hierarchy to determine if work is unblocked

**Phase to address:** v40 (design) — define composite state rules explicitly in the tier definitions. v14 (implementation) — the projector must implement these rules. v42 (quality pipeline) — cross-tier integration verifier.

---

### Pitfall 4: Naming Convention Drift

**What goes wrong:**
The first Arc is `arc-01`. The second is `auth-arc`. The third is `01JQXYZ...` (ULID-only). Phase naming is `arc-01-phase-003` for one Arc, `auth-oauth` for another. Slice naming is `phase-003-slice-012` for one Phase, `slice-004` (global counter) for another. Renaming an Arc from `arc-01` to `auth-core` breaks every Phase/Slice/Step reference that used the old name. Decimal insertions (`022.1`) work for Phases but not for Slices or Steps. A new developer reads the directory tree and cannot determine the hierarchy from directory names alone.

**Why it happens:**
Naming conventions feel "obvious" at design time — the designer picks a pattern that makes sense for the first 3 Arcs. But as the project grows (15-25+ Arcs, 60-100+ Phases, hundreds of Slices), edge cases emerge: cross-Arc dependencies, gap-closure insertions, renames for clarity, slugs that collide, slugs that are too long for filesystems. Without a single, enforced, machine-validated naming schema, each new Arc/Phase/Slice creator makes slightly different choices. Over months, the directory tree becomes illegible.

**How to avoid:**
**Machine-enforced naming, not convention-based naming.** Every `new-arc`, `new-phase`, `new-slice`, `new-step` command MUST generate IDs from a deterministic, documented algorithm. No human-chosen slugs as canonical IDs.

**Recommended ID schema:**

| Tier | ID format | Example | Generation rule |
|------|-----------|---------|-----------------|
| Arc | `arc-{seq:03d}` | `arc-001` | Global sequential counter in `events.sqlite` |
| Phase | `arc-{seq:03d}-phase-{seq:03d}` | `arc-001-phase-003` | Sequence within parent Arc |
| Slice | `arc-{seq:03d}-phase-{seq:03d}-slice-{seq:03d}` | `arc-001-phase-003-slice-012` | Sequence within parent Phase |
| Step | `arc-{seq:03d}-phase-{seq:03d}-slice-{seq:03d}-step-{seq:03d}` | `arc-001-phase-003-slice-012-step-004` | Sequence within parent Slice |

**Why hierarchical IDs:**
- The ID itself encodes the full hierarchy path — no cross-reference lookup needed to determine a Step's parent Phase
- Sortable: `ls .state/build/arcs/arc-001/phases/` returns Phases in creation order
- Decimal insertions work naturally: `arc-001-phase-003.1` (inserted between 003 and 004). The `.X` suffix signals "gap-closure, not originally planned"
- Unambiguous: no two artifacts can ever have the same ID, even across Arcs

**Slug as display-only metadata:**
Each artifact ALSO has a human-readable `slug` in its frontmatter (`slug: auth-oauth-migration`). The slug is used in TUI displays, sidebar labels, and toasts. The slug can be renamed without breaking anything. The ID never changes. The directory name on disk is the slug (for human readability when browsing `.state/`), but all cross-references use the ID.

**Directory layout uses slugs:**
```
.state/build/
├── arcs/
│   └── auth-core/          # slug, not arc-001
│       └── phases/
│           └── oauth-migration/  # slug, not arc-001-phase-003
│               └── slices/
│                   └── anthropic-oauth/  # slug
│                       └── steps/
│                           └── discuss-approach/  # slug
│                               ├── STEP.md     # id: arc-001-phase-003-slice-012-step-004
│                               ├── DISCUSS.md
│                               ├── PLAN.md
│                               └── VERIFY.md
```

**Warning signs:**
- Two artifacts exist with the same name but different formats (e.g., `arc-01` and `arc-001`)
- A rename operation requires more than one file edit
- `grep -r "phase_id:" .state/build/` returns mixed formats (some by slug, some by ID)
- Someone asks "wait, how do I know which Arc this Slice belongs to?"

**Phase to address:** v40 (design) — lock the ID schema, slug rules, and directory naming conventions. v16 (build commands) — `new-arc`/`new-phase`/`new-slice` must implement the generation algorithm. v43 (GSD port map) — include rename commands with back-reference updating.

---

### Pitfall 5: On-Disk Layout Proliferation (Too Many Directories and Files)

**What goes wrong:**
The `.state/build/` directory tree grows unboundedly. Every Arc gets its own `arcs/{slug}/` directory with `ARC.md`, `STATE.md`, `phases/`, `slices/`, `steps/` subdirectories. At 15-25 Arcs, 60-100 Phases, 400 Slices, and 2000 Steps, the on-disk tree has ~8000 files (each Step has STEP.md + DISCUSS.md + PLAN.md + EXECUTE.log + VERIFY.md = 5 files). Filesystem operations slow down, `git status` takes seconds, and macOS Finder chokes on `.state/build/arcs/auth-core/phases/oauth-migration/slices/anthropic-oauth/steps/discuss-approach/DISCUSS.md`.

Additionally, every tier creates a `STATE.md` (4 tiers × 100+ directories = 400+ STATE.md files). These are CQRS projections — they're rebuildable from the event store. Storing them on disk is redundant cache.

**Why it happens:**
The HANDOFF.md's initial directory layout sketch is deeply nested (5-6 levels deep for a single Step's artifacts). The design impulse is "every artifact gets its own directory, every directory gets a STATE.md, every relationship gets its own file." This mirrors GSD's `.planning/` layout which was designed for ~50 phases, not ~2000 Steps. The design didn't anticipate the scale.

**How to avoid:**
**Flatten where possible, nest only where hierarchy matters for human browsing.**

**Revised, flatter layout:**
```
.state/build/
├── arcs/
│   └── {arc-id}/                    # slug-based directory name
│       ├── ARC.md                   # arc definition (has frontmatter with phase list)
│       ├── phases/
│       │   └── {phase-id}/          # slug-based
│       │       ├── PHASE.md         # phase definition (has frontmatter with slice list)
│       │       └── slices/
│       │           └── {slice-id}/  # slug-based
│       │               ├── SLICE.md # slice definition (has frontmatter with step list)
│       │               └── steps/
│       │                   └── {step-id}/  # slug-based
│       │                       ├── STEP.md     # step definition + all metadata
│       │                       ├── ARTIFACTS.md # consolidated discuss+plan+verify+log
│       │                       └── snapshots/  # content-addressed, not per-Step dir
├── state/                       # CQRS projections (ONE per top-level, not per-directory)
│   ├── arcs.json                # all Arc state projections in one file
│   ├── phases.json              # all Phase state projections
│   ├── slices.json              # all Slice state projections
│   └── steps.json               # all Step state projections
├── events.sqlite                # authoritative event store (same as current)
├── templates/                   # artifact templates
├── skills/                      # build-mode skills
└── config/                      # build-mode config
```

**Key flattening decisions:**

1. **ONE `ARTIFACTS.md` per Step instead of 4 files.** DISCUSS.md, PLAN.md, VERIFY.md, and EXECUTE.log are consolidated into a single `ARTIFACTS.md` with clear section headers. The Step's frontmatter `state` field determines which section is "live." This reduces Step file count from 5 to 2.

2. **No per-directory STATE.md.** STATE projections live in `.state/build/state/` as JSON files (one per tier, rebuilt by the projector on every event). These are NOT committed to git (rebuildable from `events.sqlite`). They serve as fast read caches for the daemon, not as human-readable artifacts.

3. **Snapshots are content-addressed under a shared directory.** Not per-Step directories. Step ARTIFACTS.md references snapshot hashes; the snapshot service resolves them from the shared pool.

4. **No per-tier `STATE.md` files committed to git.** The projector rebuilds these. They're runtime caches, not source of truth. This directly addresses the HANDOFF.md's instruction: "STATE.md at each tier is a projector output, not agent-written."

**File count comparison:**

| Layout | Files for 20 Arcs / 80 Phases / 400 Slices / 2000 Steps |
|--------|-------------------------------------------------------|
| Nested (original sketch) | ~8,200 files (5 per Step + 1 STATE.md per directory) |
| Flattened (recommended) | ~2,480 files (2 per Step + 4 state projections + 80 ARC.md + 400 PHASE.md + 2000 SLICE.md) |

**Warning signs:**
- Any directory at depth > 5
- Any single Step having > 3 files
- A `find .state/build -name "*.md" | wc -l` that exceeds 150% of (2 × number_of_steps + number_of_slices + number_of_phases + number_of_arcs)
- `git status` taking > 1 second in `.state/build/`

**Phase to address:** v40 (design) — define the flattened directory layout. v16 (build commands) — `new-step` creates the 2-file Step directory. v41 (agent harness) — the harness must know that ARTIFACTS.md is a consolidated file.

---

### Pitfall 6: Frontmatter Schema Bloat

**What goes wrong:**
ARC.md frontmatter grows to 30+ fields. PHASE.md adds another 25. SLICE.md adds 20. STEP.md, the busiest tier, accumulates 40+ fields including nested objects like `verify_contract[].steps[].type`, `depends_on[].metadata`, `model_profile.anthropic_options`, `snapshots[].timestamp`, `cost_cap.currency`, etc. Every field seems "necessary for completeness." The frontmatter becomes longer than the artifact body. Pydantic validation slows down. Human authors stop reading frontmatter. Agents start skipping `extra="forbid"` validation because "it's always failing on some new field someone added." The schema becomes unmanageable.

**Why it happens:**
Frontmatter is the only structured data in an otherwise freeform Markdown document. Every requirement that needs machine-readability becomes a frontmatter field. There's no pressure to prune because "it's just YAML — it doesn't hurt anything." But the HANDOFF.md explicitly warns: "STEP.md is the busiest." Without explicit field budgets, every tier's frontmatter converges toward STEP.md's complexity. The CQRS Azure docs highlight this: "The read and write representations of data often differ. Some fields that are required during updates might be unnecessary during read operations."

**How to avoid:**
**Tier-specific field budgets with explicit justification for every field.**

| Tier | Max required fields | Max optional fields | Justification |
|------|--------------------|--------------------|---------------|
| ARC.md | 6 | 4 | Scoping container — need id, title, status, goal, success_criteria, phases[] |
| PHASE.md | 7 | 5 | Milestone container — need id, arc_id, title, status, slices[], verify_rollup, success_criteria |
| SLICE.md | 7 | 5 | Concurrency unit — need id, phase_id, title, status, steps[], worktree, depends_on[] |
| STEP.md | 10 | 8 | Full cycle tier — need id, slice_id, title, status, goal, verify_contract, depends_on[], model_profile, snapshots[] |

**Enforcement mechanism:**
Every artifact schema is a pydantic model with `extra="forbid"` and a fixed set of fields. Adding a field requires a schema version bump, a migration plan, and a justification document. The CI pipeline runs `pydantic` validation on every `.md` file in `.state/build/` — files with extra fields fail the build.

**Frontmatter is for machine-readable metadata, not prose.**
If a field contains human-readable text longer than 200 characters, it belongs in the Markdown body, not the frontmatter. The frontmatter is a structured index. The body is the narrative. This rule alone prunes many over-engineered fields (e.g., `description: <500-word paragraph>` → moved to body).

**Use the event store for temporal data.**
Fields like `snapshots[]`, `cost_accounting`, and `timing_history` are temporal data — they grow over time. They belong in `events.sqlite`, not in static frontmatter. The frontmatter stores only the *current* snapshot ref and cost cap; the full history lives in the event stream and is queryable via the projector.

**Warning signs:**
- Any tier's frontmatter exceeding 30 lines
- A field that's a list of objects with > 3 sub-fields each
- A field named `metadata` or `extra` or `misc` (escape hatch for unbounded growth)
- Someone asks "can I add just one more field to ARC.md? It's only used by the TUI..."

**Phase to address:** v40 (design) — define the pydantic models with field budgets. v16 (build commands) — artifact creation must validate against the pydantic schema. v42 (quality pipeline) — schema drift detection in the health checks.

---

### Pitfall 7: Over-Coupling to GSD's Legacy Hierarchy Model

**What goes wrong:**
The four-tier hierarchy is designed by copying GSD's two-tier (milestone→phase) and splitting each tier in half. Arc = "big milestone," Phase = "small milestone," Slice = GSD's "phase," Step = "task." The mental model inherits GSD's serial execution assumption ("phases run one after another"), GSD's linear roadmap, GSD's verification-at-the-end model, and GSD's single-directory `.planning/` layout. The hierarchy looks like four tiers but behaves like two tiers with extra nesting. The DAG scheduler is underused because the hierarchy design assumes serial progression. The concurrency model collapses.

**Why it happens:**
The HANDOFF.md explicitly maps GSD concepts to the new tiers: "Arc = no GSD equivalent," "Phase = GSD's milestone," "Slice = GSD's phase," "Step = GSD's task/wave area." This mapping is a useful onboarding aid but dangerous as a design template. The designer knows GSD intimately (13 milestones shipped on this project), so GSD's patterns are the mental default. The PROJECT.md states "GSD's two-stage milestone→phase hierarchy [is] intentionally replaced," but it doesn't specify *how* the new tiers differ behaviorally, only structurally.

**How to avoid:**
**Define each tier by its behavioral primitives, not by its GSD analogy.**

| Tier | Behavioral primitive (not GSD analogy) |
|------|--------------------------------------|
| Arc | **Feature block.** A collection of Phases that together deliver a user-visible capability. An Arc has a goal and success criteria. Arcs can depend on other Arcs (cross-cutting concerns). |
| Phase | **Milestone with rollup verification.** A Phase groups Slices that must all be verified as a unit. Phase-level verification is cross-Slice integration testing, not just "all Slices passed individually." |
| Slice | **Concurrency unit with worktree isolation.** A Slice is the quantum of parallel work. Two Slices in the same Phase can execute concurrently if their DAG edges don't block each other. A Slice equals one worktree equals one git branch. |
| Step | **The only tier that runs the discuss→plan→execute→verify cycle.** Steps within a Slice are serial. The Step is where agents think, plan, code, and verify. All other tiers are coordination. |

**Explicit anti-GSD rules to encode in the design:**

1. **No "roadmap" that is a linear list.** The roadmap is a DAG of Arcs. If two Arcs have no `depends_on` edge, they can be worked on concurrently by different sessions.
2. **No "verification at the end."** Verification is continuous — every Step verifies itself, every Slice verifies its Steps, every Phase verifies its Slices. The Arc-level verifier is a lightweight integration check, not a big-bang "does everything work?" gate.
3. **No "one active thing at a time."** The scheduler can dispatch multiple Slices across multiple Arcs simultaneously. The only constraints are `depends_on` DAG edges and worktree availability.
4. **No `.planning/` monolith.** `.state/build/` is a federated tree, not a single flat directory. Each Arc's subtree is independently navigable.

**Warning signs:**
- A design document says "this is like GSD's X but..."
- The DAG scheduler only dispatches Slices within a single Phase (no cross-Phase concurrency)
- The roadmap is presented as a numbered list rather than a DAG
- Verification is described as happening "after everything is built"

**Phase to address:** v40 (design) — behavioral primitives must be defined without GSD analogies. v43 (GSD port map) — ensure ported commands are redesigned for the new concurrency model, not copied verbatim.

---

### Pitfall 8: State Machine Deadlocks — Cross-Tier Blocking

**What goes wrong:**
Step A depends on Step B (via `depends_on: kind=blocks`). Step B is in a Slice that depends on a Slice containing Step A's Slice (cross-Slice dependency cycle). Or: Phase X can't advance to `verified` because Slice Y is `in_progress`, but Slice Y can't advance because its Step Z is `blocked`, and Step Z is blocked waiting for Phase X to reach `shipped` before an external service is available. The system deadlocks: two tiers are each waiting for the other to advance, and neither can.

**Why it happens:**
Hierarchical state machines in UML allow parent states to depend on child states ("AND decomposition" in orthogonal regions). But when dependencies cross tier boundaries in both directions (a Phase depends on a Slice's state AND a Slice depends on a Phase's state), a cycle forms. The Wikipedia article notes that in UML statecharts, "the general case of mutual dependency results in multiplicative complexity." In an event-sourced system where each tier advances on its own events, a deadlock means no events fire, the scheduler finds nothing unblocked, and the system silently stalls.

**How to avoid:**
**DAG edges only point in one direction across tiers: child → parent, never parent → child.**

| Dependency direction | Allowed? | Example |
|---------------------|----------|---------|
| Step → Step (same Slice) | YES | Step B `blocks` on Step A |
| Slice → Slice (same Phase) | YES | Slice Y `blocks` on Slice X |
| Phase → Phase (same Arc) | YES | Phase-004 `blocks` on Phase-003 |
| Arc → Arc | YES | Arc-005 `blocks` on Arc-001 |
| Step → Slice | NO | A Step cannot depend on a Slice |
| Slice → Phase | NO | A Slice cannot depend on a Phase |
| Phase → Arc | NO | A Phase cannot depend on an Arc |
| Child → Parent (any tier) | NO | A tier cannot depend on its parent container |

**The scheduler must detect and reject cross-tier dependency cycles at edge-creation time.** When a `new-step` command adds a `depends_on` edge, the scheduler runs a quick cycle check on the full DAG (all tiers flattened into one graph with the direction rule enforced). If a cycle would form, the command is rejected with a clear error message naming the cycle.

**Cross-tier coordination is handled by events, not by `depends_on` edges.**
If Slice Y truly needs Phase X to reach `shipped` before it can proceed, the mechanism is:
1. Slice Y subscribes to `state.phase.completed` for Phase X
2. When Phase X fires `state.phase.completed`, an event handler advances Slice Y's state
3. The Slice does NOT declare `depends_on: phase-x` — that's a forbidden edge

This pattern keeps the DAG acyclic by moving cross-tier waits into the reactive event system rather than the dependency graph.

**Deadlock detection as a daemon health check:**
Every scheduler tick, check: "Are there any Slices in `in_progress` for > N minutes with zero Step state changes? If so, log a deadlock warning." This is a runtime guard, not a design-time guard — it catches deadlocks that slip past the edge-creation check.

**Warning signs:**
- A `depends_on` edge references an artifact at a different tier level
- The scheduler's `schedule_tick()` returns an empty list for > 5 minutes while Slices show `in_progress`
- Someone says "this Slice can't start until the Phase above it is verified"
- A cycle-detection algorithm finds a path that traverses both `child → parent` AND `parent ← child` directions

**Phase to address:** v40 (design) — codify the one-direction DAG rule in the tier definitions. v14 (implementation) — Step FSM must not have dependencies on Slice/Phase states. v42 (quality pipeline) — the verifier must check for deadlock conditions.

---

### Pitfall 9: Artifact Immutability Violations — Mid-Execution Plan Changes

**What goes wrong:**
A STEP.md is planned (state = `planning`), the agent moves to `executing`, and then someone edits the STEP.md to add a new `verify_contract` item. The verifier now checks a contract that wasn't part of the original plan. Even worse: someone edits an ARC.md `success_criteria` while its child Phases are `in_progress`. The success criteria change retroactively, and Phase-003 fails verification because it was built to the OLD criteria. Or: a SLICE.md `depends_on` edge is removed mid-execution, unblocking a Slice that was intentionally blocked, causing concurrent writes to the same files.

**Why it happens:**
Markdown files are mutable by design — any agent or human can edit them at any time. The event store records events but doesn't lock artifacts. The HANDOFF.md explicitly asks: "Once a STEP.md is planned and execution begins, can the plan be modified? Or is it immutable? What about ARC.md when a child Phase is in progress?" This is an open design question, and the tendency is to allow editing "because flexibility is good." But flexibility in a state machine creates non-deterministic behavior.

**How to avoid:**
**Tiered immutability rules — artifacts freeze at different points:**

| Artifact | Freezes when... | Can be modified after freeze? |
|----------|----------------|-------------------------------|
| STEP.md | Step enters `executing` | NO — the plan is a contract. Modify via a NEW Step that depends on this one. |
| DISCUSS.md | Step enters `planning` | NO — discussions are historical record. New discussions go in ARTIFACTS.md notes. |
| PLAN.md | Step enters `executing` | NO — see STEP.md. |
| VERIFY.md | Step enters `done` | NO — verification results are evidence, not speculation. |
| SLICE.md | Slice enters `worktree_ready` | Partial — `depends_on` edges freeze, but `steps[]` can grow as new Steps are planned. |
| PHASE.md | Phase enters `in_progress` | Partial — `slices[]` can grow, but `success_criteria` freeze. |
| ARC.md | Arc enters `in_progress` | Partial — `phases[]` can grow, but `goal` and `success_criteria` freeze. |

**Enforcement: The daemon's HTTP middleware checks artifact state before allowing writes.**
Every `Write` or `Edit` operation that targets an artifact in `.state/build/` passes through the daemon's mode-enforcement middleware (already designed for mode gating). The middleware checks: "Is this artifact frozen? If yes, reject the write with a structured error." This is NOT an agent-side convention — it's a server-side gate, just like the mode enforcement gate.

**For necessary mid-execution changes: create a successor artifact.**
If Step-004's plan is wrong and must be changed, the workflow is:
1. Abandon Step-004 (state → `abandoned`)
2. Create Step-005 with `depends_on: step-004 (kind: data)` to inherit its artifacts
3. Plan Step-005 with the corrected contract
4. Execute Step-005

This preserves audit trail, makes the change explicit (it's an event: `state.step.abandoned` → `state.step.planned`), and prevents silent plan drift.

**Warning signs:**
- Any documentation saying "you can edit the plan after starting work"
- An Edit tool call that succeeds against a frozen artifact (the middleware missed it)
- A verifier failure where the verify_contract doesn't match what was in STEP.md at plan time
- `git log` shows frontmatter changes AFTER the state machine advanced past `planning`

**Phase to address:** v40 (design) — codify immutability rules per tier. v14 (implementation) — Step FSM must enforce immutability on state transitions. v41 (agent harness) — the harness must provide "abandon and replan" workflow.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems in hierarchy design.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip UUIDs for cross-references, use slugs only | Faster initial implementation, readable in raw YAML | Every rename breaks references; orphan detection is impossible; `validate_consistency` floods warnings | Never — UUIDs are the foundation of referential integrity |
| Allow `depends_on` edges to cross tiers (Step → Phase) | Simpler to express "this needs that to be done" without event wiring | DAG cycles become undetectable; deadlocks become probabilistic; scheduler becomes non-deterministic | Never — event-based cross-tier coordination is the correct pattern |
| Put STATE.md at every directory level | "Complete" feel, mirrors GSD's approach | 400+ STATE.md files that are always stale because agents forget to update them; projector must rebuild them anyway | Never — the projector already does this; on-disk STATE.md files are redundant cache |
| Use GSD's flat `.planning/` directory structure | Familiarity, quicker initial implementation | 2000 Steps in one directory; impossible to browse; `git status` takes 5+ seconds | Never — the scale demands hierarchy |
| Store `snapshot` history in frontmatter as a list | Convenient single-file lookup | Frontmatter grows unboundedly; pydantic validation on 100+ snapshots per Step is slow | Never — snapshots are temporal data; they belong in `events.sqlite` |
| Omit `content_hash` from cross-references | Simpler `depends_on` schema, one less field to maintain | Silent drift when target artifact is modified; verifier checks a different contract than what existed at plan time | Only in v40 prototype (throwaway) |

---

## Integration Gotchas

Common mistakes when connecting the hierarchy to existing subsystems.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Event Store (v1)** | Defining new events without adding them to `schema.py`'s `*_EVENT_TYPES` Literal unions | Every new event type MUST be added to the appropriate Literal union in `schema.py`. The daemon's mode middleware already validates event prefixes against `BUILD_ONLY_EVENT_PREFIXES`. Missed literals = runtime validation failures. |
| **DAG Scheduler (v5)** | Scheduler assumes all `depends_on` edges are flat (Step→Step); doesn't handle cross-tier edges | Scheduler already has a reactive `schedule_tick()` that recomputes on `state.step.advanced`. The hierarchy design must emit the right trigger events for Arc/Phase/Slice transitions. A Phase advancing to `shipped` should trigger the scheduler to check for unblocked Slices in dependent Phases. |
| **Worktree Service (v4)** | Creating worktrees at the Arc or Phase level instead of the Slice level | Worktrees are per-Slice (already designed). One Slice = one worktree = one git branch. Never create worktrees at higher tiers — the concurrency model depends on Slice-level isolation. |
| **Projector (CQRS)** | Projector handlers assume linear event replay and don't handle out-of-order Arc/Phase events | The projector's `rebuild_all()` already replays events in `aggregate+seq` order. But cross-tier projections (e.g., "Arc state = f(Phase states)") need the projector to handle events at ALL tiers, not just Step events. Add Phase/Slice/Arc handlers to the existing 19-handler registry. |
| **Mode Enforcement (v11)** | Mode middleware rejects `state.arc.*` events when mode is `teach` — but teach mode needs Arc events for cross-mode dashboards | Teach mode should NOT see Build-mode events. The mode gate already enforces this via `BUILD_ONLY_EVENT_PREFIXES`. If a dashboard needs cross-mode data, it queries the event store directly (read-only), not through the event append path. |
| **Plugin Hooks (v8)** | `chat.system.transform` injects everything from STEP.md frontmatter (40+ fields) into the 8K context window | The harness (v41) must select which frontmatter fields are context-relevant. The `system.transform` hook should inject only: `{goal, state, verify_contract.summary, depends_on.summary}` — ~200 tokens, not ~2000 tokens. |

---

## "Looks Done But Isn't" Checklist

Things that appear complete in a hierarchy design but are missing critical pieces.

- [ ] **Cross-reference integrity:** Design has `depends_on` fields, but no `validate_consistency` specification, no UUID generation rule, no content-hash inclusion, no orphan detection → Looks done but breaks on first rename.
- [ ] **State composition rules:** Each tier has a state machine, but the rules for how child states compose into parent states aren't written down → Looks done but the scheduler can't determine if a Phase is ready.
- [ ] **Decimal insertion:** IDs are sequential, but the rules for inserting `phase-003.1` between `phase-003` and `phase-004` aren't specified → Looks done but breaks on first gap-closure task.
- [ ] **Artifact immutability:** Frontmatter schemas exist, but there's no specification of when each artifact freezes → Looks done but plans drift mid-execution.
- [ ] **Directory depth budget:** The tree is specified, but there's no rule limiting maximum nesting depth (e.g., "no directory deeper than 6 levels from `.state/` root") → Looks done but `git status` takes 5 seconds at scale.
- [ ] **Snapshot GC integration:** Snapshots are referenced in STEP.md, but the GC policy (which snapshots survive when a Step is abandoned? when a Slice is reverted?) isn't specified → Looks done but snapshot storage fills disk.
- [ ] **Projector handler coverage:** The projector has Step handlers, but no Arc/Phase/Slice handlers are specified → Looks done but `STATE.md` projections are always empty for higher tiers.
- [ ] **Naming collision detection:** Slugs are human-readable, but the `new-arc` command doesn't check if a slug already exists (at any tier) → Looks done but two Arcs get the same slug and one silently overwrites the other's directory.
- [ ] **Event type exhaustiveness:** Events are defined for "sunny day" paths (planned, started, shipped) but not for error/recovery paths (abandoned, reverted, blocked) across ALL four tiers → Looks done but the event store rejects the first abandoned Slice.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Orphan artifacts (broken cross-references) | MEDIUM | 1. Run `state validate-consistency --fix` which scans all artifacts for broken `depends_on` and `parent_id` references. 2. For each orphan, prompt the user: "Artifact SLICE.md at path X references non-existent Phase Y. [Adopt into nearest Phase] [Delete artifact] [Skip]." 3. If content-hash mismatch, offer diff view and manual resolution. |
| State machine deadlock (scheduler returns empty for > 5 min) | LOW | 1. Daemon health check detects the stall. 2. `state dag show --deadlocks` renders the blocked subgraph. 3. User manually unblocks one Step (via `state step unblock --force`) to break the cycle. 4. Scheduler recomputes and resumes. |
| Naming convention drift | HIGH | 1. Run `state migrate-ids --dry-run` which shows every artifact whose ID doesn't match the canonical format. 2. For each, generate the correct ID from the naming algorithm. 3. Update the artifact's `id` field and all back-references. 4. This is a migration, not a fix — requires a dedicated Arc/Phase to execute safely. |
| Frontmatter schema bloat | MEDIUM | 1. Run `state validate-schema --strict` which validates all artifacts against the current pydantic models with `extra="forbid"`. 2. For each extra field, offer: [Remove field (data loss)] [Migrate to body as prose] [Create a schema version bump]. 3. Schema version bumps require a migration Arc. |
| Directory proliferation (too many files) | LOW | 1. Run `state compact --mode=flatten` which: (a) consolidates DISCUSS/PLAN/VERIFY/EXECUTE into ARTIFACTS.md, (b) removes per-directory STATE.md files (projector rebuilds them), (c) archives old snapshots beyond GC policy. 2. This is a safe operation — all information is preserved, just reorganized. |
| GSD coupling (serial execution assumption baked into commands) | HIGH | 1. Audit each ported command for serial assumptions. 2. Commands that assume "one active thing at a time" (e.g., `progress` showing a linear list) must be redesigned for concurrent DAG display. 3. This is a v43 (GSD port map) concern — don't port a command until you've verified it's concurrent-safe. |

---

## Phase-Specific Warnings

| Phase (or milestone) | Likely Pitfall | Mitigation |
|----------------------|----------------|------------|
| v40 (design) | Over-engineering tier states | Lock state counts per tier in the design documents; no tier > 8 states |
| v40 (design) | GSD analogy dominating behavioral design | Define behavioral primitives without ANY GSD comparison in the tier definitions |
| v14 (implementation) | Step FSM with cross-tier dependencies | Step FSM must reference only Step states; no Slice/Phase state checks in transition guards |
| v14 (implementation) | Skipping Arc/Phase/Slice projector handlers | Add Phase/Slice handler stubs even if they're simple; the registry must be complete |
| v16 (build commands) | `new-arc` command with ad-hoc ID generation | Enforce the naming algorithm at the CLI level; reject manually-specified IDs that don't match |
| v16 (build commands) | Artifact creation without immutability enforcement | Daemon middleware must reject writes to frozen artifacts |
| v41 (agent harness) | Context injection of entire frontmatter | Only inject curated subset; ~200 tokens max per artifact |
| v42 (quality pipeline) | Verifier assumes single-tier (Step-only) | Design verifier to traverse all 4 tiers; rollup verifiers must be specified |
| v43 (GSD port map) | Porting commands that assume serial execution | Audit each command; redesign for DAG-based concurrency |

---

## Sources

- **UML State Machine (Wikipedia):** Hierarchically nested states, orthogonal regions, state explosion, RTC execution model, event deferral, transition execution sequence. *(HIGH confidence — formal specification)* https://en.wikipedia.org/wiki/UML_state_machine
- **Azure CQRS Pattern (Microsoft Learn, updated 2025-02-20):** Command/Query separation, eventual consistency, materialized views, Event Sourcing integration, increased complexity warning. *(HIGH confidence — official Azure documentation)* https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs
- **Martin Fowler on CQRS (2011-07-14):** "CQRS adds risky complexity," bounded context applicability, ReportingDatabase as lighter alternative, "you should be very cautious about using CQRS." *(MEDIUM confidence — industry authority but 15 years old; principles still apply)* https://martinfowler.com/bliki/CQRS.html
- **GSD v1-v13 implementation experience:** 13 shipped milestones, 784+ tests, ~26K LoC. Direct experience with: `artifacts.cjs` (canonical registry), `state.cjs` (STATE.md tracking), `verify.cjs` (19 warning codes for drift detection), `frontmatter.cjs` (YAML schema enforcement). *(HIGH confidence — first-hand project artifacts)*
- **Project HANDOFF.md (v40):** Explicit acknowledgment of tracking-file consistency problem ("agents easily miss updating tracking files"), artifact catalog design requirements, cross-referencing rules, naming convention open questions. *(HIGH confidence — project source document)*
- **Existing codebase (`schema.py`, `projector.py`, `kernel.py`):** Current event taxonomy (28+ events, 9 aggregates), StepMachine skeleton (15 lines, 8 states), CQRS projector (19 handlers, 3 cache tables). *(HIGH confidence — shipped code with passing tests)*
- **ROADMAP.md:** 38 milestones, 260+ phases, v40-v50 design spike purpose, Tier 3a/3b build domain decomposition. *(HIGH confidence — project planning document)*

---

*Pitfalls research for: Build Hierarchy & Artifact System Architecture (v40 design-phase milestone)*
*Researched: 2026-05-06*
*Version: 1.0 — Initial research covering 9 critical pitfalls, technical debt patterns, integration gotchas, recovery strategies, and phase-specific warnings.*
