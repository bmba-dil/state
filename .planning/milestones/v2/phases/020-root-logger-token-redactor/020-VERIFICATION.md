---
phase: 020-root-logger-token-redactor
verified: 2026-04-30T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 020: Root-Logger Token Redactor Verification Report

**Phase Goal:** Compiled regex set, applied at root logger, refuse-daemon-start if not attached. (AUTH-10)
**Verified:** 2026-04-30
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                          | Status     | Evidence                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `redactor.py` exists with 12 compiled regex patterns + `_SECRET_KEYS` frozenset + `_walk_value` walker + public surface        | ✓ VERIFIED | `redactor.py` 469 lines; `grep -c "re.compile("` = 12; all 6 public symbols present (REDACTED, RedactorNotAttached, install, assert_redactor_attached, iter_token_patterns, redact_processor) |
| 2   | `state_core/observability/__init__.py` re-exports the 6 public symbols                                                         | ✓ VERIFIED | __init__.py imports + __all__ both contain all 6 names; `from state_core.observability import …` for all 6 succeeds                              |
| 3   | `src/state_daemon/orchestrator.py::startup` invokes `install(); assert_redactor_attached()` as Step 0 BEFORE other startup work | ✓ VERIFIED | orchestrator.py line 37 = `install()`, line 38 = `assert_redactor_attached()`, line 40 = `store = SqliteEventStore()` (Step 1 begins line 43) |
| 4   | All 4 plans (020-01..04) marked complete with SUMMARY.md present (where landed)                                                | ✓ VERIFIED | 020-02-SUMMARY.md, 020-03-SUMMARY.md, 020-04-SUMMARY.md present; 020-01 SUMMARY consolidated into 020-02-SUMMARY per executor protocol         |
| 5   | REQUIREMENTS.md AUTH-10 = `[x]`; VALIDATION.md = `status: complete` / `nyquist_compliant: true`                                 | ✓ VERIFIED | REQUIREMENTS.md:18 `- [x] **AUTH-10**: …`; 020-VALIDATION.md frontmatter: `status: complete`, `nyquist_compliant: true`, `wave_0_complete: true` |
| 6   | All 26 REDACT-NN tests pass                                                                                                    | ✓ VERIFIED | `uv run pytest tests/test_redactor.py tests/test_observability_import_graph.py -q` → **36 passed in 0.44s** (32 in redactor file + 4 in import-graph; 26 REDACT-NN rows + 4 structural extras + 2 new code-review-fix regression tests + 4 parametrized github_copilot variants) |
| 7   | Full auth suite reports ≥321 passed                                                                                            | ✓ VERIFIED | `uv run pytest tests/auth/ -q` → **321 passed, 1 skipped in 46.79s**. Note: code-review-fix regression tests (MF-01, SF-03) live in `tests/test_redactor.py`, not under `tests/auth/`, so the auth count remains at the pre-fix 321 floor |
| 8   | Mode isolation: `state_core.observability.redactor` does NOT import `state.build.*` / `state.teach.*` / `state_build` / `state_teach` | ✓ VERIFIED | `grep -nE "^from state_build\|^import state_build\|^from state_teach\|^import state_teach\|^from state\.build\|^from state\.teach"` against redactor.py + __init__.py → 0 hits |
| 9   | Determinism: regex compiled at module-import time (count = 12)                                                                 | ✓ VERIFIED | `grep -c "re.compile("` against redactor.py → **12** (matches the 12 token-shape pattern families); all calls live at module scope inside `_PATTERNS: tuple[re.Pattern[str], ...]` (lines 66-93); none inside any function body |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact                                          | Expected                                                                       | Status     | Details                                                                                                                                          |
| ------------------------------------------------- | ------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/state_core/observability/__init__.py`        | Package marker + 6-symbol re-exports                                           | ✓ VERIFIED | 49 lines; module docstring + import block + `__all__` of 6 names; no forbidden imports                                                            |
| `src/state_core/observability/redactor.py`        | 12 compiled regex + 12-key SECRET_KEYS frozenset + walker + processor + wiring | ✓ VERIFIED | 469 lines; 12 `re.compile()` (each shape family); `_SECRET_KEYS = frozenset({…})` of 12 entries; `_walk_value`, `redact_processor`, `iter_token_patterns`, `install`, `assert_redactor_attached`, `RedactorNotAttached` all present and exported |
| `src/state_daemon/orchestrator.py`                | Step 0 wiring before Step 1                                                    | ✓ VERIFIED | imports `install, assert_redactor_attached` from `state_core.observability` (line 9, no `src.` prefix per SF-04 fix); calls both in startup() at lines 37-38; module docstring on line 1 reflects "redactor → repair → migrate → reconciler" ordering |
| `tests/test_redactor.py`                          | RED stubs (Wave 1) → GREEN (Wave 2/3) for REDACT-01..24, 26                    | ✓ VERIFIED | 32 named tests pass (4 parametrized github_copilot variants); covers all 25 REDACT-NN rows plus 4 structural extras + 2 new code-review-fix regression tests (`test_redacts_multi_arg_exception` for MF-01, `test_install_self_heals_under_installed_reset` for SF-03) |
| `tests/test_observability_import_graph.py`        | Mode-isolation lint (REDACT-25 + spillovers)                                   | ✓ VERIFIED | 3 named tests pass: `test_observability_no_mode_imports`, `test_observability_imports_only_allowed_targets`, `test_observability_init_exists` |
| `.planning/milestones/v2/phases/020-…/020-VALIDATION.md` | status=complete, nyquist_compliant=true                                  | ✓ VERIFIED | Frontmatter flipped (lines 1-9 of file); per-task verification map populated with 26 REDACT rows + plan/task ID provenance; all 8 sign-off checkboxes flipped to `[x]` |
| `.planning/milestones/v2/REQUIREMENTS.md`         | AUTH-10 row = `[x]`                                                            | ✓ VERIFIED | Line 18: `- [x] **AUTH-10**: Root-logger token redactor strips sk-ant-*, sk-*, ya29.*, etc. from every log record` |

### Key Link Verification

| From                                                | To                                                            | Via                                                                                                       | Status   | Details                                                                                                                                              |
| --------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/state_daemon/orchestrator.py`                  | `state_core.observability.{install, assert_redactor_attached}` | direct import + invocation at startup() Step 0                                                            | ✓ WIRED  | line 9: `from state_core.observability import assert_redactor_attached, install`; lines 37-38: both called inside `startup()` before any other I/O    |
| `state_core.observability.redactor::install`        | structlog.configure() + root logger ProcessorFormatter         | shared_processors list at index 0 in BOTH structlog chain AND foreign_pre_chain                            | ✓ WIRED  | redactor.py:299 `shared_processors = [redact_processor, …]`; line 310 `structlog.configure(processors=shared_processors+[…])`; line 322 `formatter = structlog.stdlib.ProcessorFormatter(foreign_pre_chain=shared_processors, …)` |
| `state_core.observability.redactor::assert_redactor_attached` | `RedactorNotAttached`                                | raises on canary survival OR position-0 mismatch OR no ProcessorFormatter on root                          | ✓ WIRED  | redactor.py:392-398 (position-0 check), :405-409 (direct invocation canary), :446-451 (no-formatter), :452-458 (canary survives stdlib path) — 4 distinct raise sites |
| `tests/test_redactor.py`                            | `state_core.observability.redactor`                            | module-level imports + 32 test invocations                                                                | ✓ WIRED  | All 32 tests pass; module-level `from state_core.observability.redactor import (…)` resolves all symbols                                              |
| `state_core.observability.__init__`                 | `state_core.observability.redactor`                            | re-export of 6 public symbols                                                                              | ✓ WIRED  | __init__.py:32-39 import block + :41-48 `__all__` both list all 6 names                                                                              |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                          | Status     | Evidence                                                                                                                  |
| ----------- | ----------- | ---------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| AUTH-10     | 020-01..04  | Root-logger token redactor strips `sk-ant-*`, `sk-*`, `ya29.*`, etc. from every log record           | ✓ SATISFIED | All 26 REDACT-NN VALIDATION rows GREEN; install() + assert_redactor_attached() wired into orchestrator Step 0; mode-isolation lint passes; REQUIREMENTS.md flipped to [x]; VALIDATION.md flipped to status=complete; daemon refuses to start if redactor not attached (verified via `RedactorNotAttached` raise sites) |

