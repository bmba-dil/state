---
phase: 012
slug: auth-json-vault-chmod-0600
status: clean
reviewed: 2026-04-28
findings_critical: 0
findings_major: 0
findings_minor: 0
findings_style: 0
---

# Phase 012 — Code Review

**Files reviewed:**
- `src/state_core/auth/store.py` (302 LOC, new)
- `src/state_core/auth/__init__.py` (added 6 re-exports)
- `tests/auth/test_store.py` (480 LOC, 22 stubs)
- `tests/auth/conftest.py` (extended)

## Summary

**Status: CLEAN.** No findings at any severity level.

## Strengths

- **Atomic write sequence is exact.** `os.open(..., O_WRONLY|O_CREAT|O_TRUNC, 0o600)` → `os.fchmod(fd, 0o600)` defense-in-depth → `os.write` → `os.fsync(fd)` → `os.close(fd)` → `os.replace(tmp, target)`. No race window between create and chmod.
- **`_verify_mode` runs first on every read.** Refuses to proceed with `AuthVaultPermissionError` (PermissionError subclass). No auto-fix — security incident is surfaced, not masked. STORE-05 + STORE-12 prove mode is unchanged after exception.
- **Array-per-provider locked at 3 layers.** Pydantic typed annotation + `field_validator(mode="before")` coercion (with structlog warning for migration paths) + pre-write assert in `save_vault`. P1-7 collapse impossible at every entry point.
- **Determinism preserved.** `orjson.OPT_SORT_KEYS | OPT_INDENT_2` for byte-identical writes; STORE-20 round-trip proves it. No `import time` / `from datetime` (callers inject the clock).
- **Mode isolation respected.** Only stdlib + orjson + structlog + pydantic + state_core.auth.base imports. No state_build / state_teach references.
- **Phase 013 lock-friendly API.** All public functions sync, take `path: Path` parameter, no module globals — Phase 013 wraps with filelock.FileLock cleanly.
- **Same-filesystem `.tmp` rename.** Atomic `os.replace` invariant preserved.

## Correctness

No issues. `STATE_AUTH_JSON` env override mirrors `state_core.database.get_db_path()` exactly. Empty-vault case handled (creates `{}` atomically).

## Security

No issues. Defense-in-depth at every boundary: kernel-applied mode (O_CREAT 0o600), redundant `os.fchmod`, read-side verification, refuse-to-proceed posture, no exception leaks of credential text.

Symlink-defense (STORE-22) deliberately skipped — deferred to Phase 022 audit per RESEARCH §Pitfall 6.

## Performance

`TypeAdapter(AuthVault)` pre-built at module import. orjson ~3-5x faster than stdlib json on large vaults (relevant when 12 providers × multi-cred arrays).

## Maintainability

- Naming consistent with `state_core.database` pattern
- Single responsibility: storage layer only — no provider logic, no locking (Phase 013), no logging redaction (Phase 020)
- `__all__` matches public surface

## Notes (non-findings)

- mypy strict on the package emits a `py.typed`-marker warning — pre-existing and project-wide; out of scope.
- `STATE.md` and `ROADMAP.md` not updated (gitignored per `commit_docs=false`); orchestrator handles this.
