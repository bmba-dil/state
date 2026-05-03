---
phase: 019-multi-cred-round-robin-across
plan: 02
subsystem: auth
tags: [auth, errors, refresh, wave-2, multi-cred, AUTH-08]
dependency_graph:
  requires:
    - "Phase 011 — state_core.auth.base (AuthError, AuthMethod, Credential)"
    - "Phase 013 — state_core.auth.refresh (_new_async_lock, _lock_path_for, RefreshLockTimeout)"
    - "Phase 015 — state_core.auth.errors (promoted exception module — UnknownApiKeyProviderError already lives here)"
    - "Wave 1 (Plan 01) — tests/auth/test_rotation.py RED scaffolding committed (depends on these surface symbols at import time)"
  provides:
    - "state_core.auth.errors.NoCredentialsAvailableError — AuthError subclass with provider_id, reason, earliest_available_at attributes"
    - "state_core.auth.refresh.new_async_lock — public alias of canonical _new_async_lock (timeout=10.0, thread_local=False, poll_interval=0.05)"
  affects:
    - "Plan 03 (Wave 3) — state_core/auth/rotation.py imports both new symbols"
    - "Plan 04 (Wave 4) — state_core/auth/__init__.py re-exports NoCredentialsAvailableError"
    - "ROTATE-02, ROTATE-03, ROTATE-09, ROTATE-26 — Wave 0 RED rows partially advance at import resolution"
tech-stack:
  added: []
  patterns:
    - "Pure-Python public-alias promotion (`public_name = _private_name`) — single source of truth, zero behavioral divergence"
    - "Keyword-only constructor args via `*` separator — enforces caller intent for non-positional safety-critical parameters (T-019-3 mitigation by signature)"
key-files:
  created: []
  modified:
    - "src/state_core/auth/errors.py — appended NoCredentialsAvailableError class (~50 LOC including docstring), added to __all__"
    - "src/state_core/auth/refresh.py — added `new_async_lock = _new_async_lock` alias (1 line + 10-line WARNING comment), appended to __all__"
    - "tests/auth/test_errors.py — extended exact-match __all__ assertion in test_errors_module_exports to include NoCredentialsAvailableError (Rule 1 deviation — pre-existing pinned test)"
decisions:
  - "Keep `_new_async_lock` as canonical name + add `new_async_lock = _new_async_lock` alias (rather than rename + add underscore alias) — zero edits to Phase 013 internal call sites; Pitfall 6 WARNING reproduced on the public alias only since private name is documented module-internal"
  - "Update tests/auth/test_errors.py instead of relaxing the exact-match assertion — the pinned __all__ is a contract; extending it is the correct response to Phase 019's surface addition"
  - "errors.py keeps stdlib-only imports invariant (cardinal rule from Phase 011) — NoCredentialsAvailableError uses only `Exception`, `str`, `float | None` (built-ins); zero new import lines"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-01T02:11:32Z"
---

# Phase 019 Plan 02: Wave 2 Surface Prep (errors + refresh) Summary

Add `NoCredentialsAvailableError` to `state_core.auth.errors` and promote `_new_async_lock` to public `new_async_lock` alias in `state_core.auth.refresh` — the two external surface dependencies that Plan 03's `rotation.py` imports. Both edits are tiny, additive, and preserve existing call sites byte-for-byte.

## What Shipped

### Edit 1 — `src/state_core/auth/errors.py` (+50 LOC)

New class appended after `UnknownApiKeyProviderError`:

```python
class NoCredentialsAvailableError(AuthError):
    def __init__(
        self,
        provider_id: str,
        *,
        reason: str,
        earliest_available_at: float | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.reason = reason
        self.earliest_available_at = earliest_available_at
        msg = f"No credential available for {provider_id!r} (reason={reason})"
        if earliest_available_at is not None:
            msg += f", earliest at epoch={earliest_available_at}"
        super().__init__(msg)
```

`__all__` extended in alphabetical order:
```python
__all__ = [
    "AuthError",
    "AuthLoginError",
    "AuthRefreshError",
    "NoCredentialsAvailableError",   # new
    "UnknownApiKeyProviderError",
]
```

