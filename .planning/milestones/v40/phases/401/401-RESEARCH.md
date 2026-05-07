# Phase 401: Artifact Catalog, Naming, Layout, Cross-Refs — Research

**Researched:** 2026-05-07
**Domain:** Design-phase specification — filesystem blueprint, artifact catalog, naming conventions, cross-referencing system, consistency validation
**Confidence:** HIGH

## Summary

Phase 401 is the **second and final phase** of the v40 design milestone. It transforms Phase 400's tier definitions, state machines, and event taxonomies into a complete, actionable blueprint for the `.state/build/` filesystem. Every file, directory, template, naming rule, cross-reference mechanism, and consistency check is specified in architecture documents — zero code is written.

The phase has 17 requirements across three categories: ART (artifact catalog — 5 reqs), DSK (on-disk layout — 6 reqs), and REF (cross-referencing — 6 reqs). All 17 are under Claude's discretion for the *specific design* but constrained by 17 locked decisions from CONTEXT.md that set structural boundaries (e.g., tier-separated index.json, snapshot-before-mutation immutability, daemon-startup blocking gate).

The primary deliverable is **4–6 specification documents** that form the complete `.state/build/` blueprint. These specs are consumed downstream by v41+ (runtime implementation), v42 (quality pipeline), v43 (GSD command ports), and v14–v17 (build-mode implementation).

**Primary recommendation:** Structure Phase 401 as **3 plans** mirroring the plan structure of Phase 400: Plan 1 covers ART (catalog + templates), Plan 2 covers DSK (directory tree + index.json + naming), Plan 3 covers REF (cross-reference format + W-codes + validate_consistency()).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Artifact catalog (ART-01) | Specification document | — | Purely a design artifact cataloging all files across all tiers |
| Templates (ART-02) | Specification document | Design contract for v41+ | Templates are markdown files with frontmatter; Phase 401 defines the formats |
| Immutability rules (ART-03) | Specification per tier | Daemon (v41+) | Phase 401 specifies rules; daemon enforces via snapshot-before-mutation |
| Projection vs authored (ART-04) | Specification document | Projector (v41+) | Phase 401 classifies; projector implements the projection rebuilds |
| Schema validation (ART-05) | Specification document | Pydantic schemas (v41+) | Phase 401 specifies validation rules; pydantic models from Phase 400 |
| Directory tree (DSK-01) | Specification document | Filesystem (v41+) | Phase 401 defines the blueprint |
| Naming conventions (DSK-02) | Specification document | All tooling (v41+) | Phase 401 defines conventions; all commands follow them |
| STATE.md placement (DSK-03) | Specification document | Projector (v41+) | Phase 401 specifies placement; projector writes consolidated JSON |
| File count (DSK-04) | Specification document | Agent harness (v41+) | Phase 401 specifies per-Step file strategy |
| index.json (DSK-05) | Specification + JSON schema | Projector (v41+) | Phase 401 defines schema; projector rebuilds |
| Concurrent access (DSK-06) | Specification document | Daemon (v41+) | Phase 401 defines rules; daemon enforces |
| Cross-reference format (REF-01) | Specification document | Projector index (v41+) | Phase 401 defines ID-based resolution algorithm |
| Edge types (REF-02) | Specification document | Scheduler (v5, existing) | Phase 400 D-12 defines edge types; Phase 401 specifies how they appear in cross-refs |
| Dependency policy (REF-03) | Specification document | Scheduler + schema validation (v41+) | Phase 401 specifies rules; scheduler and validator enforce |
| Broken references (REF-04) | Specification document | Consistency validator (v41+) | Phase 401 specifies cascade rules per edge type |
| W-codes (REF-05) | Specification document | Projector health module (v41+) | Phase 401 defines 15 codes with severities |
| validate_consistency() (REF-06) | Function specification | Daemon startup (v41+) | Phase 401 defines the function contract; implemented v41+ |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-401-01:** ARC.md and STAGE.md are agent-authored tier-definition files (created by `state-new arc`/`state-new stage`). Projector updates status field only. NOT projector-rebuilt projections.
- **D-401-02:** DECISIONS.md added at each tier for gray-area decision logging. Agent-authored, append-only.
- **D-401-03:** CRIT.md = numbered falsifiable requirements (CRIT-01, CRIT-02, ...). Must-have truths. Format: each criterion is a testable assertion with acceptance evidence trail.
- **D-401-04:** MAP.md = generated plan + tracker. Created by planner during `state-new` flow. Contains child IDs (stages for arc, slices for stage), what each child must accomplish (derived from CRIT), and tracking checkboxes updated by projector automatically as children advance.
- **D-401-05:** MAP.md is unique per tier and CRIT set. Arc MAP.md lists stages with IDs + goals. Stage MAP.md lists slices with IDs + goals.
- **D-401-06:** Slice workflow docs remain separate files: DESIGN.md, RESEARCH.md, stepNPLAN.md (one per step), VERIFICATION.md, SUMMARY.md. Each is the output of its workflow step and input for the next.
- **D-401-07:** STATE.md projections are consolidated JSON under `.state/build/state/` (canonical). CLI `state export-state` generates per-directory STATE.md on demand. Keeps source-controlled markdown clean.
- **D-401-08:** Step files remain separate (7+ files per 3-step Slice acceptable). Each file has a clear purpose and workflow role. No consolidation.
- **D-401-09:** Agent-authored artifacts: ARC.md, STAGE.md, CRIT.md, MAP.md, DESIGN.md, RESEARCH.md, stepNPLAN.md, VERIFICATION.md, SUMMARY.md, DECISIONS.md.
- **D-401-10:** Projector-rebuilt artifacts: index.json, consolidated STATE.md JSON projections under `.state/build/state/`.
- **D-401-11:** MAP.md checkboxes updated by projector automatically as child tiers advance (state.stage.*, state.slice.* events trigger checkbox updates).
- **D-401-12:** Immutability: stepNPLAN.md and CRIT.md lock when Slice enters `in_progress`. DESIGN.md and RESEARCH.md remain mutable.
- **D-401-13:** Immutability enforced by snapshot-before-mutation protocol at daemon level. Attempted mutation of a locked artifact is rejected (not warned — blocked).
- **D-401-14:** index.json structure: tier-separated — `{arcs: {}, stages: {}, slices: {}, steps: {}}`. Each entry maps ID to type, path, status, last_updated. O(1) ID→path resolution.
- **D-401-15:** Broken reference handling: surface + block. Referrer flagged with W-code. If referrer is `in_progress`, execution blocks until user resolves (reassign target, defer dependency, or remove reference). No auto-cascade.
- **D-401-16:** W001–W015 consistency codes use tiered severity: ERROR (must fix, blocks ship/verify), WARNING (should fix, advisory at plan time), INFO (informational, no action required).
- **D-401-17:** `validate_consistency()` is a blocking gate on daemon startup. ERROR-severity codes prevent daemon start. Daemon MUST auto-launch a resolution workflow (session or subagent) that receives the error context and fixes consistency. Not a deadlock — auto-resolution path exists.

