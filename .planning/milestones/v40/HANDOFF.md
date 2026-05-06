# v40 Handoff: Build Hierarchy & Artifact System Architecture

## Milestone Goal

Fully architect the four-tier product hierarchy (Arc → Phase → Slice → Step), its on-disk file structure, its artifact catalog, its cross-referencing rules, its naming conventions, its state machines, and its tracking-file consistency model. This is the **backbone** of the entire Build mode — everything downstream (harness, quality, workflow, GSD mapping) depends on the decisions made here.

## Relationship to GSD

- **Arc** = no GSD equivalent. It is a feature block / project branch containing many phases. Think "the auth system" or "the plugin framework." It is a scoping container for multiple milestones.
- **Phase** = GSD's "milestone." A Phase owns multiple Slices and defines success criteria at the milestone level.
- **Slice** = GSD's "phase." A Slice is the concurrency unit (one worktree per Slice). It owns multiple Steps and is the quantum of work that gets reviewed, verified, and shipped.
- **Step** = GSD's "task/wave area." The Step is the only tier that runs the full discuss→plan→execute→verify cycle. Steps within a Slice run serially; Slices run concurrently.

## What This Milestone Must Produce

### 1. Tier Definitions (one document per tier)

For each of the four tiers, produce a complete specification:

**Arc:**
- State machine states: `planned → in_progress → shipped | abandoned`
- What events advance it (`state.arc.created`, `state.arc.retired`, `state.arc.updated`)
- What artifacts it owns (ARC.md)
- What frontmatter fields ARC.md requires (id, title, status, goal, success_criteria, depends_on, phases, opencode_surface)
- How arcs relate to each other (can arcs depend on arcs? cross-arc integration?)
- How an arc gets created, planned, tracked, and retired
- What "arc planned" means — a collection of phases with goals, not a detailed implementation plan

**Phase:**
- State machine states: `planned → in_progress → verified → shipped | abandoned`
- What events advance it (`state.phase.planned`, `state.phase.started`, `state.phase.verified`, `state.phase.completed`)
- What artifacts it owns (PHASE.md)
- What frontmatter fields PHASE.md requires (arc_id, slices, verify_rollup, success_criteria, depends_on)
- How phase planning works — what level of detail? What's the relationship to slice planning?
- How a phase is verified (it aggregates Slice rollups)

**Slice:**
- State machine states: `planned → worktree_ready → in_progress → shipped | reverted`
- What events advance it (`state.slice.planned`, `state.slice.worktree_ready`, `state.slice.shipped`, `state.slice.reverted`)
- What artifacts it owns (SLICE.md)
- What frontmatter fields SLICE.md requires (phase_id, worktree, steps[], snapshot_ref, depends_on)
- The worktree lifecycle (create, bootstrap, active, ship-or-revert, GC)
- How Slice-level snapshots work (before execution, after verification)
- How Slices depend on each other within a Phase (DAG edges)

**Step:**
- State machine states: `idle → discussing → planning → executing → verifying → done | blocked | abandoned`
- The full FSM with transition guards (already partially designed in ARCHITECTURE §8.1)
- What events advance it (10 event types already defined)
- What artifacts it owns (STEP.md, DISCUSS.md, PLAN.md, EXECUTE.log, VERIFY.md)
- What frontmatter fields STEP.md requires (goal, verify_contract, depends_on[], model_profile, snapshots[], cost_cap)
- The `depends_on` edge kinds: `blocks` (hard), `soft` (suggested), `data` (artifact-producing)
- How snapshots work at Step boundaries (pre_execute, pre_verify)
- What happens on verify failure (retry loop, max retries?)
- What happens on block (unblock trigger, timeout?)
- What happens on abandon (cleanup, artifact preservation?)

### 2. On-Disk File Structure

Design the complete `.state/build/` directory tree:

```
.state/build/
├── arcs/
│   └── {arc-id}/
│       ├── ARC.md              ← arc definition + frontmatter
│       ├── STATE.md            ← arc-level state projection
│       └── phases/
│           └── {phase-id}/
│               ├── PHASE.md    ← phase definition + frontmatter
│               ├── STATE.md    ← phase-level state projection
│               └── slices/
│                   └── {slice-id}/
│                       ├── SLICE.md     ← slice definition + frontmatter
│                       ├── steps/
│                       │   └── {step-id}/
│                       │       ├── STEP.md       ← step definition + goal
│                       │       ├── DISCUSS.md    ← discuss-phase output
│                       │       ├── PLAN.md       ← plan-phase output
│                       │       ├── VERIFY.md     ← verify-phase output
│                       │       └── EXECUTE.log   ← execution log
│                       ├── worktree/             ← git worktree (not committed)
│                       └── snapshots/            ← content-addressed snapshots
├── intel/              ← codebase intelligence (parallel with GSD)
├── codebase/           ← codebase mapping (parallel with GSD)
├── graph/              ← knowledge graph (parallel with GSD)
├── decisions/          ← gray-area decision log
├── patterns/           ← pattern library
├── skills/             ← build-mode skills (opencode auto-discovers)
├── templates/          ← artifact templates (ARC.md, PHASE.md, etc.)
└── config/             ← build-mode configuration
```

Every directory, every file, every naming convention decided.

### 3. Artifact Catalog

Formalize exactly which artifacts exist at each tier, their schemas (pydantic models with `extra="forbid"`), their frontmatter requirements, and their cross-reference rules:

| Artifact | Tier | Creator | Schema | Cross-refs |
|----------|------|---------|--------|------------|
| ARC.md | Arc | `new-arc` command | TBD | references other arcs via `depends_on` |
| PHASE.md | Phase | `new-phase` command | TBD | references parent arc, child slices |
| SLICE.md | Slice | `new-slice` command | TBD | references parent phase, child steps, depends_on edges |
| STEP.md | Step | plan-step command | TBD | goal, verify_contract, depends_on[], model_profile, cost_cap |
| DISCUSS.md | Step | discuss-step command | TBD | captures gray-area decisions, locked choices |
| PLAN.md | Step | plan-step command | TBD | task decomposition, test plan, risks, threat model |
| VERIFY.md | Step | verify-step command | TBD | pass/fail + evidence from all verifier levels |
| EXECUTE.log | Step | execute-step command | structured log | per-subtask commit hashes, timing, deviations |
| STATE.md | All tiers | projector (daemon) | projection schema | auto-generated from event stream |
| DECISIONS.md | Arc/Phase | gray-area routing | TBD | ambiguous decisions surfaced by planner |

For each artifact, specify:
- Full pydantic model (or the design contract for one)
- Frontmatter fields (required vs optional)
- How it's validated at creation time
- How it's cross-referenced (what other artifacts link to it)
- How it's updated (manual by agent vs automatic by daemon)
- How it's discovered (path convention, registry, or content-addressable)

### 4. Naming Conventions

- Arc IDs: how are they formatted? (`arc-001`, `auth-arc`, UUID-based?)
- Phase IDs: how do they relate to their parent arc? (`arc-001-phase-003`, decimal for inserts?)
- Slice IDs: how do they relate to their parent phase? (`phase-003-slice-012`)
- Step IDs: how do they relate to their parent slice? (`slice-012-step-004`)
- How are decimal insertions handled? (GSD uses `022.1`, `022.2` for gap-closure)
- File naming: what format for ARC.md, PHASE.md, SLICE.md, STEP.md, PLAN.md, etc.?
- Directory naming: arc dirs, phase dirs, slice dirs, step dirs

### 5. Cross-Referencing Rules

- How does ARC.md reference its phases? (by ID? by path? by content hash?)
- How does PHASE.md reference its parent arc and child slices?
- How does SLICE.md reference depends_on edges?
- How does STEP.md reference depends_on edges?
- How does PLAN.md reference the STEP.md goal?
- How does VERIFY.md reference PLAN.md must-haves?
- How does the verifier resolve these references at verification time?
- What happens when a reference is broken (deleted target, renamed target)?