No orphaned requirements. AUTH-10 is the single load-bearing requirement for this phase per ROADMAP / REQUIREMENTS.md.

### Anti-Patterns Found

| File                                              | Line | Pattern                       | Severity | Impact                                                                                  |
| ------------------------------------------------- | ---- | ----------------------------- | -------- | --------------------------------------------------------------------------------------- |
| `src/state_core/observability/redactor.py`        | 58   | inline comment text "anchored with  and " (empty) | ℹ️ Info  | Cosmetic: comment was authored with literal `(?<!\w)` / `(?!\w)` markers that got stripped during a `sed`-style edit. The actual regex source on lines 66-93 contains the anchors correctly (per SF-01 fix). No functional impact. |

No blocker or warning anti-patterns. No `TODO`/`FIXME`/`PLACEHOLDER` markers detected in the production code paths. The 12 `re.compile` calls all live at module-import time (lines 66-92), satisfying the determinism cardinal rule.

### Code-Review Fix Status

Per `020-REVIEW.md` (1 critical + 4 warning + 6 info findings) and `020-REVIEW-FIX.md` (5 in-scope findings fixed; 6 WORTH-KNOWING deferred):

| Finding | Severity | Status   | Evidence                                                                                                                                                                                                              |
| ------- | -------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MF-01   | CRITICAL | ✓ FIXED  | redactor.py:171-187 `_walk_value` BaseException branch returns `RuntimeError(redacted_msg)` on TypeError fallback (was `return v` — leaked live exception). Regression test `test_redacts_multi_arg_exception` added. |
| SF-01   | WARNING  | ✓ FIXED  | All 11 prefix-shape patterns wrapped with `(?<!\w)` / `(?!\w)` anchors (lines 66-92); Bearer pattern intentionally unanchored (its `\s+` provides left boundary). Hypothesis bumped to 1000 examples with widened alphabet. |
| SF-02   | WARNING  | ✓ FIXED  | `assert_redactor_attached()` (lines 379-409) now invokes `redact_processor` directly on a synthetic event_dict instead of using `capture_logs(processors=...)`; `pyproject.toml` floor `structlog>=25.1` now safe. |
| SF-03   | WARNING  | ✓ FIXED  | redactor.py:330-345 install() scans existing root handlers for a redactor-bearing ProcessorFormatter and skips re-attachment. Regression test `test_install_self_heals_under_installed_reset` added. |
| SF-04   | WARNING  | ✓ FIXED  | orchestrator.py imports use `from state_core.*` consistently (no `src.` prefix on lines 7-11); module-identity ambiguity eliminated for the redactor's `_INSTALLED` flag and `redact_processor` identity check. |
| WK-01..06 | INFO    | ⚠ DEFERRED | 6 worth-knowing items (cycle detection, pattern-order test, NamedTuple support, docstring polish, log-level clobber, error-message precision) deferred per scope policy; documented in 020-REVIEW-FIX.md. None block landing or affect AUTH-10 closure. |

