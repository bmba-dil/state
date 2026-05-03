---
phase: 021-first-run-import-opencode-local
reviewed: 2026-05-01T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/state_core/auth/__init__.py
  - src/state_core/auth/import_opencode.py
  - src/state_core/schema.py
  - src/state_daemon/orchestrator.py
  - tests/auth/test_import_graph.py
  - tests/auth/test_import_opencode.py
  - tests/test_orchestrator_import_opencode.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 021: Code Review Report

**Reviewed:** 2026-05-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 021 implements the first-run import from opencode's `auth.json` into state's vault. The implementation is solid: cardinal rules (determinism, mode isolation, secret hygiene, all-or-nothing transactional, P1-7 array preservation) are well-enforced by both code and tests. The schema addition (`AuthImportedData` / `AuthImportedEvent` / extended `AUTH_EVENT_TYPES`) is consistent with existing patterns. Wave 1 RED tests are now GREEN with thorough coverage including a hypothesis property test and an AST-level determinism scan.

The findings below are mostly correctness gaps around log/return-value contracts, an inconsistent orchestrator log line, and one test-spec mismatch that may not be exercising what its docstring claims.

No critical issues. Three warnings concern observable behavior contracts (return-type inconsistency between docstring/wiring, log key mismatch, and a fragile AST walker in tests). Five info items concern minor code quality / unused imports / missing-but-harmless cases.

## Warnings

### WR-01: Orchestrator passes coroutine return value to a `count` log key but the importer returns `list[Credential]`

**File:** `src/state_daemon/orchestrator.py:59-63`
**Issue:** The orchestrator does `imported_count = await import_from_opencode(...)` and logs `count=imported_count`, but `import_from_opencode` is annotated to return `list[Credential]` (see `src/state_core/auth/import_opencode.py:393`, `:509`). The variable name and the `count=` log key both imply an int, but the runtime value is a list. Structlog will render the entire list (which contains `Credential` objects whose `__repr__` may carry secret fields if any defaults change) into the log line. The Phase 020 redactor is the second line of defense, but the contract here is brittle: a future `Credential.__repr__` change or addition of `__str__` could leak access/refresh/key bytes into the unredacted in-memory log payload.

The `if imported_count:` truthiness check happens to work for both `[]` and `[c1, c2]`, masking the bug. The integration test (`test_orchestrator_runs_importer_after_redactor_selfcheck`) sets `mock_importer.return_value = 0`, which is what the orchestrator was apparently written against — but the importer never returns an int.

**Fix:**
```python
imported = await import_from_opencode(store=store, mirror=mirror)
if imported:
    log.info("startup: opencode importer added credentials", count=len(imported))
else:
    log.info("startup: opencode importer no-op")
```
Update `test_orchestrator_runs_importer_after_redactor_selfcheck` to set `mock_importer.return_value = []` so the type contract is enforced.

### WR-02: `auth.import.unreadable` log path on JSONDecodeError omits the `path` field that the disk-read variant supplies

**File:** `src/state_core/auth/import_opencode.py:454-463`
**Issue:** When `path.read_bytes()` fails (PermissionError/OSError), the WARN log includes `path=str(path)` (line 442). When `orjson.JSONDecodeError` fires, the same `auth.import.unreadable` event is logged at line 459-462 but WITHOUT the `path` field — only `reason=type(e).__name__`. Operators reading the journal will see one half of the same event with path context and the other half without, making it harder to identify which opencode install corrupted. Worse, when the corrupt-content path is taken via `env_inline` (no path resolved), there is no path to log at all, so the contract should explicitly distinguish source.

Additionally, IMPORT-06's test (`test_unreadable_file_warn_and_continue`) asserts on `log_level == "warning"` OR `"unreadable" in event` — the OR weakens the coverage so the missing-path field goes uncaught.

**Fix:**
```python
except orjson.JSONDecodeError as e:
    log.warning(
        "auth.import.unreadable",
        reason=type(e).__name__,
        source=str(path) if env_content is not None and 'path' in dir() else "env_inline",
    )
    return []
```
Or thread the source through more cleanly by capturing it in a local variable at the top of the function.

### WR-03: The AST-based determinism scan in `test_importer_does_not_call_time_or_datetime_now` does not actually detect `time.time()` / `datetime.now()` calls

**File:** `tests/auth/test_import_opencode.py:592-614`
**Issue:** The walker only inspects `ast.Attribute` nodes and computes `full = f"{base}.{node.attr}"` where `base` is `node.value.id`. This catches `time.time` (the attribute access) only when written as `time.time` — but for `datetime.now()` written as `datetime.datetime.now()`, the chain is nested `Attribute(value=Attribute(value=Name('datetime'), attr='datetime'), attr='now')` — `node.value` is an `Attribute` with no `.id`, the fallback `getattr(getattr(node.value, "attr", None), "__class__", type(None)).__name__` returns the string `"str"` (since `node.value.attr` is the string `'datetime'`), producing `full = "str.now"` which is not in the banned set. The test would pass even if `datetime.datetime.now()` were present in the source.

It also won't catch `from datetime import datetime` followed by `datetime.now()` — the `Attribute` would have `node.value.id == "datetime"` and `node.attr == "now"` → `"datetime.now"` IS in banned set, so that case works. But aliased imports (`import time as t; t.time()`) and `from time import time; time()` (a `Call` on a bare `Name`) are not detected.

