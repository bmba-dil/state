# STATE: state

**Last updated:** 2026-04-22 — Quick task 2 completed (pre-execution ROADMAP audit, independent re-pass)

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
**Current milestone:** — none active yet (pre-execution)
**Current phase:** — none active yet

**Phases complete:** 0 / 256
**Milestones complete:** 0 / 27
**v1 requirements satisfied:** 0 / 221

```
[............................................................] 0%
```

### Unblocked milestones (ready to start, parallel-safe)

- M-A1 — Event Store Foundation
- M-A2 — Auth Coverage (5 methods)
- M-A3 — Provider Routing + Model Profiles (soft-depends on M-A2 for cred testing; scaffolding can start now)
- M-A4 — Worktree + Snapshot Service
- M-A5 — DAG Scheduler

All five Tier 1 milestones can START concurrently; M-A3 soft-depends on M-A2 (auth creds for provider tests — scaffolding parallel-safe) and M-A5 hard-depends on M-A1 (reactive to event-store stream). See ROADMAP.md lines 396 (M-A3) and 579 (M-A5).

### Critical path preview

Build critical path: A1 → A6 → A7 → A8 → A11 → A12 → A14 → A15 → A16 → A27
Teach critical path: A1 → A6 → A7 → A8 → A11 → A13 → A18 → A20 → A22 → A27

M-A2 carries 9 of the 16 P0 pitfalls (Anthropic OAuth stealth flow); start early in parallel.

---

## Performance Metrics

| Metric | Value |
|---|---|
| Roadmap created | 2026-04-22 |
| Phases defined | 256 |
| Milestones defined | 27 |
| v1 requirements captured | 221 |
| Coverage | 100% |
| P0 pitfalls identified | 16 |
| P0 pitfall regression tests committed | 0 / 16 |
| Milestones shipped | 0 / 27 |
| Total v1 phases shipped | 0 / 256 |
| Total elapsed days since init | 0 |

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
7. **Dual-write events (SyncEvent + SQLite)** — SQLite is authoritative truth
8. **`.state/auth.json` portable, chmod 0600** — cross-host reusable
9. **Two MCP servers: state-build + state-teach** — enforces exclusive modes physically
10. **Pure-Python DAG scheduler (~300 LOC)** — zero new deps
11. **Per-Slice worktree, Step+Slice snapshots** — match human dev branch-per-feature
12. **Event-sourced teach-mode mental model** — MENTAL-MODEL.json is rebuildable projection
13. **Single bundled opencode plugin** — one install path
14. **All 5 auth methods day one** — Pro/Max audience is primary

### Open roadmap-time questions (from SUMMARY §7 — to be resolved during Plan-Phase)

1. **Verification Arc granularity** — kept inside M-A14 for now; split if verifier surface grows.
2. **Mode-runtime factoring** — resolved: shared plumbing in M-A18 kernel (Q2, per M-A20.P1).
3. **Concept-teacher ↔ modes direction** — resolved: concept-teacher orchestrator invokes modes (M-A18.P7).
4. **Docs timing** — threaded per-milestone + finalized in M-A27.P7.
5. **Test-infra timing** — threaded per-milestone + finalized in M-A27.P8.
6. **Workstreams vs Arcs** — workstreams is a first-class GSD command port (M-A16.P7) orthogonal to Arcs.
7. **Knowledge-graph Arc fit** — deferred to v2 (ADV-V2-01); intel via M-A16.P2 covers MVP.
8. **MVP personality count** — all 7 day-one (M-A21.P1) — aligns with cardinal rule thoroughness.
9. **Quick/Sketch/Spike collapse** — `/state:build:quick` only at v1 (M-A15.P7); explore/brainstorm/scan as separate commands (M-A16.P12).
10. **Eval infrastructure timing** — v2 (EVAL-V2-01, EVAL-V2-02).
11. **MVP scope boundary — host portability** — MCP-only day-one (M-A26) per PROJECT.md; full UX v2.

### Known gaps flagged for phase-time research

- **AOL drill-verify internals** (M-A19.P1) — Bayesian mastery update formula; MEDIUM confidence.
- **GSD state-machine internals** (all M-A16 phases) — roles enumerated, PROJECT.md mandates redesign not port.
- **TuiPluginInstallOptions** (M-A27.P2) — install-discovery mechanics for opencode plugin.
- **opencode `experimental.primary_tools` × `mcp__state-*__` interaction** (M-A12.P9, M-A13.P9) — compat test.
- **litellm 1.80+ Anthropic beta-flag forwarding** (M-A3.P2) — capture-and-assert.

