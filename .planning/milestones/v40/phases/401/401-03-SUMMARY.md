---
phase: 401-artifact-catalog-naming-layout-cross-refs
plan: 03
subsystem: build-hierarchy
tags: [cross-references, consistency-validation, dependency-policy, edge-semantics, W-codes]
requires: [401-01, 401-02]
provides:
  - specs/CROSS-REFERENCES.md — cross-reference format, ID resolution, edge semantics, dependency policy, broken reference handling
  - specs/CONSISTENCY-CODES.md — 15 W-codes catalog, validate_consistency() function specification
affects: [v41-daemon, v41-scheduler, v41-projector, v41-validate-consistency, v42-quality-pipeline]
tech-stack:
  added: []
  patterns:
    - "W-code structured entries: 9-property table (Code, Name, Category, Severity, Trigger, Detection Logic, Resolution, Blocking, Affected Tiers) + severity rationale"
    - "Edge type specification: 5-column table (Prerequisite Type, Scheduler Behavior, Artifact Behavior, Broken Behavior)"
    - "Dependency policy table: 6 direction types × (Allowed, Constraint, Validation)"
    - "Broken reference handling matrix: 4 target states × 3 edge types = 12 scenarios"
    - "validate_consistency() function contract pattern: Signature → Inputs → Checks → Output → Timing → Authority Rule → Auto-Resolution"
    - "Severity assignment principle: only data-loss/irreconcilable → ERROR; degraded/self-healing → WARNING; display-only → INFO"
key-files:
  created:
    - ".planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md (377 lines)"
    - ".planning/milestones/v40/phases/401/specs/CONSISTENCY-CODES.md (557 lines)"
  modified: []
key-decisions:
  - "Edge types match scheduler EdgeKind = Literal['blocks', 'soft', 'data'] exactly — no custom edge types"
  - "Broken references use surface-and-block (D-401-15) — no auto-cascade; user retains full agency via 3 resolution paths"
  - "10 ERROR, 4 WARNING, 1 INFO severity distribution — only irreconcilable data-loss risks are ERROR"
  - "validate_consistency() blocks daemon HTTP bind on ERROR findings (D-401-17) — conditional blocking: only if referrer is in_progress for W004/W011"
  - "Event store is authoritative on all filesystem vs event-stream mismatches (REF-06)"
  - "Content-hash pinning uses SHA-256 of full file content with severity-calibrated mismatch handling (WARNING for mutable targets, INFO for immutable)"
patterns-established:
  - "Cross-reference resolution: O(1) index.json dictionary lookup, no filesystem traversal"
  - "Broken reference cascade: blocks → BLOCKED dependents, soft → silently dropped, data → BLOCKED (artifacts won't arrive)"
  - "W-code stability: codes never renumbered; new codes get new numbers (W016+)"
  - "auto-resolution path: 6-step flow (collect → launch → resolve → restart → handle failure → non-deadlock via --force)"
  - "Dual-source authority check: event store (authoritative) vs filesystem (derived cache) with projector as reconciler"
requirements-completed: [REF-01, REF-02, REF-03, REF-04, REF-05, REF-06]
metrics:
  duration: "2 tasks"
  completed: 2026-05-07
---

# Phase 401 Plan 03: Cross-Reference System, Edge Type Semantics, Dependency Policy, Broken Reference Handling, and Consistency Validation Codes

**One-liner:** Specified the complete cross-reference system (format, resolution, edges, policy, broken handling) and 15-consistency-code validation framework — the health-check design contract for v41+ daemon startup gate and projector health module.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create CROSS-REFERENCES.md | `117adcd` | specs/CROSS-REFERENCES.md (377 lines) |
| 2 | Create CONSISTENCY-CODES.md | `f20cbd1` | specs/CONSISTENCY-CODES.md (557 lines) |

**Total:** 2 tasks, 2 files created, 934 lines of specification.

## What Was Built

### Task 1: CROSS-REFERENCES.md (REF-01 through REF-04)

Created the cross-reference system specification covering:

- **REF-01 — Cross-Reference Format:** Defines the `depends_on` YAML structure with `id` (required, stable aggregate ID), `edge` (required, matching scheduler EdgeKind), and `hash` (optional, SHA-256 content hash for change detection). Specifies the O(1) ID resolution algorithm via index.json tier-separated dictionary lookup (5 steps: parse tier prefix → construct hierarchical key → dictionary lookup → cache → return). Content-hash pinning with severity-calibrated mismatch handling (WARNING for mutable targets, INFO for immutable).

- **REF-02 — Edge Type Semantics:** Comprehensive table covering all 3 edge types (`blocks`, `soft`, `data`) with 5 columns: Prerequisite Type, Scheduler Behavior, Artifact Behavior, and Broken Behavior. Confirms exact match with `src/state_core/scheduler.py` line 15: `EdgeKind = Literal["blocks", "soft", "data"]`. Edge validation enforces case-sensitive lowercase exact match — W010 detects invalid edge types.

