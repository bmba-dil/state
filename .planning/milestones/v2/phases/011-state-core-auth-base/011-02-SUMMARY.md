---
phase: 011-state-core-auth-base
plan: 02
subsystem: state_core.auth
tags: [auth, base, m-a2, base-01..base-11, green, pydantic, protocol, oauth, api-key]
backfilled: 2026-05-02
backfill_reason: "Executor consolidated 011-02 GREEN write-up into 011-VERIFICATION.md at completion time. Backfilled at v2 milestone close for archive traceability."
canonical_record: 011-VERIFICATION.md
dependency-graph:
  requires:
    - 011-01 (BASE-01..BASE-11 RED stubs + fixtures)
  provides:
    - state_core.auth.base.OAuthCredential
    - state_core.auth.base.ApiKeyCredential
    - state_core.auth.base.Credential (discriminated-union alias)
    - state_core.auth.base.CredentialAdapter (pydantic.TypeAdapter)
    - state_core.auth.base.AuthMethod (runtime_checkable Protocol)
    - state_core.auth (package re-exports the 5-symbol public surface)
  affects:
    - 012 vault, 013 refresh, 014–018 providers, 019 round-robin, 020 redactor, 021 importer, 022 CLI (every downstream phase consumes this contract)
tech-stack:
  added:
    - pydantic 2.x discriminated unions (Credential = OAuthCredential | ApiKeyCredential)
  patterns:
    - "Field(repr=False) on access/refresh/key — secret-redaction at the type-system level"
    - "Wire-shape `expires` round-trips unchanged — buffer enforcement delegated to AuthMethod.is_expired (Phase 014+)"
    - "Mode isolation enforced: state_core.auth.base imports do NOT pull state_build.* / state_teach.* into sys.modules"
metrics:
  tasks_completed: 1
  red_tests_driven_green: 11
  files_created: 1
  files_modified: 1
  full_auth_suite: "11 passed in 0.08s (Phase 011 only; suite grows in 012+)"
---

# Phase 011 Plan 02: BASE-XX Implementation (GREEN) Summary

**Scope.** Implement `state_core.auth.base` (5 symbols: `OAuthCredential`, `ApiKeyCredential`, `Credential` alias, `CredentialAdapter`, `AuthMethod` Protocol) + re-export through `state_core.auth.__init__`. Drive Plan 01's 11 BASE-XX RED stubs to GREEN.

**Outcome.** All 11 BASE-XX truths VERIFIED, mypy --strict clean, repr-redaction enforced, deterministic serialization confirmed. Phase 011 is the contract every downstream auth phase consumes.

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/state_core/auth/base.py` | 221 | `OAuthCredential`, `ApiKeyCredential`, `Credential`, `CredentialAdapter`, `AuthMethod` |
| `src/state_core/auth/__init__.py` | 29 | Absolute-import re-export of the 5-symbol public surface |

## Backfill Note

The original execution session merged Plan 02's GREEN write-up into the phase-level `011-VERIFICATION.md` (which records 11/11 truths VERIFIED with full evidence). This SUMMARY is a thin backfill authored at v2 milestone close. **For full execution detail, plan-level evidence, and verification scoring, read `011-VERIFICATION.md`.**