### Claude's Discretion

- Exact frontmatter field list per artifact (user gave structural decisions; planner fills in specific fields)
- The specific 15 W-codes (W001–W015) and their exact severity assignments
- Template exact markdown format (planner creates from artifact decisions)
- index.json exact JSON schema (planner designs from tier-separated decision)
- validate_consistency() function signature and implementation details

### Deferred Ideas (OUT OF SCOPE)

- Cross-arc dependency use cases — explicitly rejected in Phase 400 D-10 (same-parent only). Can be revisited if a concrete multi-arc integration use case emerges.
- Optional review/lock-in/ship sub-flows at Slice level — deferred from Phase 400. Workflow design for v41/v43, not artifact catalog scope.
- Templates for optional sub-flow artifacts (review, lock-in, ship) — out of scope for Phase 401 core artifact catalog. Add when sub-flows are designed.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ART-01 | Complete artifact catalog documenting every file type across all four tiers with purpose, owning tier, schema ownership, creation/update triggers, and file format | Phase 400 tier specs define owned artifacts per tier. D-401-09/D-401-10 classify agent vs projector ownership. Need to enumerate all file types and their trigger conditions. |
| ART-02 | Templates for every artifact file type (ARC.md.tmpl, STAGE.md.tmpl, SLICE.md.tmpl, STEP.md.tmpl, DESIGN.md.tmpl, PLAN.md.tmpl, VERIFY.md.tmpl, STATE.md) with validated frontmatter structure | Phase 400 FRONTMATTER-SCHEMAS.md provides pydantic models. Templates are markdown with validated YAML frontmatter blocks. STATE.md is projector-rebuilt, not templated (D-401-07). |
| ART-03 | Immutability rules per tier — STEP.md verify_contract locks after execute begins, ARC.md phases[] array locks while child Phases are in_progress, snapshot-before-mutation protocol | D-401-12/D-401-13 specify which artifacts lock when. Need to design the snapshot-before-mutation protocol integrating with v4 Snapshot service. |
| ART-04 | Classification of projections (STATE.md, index.json) vs agent-authored originals (ARC.md goal/description, STEP.md plan, etc.) | D-401-09/D-401-10 provide the classification. Need to document the projection rebuild mechanism and how agent-written fields survive projector rebuilds. |
| ART-05 | Schema validation rules — pydantic validation on every artifact read, unknown fields rejected, cross-reference IDs verified, descoped-ID references flagged | Phase 400 pydantic models use `extra="forbid"`. Need to specify when validation fires (creation time, read time, verify time) and how cross-refs are verified against index.json. |
| DSK-01 | Complete `.state/build/` directory tree — arcs/{arc-id}/stages/{stage-id}/slices/{slice-id}/ with hierarchy nesting | Phase 400 tier specs define directory paths per tier. Need to reconcile with D-401-07 (consolidated STATE.md) and specify the exact tree with every directory and artifact file. |
| DSK-02 | Naming conventions — numeric IDs (sequential per parent, zero-padded), directory paths (ID-based), slugs (display-only, derived from title), display prefixes (child-prefixed) | D-01/D-02 (Phase 400) define dash-prefix, no-leading-zeros IDs with kebab-case slug suffixes. D-04 defines step file naming. |
| DSK-03 | STATE.md placement — consolidated JSON projections under `.state/build/state/` are canonical, `export-state` CLI for on-demand per-directory STATE.md | D-401-07 specifies the consolidated strategy. Need to design the JSON projection format and the export-state CLI contract. |
| DSK-04 | Per-Step file consolidation strategy — 5 separate files vs consolidated ARTIFACTS.md, file count at scale (20 Arcs × ~100 Steps = ~2,000 Steps) | D-401-08 specifies separate files remain. Need to document the file count strategy and the rationale for separate vs consolidated. |
| DSK-05 | index.json artifact registry at `.state/build/index.json` — machine-readable, ID→path mapping, rebuilt by projector | D-401-14 defines tier-separated structure. Need to design exact JSON schema with all entry fields and the projector rebuild trigger conditions. |
| DSK-06 | Concurrent access support — multiple worktrees, clear directory creation rules | Phase 400 D-04: Steps are flat files, no directories. Slices own worktrees. Need to specify lock-free append-only write model. |
| REF-01 | Cross-reference format — stable IDs (never paths, never slugs), ID→path resolution via projector's index, content-hash pinning at creation time | Phase 400 D-09 defines ID resolution via index.json. D-01 defines ID format. Need to design the resolution algorithm and hash pinning mechanism. |
| REF-02 | Depends-on edge types (blocks, soft, data) — full semantics per type, scheduler behavior, artifact path copy for data edges | Phase 400 D-12 defines the three edge types. Scheduler (v5) already knows these types. Need to specify how they manifest in cross-references. |
| REF-03 | Cross-tier dependency policy — same-tier allowed, upward allowed, downward forbidden, cross-mode blocked | Phase 400 D-10 defines same-parent-only constraint. Need to specify validation rules for each direction. |
| REF-04 | Broken reference handling — behavior when target deleted/descoped/abandoned, cascade rules per edge type | Phase 400 DESC-SEMANTICS.md defines abandon cascade (D-13), deferment (D-14), blocked (D-15). Need to specify W-code assignments per scenario. |
| REF-05 | 15 consistency validation codes (W001–W015) — covering orphan IDs, stale status, missing parents, cross-referenced-to-descoped, mismatched projections, duplicate IDs, invalid edges, cycle detection, cross-mode leakage | Under Claude's discretion for specific code assignments. Need to design the full catalog of 15 codes with severities. |
| REF-06 | validate_consistency() function specification — runs on daemon startup, walks all artifacts, verifies every cross-reference, detects filesystem-vs-event-store divergence | D-401-17 defines the blocking gate behavior. Need to design function signature, check algorithm, and error output format. |

## Standard Stack

### Core (Design Patterns & Reference Architectures)

| Library / Reference | Version / Source | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic `extra="forbid"` | As defined in Phase 400 FRONTMATTER-SCHEMAS.md | Schema validation contracts for all artifacts | Phase 400 established this convention across all tier frontmatter models |
| YAML frontmatter | Standard markdown convention (--- delimited) | Artifact metadata blocks | GSD reference pattern; all state artifacts follow this convention |
| Hierarchical aggregate IDs | `arc-{n}/stage-{n}/slice-{n}/step-{n}` (Phase 400) | Cross-reference target format | Phase 400 FRONTMATTER-SCHEMAS.md defines this; used for event store keying |
| CQRS event-sourced architecture | `.state/events.sqlite` authoritative | Projector rebuilds STATE.md / index.json | ARCHITECTURE.md §5; all truth in event store |
| Composite event cascade | Phase 400 COMPOSITE-CASCADE.md | Cross-tier rollup | Phase 400 specifies the cascade; Phase 401 references it for cross-reference behavior |

### Supporting (Documentation Conventions)

