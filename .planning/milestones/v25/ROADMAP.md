# v25 — Migration & Import

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 231–238 (8 phases)

---

## Phases

#### Phase 231 — `state migrate from-gsd` importer (reads `.planning/` → writes `.state/build/`)
**Goal:** Best-effort mapping: GSD milestones → Arcs, phases → Phases, plans → Slices; preserves REQUIREMENTS.md traceability.
**Depends on:** 124
**Requirements:** MIG-01
**Parallelizable:** yes

#### Phase 232 — `state migrate from-aol` importer (reads `.aol/` → writes `.state/teach/`)
**Goal:** Subject + concepts + OBSERVATIONS.jsonl + mental model + confidence/mistakes → `.state/teach/`; preserves array shape (P1-7).
**Depends on:** 167
**Requirements:** MIG-02
**Parallelizable:** yes

#### Phase 233 — Event replay of migration actions (auditable)
**Goal:** Each migration step is an event; full migration replayable from log; idempotence.
**Depends on:** 009, 231, 232
**Requirements:** MIG-03
**Parallelizable:** yes

#### Phase 234 — Dry-run mode + diff preview
**Goal:** `--dry-run` flag; rich-rendered diff of intended writes; no filesystem changes.
**Depends on:** 231, 232
**Requirements:** MIG-04
**Parallelizable:** yes

#### Phase 235 — AOL array-shape preservation (P1-7 defence)
**Goal:** Multi-credential arrays preserved even for single-credential sources; round-trip test 1/2/5 creds.
**Depends on:** 232
**Requirements:** MIG-02
**Parallelizable:** yes

#### Phase 236 — Import from opencode `auth.json` (first-run migration path)
**Goal:** Refinement of 021; treat as a migration, not ambient bootstrap.
**Depends on:** 021, 231
**Requirements:** AUTH-11 (shared)
**Parallelizable:** yes

#### Phase 237 — GSD-2pi analysis integration
**Goal:** Use `state-inputs/gsd-2pi-codebase-analysis/10-python-rebuild-mapping.md` as a mapping authority; capture unknown field warnings.
**Depends on:** 231
**Requirements:** MIG-01
**Parallelizable:** yes

#### Phase 238 — Migration integration test (fixture GSD + AOL projects)
**Goal:** Canned fixture repo; migrate; verify projections; re-migrate → no-op.
**Depends on:** 231..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

