# Phase 401: Artifact Catalog, Naming, Layout, Cross-Refs — Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 14 potential spec outputs → 5–6 consolidated (planner decides)
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `specs/ARTIFACT-CATALOG.md` | specification | design-contract | Phase 400 `specs/TIER-ARC.md` | exact (same tier-artifact catalog format) |
| `specs/TEMPLATES.md` | specification | design-contract | Phase 400 `specs/FRONTMATTER-SCHEMAS.md` | exact (field schemas → template schemas) |
| `specs/IMMUTABILITY-RULES.md` | specification | design-contract | Phase 400 `specs/DESC-SEMANTICS.md` | exact (rule-based specification format) |
| `specs/PROJECTION-CLASSIFICATION.md` | specification | design-contract | Phase 400 `specs/FRONTMATTER-SCHEMAS.md` §Field Ownership | exact (field ownership table pattern) |
| `specs/SCHEMA-VALIDATION.md` | specification | design-contract | Phase 400 `specs/FSM-TABLES.md` | exact (guard condition / validation specification) |
| `specs/DIRECTORY-TREE.md` | specification | design-contract | Phase 400 `specs/TIER-ARC.md` §Directory path | exact (path definition pattern) |
| `specs/STATE-PLACEMENT.md` | specification | design-contract | Phase 400 `specs/TIER-ARC.md` §Owned Artifacts | exact (artifact placement specification) |
| `specs/FILE-COUNT-STRATEGY.md` | specification | design-contract | Phase 400 `specs/FSM-TABLES.md` §Tier Count Rules | exact (count/scale specification) |
| `specs/INDEX-SCHEMA.md` | specification | design-contract | Phase 400 `specs/FRONTMATTER-SCHEMAS.md` | exact (pydantic model → JSON schema) |
| `specs/CONCURRENT-ACCESS.md` | specification | design-contract | Phase 400 `specs/DESC-SEMANTICS.md` §Blocked State | exact (concurrency rules specification) |
| `specs/CROSS-REFERENCES.md` | specification | design-contract | Phase 400 `specs/FRONTMATTER-SCHEMAS.md` §Cross-Tier ID Encoding | exact (ID format specification) |
| `specs/BROKEN-REFERENCES.md` | specification | design-contract | Phase 400 `specs/DESC-SEMANTICS.md` §Abandon Cascade | exact (cascade rules specification) |
| `specs/CONSISTENCY-CODES.md` | specification | design-contract | Phase 400 `specs/EVENT-TAXONOMY.md` | exact (structured catalog format) |
| `specs/VALIDATE-FUNCTION.md` | specification | design-contract | Phase 400 `specs/COMPOSITE-CASCADE.md` | exact (function spec + pseudocode) |

**Consolidation note:** RESEARCH.md recommends consolidating into 5–6 documents. Plausible groupings:
- Plan 1 (ART): ARTIFACT-CATALOG.md + TEMPLATES.md + IMMUTABILITY-RULES.md → `ARTIFACT-CATALOG.md` (single comprehensive catalog)
- Plan 1 (ART): PROJECTION-CLASSIFICATION.md + SCHEMA-VALIDATION.md → `SCHEMA-OWNERSHIP.md` (combined ownership + validation)
- Plan 2 (DSK): DIRECTORY-TREE.md + STATE-PLACEMENT.md + FILE-COUNT-STRATEGY.md + CONCURRENT-ACCESS.md → `DIRECTORY-TREE.md` (comprehensive filesystem blueprint)
- Plan 2 (DSK): INDEX-SCHEMA.md → standalone (machine-readable schema, consumed independently)
- Plan 3 (REF): CROSS-REFERENCES.md + BROKEN-REFERENCES.md → `CROSS-REFERENCES.md` (format + edge semantics + broken handling)
- Plan 3 (REF): CONSISTENCY-CODES.md + VALIDATE-FUNCTION.md → `CONSISTENCY-CODES.md` (codes + function spec together)

---

## Pattern Assignments

### `specs/ARTIFACT-CATALOG.md` (specification, design-contract)

**Analog:** Phase 400 `specs/TIER-ARC.md`

