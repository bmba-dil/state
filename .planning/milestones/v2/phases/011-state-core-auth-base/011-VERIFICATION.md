---
phase: 011-state-core-auth-base
verified: 2026-04-28T00:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: null
---

# Phase 011: state_core.auth.base Verification Report

**Phase Goal:** Pydantic `Credential` model, `AuthMethod` Protocol, `is_token`/`is_expired`/`http_headers`/`login`/`refresh` signatures.
**Verified:** 2026-04-28
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

Phase 011 defines the foundational auth contract every downstream phase (012 vault, 013 refresh, 014–018 providers, 019 round-robin, 020 redactor, 022 CLI) consumes. Verification merges plan-level must-haves from `011-01-PLAN.md` (test infrastructure / RED) and `011-02-PLAN.md` (implementation / GREEN). Because plan 02 supersedes plan 01's RED criterion, the union of truths verified is the GREEN end-state plus plan 01's persistent infrastructure deliverables.

### Observable Truths

| #   | Truth                                                                                                                              | Status     | Evidence |
| --- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------- |
| 1   | `tests/auth/` package exists and is collected by pytest (Plan 01)                                                                  | VERIFIED   | `tests/auth/__init__.py` (0 lines) + `tests/auth/conftest.py` (39 lines) + `tests/auth/test_base.py` (183 lines) all exist; pytest collects 11 tests. |
| 2   | All 11 BASE-XX test stubs are present in `test_base.py` (Plan 01)                                                                  | VERIFIED   | `grep -c "BASE-"` → 12 (one comment per BASE-01..BASE-11 plus the docstring line referencing the family); 11 `def test_` (10 plain + 1 `@given`-wrapped). |
| 3   | Shared fixtures (`oauth_cred`, `api_key_cred`, `now_frozen`) are defined and importable (Plan 01)                                 | VERIFIED   | Three `@pytest.fixture` decorators in `conftest.py` lines 10/27/36; secrets carry `-do-not-redact-in-test-only` infix. |
| 4   | All 11 BASE-XX tests from Plan 01 pass GREEN (Plan 02)                                                                             | VERIFIED   | `pytest tests/auth/ -v` → `11 passed in 0.08s`; every BASE-01..BASE-11 in PASSED state. |
| 5   | `OAuthCredential`, `ApiKeyCredential`, `Credential`, `CredentialAdapter`, `AuthMethod` are exported from `state_core.auth` (Plan 02) | VERIFIED   | `from state_core.auth import OAuthCredential, ApiKeyCredential, Credential, CredentialAdapter, AuthMethod` succeeds; `__all__` matches the five-symbol set; re-export identity (`OAuthCredential is base.OAuthCredential`) holds. |
| 6   | Importing `state_core.auth.base` does NOT pull `state_build.*` or `state_teach.*` into `sys.modules` (Plan 02)                     | VERIFIED   | Runtime check after `import state_core.auth` → `leaked: []`. BASE-08 test passes. |
| 7   | `repr(cred)` does not contain any value of `access` / `refresh` / `key` fields (Plan 02)                                          | VERIFIED   | Manual probe: `OAuthCredential(access='sk-ant-oat-PEEK', refresh='RT-PEEK', ...)` → repr is `OAuthCredential(type='oauth', expires=1.0, account_id=None, provider_id='anthropic', extras={})` — both secrets absent. ApiKey repr likewise omits `key`. BASE-06 test passes. |
| 8   | `model_dump_json()` returns byte-identical output across two calls (Plan 02)                                                       | VERIFIED   | BASE-09 (`test_deterministic_serialization`) passes; covers single instance + independent twins. |
| 9   | `OAuthCredential.expires` stores the wire-shape epoch (no 5-min buffer subtracted in storage) (Plan 02)                            | VERIFIED   | Field declared as `expires: float` with docstring `"WIRE VALUE returned by the OAuth server"`; no subtraction at construction; round-trip tests preserve exact value. Buffer enforcement is delegated to `AuthMethod.is_expired` (Phase 014+). |
| 10  | `AuthMethod` is `@runtime_checkable`; structurally-conforming classes pass `isinstance` (Plan 02)                                  | VERIFIED   | BASE-07 (`test_protocol_runtime_checkable`) passes; stub class with the 5 methods + `provider_id` returns True. |
| 11  | mypy strict on `src/state_core/auth/base.py` is clean (Plan 02)                                                                    | VERIFIED   | `mypy --strict src/state_core/auth/base.py` → `Success: no issues found in 1 source file`. (Note: `__init__.py` triggers a project-wide `py.typed` marker warning that pre-dates this phase and affects every package — not a phase-011 regression; see Caveats below.) |