| Reference | Source | Purpose | When to Use |
|---------|---------|---------|-------------|
| GSD artifacts.cjs pattern | `state-inputs/get-shit-done/bin/lib/artifacts.cjs` (10 exact-match + 2 pattern-match) | Canonical artifact registry design | index.json and artifact catalog design reference |
| GSD verify.cjs pattern | `state-inputs/get-shit-done/bin/lib/verify.cjs` (19 warning codes, schema drift detection) | Health check design pattern | W-codes (W001–W015) design reference |
| GSD frontmatter.cjs pattern | `state-inputs/get-shit-done/bin/lib/frontmatter.cjs` | YAML frontmatter handling | Template frontmatter design reference (not available at state-inputs; use Phase 400 FRONTMATTER-SCHEMAS.md) |
| Projector handler registration | `src/state_core/projector.py` — `@_register_handler` decorator | Pattern for new projector handlers | Integration point for index.json rebuild handler |
| Scheduler EdgeKind types | `src/state_core/scheduler.py` — `EdgeKind = Literal["blocks", "soft", "data"]` | Already-defined edge type enumeration | REF-02 edge type specifications must match |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tier-separated index.json | Single flat map | Tier-separated (D-401-14) is decided — enables O(1) tier-filtered queries |
| Per-directory STATE.md | Consolidated JSON only | Consolidated JSON is canonical (D-401-07); per-directory is generated on-demand |
| Step consolidation (1-2 files) | 7+ separate files per Step | Separate files (D-401-08) — each has a clear purpose; consolidation obscures workflow role |

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Phase 401 Design Flow                        │
│                                                                  │
│  Phase 400 Inputs (READ-ONLY)                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ TIER-*.md│  │ FSM      │  │ EVENT        │  │ FRONTMATTER│  │
│  │ (4 tiers)│  │ TABLES   │  │ TAXONOMY     │  │ SCHEMAS    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  └─────┬──────┘  │
│       │              │               │                │         │
│       └──────────────┴───────────────┴────────────────┘         │
│                            │                                     │
│                            ▼                                     │
│         ┌──────────────────────────────────────┐                │
│         │        Phase 401 Design Process       │                │
│         │                                       │                │
│         │  Plan 1: ART (Catalog + Templates)    │                │
│         │    ┌─────────────────────────┐        │                │
│         │    │ Artifact Catalog Table  │        │                │
│         │    │ (ART-01: all 15+ types) │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ 8 Templates with        │        │                │
│         │    │ validated frontmatter   │        │                │
│         │    │ (ART-02)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ Immutability rules      │        │                │
│         │    │ per tier + artifact     │        │                │
│         │    │ (ART-03)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ Projection vs authored  │        │                │
│         │    │ classification          │        │                │
│         │    │ (ART-04)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ Schema validation rules │        │                │
│         │    │ (ART-05)                │        │                │
│         │    └─────────────────────────┘        │                │
│         │                                       │                │
│         │  Plan 2: DSK (Layout + Naming)        │                │
│         │    ┌─────────────────────────┐        │                │
│         │    │ Directory tree spec     │        │                │
│         │    │ (DSK-01)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ Naming conventions      │        │                │
│         │    │ (DSK-02)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ STATE.md placement +    │        │                │
│         │    │ export-state CLI        │        │                │
│         │    │ (DSK-03)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ File count strategy     │        │                │
│         │    │ (DSK-04)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ index.json JSON schema  │        │                │
│         │    │ (DSK-05)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ Concurrent access rules │        │                │
│         │    │ (DSK-06)                │        │                │
│         │    └─────────────────────────┘        │                │
│         │                                       │                │
│         │  Plan 3: REF (Cross-Refs + Health)    │                │
│         │    ┌─────────────────────────┐        │                │
│         │    │ Cross-reference format  │        │                │
│         │    │ (REF-01)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ Edge type semantics     │        │                │
│         │    │ (REF-02)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ Dependency policy       │        │                │
│         │    │ (REF-03)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ Broken reference rules  │        │                │
│         │    │ (REF-04)                │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ 15 W-codes with         │        │                │
│         │    │ severities (REF-05)     │        │                │
│         │    ├─────────────────────────┤        │                │
│         │    │ validate_consistency()  │        │                │
│         │    │ function spec (REF-06)  │        │                │
│         │    └─────────────────────────┘        │                │
│         └──────────────────────────────────────┘                │
│                            │                                     │
│                            ▼                                     │
│         ┌──────────────────────────────────────┐                │
│         │         Output Specifications        │                │
│         │                                       │                │
│         │  specs/ARTIFACT-CATALOG.md            │                │
│         │  specs/TEMPLATES.md   (or templates/) │                │
│         │  specs/DIRECTORY-TREE.md              │                │
│         │  specs/INDEX-SCHEMA.md                │                │
│         │  specs/NAMING-CONVENTIONS.md          │                │
│         │  specs/CROSS-REFERENCES.md            │                │
│         │  specs/CONSISTENCY-CODES.md           │                │
│         │  specs/VALIDATE-FUNCTION.md           │                │
│         │                                      │                │
│         │  Consumed by: v41+ (runtime), v42    │                │
│         │  (quality), v43 (GSD ports), v14-17 │                │
│         └──────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Specification Structure

```
.planning/milestones/v40/phases/401/
├── 401-CONTEXT.md                          # User decisions (already exists)
├── 401-RESEARCH.md                         # This file
├── 401-01-PLAN.md                          # Plan 1: Artifact Catalog + Templates
├── 401-02-PLAN.md                          # Plan 2: Directory Layout + Naming
├── 401-03-PLAN.md                          # Plan 3: Cross-References + Consistency Codes
├── specs/
│   ├── ARTIFACT-CATALOG.md                 # ART-01: Complete file-type catalog
│   ├── TEMPLATES.md                        # ART-02: All 8+ templates with frontmatter
│   ├── IMMUTABILITY-RULES.md               # ART-03: Lock rules per tier + snapshot protocol
│   ├── PROJECTION-CLASSIFICATION.md        # ART-04: Projector vs agent ownership
│   ├── SCHEMA-VALIDATION.md                # ART-05: Validation rules + cross-ref verification
│   ├── DIRECTORY-TREE.md                   # DSK-01, DSK-02: Full directory tree + naming
│   ├── STATE-PLACEMENT.md                  # DSK-03: Consolidated JSON + export-state CLI
│   ├── FILE-COUNT-STRATEGY.md              # DSK-04: Per-Step file consolidation rationale
│   ├── INDEX-SCHEMA.md                     # DSK-05: index.json JSON schema + rebuild rules
│   ├── CONCURRENT-ACCESS.md                # DSK-06: Lock-free append-only write rules
│   ├── CROSS-REFERENCES.md                 # REF-01, REF-02, REF-03: Format + edges + policy
│   ├── BROKEN-REFERENCES.md                # REF-04: Broken reference cascade rules
│   ├── CONSISTENCY-CODES.md                # REF-05: W001–W015 catalog with severities
│   └── VALIDATE-FUNCTION.md                # REF-06: validate_consistency() specification
```

