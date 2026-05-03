---
phase: 018-plain-api-key-vault
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/state_core/auth/providers/api_key.py
  - src/state_core/auth/loader.py
  - src/state_core/auth/errors.py
  - src/state_core/auth/__init__.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues
---

# Phase 018 — Code Review Report

**Reviewed:** 2026-04-30
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found (no critical issues; 2 minor warnings + 4 info notes)

## Summary

Phase 018 ships the plain-api-key vault: a registry-driven `PlainApiKeyAuth`
(607 LOC) covering 12 vendors and a single-function loader (`load_credentials`,
169 LOC) that fuses Phase 012's vault round-trip with the canonical env-var
table. Plus a small `UnknownApiKeyProviderError` addition to `auth/errors.py`
and a re-export in `auth/__init__.py`.

Code quality is high. The phase's own threat model (T-018-1 through T-018-10)
is comprehensively addressed in code, with provenance comments, deterministic
behavior, and explicit one-way import edges. Secret-handling matches project
cardinal rules: `ApiKeyCredential.key` is `Field(repr=False)`, the prefix-
mismatch warning logs only `key[:8]`, the unknown-provider error carries no
key bytes, and login uses getpass on TTY / stdin on non-TTY (no argv leak).
File-mode 0600 is correctly delegated to Phase 012's `save_vault` /
`ensure_initialized`. Mode isolation (no `state.build.*` / `state.teach.*`
imports) holds. Determinism rules hold (no `datetime.now()` / `time.time()`).

Two minor warnings (one race condition in `_main()` persistence, one
unused-import / re-export hygiene issue) and four info-level observations
(documentation drift, defensive guards) are recorded below. None block
landing; all are minor maintainability items that can be addressed in
Phase 022 when the production CLI replaces the smoke surface.

## Warnings

### WR-01: Race window between `load_vault` and `save_vault` in `_main()` login persistence

**File:** `src/state_core/auth/providers/api_key.py:562-578`
**Issue:** The `_main()` login subcommand does
`load_vault → mutate bucket → save_vault` without holding any inter-process
lock. If two `python -m state_core.auth.providers.api_key login <pid>`
invocations race (or the user runs login while the daemon is also writing),
the second writer's `save_vault` overwrites the first's bucket additions
with a stale snapshot — silent credential loss. T-018-8 (vault-file race)
is explicitly tracked as DEFERRED to Phase 022 per the Plan-02 SUMMARY,
which makes this a known-deferred issue rather than a surprise bug. But
the smoke surface is reachable today via `python3 -m
state_core.auth.providers.api_key login ...` and a user re-running login
(append-default) is not unusual.

**Fix:** Either (a) wrap the read-mutate-write block in a `filelock.FileLock`
sibling-file (matching Phase 013's `RefreshLockTimeout` pattern; `filelock`
is already in the stack pin) — minimal diff, ~6 lines; or (b) leave as-is
and add a `WARNING: smoke surface only — no concurrent-write protection;
use the Phase 022 CLI for production.` banner above the
`if args.cmd == "login":` block to document the constraint inline so a
future reader doesn't ship this as production. Option (b) is the lower-cost
choice given the explicit DEFERRED tag in the threat model.

```python
# Option (b) — minimal documentary fix
if args.cmd == "login":
    # NOTE: smoke surface only — no concurrent-write protection between
    # load_vault and save_vault. T-018-8 deferred to Phase 022's CLI which
    # owns filelock.FileLock around the read-mutate-write block.
    try:
        ...
```

### WR-02: `AuthVaultPermissionError` import in `loader.py` is `noqa: F401` "for caller convenience" but is not actually re-exported

**File:** `src/state_core/auth/loader.py:71-75`
**Issue:** The import comment claims `AuthVaultPermissionError` is
"re-exported for caller convenience", but the module's `__all__` only lists
`["load_credentials"]` (line 169). `from state_core.auth.loader import
AuthVaultPermissionError` would still work due to Python's lax module-level
attribute exposure, but it is a misleading no-op annotation: the symbol is
imported into the module's namespace but is not part of its declared public
API and is NOT what callers should import. The proper consumer source is
`from state_core.auth import AuthVaultPermissionError` (already in
`__init__.py:34`) or `from state_core.auth.store import
AuthVaultPermissionError`.

**Fix:** Remove the unused import to avoid implying a non-existent re-export
contract, OR add the symbol to `__all__` if the re-export is genuinely
intended:

```python
# loader.py:71-75 — remove the line:
from state_core.auth.store import (
    get_auth_json_path,
    load_vault,
)
```

The docstring already documents `Raises: AuthVaultPermissionError` so the
type is discoverable; callers import it from `state_core.auth.store` or
`state_core.auth` (the package re-export) per existing convention.

## Info

### IN-01: `AuthMethod` and `AuthError` imported into `api_key.py` only as `noqa: F401`

**File:** `src/state_core/auth/providers/api_key.py:89, 93`
**Issue:** Both `AuthMethod` (Protocol) and `AuthError` (base class) are
imported with `noqa: F401` justifications. `AuthMethod` is used as the
declared return type of `get_api_key_auth` (`-> AuthMethod`, line 425) so
its import is genuinely required at type-check time and the F401 silence
is fine — the comment "runtime_checkable Protocol; isinstance check in
tests" is correct but understates that the symbol is also a return-type
annotation. `AuthError`, by contrast, is purely re-export symmetry — never
referenced in the module body. The "Phase 022 catches AuthError broadly"
justification is reasonable but would be cleaner if exposed via `__all__`
rather than a hidden re-export.
**Fix:** Either add `AuthError` to `__all__` (line 600) so the re-export
is part of the declared API, or drop the import entirely and let consumers
import from `state_core.auth.errors` directly. No functional impact either
way.

