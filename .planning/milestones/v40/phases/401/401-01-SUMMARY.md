---
phase: 401-artifact-catalog-naming-layout-cross-refs
plan: 01
subsystem: build-hierarchy
tags: [artifact-catalog, templates, immutability, schema-ownership, validation-rules, specification, design-contract]
requires:
  - "Phase 400: 9 spec docs (TIER-ARC, TIER-STAGE, TIER-SLICE, TIER-STEP, FRONTMATTER-SCHEMAS, DESC-SEMANTICS, FSM-TABLES, EVENT-TAXONOMY, COMPOSITE-CASCADE)"
provides:
  - "ARTIFACT-CATALOG.md: complete catalog of 13 artifact types with property tables, 10 embedded templates, immutability rules"
  - "SCHEMA-OWNERSHIP.md: 13-artifact classification table, MAP.md hybrid ownership spec, 12 schema validation rules"
affects:
  - "Phase 401 Plan 02 (DIRECTORY-TREE.md)"
  - "Phase 401 Plan 03 (CROSS-REFERENCES.md + CONSISTENCY-CODES.md)"
  - "v41+ daemon projector, artifact loader, pydantic validator"
  - "v42 quality pipeline verifier"
tech-stack:
  added: []
  patterns:
    - "Property table format for artifact catalog entries (13 fields per entry)"
    - "YAML frontmatter template structure with Agent/Projector field markers"
    - "Template↔Schema cross-reference validation table pattern"
    - "Immutability rules table with lock triggers, enforcement levels"
    - "Projection-vs-authored classification with rebuild trigger + fields-surviving-rebuild columns"
    - "Hybrid ownership specification with exact event trigger mapping"
    - "Design contract document structure: header + conventions + sections + cross-references + threat model"
key-files:
  created:
    - ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (792 lines)"
    - ".planning/milestones/v40/phases/401/specs/SCHEMA-OWNERSHIP.md (205 lines)"
  modified: []
key-decisions:
  - "CRIT.md frontmatter fields: parent_id, criteria (array of {id, title, description, acceptance_test}), created_at, updated_at — designed under Claude's discretion per plan"
  - "MAP.md frontmatter fields: parent_id, children (array of {id, goal, status_checkbox}), generated_by, generated_at, last_updated — hybrid artifact with projector-only checkbox updates"
  - "DECISIONS.md frontmatter fields: parent_id, decisions (array of {id, title, context, decision, date}) — append-only, no projector fields"
  - "DESIGN.md frontmatter fields: slice_id, design_version, architecture_approach, components (array of {name, responsibility, interfaces})"
  - "RESEARCH.md frontmatter fields: slice_id, research_topics (array of {topic, decision, alternatives_considered, rationale}), standard_stack, confidence"
  - "Schema validation rules numbered V-01 through V-12 (not W-codes — W-codes are for Plan 03 consistency validation)"
  - "VERIFICATION.md and SUMMARY.md classified as agent-authored with snapshot-before-mutation lock on Slice shipped"
  - "DECISIONS.md classified as always mutable (append-only but no lock trigger)"
  - "Immutability enforcement levels unified: Rejected (blocked) for full-lock artifacts, Snapshot-before-mutation for partial-lock artifacts, N/A for always-mutable"
patterns-established:
  - "Artifact catalog property table: Purpose, Owning Tier, Schema Owner, Created By, Creation Trigger, Updated By, Update Triggers, File Format, Frontmatter Model, Immutability, Cross-Refs From, Cross-Refs To, File Path"
  - "Path variable notation: arc-{n}, stage-{n}, slice-{n}, step-{n} — uniformly enforced across all entries"
  - "Projector-owned field comment marker: '# ── Projector-owned (populated by daemon, NEVER edit) ──'"
  - "Template body guidance sections with inline comments describing what the agent should write"
  - "Hybrid ownership spec: agent creates structure, projector updates specific sub-fields on named events, guarantees no child insertion/removal/reordering"
  - "Validation rule classification: pydantic-level (5 rules) vs cross-reference/additional (7 rules)"
  - "Validation timing table: creation, read, verify, daemon startup — with consumer attribution"
requirements-completed: [ART-01, ART-02, ART-03, ART-04, ART-05]
metrics:
  duration: "~60 minutes"
  completed: "2026-05-07"
---

# Phase 401 Plan 01: Artifact Catalog & Schema Ownership — Summary