**Consolidation note:** Some topics may combine into fewer documents if they're tightly coupled (e.g., DIRECTORY-TREE.md could include naming conventions and concurrent access rules in one document). The planner decides the optimal document split based on narrative coherence. The minimum viable set is 5–6 documents covering all 17 requirements.

### Pattern 1: Artifact Catalog Entry Format

**What:** Every artifact in the catalog is documented as a structured entry with consistent fields.
**When to use:** ART-01 artifact catalog specification.
**Example:**
```markdown
### ARC.md

| Property | Value |
|----------|-------|
| **Purpose** | Arc definition document — defines the feature block scope |
| **Owning Tier** | Arc |
| **Schema Owner** | Agent (id, title, goal, success_criteria, depends_on) / Projector (status, stage_count, shipped_stage_count, completed_at) |
| **Created By** | `/state-new arc` command |
| **Creation Trigger** | User creates a new Arc |
| **Updated By** | Agent (edits frontmatter) / Projector (status updates on state change events) |
| **Update Triggers** | state.arc.started, state.arc.stages_shipped, state.arc.shipped, state.arc.abandoned |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | `ArcFrontmatter` (Phase 400 FRONTMATTER-SCHEMAS.md) |
| **Immutability** | Mutable while Arc is `planned`; `depends_on` and `success_criteria` lock when Arc enters `in_progress` |
| **Cross-Refs From** | None (Arc is root tier; no parent) |
| **Cross-Refs To** | Child Stages via MAP.md; sibling Arcs via `depends_on` |
| **File Path** | `.state/build/arcs/arc-{n}/ARC.md` |
```

### Pattern 2: Directory Tree Blueprint Format

**What:** The complete `.state/build/` directory tree is presented as an annotated tree with every file and directory explained.
**When to use:** DSK-01 directory tree specification.
**Example:**
```
.state/build/
├── index.json                    # [PROJECTOR] Artifact registry — ID→path mapping
├── state/                        # [PROJECTOR] Consolidated STATE.md JSON projections
│   ├── arcs.json                 # All Arc STATE projections
│   ├── stages.json               # All Stage STATE projections
│   ├── slices.json               # All Slice STATE projections
│   └── steps.json                # All Step STATE projections
├── arcs/
│   └── arc-{n}/                  # D-01: dash-prefix, no leading zeros
│       ├── ARC.md                # [AGENT] Arc definition
│       ├── CRIT.md               # [AGENT] Must-have criteria (CRIT-01, CRIT-02, ...)
│       ├── MAP.md                # [AGENT+PROJECTOR] Plan + tracker with checkboxes
│       ├── DECISIONS.md          # [AGENT] Gray-area decision log (append-only)
│       ├── stages/
│       │   └── stage-{n}/        # D-01: dash-prefix, no leading zeros
│       │       ├── STAGE.md      # [AGENT] Stage definition
│       │       ├── CRIT.md       # [AGENT] Must-have criteria
│       │       ├── MAP.md        # [AGENT+PROJECTOR] Slice plan + tracker
│       │       ├── DECISIONS.md  # [AGENT] Gray-area decision log
│       │       └── slices/
│       │           └── slice-{n}/# D-01: integer, or slice-{n}.{d} for decimal
│       │               ├── SLICE.md           # [AGENT] Slice definition
│       │               ├── DESIGN.md          # [AGENT] Design phase output
│       │               ├── RESEARCH.md        # [AGENT] Research phase output
│       │               ├── step1PLAN.md       # [AGENT] Run tracking file (Step 1)
│       │               ├── ...                # [AGENT] stepNPLAN.md (Steps 2..N)
│       │               ├── VERIFICATION.md    # [AGENT] Verify phase output
│       │               ├── SUMMARY.md         # [AGENT] Summary phase output
│       │               └── {worktree}/        # Git worktree (per Slice)
└── templates/                    # [STATIC] Artifact templates (shipped with engine)
    ├── ARC.md.tmpl
    ├── STAGE.md.tmpl
    ├── SLICE.md.tmpl
    ├── STEP.md.tmpl
    ├── CRIT.md.tmpl
    ├── MAP.md.tmpl
    ├── DESIGN.md.tmpl
    ├── RESEARCH.md.tmpl
    ├── PLAN.md.tmpl
    └── VERIFICATION.md.tmpl
```

### Pattern 3: W-Code Catalog Format

**What:** Each consistency validation code has a structured entry with severity, trigger, and resolution.
**When to use:** REF-05 W-code specification.
**Example:**
```markdown
### W001: Orphan ID in index.json

| Property | Value |
|----------|-------|
| **Code** | W001 |
| **Name** | Orphan ID in index.json |
| **Category** | Cross-Reference Integrity |
| **Severity** | ERROR |
| **Trigger** | An entry exists in index.json but no corresponding file exists on disk |
| **Detection Logic** | `validate_consistency()` iterates all index.json entries; for each entry, checks `os.path.exists(entry.path)`. Missing file → W001 |
| **Resolution** | Manual: remove orphan entry from index.json (projector will rebuild correctly on next state change). Auto-resolution: projector can remove orphan entries on daemon restart if the event stream confirms no such aggregate was created. |
| **Blocking** | BLOCKS daemon startup (ERROR severity per D-401-17) |
| **Affected Tiers** | All (any tier's artifact can become orphaned) |
```

### Anti-Patterns to Avoid

- **Spec-padding:** Filling documents with restatements of Phase 400 material instead of new design decisions. Phase 401 should reference Phase 400, not reproduce it.
- **Premature implementation detail:** Including Python function bodies, SQL schemas, or CLI argument parsers. Phase 401 is a design contract, not a code spec — describe WHAT, let v41+ decide HOW.
- **Missing consistency across documents:** ART-01 catalog says a file exists at path X, DSK-01 tree shows it at path Y. This is fatal — every artifact path must be consistent across all specs.
- **Ambiguous severity:** "This should probably be a warning" — NO. Every W-code must have an unambiguous severity (ERROR/WARNING/INFO) with explicit rationale.
- **Template drift from frontmatter schemas:** A template includes a field not in the pydantic model, or omits a required field. All templates must be validated against their corresponding Phase 400 frontmatter schema.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frontmatter parsing | Custom YAML parser | YAML frontmatter convention (--- delimited) | Standard markdown convention; Phase 400 pydantic models provide the validation contract |
| ID validation regex | Ad-hoc string checks | Per-tier regex patterns from Phase 400 DESC-SEMANTICS.md: `^arc-\d+$`, `^stage-\d+(\.\d+)?$`, `^slice-\d+(\.\d+)?$`, `^step-\d+(\.\d+)?$` | Already specified; Phase 401 references, doesn't redefine |
| Cross-reference ID format | Paths, slugs, URNs | Hierarchical aggregate IDs: `arc-{n}/stage-{n}/slice-{n}/step-{n}` | Phase 400 FRONTMATTER-SCHEMAS.md defines this; used for event store keying |
| Edge type definitions | Custom dependency taxonomy | Phase 400 D-12: `blocks`, `soft`, `data` — already matched by scheduler `EdgeKind` literal | Already locked decision; cross-refs use the same edge types |
| State machine validation | Custom state validation | Phase 400 FSM-TABLES.md transition tables | Already specified; consistency codes reference these transitions |
| Event-driven projector rebuild | Custom projection engine | Existing `src/state_core/projector.py` handler registration pattern | Phase 401 defines WHAT handlers are needed; v41+ follows existing pattern |