This is a false-negative risk: the test gives confidence that the determinism rule is enforced, but the enforcement is weaker than intended.

**Fix:** Replace the attribute walker with a substring scan plus an `ast.Call` walker that checks function-call targets:
```python
banned_substrs = ("time.time(", "datetime.now(", "datetime.utcnow(", ".utcnow(")
for needle in banned_substrs:
    assert needle not in src, f"determinism violation: {needle} in import_opencode.py"
# Belt-and-suspenders AST check for `from time import time; time()` and aliases:
banned_names = {"time", "now", "utcnow"}
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module in {"time", "datetime"}:
        for alias in node.names:
            assert alias.name not in banned_names, (
                f"determinism violation: from {node.module} import {alias.name}"
            )
```

## Info

### IN-01: `Path` and `pathlib` both imported in test scaffold

**File:** `tests/auth/test_import_opencode.py:51-53`
**Issue:** The file imports both `pathlib` (line 52) and `from pathlib import Path` (line 53). Both are used (`pathlib.Path(__file__)...` at line 504 and 597; `Path` as a type hint at line 135 etc.). Not a bug, but stylistically inconsistent — pick one.
**Fix:** Standardize on `from pathlib import Path` and use `Path(__file__).parent.parent.parent / "src" / ...` consistently.

### IN-02: Unused import `AuthImportedEvent` in test file

**File:** `tests/auth/test_import_opencode.py:71`
**Issue:** `from state_core.schema import AuthImportedData, AuthImportedEvent` — only `AuthImportedData` is used in this file. `AuthImportedEvent` is imported but never referenced.
**Fix:** Remove `AuthImportedEvent` from the import, or add an event-construction smoke test that uses it.

### IN-03: `ApiKeyCredential` and `OAuthCredential` imported with re-exports under `_API_KEY_REGISTRY`

**File:** `src/state_core/auth/import_opencode.py:51-56`
**Issue:** The importer reaches into a private symbol `_REGISTRY` from `state_core.auth.providers.api_key` (line 56) using a private-prefixed import alias. While this is the intended way to access the known-provider list (per the `_KNOWN_PROVIDER_IDS` construction at line 91-93), reaching into `_REGISTRY` from a sibling submodule creates an undocumented coupling: any rename inside `providers/api_key.py` silently breaks the importer. The Phase 018 contract documented in `__init__.py:11-12` explicitly says providers/* are accessed via the dispatcher.

**Fix:** Expose a public `KNOWN_API_KEY_PROVIDERS: frozenset[str]` constant in `providers/api_key.py` (or in `loader.py`) and import that. Or move `_KNOWN_PROVIDER_IDS` into a small public helper in `state_core.auth.providers.api_key` to centralize the contract.

### IN-04: `existing_vault` parameter on `import_from_opencode` is documented but ignored on the disk-read path

**File:** `src/state_core/auth/import_opencode.py:475-476`
**Issue:** The docstring at line 398-401 says "If None, the importer loads via get_auth_json_path() when a vault write is needed." But the code at line 475-476 unconditionally calls `load_vault(target_path)` whenever `existing_vault is None` AND there are candidates — which means tests that pass `existing_vault=None` rely on the daemon's `STATE_AUTH_JSON` env var being set. The IMPORT-06 / IMPORT-26 test bodies (line 209-211, 626-629) call with `existing_vault=None` while only setting `STATE_OPENCODE_AUTH_PATH` — these tests work only because the file is absent so we never reach the `load_vault` call. If a future refactor adds candidates before file checks, those tests would silently pollute the developer's real `~/.state/auth.json`.

**Fix:** Add an early-return check after `if not candidates:` (line 469) that's already present, but document the dependency clearly. Alternatively, in tests always set `STATE_AUTH_JSON` to a tmp path even when expecting no-op behavior. The IMPORT-22/IMPORT-23 test bodies do this correctly via `auth_json_path` fixture; IMPORT-05/IMPORT-06/IMPORT-26 do not.

### IN-05: Magic constant `_IDENTITY_PREFIX_LEN = 12` not validated against minimum credential length

**File:** `src/state_core/auth/import_opencode.py:72, 259-262`
**Issue:** `_identity()` returns `secret[:12]`. If an opencode entry contained a `key` of length < 12 (e.g., `"k"` in the IMPORT-01 test fixture at line 142), the prefix becomes the entire string, which is fine but means a 1-character key and a 5-character key starting with the same character collide as the same identity. This is unreachable in practice (real API keys / OAuth tokens are 30+ chars), and the IMPORT-01 fixture is just exercising the env-var path. Not a bug, but the hypothesis test at line 425-444 generates keys with `min_size=20` (`f"sk-TEST-CANARY-{'x' * (20 + i)}"`) — consider tightening `_OpencodeApiEntry.key` with `min_length=12` if opencode's contract supports it, or document that short keys may collide.

**Fix:** Either add `Field(min_length=12)` to `_OpencodeApiEntry.key` / `_OpencodeOauthEntry.access` and `.refresh`, or add a comment at line 72 noting the assumption.

---

_Reviewed: 2026-05-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
