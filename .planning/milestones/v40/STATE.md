---
gsd_state_version: 1.0
status: executing
last_updated: 2026-05-07T02:15:18.485Z
phase_state: executing
---

# STATE: v40 Build Hierarchy & Artifact System Architecture

**Milestone:** v40
**Type:** Design-phase (no code — architecture documents only)
**Created:** 2026-05-06

---

## Project Reference

**Core value:** A single polyglot engine lets me ship software (build mode) and learn new skills (teach mode) with the same deep tooling — event-sourced history, dependency-DAG concurrency, cross-host portability.

**Current focus:** v40 design spike — fully architecting the four-tier product hierarchy (Arc → Phase → Slice → Step) and its artifact system before build-mode implementation resumes in v14.

---

## Current Position

**Milestone:** v40
**Phase:** 400 ✓ Complete — Tier Definitions & State Machines
**Next Phase:** 401 (Artifact Catalog, Naming, Layout, Cross-Refs)
**Status:** Phase 400 complete, ready for Phase 401

```
[████████████████░░░░] 1/2 phases complete
Phase 400:  ✓ Complete (9 spec docs, 3,332 lines)
Phase 401:  Not started
```

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases in milestone | 2 |
| Phases completed | 0 |
| Requirements mapped | 31/31 (100%) |
| Documents produced (est.) | 12–18 markdown specification files |
| P0 pitfalls owned | 0 (design-phase only) |

---

## Accumulated Context

### Decisions

*None yet — phase planning not started.*

### Key Questions for Discuss-Phase

From HANDOFF.md and research SUMMARY.md:

1. **Arc → Phase relationship**: Can an Arc contain phases that depend on phases in another Arc? Or are Arcs fully independent?
2. **Arc planning depth**: Just a list of phases with goals? Or include dependency graphs between phases?
3. **Phase planning depth**: Just a list of Slices with goals? Does the Phase plan include the DAG of Slices?
4. **Slice dependency DAG**: Slices can depend on other Slices (within same Phase? across Phases?). What's the boundary?
5. **Step serialization**: Steps always serial within a Slice? Can a Slice ever have concurrent Steps?
6. **Decimal insertions**: Supported at Slice level? At Step level? How does renumbering work?
7. **STATE.md placement**: Per-directory vs consolidated JSON projections? (research tension)
8. **Artifact immutability**: Can STEP.md be modified after execution begins? ARC.md when child Phase in progress?
9. **Naming style**: Human-readable slugs vs machine-sortable IDs vs both?
10. **Cross-reference format**: File paths? Content hashes? Event IDs? Frontmatter keys?

### Tensions to Resolve (from research)

| Tension | ARCHITECTURE.md | PITFALLS.md | Resolution |
|---------|-----------------|-------------|------------|
| STATE.md placement | Per-directory | Consolidated JSON projections | Discuss-phase |
| Canonical ID format | Sequential integers | UUIDs/ULIDs | Discuss-phase |
| Step file count | 5 separate files | Consolidated 1-2 files | Discuss-phase |
| Descope semantics | — | — | Discuss-phase |

### Blockers

*None.*

### Potential Risks

- **Scope creep**: v40 is a design-only milestone — temptation to start coding schemas must be resisted; implementation belongs in v14.
- **Analysis paralysis**: 31 requirements with multiple tensions flagged — discuss-phase must resolve tensions without over-engineering.
- **Drift from research**: Research recommends specific state counts (Arc:3, Phase:4, Slice:5, Step:8) — phase planning must respect these caps or explicitly override with rationale.

---

## Session Continuity

**Last session:** 2026-05-06 — Roadmap created.
**Next action:** `/gsd:plan-phase v40.P400` (or `v40.400`) — Plan Phase 400: Tier Definitions & State Machines.

---

*State file created: 2026-05-06*
*Last updated: 2026-05-06*
