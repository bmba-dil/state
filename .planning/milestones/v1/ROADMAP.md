# v1 — Event Store Foundation

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 001–010.1 (11 phases)

---

## Phases

#### Phase 001 — Project scaffolding + pyproject + `state_core` package skeleton
**Goal:** Create the `state_core` package, `pyproject.toml` (pinning per STACK.md), `uv` workspace, base directory layout.
**Depends on:** (none)
**Requirements:** (foundational; no REQ-IDs directly — prerequisite)
**Parallelizable:** no (first phase)

#### Phase 002 — Pydantic event schema for all 28+ event types (`state_core.schema`)
**Goal:** Define `EventEnvelope` and every `state.*` event with `extra = "forbid"`, including aggregate discriminator, ULID IDs, per-aggregate seq.
**Depends on:** 001
**Requirements:** EVT-05, EVT-08
**Parallelizable:** yes with 003

#### Phase 003 — SQLite schema + numbered migrations (0001_init.sql)
**Goal:** Author `events`, `aggregate_seq`, `steps`, `slices`, `concepts`, `decisions`, `tool_calls`, `auth_rotations` tables per ARCHITECTURE §11.3; WAL mode, synchronous=NORMAL, full index set.
**Depends on:** 001
**Requirements:** EVT-01, EVT-02
**Parallelizable:** yes with 002

#### Phase 004 — Writer task (single-writer aiosqlite + commit-then-emit)
**Goal:** Implement `EventStore.append()` with per-aggregate seq enforcement, monotonic guarantee, deterministic clock injection.
**Depends on:** 002, 003
**Requirements:** EVT-01, EVT-02, EVT-03, EVT-06
**Parallelizable:** no

#### Phase 005 — SyncEvent mirror emitter
**Goal:** Implement post-commit SyncEvent emission over opencode HTTP (when reachable), marking `synced_to_opencode=1` per row.
**Depends on:** 004
**Requirements:** EVT-01
**Parallelizable:** yes with 006

#### Phase 006 — Startup reconciliation (unsent-event replay to opencode)
**Goal:** On daemon start, find rows with `synced_to_opencode=0` and emit; handle opencode-unreachable with exponential backoff.
**Depends on:** 004
**Requirements:** EVT-04
**Parallelizable:** yes with 005

#### Phase 007 — Monotonic seq crash-recovery (P0-9 regression test harness)
**Goal:** Add `fsync` discipline + recovery routine that detects and repairs gaps/duplicates in `aggregate_seq`; Hypothesis property-test that ANY crash offset + replay → monotonic sequence.
**Depends on:** 004
**Requirements:** EVT-03
**Parallelizable:** no

#### Phase 008 — Projector (steps/slices/concepts cache rebuild from events)
**Goal:** Rebuildable projections written through the single writer; `state events rebuild-projections` CLI.
**Depends on:** 004
**Requirements:** EVT-02
**Parallelizable:** yes with 009

#### Phase 009 — CLI: `state events tail | replay | export`
**Goal:** Typer-based commands with SSE tailing, `--from <ulid>` replay, `--format jsonl` export, `--mode build|teach|kernel` filter.
**Depends on:** 004
**Requirements:** EVT-07, EVT-08
**Parallelizable:** yes with 008

#### Phase 010 — Event-store verifier + 10,000-event replay golden fixture
**Goal:** Hypothesis property tests: idempotence + determinism; golden-fixture replay assertion.
**Depends on:** 005, 007, 008
**Requirements:** EVT-06 (verifier)
**Parallelizable:** no (final)

#### Phase 010.1 — Gap closure: CLI polish, Protocol update, daemon orchestrator, EVT-05 checkbox
**Goal:** Fix tech debt: validate CLI `--mode` against Mode literal, update EventStore Protocol with Phase 009 methods, add daemon startup orchestrator, mark EVT-05 complete.
**Depends on:** 009, 010
**Requirements:** EVT-04, EVT-05
**Parallelizable:** no

---

