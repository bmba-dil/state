---
gsd_state_version: 1.0
milestone: v2
milestone_name: Auth Coverage
current_phase: "011"
status: v2 active — phase 011 (state_core.auth.base) up next; v1 shipped & merged
last_updated: "2026-04-29T00:54:32.609Z"
---

# STATE: state

**Last updated:** 2026-04-28 — v2 (Auth Coverage) is now the **active milestone**. Phase 011 (`state_core.auth.base`) is next up. v1 (Event Store Foundation) shipped and merged to `main` 2026-04-28: 11 phases + 010.1 gap-closure, 67 commits, ~2,779 LoC Python, 321 tests passing, 0 regressions.

---

## Project Reference

**Core Value:** A single polyglot engine lets me ship software (build mode) and learn new skills (teach mode) with the same deep tooling — event-sourced history, dependency-DAG concurrency, cross-host portability.

**Primary host:** opencode
**Runtime:** Python 3.12+
**Mode model:** Build + Teach (exclusive per invocation; shared kernel; siloed logic)
**Planning hierarchy:** Arc → Phase → Slice → Step (product); Milestone → Phase (GSD)
**Granularity:** fine
**Parallelization:** true (DAG-native, not linear)

---

## Current Position

**Current tier:** Tier 1 (Foundation)
**Active milestone:** v2 — Auth Coverage (5 Methods + Multi-Cred) — phases 011–022 (12 phases)
**Active phase:** 011 — `state_core.auth.base` (AuthMethod protocol + Credential container) — Not started
**Previous milestone:** v1 — Event Store Foundation — Complete (shipped 2026-04-26, merged to main 2026-04-28)

**Phases complete:** 11 / 256 (v1.001 .. v1.010 + v1.010.1)
**Milestones complete:** 1 / 27
**v1 requirements satisfied:** 8 / 8 (EVT-01..EVT-08) — full coverage
**v2 requirements satisfied:** 0 / N (phase-time mapping; AUTH-01..AUTH-09 + ANTH-* + GEM-* + AGR-* + COP-* + APIK-*)

```
[##..........................................................] 4%
```

### Unblocked milestones (ready to start, parallel-safe)

- v2 — Auth Coverage (5 methods) — **active** (9× P0 pitfalls)
- v3 — Provider Routing + Model Profiles — soft-depends on v2 for cred testing; scaffolding parallel-safe
- v4 — Worktree + Snapshot Service — independent
- v5 — DAG Scheduler — was hard-blocked on v1 (reactive to event stream); now unblocked

v3, v4, v5 can run concurrently with v2.

### Critical path preview

Build critical path: A1 → A6 → A7 → A8 → A11 → A12 → A14 → A15 → A16 → A27
Teach critical path: A1 → A6 → A7 → A8 → A11 → A13 → A18 → A20 → A22 → A27

A1 (= v1) is now complete.

---

## Performance Metrics

| Metric | Value |
|---|---|
| Roadmap created | 2026-04-22 |
| v1 shipped | 2026-04-26 (merged to main 2026-04-28) |
| Phases defined | 256 |
| Milestones defined | 27 |
| v1 requirements captured | 221 |
| Coverage | 100% |
| P0 pitfalls identified | 16 |
| P0 pitfall regression tests committed | 1 / 16 (P0-9 in v1.007-D) |
| Milestones shipped | 1 / 27 |
| Total v1-milestone phases shipped | 11 / 11 |
| Total project phases shipped | 11 / 256 |
| v1 commits | 67 |
| v1 LoC (Python) | ~2,779 |
| v1 tests passing | 321 |
| v1 timeline | 4 days |

---

## Accumulated Context

### Decisions committed (architectural)

Already in PROJECT.md Key Decisions table; re-referenced here:

1. **Python 3.12+** — learn-through-build
2. **Opencode primary host, own no TUI framework** — leverage existing surface
3. **Build and Teach modes exclusive** — physical silo, separate packages + MCP servers
4. **Four-tier Arc → Phase → Slice → Step product hierarchy** — distinct from GSD's milestone/phase
5. **Dependency DAG over linear ordering** — `depends_on` typed edges with scheduler
6. **Hybrid daemon (always-on + per-session worker)** — dashboards + hot state
7. **Dual-write events (SyncEvent + SQLite)** — SQLite is authoritative truth ✓ delivered in v1
8. **`.state/auth.json` portable, chmod 0600** — cross-host reusable
9. **Two MCP servers: state-build + state-teach** — enforces exclusive modes physically
10. **Pure-Python DAG scheduler (~300 LOC)** — zero new deps
11. **Per-Slice worktree, Step+Slice snapshots** — match human dev branch-per-feature
12. **Event-sourced teach-mode mental model** — MENTAL-MODEL.json is rebuildable projection
13. **Single bundled opencode plugin** — one install path
14. **All 5 auth methods day one** — Pro/Max audience is primary