- **REF-03 — Dependency Policy:** Table covering 6 direction types (same-tier sibling, upward, downward, cross-mode, cross-arc, self-reference) with allowed/forbidden + constraint + validation. Downward references (parent→child) are forbidden — violates scoping hierarchy. Cross-mode references (build↔teach) are forbidden — violates mode isolation (v11). Cross-arc references below Arc tier are forbidden — D-10 same-parent constraint. Self-references are forbidden — meaningless cycle. Detection logic provided for each forbidden direction.

- **REF-04 — Broken Reference Handling:** 12-scenario matrix (4 target states × 3 edge types) covering deleted, abandoned, deferred, and descoped targets. Resolution paths per D-401-15: reassign target, defer dependency, remove reference. Surface-to-agent protocol specifying the 6-step resolution flow (collect findings → launch resolution session → iterate → user resolves → restart daemon) with a non-deadlock `--force` escape hatch.

### Task 2: CONSISTENCY-CODES.md (REF-05 through REF-06)

Created the consistency validation specification covering:

- **REF-05 — 15 W-Codes Catalog:** All 15 codes (W001–W015) with structured entries containing 9 properties (Code, Name, Category, Severity, Trigger, Detection Logic, Resolution, Blocking, Affected Tiers) plus a severity rationale paragraph for each. Severity distribution: 10 ERROR (W001, W004, W006–W012, W014, W015), 4 WARNING (W002, W003, W005, W013), 1 INFO (W005 nuance — downgrades to INFO when target is soft-done via deferment). Summary table with category-based grouping.

- **REF-06 — validate_consistency() Function Specification:** Complete function contract specifying: 5 inputs (event store, index.json, filesystem, frontmatter files, FSM tables), 15 checks organized by category (Projection Health → Cross-Reference Integrity → Hierarchy Integrity → State Machine Integrity → DAG Integrity → Mode Isolation → ID Format Integrity → System Integrity), ConsistencyReport output type (8 fields: daemon_startup_blocked, errors, warnings, infos, total_artifacts_checked, total_cross_references_checked, event_store_sequence, duration_ms), Finding output type (6 fields: code, severity, artifact_id, path, message, detail), 3 execution timing points (daemon startup full check with HTTP bind gate, post-state-change incremental check, on-demand CLI scoped check), authority rule (event store authoritative on mismatch), and auto-resolution path (6-step D-401-17 flow with non-deadlock path).

### W-Code Severity Assignment Rationale

Each code's severity was assigned using the data-loss-risk principle from RESEARCH.md pitfall #3:

**ERROR (10 codes) — irreconcilable with filesystem, data loss risk, or violates hard architectural constraint:**

- **W001** (Orphan in index): Index entry without file → ID→path resolution returns non-existent path. Index is authoritative for lookups — broken lookup contract.
- **W004** (Unresolved cross-ref): Depends_on targets a non-existent ID. If referrer is in_progress, it's blocked on a phantom — execution cannot proceed.
- **W006** (Missing parent pointer): No hierarchy context → DAG position indeterminate. Breaks parent aggregate counts and hierarchical traversal.
- **W007** (Parent-child mismatch): Frontmatter says one parent, filesystem says another. Two authoritative sources disagree — must reconcile.
- **W008** (Invalid state transition): Event stream has impossible transition per FSM. Breaks state-dependent operations throughout the system.
- **W009** (Duplicate ID): Two artifacts claim the same identity. Every ID-based lookup is ambiguous.
- **W010** (Invalid edge type): Unknown edge value ("requires", "needs") → scheduler can't classify the dependency. DAG edge unprocessable.
- **W011** (Cycle): DAG has no valid topological sort. Scheduler deadlock inevitable.
- **W012** (Cross-mode leakage): Build↔teach reference violates mode isolation. Defense-in-depth — 6 enforcement layers broken by one reference.
- **W014** (Invalid decimal ID): Double-decimal or Arc-decimal violates D-16. ID string unparseable — breaks all parsing-dependent operations.
- **W015** (FS-vs-event divergence): Event store (authoritative) says artifact exists, filesystem doesn't. Two primary data stores disagree on fundamental state.

**WARNING (4 codes) — degraded information, projector can self-heal, no data loss:**

- **W002** (Stale index): File exists, index doesn't know about it. Projector adds entry on next rebuild. Temporary "not found" for ID→path resolution until healed.
- **W003** (Status mismatch): Index status ≠ frontmatter status. Projector corrects on next state change event. Temporary display of stale status.
- **W005** (Cross-ref to descoped): Target intentionally abandoned/deferred by user. Planning decision, not system error. Scheduler already adapted via cascade rules.
- **W013** (Stale projection): STATE.md ≠ event-store-computed state. Projector overwrites on next write. Derived read model — not authoritative.

**INFO (1 code, contextual):**

- **W005 nuance:** When target is deferred and referrer already has `deferred_dep` flag → system adapted, no action needed. Downgrades to INFO.