### Todos (project-level; not phase-scoped)

- [ ] First Tier 1 milestone kickoff — pick among M-A1..M-A5 (suggested start: M-A1 + M-A2 in parallel since they have zero predecessors and carry the heaviest risk)
- [ ] Create per-milestone ARC.md files under `.state/build/arcs/` once Tier 1 produces the directory structure (after M-A11.P7 init)
- [ ] Commit `.planning/ROADMAP.md`, `.planning/STATE.md`, updated `.planning/REQUIREMENTS.md` in initial roadmap commit
- [ ] After M-A2.P4 completes, re-capture claude-cli headers for version-lock doc (P2-1 defence)

### Blockers

(none — foundation is unblocked)

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 1 | Pre-execution audit of ROADMAP.md → REVIEW-ROADMAP.md | 2026-04-22 | (uncommitted — commit_docs=false) |  | [1-pre-execution-audit-of-roadmap-md-review](./quick/1-pre-execution-audit-of-roadmap-md-review/) |
| 2 | Independent re-audit of ROADMAP.md (--full): domain hygiene + Arc/Phase/Slice/Step vs Milestone/Phase conflation | 2026-04-22 | (uncommitted — commit_docs=false) | Verified | [2-audit-roadmap-md-for-domain-confusion-an](./quick/2-audit-roadmap-md-for-domain-confusion-an/) |

---

## Session Continuity

### Next actions (when resuming or starting)

1. **Review ROADMAP.md and approve milestone structure** (via orchestrator `/gsd:new-project` confirmation).
2. **Approve the starting milestone set** — recommended: M-A1 (Event Store) + M-A2 (Auth) in parallel. M-A2 carries the tallest P0 concentration (Anthropic OAuth stealth — 9 P0 pitfalls); starting it early in parallel ensures no late-stage auth surprises.
3. **Run `/gsd:plan-phase M-A1.P1`** (project scaffolding + pyproject + `state_core` package skeleton) — first concrete Slice/Step decomposition.
4. **Run `/gsd:plan-phase M-A2.P1`** (AuthMethod protocol + Credential container) — parallel to M-A1.
5. As Tier 1 ships: unblock Tier 2 milestones in dependency order per ROADMAP.md DAG.

### Plan-phase consumer guidance

`/gsd:plan-phase <milestone>.<phase>` reads:
- Phase goal + Requirements + Depends on from ROADMAP.md
- Success criteria from the parent milestone
- Opencode surface + source influence + artifacts written + verifier — informs must_haves
- P0 pitfalls owned — mandatory regression tests before phase closure

### Project state file set

- `/Users/tmac/Projects/state/.planning/PROJECT.md` — cardinal rules, constraints, key decisions
- `/Users/tmac/Projects/state/.planning/REQUIREMENTS.md` — 221 v1 REQ-IDs + traceability
- `/Users/tmac/Projects/state/.planning/ROADMAP.md` — 27 milestones, 256 phases, DAG
- `/Users/tmac/Projects/state/.planning/STATE.md` — this file (live project memory)
- `/Users/tmac/Projects/state/.planning/research/` — SUMMARY, ARCHITECTURE, FEATURES, PITFALLS, STACK
- `/Users/tmac/Projects/state/.planning/config.json` — mode=yolo, granularity=fine, parallelization=true, verifier=true, plan_check=true, nyquist_validation=true, auto_advance=true
- `/Users/tmac/Projects/state/state-inputs/` — gitignored reference material (opencode source, GSD source, AOL workflows, claude-oauth.md, gsd2-auth-analysis.md)

### Tier boundary gates

- **Tier 1 → Tier 2:** all of M-A1..M-A5 ship (foundation complete).
- **Tier 2 → Tier 3:** all of M-A6..M-A13 ship (kernel + plumbing complete).
- **Tier 3 → Tier 4:** all of M-A14..M-A24 ship (build + teach kernels complete).
- **Tier 4 → v1:** M-A27 ships (release ready).

---

*State initialized: 2026-04-22*