### Open roadmap-time questions (from SUMMARY §7 — to be resolved during Plan-Phase)

1. **Verification Arc granularity** — kept inside v14 for now; split if verifier surface grows.
2. **Mode-runtime factoring** — resolved: shared plumbing in v18 kernel (Q2, per 187).
3. **Concept-teacher ↔ modes direction** — resolved: concept-teacher orchestrator invokes modes (173).
4. **Docs timing** — threaded per-milestone + finalized in 253.
5. **Test-infra timing** — threaded per-milestone + finalized in 254.
6. **Workstreams vs Arcs** — workstreams is a first-class GSD command port (151) orthogonal to Arcs.
7. **Knowledge-graph Arc fit** — deferred to v2 (ADV-V2-01); intel via 146 covers MVP.
8. **MVP personality count** — all 7 day-one (198) — aligns with cardinal rule thoroughness.
9. **Quick/Sketch/Spike collapse** — `/state:build:quick` only at v1 (141); explore/brainstorm/scan as separate commands (156).
10. **Eval infrastructure timing** — v2 (EVAL-V2-01, EVAL-V2-02).
11. **MVP scope boundary — host portability** — MCP-only day-one (v26) per PROJECT.md; full UX v2.

### Known gaps flagged for phase-time research

- **AOL drill-verify internals** (178) — Bayesian mastery update formula; MEDIUM confidence.
- **GSD state-machine internals** (all v16 phases) — roles enumerated, PROJECT.md mandates redesign not port.
- **TuiPluginInstallOptions** (248) — install-discovery mechanics for opencode plugin.
- **opencode `experimental.primary_tools` × `mcp__state-*__` interaction** (114, 123) — compat test.
- **litellm 1.80+ Anthropic beta-flag forwarding** (024) — capture-and-assert.

### Todos (project-level; not phase-scoped)

- [ ] First Tier 2 milestone kickoff after v2..v5 ship — pick among v6..v13 in dep order
- [ ] Create per-milestone ARC.md files under `.state/build/arcs/` once Tier 1 produces the directory structure (after 103 init)
- [ ] After 014 completes, re-capture claude-cli headers for version-lock doc (P2-1 defence)
- [ ] Cleanup: delete merged `gsd/phase-{008..010.1*}` branches when convenient

### Blockers

(none — v1 shipped; Tier 1 siblings unblocked)

### Phases Completed

| Phase | Description | Date | Plans |
|-------|-------------|------|-------|
| 001 | Project scaffolding + pyproject + state_core package skeleton | 2026-04-23 | [001-A](milestones/v1/phases/001-project-scaffolding-pyproject-state-core/001-A-pyproject-workspace-and-tooling.md), [001-B](milestones/v1/phases/001-project-scaffolding-pyproject-state-core/001-B-package-skeleton-and-directory-layout.md) |
| 002 | Pydantic event schema for all 28+ event types | 2026-04-23 | [002-A](milestones/v1/phases/002-pydantic-event-schema-all-28/002-A-base-envelope-and-types.md), [002-B](milestones/v1/phases/002-pydantic-event-schema-all-28/002-B-per-aggregate-models.md), [002-C](milestones/v1/phases/002-pydantic-event-schema-all-28/002-C-tests-and-factories.md) |
| 003 | SQLite schema + numbered migrations | 2026-04-23 | [003-A](milestones/v1/phases/003-sqlite-schema-numbered-migrations/003-A-database-connection-and-event-migrations.md), [003-B](milestones/v1/phases/003-sqlite-schema-numbered-migrations/003-B-cache-tables-migration.md), [003-C](milestones/v1/phases/003-sqlite-schema-numbered-migrations/003-C-tests-for-database-and-migrations.md) |
| 004 | Writer task (single-writer aiosqlite + commit-then-emit) | 2026-04-23 | [004-A](milestones/v1/phases/004-writer-task/004-A-writer-core-and-seq-enforcement.md), [004-B](milestones/v1/phases/004-writer-task/004-B-writer-tests.md) |
| 005 | SyncEvent mirror emitter | 2026-04-23 | [005-A](milestones/v1/phases/005-syncevent-mirror-emitter/005-A-mirror-core-and-integration.md), [005-B](milestones/v1/phases/005-syncevent-mirror-emitter/005-B-mirror-tests.md) |
| 006 | Startup reconciliation | 2026-04-23 | [006-A](milestones/v1/phases/006-startup-reconciliation/006-A-startup-reconciler.md) |
| 007 | Monotonic seq crash-recovery (P0-9 regression harness) | 2026-04-24 | 007-A, 007-B, 007-C, 007-D — see `milestones/v1/phases/007-monotonic-seq-crash-recovery/` |
| 008 | Projector (steps/slices/concepts cache rebuild) | 2026-04-24 | 008-A (Core), 008-B (CLI Integration), 008-C (Test Suite) |
| 009 | CLI: `state events tail \| replay \| export` | 2026-04-25 | 009-A (Queries), 009-B (Commands), 009-C (Tests) |
| 010 | Event-store verifier + 10K replay golden fixture | 2026-04-25 | 010-A (Generator), 010-B (Hypothesis), 010-C (Projector props), 010-D (Verifier) |
| 010.1 | Gap closure: CLI mode validation + Protocol update + daemon orchestrator + EVT-05 | 2026-04-26 | 010.1-A (Mode), 010.1-B (Protocol), 010.1-C (Orchestrator) |