**One-liner:** Produces the complete blueprint for every `.state/build/` artifact type — 13 cataloged with structured property tables, 10 with embedded YAML frontmatter templates validated against Phase 400 pydantic models, full immutability rules, projection-vs-authored classification, and 12 schema validation rules.

## Outcomes

1. **ARTIFACT-CATALOG.md** (792 lines, b884475) — Single source of truth for all 13 artifact types across all four tiers. Each entry includes 13 property fields (Purpose through File Path) with uniform path variable notation. 10 embedded templates with complete YAML frontmatter blocks, body guidance comments, and a Template↔Schema cross-reference table proving no field drift from Phase 400 pydantic models. Comprehensive immutability rules covering lock triggers, locked/mutable fields, and enforcement levels for every artifact. D-401-12 lock rules (stepNPLAN.md + CRIT.md lock on `in_progress`) explicitly documented.

2. **SCHEMA-OWNERSHIP.md** (205 lines, 9078c3b) — Complete projection-vs-authored classification: 10 agent-authored, 1 hybrid (MAP.md), 2 projector-rebuilt. MAP.md hybrid ownership specified with exact checkbox trigger events (`state.stage.shipped`, `state.slice.shipped`, `state.*.abandoned`) and five projector guarantees. 12 schema validation rules: 5 pydantic-level (V-01 through V-05, enforced by `extra="forbid"`) and 7 cross-reference/additional (V-06 through V-12, enforced by daemon artifact loader, scheduler, and consistency validator). Four validation trigger points (creation, read, verify, daemon startup) with consumer attribution for every rule.

## Requirements Satisfied

| Requirement | Description | Satisfied By |
|-------------|-------------|--------------|
| ART-01 | Catalog of all 13 artifact types with purpose, tier, ownership, triggers, format | ARTIFACT-CATALOG.md Section 1 — 13 structured property-table entries |
| ART-02 | Templates for all 10 agent-authored types with frontmatter field validation | ARTIFACT-CATALOG.md Section 2 — 10 embedded templates + Template↔Schema cross-reference table |
| ART-03 | Immutability rules per artifact — lock triggers, locked/mutable fields, enforcement | ARTIFACT-CATALOG.md Section 3 — 14-row immutability rules table |
| ART-04 | Projection-vs-authored classification with rebuild triggers | SCHEMA-OWNERSHIP.md Section 1 — 13-artifact classification table + rebuild trigger column |
| ART-05 | Schema validation rules — when validation fires and what it checks | SCHEMA-OWNERSHIP.md Section 3 — 4 trigger points + 12 validation rules with consumer attribution |

## Decisions Made

Under Claude's discretion (per plan):

- **CRIT.md frontmatter:** `parent_id` (tier aggregate ID), `criteria` (array of {id, title, description, acceptance_test}), `created_at`, `updated_at`. Minimal schema — CRIT.md is primarily body prose with a lightweight frontmatter for indexing.
- **MAP.md frontmatter:** `parent_id`, `children` (array of {id, goal, status_checkbox}), `generated_by`, `generated_at`, `last_updated`. The `status_checkbox` field uses the literal string format `[ ]`, `[x]`, `[!]` — the projector writes these exact values.
- **DECISIONS.md frontmatter:** `parent_id`, `decisions` (array of {id, title, context, decision, date}). Each decision entry has its own `date` field for chronological tracking.
- **DESIGN.md frontmatter:** `slice_id`, `design_version` (semver string), `architecture_approach` (free-text), `components` (array of {name, responsibility, interfaces}). Components are declared in frontmatter for machine-readability; body prose expands on them.
- **RESEARCH.md frontmatter:** `slice_id`, `research_topics` (array of {topic, decision, alternatives_considered, rationale}), `standard_stack`, `confidence` (HIGH/MEDIUM/LOW). The `alternatives_considered` field captures rejected options alongside the chosen one.
- **Validation rule numbering:** Used V-01 through V-12 instead of the W-code namespace (W001–W015). W-codes are reserved for Plan 03 consistency validation codes. Validation rules (V-01..V-12) describe WHAT checks fire; W-codes (Plan 03) describe WHAT inconsistencies are detected.
- **VERIFICATION.md and SUMMARY.md immutability:** Lock on Slice `shipped` with snapshot-before-mutation enforcement. Before shipping, they remain fully mutable for the agent to iterate.
- **DECISIONS.md immutability:** Always mutable but append-only by convention (D-401-02). No formal immutability lock — the append-only policy is a workflow convention, not a daemon-enforced lock. Individual entries once written are never edited by convention.
- **Immutability enforcement taxonomy:** Three levels — Rejected (blocked), Snapshot-before-mutation, N/A. Unified across all artifacts to avoid ambiguous "warned vs blocked" semantics.

