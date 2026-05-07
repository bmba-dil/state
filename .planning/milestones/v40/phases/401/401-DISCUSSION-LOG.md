# Phase 401: Discussion Log

**Phase:** 401 — Artifact Catalog, Naming, Layout, Cross-Refs
**Milestone:** v40 — Build Hierarchy & Artifact System Architecture
**Date:** 2026-05-07
**Mode:** Interactive (no flags)

---

## Prior Context

Phase 400 CONTEXT.md loaded with 19 decisions (D-01 through D-19) carried forward:
- D-01/D-02: Dash-prefix IDs + kebab-case slugs
- D-04: Steps as markdown files, Slice folder holds all
- D-05: Core artifacts named (CRIT.md, MAP.md, DESIGN.md, RESEARCH.md, stepNPLAN.md, VERIFICATION.md, SUMMARY.md)
- D-06: Slice workflow order
- D-09: ID resolution via index.json
- D-10: Same-parent-only dependencies
- D-12: depends_on as frontmatter ID array with edge types

v40 ROADMAP, REQUIREMENTS, HANDOFF, and STATE.md loaded. REQ IDs: ART-01..05, DSK-01..06, REF-01..06 (17 total for Phase 401).

---

## Area 1: Artifact Catalog Details

**Q1:** Beyond D-05 named artifacts, additional files?
**A:** Option 2 (ARC.md/STAGE.md) + Option 3 (DECISIONS.md). Both added.
→ D-401-01, D-401-02

**Q2:** CRIT.md format?
**A:** Numbered falsifiable requirements (CRIT-01, CRIT-02...)
→ D-401-03

**Q3:** MAP.md — what kind of map?
**A:** "This is our 'roadmap', the main 'tracking file' that will hold all the stages and all the slices and be updated as work is done. generated in the state-new stage/arc flow, is the tracker file, constantly updated after initial generation. check out our own roadmap.md files for reference."
→ D-401-04, D-401-05

**Q4:** Slice workflow docs — separate or consolidated?
**A:** Separate files. Each is output of one workflow step, input for the next.
→ D-401-06

---

## Area 2: STATE.md Consolidation & File Count

**Q1:** STATE.md placement?
**A:** Consolidated JSON (recommended). Canonical under `.state/build/state/`. CLI generates per-directory on demand.
→ D-401-07

**Q2:** Step file count?
**A:** Acceptable as-is. 7+ files per Slice fine. Each file has clear purpose.
→ D-401-08

---

## Area 3: Projection vs Authored Boundary

**Q1:** ARC.md/STAGE.md — authored or projector?
**A:** Agent-authored. Projector updates status field only.
→ D-401-09, D-401-10

**Q2:** MAP.md checkboxes — who updates?
**A:** Projector updates checkboxes automatically.
→ D-401-11

**Q3:** Immutability — what locks on execute?
**A:** Plan + criteria only (stepNPLAN.md + CRIT.md). DESIGN.md, RESEARCH.md remain mutable.
→ D-401-12

**Q4:** Enforcement mechanism?
**A:** Snapshot protocol (recommended). Snapshot-before-mutation, daemon-level enforcement.
→ D-401-13

---

## Area 4: Cross-Reference & Consistency Codes

**Q1:** index.json structure?
**A:** Tier-separated: `{arcs: {}, stages: {}, slices: {}, steps: {}}`
→ D-401-14

**Q2:** Broken reference handling?
**A:** Surface + block. W-code flag. In-progress referrer blocks execution until user resolves.
→ D-401-15

**Q3:** Consistency code severity?
**A:** Tiered severity: ERROR, WARNING, INFO.
→ D-401-16

**Q4:** validate_consistency() — advisory or blocking?
**A:** "blocking gate, but daemon MUST resolve by launching a workflow to fix it in session or subagent to fix it. error + issue + resolution generated on the spot and injected as context into session/subagent"
→ D-401-17

---

## Summary

17 decisions captured (D-401-01 through D-401-17). All four gray areas discussed and resolved. 5 items in Claude's Discretion. 3 deferred ideas.