### Quick Tasks Completed

(none recorded)

---

## Session Continuity

### Next actions (when resuming or starting)

1. **Run `/gsd:autonomous --from 11`** (or `/gsd:plan-phase v2.011`) — start v2 (Auth Coverage). v2 owns 9 of 16 P0 pitfalls; highest-priority Tier 1 sibling.
2. **In parallel:** scaffold v3 (Provider Routing) and v4 (Worktree + Snapshot) — both are independent of v2's runtime, only soft-depend on auth creds for tests.
3. **v5 (DAG Scheduler)** — now unblocked since v1 ships event stream; can start concurrently.
4. (Optional) Delete merged `gsd/phase-{008..010.1*}` branches at convenience.

### Plan-phase consumer guidance

`/gsd:plan-phase <milestone>.<phase>` reads:

- Phase goal + Requirements + Depends on from ROADMAP.md
- Success criteria from the parent milestone
- Opencode surface + source influence + artifacts written + verifier — informs must_haves
- P0 pitfalls owned — mandatory regression tests before phase closure

### Project state file set

- `/Users/tmac/Projects/state/.planning/PROJECT.md` — cardinal rules, constraints, key decisions
- `/Users/tmac/Projects/state/.planning/ROADMAP.md` — 27 milestones, 256 phases, DAG
- `/Users/tmac/Projects/state/.planning/STATE.md` — this file (live project memory)
- `/Users/tmac/Projects/state/.planning/MILESTONES.md` — shipped-milestone log (v1 entry: 2026-04-26)
- `/Users/tmac/Projects/state/.planning/DEBT.md` — tech-debt register (empty post-010.1)
- `/Users/tmac/Projects/state/.planning/milestones/v1/REQUIREMENTS.md` — 221 v1 REQ-IDs (EVT-01..08 ✓)
- `/Users/tmac/Projects/state/.planning/milestones/v1/STATE.md` — v1 milestone state (Complete)
- `/Users/tmac/Projects/state/.planning/milestones/v1/v1-MILESTONE-AUDIT.md` — 2026-04-25 audit
- `/Users/tmac/Projects/state/.planning/research/` — SUMMARY, ARCHITECTURE, FEATURES, PITFALLS, STACK
- `/Users/tmac/Projects/state/.planning/config.json` — mode=yolo, granularity=fine, parallelization=true
- `/Users/tmac/Projects/state/state-inputs/` — gitignored reference material (opencode source, GSD source, AOL workflows, claude-oauth.md, gsd2-auth-analysis.md)

### Tier boundary gates

- **Tier 1 → Tier 2:** all of v1..v5 ship (foundation complete). **v1 ✓ — 4 left (v2, v3, v4, v5).**
- **Tier 2 → Tier 3:** all of v6..v13 ship (kernel + plumbing complete).
- **Tier 3 → Tier 4:** all of v14..v24 ship (build + teach kernels complete).
- **Tier 4 → v1 release:** v27 ships (release ready).

---

*State initialized: 2026-04-22 — v1 shipped: 2026-04-26 — v1 merged to main: 2026-04-28 — v2 activated: 2026-04-28*
