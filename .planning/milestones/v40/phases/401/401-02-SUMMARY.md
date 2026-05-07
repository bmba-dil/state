---
phase: 401-artifact-catalog-naming-layout-cross-refs
plan: 02
subsystem: build-hierarchy
tags: [specification, directory-tree, index-schema, naming-conventions, concurrent-access]
requires: [Phase 400 Tier Definitions, Plan 401-01 ARTIFACT-CATALOG.md, Plan 401-01 SCHEMA-OWNERSHIP.md]
provides: [DIRECTORY-TREE.md, INDEX-SCHEMA.md, DSK-01..DSK-06 requirements]
affects: [v41+ daemon, v41+ projector, v41+ CLI commands, v41+ worktree manager, Plan 401-03 CROSS-REFERENCES.md]
tech-stack:
  added: []
  patterns:
    - "Annotated ASCII directory tree with [OWNER] tags (AGENT/PROJECTOR/AGENT+PROJECTOR/STATIC)"
    - "Path Verification Table — cross-referencing every tree node against single-source-of-truth catalog"
    - "JSON Schema 2020-12 with $defs.IndexEntry — projector-rebuilt artifact registry"
    - "Atomic rename write pattern — no file locks, event-sourced conflict resolution"
    - "O(1) ID→path resolution via tier-separated dictionary lookup in index.json"
key-files:
  created:
    - ".planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md (553 lines)"
    - ".planning/milestones/v40/phases/401/specs/INDEX-SCHEMA.md (462 lines)"
  modified: []
key-decisions:
  - "C-DISCRETION-01: PLAN.md.tmpl template included in directory tree (not in ARTIFACT-CATALOG) as backward-compatibility template for GSD-origin plan formats"
  - "C-DISCRETION-02: export-state CLI contract uses read-only model — reads from state/*.json projections, never touches event store"
  - "C-DISCRETION-03: File count upper bound projected at ~17K files for 20 Arcs × 10 Stages × 10 Slices — acceptable on ext4/APFS/NTFS"
  - "C-DISCRETION-04: Worktree preservation on abandon, destruction on shipped (configurable via --keep-worktree flag)"
  - "C-DISCRETION-05: Content-hash pinning uses WARNING for mutable targets, INFO for immutable targets — drift detection without blocking"
  - "C-DISCRETION-06: Incremental rebuild skip optimization uses event_sequence comparison — projector only processes events newer than last rebuild"
patterns-established:
  - "Directory tree: ID-based directory naming with optional kebab-case slug (D-02)"
  - "Step files: flat in Slice directory, no Step subdirectory (D-04)"
  - "STATE.md: consolidated JSON projections (state/*.json) — canonical; export-state CLI generates per-directory markdown on demand"
  - "Projector rebuild: full on daemon startup, incremental per state.* event, atomic write to .tmp then rename"
  - "index.json: tier-separated structure (arcs/stages/slices/steps) per D-401-14 with hierarchical aggregate ID keys"
  - "Concurrent access: lock-free append-only model — atomic rename for writes, event store for conflict resolution"
requirements-completed: [DSK-01, DSK-02, DSK-03, DSK-04, DSK-05, DSK-06]
metrics:
  duration: "11m 51s"
  completed: "2026-05-07"
---

# Phase 401 Plan 02: Directory Tree & Index Schema Summary

**One-liner:** Complete `.state/build/` filesystem blueprint (DIRECTORY-TREE.md, 553 lines) and `index.json` JSON Schema with projector rebuild rules (INDEX-SCHEMA.md, 462 lines) — the authoritative design contracts for v41+ daemon, projector, CLI, and worktree manager.

## Task Summary

| Task | Name | Commit | Files | Lines |
|------|------|--------|-------|-------|
| 1 | DIRECTORY-TREE.md — Directory tree, naming, STATE placement, file count, concurrent access | `02e61d2` | `specs/DIRECTORY-TREE.md` | 553 |
| 2 | INDEX-SCHEMA.md — index.json JSON Schema with rebuild rules | `9070999` | `specs/INDEX-SCHEMA.md` | 462 |