### IN-02: `print = print` rebind is non-idiomatic and triggers `noqa: A001`

**File:** `src/state_core/auth/providers/api_key.py:82`
**Issue:** The shadowing of the builtin `print` with itself (`print = print`)
to make it monkeypatch-friendly works but is unusual. The justification
("mirrors anthropic.py / google_gemini.py") is consistent with the
codebase, so this is not a regression. Worth a tracking note for a future
test-infra refactor: a `_print = print` indirection (test patches `_print`,
production calls `_print(...)`) avoids the shadowing of a builtin and the
need for the `noqa: A001`. Defer until Phase 022 unifies the smoke
surfaces.
**Fix:** No change required for Phase 018. Track for Phase 022 cleanup.

### IN-03: `_main()`'s broad `except Exception` swallows specific failure modes

**File:** `src/state_core/auth/providers/api_key.py:579`
**Issue:** The vault-persistence block catches bare `Exception` and prints
a single generic message. This is acceptable for a smoke surface (any
failure surfaces a non-zero exit), but it does conflate distinct failure
modes — e.g., `AuthVaultPermissionError` (security incident — wrong
chmod), disk-full, JSON serialization error, or unexpected `Credential`
subtype. The 018-VALIDATION matrix has no row asserting specific exception
types here, so test coverage doesn't require narrowing.
**Fix:** Phase 022's CLI should differentiate `AuthVaultPermissionError`
(exit 2 + actionable message) from generic write failures. For Phase 018
the broad catch is acceptable.

### IN-04: `loader.py` env-synthesis branch logs at `debug` level; no `info` audit trail for env credential use

**File:** `src/state_core/auth/loader.py:161-165`
**Issue:** When env-synthesis fires, the `loader.env_synthesis` event is
logged at `debug` level. Production observability (Phase 020's redactor
work and the daemon's structlog config) typically filters out `debug`.
This means in production an env-sourced credential will be used silently,
with no `info`-level audit trail showing "fell back to env var X for
provider Y." Given the threat model's emphasis on "vault is the source
of truth", an `info` (or even `warning` on first synthesis per process)
event would make the fallback observable in real-world logs.
**Fix:** Consider promoting to `log.info(...)` for the env_synthesis event
(the env_var name is non-secret; only the key itself is sensitive and is
not logged). Alternatively add a process-lifetime `_synthesized_once`
guard that logs `warning` once per provider per process. Defer to Phase
020 / Phase 022 — Phase 018 baseline is correct.

---

## Cardinal-Rule Spot Check (all PASS)

| Rule | File | Status |
|---|---|---|
| Mode isolation: no `state.build.*` / `state.teach.*` imports | both | PASS |
| Mode isolation: api_key.py has no module-scope import of loader | api_key.py | PASS (line 98-103 explicit comment + import-graph test) |
| Mode isolation: loader.py imports only allowed targets | loader.py | PASS (`base, store, providers.api_key, errors` only) |
| Determinism: no `datetime.now()` / `time.time()` | both | PASS (is_expired takes `now` as parameter) |
| Secret hygiene: `Field(repr=False)` on `ApiKeyCredential.key` | base.py (Phase 011) | PASS |
| Secret hygiene: argparse exposes no `--api-key` flag | api_key.py:485-526 | PASS |
| Secret hygiene: prefix-mismatch warning logs `key[:8]` only | api_key.py:300-305 | PASS |
| Secret hygiene: `UnknownApiKeyProviderError` carries `provider_id` only | errors.py:91-93 | PASS |
| Secret hygiene: `_validate_format` uses generic message | api_key.py:283 | PASS |
| chmod 0600: delegated to Phase 012 `save_vault` / `ensure_initialized` | api_key.py:560-578 | PASS (inherited) |
| Input validation: empty/whitespace key rejected | api_key.py:282-283 | PASS |
| Input validation: empty/whitespace env var treated as unset | loader.py:142-143 | PASS |
| Per-call factory (no module singletons except `_REGISTRY`) | api_key.py:425-441 | PASS |
| Provenance comments above each `_REGISTRY` row | api_key.py:141, 152, 160, 174, 185, 193, 201, 213, 221, 229, 237, 250 | PASS (12/12) |
| `__all__` declared in both modules | api_key.py:600-607, loader.py:169 | PASS |

## Security Spot Check (all PASS)

- No hardcoded secrets — `_REGISTRY` contains no API keys; just env-var
  names and prefix strings.
- No `eval()` / `exec()` / `os.system()` / `subprocess` use.
- No SQL / shell injection surfaces (no DB / shell calls in either file).
- No path traversal — vault path is resolved via `get_auth_json_path()`
  (Phase 012 owned).
- No insecure crypto (no crypto in this phase; AES-encrypted vault is a
  deliberate non-goal per Phase 012 / Phase 022 deferred tag).
- argparse `choices=sorted(_REGISTRY.keys())` constrains the
  `provider_id` to known providers — no spoofing.
- KeyboardInterrupt cleanly returns 130 (no key bytes in the cancellation
  path).
- `value_template.format(key=cred.key)` (line 366) is safe — only
  `{key}` placeholder; `_REGISTRY` is module-private and only contains
  values authored in this file.

## No-Regression Confirmation

Per 018-03-SUMMARY.md verification output:
- `pytest tests/auth/ -q` → 291 passed, 1 skipped (the skip is the
  Phase 012 symlink-attack placeholder, tracked as T-018-9 deferred).
- All 21 VALIDATION rows GREEN.
- Both directions of the import-graph constraint (T-018-7) GREEN.

---

_Reviewed: 2026-04-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