**Key insight:** Phase 401 is primarily a SYNTHESIS phase — it takes decisions and specs from Phase 400 and organizes them into a complete filesystem blueprint. Most "don't hand-roll" items are about not redefining what Phase 400 already defined. The Phase 401 planner must be vigilant about referencing Phase 400 rather than duplicating it.

## Common Pitfalls

### Pitfall 1: Inconsistency Between Artifact Catalog and Directory Tree

**What goes wrong:** ARTIFACT-CATALOG.md says ARC.md lives at `.state/build/arcs/arc-{n}/ARC.md`, but DIRECTORY-TREE.md shows it at `.state/build/arcs/{arc-id}/ARC.md` (using a different variable name for the same concept). Downstream implementors end up with two competing "official" layouts.

**Why it happens:** Different plan agents writing different spec documents with different conventions. If both documents define paths independently, drift is nearly guaranteed.

**How to avoid:** Define paths ONCE in the artifact catalog (ART-01), then have DIRECTORY-TREE.md REFERENCE the catalog paths with the same variable notation. Or define the canonical directory tree first (DSK-01), then have the artifact catalog cite it. Either way, one document is the single source of truth for paths.

**Warning signs:** Two documents using different variable names for the same tier (arc-{n} vs {arc-id} vs arc_id). One document cites a path the other doesn't list.

### Pitfall 2: Frontmatter Field Drift Between Templates and Schemas

**What goes wrong:** The ARC.md.tmpl includes a field `priority: high` but ArcFrontmatter in Phase 400 has no `priority` field (and uses `extra="forbid"`). v41+ validation would reject the template's output.

**Why it happens:** Templates are designed for usability by a different agent than the one who designed the pydantic models. Without cross-validation, fields drift.

**How to avoid:** For every template, enumerate its frontmatter fields. Cross-reference each field against the corresponding Phase 400 pydantic model. Document the cross-reference explicitly in TEMPLATES.md. Include a validation table that confirms every template field exists in the schema.

**Warning signs:** Template includes fields not mentioned in FRONTMATTER-SCHEMAS.md. Template omits required fields. Template uses different field names than the schema.

### Pitfall 3: W-Code Severity Inflation

**What goes wrong:** Every W-code gets assigned ERROR severity "to be safe," making the daemon startup gate so restrictive that it blocks for trivial issues.

**Why it happens:** It's easier to assign ERROR than to think through the actual operational impact of each inconsistency. The D-401-17 auto-resolution path provides a safety net that makes ERROR assignment seem low-risk.

**How to avoid:** For each W-code, ask: "Does this inconsistency actually prevent correct operation?" If the daemon can still function (just with degraded information), it's WARNING. If only the projector notices but no user-facing behavior changes, it's INFO. Only issues that make the event stream irreconcilable with the filesystem (data loss risk) are ERROR.

**Warning signs:** More than 5 ERROR-severity codes. Codes for "stale" or "potentially out of date" marked ERROR. Codes that only affect display marked ERROR.

### Pitfall 4: Missing Integration Point Alignment

**What goes wrong:** The index.json schema specifies a `status` field with values `["active", "completed", "failed"]`, but the FSM tables use `["planned", "in_progress", "shipped"]`. The projector can't map between them without an adapter — and nobody defined the mapping.

**Why it happens:** Each spec document is designed in isolation, focusing on its own domain without checking how other specs reference the same concepts.

**How to avoid:** Before finalizing any spec document, check: (1) Does this use the same state names as FSM-TABLES.md? (2) Does this use the same ID format as FRONTMATTER-SCHEMAS.md? (3) Does this reference the correct event types from EVENT-TAXONOMY.md? (4) Does this respect the edge-type semantics from DESC-SEMANTICS.md?

**Warning signs:** A spec document defines its own state enum instead of referencing FSM-TABLES.md. A spec document invents a new ID format instead of using the hierarchical format.

### Pitfall 5: Over-Specifying v41+ Implementation Details

**What goes wrong:** The validate_consistency() spec includes Python pseudocode with specific SQL queries, file I/O operations, and error handling patterns. This constrains v41+ implementation to a specific approach when better approaches may emerge.

**Why it happens:** The planner wants to be "complete" and drifts from design contract to implementation guide. The boundary between "specify what" and "specify how" is fuzzy.

**How to avoid:** For validate_consistency() and similar function specs: describe (1) what inputs it takes, (2) what checks it performs (as a bulleted list of conditions), (3) what output format it produces, and (4) when it runs. Do NOT describe internal data structures, database queries, or algorithmic approaches. The v41+ developer picks those.

**Warning signs:** Pseudocode with variable assignments and loops. References to specific Python modules (`os.path`, `json.load`). Database query syntax (`SELECT ... FROM events WHERE ...`).

## Code Examples

### Cross-Reference Resolution Algorithm (REF-01)

The cross-reference format uses stable aggregate IDs. The resolution algorithm maps an ID to its filesystem path via index.json:

```
Algorithm: resolve_id(id: str) -> Optional[Path]

1. Parse the ID to extract tier prefix: arc-, stage-, slice-, step-
2. Look up the full ID in index.json under the appropriate tier section
3. If found in index.json:
   a. Return the path from the entry's "path" field
   b. Cache the result for subsequent lookups
4. If NOT found in index.json:
   a. Check if the ID format matches a valid pattern (per DESC-SEMANTICS.md regex)
   b. If valid format but missing from index: return None (unresolved)
   c. If invalid format: return None (malformed ID)
5. Resolution is O(1) via dictionary lookup — no filesystem traversal needed

Content-hash pinning (at creation time):
- When artifact A cross-references artifact B, A records B's content hash at the time of reference
- The content hash is stored as part of the reference: {id: "slice-12", edge: "blocks", pinned_hash: "sha256:abc123..."}
- On consistency check (W0xx): compare current hash of B's file against pinned hash
- Hash mismatch: WARNING if B is mutable (DESIGN.md), INFO if B is immutable (stepNPLAN.md)
```

Source: Derived from Phase 400 D-09 (ID resolution via index.json), D-401-14 (tier-separated index.json structure), REF-01 requirement (content-hash pinning).