T-019-3 mitigation enforced **by signature**: the constructor accepts only `provider_id` (public string), `reason` (constrained string — `"empty"` | `"all_cooled_down"`), and `earliest_available_at` (float | None). It physically cannot accept any credential bytes — there is no parameter to receive them. The `!r` format is on `provider_id` (a public string), never on `cred`.

### Edit 2 — `src/state_core/auth/refresh.py` (+14 LOC: 1 alias line + 10-line WARNING comment + 1 `__all__` entry)

Public alias added immediately after the canonical private function:

```python
new_async_lock = _new_async_lock
```

with a WARNING block reproducing Pitfall 6 (REFRESH-27 — reentrant deadlock at the 10s acquire timeout). `__all__` extended to include `"new_async_lock"` in alphabetical order.

Phase 013 internal callers (`read_credential`, `refresh_credential` bodies) untouched — they still call `_new_async_lock(...)` by its underscored name. Backward-compat preserved: `from state_core.auth.refresh import _new_async_lock` still works.

### Edit 3 — `tests/auth/test_errors.py` (deviation)

Extended the `test_errors_module_exports` exact-match `__all__` assertion to include `"NoCredentialsAvailableError"` in alphabetical order. Rationale: the existing test pins the `__all__` contract; Phase 019's legitimate surface addition requires the pinned contract to grow.

## Acceptance Criteria — All PASS

### Task 1 (NoCredentialsAvailableError)

| AC | Result |
|----|--------|
| `grep -n "class NoCredentialsAvailableError" src/state_core/auth/errors.py` returns 1 hit | ✓ line 96 |
| `grep -c "NoCredentialsAvailableError" src/state_core/auth/errors.py >= 2` | ✓ 6 hits |
| `grep -nE "^from state_core\.|^import state_core\." src/state_core/auth/errors.py` returns 0 hits (stdlib-only invariant) | ✓ exit 1 (no match) |
| Import smoke (provider_id, reason, earliest_available_at attrs) | ✓ `OK` |
| Leak-free smoke (`sk-` and `Bearer` absent from str) | ✓ `OK leak-free` |
| Keyword-only `reason` enforcement (positional call raises TypeError) | ✓ `TypeError` raised |
| `pytest tests/auth/test_errors.py` | ✓ 6 passed |

### Task 2 (new_async_lock alias)

| AC | Result |
|----|--------|
| `grep -n "^new_async_lock = _new_async_lock" src/state_core/auth/refresh.py` returns 1 hit | ✓ line 142 |
| `grep -n "\"new_async_lock\"" src/state_core/auth/refresh.py` returns 1 hit | ✓ line 329 |
| Alias identity (`new_async_lock is _new_async_lock`) | ✓ `OK` |
| `"new_async_lock" in state_core.auth.refresh.__all__` | ✓ `OK in __all__` |
| Returned-lock timeout is 10.0 | ✓ `OK timeout` |
| `pytest tests/auth/test_refresh.py` (Phase 013 regression) | ✓ 30 passed |

## Pytest Tail (Regression Proof)

```
$ pytest tests/auth/ --ignore=tests/auth/test_rotation.py -q
...
2 failed, 291 passed, 1 skipped in 44.94s
```

The 2 failures are **expected Wave 0 RED placeholders** in `tests/auth/test_import_graph.py` — both fail with the message `"Wave 0 RED: src/state_core/auth/rotation.py does not exist yet"` (the rotation module is Plan 03's responsibility). They are NOT regressions caused by this plan; they were RED before Wave 2 began and remain RED until Plan 03 lands.

Phase 011/012/013/014/015/016/017/018 tests: **all 291 passing**, 1 unchanged skip.

## Smoke Test (Both New Symbols Importable)

```python
from state_core.auth.errors import NoCredentialsAvailableError, AuthError
from state_core.auth.refresh import new_async_lock, _new_async_lock

e = NoCredentialsAvailableError('test', reason='empty')
assert isinstance(e, AuthError)
assert e.provider_id == 'test'
assert e.reason == 'empty'
assert e.earliest_available_at is None

assert new_async_lock is _new_async_lock

print('Wave 2 prep complete')
```

Output: `Wave 2 prep complete`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Pinned test] tests/auth/test_errors.py exact-match `__all__` assertion**