### Human Verification Required

None. All goal-achievement assertions verified programmatically:

- All 36 unit/property/integration tests pass deterministically.
- The full 321-test auth regression suite passes with no new failures.
- The hypothesis property at 1000 draws (Plan 04 phase gate) shows zero falsifying examples.
- The orchestrator's Step 0 sequencing is enforced at the source level (lines 37-38 are syntactically before line 40).
- Mode-isolation is enforced at the test level (`tests/test_observability_import_graph.py` runs every test session).
- Daemon-refusal contract is enforced by 4 distinct `raise RedactorNotAttached` sites in `assert_redactor_attached()` and exercised by REDACT-21.

The Plan 04 SUMMARY documents a manual smoke test (5 OK assertions, 0 canary leaks) that exercised the import-edge of the orchestrator + canary stripping on both structlog and stdlib paths + idempotency + negative path. That smoke test is reproducible from the SUMMARY's verbatim block; no fresh human verification step is required for this verification pass.

### Gaps Summary

None. AUTH-10 is fully satisfied. Phase 020 goal "Compiled regex set, applied at root logger, refuse-daemon-start if not attached" is achieved end-to-end:

1. **Compiled regex set** — 12 `re.Pattern` objects compiled at module import (verified count = 12), each with traceable provenance to a source-of-truth file (Anthropic OAuth spec, `_REGISTRY` in api_key.py, RFC 6750, GitHub upstream announcement).
2. **Applied at root logger** — `install()` wires the same `shared_processors` list at structlog position 0 AND as the stdlib `ProcessorFormatter.foreign_pre_chain`, giving universal coverage across structlog-native callers and stdlib third-party libraries (httpx, litellm, pygit2, aiosqlite).
3. **Refuse-daemon-start** — `assert_redactor_attached()` runs as Step 0 of `src/state_daemon/orchestrator.py::startup()` and raises `RedactorNotAttached` (a fatal `RuntimeError` subclass) if the chain is broken or the canary survives any rendering path. Verified by REDACT-21 (`test_selfcheck_fails_when_not_installed`).

Score 9/9 must-haves verified. No remaining gaps. AUTH-10 closure is real, not nominal.

## Step 7b: Quality Findings

Skipped (quality.level: fast)

---

_Verified: 2026-04-30_
_Verifier: Claude (gsd-verifier)_
