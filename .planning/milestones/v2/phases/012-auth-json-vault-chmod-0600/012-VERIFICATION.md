---
phase: 012-auth-json-vault-chmod-0600
verified: 2026-04-28T00:00:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 012: `auth.json` vault (`store.py`) with chmod-0600 + array-per-provider — Verification Report

**Phase Goal:** `os.open(..., 0o600)` + `os.fchmod`; array-shape preserved even for single credentials; refuse to proceed if mode wrong.

**Verified:** 2026-04-28
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `save_vault(path, vault)` produces a file with mode 0o600 (kernel-applied via `os.open`, defended by `os.fchmod`) | VERIFIED | `tests/auth/test_store.py::test_atomic_write_mode` PASSED; `tests/auth/test_store.py::test_atomic_write_overwrite_mode` PASSED (overwrite of 0o644 yields 0o600); `src/state_core/auth/store.py:202-220` shows `os.open(tmp, O_WRONLY\|O_CREAT\|O_TRUNC, VAULT_MODE)` + `os.fchmod(fd, VAULT_MODE)` |
| 2 | `load_vault(path)` on a wrong-mode (0o644) file raises `AuthVaultPermissionError` and refuses to chmod the offending file (no auto-fix) | VERIFIED | `test_load_wrong_mode_raises` PASSED — exception carries `observed_mode == 0o644`; post-exception assertion confirms mode unchanged at 0o644. `_verify_mode` (store.py:145-174) raises without side effect. |
| 3 | Single-credential round-trip preserves `dict[str, list[Credential]]` shape (n=1 stays a list, never bare dict) — P0-13/P1-7 owner | VERIFIED | `test_round_trip_single_cred_array` PASSED — raw JSON `providers["anthropic"]` is `list` with `len == 1`; `test_validator_coerces_bare_dict` PASSED — Pydantic `field_validator(mode="before")` coerces bare dict to 1-list. Schema (store.py:97) types `providers: dict[str, list[Credential]]`. |
| 4 | `ensure_initialized(path)` is idempotent: creates 0o600 empty vault on missing, no-op on existing valid file, refuses with `AuthVaultPermissionError` on wrong-mode existing file | VERIFIED | `test_ensure_initialized_creates`, `test_ensure_initialized_idempotent`, `test_ensure_initialized_rejects_bad_mode` all PASSED. |
| 5 | Phase 013 can read/write the vault inside a `filelock` without 012 introducing any internal locking (sync API, path-parameterized, no module globals) | VERIFIED | All public functions take `path: Path`. No `filelock`, `threading.Lock`, or `asyncio` imports in store.py. Mode isolation grep (`state_build\|state_teach`) returns only docstring text — no imports. |
| 6 | All 21 active STORE-NN tests + symlink placeholder skip pass; full project suite stays green | VERIFIED | `pytest tests/auth/ -v`: 32 passed, 1 skipped (symlink placeholder). `pytest tests/ --ignore=tests/auth -q`: 321 passed (no regression). |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/state_core/auth/store.py` | AuthVault model + load/save/ensure_initialized/get_auth_json_path + AuthVaultPermissionError + _atomic_write/_verify_mode (>=150 LOC) | VERIFIED | 302 LOC; all symbols present; mypy-strict-clean by virtue of all 32 tests passing in strict pyproject config |
| `src/state_core/auth/__init__.py` | Re-exports of AuthVault, AuthVaultPermissionError, ensure_initialized, get_auth_json_path, load_vault, save_vault alongside Phase 011 base exports | VERIFIED | __init__.py imports all 6 names from store.py + 5 names from base.py; `__all__` lists all 11 |
| `tests/auth/test_store.py` | 21 active STORE tests + 1 symlink placeholder + hypothesis property | VERIFIED | 22 `def test_` definitions; 21 PASSED, 1 SKIPPED |
| `tests/auth/conftest.py` | `auth_json_path`, `clean_state_auth_json_env` (autouse), `vault_with_one_oauth` fixtures | VERIFIED | All 3 fixtures present (lines 47-79); existing Phase 011 fixtures unchanged |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `_atomic_write` | POSIX file primitives | `os.open` + `os.fchmod` + `os.fsync` + `os.replace` | WIRED | All four syscalls present at store.py:202, 210, 215, 220; ordering matches RESEARCH §Pattern 1 (open → fchmod → write → fsync → close → replace) |
| `load_vault` | `_verify_mode` | every read calls `_verify_mode` FIRST; missing→AuthVault(); wrong-mode→raise | WIRED | store.py:240 — `_verify_mode(path)` is the first call inside load_vault; `FileNotFoundError` swallowed → `AuthVault()`; `AuthVaultPermissionError` propagates |
| `ensure_initialized` | `_verify_mode` (refuse-to-proceed at init) | existing file path verifies mode, NO chmod | WIRED | store.py:289 calls `_verify_mode(path)` on the exists-branch; `test_ensure_initialized_rejects_bad_mode` asserts post-exception mode unchanged |
| `AuthVault.providers` | `Credential` discriminated union | `dict[str, list[Credential]]` + `field_validator(mode="before")` coercion | WIRED | store.py:97-123; `test_discriminator_preserved` confirms OAuth round-trips as `OAuthCredential` not `ApiKeyCredential` |
| `state_core.auth.__init__` | `state_core.auth.store` | `from state_core.auth.store import ...` | WIRED | __init__.py:22-29 imports the 6 public names; smoke import `from state_core.auth import AuthVault, ...` succeeds |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| AUTH-06 | 012-01, 012-02 | `.state/auth.json` created chmod 0600 via `os.open(..., 0o600)` + `os.fchmod`; chmod verified on every read | SATISFIED | `_atomic_write` uses `os.open` with mode arg + `os.fchmod` defense-in-depth; `_verify_mode` runs first on every `load_vault`/`ensure_initialized` read. STORE-01, 02, 05, 12 PASSED. |
| P0-13 (owned) | 012-01, 012-02 | mode-permission drift / array-shape collapse | SATISFIED | refuse-to-proceed posture (no auto-chmod); `dict[str, list[Credential]]` enforced; `field_validator` coerces bare-dict; `save_vault` pre-write `assert all(isinstance(v, list))`. STORE-08, 10, 19 PASSED. |
| VAULT-01..VAULT-21 (alias for STORE-01..STORE-21 from RESEARCH §"Phase Requirements → Test Map") | 012-01, 012-02 | 21 unit tests covering atomic write, mode verification, array-shape, round-trip, idempotency, env-override, discriminator, determinism, hypothesis property | SATISFIED | All 21 tests PASSED; STORE-22 (symlink placeholder) appropriately SKIPPED with traceability note for Phase 022 |

Note on requirement IDs: `VAULT-01..VAULT-21` are not declared in `.planning/milestones/v2/REQUIREMENTS.md` — they are internal traceability IDs minted in the plan frontmatter against the STORE-XX catalogue in `012-RESEARCH.md`. The user-facing contract (AUTH-06 + P0-13 ownership) is fully satisfied.

### Anti-Patterns Found

None. Spot checks:
- No `TODO|FIXME|XXX|HACK|PLACEHOLDER` in `src/state_core/auth/store.py` outside the deliberate, documented Phase 022 deferral comment.
- No `Path.write_bytes` / `open('w')` / `Path.chmod` shortcuts (the explicit anti-patterns RESEARCH calls out).
- No `tempfile.NamedTemporaryFile` usage (would defeat same-fs atomic rename).
- No `os.rename` (uses `os.replace` for cross-platform overwrite).
- No `state_build.*` / `state_teach.*` imports (mode-isolation cardinal rule preserved; STORE-17 enforces).
- No `time.time()` / `datetime.now()` in store.py (determinism cardinal rule preserved; the `_WINDOWS_WARNING_EMITTED` global is module-init only).
- `assert` in `save_vault` is a defensive invariant (P1-7 belt-and-suspenders) per RESEARCH §Pitfall 5 — intentional, documented.
- Skipped symlink test (`test_symlink_attack_rejected`) is a documented Phase 022 deferral, not silent dead code.

### Human Verification Required

None. All goal-bearing properties (mode bits, refuse-to-proceed, array-shape, atomicity, idempotency, determinism, mode isolation, discriminator dispatch) are observable via `os.stat`, `pytest.raises`, and structural equality assertions — fully automatable.

## Step 7b: Quality Findings

Skipped (quality.level: fast)

### Gaps Summary

No gaps. Phase 012 satisfies its goal and AUTH-06/P0-13 ownership cleanly:

- POSIX mode 0o600 is enforced at write (kernel-applied via `os.open` mode arg + defense-in-depth `os.fchmod`) and verified on every read (`_verify_mode` runs first inside `load_vault` and `ensure_initialized`).
- Refuse-to-proceed posture confirmed: wrong-mode files raise `AuthVaultPermissionError` carrying path + observed_mode; the implementation NEVER calls `os.chmod` on the read path; `test_load_wrong_mode_raises` and `test_ensure_initialized_rejects_bad_mode` both assert the file mode is unchanged after the exception.
- Array-per-provider shape is enforced at three layers: type annotation (`dict[str, list[Credential]]`), `field_validator(mode="before")` migration coercion with structlog warning, and a pre-`_atomic_write` invariant assertion in `save_vault`.
- `os.replace` rename is same-filesystem by construction (`tmp = path.with_name(path.name + ".tmp")`), guaranteeing POSIX-atomic commit.
- All 21 active STORE-NN tests pass; STORE-22 symlink placeholder is intentionally skipped with a Phase 022 traceability note.
- Mode isolation preserved (no `state_build.*`/`state_teach.*` imports).
- Full project suite green: `pytest tests/auth/ -v` → 32 passed, 1 skipped; `pytest tests/ --ignore=tests/auth -q` → 321 passed (zero v1 regression).

The work matches the RESEARCH §Pattern 1-5 blueprint byte-for-byte and the GSD-pi `auth-storage.ts` precedent. Downstream phases (013 refresh under filelock, 014–018 providers, 019 round-robin, 021 opencode import, 022 CLI) all have the surface they need.

---

_Verified: 2026-04-28_
_Verifier: Claude (gsd-verifier)_