### index.json JSON Schema (DSK-05)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Artifact Index",
  "description": "Projector-rebuilt registry mapping every artifact ID to its path, type, tier, status, and last-updated timestamp. Tier-separated per D-401-14.",
  "type": "object",
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0",
      "description": "Schema version for forward compatibility"
    },
    "last_rebuilt": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of last projector rebuild"
    },
    "event_sequence": {
      "type": "integer",
      "description": "Sequence number of last processed event — enables incremental rebuild"
    },
    "arcs": {
      "type": "object",
      "description": "All Arc-level artifacts, keyed by aggregate ID",
      "additionalProperties": {
        "$ref": "#/$defs/IndexEntry"
      }
    },
    "stages": {
      "type": "object",
      "description": "All Stage-level artifacts, keyed by aggregate ID",
      "additionalProperties": {
        "$ref": "#/$defs/IndexEntry"
      }
    },
    "slices": {
      "type": "object",
      "description": "All Slice-level artifacts, keyed by aggregate ID",
      "additionalProperties": {
        "$ref": "#/$defs/IndexEntry"
      }
    },
    "steps": {
      "type": "object",
      "description": "All Step-level artifacts, keyed by aggregate ID (hierarchical)",
      "additionalProperties": {
        "$ref": "#/$defs/IndexEntry"
      }
    }
  },
  "required": ["version", "last_rebuilt", "event_sequence", "arcs", "stages", "slices", "steps"],
  "$defs": {
    "IndexEntry": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "description": "Artifact file type: ARC.md, STAGE.md, SLICE.md, stepNPLAN.md, CRIT.md, MAP.md, DESIGN.md, RESEARCH.md, VERIFICATION.md, SUMMARY.md, DECISIONS.md, STATE.md",
          "enum": ["ARC.md", "STAGE.md", "SLICE.md", "stepNPLAN.md", "CRIT.md", "MAP.md", "DESIGN.md", "RESEARCH.md", "VERIFICATION.md", "SUMMARY.md", "DECISIONS.md", "STATE.md"]
        },
        "path": {
          "type": "string",
          "description": "Relative path from .state/build/ root"
        },
        "tier": {
          "type": "string",
          "description": "Owning tier: arc, stage, slice, step",
          "enum": ["arc", "stage", "slice", "step"]
        },
        "status": {
          "type": "string",
          "description": "Current FSM state of the owning aggregate (matches status field in frontmatter)"
        },
        "schema_owner": {
          "type": "string",
          "description": "Who owns the schema: agent, projector, or hybrid (for MAP.md where agent writes content, projector updates checkboxes)",
          "enum": ["agent", "projector", "hybrid"]
        },
        "last_updated": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 timestamp of last update"
        },
        "content_hash": {
          "type": "string",
          "description": "SHA-256 hash of file content (for cross-ref hash pinning)"
        }
      },
      "required": ["type", "path", "tier", "status", "schema_owner", "last_updated"]
    }
  }
}
```

Source: Derived from D-401-14 (tier-separated structure), ART-01 (artifact types), Phase 400 FRONTMATTER-SCHEMAS.md (status values per tier).

### validate_consistency() Function Contract (REF-06)

```markdown
## Function: validate_consistency()

### Purpose
Walks all artifacts in `.state/build/`, verifies every cross-reference resolves to an existing ID,
detects filesystem-vs-event-store divergence, and reports all inconsistencies. Event store is
ALWAYS authoritative on mismatch (REF-06 requirement).

### Signature (design contract, not implementation)
```
validate_consistency() -> ConsistencyReport
```

### Inputs
- Event store (`.state/events.sqlite`) — authoritative source of truth
- index.json (`.state/build/index.json`) — projector-rebuilt artifact registry
- Filesystem (`.state/build/` directory tree) — actual artifact files on disk
- All artifact frontmatter files (ARC.md, STAGE.md, SLICE.md, stepNPLAN.md, etc.)
- All frontmatter `depends_on` fields — cross-reference source data
- Phase 400 FSM transition tables — for state validity checking

### Checks Performed (15 checks, W001–W015)
1. **W001** — Orphan ID: entry in index.json with no corresponding file on disk
2. **W002** — Stale index: file exists on disk but missing from index.json
3. **W003** — Mismatched status: STATUS in index.json ≠ STATUS in artifact frontmatter
4. **W004** — Unresolved cross-reference: depends_on[{id}] not found in index.json
5. **W005** — Cross-referenced to descoped: target ID is `abandoned` or `deferred`
6. **W006** — Missing parent pointer: child artifact lacks arc_id/stage_id/slice_id
7. **W007** — Parent-child ID mismatch: child's stage_id ≠ parent's actual ID
8. **W008** — Invalid state transition: current state + pending event → invalid per FSM tables
9. **W009** — Duplicate aggregate ID: two artifacts claim the same aggregate ID
10. **W010** — Invalid edge type: depends_on[{edge}] not in {blocks, soft, data}
11. **W011** — Cycle detected: DAG contains a cycle in dependency edges
12. **W012** — Cross-mode leakage: build-mode artifact references teach-mode artifact (or vice versa)
13. **W013** — Stale projection: STATE.md projection doesn't match event store computed state
14. **W014** — Invalid decimal ID: decimal insertion violates format rules (double decimal, empty trailing)
15. **W015** — Filesystem-vs-event-store divergence: event store says artifact exists but filesystem doesn't

### Output: ConsistencyReport
```
ConsistencyReport {
    daemon_startup_blocked: bool,          // true if any ERROR-severity code found
    errors: list[Finding],                  // ERROR-severity findings (blocks startup)
    warnings: list[Finding],                // WARNING-severity findings (advisory)
    infos: list[Finding],                   // INFO-severity findings (no action needed)
    total_artifacts_checked: int,
    total_cross_references_checked: int,
    event_store_sequence: int,              // last processed event sequence number
    duration_ms: int,
}

Finding {
    code: str,                              // "W001" through "W015"
    severity: Literal["ERROR", "WARNING", "INFO"],
    artifact_id: str,                       // aggregate ID of affected artifact
    path: str | None,                       // filesystem path of affected artifact
    message: str,                           // human-readable description
    detail: dict | None,                    // structured detail (e.g., target ID, expected vs actual)
}
```

### Execution Timing
- **Daemon startup:** Runs BEFORE HTTP server binds (D-401-17). If `daemon_startup_blocked == true`, daemon auto-launches resolution workflow.
- **Post-state-change:** Runs after every `state.*` event is processed by the projector (incremental check — only affected artifacts).
- **On-demand:** Via CLI command `state build health` (full check).

### Authority Rule (REF-06)
On any mismatch between filesystem state and event store state: **event store is authoritative.** The projector rebuilds all projections from the event stream. Filesystem state is a cache that can be regenerated.

### Auto-Resolution Path (D-401-17)
When ERROR-severity codes block daemon startup:
1. Daemon collects all ERROR findings into a resolution context
2. Daemon auto-launches a resolution session (opencode subagent) with the error context
3. Resolution session fixes consistency issues (e.g., removes orphan index entries, rebuilds index.json)
4. Resolution session restarts daemon after fixes
5. If resolution session fails, daemon reports the error and exits (not a deadlock — manual intervention path exists)

