---
phase: 013-filelock-guarded-refresh-lock
plan: 01
subsystem: state_core.auth
tags: [auth, refresh, filelock, m-a2, refresh-01..refresh-30, red-tests, scaffold]
backfilled: 2026-05-02
backfill_reason: "Executor consolidated 013-01 RED scaffold write-up into the 013-02 GREEN SUMMARY (which is canonical). Backfilled at v2 milestone close for archive traceability."
canonical_record: 013-02-SUMMARY.md
dependency-graph:
  requires:
    - 011 (Credential, AuthMethod)
    - 012 (AuthVault)
  provides:
    - tests/auth/test_refresh.py (30 RED REFRESH-NN test stubs)
    - tests/auth/conftest.py (Phase 013 fixtures: tmp_vault_with_oauth_cred, frozen_now, lock_path_for, etc.)
    - pyproject.toml (filelock>=3.20.3 declared)
  affects:
    - 013-02 (GREEN — drives 30 REFRESH-NN truths to pass)
metrics:
  tasks_completed: 1
  red_stubs_authored: 30
  files_modified: 3
---

# Phase 013 Plan 01: REFRESH-NN Test Scaffold (RED) Summary

**Scope.** Author the 30 REFRESH-NN RED test stubs in `tests/auth/test_refresh.py` (covers AUTH-07 + AUTH-09: filelock-guarded refresh with 10 s acquire + double-check + 5-min expiry buffer + 15 s outer cap), add Phase 013 fixtures to `tests/auth/conftest.py`, and pin the `filelock>=3.20.3` dependency in `pyproject.toml`.

**Outcome.** All 30 REFRESH-NN stubs landed RED (collection-time `ImportError` on `state_core.auth.refresh`); Plan 02 drove 30/30 GREEN.

## Backfill Note

The full Plan 01→02 narrative (RED scaffold + GREEN implementation) is consolidated in `013-02-SUMMARY.md`. This thin backfill exists at v2 milestone close to maintain a complete plan-summary chain. **For full execution detail and verification evidence, read `013-02-SUMMARY.md` and `013-VERIFICATION.md`.**