## Created Files

### `.planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md` (553 lines)

Complete blueprint for the `.state/build/` filesystem covering:

- **Section 1 — Complete Directory Tree (DSK-01):** Annotated ASCII tree with 16 directories, 28+ files, each annotated with `[OWNER]` tag (AGENT/PROJECTOR/AGENT+PROJECTOR/STATIC). Consumer notes table maps every tree node to its v41+ consumer and lifecycle timing. Path Verification Table confirms 28/28 catalog paths match ARTIFACT-CATALOG.md (one addition: `PLAN.md.tmpl` for backward compatibility).

- **Section 2 — Naming Conventions (DSK-02):** ID regex patterns for all 4 tiers (`^arc-\d+$`, `^stage-\d+(\.\d+)?$`, `^slice-\d+(\.\d+)?$`, step_number is integer). Directory naming (ID-based + optional slug per D-02). Step file naming (`step{N}PLAN.md` as flat files per D-04). Display prefix convention (derived from hierarchical aggregate ID). Slug derivation rules: kebab-case, max 50 chars, alphanumeric+hyphens only, deduplication on collision.

- **Section 3 — STATE.md Placement (DSK-03):** Consolidated JSON projections under `.state/build/state/` (arcs.json, stages.json, slices.json, steps.json). JSON projection format with example. `export-state` CLI contract: `state export-state [--tier] [--id] [--dir]` generates per-directory STATE.md from canonical JSON. Rebuild semantics: full (daemon startup from event store) and incremental (per state.* event with event_sequence skip optimization).

- **Section 4 — File Count Strategy (DSK-04):** Per-Step file formula (N+5 files per N-step Slice). Scalability projection table from small (189 files) to upper bound (~17K files across 20 Arcs × 10 Stages × 10 Slices). Bloat mitigation: Stage planning scope, single subtree, index-driven discovery, worktree isolation.

- **Section 5 — Concurrent Access Rules (DSK-06):** Directory creation ownership table (who creates each directory, when). Lock-free append-only write model: atomic rename pattern (write to .tmp, rename). Conflict resolution: event store is authoritative, projector overwrites on state change. Concurrent worktree rules: one per Slice, worktree_ready gate, preservation on abandon, destruction on shipped (configurable retention).

- **Section 6 — Cross-References:** Complete mapping to Phase 400 specs (TIER-ARC through FSM-TABLES) and Plan 401-01 specs (ARTIFACT-CATALOG.md, SCHEMA-OWNERSHIP.md). Anti-pattern enforcement list.

### `.planning/milestones/v40/phases/401/specs/INDEX-SCHEMA.md` (462 lines)

Complete JSON Schema and rebuild specification for `index.json` covering:

- **Section 1 — JSON Schema (DSK-05):** Full JSON Schema (Draft 2020-12) with `$defs.IndexEntry` (7 properties: type, path, tier, status, schema_owner, last_updated, content_hash). Type enum: 12 values verified against ARTIFACT-CATALOG.md. Tier enum: arc/stage/slice/step verified against Phase 400. Schema_owner enum: agent/projector/hybrid verified against SCHEMA-OWNERSHIP.md. Required top-level: version, last_rebuilt, event_sequence, arcs, stages, slices, steps. Required on IndexEntry: type, path, tier, status, schema_owner, last_updated.

- **Section 2 — Example index.json:** Four tier entries demonstrating hierarchical aggregate ID keys (arc-1 → arc-1/stage-1 → arc-1/stage-1/slice-1 → arc-1/stage-1/slice-1/step-1).

- **Section 3 — Projector Rebuild Rules:** Full rebuild (daemon startup: walk directory tree, reconcile with event store, orphan cleanup, atomic write). Incremental rebuild (per state.* event: extract aggregate_id, update affected entries, cascade parent counts, atomic write). Event→Index Update table mapping every `state.*` event pattern to its index update and cascade behavior.