### 6. Tracking File Consistency Model

This is critical — you noted agents easily miss updating tracking files. Design a model where:

- **STATE.md at each tier is a projector output**, not agent-written. The daemon's CQRS projector rebuilds STATE.md from the event stream. Agents NEVER write STATE.md directly.
- **Progress tracking is event-driven**: when a Step advances to DONE, the projector updates:
  - The Slice's STATE.md (step count, completion percentage)
  - The Phase's STATE.md (slice rollup)
  - The Arc's STATE.md (phase rollup)
- **Health validation**: a `validate_consistency` function (like GSD's W011) detects when filesystem state diverges from event-store state
- **Reconciliation**: on daemon startup, projector replays all events to rebuild STATE.md files from scratch — they are throwaway projections, not source of truth

### 7. Mental Model

A visual or textual model of how all four tiers compose:

```
ARC: Auth System Overhaul
├── PHASE: OAuth Provider Migration (milestone-level)
│   ├── SLICE: Anthropic OAuth (worktree-isolated)
│   │   ├── STEP: Discuss approach
│   │   ├── STEP: Plan implementation
│   │   ├── STEP: Execute OAuth flow
│   │   ├── STEP: Verify stealth headers
│   │   └── STEP: Ship + PR
│   ├── SLICE: Google OAuth
│   └── SLICE: GitHub OAuth
├── PHASE: Token Refresh System
│   ├── SLICE: Refresh loop
│   └── SLICE: Rotation logic
└── PHASE: Auth Error Recovery
```

With concrete examples of every artifact at every tier, filled in with realistic content.

## Success Criteria

1. A developer can read the four tier definitions and understand exactly what each tier is, what it owns, and how it relates to others — without reading any other document.
2. The `.state/build/` directory tree is fully specified with every file, directory, and naming convention.
3. The artifact catalog lists every artifact, its schema, its creator, its cross-references, and its update mechanism.
4. The tracking file consistency model ensures STATE.md files are always consistent with the event store (projector-built, not agent-written).
5. The mental model is concrete enough that a new ARC.md, PHASE.md, SLICE.md, and STEP.md could be generated from templates.

## Research Inputs

Read these before and during the discuss-phase:

**Primary reference — shipped state code:**
- `src/state_core/schema.py` — 34+ event types, aggregate definitions, mode configuration, subtree validation (this IS the current schema; the design must extend it)
- `src/state_core/projector.py` — CQRS projection engine (19 handlers, 3 cache tables — the design must define what projection tables/STATE.md files are needed)
- `src/state_core/events.py` — event store API (append, read_stream, post-commit callbacks)
- `src/state_build/kernel.py` — current StepMachine skeleton (15 lines, defines existing states)
- `src/state_core/scheduler.py` — DAG scheduler (already knows about `state.step.advanced` — the design must define what other events trigger recomputation)
- `src/state_core/worktree.py` — WorktreeService protocol (already defined — the design must define how Slices own worktrees)

**GSD reference (quality pipeline patterns):**
- `state-inputs/get-shit-done/bin/lib/artifacts.cjs` — canonical artifact registry (10 exact-match + 2 pattern-match)
- `state-inputs/get-shit-done/bin/lib/state.cjs` — STATE.md operations (how GSD manages state tracking)
- `state-inputs/get-shit-done/bin/lib/verify.cjs` — health checks (19 warning codes, schema drift detection)
- `state-inputs/get-shit-done/bin/lib/frontmatter.cjs` — YAML frontmatter handling

**Project context:**
- `.planning/PROJECT.md` — requirements, constraints, key decisions
- `.planning/research/ARCHITECTURE.md` — especially §5 (event taxonomy), §8 (build mode kernel), §3 (directory layout)
- `.planning/ROADMAP.md` — current v14-v17 milestone definitions (understand what exists before rewriting)
- `.planning/milestones/v14/REQUIREMENTS.md` — BLD-01 through BLD-09

**Opencode extension surface:**
- `state-inputs/opencode/packages/opencode/src/sync/` — how opencode handles event syncing
- `state-inputs/opencode/packages/opencode/src/skill/index.ts` — skill auto-discovery (for `.state/build/skills/`)
- `state-inputs/opencode/packages/opencode/src/snapshot/` — opencode's snapshot service (for worktree integration)

## Key Questions for Discuss-Phase

These are the gray-area decisions you'll need to make:

1. **Arc → Phase relationship**: Can an Arc contain phases that depend on phases in another Arc? Or are Arcs fully independent? (GSD has no equivalent — milestones are independent)

2. **Arc planning depth**: How detailed is an Arc plan? Just a list of phases with goals? Or does it include dependency graphs between phases?

3. **Phase planning depth**: How detailed is a Phase plan? Just a list of Slices with goals? Does the Phase plan include the DAG of Slices?

4. **Slice dependency DAG**: Slices can depend on other Slices (within the same Phase? across Phases?). What's the boundary?

5. **Step serialization within a Slice**: You said Steps run serially within a Slice. Is this always the case? Can a Slice ever have concurrent Steps?

6. **Decimal insertions**: For urgent gap-closure work, do we support decimal numbering at the Slice level? At the Step level? How does renumbering work?

7. **STATE.md at every tier**: State projection files at Arc, Phase, Slice, AND Step levels? Or just at Arc and Phase? Storage cost vs. utility?

8. **Artifact immutability**: Once a STEP.md is planned and execution begins, can the plan be modified? Or is it immutable? What about ARC.md when a child Phase is in progress?

9. **Naming style**: Human-readable slugs (`auth-oauth-migration`) vs machine sortable (`arc-003-phase-007`) vs both?

10. **Cross-reference format**: File paths? Content hashes? Event IDs? Frontmatter keys?

## Dependencies

- **v11 (Mode Enforcement)** — shipped. The hierarchy lives under `.state/build/` and must respect mode isolation.
- **v5 (DAG Scheduler)** — shipped. The scheduler already exists; the hierarchy design must integrate with it.
- **v4 (Worktree + Snapshot)** — shipped. Worktrees attach to Slices; snapshots attach to Steps.
- **v1 (Event Store)** — shipped. All state changes are events.

## Scope Boundaries

**In scope:**
- Full definition of all four tiers (Arc, Phase, Slice, Step)
- On-disk file structure for `.state/build/`
- Artifact catalog with schemas
- Naming conventions for all tiers, directories, and files
- Cross-referencing rules between artifacts
- Tracking file consistency model
- State machine definitions for all four tiers

**Out of scope (belongs to later milestones):**
- Agent harness design (v41)
- Quality pipeline design (v42)
- GSD command porting (v43)
- Any implementation code
- Teach mode equivalents (v46)
- Rust DB design (v44)

## Reference Patterns from GSD

GSD's artifact system has proven patterns worth studying:

1. **`artifacts.cjs`**: A single canonical registry defining exactly which files are recognized in `.planning/`. State needs the equivalent for `.state/build/` — probably more sophisticated since it spans 4 tiers.

2. **`state.cjs` STATE.md operations**: GSD's STATE.md tracks plan counts, phase status, session history, decisions. State needs separate STATE.md projections per tier, with the projector rebuilding them from events — not the agent manually updating them.

3. **`verify.cjs` health checks**: GSD's 19 warning codes detect drift between STATE.md, ROADMAP.md, REQUIREMENTS.md, and the filesystem. State needs equivalent health checks across all four tiers — but with the projector as ground truth instead of agent-written STATE.md.

4. **`frontmatter.cjs`**: GSD's YAML frontmatter handling with schema validation. State's artifact schemas need pydantic equivalents with `extra="forbid"`.