**Score:** 11 / 11 truths verified.

### Required Artifacts

| Artifact                          | Expected                                                       | Status     | Details |
| --------------------------------- | -------------------------------------------------------------- | ---------- | ------- |
| `tests/auth/__init__.py`          | Package marker (≥0 lines)                                      | VERIFIED   | Exists, empty (correct). |
| `tests/auth/conftest.py`          | `oauth_cred` + `api_key_cred` fixtures (≥20 lines, `@pytest.fixture`) | VERIFIED | 39 lines; 3 fixtures (`oauth_cred`, `api_key_cred`, `now_frozen`); imports from `state_core.auth.base`. |
| `tests/auth/test_base.py`         | BASE-01..BASE-11 stubs (≥120 lines, `def test_oauth_round_trip`) | VERIFIED | 183 lines; 11 tests collected and passing; `def test_oauth_round_trip` present at line 28. |
| `src/state_core/auth/base.py`     | `OAuthCredential`, `ApiKeyCredential`, `Credential`, `CredentialAdapter`, `AuthMethod` (≥80 lines, `class OAuthCredential`) | VERIFIED | 221 lines; all five symbols defined; class declarations confirmed via grep. |
| `src/state_core/auth/__init__.py` | Re-exports from base.py (≥10 lines, contains `OAuthCredential`) | VERIFIED   | 29 lines; absolute-import re-export of the five-symbol public surface; `__all__` set matches base. |

### Key Link Verification

| From                               | To                          | Via                                                                                       | Status | Details |
| ---------------------------------- | --------------------------- | ----------------------------------------------------------------------------------------- | ------ | ------- |
| `tests/auth/test_base.py`          | `state_core.auth.base`      | `from state_core.auth.base import OAuthCredential, ApiKeyCredential, AuthMethod, CredentialAdapter, Credential` | WIRED  | Import block at lines 18-24; all 11 tests successfully consume the imports. |
| `tests/auth/conftest.py`           | `state_core.auth.base`      | Fixtures construct `OAuthCredential(...)` / `ApiKeyCredential(...)`                       | WIRED  | Line 7 import; lines 18 + 30 construct instances; downstream tests use them. |
| `src/state_core/auth/__init__.py`  | `src/state_core/auth/base.py` | `from state_core.auth.base import (...)`                                                | WIRED  | Lines 15-21; absolute import; `OAuthCredential is base.OAuthCredential` holds. |
| `src/state_core/auth/base.py`      | `pydantic.TypeAdapter`      | `CredentialAdapter = TypeAdapter(Credential)`                                             | WIRED  | Line 120; consumed by BASE-01/02/03/11 round-trip tests. |
| `src/state_core/auth/base.py`      | `Field(repr=False)`         | Secret-redaction enforcement                                                              | WIRED  | Three matches at lines 59 (`access`), 62 (`refresh`), 97 (`key`); BASE-06 test confirms behavioral effect. |

### Requirements Coverage

