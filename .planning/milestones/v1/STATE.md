---
gsd_state_version: 1.0
milestone: v1
milestone_name: Event Store Foundation
status: complete
last_updated: "2026-04-28T03:14:44.283Z"
last_activity: 2026-04-26
---

# STATE: v1 — Event Store Foundation

**Milestone:** v1
**Phase range:** 001–010 (+ 010.1 gap-closure)
**Status:** Shipped 2026-04-26 — merged into `main` 2026-04-28
**Phases complete:** 11 / 11
**Requirements satisfied:** 8 / 8 (EVT-01 .. EVT-08)
**Last activity:** 2026-04-26

---

## Phase Status

| Phase | Slug | Status | Date |
|-------|------|--------|------|
| 001 | project-scaffolding-pyproject-state-core | **Complete** | 2026-04-23 |
| 002 | pydantic-event-schema-all-28 | **Complete** | 2026-04-23 |
| 003 | sqlite-schema-numbered-migrations | **Complete** | 2026-04-23 |
| 004 | writer-task | **Complete** | 2026-04-23 |
| 005 | syncevent-mirror-emitter | **Complete** | 2026-04-23 |
| 006 | startup-reconciliation | **Complete** | 2026-04-23 |
| 007 | monotonic-seq-crash-recovery | **Complete** | 2026-04-24 |
| 008 | projector | **Complete** | 2026-04-24 |
| 009 | cli-state-events-tail-replay | **Complete** | 2026-04-25 |
| 010 | event-store-verifier-10-000 | **Complete** | 2026-04-25 |
| 010.1 | gap-closure (CLI mode validation, Protocol update, daemon orchestrator) | **Complete** | 2026-04-26 |

---

## Audit Result

**Audited:** 2026-04-25 (`v1-MILESTONE-AUDIT.md`)
**Initial verdict:** `tech_debt`
**Resolution:** Addressed by Phase 010.1 (gap-closure)

**Audit scores:**
- Requirements: 8 / 8
- Phases: 10 / 10
- Integration: 5 / 5
- Flows: 5 / 5

**Tech-debt items closed by 010.1:**
- 010.1-A — CLI `--mode` validated against `Mode` literal (Typer callback rejects invalid values)
- 010.1-B — `EventStore` Protocol updated with Phase 009 query methods (`read_events`, `read_events_iter`, `count_events`, `get_last_events`)
- 010.1-C — Daemon startup orchestrator (`repair → migrate → reconciler` sequence)
- EVT-05 checkbox flipped in REQUIREMENTS.md

---

## Delivered

**Code (per MILESTONES.md):**
- 67 commits, ~2,779 lines of Python, 4-day timeline
- 321 tests passing, zero regressions

**Capabilities:**
- Dual-write event store (SQLite authoritative + opencode SyncEvent mirror)
- Per-aggregate monotonic seq with crash-recovery (`UNIQUE(aggregate_id, seq)` index, fsync discipline, repair routine)
- CQRS projector with 19 handler functions for steps/slices/concepts; rebuildable from event log
- CLI: `state events tail | replay --from <ulid> | export --format jsonl | rebuild-projections`, all with `--mode build|teach|kernel` filter
- Golden 10K-event fixture + triple SHA-256 checksum verifier (DB ≡ JSONL ≡ projection)
- Hypothesis property tests (idempotence + determinism across 34 event types)
- Startup reconciliation (replay unsent events when opencode reconnects)
- Daemon startup orchestrator (repair → migrate → reconciler)

**Pitfalls covered:**
- P0-9 (SQLite event-sequence non-monotonic after crash) — regression test harness in 007-D

---

## Branch Status

✓ All v1 work merged into `main` via merge commit on 2026-04-28
(`Merge phases 009 + 010 + 010.1 into main (v1 Event Store Foundation complete)`).

The per-phase branches (`gsd/phase-008-projector`, `gsd/phase-009-cli-state-events-tail-replay`,
`gsd/phase-010-event-store-verifier-10-000`, `gsd/phase-010.1-gap-closure`) are now reachable
from `main` and can be deleted at convenience.

---

## What's Next

v1 is foundation-complete. Tier 1 unblocks:

- **v2 — Auth Coverage (5 methods)** — 9 of 16 P0 pitfalls live here; recommended next.
- **v3 — Provider Routing + Model Profiles** — soft-depends on v2 for cred testing; scaffolding parallel-safe.
- **v4 — Worktree + Snapshot Service** — independent.
- **v5 — DAG Scheduler** — hard-depends on v1 (reactive to event stream); now unblocked.

See `.planning/ROADMAP.md` for the full DAG.
