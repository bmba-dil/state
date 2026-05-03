# Milestone v1 — Event Store Foundation (SHIPPED 2026-04-26)

**Status:** Complete
**Phases:** 10 + 1 gap closure
**Date:** 2026-04-22 → 2026-04-26

---

## Phase Details

#### Phase 001 — Project scaffolding + pyproject + `state_core` package skeleton
**Goal:** Create the `state_core` package, `pyproject.toml`, `uv` workspace, base directory layout.
**Completed:** 2026-04-22

#### Phase 002 — Pydantic event schema for all 28+ event types (`state_core.schema`)
**Goal:** Define `EventEnvelope` and every `state.*` event with `extra = "forbid"`, aggregate discriminator, ULID IDs.
**Completed:** 2026-04-22

#### Phase 003 — SQLite schema + numbered migrations (0001_init.sql)
**Goal:** Author `events`, `aggregate_seq`, `steps`, `slices`, `concepts` tables; WAL mode, full index set.
**Completed:** 2026-04-22

#### Phase 004 — Writer task (single-writer aiosqlite + commit-then-emit)
**Goal:** Implement `EventStore.append()` with per-aggregate seq enforcement, monotonic guarantee.
**Completed:** 2026-04-22

#### Phase 005 — SyncEvent mirror emitter
**Goal:** Implement post-commit SyncEvent emission over opencode HTTP.
**Completed:** 2026-04-22

#### Phase 006 — Startup reconciliation (unsent-event replay)
**Goal:** On daemon start, find unsynced events and emit; exponential backoff for unreachable opencode.
**Completed:** 2026-04-22

#### Phase 007 — Monotonic seq crash-recovery (P0-9 test harness)
**Goal:** fsync discipline + recovery routine; Hypothesis property-test for monotonic seq.
**Completed:** 2026-04-22

#### Phase 008 — Projector (steps/slices/concepts cache rebuild from events)
**Goal:** Rebuildable projections; CQRS projection engine with 19 handlers. `state events rebuild-projections` CLI.
**Completed:** 2026-04-24

#### Phase 009 — CLI: `state events tail | replay | export`
**Goal:** Typer-based commands with polling tail, `--from <ulid>` replay, `--format jsonl` export, `--mode` filter.
**Completed:** 2026-04-25

#### Phase 010 — Event-store verifier + 10,000-event golden fixture
**Goal:** Hypothesis property tests: idempotence + determinism; golden-fixture replay assertion.
**Completed:** 2026-04-25

#### Phase 010.1 — Gap closure (CLI polish, Protocol update, daemon orchestrator)
**Goal:** Fix CLI `--mode` validation, update EventStore Protocol, create daemon startup orchestrator, mark EVT-05.
**Completed:** 2026-04-26

---

## Milestone Summary

### What Was Built
- Event store with WAL-mode SQLite (5 migrations, 9 tables, 7 indexes)
- CQRS projection engine (19 handlers, rebuildable steps/slices/concepts cache tables)
- CLI commands (tail, replay, export, rebuild-projections)
- Daemon startup orchestrator (repair → migrate → reconciler)
- Golden 10K-event fixture with triple SHA-256 checksum verification
- 321 passing tests (Hypothesis property, unit, integration, E2E)

### Key Decisions
- Direct SQLite polling for CLI tail (not HTTP SSE)
- Single-writer discipline with BEGIN IMMEDIATE + COMMIT
- Deterministic ULIDs in golden fixture (`f"{i:024d}01"`)
- Decorator-based handler registry for projector
- Late imports in CLI async runners to avoid circular deps

### Tech Debt at Close
- CLI --mode unvalidated (fixed in 010.1)
- EventStore Protocol stale (fixed in 010.1)
- Daemon orchestrator missing (fixed in 010.1)
- EVT-05 checkbox (fixed in 010.1)

### Stats
- **Phases:** 11 (001-010.1)
- **Plans:** 17
- **Commits:** 67
- **Lines of Python:** 2,779
- **Timeline:** 4 days