The phase carries no AUTH-XX IDs of its own; it uses internal BASE-01..BASE-11 IDs (declared in both PLAN frontmatters' `requirements:` field and asserted in `tests/auth/test_base.py`).

| Requirement | Source Plan | Description                                                              | Status   | Evidence |
| ----------- | ----------- | ------------------------------------------------------------------------ | -------- | -------- |
| BASE-01     | 01, 02      | `OAuthCredential` round-trips through `CredentialAdapter`               | SATISFIED | `test_oauth_round_trip` PASSED |
| BASE-02     | 01, 02      | `ApiKeyCredential` round-trips, omits OAuth-only fields                 | SATISFIED | `test_api_key_round_trip` PASSED |
| BASE-03     | 01, 02      | Discriminator dispatch (`type` literal)                                  | SATISFIED | `test_discriminator_dispatch` PASSED |
| BASE-04     | 01, 02      | `extra="forbid"` rejects unknown fields                                 | SATISFIED | `test_extra_forbid` PASSED |
| BASE-05     | 01, 02      | `frozen=True` blocks attribute assignment                                | SATISFIED | `test_frozen_immutable` PASSED |
| BASE-06     | 01, 02      | `Field(repr=False)` redacts secrets in repr                              | SATISFIED | `test_repr_redacts_secrets` PASSED + manual probe |
| BASE-07     | 01, 02      | `AuthMethod` `@runtime_checkable` accepts structural conformers          | SATISFIED | `test_protocol_runtime_checkable` PASSED |
| BASE-08     | 01, 02      | Mode isolation — no `state_build.*` / `state_teach.*` import leak        | SATISFIED | `test_no_mode_imports` PASSED + post-import sys.modules diff |
| BASE-09     | 01, 02      | Deterministic JSON serialization                                         | SATISFIED | `test_deterministic_serialization` PASSED |
| BASE-10     | 01, 02      | `model_copy(update=...)` returns new frozen instance                     | SATISFIED | `test_model_copy_preserves_frozen` PASSED |
| BASE-11     | 01, 02      | Hypothesis property — round-trip is lossless on safe-ASCII inputs        | SATISFIED | `test_hypothesis_round_trip` PASSED (50 examples) |

No orphaned requirements: the user-supplied requirement list was "none (foundational — uses internal BASE-01..BASE-11 IDs)" and all 11 are claimed by both plans and verified in tests.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

None found. Specifically:

- `grep -nE "import time|from datetime|state_build|state_teach" src/state_core/auth/base.py` → exit 1 (no matches). Cardinal determinism rule and mode-isolation rule both upheld.
- No TODO/FIXME/PLACEHOLDER markers in any phase 011 file.
- No empty-body shortcuts (`return None`, `pass`-only) on production paths — Protocol method bodies use `...` which is the idiomatic Protocol stub.
- `Protocol` is not used as a Pydantic field type anywhere (Pitfall 1 avoided).

### Human Verification Required

None. All 11 BASE-XX behaviors have automated coverage; VALIDATION.md "Manual-Only Verifications" table is empty by design ("All foundational types have full automated coverage").

### Full-Suite Regression Check

- `pytest tests/ -q --ignore=tests/auth` → **321 passed** in 14.92s. No v1 regressions.
- `pytest tests/auth/ -v` → **11 passed** in 0.08s. All BASE-XX GREEN.
- Combined: **332 passing tests** post-phase-011 (was 321 pre-phase).

### Caveats

1. **mypy `py.typed` marker on `__init__.py`**: Running `mypy --strict src/state_core/auth/__init__.py` (or the whole package) emits one `import-untyped` error on the import-from-base line because `src/state_core/` has no `py.typed` marker file. This is a **project-wide pre-existing condition** — `mypy src/state_core/` shows the same class of errors across `projector.py`, `schema.py`, etc. (11 errors total in 6 files), all unrelated to phase 011. Plan 02 Task 1's acceptance criterion (`mypy --strict src/state_core/auth/base.py 2>&1 | grep -E "Success: no issues found"`) targets the file directly and passes cleanly. The phase-011 implementation introduces zero new mypy errors. Adding a `py.typed` marker is a project-hygiene fix outside this phase's scope.

2. **VALIDATION.md frontmatter `nyquist_compliant: false`**: Plan 02's `<success_criteria>` explicitly notes this flag should flip to `true` after this plan. The verifier does not edit it. Recommend updating to `nyquist_compliant: true` in the SUMMARY/cleanup pass (or a follow-up commit) to reflect the GREEN state.

### Gaps Summary

No gaps. All 11 observable truths verified, all 5 artifacts pass three-level checks, all 5 key links wired, all 11 BASE-XX requirements satisfied by passing tests, no anti-patterns detected, no v1 regressions. The contract for downstream phases (012 vault, 013 refresh, 014–018 providers, 019 round-robin, 020 redactor, 022 CLI) is locked.

## Step 7b: Quality Findings

Skipped (quality.level: fast)

---

_Verified: 2026-04-28_
_Verifier: Claude (gsd-verifier)_
