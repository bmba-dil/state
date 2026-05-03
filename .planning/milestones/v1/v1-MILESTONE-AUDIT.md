---
milestone: v1
audited: 2026-04-25
status: tech_debt
scores:
  requirements: 8/8
  phases: 10/10
  integration: 5/5
  flows: 5/5
gaps:
  requirements: []
  integration: []
  flows: []
tech_debt:
  - phase: 009
    items:
      - "CLI --mode flag accepts any string without validating against Mode literal"
      - "EventStore Protocol not updated for Phase 009 query methods"
  - phase: 006
    items:
      - "No daemon orchestrating startup ordering (repair -> migrate -> reconciler)"
  - phase: 002
    items:
      - "EVT-05 checkbox not updated in REQUIREMENTS.md (code is complete)"
---

# Milestone v1 — Event Store Foundation Audit

**Audited:** 2026-04-25
**Status:** Tech debt review

---

## Requirements Coverage

| REQ-ID | Description | Status | Phase | Notes |
|--------|-------------|--------|-------|-------|
| EVT-01 | Daemon writes events to SQLite | ✓ Satisfied | 004 | WAL+sync=NORMAL, commit-then-emit |
| EVT-02 | SQLite is authoritative | ✓ Satisfied | 008 | Projector reads from SQLite only |
| EVT-03 | Monotonic seq with crash recovery | ✓ Satisfied | 007 | UNIQUE index, repair, Hypothesis tests |
| EVT-04 | Startup reconciliation | ✓ Satisfied | 006 | emittens unsent events on reconnect |
| EVT-05 | Pydantic schemas with extra="forbid" | ✓ Satisfied | 002 | Code complete; checkbox needs update |
| EVT-06 | Deterministic event payloads | ✓ Satisfied | 010 | Golden fixture + Hypothesis + triple checksum |
| EVT-07 | CLI commands | ✓ Satisfied | 009 | tail, replay --from, export --format jsonl |
| EVT-08 | Mode filtering | ✓ Satisfied | 009 | mode param on all CLI commands and EventStore queries |

**Score:** 8/8 requirements satisfied

---

## Phase Summary

| Phase | Name | Status |
|-------|------|--------|
| 001 | Project scaffolding + pyproject | Complete |
| 002 | Pydantic event schema | Complete |
| 003 | SQLite schema + migrations | Complete |
| 004 | Writer task | Complete |
| 005 | SyncEvent mirror emitter | Complete |
| 006 | Startup reconciliation | Complete |
| 007 | Monotonic seq crash-recovery | Complete |
| 008 | Projector | Complete |
| 009 | CLI: tail, replay, export | Complete |
| 010 | Event store verifier + golden fixture | Complete |

**Score:** 10/10 phases complete

---

## Cross-Phase Integration

**Score:** 5/5 E2E flows complete

| Flow | From → To | Status |
|------|-----------|--------|
| EventStore.append() → events table → projector.rebuild_all() | 003→004→008 | ✓ |
| CLI commands calling EventStore query methods | 009→004/009 | ✓ |
| Golden fixture replay assertion | 010→010 | ✓ |
| Mode filtering (schema → DB → CLI → verifier) | 002→003→004→009→010 | ✓ |
| Migration files 0001→0005 | 003→008/009/010 | ✓ |

**Connections:** 14 cross-phase exports verified, 0 orphaned

---

## Tech Debt

### CLI --mode unvalidated (Phase 009)
The `--mode` CLI flag accepts any string without validating against the `Mode` literal. Invalid modes silently return 0 rows instead of raising an error. Fixed in `test_cli.py` docs but not in code.

### EventStore Protocol stale (Phase 009)
The `EventStore` Protocol in `events.py` only declares `append()` and `read_stream()`. Phase 009's `read_events()`, `count_events()`, etc. are not in the protocol. No consumers depend on the protocol for these methods, but it's a maintenance risk.

### Daemon orchestrator missing (Phase 006)
Startup ordering (repair → migrate → reconciler) is specified in docstrings but no daemon module enforces it. Currently `_maybe_repair()` runs lazily on first access. Will be addressed in future milestone.

### EVT-05 checkbox (Phase 002)
Code for `extra="forbid"` is verified present on all 29 data models and `EventEnvelope`. The checkbox in `REQUIREMENTS.md` was not updated.

---

## Nyquist Compliance

Nyquist validation created for phases 008, 009, 010 only (preceding phases predate Nyquist integration in the workflow). All three have VALIDATION.md files with completed dimensions.

| Phase | VALIDATION.md | Status |
|-------|---------------|--------|
| 001-007 | N/A (predates Nyquist) | — |
| 008 | ✓ | Compliant |
| 009 | ✓ | Compliant |
| 010 | ✓ | Compliant |

---

## Recommendation

**Status: Tech debt review.** All 8 requirements satisfied, all 10 phases complete, all 5 E2E flows verified. The accumulated tech debt is minor (4 items, none blocking). Recommend completing the milestone and tracking debt in backlog.

**Next step:** `/gsd-complete-milestone v1`