**Document structure pattern** (lines 1–124):
```markdown
# Tier Specification: Arc

## Role in Hierarchy

[2-5 paragraph prose describing the tier's purpose, constraints, and key
behaviors. Uses concrete examples and references locked decisions by ID.]

## State Machine

[ASCII art state diagram with transitions labeled by event types.
Guard conditions noted inline. Exit states clearly separated.]

## State Transition Table

| From | To | Event Trigger | Guard Condition |
|------|----|---------------|-----------------|
| `planned` | `in_progress` | `state.arc.started` | ≥1 child Stage is `planned` |

## Owned Artifacts

| Artifact | Purpose | Schema Owner |
|----------|---------|--------------|
| CRIT.md | Must-have criteria | Agent |
| MAP.md | Arc-level roadmap | Agent |

## Frontmatter Fields

| Field | Type | Owner | Required | Description |
|-------|------|-------|----------|-------------|
| `id` | `str` | Agent | Yes | Arc identifier: `arc-{n}` |

## Events

| Event Type | Trigger | State Transition | Description |
|-----------|---------|------------------|-------------|
| `state.arc.created` | `/state-new arc` | none → `planned` | Arc aggregate created |

## Cross-Tier Relationships

- **Parent of:** [child tier]
- **Sibling of:** [sibling tier + constraints]
- **Child of:** [parent tier or "None - root tier"]
- **ID format:** `arc-{n}` (D-01)
- **Directory path:** `.state/build/arcs/arc-{n}/`
```

**Core catalog entry pattern** (from RESEARCH.md §Pattern 1 — this is the proposed format for ARTIFACT-CATALOG.md):
```markdown
### ARC.md

| Property | Value |
|----------|-------|
| **Purpose** | Arc definition document — defines the feature block scope |
| **Owning Tier** | Arc |
| **Schema Owner** | Agent (id, title, goal) / Projector (status, stage_count) |
| **Created By** | `/state-new arc` command |
| **Creation Trigger** | User creates a new Arc |
| **Updated By** | Agent (edits frontmatter) / Projector (status updates) |
| **Update Triggers** | state.arc.started, state.arc.stages_shipped, state.arc.shipped |
| **File Format** | Markdown with YAML frontmatter |
| **Frontmatter Model** | `ArcFrontmatter` (FRONTMATTER-SCHEMAS.md) |
| **Immutability** | `depends_on` and `success_criteria` lock when Arc enters `in_progress` |
| **Cross-Refs From** | None (Arc is root tier) |
| **Cross-Refs To** | Child Stages via MAP.md; sibling Arcs via `depends_on` |
| **File Path** | `.state/build/arcs/arc-{n}/ARC.md` |
```

**Design conventions header** (from Phase 400 FRONTMATTER-SCHEMAS.md lines 6–14):
```markdown
## Design Conventions

- All models use `ConfigDict(extra="forbid")` — NOT `frozen=True`.
- Field ownership is classified as **AGENT** or **PROJECTOR** — never mixed within a field.
- Status fields use pydantic `Literal` types for state-machine enforcement.
- ID fields follow D-01 dash-prefix format. No leading zeros.
- All models use Python 3.12+ syntax.
- These are design contracts for v41+ runtime; code implementation is out of scope for v40.
```

---

### `specs/TEMPLATES.md` (specification, design-contract)

**Analog:** Phase 400 `specs/FRONTMATTER-SCHEMAS.md`

**Frontmatter schema documentation pattern** (lines 16–53, ArcFrontmatter):
```markdown
## Arc Frontmatter (ARC.md)

[Purpose paragraph explaining what this document represents and how it's
created/updated. Migration notes if applicable.]

\`\`\`python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class ArcFrontmatter(BaseModel):
    """Design contract for ARC.md frontmatter — v41+ runtime validation."""
    model_config = ConfigDict(extra="forbid")

    # ── Agent-owned fields ──
    id: str                              # "arc-{n}" per D-01
    title: str                           # Human-readable name
    goal: str                            # One-line outcome
    success_criteria: list[str]           # Measurable outcomes
    depends_on: list[dict[str, str]] = []  # [{id: "arc-02", edge: "blocks"}]

    # ── Projector-owned fields (written by daemon projector, NEVER by agent) ──
    status: Literal["planned", "in_progress", "auditing", "shipped", "abandoned"] = "planned"
    stage_count: int = 0
    shipped_stage_count: int = 0
    completed_at: str | None = None
\`\`\`

**Field count:** 5 agent-owned, 4 projector-owned = 9 total fields.
```