```

Source: Derived from D-401-16 (severity tiers), D-401-17 (blocking gate + auto-resolution), REF-05 (15 W-codes), REF-06 (event store authoritative on mismatch), GSD verify.cjs pattern (19 warning codes as design reference).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GSD `artifacts.cjs` (10 exact-match + 2 pattern-match) | Tier-separated index.json with O(1) ID→path lookup | Phase 401 design | More structured, supports ID-based cross-referencing |
| GSD `verify.cjs` (19 warning codes, flat) | W001–W015 with tiered severity (ERROR/WARNING/INFO) | Phase 401 design | Severity-based gating; ERROR codes block daemon startup |
| Phase→Stage terminology | Stage is canonical term; Phase only appears in migration notes | Phase 400 D-01 rename | All Phase 401 specs use "Stage" terminology |
| `discuss`/`execute` workflow phase names | `design`/`run` workflow phase names | Phase 400 D-03 rename | All Phase 401 specs use D-03 renamed terminology |
| Per-directory STATE.md files | Consolidated JSON under `.state/build/state/` + `export-state` CLI | Phase 401 D-401-07 | Reduces filesystem clutter; keeps source-controlled markdown clean |
| GSD STATE.md manually written by agents | Projector-rebuilt from event stream (agent NEVER writes STATE.md) | Phase 400 design | Eliminates drift between tracking files and actual state |

**Deprecated/outdated:**
- `state.phase.*` event type strings — replaced by `state.stage.*` (Phase 400 D-01). All Phase 401 specs use `state.stage.*`.
- `state.step.discussed` / `state.step.executed` — replaced by `state.step.designed` / `state.step.ran` (Phase 400 D-03).
- `state.arc.retired` — replaced by `state.arc.shipped` and `state.arc.abandoned` (Phase 400 EVENT-TAXONOMY.md).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 400 specification documents are internally consistent and up-to-date — no contradictions between TIER specs, FSM tables, and frontmatter schemas | Source Analysis | If contradictions exist, Phase 401 specs built on them will be inconsistent. Mitigation: cross-reference check between Phase 400 docs as part of Plan 1. |
| A2 | The 15 W-codes (W001–W015) catalogue suggested in Code Examples (W001–W015 allocations) is a reasonable starting design | Code Examples | If user wants different code assignments, the planner can reassign. Claude's discretion covers this (D-401-16). |
| A3 | The index.json JSON schema structure (tier-separated with IndexEntry objects) matches D-401-14 intent | Code Examples | D-401-14 specifies `{arcs: {}, stages: {}, slices: {}, steps: {}}` — the schema follows this. Risk is low. |
| A4 | `state-inputs/get-shit-done/bin/lib/artifacts.cjs` and `verify.cjs` exist and are accessible for reference during planning | Standard Stack | These files were not found at the specified paths (state-inputs is gitignored). However, their patterns are described in HANDOFF.md and CONTEXT.md. The planner can use these descriptions as reference. Risk: planner may not get full detail from the actual source files. |
| A5 | The snapshot-before-mutation protocol (D-401-13) integrates with the existing v4 Snapshot service (`src/state_core/snapshot.py`) | Immutability Rules | If the v4 Snapshot service API doesn't support the exact protocol needed, the Phase 401 spec may need adjustment. Mitigation: Phase 401 specifies the protocol contract; v41+ reconciles with existing API. |
| A6 | The `validate_consistency()` function spec does not need to handle teach-mode artifacts (`.state/teach/`) — only build-mode | Code Examples | D-401-17 says "daemon startup gate" which implies the full daemon. If teach-mode artifacts must also be validated at startup, additional codes are needed. Mitigation: Phase 401 specs document the current scope as build-mode only, with a note that teach-mode validation is v46+. |

## Open Questions (RESOLVED)

1. **Exact W001–W015 severity assignments**
   - What we know: D-401-16 defines three tiers (ERROR/WARNING/INFO). D-401-17 says ERROR blocks daemon startup. The 15 codes are under Claude's discretion.
   - What's unclear: Which specific codes should be ERROR vs WARNING vs INFO. The code examples suggest a starting assignment but user confirmation is needed.
   - Recommendation: Plan 3 provides a proposed severity assignment table; user reviews and adjusts during plan review.

2. **DEPRECATED, UNCHANGED, REMOVED, etc. in table of contents / DECISIONS.md discussion** — NOT APPLICABLE. This question was about discussion-phase mechanics, not Phase 401 design. All Phase 401 decisions are in CONTEXT.md.

3. **Template frontmatter field completeness**
   - What we know: Phase 400 FRONTMATTER-SCHEMAS.md defines pydantic models with field lists. Templates must match these models.
   - What's unclear: Whether optional fields (e.g., `depends_on: []`) should be present in templates with default values, or omitted entirely. Templates with defaults guide the agent; templates without them are cleaner.
   - Recommendation: Include all fields in templates (required + optional with defaults) to serve as a complete reference for agents. Document that optional fields can be removed if unused.

4. **Content-hash pinning mechanism detail**
   - What we know: REF-01 requires "content-hash pinning of cross-references at creation time." The cross-reference format should store the pinned hash.
   - What's unclear: Whether the hash covers the entire artifact file or just the frontmatter block. Whether hash mismatches are WARNING or INFO. Whether the hash is stored inline in the `depends_on` entry or in a separate field.
   - Recommendation: Plan 3 proposes: hash covers full file content (including body, not just frontmatter). Hash mismatch is WARNING for mutable artifacts (DESIGN.md), INFO for immutable artifacts. Hash stored inline in reference: `{id: "slice-12", edge: "blocks", hash: "sha256:abc..."}`.

5. **Interaction between immutability rules and STATE.md projection rebuilds**
   - What we know: D-401-12 locks stepNPLAN.md and CRIT.md when Slice enters `in_progress`. D-401-13 enforces via snapshot-before-mutation. The projector rebuilds STATE.md from events.
   - What's unclear: If a projector rebuild happens during a Slice's `in_progress` state, does the projector write to the locked STATE.md? If so, does the snapshot protocol intercept the projector's write too?
   - Recommendation: Clarify that immutability rules apply ONLY to agent-authored writes. Projector writes (STATUS updates) bypass the immutability lock. The snapshot-before-mutation protocol only triggers on agent-initiated frontmatter mutations.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified). Phase 401 is a design phase producing markdown specification documents. No external tools, services, or runtimes beyond what's already available (text editor, git) are needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | N/A — design-phase only (no code) |
| Config file | N/A |
| Quick run command | N/A — validation is via cross-reference consistency checks between spec documents |
| Full suite command | N/A |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ART-01 | Complete catalog documents every file type | Manual review | Cross-ref ARTIFACT-CATALOG.md against Phase 400 tier specs | ❌ Wave 0 |
| ART-02 | Templates exist for all 8+ artifact file types | Manual review | Validate each template's frontmatter against Phase 400 pydantic model | ❌ Wave 0 |
| ART-03 | Immutability rules specified per tier | Manual review | Check lock rules are documented per artifact type | ❌ Wave 0 |
| ART-04 | Projection vs authored classification complete | Manual review | Verify every agent-authored artifact is listed in D-401-09 | ❌ Wave 0 |
| ART-05 | Schema validation rules specified | Manual review | Verify rules cover creation, read, and cross-ref verification timing | ❌ Wave 0 |
| DSK-01 | Directory tree fully specified | Manual review | Verify every ART-01 path appears in tree; every tree entry has purpose annotation | ❌ Wave 0 |
| DSK-02 | Naming conventions specified | Manual review | Check ID format, directory naming, slug rules, display prefixes | ❌ Wave 0 |
| DSK-03 | STATE.md placement resolved | Manual review | Confirm consolidated JSON spec + export-state CLI contract | ❌ Wave 0 |
| DSK-04 | File count optimization specified | Manual review | Check per-Step strategy documented with scalability projection | ❌ Wave 0 |
| DSK-05 | index.json schema specified | Manual review | Validate JSON Schema against D-401-14 tier-separated structure | ❌ Wave 0 |
| DSK-06 | Concurrent access rules specified | Manual review | Check worktree creation rules, directory ownership, append-only write rules | ❌ Wave 0 |
| REF-01 | Cross-reference format specified | Manual review | Verify ID-based resolution algorithm, hash pinning mechanism | ❌ Wave 0 |
| REF-02 | Edge type semantics specified | Manual review | Confirm blocks/soft/data match Phase 400 D-12 and scheduler EdgeKind | ❌ Wave 0 |
| REF-03 | Cross-tier dependency policy specified | Manual review | Check same-tier/upward/downward/cross-mode rules documented | ❌ Wave 0 |
| REF-04 | Broken reference handling specified | Manual review | Verify cascade rules per edge type, W-code assignments, surface-to-agent behavior | ❌ Wave 0 |
| REF-05 | 15 W-codes specified | Manual review | Confirm all 15 codes documented with severity, trigger, resolution | ❌ Wave 0 |
| REF-06 | validate_consistency() spec provided | Manual review | Check signature, inputs, checks, output format, timing, authority rule | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** N/A — no automated tests (design phase)
- **Per wave merge:** Cross-reference consistency check between spec documents
- **Phase gate:** All 17 requirements reviewed against success criteria

### Wave 0 Gaps
- [ ] **Cross-reference validation script** — A lightweight script (or manual checklist) to verify that every path in ARTIFACT-CATALOG.md appears in DIRECTORY-TREE.md, every template field maps to a frontmatter schema field, and every W-code has a severity assignment. This is the design-phase equivalent of a test suite.
- [ ] **Consistency checklist** — A markdown checklist that the planner uses before marking each plan complete: "Does this spec contradict any Phase 400 spec? Does it use the same terminology? Does it define paths redundantly?"

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — Phase 401 is design documents, not runtime code |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — design documents; access control on `.state/build/` is v41+ concern |
| V5 Input Validation | Yes (design contract) | Pydantic `extra="forbid"` on all frontmatter schemas; ID regex validation; cross-reference ID verification against index.json |
| V6 Cryptography | No | N/A — content hashing (SHA-256) uses standard library, not custom crypto |

### Known Threat Patterns for Specification Documents

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Frontmatter field injection (extra fields in YAML) | Tampering | `extra="forbid"` on all pydantic models — rejects unknown fields at parse time (Phase 400 design, Phase 401 references) |
| Malformed aggregate ID (double decimal, leading zeros) | Tampering | Regex validation per DESC-SEMANTICS.md: `^slice-\d+(\.\d+)?$` — rejects invalid formats |
| Cross-mode reference leakage (build artifact refs teach artifact) | Information Disclosure | REF-03 cross-mode blocking; W012 detection code (proposed) |
| Agent writes to projector-owned fields (status, completed_at) | Elevation of Privilege | Field ownership classification (Phase 400 TIER-07); projector-rebuild overwrites agent-written projector fields; schema validation rejects agent writes to projector fields |
| Broken reference exploit (injecting references to non-existent artifacts) | Spoofing | REF-01 ID resolution via index.json; REF-04 surface-and-block; W004 unresolved cross-reference detection |
| Immutability bypass (agent mutating locked artifact) | Tampering | D-401-13 snapshot-before-mutation protocol; attempted mutation rejected, not warned |
| Stale index entries (artifact deleted but index not updated) | Denial of Service | projector rebuilds index.json on every state change; W002 stale index detection |

## Sources

### Primary (HIGH confidence)
- Phase 400 specification documents (9 files under `.planning/milestones/v40/phases/400/specs/`):
  - `TIER-ARC.md` — Arc tier definition, owned artifacts, frontmatter fields, directory path
  - `TIER-STAGE.md` — Stage tier definition, owned artifacts, frontmatter fields, directory path
  - `TIER-SLICE.md` — Slice tier definition, owned artifacts, frontmatter fields, directory path
  - `TIER-STEP.md` — Step tier definition, owned artifacts, frontmatter fields, file path
  - `FSM-TABLES.md` — All state transitions with guard conditions and event triggers
  - `EVENT-TAXONOMY.md` — Complete event taxonomy (36 events across 4 tiers)
  - `COMPOSITE-CASCADE.md` — Step→Slice→Stage→Arc composite event cascade
  - `FRONTMATTER-SCHEMAS.md` — Pydantic frontmatter models for all 4 tiers
  - `DESC-SEMANTICS.md` — Descope, abandon, blocked, and decimal insertion semantics
- Phase 401 CONTEXT.md — 17 locked decisions (D-401-01 through D-401-17)
- Phase 400 CONTEXT.md — 19 locked decisions (D-01 through D-19) carried forward
- `REQUIREMENTS.md` — 17 requirements (ART-01..05, DSK-01..06, REF-01..06)
- `ROADMAP.md` — Success criteria SC1–SC5 for Phase 401
- Existing codebase (read directly):
  - `src/state_core/projector.py` (663 lines) — CQRS handler registration pattern, `@_register_handler` decorator
  - `src/state_core/schema.py` (936 lines) — 34+ event types, BUILD_ONLY_EVENT_PREFIXES, aggregate definitions
  - `src/state_core/scheduler.py` (828 lines) — `EdgeKind = Literal["blocks", "soft", "data"]`, DAG node types, `_parse_sort_key`

### Secondary (MEDIUM confidence)
- GSD reference patterns (described in HANDOFF.md, CONTEXT.md — source files not accessible):
  - `state-inputs/get-shit-done/bin/lib/artifacts.cjs` — 10 exact-match + 2 pattern-match artifact registry
  - `state-inputs/get-shit-done/bin/lib/verify.cjs` — 19 warning codes, schema drift detection
- `.planning/research/ARCHITECTURE.md` — CQRS aggregate design, directory layout proposal, health check pseudocode

### Tertiary (LOW confidence)
- None — all claims are either verified against Phase 400 specs or explicitly marked as [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all patterns are defined in Phase 400 specs; Phase 401 is synthesis, not discovering new libraries
- Architecture: HIGH — the three-plan structure mirrors Phase 400's proven approach; 17 requirements map cleanly to 3 plans
- Pitfalls: MEDIUM — pitfalls are inferred from common design-spec failures and the tension between "design contract" and "implementation detail"; actual pitfalls may surface during planning
- Research date: 2026-05-07
- Valid until: 2026-06-07 (30-day stability — Phase 400 specs are stable, Phase 401 builds on them)

**Research date:** 2026-05-07
**Valid until:** 2026-06-07
