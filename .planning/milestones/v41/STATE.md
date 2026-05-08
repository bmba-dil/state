---
gsd_state_version: 1.0
milestone: v41
milestone_name: Agent Harness & Context Control Design
status: roadmap_complete
stopped_at: Roadmap drafted; awaiting plan-phase 402
last_updated: "2026-05-08T00:00:00.000Z"
last_activity: 2026-05-08 — Roadmap created (5 phases, 402-406, 72/72 v1 reqs mapped)
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State — Milestone v41

**Created:** 2026-05-08
**Status:** Roadmap complete; phase planning pending

---

## Milestone Reference

**Goal:** Design the Build-mode agent harness — the control plane governing agent behavior during a Slice's execute phase. Specify context management, plan format, proof gates, discipline guards, deviation handling, and subagent fanout.

**Type:** Design-phase milestone (zero code — architecture/specification documents only)
**Depends on:** v40 (shipped), v8 (shipped), v7 (shipped), v6 (shipped), v11 (shipped)
**Phase range:** 402–406 (5 phases, integer numbering, override of init's 257)

---

## Current Position

**Active phase:** Not started — Phase 402 (Slice-Cycle & Context Window Spec) is the first phase, ready to plan.
**Phases complete:** 0 / 5
**Plans complete:** 0 / 0 (plans defined per-phase via `/gsd:plan-phase`)

```
[..............................................] 0%
```

### Unblocked phases (ready to plan/start)

- **Phase 402: Slice-Cycle & Context Window Spec** — first phase, no internal deps. Run `/gsd:plan-phase 402` next.

### Phase DAG

```
402 ──► 403 ──► 404 ──► 405 ──► 406
(linear; each phase synthesizes prior spec docs)
```

Each phase consumes the prior phase's spec output. Phase 406 (Harness Architecture Rollup) requires Phases 402–405 to be complete because it cross-references every prior spec.

---

## Requirements Coverage

**v1 requirements:** 72 (across 10 categories: SLC, CTX, STP, PAP, PRF, APG, SRP, DEV, SUB, HRN)
**Mapped to phases:** 72 / 72 (100%)
**Orphaned:** 0

| Category | Count | Phase |
|----------|-------|-------|
| SLC | 7 | 402 |
| CTX | 8 | 402 |
| STP | 8 | 403 |
| PAP | 6 | 403 |
| PRF | 7 | 404 |
| APG | 6 | 404 |
| SRP | 6 | 404 |
| DEV | 7 | 405 |
| SUB | 9 | 405 |
| HRN | 8 | 406 |

---

## Locked Design Decisions (D-1..D-12)

These were locked via discuss-milestone before roadmap creation. The roadmap structure respects all twelve.

| # | Decision | Owning phase |
|---|----------|--------------|
| D-1 | Slice owns the cycle (discuss → plan → execute → verify); Step is leaf | 402 |
| D-2 | Context boundary = Slice (fresh session per Slice; intra-Slice compaction) | 402 |
| D-3 | Slice budget = 200k absolute (not ratio-scaled) | 402 |
| D-4 | Snapshot artifacts are structured (Pydantic+orjson, not markdown) | 402 |
| D-5 | Step = `stepNN-PLAN.md` (GSD-shape: YAML frontmatter + XML body) | 403 |
| D-6 | Boolean proof gate = `must_haves.{truths, artifacts, key_links}` + per-task `<verify><automated>` | 404 |
| D-7 | Plans mutable with audit log; `must_haves` and `<verify>` blocks immutable | 403 |
| D-8 | Proof-gate fail: 3 strikes → context clear+reinject → 3 more strikes → human gate at 6 total | 404 |
| D-9 | Subagents whitelist static per Slice stage; parallelism near-uncapped (default 20) | 405 |
| D-10 | Intervention tiers: advisory → tool-block → force clear+reinject → force-stop+human gate | 406 |
| D-11 | Tiered autonomy: `--tiered`, `--full-yolo`, `--conservative`; per-Slice override | 405 |
| D-12 | plan-slice itself is multi-stage (research → pattern-mapping → planning → validation) | 402 (SLC-03 captures shape) |

---

## Next Actions

1. `/gsd:plan-phase 402` — plan Phase 402 (Slice-Cycle & Context Window Spec). Includes SLC-07 v40-amendment work.
2. After 402 ships, `/gsd:plan-phase 403` (Step/Task Decomposition & Plan-as-Prompt).
3. After 403 ships, `/gsd:plan-phase 404` (Boolean Proof Gate & Discipline Guards).
4. After 404 ships, `/gsd:plan-phase 405` (Deviation Rules & Subagent Management).
5. After 405 ships, `/gsd:plan-phase 406` (Harness Architecture Rollup) — synthesizes 402–405.

---

## Files

- `.planning/milestones/v41/HANDOFF.md` — milestone handoff from discuss
- `.planning/milestones/v41/REQUIREMENTS.md` — 72 v1 requirements (SLC + CTX + STP + PAP + PRF + APG + SRP + DEV + SUB + HRN)
- `.planning/milestones/v41/ROADMAP.md` — phase decomposition (this milestone's roadmap)
- `.planning/milestones/v41/STATE.md` — this file
- `.planning/milestones/v41/phases/` — populated by `/gsd:plan-phase` per phase

---

*State updated: 2026-05-08 — roadmap drafted; 5 phases (402-406); 72/72 reqs mapped*
