# Artifact Catalog: `.state/build/` Complete Blueprint

> **Design contract for v41+ runtime filesystem implementation.**
> Consumed by: v41+ (runtime daemon projector, artifact loader, `/state-new` CLI commands), v42 (quality pipeline verifier), v43 (GSD command ports), Phase 401 Plan 02 (DIRECTORY-TREE.md), Phase 401 Plan 03 (CROSS-REFERENCES.md).

## Design Conventions

This document is the single source of truth for every artifact file type in the `.state/build/` filesystem. It defines what each artifact is, who creates and updates it, what triggers those operations, what fields it contains, when it becomes immutable, and how it cross-references other artifacts. All path definitions use the uniform variable notation `arc-{n}`, `stage-{n}`, `slice-{n}`, `step-{n}` — no competing notations are permitted (per pitfall #1 in RESEARCH.md).

The document implements ART-01 (artifact catalog), ART-02 (embedded templates), and ART-03 (immutability rules) from Phase 401 requirement set. Field ownership follows Phase 400 FRONTMATTER-SCHEMAS.md §Field Ownership Rules: every field is classified EXACTLY ONCE as Agent or Projector, never both. The projector-rebuilt artifacts (index.json, STATE.md) follow the CQRS projection pattern established in Phase 400.

Locked decisions referenced by ID: D-401-01 through D-401-13 (from 401-CONTEXT.md). Phase 400 specs are referenced by document+section — never reproduced (per the anti-pattern avoidance pattern from PATTERNS.md lines 600-601).

---

## Section 1: Artifact Catalog (ART-01)

The 13 artifact types are presented below in tier order: Arc → Stage → Slice → Step → projector-level. Each entry uses the exact property table format from PATTERNS.md lines 91-109. Path variable notation is uniform across all entries.

### ARC.md

| Property | Value |
|----------|-------|
| **Purpose** | Arc definition document — defines the feature block scope containing multiple Stages. The Arc is the coarsest scoping container and the only tier that maps to a GSD milestone. |
| **Owning Tier** | Arc |
| **Schema Owner** | Agent (id, title, goal, success_criteria, depends_on) / Projector (status, stage_count, shipped_stage_count, completed_at) |
| **Created By** | `/state-new arc` CLI command |
| **Creation Trigger** | User creates a new Arc to define a feature block or project branch |
| **Updated By** | Agent (edits id, title, goal, success_criteria, depends_on, body prose) / Projector (status transitions, counts, timestamps) |
| **Update Triggers** | Agent: `state.arc.updated` on frontmatter edit. Projector: `state.arc.started`, `state.arc.stages_shipped`, `state.arc.shipped`, `state.arc.abandoned` — updates status and counts |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | `ArcFrontmatter` — see Phase 400 FRONTMATTER-SCHEMAS.md §Arc Frontmatter. 5 agent fields + 4 projector fields = 9 total. `extra="forbid"` |
| **Immutability** | `depends_on` and `success_criteria` lock when Arc enters `in_progress` (D-401-12 analog). `title`, `goal`, and body prose remain mutable. See Section 3 for full rules. |
| **Cross-Refs From** | Sibling Arcs via `depends_on` field (cross-Arc deps are root-tier, not bound by D-10 same-parent). Child Stages reference this Arc via `arc_id` frontmatter field |
| **Cross-Refs To** | Sibling Arcs via `depends_on` (edge types: blocks, soft, data per D-12). Child Stages listed in Arc MAP.md |
| **File Path** | `arcs/arc-{n}/ARC.md` |

### STAGE.md

| Property | Value |
|----------|-------|
| **Purpose** | Stage definition document — decomposes an Arc into coherent work groupings of related Slices. Tracks cross-Slice integration and verification. |
| **Owning Tier** | Stage |
| **Schema Owner** | Agent (id, title, goal, success_criteria, arc_id, depends_on) / Projector (status, slice_count, shipped_slice_count, completed_at) |
| **Created By** | `/state-new stage` CLI command |
| **Creation Trigger** | User creates a new Stage within an Arc to group related Slices |
| **Updated By** | Agent (edits id, title, goal, success_criteria, depends_on, body prose) / Projector (status transitions, counts, timestamps) |
| **Update Triggers** | Agent: `state.stage.updated` on frontmatter edit. Projector: `state.stage.started`, `state.stage.slices_shipped`, `state.stage.audited`, `state.stage.completed`, `state.stage.abandoned` — updates status and counts |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | `StageFrontmatter` — see Phase 400 FRONTMATTER-SCHEMAS.md §Stage Frontmatter. 6 agent fields + 4 projector fields = 10 total. `extra="forbid"` |
| **Immutability** | `depends_on` and `success_criteria` lock when Stage enters `in_progress`. `title`, `goal`, and body prose remain mutable. See Section 3. |
| **Cross-Refs From** | Sibling Stages via `depends_on` (same-parent-only per D-10). Child Slices via `stage_id` frontmatter field. Parent Arc via `arc_id` field |
| **Cross-Refs To** | Parent Arc via `arc_id`. Sibling Stages via `depends_on`. Child Slices listed in Stage MAP.md |
| **File Path** | `arcs/arc-{n}/stages/stage-{n}/STAGE.md` |

### SLICE.md

| Property | Value |
|----------|-------|
| **Purpose** | Slice definition document — the terminal container tier. One Slice maps to one coherent unit of work that gets its own worktree. All workflow artifacts (DESIGN.md, RESEARCH.md, stepNPLAN.md, VERIFICATION.md, SUMMARY.md) live in the Slice folder. |
| **Owning Tier** | Slice |
| **Schema Owner** | Agent (id, title, goal, success_criteria, stage_id, depends_on, deferred_reason, blocked_reason) / Projector (status, step_count, completed_step_count, worktree_dir, worktree_branch, completed_at) |
| **Created By** | `/state-new slice` CLI command |
| **Creation Trigger** | User creates a new Slice within a Stage as a dispatachable work unit |
| **Updated By** | Agent (edits id, title, goal, success_criteria, depends_on, deferred_reason, blocked_reason, body prose) / Projector (status transitions, counts, worktree info, timestamps) |
| **Update Triggers** | Agent: `state.slice.updated`, `state.slice.deferred`, `state.slice.blocked`. Projector: `state.slice.worktree_ready`, `state.slice.started`, `state.slice.shipped`, `state.slice.reverted`, `state.slice.unblocked`, `state.slice.undeferred` |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | `SliceFrontmatter` — see Phase 400 FRONTMATTER-SCHEMAS.md §Slice Frontmatter. 6 agent fields + 7 projector fields + 2 agent reason fields = 15 total. `extra="forbid"` |
| **Immutability** | `depends_on`, `success_criteria`, and `goal` lock when Slice enters `in_progress`. `title` and body prose remain mutable. See Section 3. |
| **Cross-Refs From** | Sibling Slices via `depends_on` (same-parent-only per D-10). Child Steps via `slice_id` frontmatter field. Parent Stage via `stage_id` field |
| **Cross-Refs To** | Parent Stage via `stage_id`. Sibling Slices via `depends_on`. Child Steps tracked as flat files in Slice directory |
| **File Path** | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/SLICE.md` |

### CRIT.md

| Property | Value |
|----------|-------|
| **Purpose** | Numbered falsifiable requirements — defines must-have truths that MAP.md is generated from. Each criterion is a testable assertion (CRIT-01, CRIT-02, ...) with acceptance evidence trail. Per D-401-03. Exists at Arc and Stage tiers. |
| **Owning Tier** | Arc, Stage |
| **Schema Owner** | Agent (all fields — CRIT.md has no projector-owned fields) |
| **Created By** | Planner during `/state-new arc` or `/state-new stage` flow |
| **Creation Trigger** | Arc or Stage is created — planner reads scope and generates CRIT.md criteria |
| **Updated By** | Agent (adds, edits, or removes criteria during planning). Projector NEVER modifies CRIT.md |
| **Update Triggers** | Agent edits during planning phase (before parent tier enters `in_progress`). After lock, all mutations are rejected per D-401-13 |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | Phase 401 design — frontmatter schema defined in this document (see Template). Not part of Phase 400 pydantic models (CRIT.md is a Phase 401 artifact). 4 fields: `parent_id`, `criteria` (array), `created_at`, `updated_at` |
| **Immutability** | ALL fields lock when parent tier enters `in_progress` (per D-401-12). Arc CRIT.md locks on Arc `in_progress`; Stage CRIT.md locks on Stage `in_progress`. Enforcement: rejected, not warned (D-401-13). |
| **Cross-Refs From** | Parent Arc/Stage MAP.md — planner reads CRIT.md to generate MAP.md children. Referenced by verification tools during audit |
| **Cross-Refs To** | Parent tier aggregate ID (via `parent_id`). Each criterion can reference external sources (docs, specs) in its description |
| **File Path** | `arcs/arc-{n}/CRIT.md` (Arc level), `arcs/arc-{n}/stages/stage-{n}/CRIT.md` (Stage level) |

### MAP.md

| Property | Value |
|----------|-------|
| **Purpose** | Generated plan + tracker — maps child tiers (Stages for Arc MAP.md, Slices for Stage MAP.md) with IDs, goals, and tracking checkboxes. Modeled after `.planning/ROADMAP.md`. Per D-401-04 and D-401-05. |
| **Owning Tier** | Arc, Stage |
| **Schema Owner** | Hybrid — Agent writes child entries and goals. Projector updates checkboxes on child state change events. Per D-401-11 |
| **Created By** | Planner during `/state-new arc` or `/state-new stage` flow |
| **Creation Trigger** | Parent tier is created — planner reads CRIT.md, generates MAP.md children |
| **Updated By** | Agent (edits child goals, adds/removes entries during planning) / Projector (updates checkboxes on `state.stage.*` and `state.slice.*` events) |
| **Update Triggers** | Agent: during planning before parent enters `in_progress`. Projector: `state.stage.shipped` (Arc MAP.md checkbox), `state.slice.shipped` (Stage MAP.md checkbox), `state.stage.abandoned` / `state.slice.abandoned` → `[!]` abandoned marker |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | Phase 401 design — frontmatter schema defined in this document (see Template). Not part of Phase 400 pydantic models. 5 fields: `parent_id`, `children` (array of {id, goal, status_checkbox}), `generated_by`, `generated_at`, `last_updated` |
| **Immutability** | Hybrid — agent-written child goals mutable until parent enters `in_progress`; projector checkboxes always writable by projector. Projector bypasses immutability lock per RESEARCH.md open question #5. See Section 3. |
| **Cross-Refs From** | Parent tier artifact loader — reads MAP.md for child tier inventory. DAG scheduler — reads for dependency ordering hints. STATE.md projections |
| **Cross-Refs To** | Child tier artifacts via `id` field in children array. Each child entry references a specific Stage or Slice ID |
| **File Path** | `arcs/arc-{n}/MAP.md` (Arc level), `arcs/arc-{n}/stages/stage-{n}/MAP.md` (Stage level) |

### DECISIONS.md

| Property | Value |
|----------|-------|
| **Purpose** | Gray-area decision log — captures architectural decisions, trade-offs, and rationale made during planning and execution. Append-only per D-401-02. |
| **Owning Tier** | Arc, Stage |
| **Schema Owner** | Agent (all fields — DECISIONS.md has no projector-owned fields) |
| **Created By** | Agent during planning or execution (any time a gray-area decision is made) |
| **Creation Trigger** | Agent encounters a decision point that warrants documentation — created on first decision entry |
| **Updated By** | Agent (appends new decisions). Projector NEVER modifies DECISIONS.md |
| **Update Triggers** | Agent appends a new decision entry (D-{N}) at any workflow stage. Never deleted — decisions are immutable once logged |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | Phase 401 design — frontmatter schema defined in this document (see Template). 2 fields: `parent_id`, `decisions` (array of {id, title, context, decision, date}) |
| **Immutability** | Always mutable (append-only per D-401-02). Individual decision entries, once written, are never edited — but new entries can be appended at any time. See Section 3. |
| **Cross-Refs From** | Downstream plans and verifiers — references decisions by D-{N} ID. Audit traces |
| **Cross-Refs To** | Parent tier aggregate ID via `parent_id`. Decision entries may reference artifact IDs and external sources |
| **File Path** | `arcs/arc-{n}/DECISIONS.md` (Arc level), `arcs/arc-{n}/stages/stage-{n}/DECISIONS.md` (Stage level) |

### DESIGN.md

| Property | Value |
|----------|-------|
| **Purpose** | Design phase output — explores the problem space, proposes architecture approach, and identifies components and their interfaces. Per D-401-06. |
| **Owning Tier** | Slice |
| **Schema Owner** | Agent (all fields — DESIGN.md has no projector-owned fields) |
| **Created By** | Agent during the design phase of Slice workflow (`/state-design slice`, Step `designing` state per D-03) |
| **Creation Trigger** | Slice's first Step enters `designing` state — agent produces DESIGN.md |
| **Updated By** | Agent (refines design as new information emerges during planning and execution) |
| **Update Triggers** | Agent edits during any workflow phase — DESIGN.md is always mutable. Revisited when verification reveals design gaps |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | Phase 401 design — frontmatter schema defined in this document (see Template). 4 fields: `slice_id`, `design_version`, `architecture_approach`, `components` (array) |
| **Immutability** | Never — all fields always mutable. See Section 3. |
| **Cross-Refs From** | RESEARCH.md (builds on design decisions), stepNPLAN.md (implements the design), VERIFICATION.md (verifies against design) |
| **Cross-Refs To** | Parent Slice via `slice_id`. Components may reference external libraries and patterns |
| **File Path** | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/DESIGN.md` |

### RESEARCH.md

| Property | Value |
|----------|-------|
| **Purpose** | Research phase output — evaluates libraries, patterns, and alternatives. Documents decisions on technology choices with rationale. Per D-401-06. |
| **Owning Tier** | Slice |
| **Schema Owner** | Agent (all fields — RESEARCH.md has no projector-owned fields) |
| **Created By** | Agent during the research phase of Slice workflow (`/state-research slice`) |
| **Creation Trigger** | DESIGN.md is complete — agent researches alternatives before planning implementation |
| **Updated By** | Agent (adds new research topics, updates decisions as new information emerges) |
| **Update Triggers** | Agent edits during planning or when new alternatives are discovered during execution |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | Phase 401 design — frontmatter schema defined in this document (see Template). 5 fields: `slice_id`, `research_topics` (array), `standard_stack`, `confidence` |
| **Immutability** | Never — all fields always mutable. See Section 3. |
| **Cross-Refs From** | stepNPLAN.md (implements decisions from research), DESIGN.md (informed by research outcomes) |
| **Cross-Refs To** | Parent Slice via `slice_id`. Research topics reference external libraries, docs, and benchmarks |
| **File Path** | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/RESEARCH.md` |

### stepNPLAN.md

| Property | Value |
|----------|-------|
| **Purpose** | Step execution plan — one file per Step within the parent Slice. Contains the plan summary, verification criteria, and tracks Step-level state. Steps are markdown FILES, not directories (D-04). |
| **Owning Tier** | Slice (container — Step is a leaf tier with no own directory) |
| **Schema Owner** | Agent (step_number, title, goal, slice_id, plan_summary, verification_criteria, blocked_reason) / Projector (status, completed_at) |
| **Created By** | Agent during the run phase (`/state-run slice`) — generates step1PLAN.md through stepNPLAN.md |
| **Creation Trigger** | Slice enters `in_progress` — agent sequences Steps and creates tracking files |
| **Updated By** | Agent (edits plan_summary, verification_criteria during execution) / Projector (status transitions, timestamps) |
| **Update Triggers** | Agent: `state.step.designed`, `state.step.planned`, `state.step.ran`, `state.step.blocked`. Projector: `state.step.verify_started`, `state.step.verify_passed`, `state.step.verify_failed`, `state.step.unblocked`, `state.step.abandoned` |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | `StepFrontmatter` — see Phase 400 FRONTMATTER-SCHEMAS.md §Step Frontmatter. 6 agent fields + 2 projector fields + 1 agent reason field = 9 total. `extra="forbid"` |
| **Immutability** | ALL fields lock when parent Slice enters `in_progress` (per D-401-12). Enforcement: rejected, not warned (D-401-13). See Section 3. |
| **Cross-Refs From** | Parent Slice VERIFICATION.md (verifies Step criteria). Parent Slice SUMMARY.md (documents Step completion). STATE.md projections |
| **Cross-Refs To** | Parent Slice via `slice_id`. Step number is sequential within parent Slice — no cross-Step deps (Steps run serial per D-11) |
| **File Path** | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/step{step_number}PLAN.md` |

### VERIFICATION.md

| Property | Value |
|----------|-------|
| **Purpose** | Verify phase output — test results, UAT pass/fail evidence, and verification criteria audit. Produced during the verify phase of the Slice workflow. Per D-401-06. |
| **Owning Tier** | Slice |
| **Schema Owner** | Agent (all fields — VERIFICATION.md has no projector-owned fields) |
| **Created By** | Agent during the verify phase (`/state-verify slice`) |
| **Creation Trigger** | All child Steps are `done` — agent produces VERIFICATION.md with pass/fail results per verification criteria |
| **Updated By** | Agent (updates when verification re-runs after fix loops). May be revisited if Slice is reverted and re-executed |
| **Update Triggers** | Agent edits during verify phase. If `state.step.verify_failed` → loop back to running → re-verify |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | N/A — VERIFICATION.md is primarily body prose with a minimal frontmatter header. No Phase 400 pydantic model (artifact-specific to Slice workflow). |
| **Immutability** | Locked when parent Slice enters `shipped`. Enforcement: snapshot-before-mutation (D-401-13). See Section 3. |
| **Cross-Refs From** | Slice SUMMARY.md (references verification results). Parent Stage state transition guard (Slice cannot ship without VERIFICATION.md passing) |
| **Cross-Refs To** | Parent Slice. Individual Step verification_criteria. DESIGN.md for design-compliance checks |
| **File Path** | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/VERIFICATION.md` |

### SUMMARY.md

| Property | Value |
|----------|-------|
| **Purpose** | Plan completion documentation — summarizes what was built, decisions made, deviations from plan, and verification results. Produced during the summary phase. Per D-401-06. |
| **Owning Tier** | Slice |
| **Schema Owner** | Agent (all fields — SUMMARY.md has no projector-owned fields) |
| **Created By** | Agent during the summary phase (`/state-summary slice`) |
| **Creation Trigger** | VERIFICATION.md passes — agent produces SUMMARY.md as the final Slice artifact |
| **Updated By** | Agent (final edits before Slice ships). May be revisited if Slice is reverted and re-executed |
| **Update Triggers** | Agent edits during summary phase. Last write before Slice transitions to `shipped` |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | N/A — SUMMARY.md is primarily body prose with a minimal frontmatter header. No Phase 400 pydantic model. |
| **Immutability** | Locked when parent Slice enters `shipped`. Enforcement: snapshot-before-mutation (D-401-13). See Section 3. |
| **Cross-Refs From** | Parent Stage and Arc audit (reads SUMMARY.md for completion evidence). Milestone close procedures |
| **Cross-Refs To** | Parent Slice. VERIFICATION.md results. DECISIONS.md for decisions captured. Step tracking files |
| **File Path** | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/SUMMARY.md` |

### index.json

| Property | Value |
|----------|-------|
| **Purpose** | Projector-rebuilt artifact registry — maps every artifact ID to its type, path, tier, status, schema owner, last_updated timestamp, and content hash. Provides O(1) ID→path resolution. Per D-401-14. |
| **Owning Tier** | N/A (projector-level — lives at `.state/build/` root) |
| **Schema Owner** | Projector (all fields — rebuilt from event stream on every state change) |
| **Created By** | Daemon projector — rebuilt from scratch on daemon startup, incrementally updated on every `state.*` event |
| **Creation Trigger** | Daemon startup (full rebuild from event store). Every state change event (incremental update for affected entries) |
| **Updated By** | Projector exclusively. Agent NEVER writes to index.json |
| **Update Triggers** | Every `state.*` event — projector creates/updates the affected artifact's entry. Daemon startup triggers full rebuild |
| **File Format** | JSON |
| **Frontmatter Model** | N/A — JSON schema defined in Plan 401-02 (INDEX-SCHEMA.md). Tier-separated structure: `{arcs: {}, stages: {}, slices: {}, steps: {}}` per D-401-14 |
| **Immutability** | Always mutable — projector rebuilds at any time. Agent NEVER writes to this file. See Section 3. |
| **Cross-Refs From** | Daemon artifact loader (reads for path resolution). Cross-reference resolver (O(1) ID lookup). `validate_consistency()` (reads for orphan/stale detection) |
| **Cross-Refs To** | Every artifact in `.state/build/` — each entry maps one artifact ID to its path and metadata |
| **File Path** | `index.json` |

### STATE.md

| Property | Value |
|----------|-------|
| **Purpose** | Consolidated projector-rebuilt JSON projections of current state for all tiers — provides fast state queries without parsing individual artifact files. Rebuilt from event store on every state change. Per D-401-07. |
| **Owning Tier** | N/A (projector-level — lives under `.state/build/state/`) |
| **Schema Owner** | Projector (all fields — completely rebuilt from event stream) |
| **Created By** | Daemon projector — rebuilt from scratch on daemon startup, incrementally updated on every `state.*` event |
| **Creation Trigger** | Daemon startup (full rebuild). Every state change event (incremental update) |
| **Updated By** | Projector exclusively. Agent NEVER writes to STATE.md projections |
| **Update Triggers** | Every `state.*` event — projector updates the affected tier's JSON projection file |
| **File Format** | JSON (one file per tier: arcs.json, stages.json, slices.json, steps.json) |
| **Frontmatter Model** | N/A — these are JSON projection files, not markdown artifacts. No frontmatter. Schema defined by projector CQRS handler |
| **Immutability** | Always mutable — projector rebuilds at any time. Agent NEVER writes to these files. |
| **Cross-Refs From** | TUI dashboard (reads for display). CLI `state build state` command. DAG viewer. Audit tools |
| **Cross-Refs To** | All aggregate IDs are keys in projection arrays. Each entry references the full artifact metadata |
| **File Path** | `state/arcs.json`, `state/stages.json`, `state/slices.json`, `state/steps.json` |

---

## Section 2: Templates (ART-02)

Each template lives at `.state/build/templates/{NAME}.tmpl` and is rendered by v41+ `/state-new` CLI commands into editable artifact files. Every template frontmatter field maps to a Phase 400 pydantic model field (verified by the cross-reference table below). Phase 401-designed artifacts (CRIT.md, MAP.md, DECISIONS.md, DESIGN.md, RESEARCH.md) have no Phase 400 pydantic model — their frontmatter schemas are defined here.

Templates include inline guidance comments for the agent (how to fill prose sections, what each field means). Projector-owned fields are clearly marked and include the directive: `# ── Projector-owned (populated by daemon, NEVER edit) ──`.

### ARC.md.tmpl

**Template path:** `.state/build/templates/ARC.md.tmpl`

```yaml
---
id: ""
title: ""
goal: ""
success_criteria: []
depends_on: []
# ── Projector-owned (populated by daemon, NEVER edit) ──
status: planned
stage_count: 0
shipped_stage_count: 0
completed_at: null
---
```

**Body guidance:**
```
# Arc: [title]

## Goal
[Expand on the goal — describe the complete deliverable this Arc represents.
Answer: what does "done" look like at the Arc level?]

## Success Criteria
[Expand on each success_criterion from frontmatter. Each must be a
measurable, testable outcome. These are the gating conditions for
the Arc auditing→shipped transition.]

## Scope
[What is in scope for this Arc? What is explicitly out of scope?
Bound the feature block clearly — this is the coarsest container.]

## Child Stages
[Describe the planned Stages. What does each Stage accomplish? How
do they fit together? Refer to MAP.md for the detailed tracker.]
```

### STAGE.md.tmpl

**Template path:** `.state/build/templates/STAGE.md.tmpl`

```yaml
---
id: ""
title: ""
goal: ""
success_criteria: []
arc_id: ""
depends_on: []
# ── Projector-owned (populated by daemon, NEVER edit) ──
status: planned
slice_count: 0
shipped_slice_count: 0
completed_at: null
---
```

**Body guidance:**
```
# Stage: [title]

## Goal
[Expand on the goal — what does this Stage deliver within the parent Arc?
How does it decompose the Arc's scope into a coherent work grouping?]

## Success Criteria
[Expand on each success_criterion. These are the gating conditions
for the Stage slices_shipped→verified transition.]

## Child Slices
[Describe the planned Slices. What does each Slice accomplish? How
do they depend on each other? Refer to MAP.md for the detailed tracker.]

## Dependencies
[Document sibling Stage dependencies from depends_on frontmatter.
Explain WHY each dependency exists — what does this Stage need from
the sibling Stage before it can proceed?]
```

### SLICE.md.tmpl

**Template path:** `.state/build/templates/SLICE.md.tmpl`

```yaml
---
id: ""
title: ""
goal: ""
success_criteria: []
stage_id: ""
depends_on: []
# ── Projector-owned (populated by daemon, NEVER edit) ──
status: planned
step_count: 0
completed_step_count: 0
worktree_dir: null
worktree_branch: null
completed_at: null
# ── Agent-written reason fields ──
deferred_reason: null
blocked_reason: null
---
```

**Body guidance:**
```
# Slice: [title]

## Goal
[Expand on the goal — what is the one coherent unit of work this Slice
delivers? This is the terminal container — everything below is flat files.]

## Success Criteria
[Expand on each success_criterion. These define when this Slice is "done."
All child Steps must complete + VERIFICATION.md must pass.]

## Dependencies
[Document sibling Slice dependencies from depends_on. Explain edge types:
blocks (hard prerequisite), soft (advisory), data (artifact-producing).]

## Planned Steps
[Describe the planned Steps and their order. Remember: Steps run serially
within the agent session — order matters. List step numbers, goals, and
expected outcomes.]
```

### STEP.md.tmpl

**Template path:** `.state/build/templates/STEP.md.tmpl`

```yaml
---
step_number: 0
title: ""
goal: ""
slice_id: ""
plan_summary: ""
verification_criteria: []
# ── Projector-owned (populated by daemon, NEVER edit) ──
status: idle
completed_at: null
# ── Agent-written reason field ──
blocked_reason: null
---
```

**Body guidance:**
```
## Step Plan

[Expand on plan_summary. List the concrete implementation steps in order.
This is the agent's execution guide — write it as a checklist the agent
can follow during the running phase.]

1. [Step 1 description]
2. [Step 2 description]
...

## Verification Criteria

[Expand on each verification_criterion from frontmatter. How will the
agent confirm each criterion is met? What tests, checks, or manual
verification steps are needed?]

## Implementation Notes

[Any notes, gotchas, or context the agent needs during execution.
Reference DESIGN.md and RESEARCH.md decisions that inform this Step.]

## Sub-Steps (if needed)

[Optional decomposition into sub-steps (1.1, 1.2, ...). Sub-steps are
agent-internal — no scheduler involvement. Use for complex Steps that
need finer-grained tracking within a single session.]
```

### CRIT.md.tmpl

**Template path:** `.state/build/templates/CRIT.md.tmpl`

```yaml
---
parent_id: ""
criteria:
  - id: "CRIT-01"
    title: ""
    description: ""
    acceptance_test: ""
created_at: ""
updated_at: ""
---
```

**Body guidance:**
```
# Critical Requirements: [parent tier title]

> **Numbered falsifiable requirements — per D-401-03.**
> Each criterion MUST be a testable assertion with a defined acceptance test.
> When fully satisfied, these criteria define "done" at this tier.

## CRIT-01: [criterion title]

**Description:** [What must be true? Describe the requirement clearly.
Be specific enough that a verifier can determine pass/fail unambiguously.]

**Acceptance Test:** [How will we know this is satisfied? Describe the
test, check, or evidence that confirms the criterion is met.]

## CRIT-02: [criterion title]

**Description:** [Next criterion...]

**Acceptance Test:** [How verified...]

## CRIT-N: ...

[Continue for all criteria. MAP.md children are generated from these criteria
— each CRIT should map to one or more child tier units in MAP.md.]
```

### MAP.md.tmpl

**Template path:** `.state/build/templates/MAP.md.tmpl`

```yaml
---
parent_id: ""
children:
  - id: ""
    goal: ""
    status_checkbox: "[ ]"
generated_by: ""
generated_at: ""
last_updated: ""
---
```

**Body guidance:**
```
# MAP: [parent tier title]

> **Generated plan + tracker — per D-401-04 and D-401-05.**
> Child entries and goals are agent-written. Checkboxes are projector-updated
> automatically as children advance through their state machines (D-401-11).
> Modeled after `.planning/ROADMAP.md`.

## Child Inventory

| ID | Goal | Status |
|----|------|--------|
| [child-id-1] | [goal from CRIT.md] | [ ] |
| [child-id-2] | [goal from CRIT.md] | [ ] |
| ... | ... | ... |

**Checkbox legend:**
- `[ ]` — Planned (not yet started)
- `[x]` — Shipped (projector-updated on state.{child-tier}.shipped)
- `[!]` — Abandoned (projector-updated on state.{child-tier}.abandoned)

## Dependency Graph

[Describe or diagram the dependency relationships between children.
Which ones must complete before others can start? Reference the
depends_on fields in each child's definition document.]

## Generated By

[Which command/workflow generated this MAP.md. E.g., `/state-new arc`
or `/state-new stage`. The generated_by and generated_at fields in
frontmatter track provenance.]
```

### DECISIONS.md.tmpl

**Template path:** `.state/build/templates/DECISIONS.md.tmpl`

```yaml
---
parent_id: ""
decisions:
  - id: "D-1"
    title: ""
    context: ""
    decision: ""
    date: ""
---
```

**Body guidance:**
```
# Decisions: [parent tier title]

> **Append-only decision log — per D-401-02.**
> Every gray-area architectural or implementation decision gets a D-{N} entry.
> Once written, decisions are never edited — new decisions are appended.

## D-1: [decision title]

**Context:** [What was the situation? What were the options? Why was
a decision needed at this point?]

**Decision:** [What did we decide? Be specific — include trade-offs
accepted and rejected.]

**Date:** [When was this decision made? ISO 8601 date.]

## D-2: ...

[Append new decisions below. Do NOT edit existing entries.]
```

### DESIGN.md.tmpl

**Template path:** `.state/build/templates/DESIGN.md.tmpl`

```yaml
---
slice_id: ""
design_version: "1.0"
architecture_approach: ""
components:
  - name: ""
    responsibility: ""
    interfaces: ""
---
```

**Body guidance:**
```
# Design: [slice title]

> **Design phase output — per D-401-06.**
> Explores the problem space, proposes architecture, and identifies
> components and their interfaces. This is a living document — update
> as new information emerges during planning and execution.

## Architecture Approach

[Expand on architecture_approach from frontmatter. Describe the overall
design: what pattern are we using? What are the key abstractions?
How does data flow through the system?]

## Component Breakdown

[Expand on each component from frontmatter. For each component, describe:
- What problem it solves
- Why it's separate (cohesion/coupling rationale)
- Its public interface (what other components can call)
- Its dependencies (what it needs from other components or externals)]

## Design Decisions

[Document any design decisions made during this phase. If a decision
rises to the level of a gray-area architectural choice, also add it
to the parent tier's DECISIONS.md with a D-{N} entry.]

## Open Questions

[What isn't decided yet? What risks or unknowns remain? These are
inputs for the RESEARCH.md phase.]
```

### RESEARCH.md.tmpl

**Template path:** `.state/build/templates/RESEARCH.md.tmpl`

```yaml
---
slice_id: ""
research_topics:
  - topic: ""
    decision: ""
    alternatives_considered: ""
    rationale: ""
standard_stack: ""
confidence: ""
---
```

**Body guidance:**
```
# Research: [slice title]

> **Research phase output — per D-401-06.**
> Evaluates libraries, patterns, and alternatives. Documents technology
> choices with rationale. Builds on DESIGN.md decisions.

## Standard Stack

[Expand on standard_stack from frontmatter. What libraries, tools, and
patterns are we using? What versions? Are these already in the project's
STACK.md, or are they new additions?]

## Research Topics

[Expand on each research_topic from frontmatter. For each:
- What was evaluated?
- What alternatives were considered and why were they rejected?
- What was the final decision and rationale?
- Are there any licensing, performance, or compatibility concerns?]

## Confidence Assessment

[Expand on confidence from frontmatter. How confident are we in these
decisions? HIGH (well-understood, proven in this project), MEDIUM
(understood but new to this codebase), LOW (spike needed, significant
unknowns). Document what would increase confidence.]
```

---

### Template ↔ Schema Cross-Reference

Every template frontmatter field is validated against the corresponding Phase 400 pydantic model. This table confirms that no template field exists that is absent from the pydantic model (would violate `extra="forbid"`) and that every required field from the pydantic model is present in the template.

| Template Field | ArcFrontmatter | StageFrontmatter | SliceFrontmatter | StepFrontmatter | Notes |
|----------------|:---:|:---:|:---:|:---:|-------|
| `id` | ✓ | ✓ | ✓ | — | D-01 dash-prefix format. Agent-owned |
| `step_number` | — | — | — | ✓ | Sequential int, no leading zeros. Agent-owned |
| `title` | ✓ | ✓ | ✓ | ✓ | Human-readable name. Agent-owned |
| `goal` | ✓ | ✓ | ✓ | ✓ | One-line outcome. Agent-owned |
| `success_criteria` | ✓ | ✓ | ✓ | — | Measurable outcomes (list). Agent-owned |
| `verification_criteria` | — | — | — | ✓ | Step "done" criteria (list). Agent-owned |
| `plan_summary` | — | — | — | ✓ | Brief execution plan. Agent-owned |
| `arc_id` | — | ✓ | — | — | Parent Arc reference. Agent-owned |
| `stage_id` | — | — | ✓ | — | Parent Stage reference. Agent-owned |
| `slice_id` | — | — | — | ✓ | Parent Slice reference. Agent-owned |
| `depends_on` | ✓ | ✓ | ✓ | — | D-12 edge types. Agent-owned |
| `status` | ✓ | ✓ | ✓ | ✓ | Projector-owned, Literal enum |
| `stage_count` | ✓ | — | — | — | Projector-owned |
| `shipped_stage_count` | ✓ | — | — | — | Projector-owned |
| `slice_count` | — | ✓ | — | — | Projector-owned |
| `shipped_slice_count` | — | ✓ | — | — | Projector-owned |
| `step_count` | — | — | ✓ | — | Projector-owned |
| `completed_step_count` | — | — | ✓ | — | Projector-owned |
| `worktree_dir` | — | — | ✓ | — | Projector-owned |
| `worktree_branch` | — | — | ✓ | — | Projector-owned |
| `completed_at` | ✓ | ✓ | ✓ | ✓ | Projector-owned, ISO 8601 |
| `deferred_reason` | — | — | ✓ | — | Agent reason field |
| `blocked_reason` | — | — | ✓ | ✓ | Agent reason field |

**Phase 401-designed artifacts (no Phase 400 pydantic model):**

| Template Field | CRIT.md | MAP.md | DECISIONS.md | DESIGN.md | RESEARCH.md | Notes |
|----------------|:---:|:---:|:---:|:---:|:---:|-------|
| `parent_id` | ✓ | ✓ | ✓ | — | — | Tier aggregate ID |
| `slice_id` | — | — | — | ✓ | ✓ | Parent Slice reference |
| `criteria` | ✓ | — | — | — | — | Array of {id, title, description, acceptance_test} |
| `children` | — | ✓ | — | — | — | Array of {id, goal, status_checkbox} |
| `decisions` | — | — | ✓ | — | — | Array of {id, title, context, decision, date} |
| `created_at` | ✓ | — | — | — | — | ISO 8601 timestamp |
| `updated_at` | ✓ | — | — | — | — | ISO 8601 timestamp |
| `generated_by` | — | ✓ | — | — | — | Which command generated MAP.md |
| `generated_at` | — | ✓ | — | — | — | ISO 8601 timestamp |
| `last_updated` | — | ✓ | — | — | — | ISO 8601 timestamp |
| `design_version` | — | — | — | ✓ | — | Semver for design iteration |
| `architecture_approach` | — | — | — | ✓ | — | Prose field |
| `components` | — | — | — | ✓ | — | Array of {name, responsibility, interfaces} |
| `research_topics` | — | — | — | — | ✓ | Array of {topic, decision, alternatives_considered, rationale} |
| `standard_stack` | — | — | — | — | ✓ | Prose field |
| `confidence` | — | — | — | — | ✓ | HIGH/MEDIUM/LOW |
| `date` | — | — | ✓ (in decisions[]) | — | — | ISO 8601 date per decision entry |

---

## Section 3: Immutability Rules (ART-03)

Immutability is enforced by the snapshot-before-mutation protocol at daemon level (D-401-13). When an artifact's lock trigger fires, the daemon prevents agent-initiated mutations to locked fields. Projector-owned fields are exempt from immutability locks — the projector must always be able to update status, counts, and timestamps (per RESEARCH.md open question #5).

**Lock enforcement levels:**
- **Rejected (blocked):** Mutation attempt is rejected outright. The artifact is permanently or conditionally immutable. Per D-401-13: "blocked, not warned."
- **Snapshot-before-mutation:** A snapshot is taken before the mutation is allowed. Used for artifacts where some fields lock but others remain mutable.
- **N/A:** No lock — all fields always mutable.

| Artifact | Lock Trigger | Locked Fields | Mutable Fields | Enforcement |
|----------|-------------|--------------|----------------|-------------|
| ARC.md | Arc enters `in_progress` | `depends_on`, `success_criteria` | `title`, `goal`, description body | Snapshot-before-mutation (D-401-13) |
| STAGE.md | Stage enters `in_progress` | `depends_on`, `success_criteria` | `title`, `goal`, description body | Snapshot-before-mutation |
| SLICE.md | Slice enters `in_progress` | `depends_on`, `success_criteria`, `goal` | `title`, description body | Snapshot-before-mutation |
| CRIT.md (Arc) | Arc enters `in_progress` | ALL fields (per D-401-12) | None after lock | Rejected, not warned (D-401-13) |
| CRIT.md (Stage) | Stage enters `in_progress` | ALL fields (per D-401-12) | None after lock | Rejected, not warned |
| stepNPLAN.md | Parent Slice enters `in_progress` (per D-401-12) | ALL fields | None after lock | Rejected, not warned |
| DESIGN.md | Never | — | All fields always mutable | N/A |
| RESEARCH.md | Never | — | All fields always mutable | N/A |
| DECISIONS.md | Never | — | All fields always mutable (append-only per D-401-02) | N/A |
| MAP.md | Hybrid — agent content locks when parent enters `in_progress` | Agent-written child goals (once parent in `in_progress`) | Projector checkboxes always writable by projector; agent-written goals mutable before lock | Projector bypasses immutability lock per RESEARCH.md open question #5 |
| VERIFICATION.md | Parent Slice enters `shipped` | ALL fields | None after lock | Snapshot-before-mutation (D-401-13) |
| SUMMARY.md | Parent Slice enters `shipped` | ALL fields | None after lock | Snapshot-before-mutation (D-401-13) |
| index.json | Never (projector-only) | — | All fields always mutable by projector | N/A (agent never writes) |
| STATE.md (projections) | Never (projector-only) | — | All fields always mutable by projector | N/A (agent never writes) |

**D-401-12 alignment verified:** stepNPLAN.md and CRIT.md lock when the parent Slice (for Steps) or parent tier (for CRIT) enters `in_progress`. CRIT.md at Arc level locks when Arc enters `in_progress`; CRIT.md at Stage level locks when Stage enters `in_progress` (analogous application of the rule). DESIGN.md and RESEARCH.md remain always mutable — they are living documents that evolve throughout the Slice lifecycle.

---

## Section 4: Cross-References to Phase 400

This document depends on the following Phase 400 specifications. Each is referenced by document+section — Phase 400 content is never reproduced.

| Phase 400 Spec | What This Document Uses From It |
|----------------|--------------------------------|
| TIER-ARC.md | Arc state machine status values, owned artifacts, directory path, cross-tier relationships |
| TIER-STAGE.md | Stage state machine status values, owned artifacts, directory path, cross-tier relationships |
| TIER-SLICE.md | Slice state machine status values, owned artifacts, directory path, Step file naming convention (D-04), workflow order (D-06) |
| TIER-STEP.md | Step state machine status values (D-03 renamed), Step file naming (stepNPLAN.md flat files), lack of `depends_on` (D-11) |
| FRONTMATTER-SCHEMAS.md | All four pydantic frontmatter models (ArcFrontmatter, StageFrontmatter, SliceFrontmatter, StepFrontmatter) — field definitions, status enums, `extra="forbid"` convention. §Field Ownership Rules (TIER-07) — Agent vs Projector classification. §Cross-Tier ID Encoding — aggregate ID format |
| DESC-SEMANTICS.md | D-13 abandon cascade (affects immutability — abandoned artifacts are permanently locked), D-14 deferment (affects blocked_reason/deferred_reason semantics), D-15 blocked state mechanics |
| EVENT-TAXONOMY.md | Event types used as update triggers in catalog entries — `state.arc.*`, `state.stage.*`, `state.slice.*`, `state.step.*` |

---

## Section 5: Threat Model Alignment

Mapping specification-level threats to mitigations in this document:

| Threat ID | Category | Mitigation |
|-----------|----------|------------|
| T-401-01 | Tampering — Path inconsistency with directory tree | Single source of truth for paths in this document (Section 1 catalog). Every entry uses identical variable notation (arc-{n}, stage-{n}, slice-{n}, step-{n}). Plan 401-02 DIRECTORY-TREE.md cross-verifies paths against this catalog. |
| T-401-02 | Tampering — Template frontmatter drift from Phase 400 schemas | Template↔Schema Cross-Reference table (Section 2) validates every template field against the corresponding Phase 400 pydantic model. `extra="forbid"` on all pydantic models rejects unknown fields at parse time. Phase 401-designed artifacts (CRIT.md, MAP.md, DECISIONS.md, DESIGN.md, RESEARCH.md) are explicitly marked as having schemas defined in this document. |
| T-401-03 | Elevation of Privilege — Agent writing to projector-owned fields | Every catalog entry (Section 1) explicitly separates Schema Owner into Agent and Projector with field-level detail. Templates mark projector-owned fields with `# ── Projector-owned (populated by daemon, NEVER edit) ──`. Field ownership table (TIER-07 in FRONTMATTER-SCHEMAS.md) classifies every field exactly once. Projector rebuilds overwrite any agent-written projector-owned fields. |
| T-401-04 | Tampering — Immutability bypass | Immutability rules table (Section 3) specifies exactly which artifacts lock, when, and at what enforcement level. D-401-13 snapshot-before-mutation protocol at daemon level rejects (does not warn) attempted mutations of locked artifacts. CRIT.md and stepNPLAN.md are the strictest — ALL fields lock, enforcement is "Rejected, not warned." |
| T-401-05 | Information Disclosure — Specification quality degradation | Cross-reference consistency checks between Plan 01 (this document), Plan 02 (DIRECTORY-TREE.md), and Plan 03 (CROSS-REFERENCES.md) catch contradictions. No sensitive data in design specs. |

---

*Design contract for v41+ runtime filesystem implementation. All 13 artifact types documented with complete property tables, 10 embedded templates with frontmatter cross-reference validation, and comprehensive immutability rules. Path variable notation uniform throughout (arc-{n}, stage-{n}, slice-{n}, step-{n}). Consumed by Phase 401 Plan 02 (DIRECTORY-TREE.md), Plan 03 (CROSS-REFERENCES.md), and v41+ daemon projector.*

---

## v41 Amendment

**Amended:** Phase 402 (v41 milestone — Slice-Cycle & Context Window Spec)
**Cause:** SLC-06 / SLC-07 — canonical Slice folder layout + cycle ownership.
**Canonical successor:** [`.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md) §"Canonical Slice Folder Layout (SLC-06 amended)"

### Effect on this document

Artifact catalog (ART-01) entries for the Slice tier remain authoritative for filename, schema owner, and immutability. SLICE-CYCLE.md adds the producer-stage mapping (which of design-slice / research-slice / run-slice / verify-slice writes each artifact) and the v41 vocabulary reconciliation. Readers consulting this catalog for v41+ scheduling should cross-reference SLICE-CYCLE.md §"Canonical Slice Folder Layout".

*Original v40 spec text above this amendment block is untouched.*

---

## v41 Amendment — Phase 404 Verification + Discipline Artifacts

**Amended:** Phase 404 (v41 milestone — Boolean Proof Gate & Discipline Guards)
**Amendment date:** 2026-05-11
**Amendment type:** Additive — three new per-Step/per-Slice artifacts registered; v40 baseline + Phase 402 amendment unchanged.
**Forward-pointers:**
  - `stepN-VERIFY.json` + `slice-verification.sh` + `N-VERIFICATION.md` column schema: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md`
  - `deferred-items.md`: `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md`

### v40 baseline + Phase 402 amendment scope

The v40 ARTIFACT-CATALOG.md catalogued the canonical Slice folder layout including `N-CONTEXT.md`, `N-DISCUSSION-LOG.md`, `N-RESEARCH.md`, `N-PATTERNS.md`, `N-VALIDATION.md`, `stepNPLAN.md`, `stepNSUMMARY.md`, `N-VERIFICATION.md`, and `RESUME.txt`. The Phase 402 amendment confirmed Slice-owns-cycle producer mapping. Phase 404 introduces three new artifacts (one per-Step JSON, one per-Slice executable script, one per-Slice markdown out-of-scope log) and pins `N-VERIFICATION.md`'s previously-implicit column schema to PROOF-GATE.md Section 8.

### v41 extension scope (3 new artifacts + 1 column-schema pin)

| Filename | Producer Stage | Schema Owner | Immutability | Description |
|---------|----------------|--------------|--------------|-------------|
| `stepN-VERIFY.json` | execute-slice (Step-end gate) | PROOF-GATE.md §7 (StepVerifyResult schema_version: Literal[1]) | Immutable post-write (append-only event store row; rewrites of stepN-VERIFY.json on replay are projector-driven from events) | Per-Step machine-readable verification artifact. Pydantic StepVerifyResult v1 (server-side recomputed `overall_passed`; nested `must_haves` + `acceptance_criteria` + `verify_automated` results with bounded-truncation 2KB per check, 10KB total). Authoritative per-Step evidence. |
| `slice-verification.sh` | plan-slice (authored at planning end); immutable post-execute-slice start | PROOF-GATE.md §4 + §8 (bash script; pure-machine; 600s timeout default; Slice-frontmatter override `verify: {slice_timeout_s: int}`) | Immutable post-execute-slice start (locked per PAP-03 mutability matrix on the parent Slice) | Per-Slice executable bash script. Runs at verify-slice stage. Aggregates Step-level evidence (reads each `stepN-VERIFY.json`) + runs cross-Step integration checks. Pure-machine; exit 0 = pass (gates `N-VERIFICATION.md` projector emission); non-zero = fail. |
| `deferred-items.md` | execute-slice (auto-appended by `state.step.scope_check` projector on `exception_matched=False` events) + verify-slice (Slice SUMMARY.md surface step) | SCOPE-PROHIBITION.md §9 (5-column table: ID, source_task, description, raised_at, status) | Mutable (humans + harness append rows; status updates allowed) | Per-Slice out-of-scope log. Auto-append rule: `scope_check` events with unresolved EXCEPTION_RE produce new rows. Status vocabulary: `open`, `scheduled-next-slice`, `scheduled-future-milestone`, `rejected`, `resolved-in-slice`. Surfaces in Slice SUMMARY.md `## Deferred Items` section. |
| `N-VERIFICATION.md` (column-schema pin) | verify-slice (deterministic projector — re-renderable from event store at any time) | PROOF-GATE.md §8 (10-column truth-table schema: step_id, task_id, check_id, scope, source_expr, verdict, strike_count_at_close, gate_strike_event_ids, evidence_excerpt, timestamp) | Mutable (re-renderable; the underlying event-store source rows are append-only) | Existing v40 artifact; column schema previously implicit. Phase 404 PINS the schema to PROOF-GATE.md §8 (rolled-up wide audit-traceable view). Per-row `evidence_excerpt` <= 2KB; whole-file size unbounded (per-Step JSON files cap evidence). Ordering: Step DAG topology, then check_id index ascending within each Step. omitted rows ARE included (audit clarity). |

### Conventions inherited

All v41 Phase 404 artifact additions follow v40 conventions:
- **Filename form**: `stepN` prefix has no dash and no leading zeros (per Phase 402 carry-forward + v40 ARTIFACT-CATALOG.md confirmation).
- **Per-Slice folder**: artifacts live in `slices/N-name/` per the canonical Slice folder layout (SLC-06).
- **Schema-version migration**: `stepN-VERIFY.json` carries `schema_version: Literal[1]` per PROOF-GATE.md §7; bump literal to migrate; old files surface as parse errors.
- **Build-mode only**: all three artifacts (and the column-schema pin) live under Build-mode subtree; teach-mode equivalents are v47 scope.
- **Mutability classification**: stepN-VERIFY.json immutable post-write; slice-verification.sh immutable post-execute-slice start; deferred-items.md mutable (rows appended over Slice lifecycle); N-VERIFICATION.md mutable-but-re-renderable (projector idempotent from event store).

### Authoritative ordering

Pydantic class definitions in the owning specs (PROOF-GATE.md / SCOPE-PROHIBITION.md) are authoritative; this catalog amendment is a registry index — full schemas live in the owning specs. If the registry row description and the owning spec drift, the owning spec wins; readers should treat the registry as a forward-pointer index, not a substitute for the spec.

### Effect on this document

Canonical Slice folder layout (ART-01 entries for `slices/N-name/`) gains three new files: `stepN-VERIFY.json` (one per Step), `slice-verification.sh` (one per Slice), and `deferred-items.md` (one per Slice; may be empty). Plus a column-schema pin for the existing `N-VERIFICATION.md`. Readers consulting this catalog for v41+ scheduling should cross-reference PROOF-GATE.md §8 (column schema) + §9 (artifact list) and SCOPE-PROHIBITION.md §9 (deferred-items.md). v14 Build Kernel implements the StepVerifyResult parser, the slice-verification.sh runner with timeout, the N-VERIFICATION.md projector, and the deferred-items.md auto-append projector.

*Original v40 spec text + Phase 402 amendment above this block are untouched. This amendment is purely additive, appended per Phase 402 convention (no in-line strikethroughs).*

---

## v41 Amendment — Phase 405 Deviation + Subagent Artifacts

**Phase:** 405 (Deviation Rules & Subagent Management)
**Status:** Canonical (v41)
**Append-only:** All entries below are NEW; nothing above this header has been edited.
**Build-mode only:** All entries live under `state_build/` lineage. CI import-graph lint enforces no `state_teach/` imports.
**Naming discipline:** All module paths are `state_build/*`; no `state_gsd/*` or `gsd_*` paths exist in Phase 405.

Phase 405's three sibling spec docs (DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, SUBAGENT-MONITORING.md) introduce nine new Python modules + one extension to Phase 402's `CompactionSnapshot` Pydantic + one new `stepNSUMMARY.md` section. Full Pydantic schemas + behaviors live in the owning Phase 405 spec docs; this amendment is a registry index.

### New Artifacts

| Filename / Module Path | Producer Stage | Schema Owner (spec doc) | Immutability | Description |
|---|---|---|---|---|
| `state_build/deviation/arch_patterns.py` | v14 Build Kernel | DEVIATION-RULES.md §5 | append-extensible | `ARCH_PATTERN_ALLOWLIST: list[re.Pattern]` (6 starter entries) + `match_arch_pattern()` + `classify_diff_kind()` — Rule-4 detection single-source-of-truth. |
| `state_build/deviation/log_deviation.py` | v14 Build Kernel | DEVIATION-RULES.md §3-§4 | append-extensible | `log_deviation` MCP tool handler + 5-step cross-validation chain. |
| `state_build/commit/trailers.py` | v14 Build Kernel | DEVIATION-RULES.md §5 | append-extensible | STATE-* trailer constants (`STATE-Task`, `STATE-DeviationRule`, `STATE-DeviationAttempt`, `STATE-Subagent-Invocation`) + `infer_commit_type()` (gsd-2 COMMIT_TYPE_RULES adapter). |
| `state_build/projectors/deviation_summary.py` | v14 Build Kernel | DEVIATION-RULES.md §10 | append-extensible | `## Deviations` SUMMARY section projector — subscribes to `deviation_logged` + `deviation_resolution_recorded`; aggregates by `(rule_id, issue_signature)`; writes 8-column markdown table to `stepNSUMMARY.md`. |
| `state_build/subagents/types.py` | v14 Build Kernel | SUBAGENT-MANAGEMENT.md §3 | append-extensible | `SubagentType` Literal (14 named types) + `STAGE_ROSTER: dict[SliceStage, frozenset[SubagentType]]` (4 stage rosters). |
| `state_build/subagents/dispatch.py` | v14 Build Kernel | SUBAGENT-MANAGEMENT.md §2 + §5-§6 | append-extensible | `dispatch_subagent` MCP tool handler + DispatchSubagent / SingleDispatch / ParallelDispatch / ChainDispatch Pydantic shapes + whitelist enforcement + parallel-cap accounting. |
| `state_build/subagents/parallel_cap.py` | v14 Build Kernel | SUBAGENT-MANAGEMENT.md §6 | append-extensible | `MAX_PARALLEL_CAP_DEFAULT = 20` + `resolve_effective_cap()` + `acquire_slot()` / `release_slot()` — daemon-side FIFO semaphore. |
| `state_build/subagents/returns.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §3 | append-extensible | `SUBAGENT_RETURN_REGISTRY: dict[SubagentType, type[SubagentReturnBase]]` + `ArtifactDeclaration` + `SubagentReturnBase` Pydantic shapes; per-stage subclasses in `returns_{stage}.py` modules. |
| `state_build/subagents/spot_check.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §4 | append-extensible | `run_spot_check_stack()` — 4-layer pure-machine validation (process / pydantic / artifact / commit). |
| `state_build/subagents/restart.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §6 | append-extensible | `build_restart_prompt()` — augmented `<prior_crash>` XML continuation context. |
| `state_build/subagents/remediation_hints.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §6 | append-extensible | Default `remediation_hint` strings keyed by `crash_source`. |
| `state_build/subagents/orphan_reconcile.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §7 | append-extensible | 6-step daemon-resume orphan reconciliation flow + `SubagentOrphanDetected` + `InFlightSubagent` Pydantic. |
| `state_build/subagents/autonomy.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §8 | append-extensible | `compute_effective_autonomy(parent_effective, override) -> AutonomyMode` — SUB-09 inheritance flow. |
| `stepNSUMMARY.md` `## Deviations` section | v15 Build Core Commands (verify-slice) | DEVIATION-RULES.md §10 | projector-generated | 8-column markdown table; section omitted when zero deviations. |

### CompactionSnapshot Extension (Phase 402 Pydantic model)

Phase 405 EXTENDS Phase 402's `CompactionSnapshot` Pydantic model with two new fields. The schema owner remains Phase 402's CONTEXT-PROTOCOL.md; the Phase 405 extension is documented in SUBAGENT-MONITORING.md §7:

| Field | Type | Owning REQ → Spec |
|---|---|---|
| `subagent_restart_counters` | `dict[str, int]` (key = `"{parent_task_id}|{subagent_type}"`) | SUB-08 → SUBAGENT-MONITORING.md §7 |
| `in_flight_subagents` | `list[InFlightSubagent]` | SUB-08 → SUBAGENT-MONITORING.md §7 |

### Authoritative-ordering note

Pydantic class definitions in the owning Phase 405 spec docs are authoritative; this amendment is a registry index for module paths. When module-export details diverge between this catalog and the owning spec, the owning spec wins.