- **Found during:** Task 1 verification (`pytest tests/auth/test_errors.py` failed on `test_errors_module_exports`)
- **Issue:** The existing Phase 015/018 test pins `errors.__all__` to the exact 4-element list `["AuthError", "AuthLoginError", "AuthRefreshError", "UnknownApiKeyProviderError"]`. Phase 019's plan explicitly extends `__all__` with `"NoCredentialsAvailableError"`, invalidating the pin.
- **Fix:** Extended the test's expected list to the 5-element form including `"NoCredentialsAvailableError"` (alphabetical position between `AuthRefreshError` and `UnknownApiKeyProviderError`). Updated the inline comment to reference Phase 019.
- **Files modified:** `tests/auth/test_errors.py` (5 lines)
- **Commit:** `87c34d3` (bundled with Task 1's primary edit)
- **Rationale:** Updating the test is the correct response — the `__all__` pin is a contract that grows with each phase. The alternative (relaxing the assertion to a subset check) would weaken Phase 015's intent of catching accidental `__all__` drift.

### Other Deviations

None. Both surface edits applied exactly as specified in `<action>` blocks.

## Worktree Recovery Notes

The Wave 2 worktree was originally created from a stale base commit. On entry the `worktree_branch_check` step detected the mismatch (`ACTUAL_BASE = 5acaf88...` ≠ `EXPECTED_BASE = 44481e4...`) and the executor:

1. Ran `git reset --soft 44481e4...` to advance HEAD to the correct Wave 1 base.
2. Ran `git checkout HEAD -- .` to restore the working tree (deleted/missing files in the stale worktree were re-materialized from the new HEAD's tree).
3. Verified all Wave 1 RED scaffolding files (`tests/auth/test_rotation.py`, `tests/auth/conftest.py`, `tests/auth/test_import_graph.py` ROTATE-21 rows) were present.

This recovery was transparent and added no commits. The worktree is now at the correct Wave 1 base + the 2 new Wave 2 commits on top.

## Quality Gates

Quality level is `fast` (`.planning/config.json:quality.level == "fast"`). The quality_sentinel was skipped per protocol — no codebase-scan, Context7, baseline, gate, or diff-review steps ran. Smoke and regression tests below substitute for the gate evidence.

## Hand-off — Wave 3 Continuation

**Plan 03 (Wave 3) creates `state_core/auth/rotation.py`** which imports:

```python
from state_core.auth.errors import NoCredentialsAvailableError  # ← this plan provides
from state_core.auth.refresh import new_async_lock              # ← this plan provides
```

When Plan 03 lands:
- ROTATE-02 (`test_select_empty_raises`) — partially GREEN at Wave 2 (import resolves), fully GREEN at Wave 3 (rotation logic implemented)
- ROTATE-03 (`test_select_missing_provider_raises`) — same trajectory
- ROTATE-09 (`test_all_cooled_down_raises_with_earliest`) — same trajectory; the `earliest_available_at` attribute this plan provides is the load-bearing contract
- ROTATE-26 (`test_public_reexports`) — partially GREEN at Wave 2 + Plan 04 (re-exports at `state_core.auth` root)

The `_new_async_lock` private name remains importable for any caller that already depends on it; the public `new_async_lock` is the documented import for new callers (Plan 03's `rotation.py`).

## Commits

| Task | Hash      | Message |
|------|-----------|---------|
| 1    | `87c34d3` | `feat(019-02): add NoCredentialsAvailableError to state_core.auth.errors` |
| 2    | `30efa4f` | `feat(019-02): promote _new_async_lock to public new_async_lock alias` |

## Self-Check: PASSED

**Files claimed created/modified — verification:**

- `src/state_core/auth/errors.py` — FOUND (modified)
- `src/state_core/auth/refresh.py` — FOUND (modified)
- `tests/auth/test_errors.py` — FOUND (modified)
- `.planning/milestones/v2/phases/019-multi-cred-round-robin-across/019-02-SUMMARY.md` — FOUND (this file)

**Commits claimed — verification:**

- `87c34d3` — FOUND (`feat(019-02): add NoCredentialsAvailableError…`)
- `30efa4f` — FOUND (`feat(019-02): promote _new_async_lock to public new_async_lock alias`)

All claims verified.