- **Section 4 — ID→Path Resolution Algorithm:** O(1) dictionary lookup via tier-separated index sections. Resolution examples for all 4 tiers. Content-hash pinning integration (REF-01): pin hash at reference creation time, WARNING on mutable target mismatch, INFO on immutable target mismatch.

- **Section 5 — Cross-References:** Complete mapping to Phase 400 specs (FRONTMATTER-SCHEMAS.md through EVENT-TAXONOMY.md) and Plan 401-01 specs (ARTIFACT-CATALOG.md, SCHEMA-OWNERSHIP.md). Consumer attribution table (daemon, projector, validate_consistency(), CLI, TUI).

## Requirement Coverage

All 6 DSK requirements satisfied:

| Requirement | Document | Section | Status |
|-------------|----------|---------|--------|
| DSK-01 | DIRECTORY-TREE.md | §1 | ✓ Complete annotated directory tree |
| DSK-02 | DIRECTORY-TREE.md | §2 | ✓ Naming conventions (ID regex, directory naming, slugs, display prefixes) |
| DSK-03 | DIRECTORY-TREE.md | §3 | ✓ STATE.md placement (consolidated JSON + export-state CLI) |
| DSK-04 | DIRECTORY-TREE.md | §4 | ✓ File count strategy (per-Step formula + scalability table) |
| DSK-05 | INDEX-SCHEMA.md | §§1–4 | ✓ JSON Schema + rebuild rules + O(1) resolution |
| DSK-06 | DIRECTORY-TREE.md | §5 | ✓ Concurrent access rules (ownership table + atomic write + worktree rules) |

## Path Verification Table Results