## Phase 400 Cross-Reference Index

Both documents reference Phase 400 specs by document+section (never reproduce):

| Phase 400 Spec | Referenced By | For |
|----------------|---------------|-----|
| TIER-ARC.md | ARTIFACT-CATALOG.md | Arc state machine, owned artifacts, directory path |
| TIER-STAGE.md | ARTIFACT-CATALOG.md | Stage state machine, owned artifacts, directory path |
| TIER-SLICE.md | ARTIFACT-CATALOG.md | Slice state machine, owned artifacts, Step file naming (D-04), workflow order (D-06) |
| TIER-STEP.md | ARTIFACT-CATALOG.md | Step state machine, D-03 renamed status values, lack of `depends_on` (D-11) |
| FRONTMATTER-SCHEMAS.md | Both documents | All four pydantic models, field ownership (TIER-07), ID encoding, `extra="forbid"` |
| DESC-SEMANTICS.md | Both documents | D-13 abandon cascade, D-14 deferment, D-15 blocked mechanics, D-16 decimal IDs |
| FSM-TABLES.md | SCHEMA-OWNERSHIP.md | Status Literal valid values per tier (V-04 validation) |
| EVENT-TAXONOMY.md | ARTIFACT-CATALOG.md | Event types used as update triggers in catalog entries |

## Consumer Audit

Which downstream plans and runtime components consume each document section:

| Document Section | Consumed By |
|-----------------|-------------|
| ARTIFACT-CATALOG.md §1 (Catalog) | Plan 401-02 DIRECTORY-TREE.md (places artifacts on disk), Plan 401-03 CROSS-REFERENCES.md (cross-reference candidates), v41+ artifact loader (path resolution) |
| ARTIFACT-CATALOG.md §2 (Templates) | v41+ `/state-new arc|stage|slice` CLI commands (render templates into editable files) |
| ARTIFACT-CATALOG.md §3 (Immutability) | v41+ daemon snapshot-before-mutation protocol (D-401-13), v42 quality pipeline verifier |
| SCHEMA-OWNERSHIP.md §1 (Classification) | v41+ projector rebuild logic (decides which artifacts to rebuild), v41+ daemon artifact loader (knows which files are projector-owned) |
| SCHEMA-OWNERSHIP.md §2 (MAP.md Hybrid) | v41+ projector handler for `state.stage.shipped` / `state.slice.shipped` events (checkbox update logic), v41+ MAP.md rendering in TUI |
| SCHEMA-OWNERSHIP.md §3 (Validation Rules) | v41+ pydantic frontmatter validator (V-01..V-05), daemon artifact loader (V-06..V-10), consistency validator (V-11..V-12), Plan 401-03 CONSISTENCY-CODES.md (W-code counterparts) |

## Deviations from Plan

None — plan executed exactly as written. All locked decisions from 401-CONTEXT.md (D-401-01 through D-401-17) reflected in specification content. All 17 locked decisions referenced by ID. No auth gates encountered. No architectural changes needed.

### Claude's Discretion Decisions (per plan authorization)

The plan explicitly authorized Claude's discretion for: CRIT.md/MAP.md/DECISIONS.md/DESIGN.md/RESEARCH.md frontmatter field design, template body guidance text, and VERIFICATION.md/SUMMARY.md immutability classification. These were exercised as documented in the "Decisions Made" section above. All decisions align with D-401-01 through D-401-13 locked decisions.

## Threat Flags

None — both documents are design contracts (not runtime code). The threat model (T-401-01 through T-401-05) is fully addressed within each document's threat model alignment section. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced.

## Known Stubs

None — no hardcoded empty values flowing to UI, no placeholder text, no TODO/FIXME markers. All template frontmatter fields are properly specified with documented types and defaults.

---

*Plan 401-01 complete. ARTIFACT-CATALOG.md (792 lines, ART-01/02/03) and SCHEMA-OWNERSHIP.md (205 lines, ART-04/05) committed. 997 total specification lines. Downstream consumers: Plan 401-02 (DIRECTORY-TREE.md), Plan 401-03 (CROSS-REFERENCES.md), v41+ daemon projector and artifact loader.*