**Template structure pattern** (from CONTEXT.md D-401-03 CRIT.md definition + RESEARCH.md directory tree):
```markdown
### ARC.md.tmpl

**Template path:** `.state/build/templates/ARC.md.tmpl`

\`\`\`yaml
---
id: arc-{n}
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
\`\`\`

[Body section with stubs and inline guidance comments for the agent.]

**Validation:** Every frontmatter field in this template maps to a field in
`ArcFrontmatter` (Phase 400 FRONTMATTER-SCHEMAS.md). Required fields are
present; optional fields have defaults. No fields exist in the template
that are absent from the pydantic model (`extra="forbid"` enforces this).
```

**Cross-reference validation table pattern** (from RESEARCH.md pitfall #2):
```markdown
### Template ↔ Schema Cross-Reference

| Template Field | ArcFrontmatter | StageFrontmatter | SliceFrontmatter | StepFrontmatter |
|----------------|---------------|-----------------|-----------------|-----------------|
| `id` | ✓ | ✓ | ✓ | — |
| `step_number` | — | — | — | ✓ |
| `title` | ✓ | ✓ | ✓ | ✓ |
| `goal` | ✓ | ✓ | ✓ | ✓ |
| `success_criteria` | ✓ | ✓ | ✓ | — |
| `verification_criteria` | — | — | — | ✓ |
| `depends_on` | ✓ | ✓ | ✓ | — |
| `status` | ✓ | ✓ | ✓ | ✓ |
| `stage_count` | ✓ | — | — | — |
| ... | ... | ... | ... | ... |
```

---

### `specs/DIRECTORY-TREE.md` (specification, design-contract)

**Analog:** Phase 400 `specs/TIER-ARC.md` §Directory path (line 124) + RESEARCH.md §Pattern 2

**Directory tree blueprint pattern** (from RESEARCH.md lines 290–330):
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
│       ├── CRIT.md               # [AGENT] Must-have criteria
│       ├── MAP.md                # [AGENT+PROJECTOR] Plan + tracker
│       ├── DECISIONS.md          # [AGENT] Gray-area decision log (append-only)
│       ├── stages/
│       │   └── stage-{n}/
│       │       ├── STAGE.md      # [AGENT] Stage definition
│       │       ├── CRIT.md
│       │       ├── MAP.md
│       │       ├── DECISIONS.md
│       │       └── slices/
│       │           └── slice-{n}/
│       │               ├── SLICE.md
│       │               ├── DESIGN.md
│       │               ├── RESEARCH.md
│       │               ├── step1PLAN.md
│       │               ├── stepNPLAN.md
│       │               ├── VERIFICATION.md
│       │               ├── SUMMARY.md
│       │               └── {worktree}/
└── templates/                    # [STATIC] Artifact templates
    ├── ARC.md.tmpl
    ├── STAGE.md.tmpl
    └── ...
```

**Annotation convention:** Every node uses `[OWNER]` tag — `[AGENT]`, `[PROJECTOR]`, `[AGENT+PROJECTOR]`, `[STATIC]`. Directories show ID format (`arc-{n}`). Files show creation trigger where non-obvious.

**Path consistency rule** (from RESEARCH.md pitfall #1):
- Define paths ONCE in the artifact catalog (ARTIFACT-CATALOG.md), then DIRECTORY-TREE REFERENCES them
- Or define the canonical tree first (this doc), then ARTIFACT-CATALOG.md cites it
- Use the same variable notation everywhere: `arc-{n}` not `{arc-id}` or `arc_id`
- Every tree entry must have a corresponding entry in ARTIFACT-CATALOG.md (cross-reference check)

---

### `specs/INDEX-SCHEMA.md` (specification, design-contract)

**Analog:** Phase 400 `specs/FRONTMATTER-SCHEMAS.md` (pydantic model → JSON Schema)

**JSON schema pattern** (from RESEARCH.md lines 457–548):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Artifact Index",
  "description": "Projector-rebuilt registry mapping every artifact ID to its path...",
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
      "description": "Sequence number of last processed event"
    },
    "arcs": {
      "type": "object",
      "additionalProperties": { "$ref": "#/$defs/IndexEntry" }
    },
    "stages": { "type": "object", "additionalProperties": { "$ref": "#/$defs/IndexEntry" } },
    "slices": { "type": "object", "additionalProperties": { "$ref": "#/$defs/IndexEntry" } },
    "steps": { "type": "object", "additionalProperties": { "$ref": "#/$defs/IndexEntry" } }
  },
  "required": ["version", "last_rebuilt", "event_sequence", "arcs", "stages", "slices", "steps"],
  "$defs": {
    "IndexEntry": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["ARC.md", "STAGE.md", "SLICE.md", "stepNPLAN.md", "CRIT.md", "MAP.md",
                   "DESIGN.md", "RESEARCH.md", "VERIFICATION.md", "SUMMARY.md", "DECISIONS.md", "STATE.md"]
        },
        "path": { "type": "string", "description": "Relative path from .state/build/ root" },
        "tier": { "type": "string", "enum": ["arc", "stage", "slice", "step"] },
        "status": { "type": "string", "description": "Current FSM state" },
        "schema_owner": { "type": "string", "enum": ["agent", "projector", "hybrid"] },
        "last_updated": { "type": "string", "format": "date-time" },
        "content_hash": { "type": "string", "description": "SHA-256 hash for cross-ref pinning" }
      },
      "required": ["type", "path", "tier", "status", "schema_owner", "last_updated"]
    }
  }
}
```

**Schema design conventions header** (from Phase 400 FRONTMATTER-SCHEMAS.md lines 6–14):

Include the standard design conventions block explaining: tier-separated per D-401-14, O(1) ID→path lookup, projector rebuilds on every state change, `content_hash` enables cross-ref hash pinning.

---

### `specs/CROSS-REFERENCES.md` (specification, design-contract)

**Analog:** Phase 400 `specs/FRONTMATTER-SCHEMAS.md` §Cross-Tier ID Encoding (lines 239–269) + Phase 400 `specs/DESC-SEMANTICS.md` §Abandon Cascade

**ID format specification pattern** (from FRONTMATTER-SCHEMAS.md lines 240–269):
```markdown
## Cross-Tier ID Encoding

Aggregate IDs use hierarchical slash-delimited encoding that enables parent
extraction at parse time.

\`\`\`
Arc:    "arc-{n}"                                    Example: "arc-45"
Stage:  "arc-{n}/stage-{n}"                           Example: "arc-45/stage-22"
Slice:  "arc-{n}/stage-{n}/slice-{n}"                 Example: "arc-45/stage-22/slice-12"
Step:   "arc-{n}/stage-{n}/slice-{n}/step-{n}"        Example: "arc-45/stage-22/slice-12/step-5"
\`\`\`

**Encoding rules:**
- Every aggregate ID encodes its full lineage
- The `arc_id`, `stage_id`, and `slice_id` frontmatter fields store the SHORT form
- The hierarchical form is used internally for event store keying
```

**Edge type specification pattern** (from Phase 400 FSM-TABLES.md lines 163–166):
```markdown
### D-12 Edge Types

| Edge | Semantics | Scheduler Behavior | Artifact Behavior |
|------|-----------|-------------------|-------------------|
| `blocks` | Hard prerequisite | Dependent cannot start until blocker is `shipped` | N/A |
| `soft` | Advisory ordering | Scheduler prioritizes ordering but may override | N/A |
| `data` | Artifact-producing | Hard prerequisite + artifact copy | Artifact directory copied from source to dependent |
```

**Cross-reference format specification** (from RESEARCH.md lines 432–451):
```
## Cross-Reference Resolution Algorithm

Algorithm: resolve_id(id: str) -> Optional[Path]

1. Parse the ID to extract tier prefix: arc-, stage-, slice-, step-
2. Look up the full ID in index.json under the appropriate tier section
3. If found: Return the path from the entry's "path" field. Cache result.
4. If NOT found:
   a. Check if the ID format matches a valid pattern
   b. If valid but missing: return None (unresolved → W004)
   c. If invalid format: return None (malformed → W004)
5. Resolution is O(1) via dictionary lookup — no filesystem traversal

Content-hash pinning (at creation time):
- When artifact A cross-references artifact B, A records B's content hash
- Format: {id: "slice-12", edge: "blocks", pinned_hash: "sha256:abc123..."}
- On consistency check (W-WXX): compare current hash vs pinned hash
- Hash mismatch: WARNING if mutable, INFO if immutable
```

**Dependency policy table pattern** (from Phase 400 D-10 + DESC-SEMANTICS.md):
```markdown
### Cross-Tier Dependency Policy

| Direction | Allowed? | Constraint | Rationale |
|-----------|----------|------------|-----------|
| Same-tier (sibling) | Yes | D-10 same-parent: sibling within same parent only | Bounded dependency graph per parent container |
| Upward (child→parent) | Yes | Implicit via aggregate ID hierarchy | Every child knows its parent via arc_id/stage_id/slice_id |
| Downward (parent→child) | No | Forbidden | Parent should not depend on children; violates scoping hierarchy |
| Cross-mode (build↔teach) | No | Blocked | Mode isolation (v6); W012 detects leakage |
```

---

### `specs/CONSISTENCY-CODES.md` (specification, design-contract)

**Analog:** Phase 400 `specs/EVENT-TAXONOMY.md` (structured catalog with consistent entry format)

**W-code entry format** (from RESEARCH.md lines 337–351):
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
| **Resolution** | Manual: remove orphan entry. Auto-resolution: projector removes orphan entries on daemon restart. |
| **Blocking** | BLOCKS daemon startup (ERROR severity per D-401-17) |
| **Affected Tiers** | All (any tier's artifact can become orphaned) |
```

**Full W-code catalog header pattern** (from Phase 400 EVENT-TAXONOMY.md lines 1–14):
```markdown
# Consistency Validation Codes — W001–W015

> **Design contract for v41+ runtime consistency validation.**
> Consumed by: v41+ daemon startup gate (`validate_consistency()`), projector health
> module, CLI `state build health` command.

## Design Conventions

- All codes use tiered severity: ERROR (blocks daemon startup), WARNING (advisory
  at plan time), INFO (informational, no action required) — per D-401-16.
- Codes are stable identifiers — W001 will always mean "Orphan ID in index.json".
  New codes get new numbers; no renumbering.
- Every code has: Code, Name, Category, Severity, Trigger, Detection Logic,
  Resolution, Blocking behavior, Affected Tiers.
- Severity assignment follows the RESEARCH.md pitfall #3 rule: only issues that
  make the event stream irreconcilable with the filesystem (data loss risk)
  are ERROR. Degraded information is WARNING. Display-only issues are INFO.
```

**Code-to-requirement cross-reference** (from Phase 400 EVENT-TAXONOMY.md lines 184–192):
```markdown
## W-Code Summary

| Code | Name | Category | Severity | Blocks Startup |
|------|------|----------|----------|---------------|
| W001 | Orphan ID | Cross-Ref Integrity | ERROR | Yes |
| W002 | Stale index | Projection Health | WARNING | No |
| ... | ... | ... | ... | ... |

**Total:** 15 codes (N ERROR, M WARNING, K INFO)
```

---

### `specs/VALIDATE-FUNCTION.md` (specification, design-contract)

**Analog:** Phase 400 `specs/COMPOSITE-CASCADE.md` (projector pseudocode + function specs)

**Function specification structure** (from RESEARCH.md lines 555–634):
```markdown
## Function: validate_consistency()

### Purpose
Walks all artifacts in `.state/build/`, verifies every cross-reference resolves
to an existing ID, detects filesystem-vs-event-store divergence, and reports all
inconsistencies. Event store is ALWAYS authoritative on mismatch.

### Signature (design contract, not implementation)
\`\`\`
validate_consistency() -> ConsistencyReport
\`\`\`

### Inputs
- Event store (`.state/events.sqlite`) — authoritative source of truth
- index.json (`.state/build/index.json`) — projector-rebuilt artifact registry
- Filesystem (`.state/build/` directory tree) — actual artifact files on disk
- All artifact frontmatter files
- All frontmatter `depends_on` fields — cross-reference source data
- Phase 400 FSM transition tables — for state validity checking

### Checks Performed (15 checks, W001–W015)
1. **W001** — Orphan ID: entry in index.json with no corresponding file on disk
2. **W002** — Stale index: file exists on disk but missing from index.json
...
15. **W015** — Filesystem-vs-event-store divergence

### Output: ConsistencyReport
\`\`\`
ConsistencyReport {
    daemon_startup_blocked: bool,
    errors: list[Finding],
    warnings: list[Finding],
    infos: list[Finding],
    total_artifacts_checked: int,
    total_cross_references_checked: int,
    event_store_sequence: int,
    duration_ms: int,
}

Finding {
    code: str,           # "W001" through "W015"
    severity: Literal["ERROR", "WARNING", "INFO"],
    artifact_id: str,
    path: str | None,
    message: str,
    detail: dict | None,
}
\`\`\`

### Execution Timing
- **Daemon startup:** Runs BEFORE HTTP server binds (D-401-17)
- **Post-state-change:** Runs after every `state.*` event (incremental — only affected artifacts)
- **On-demand:** Via CLI command `state build health` (full check)

### Authority Rule
On any mismatch between filesystem state and event store state: **event store is authoritative.**
The projector rebuilds all projections from the event stream.

### Auto-Resolution Path (D-401-17)
When ERROR-severity codes block daemon startup:
1. Daemon collects all ERROR findings into a resolution context
2. Daemon auto-launches a resolution session (opencode subagent)
3. Resolution session fixes consistency issues
4. Resolution session restarts daemon after fixes
5. If resolution session fails, daemon reports error and exits
```

**Anti-pattern avoidance** (from RESEARCH.md pitfalls #4 and #5):
- Do NOT include Python pseudocode with variable assignments and loops
- Do NOT reference specific Python modules (`os.path`, `json.load`)
- Do NOT include database query syntax
- Describe WHAT (inputs, checks, output format, timing) — not HOW (implementation)

---

## Shared Patterns

### Spec Document Common Structure

**Source:** Phase 400 `specs/TIER-ARC.md`, `specs/FRONTMATTER-SCHEMAS.md`, `specs/EVENT-TAXONOMY.md`
**Apply to:** All Phase 401 specification documents

All Phase 401 spec documents share this common structure:

```markdown
# [Document Title]

> **Design contract for v41+ runtime [what it enables].**
> Consumed by: [list of downstream consumers — Phase 401 plans, v41+ code modules,
> v42 quality pipeline, specific CLI commands].

## Overview / Design Conventions

[1-3 paragraphs establishing scope, key constraints, and design conventions.
References Phase 400 locked decisions by ID (e.g., "per D-401-14").]

## [Section 1: Primary Content]

[Structured content using consistent table or list formats.]

## [Section 2: Secondary Content]

[...]

## Cross-References to Phase 400

[Explicit references to Phase 400 specs where this document depends on them:
- TIER-ARC.md: [what this uses from it]
- FSM-TABLES.md: [what this uses from it]
- FRONTMATTER-SCHEMAS.md: [what this uses from it]
- EVENT-TAXONOMY.md: [what this uses from it]
- DESC-SEMANTICS.md: [what this uses from it]
- COMPOSITE-CASCADE.md: [what this uses from it]]

## Threat Model Alignment

[Table mapping specific threats/mitigations from the security domain, referencing
ASVS categories and STRIDE where applicable.]

---

*Design contract for v41+ runtime [what it enables]. All [content type] validated
against [which Phase 400 specs this cross-references]. Consumed by [downstream consumers].*
```

### Reference To Phase 400 Pattern (not reproduction)

**Source:** Phase 400 `specs/TIER-ARC.md` lines 112–114 (migration notes)
**Apply to:** All Phase 401 specification documents

```markdown
**Migration note:** The existing codebase (`src/state_core/schema.py`) defines
`state.arc.created`, `state.arc.retired`, and `state.arc.updated`. In the v40 design:
- `state.arc.retired` is replaced by `state.arc.shipped` and `state.arc.abandoned`
```

Phase 401 documents should similarly reference (not reproduce) Phase 400 material:
- Use `per D-{N}` and `per D-401-{N}` to cite locked decisions
- Use `see TIER-ARC.md §State Machine` for state machine details
- Use `see FRONTMATTER-SCHEMAS.md §ArcFrontmatter` for field definitions
- Use `see FSM-TABLES.md §Arc State Transition Table` for transition guards

**Anti-pattern:** Reproducing Phase 400 state machines, event lists, or field tables
in Phase 401 documents. Always reference — never duplicate.

### Field Ownership Classification Table

**Source:** Phase 400 `specs/FRONTMATTER-SCHEMAS.md` lines 200–235
**Apply to:** ARTIFACT-CATALOG.md, TEMPLATES.md, PROJECTION-CLASSIFICATION.md

```markdown
| Field | Arc | Stage | Slice | Step | Owner | Notes |
|-------|-----|-------|-------|------|-------|-------|
| `id` | ✓ | ✓ | ✓ | — | Agent | D-01 dash-prefix format |
| `title` | ✓ | ✓ | ✓ | ✓ | Agent | Human-readable name |
| ... | ... | ... | ... | ... | ... | ... |

**Field count by owner:**
- **Agent-owned:** N distinct fields across all tiers
- **Projector-owned:** M distinct fields across all tiers
- **Total:** N+M fields classified, each owned by exactly one role
```

### Immutability Rules Table Pattern

**Source:** Phase 400 `specs/DESC-SEMANTICS.md` §Blocked State Mechanics (lines 144–211)
**Apply to:** IMMUTABILITY-RULES.md (part of ART-03)

```markdown
### [Artifact Name]: [ArtifactPath]

| Property | Value |
|----------|-------|
| **Artifact** | [file name] |
| **Owning Tier** | [tier] |
| **Lock Trigger** | [when the artifact becomes immutable — e.g., "Slice enters `in_progress`"] |
| **Locked Fields** | [which frontmatter fields are frozen] |
| **Mutable Fields** | [which fields remain editable] |
| **Enforcement** | Snapshot-before-mutation at daemon level (D-401-13). Attempted write to locked field → rejected (not warned). |
| **Unlock** | [when/if the artifact becomes mutable again, or "never — permanent lock"] |
| **Projector Bypass** | Projector writes (STATUS updates) bypass the immutability lock. Immutability applies ONLY to agent-initiated mutations (D-401-12 clarification from RESEARCH.md open question #5). |
```

### Depends-On Edge Format

**Source:** Phase 400 D-12 (locked decision) + Phase 400 `specs/FSM-TABLES.md` lines 164–166
**Applies to:** CROSS-REFERENCES.md, CONSISTENCY-CODES.md

```yaml
depends_on:
  - {id: "slice-10", edge: "blocks"}
  - {id: "slice-11", edge: "soft"}
  - {id: "slice-09", edge: "data"}
```

- Edge types: `blocks`, `soft`, `data` — these are the ONLY valid values (W010 detects invalid)
- Must match `EdgeKind = Literal["blocks", "soft", "data"]` from `src/state_core/scheduler.py` line 15
- Same-parent-only constraint (D-10): target must be a sibling within the same parent container

### Code Integration: Projector Handler Registration

**Source:** `src/state_core/projector.py` lines 38–45
**Apply to:** INDEX-SCHEMA.md (index.json projector handler specification), STATE-PLACEMENT.md

```python
# Pattern for new projector handlers that v41+ will implement:
# Phase 401 specifies WHAT handlers — v41+ implements HOW.

@_register_handler("state.arc.started")
def _handle_arc_started(current, data) -> dict:
    """Update Arc index.json entry and MAP.md checkboxes on arc start."""
    pass  # v41+ implementation — Phase 401 specifies the WHAT (trigger, update scope)

# index.json handler: runs on EVERY state change event
@_register_handler("*")  # conceptual — v41+ decides actual registration
def _handle_index_update(current, data) -> dict:
    """Rebuild index.json entry for the affected artifact."""
    pass  # v41+ implementation — see INDEX-SCHEMA.md §Rebuild Rules
```

### Code Integration: Scheduler EdgeKind

**Source:** `src/state_core/scheduler.py` line 15
**Apply to:** CROSS-REFERENCES.md (REF-02 edge type specifications)

```python
EdgeKind = Literal["blocks", "soft", "data"]
"""
- blocks: hard prerequisite — target cannot start until source completes.
- soft: advisory — scheduler may override.
- data: data-flow dependency — target needs source's output artifacts.
"""
```

Phase 401 cross-reference edge types MUST match this existing enum exactly.
No new edge types are introduced in v40 — the scheduler's EdgeKind is the
canonical source for valid edge values. W010 checks `depends_on[{edge}]`
against this literal set.

### Code Integration: Mode Isolation

**Source:** `src/state_core/schema.py` lines 19–48
**Apply to:** CROSS-REFERENCES.md (REF-03 cross-mode blocking), CONSISTENCY-CODES.md (W012)

```python
BUILD_ONLY_EVENT_PREFIXES: frozenset[str] = frozenset(
    {"state.arc.", "state.phase.", "state.slice.", "state.step."}
)
"""Event-type prefixes restricted to build mode."""

TEACH_ONLY_EVENT_PREFIXES: frozenset[str] = frozenset(
    {"state.concept.", "state.drill."}
)
"""Event-type prefixes restricted to teach mode."""

RUNTIME_MODES: frozenset[str] = frozenset({"build", "teach", "kernel"})
BUILD_SUBTREE: str = ".state/build"
TEACH_SUBTREE: str = ".state/teach"
```

W012 cross-mode leakage detection must check: artifact in `.state/build/` subtree
must only reference targets in `.state/build/` subtree (and vice versa for teach).
The authoritative mode prefixes (`BUILD_ONLY_EVENT_PREFIXES`, `TEACH_ONLY_EVENT_PREFIXES`)
are used to classify artifacts by mode.

---

## No Analog Found

All files have strong analogs from Phase 400 specifications. No unmatched files.

The Phase 401 planner should note that these specs are a DIFFERENT *kind* of document
than Phase 400 specs — Phase 400 defines tier definitions and state machines (WHAT
each tier IS), while Phase 401 defines the filesystem blueprint and cross-referencing
system (HOW the tiers MANIFEST on disk and reference each other). The structural
patterns (design conventions header, table formats, cross-reference sections) are
identical — the CONTENT domain is different.

## Metadata

**Analog search scope:**
- `.planning/milestones/v40/phases/400/specs/` (9 Phase 400 specification documents)
- `src/state_core/` (projector.py, scheduler.py, schema.py — code integration points)

**Files scanned:** 14 potential spec outputs + 9 Phase 400 specs + 3 code files = 26

**Pattern extraction date:** 2026-05-07

**Key patterns identified:**
1. Spec document header: `> **Design contract for v41+ runtime [purpose].**` + `Consumed by: [...]`
2. Structured property tables for catalog entries, W-codes, immutability rules
3. ASCII tree format with `[OWNER]` annotations for directory layout
4. JSON Schema + pydantic model pairs for machine-readable contracts
5. Function specification with signature, inputs, checks, output, timing (no implementation)
6. Phase 400 cross-reference pattern: cite by D-{N} ID or `spec/FILE.md §Section` — never reproduce
7. Projector handler registration decorator: `@_register_handler(event_type)` — v41+ pattern
8. Scheduler `EdgeKind = Literal["blocks", "soft", "data"]` — cross-ref edge type canonical source
9. Mode isolation via `BUILD_ONLY_EVENT_PREFIXES` / `TEACH_ONLY_EVENT_PREFIXES` — W012 detection source

**Consolidation recommendation for planner:** Consolidate the 14 potential spec files into 5–6 documents
to avoid fragmentation. Three plans (ART, DSK, REF) each produce 1–2 consolidated specs.
The minimum viable document set covering all 17 requirements is:
1. `ARTIFACT-CATALOG.md` — covers ART-01 through ART-05 (catalog + templates + immutability + classification + validation)
2. `DIRECTORY-TREE.md` — covers DSK-01 through DSK-06 (tree + naming + placement + file count + index schema + concurrent access)
3. `INDEX-SCHEMA.md` — standalone JSON schema (machine-readable, consumed independently by v41+ projector)
4. `CROSS-REFERENCES.md` — covers REF-01 through REF-04 (format + edges + policy + broken handling)
5. `CONSISTENCY-CODES.md` — covers REF-05 and REF-06 (15 W-codes + validate_consistency() function spec)