28/28 catalog paths match between DIRECTORY-TREE.md and ARTIFACT-CATALOG.md. One addition: `templates/PLAN.md.tmpl` is included in the directory tree as a backward-compatibility template for GSD-origin plan formats — it is not in ARTIFACT-CATALOG.md (which covers the 9 agent-authored artifact templates + STEP.md.tmpl). The `{worktree}/` directory is correctly absent from the catalog (it's a runtime git artifact, not an engine design artifact).

## Cross-Reference Matrix

Both documents reference Phase 400 specifications and Plan 401-01 outputs without reproducing content:

| Phase 400 Spec | DIRECTORY-TREE.md | INDEX-SCHEMA.md |
|----------------|:---:|:---:|
| TIER-ARC.md | ✓ | ✓ |
| TIER-STAGE.md | ✓ | ✓ |
| TIER-SLICE.md | ✓ | ✓ |
| TIER-STEP.md | ✓ | ✓ |
| FRONTMATTER-SCHEMAS.md | ✓ | ✓ |
| DESC-SEMANTICS.md | ✓ | ✓ |
| FSM-TABLES.md | ✓ | ✓ |
| EVENT-TAXONOMY.md | — | ✓ |

| Plan 401-01 Spec | DIRECTORY-TREE.md | INDEX-SCHEMA.md |
|------------------|:---:|:---:|
| ARTIFACT-CATALOG.md | ✓ | ✓ |
| SCHEMA-OWNERSHIP.md | ✓ | ✓ |

## Consumer Audit

| Consumer | Reads From | When | Purpose |
|----------|-----------|------|---------|
| v41+ daemon initializer | DIRECTORY-TREE.md §1, §5 | First startup | Creates top-level directories (arcs/, state/, templates/) |
| v41+ daemon artifact loader | INDEX-SCHEMA.md §4 | Startup | Loads index.json into memory for O(1) ID→path resolution |
| v41+ projector | INDEX-SCHEMA.md §3 | Every state.* event | Full + incremental index.json rebuild |
| v41+ `validate_consistency()` | INDEX-SCHEMA.md §4 | Startup + on-demand | Orphan detection (W002), stale entry detection (W003), hash mismatch (W012) |
| v41+ CLI `/state-new arc\|stage\|slice` | DIRECTORY-TREE.md §1, §2 | Artifact creation | Directory creation, ID validation, template rendering |
| v41+ CLI `state export-state` | DIRECTORY-TREE.md §3 | On-demand | Generate per-directory STATE.md from state/*.json |
| v41+ worktree manager | DIRECTORY-TREE.md §5 | Slice `worktree_ready` | Worktree creation, naming, lifecycle management |
| v41+ CLI `/state-design` `/state-run` | INDEX-SCHEMA.md §4 | Planning/execution | ID→path resolution for depends_on verification, worktree discovery |
| v17 TUI extensions | INDEX-SCHEMA.md §4 | Session lifecycle | Artifact browser navigation, tier-filtered queries |
| Plan 401-03 CROSS-REFERENCES.md | Both documents | Planning | Resolution algorithm, consistency codes, hash pinning integration |

## Decisions Made Under Claude's Discretion

Per the plan's "Claude's Discretion" scope from 401-CONTEXT.md:

1. **PLAN.md.tmpl inclusion:** Added as backward-compatibility template in the directory tree. Not in ARTIFACT-CATALOG.md (which covers 9 agent-authored templates). Documented as a deliberate addition in the Path Verification Table.

2. **export-state CLI contract:** Specified as `state export-state [--tier arc|stage|slice|step] [--id <aggregate-id>] [--dir <path>]` — reads from state/*.json projections, never touches event store. Output format uses YAML frontmatter matching pydantic models.

3. **Atomic rename details:** Specified the exact pattern: write to `<filename>.tmp` in same directory, then `os.rename()` (POSIX atomic). This is the universal write pattern for all projector-owned files (index.json, state/*.json).

4. **Scalability table numbers:** Derived from the hierarchy structure: small (3×2×3 = 18 Slices, ~189 files), medium (10×3×3 = 90 Slices, ~920 files), large (20×5×5 = 500 Slices, ~5,600 files), upper bound (20×10×10 = 2,000 Slices, ~17K files). All validated as acceptable on ext4/APFS/NTFS.

5. **Worktree lifecycle:** Specified preservation on abandon (forensics per D-13), destruction on shipped (configurable via `--keep-worktree` flag). Worktree manager cleans up stale worktrees on daemon startup.

6. **Content-hash pinning severity:** WARNING for mutable target mismatch (DESIGN.md, RESEARCH.md — expected to change), INFO for immutable target mismatch (CRIT.md after lock, stepNPLAN.md after lock — unexpected). This enables drift detection without blocking.

7. **Incremental rebuild skip:** Uses `event_sequence` comparison — projector skips events where sequence ≤ index's `event_sequence`. Makes daemon restart fast.

## Deviations from Plan

None — plan executed exactly as written. Both tasks followed the detailed action specifications, verification checks passed, and acceptance criteria were met.

## Known Stubs

None — both documents are complete design contracts with no placeholder text, TODO markers, or unimplemented references.

## Threat Flags

None — the specification documents introduce no new security-relevant surface. The atomic rename pattern specified in DIRECTORY-TREE.md §5 is a defensive mechanism (prevents partial reads, aligns with T-401-08 mitigation in the plan's threat model).

## Self-Check

| Check | Status |
|-------|--------|
| DIRECTORY-TREE.md exists at correct path | ✓ (553 lines) |
| INDEX-SCHEMA.md exists at correct path | ✓ (462 lines) |
| Commit `02e61d2` exists | ✓ |
| Commit `9070999` exists | ✓ |
| All 6 DSK requirements addressed | ✓ |
| Path Verification Table confirms 28/28 catalog matches | ✓ |
| Cross-reference matrix covers Phase 400 + Plan 401-01 | ✓ |
| Consumer audit covers all v41+ components | ✓ |
| No deviations from plan | ✓ |
| No stubs found | ✓ |
| No threat flags | ✓ |

## Self-Check: PASSED

All verifications passed. Both specification documents are committed and complete.