### Phase 400 + Plan 01/02 Cross-Reference Index

| This Plan's Specs | Depends On |
|-------------------|-----------|
| CROSS-REFERENCES.md §Section 2 | INDEX-SCHEMA.md §Section 4 (ID→Path Resolution Algorithm), FRONTMATTER-SCHEMAS.md §Cross-Tier ID Encoding |
| CROSS-REFERENCES.md §Section 3 | FSM-TABLES.md lines 163–166 (D-12 edge types), scheduler.py line 15 (EdgeKind literal) |
| CROSS-REFERENCES.md §Section 4 | DESC-SEMANTICS.md §D-10 (same-parent constraint), schema.py lines 42–48 (mode prefixes) |
| CROSS-REFERENCES.md §Section 5 | DESC-SEMANTICS.md §D-13 (abandon cascade), D-14 (deferment), D-15 (blocked state) |
| CONSISTENCY-CODES.md W004/W005/W010/W011 | CROSS-REFERENCES.md §Section 5 (broken reference handling) |
| CONSISTENCY-CODES.md W001/W002/W003 | INDEX-SCHEMA.md §Sections 1, 3 (JSON Schema, rebuild rules) |
| CONSISTENCY-CODES.md W006/W007/W009 | ARTIFACT-CATALOG.md §Section 1 (parent reference fields), FRONTMATTER-SCHEMAS.md §Cross-Tier ID Encoding |
| CONSISTENCY-CODES.md W008 | FSM-TABLES.md (state transition tables per tier) |
| CONSISTENCY-CODES.md W012 | CROSS-REFERENCES.md §Section 4 (cross-mode detection), schema.py (mode prefixes) |
| CONSISTENCY-CODES.md W013/W015 | COMPOSITE-CASCADE.md (composite events), EVENT-TAXONOMY.md (event types) |
| CONSISTENCY-CODES.md W014 | DESC-SEMANTICS.md §D-16 (decimal insertion) |

### Consumer Audit

**CROSS-REFERENCES.md consumed by:**
- v41+ daemon artifact loader — reads depends_on format, uses resolve_id() for artifact loading
- v41+ scheduler — reads edge semantics for DAG building and frontier calculation
- v41+ projector — indexes cross-references in index.json for fast W004/W005 checks
- v41+ validate_consistency() — reads broken reference rules for W004/W005/W010/W011 detection
- v41+ CLI commands — resolves depends_on for status display and execution gating
- v42 quality pipeline verifier — audits all depends_on entries across artifact tree

**CONSISTENCY-CODES.md consumed by:**
- v41+ daemon — implements validate_consistency() startup gate using ConsistencyReport
- v41+ projector health module — runs incremental W-code checks on state.* events
- v41+ CLI (`state build health`) — renders ConsistencyReport to stdout
- v41+ resolution workflow subagent — reads auto-resolution path and Finding.detail schemas
- v42 quality pipeline verifier — runs validate_consistency() as pre-ship gate
- v17 TUI dashboard — displays W-code counts with severity color coding

## Deviations from Plan

None — plan executed exactly as written. No auto-fix issues, no blocking issues, no architectural changes needed.

## Known Stubs

None — both specification documents are complete. All W-codes have full structured entries (9 properties + severity rationale). All cross-reference semantics are fully specified (format, resolution, edges, policy, broken handling, resolution protocol). No placeholder text, no TODO markers, no incomplete sections.

## Threat Flags

None. Both specifications fully address the threats in the plan's `<threat_model>`:
- T-401-11 (Spoofing → cross-ref to non-existent ID): Mitigated by W004 ERROR + daemon startup gate
- T-401-12 (Tampering → invalid edge type): Mitigated by W010 ERROR + EdgeKind literal enforcement
- T-401-13 (DoS → dependency cycle): Mitigated by W011 ERROR + cycle detection at startup
- T-401-14 (Elevation → cross-mode reference): Mitigated by W012 ERROR + subtree path check
- T-401-15 (Tampering → status mismatch): Mitigated by W003 WARNING + projector self-heal
- T-401-16 (Repudiation → FS-vs-event divergence): Mitigated by W015 ERROR + event store authority rule

## Self-Check

Verifying created files exist and commits are reachable:

```bash
[ -f ".planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md" ] && echo "FOUND: CROSS-REFERENCES.md" || echo "MISSING: CROSS-REFERENCES.md"
[ -f ".planning/milestones/v40/phases/401/specs/CONSISTENCY-CODES.md" ] && echo "FOUND: CONSISTENCY-CODES.md" || echo "MISSING: CONSISTENCY-CODES.md"
git log --oneline --all | grep -q "117adcd" && echo "FOUND: 117adcd" || echo "MISSING: 117adcd"
git log --oneline --all | grep -q "f20cbd1" && echo "FOUND: f20cbd1" || echo "MISSING: f20cbd1"
```
