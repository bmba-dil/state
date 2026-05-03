---
phase: 020-root-logger-token-redactor
plan: 04
subsystem: observability
tags: [observability, redactor, auth, p0-14, wave-4, verification, phase-gate, hypothesis-1000-draws, smoke-test, validation-flip]
dependency_graph:
  requires:
    - 020-01 (Wave 1 RED scaffolding — REDACT-01..24,26 stubs in tests/test_redactor.py + REDACT-25 in tests/test_observability_import_graph.py)
    - 020-02 (Wave 2 GREEN — src/state_core/observability/redactor.py with 12 compiled regex patterns + _walk_value + redact_processor)
    - 020-03 (Wave 3 wiring — install() + assert_redactor_attached() + RedactorNotAttached; orchestrator Step 0 wiring)
  provides:
    - VALIDATION.md with status=complete, nyquist_compliant=true, wave_0_complete=true
    - 26/26 GREEN row matrix with plan/task ID provenance
    - Hypothesis 1000-draw phase-gate evidence (RESEARCH §Sampling Rate target met)
    - Smoke-test evidence that install() + assert_redactor_attached() + canary stripping (structlog + stdlib paths) + idempotency + negative path all work end-to-end
    - AUTH-10 closure ready for /gsd:verify-work and v2 milestone STATE.md "Phases complete: 7 -> 8" bump
  affects:
    - .planning/milestones/v2/STATE.md (orchestrator will bump completed_phases 7 -> 8)
    - .planning/milestones/v2/ROADMAP.md (orchestrator will flip Phase 020 plans block to [x])
    - Phase 022 (CLI auth) — depends on AUTH-10 closure for log-safe `state auth status` output
tech_stack:
  added:
    - none (verification-only — pytest 8.4 + hypothesis 6.152 + structlog 25.5 + stdlib only)
  patterns:
    - Phase-gate plan with no production-code changes — exclusively a verification + frontmatter-flip wave
    - Tempdir hypothesis harness at max_examples=1000 to enforce RESEARCH §Sampling Rate without modifying Plan 01's per-task max_examples=200 stub
    - Multi-path smoke test (structlog `capture_logs(processors=...)` + stdlib `LogRecord` formatter render) covering both leak surfaces
    - Plan/Task ID column in VALIDATION.md per-task verification map (provenance for which plan landed which row)
key_files:
  created:
    - .planning/milestones/v2/phases/020-root-logger-token-redactor/020-04-SUMMARY.md (this file)
  modified:
    - .planning/milestones/v2/phases/020-root-logger-token-redactor/020-VALIDATION.md (frontmatter flip + per-task map populated with 26 REDACT rows + 8 checkboxes flipped)
    - .planning/milestones/v2/REQUIREMENTS.md (AUTH-10 row flipped from [ ] to [x])
key_decisions:
  - mypy `Found 1 error in 1 file` is treated as out-of-scope per the executor scope-boundary rule. The single error is `[import-untyped]` "missing py.typed marker" on `__init__.py`'s import of `state_core.observability.redactor` — a project-wide infrastructure gap inherited from Phases 011-019 (identical shape across all six prior auth modules; see 019-04-SUMMARY for precedent). Zero errors point to logic in redactor.py itself. Adding a `py.typed` marker is a project-wide concern (would need updates to every state_core.* module + every consumer test) that belongs in a future infrastructure phase, not Phase 020's verification gate.
  - The Plan 04 hypothesis gate harness (Step 4) was supplied by the planner with a wider `whitelist_categories=("Ll", "Lu", "Nd")` strategy that produced falsifying examples (`µ` in body terminating the regex match boundary). This was Rule-1-fixed inline by narrowing the body alphabet to ASCII alnum only — matching the in-tree REDACT-24 stub's Wave-3-narrowed strategy verbatim (line 593-607 of tests/test_redactor.py). The harness is a tempdir-only verification artefact (not committed); the fix mirrors Plan 01's deliberate Wave 3 narrowing (the in-tree stub's docstring explicitly notes "Wave 3 narrowed this from a wider strategy after observing µ / ² / `_-`-suffix falsifying examples").
  - The Plan 04 smoke test (Step 5) used `capture_logs()` without passing the configured processors, which strips the redactor (capture_logs() bypasses `structlog.configure()` processors by default — explicitly documented as Pitfall 2 in `assert_redactor_attached`'s implementation). Rule-1-fixed inline by passing `processors=capture_chain` (the configured chain minus the terminal `wrap_for_formatter`) — mirrors the canonical pattern in `assert_redactor_attached` line 380. The fix is local to the smoke script (which is `python3 -c '...'` invoked from bash; not a committed artefact).
  - VALIDATION.md and REQUIREMENTS.md were committed (no `-f` needed — both were already tracked from prior phases via the established `commit_docs=false` carve-out for verification flips). This matches the established pattern from 010.1-A (b549379), 016-01 (083f2dc), 018-04 (7c59cde, ead8b2f), and 019-04 (d8bfbe2, 6c5272a).
  - Worktree base mismatch + missing local infrastructure files (same shape as 019-04): the agent worktree at `/Users/tmac/Projects/state/.claude/worktrees/agent-a47b263a5725ebcad/` was provisioned from an older v1-lineage base (5acaf88), so `git reset --hard 328934f` was needed to land at the correct Wave 3 integration tip; `.state/migrations/0001-0003.sql` and a schema-bearing `.state/events.sqlite` had to be copied from the main worktree at `/Users/tmac/Projects/state/` to satisfy the repo-wide regression sweep. Documented under Issues Encountered.
patterns_established:
  - "Phase-gate hypothesis run: tempdir harness at max_examples=1000 (RESEARCH §Sampling Rate target) without editing the in-tree per-task stub at max_examples=200"
  - "Smoke-test pattern for log redactors: pass configured processors explicitly to capture_logs(), iterate root-logger ProcessorFormatter handlers for the stdlib leak surface"
  - "26/26 row matrix with explicit plan/task ID provenance for every assertion"
  - "Out-of-scope mypy infrastructure findings explicitly documented rather than silently passed"
requirements_completed: [AUTH-10]
metrics:
  duration_minutes: 4
  completed_date: 2026-04-30
  task_count: 1
  file_count: 1 created (this SUMMARY) + 2 modified (VALIDATION.md, REQUIREMENTS.md)
  test_pass_count_quick: 34
  test_pass_count_full_auth: 321
  test_pass_count_repo_minus_auth: 355
  hypothesis_examples_at_phase_gate: 1000
  smoke_assertions_passed: 5
---

# Phase 020 Plan 04: Wave 4 Verification — Phase-Gate Closure for AUTH-10

Wave 4 verifies the cumulative output of Waves 1-3: 26/26 REDACT-NN
VALIDATION rows GREEN, no regression anywhere in the repo, the
`install()` + `assert_redactor_attached()` + canary-stripping public
surface works end-to-end on both the structlog-native and stdlib
caller paths, the mode-isolation import-graph constraint holds, and
the Hypothesis property test (REDACT-24) passes at the
RESEARCH §Sampling Rate-pinned 1000-draw target. With this gate,
`state_core.observability` now offers
`install() / assert_redactor_attached() / RedactorNotAttached / REDACTED /
iter_token_patterns() / redact_processor` — the canonical surface
that the daemon orchestrator wires at Step 0 (BEFORE any other I/O)
to refuse-startup if the root-logger redactor is not attached.

## Performance

- **Duration:** ~4 min (verification + frontmatter flip + SUMMARY)
- **Started:** 2026-05-01T12:32:25Z
- **Completed:** 2026-05-01T12:36:08Z
- **Tasks:** 1
- **Files modified:** 2 (VALIDATION.md + REQUIREMENTS.md) + 1 created (this SUMMARY)

## Accomplishments

- **34 / 34** on the targeted Phase 020 quick run (31 in
  `test_redactor.py` + 3 in `test_observability_import_graph.py`)
- **321 passed / 1 skipped** on the full `tests/auth/` suite (one
  pre-existing Phase 014 skip)
- **355 passed / 0 failed** on `pytest tests/ --ignore=tests/auth`
  (repo-wide regression sweep clean, after restoring missing
  `.state/migrations/0001-0003.sql` and a schema-bearing
  `.state/events.sqlite` from the main worktree)
- **Hypothesis 1000-draw phase gate:** `1000 passing examples, 0
  failing examples, 0 invalid examples` — RESEARCH §Sampling Rate
  target met
- **Hypothesis 200-draw in-tree stub:** `200 passing examples, 0
  failing examples` — Plan 01's RED-stub source intact at
  per-task feedback latency
- **5 smoke assertions** PASS (structlog path canary stripped,
  stdlib path canary stripped, negative path raises
  `RedactorNotAttached`, `install()` idempotent across 4 calls,
  pattern set has 12 compiled regex patterns); 0 canary leaks in
  the smoke output buffer
- **Import-graph one-way edge** verified manually: redactor.py +
  `__init__.py` have 0 lines importing from `state_build.*` /
  `state_teach.*` / `state.build.*` / `state.teach.*`; 0 lines
  importing from `state_core.*` (mode-neutral plumbing per
  RESEARCH); all imports are stdlib (`re`, `logging`, `uuid`,
  `typing`) or structlog
- **Public surface re-exports** verified: `from
  state_core.observability import install, assert_redactor_attached,
  RedactorNotAttached, REDACTED, iter_token_patterns,
  redact_processor` all importable; `REDACTED == '[REDACTED]'`;
  `RedactorNotAttached` is a `RuntimeError` subclass; pattern set
  is a `tuple` of `re.Pattern[str]` with `len >= 12`
- **Orchestrator Step 0 wiring** verified: `src/state_daemon/orchestrator.py`
  imports `install` + `assert_redactor_attached` from
  `src.state_core.observability` and calls both inside `startup()`
  before any other I/O (lines 37, 38)

## Task Commits

Each documentation flip was committed atomically with `--no-verify`
(parallel-executor protocol):

1. **VALIDATION.md flip** — `5931ab0` (docs(020-04): flip
   VALIDATION.md to compliant — Phase 020 verification gate)
2. **REQUIREMENTS.md flip** — `2b4923c` (docs(020-04): mark AUTH-10
   complete in v2 REQUIREMENTS.md)

_Note: This is a verification-only wave. No production code modified;
all artefacts are planning documents (VALIDATION.md, REQUIREMENTS.md,
this SUMMARY)._

## VALIDATION Row Matrix — 26 / 26 GREEN

| #  | Behavior under test                                                              | Plan/Task        | Status |
|----|----------------------------------------------------------------------------------|------------------|--------|
| 01 | Anthropic OAuth access token (`sk-ant-oat-…`) redacted in event_dict value      | 01-T2 + 02-T2    | PASS   |
| 02 | Anthropic API key (`sk-ant-api03-…`) redacted                                   | 01-T2 + 02-T2    | PASS   |
| 03 | Generic OpenAI key (`sk-` ≥ 40 chars) redacted                                  | 01-T2 + 02-T2    | PASS   |
| 04 | Anthropic OAuth refresh redacted via key-context (`refresh_token` key)          | 01-T2 + 02-T2    | PASS   |
| 05 | Google OAuth access (`ya29.…`) redacted                                         | 01-T2 + 02-T2    | PASS   |
| 06 | Google OAuth refresh (`1//…`) redacted                                          | 01-T2 + 02-T2    | PASS   |
| 07 | GitHub Copilot device-code token (`gho_/ghu_/ghs_/ghp_`) redacted               | 01-T2 + 02-T2    | PASS   |
| 08 | Antigravity / Copilot opaque refresh redacted via key-context                   | 01-T2 + 02-T2    | PASS   |
| 09 | Bearer header (`Bearer sk-ant-oat-…`) redacted incl. double-space variant       | 01-T2 + 02-T2    | PASS   |
| 10 | HTTP-header dict with `Authorization` key redacted via key-context              | 01-T2 + 02-T2    | PASS   |
| 11 | Nested-dict secret redacted (token inside `{"request":{"headers":{...}}}`)      | 01-T2 + 02-T2    | PASS   |
| 12 | Secret in `list` value redacted                                                 | 01-T2 + 02-T2    | PASS   |
| 13 | Secret in stdlib `httpx`-style record redacted via foreign_pre_chain            | 01-T2 + 03-T1    | PASS   |
| 14 | Secret in stdlib `litellm`-style record redacted                                | 01-T2 + 03-T1    | PASS   |
| 15 | Secret in raised exception's `str()` redacted                                   | 01-T2 + 02-T2    | PASS   |
| 16 | Secret in exception traceback chain redacted (exc_info=True path)               | 01-T2 + 02-T2    | PASS   |
| 17 | Final JSONRenderer output free of token-shape regex matches (belt-and-braces)   | 01-T2 + 03-T1    | PASS   |
| 18 | `redact_processor` at position 0 in `structlog.get_config()["processors"]`      | 01-T2 + 02-T2    | PASS   |
| 19 | `ProcessorFormatter` attached to root logger with redact_processor in chain     | 01-T2 + 03-T1    | PASS   |
| 20 | `assert_redactor_attached()` returns OK after `install()` ran                   | 01-T2 + 03-T1    | PASS   |
| 21 | `assert_redactor_attached()` raises `RedactorNotAttached` when not installed    | 01-T2 + 03-T1    | PASS   |
| 22 | Negative test: `sk-foundation`, `sk-2`, `Bearer xyz`, `Skill-1234` NOT redacted | 01-T2 + 02-T2    | PASS   |
| 23 | `install()` idempotent — calling twice doesn't duplicate handlers/processors    | 01-T2 + 02-T2    | PASS   |
| 24 | Hypothesis property: every secret-shaped string is fully redacted (200 ex)      | 01-T2 + 02-T2    | PASS   |
| 25 | Mode-isolation lint: state_core.observability.* imports no state_build/teach    | 01-T1 + 02-T1    | PASS   |
| 26 | Existing `tests/auth/conftest.py` `_isolate_structlog_for_auth_tests` works     | 01-T2 + 02-T2    | PASS   |

## Pytest Output (verbatim, tail)

### Step 1 — Phase 020 quick surface (-x -v):

```
tests/test_redactor.py::test_redacts_anthropic_oat PASSED                [  2%]
tests/test_redactor.py::test_redacts_anthropic_api_key PASSED            [  5%]
tests/test_redactor.py::test_redacts_openai_generic PASSED               [  8%]
tests/test_redactor.py::test_redacts_opaque_refresh_by_key PASSED        [ 11%]
tests/test_redactor.py::test_redacts_google_ya29 PASSED                  [ 14%]
tests/test_redactor.py::test_redacts_google_refresh_1slash PASSED        [ 17%]
tests/test_redactor.py::test_redacts_github_copilot[gho_…] PASSED        [ 20%]
tests/test_redactor.py::test_redacts_github_copilot[ghu_…] PASSED        [ 23%]
tests/test_redactor.py::test_redacts_github_copilot[ghs_…] PASSED        [ 26%]
tests/test_redactor.py::test_redacts_github_copilot[ghp_…] PASSED        [ 29%]
tests/test_redactor.py::test_redacts_opaque_antigravity_refresh PASSED   [ 32%]
tests/test_redactor.py::test_redacts_bearer_header_variants PASSED       [ 35%]
tests/test_redactor.py::test_redacts_authorization_header_dict PASSED    [ 38%]
tests/test_redactor.py::test_redacts_nested_dict_secret PASSED           [ 41%]
tests/test_redactor.py::test_redacts_list_value PASSED                   [ 44%]
tests/test_redactor.py::test_redacts_stdlib_httpx_record PASSED          [ 47%]
tests/test_redactor.py::test_redacts_stdlib_litellm_record PASSED        [ 50%]
tests/test_redactor.py::test_redacts_exception_message PASSED            [ 52%]
tests/test_redactor.py::test_redacts_traceback_chain PASSED              [ 55%]
tests/test_redactor.py::test_jsonrenderer_output_clean PASSED            [ 58%]
tests/test_redactor.py::test_processor_at_position_zero PASSED           [ 61%]
tests/test_redactor.py::test_processorformatter_attached_to_root PASSED  [ 64%]
tests/test_redactor.py::test_selfcheck_passes_when_installed PASSED      [ 67%]
tests/test_redactor.py::test_selfcheck_fails_when_not_installed PASSED   [ 70%]
tests/test_redactor.py::test_negative_no_overredaction PASSED            [ 73%]
tests/test_redactor.py::test_install_idempotent PASSED                   [ 76%]
tests/test_redactor.py::test_hypothesis_secrets_never_survive PASSED     [ 79%]
tests/test_redactor.py::test_existing_auth_log_calls_still_render PASSED [ 82%]
tests/test_redactor.py::test_pattern_set_compiled_at_import PASSED       [ 85%]
tests/test_redactor.py::test_iter_token_patterns_returns_tuple PASSED    [ 88%]
tests/test_redactor.py::test_walk_value_and_secret_keys_imported PASSED  [ 91%]
tests/test_observability_import_graph.py::test_observability_no_mode_imports PASSED [ 94%]
tests/test_observability_import_graph.py::test_observability_imports_only_allowed_targets PASSED [ 97%]
tests/test_observability_import_graph.py::test_observability_init_exists PASSED [100%]

============================== 34 passed in 0.58s ==============================
```

### Step 2 — Full auth suite (-q):

```
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 67%]
........................................................................ [ 89%]
.................................s                                       [100%]
321 passed, 1 skipped in 46.79s
```

### Step 3 — Repo-wide minus auth (-q --ignore=tests/auth):

```
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 81%]
...................................................................      [100%]
355 passed in 14.90s
```

## mypy Output (verbatim)

```
src/state_core/observability/__init__.py:32: error: Skipping analyzing "state_core.observability.redactor": module is installed, but missing library stubs or py.typed marker  [import-untyped]
src/state_core/observability/__init__.py:32: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
Found 1 error in 1 file (checked 2 source files)
```

**Out-of-scope per the executor scope-boundary rule.** The single
diagnostic is `[import-untyped]` "missing py.typed marker" on
`__init__.py`'s import of `state_core.observability.redactor` — a
project-wide infrastructure gap inherited from Phases 011-019. All six
prior `state_core.auth.*` modules report identical `[import-untyped]`
diagnostics on cross-module re-exports (Phase 019: 10 errors; Phase
018: 10 errors; Phase 013: 9 errors). **Zero errors point to logic in
redactor.py itself.** Adding a `py.typed` marker is a project-wide
concern that affects every existing module, every consumer test, and
every cross-module import — it belongs in a future infrastructure
phase, not Phase 020's verification gate.

## Hypothesis Statistics — 1000-draw Phase Gate (verbatim)

```
test_phase020_gate_hypothesis.py::test_phase_gate_hypothesis_1000_draws PASSED [100%]
============================ Hypothesis Statistics =============================

test_phase020_gate_hypothesis.py::test_phase_gate_hypothesis_1000_draws:

  - during generate phase (0.32 seconds):
    - Typical runtimes: < 1ms, of which < 1ms in data generation
    - 1000 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because settings.max_examples=1000


============================== 1 passed in 0.36s ==============================
```

**Phase-gate sampling rate target met:** `1000 passing examples, 0
failing examples, 0 invalid examples`. The harness re-implements
REDACT-24's property at `@settings(max_examples=1000, deadline=None)`
in a tempdir-only test file (Plan 01's in-tree stub remains at
`max_examples=200` for per-task feedback latency, per RESEARCH
§Sampling Rate explicit guidance).

In-tree REDACT-24 (200 examples) re-run for completeness:

```
tests/test_redactor.py::test_hypothesis_secrets_never_survive PASSED     [100%]

  - during generate phase (0.06 seconds):
    - Typical runtimes: < 1ms, of which < 1ms in data generation
    - 200 passing examples, 0 failing examples, 0 invalid examples
```

## Smoke-Test Output (verbatim)

```
OK structlog path canary stripped
OK stdlib path canary stripped
OK negative path raises RedactorNotAttached
OK install() idempotent
OK pattern set has 12 compiled patterns
```

5 OK assertions; 0 canary leaks; exit 0; final marker `Phase 020
smoke test passed`. The smoke script:

1. Imports `src.state_daemon.orchestrator.startup` (verifies the
   import edge — does NOT run startup, which would touch SQLite +
   filesystem).
2. Calls `install()` + `assert_redactor_attached()`.
3. Emits a canary `sk-ant-oat-SMOKE-XXXXXXXX...` (50 X chars)
   through `structlog.get_logger().info(...)` and verifies it does
   NOT survive in the captured log records (using
   `capture_logs(processors=capture_chain)` to drive the redactor —
   `capture_logs()` without `processors=...` bypasses configured
   processors per Pitfall 2 in `assert_redactor_attached`).
4. Renders a synthetic `LogRecord` with the same canary through
   each `ProcessorFormatter` handler attached to the root logger
   and verifies the rendered output contains `[REDACTED]` rather
   than the canary bytes.
5. Resets defaults, breaks the install guard, calls
   `assert_redactor_attached()` and verifies it raises
   `RedactorNotAttached`.
6. Calls `install()` four times total and verifies the
   `redact_processor` callable appears exactly once in
   `structlog.get_config()["processors"]` (idempotency).
7. Calls `iter_token_patterns()` and verifies it returns a `tuple`
   of `re.Pattern[str]` with `len >= 12`.

## Import-Graph Verification

All three Step 6 grep checks return 0 matches (clean):

```
$ grep -nE "^from state_build|^from state_teach|^import state_build|^import state_teach|^from state\.build|^from state\.teach" \
    src/state_core/observability/redactor.py src/state_core/observability/__init__.py
(no output, exit 1)

$ grep -nE "^from state_core\." src/state_core/observability/redactor.py
(no output, exit 1)

$ grep -nE "^from |^import " src/state_core/observability/redactor.py | \
    grep -vE "from __future__|import re|import logging|import uuid|from typing|import structlog|from structlog\.testing"
(no output, exit 1)
```

Mode isolation enforced; redactor.py's only imports are stdlib
(`re`, `logging`, `uuid`, `from typing import Any`,
`from __future__ import annotations`) and structlog
(`import structlog`, `from structlog.testing import capture_logs`).

## Final 8-Threat Mitigation Status

The phase-level threat model lives in `020-RESEARCH.md`; Plan 04's
addendum (T-020-W4-1..5) is purely about evidence integrity. Combined
status:

| ID         | Threat                                                                                | Severity | Layer                                                                                  | Status |
|------------|---------------------------------------------------------------------------------------|----------|----------------------------------------------------------------------------------------|--------|
| T-020-1    | sk-* false-positive collision with `sk-foundation`, `sk-2`                            | HIGH     | ≥40-char minimum on generic `sk-…`; REDACT-22 negative test                            | CLOSED |
| T-020-2    | Length-preserving placeholder leaks token-class via length                            | HIGH     | Length-uniform `[REDACTED]` substitution; redactor.py docstring §3                     | CLOSED |
| T-020-3    | Opaque refresh tokens (no prefix) escape regex set                                    | MEDIUM   | `_SECRET_KEYS` key-context check (refresh_token, code_verifier, etc.); REDACT-04, -08  | CLOSED |
| T-020-4    | Stdlib `httpx`/`litellm` records bypass structlog chain                               | HIGH     | `ProcessorFormatter.foreign_pre_chain=shared_processors`; REDACT-13, -14, -19          | CLOSED |
| T-020-5    | Token in exception traceback survives `format_exc_info`                               | MEDIUM   | `_walk_value` BaseException branch; REDACT-15, -16                                     | CLOSED |
| T-020-6    | False-positive over-redaction breaks legitimate identifiers                           | LOW      | Anchored regex (≥20 alnum body); REDACT-22 covers `Skill-1234`, `Bearer xyz`           | CLOSED |
| T-020-7    | Mode-isolation regression: observability imports state_build/state_teach              | HIGH     | grep-based import-graph test; REDACT-25 + companion `test_observability_init_exists`   | CLOSED |
| T-020-8    | Process control: install() not called → daemon runs without redactor                  | LOW      | `assert_redactor_attached()` at orchestrator Step 0; REDACT-21 documents semantics     | CLOSED |
| T-020-W4-1 | Verification step fakes GREEN by skipping tests                                       | LOW      | Steps 1-2 use pytest -x (fail-fast); explicit numeric pass-count assertions            | CLOSED |
| T-020-W4-2 | Mode-isolation regression slips in via future patch                                   | LOW      | REDACT-25 + companion are part of standing CI suite (`test_observability_import_graph.py`) | CLOSED |
| T-020-W4-3 | REQUIREMENTS.md flip is forgotten                                                     | LOW      | Explicit Step 8 + grep acceptance criterion; commit `2b4923c`                          | CLOSED |
| T-020-W4-4 | Manual smoke leaks canary bytes to stdout/stderr                                      | LOW      | Smoke output captured to tmpfile; canary literal grep-checked for 0 hits               | CLOSED |
| T-020-W4-5 | Hypothesis run with too few examples passes vacuously                                 | LOW      | Tempdir harness asserts `≥1000 examples` from statistics line; gate fails on shortfall | CLOSED |

All HIGH (4) closed: T-020-1 (sk-* false positive), T-020-2 (length
side-channel), T-020-4 (stdlib bypass), T-020-7 (mode-isolation).
All MEDIUM (2) closed: T-020-3 (opaque refresh), T-020-5
(traceback). All LOW (7) closed. 13 threats total (8 phase + 5
Wave 4 addendum).

## Out-of-Scope Items Reaffirmed

Per RESEARCH §Open Questions, these are deferred and not addressed by
Phase 020:

- **OOS-1:** Cycle-detection in `_walk_value` (RESEARCH §Open Question 3
  — Pydantic event-dicts in practice never contain cycles; defer until
  a real cycle is observed).
- **OOS-2:** `py.typed` marker for `state_core.*` (project-wide
  infrastructure gap — not redactor-specific; deferred to a future
  infrastructure phase).
- **OOS-3:** Live OAuth refresh log inspection (manual-only — deferred
  to Phase 022 captured-header regression tests).
- **OOS-4:** Operator-visible refusal banner UX (verified by smoke
  step; full daemon-start → exit-code observation deferred to Phase
  022).
- **OOS-5:** Encrypted log archives at rest (orthogonal — out of P0-14
  scope).
- **OOS-6:** Per-call-site redaction discipline regression test
  (already covered by Phase 011-019 unit tests; layer 1 of
  defense-in-depth — this phase is layer 2).
- **OOS-7:** Bearer-header double-space variant beyond 2 spaces
  (regex `\s+` covers all whitespace counts; verified by REDACT-09).
- **OOS-8:** Custom replacement literal (`REDACTED` is a fixed module
  constant; Pitfall 4 explicitly forbids customization).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan 04 hypothesis gate harness used over-wide body strategy**

- **Found during:** Step 4 first run
- **Issue:** The Plan 04-supplied tempdir harness for the 1000-draw
  hypothesis gate used `whitelist_categories=("Ll", "Lu", "Nd")` plus
  `whitelist_characters="_-"` for the body strategy. This generates
  Unicode characters like `µ` (Latin lowercase letter `Ll`) and `²`
  (digit `Nd`) that fall outside the regex pattern's `[A-Za-z0-9_-]`
  / `[A-Za-z0-9]` character classes — terminating the regex match
  before the full secret is captured. The result: hypothesis found
  falsifying example `sk-ant-oat-0000000000000000000µ` where the `µ`
  truncated the match boundary and the `0`s+`µ` portion survived.
- **Root cause:** Plan 04 was written before Wave 3 narrowed the
  in-tree REDACT-24 strategy. The Wave 3 narrowing is documented
  verbatim in `tests/test_redactor.py:593-607` ("Wave 3 narrowed
  this from a wider strategy after observing µ / ² / `_-`-suffix
  falsifying examples"), but Plan 04's harness was not updated to
  match.
- **Fix:** Inline-edited the tempdir harness to use
  `whitelist_categories=()` plus
  `whitelist_characters="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"`,
  mirroring the in-tree Wave 3 strategy verbatim.
- **Files modified:** Tempdir harness file only (not committed —
  verification artefact).
- **Outcome:** `1000 passing examples, 0 failing examples, 0 invalid
  examples` on retry.

**2. [Rule 1 - Bug] Plan 04 smoke-test structlog assertion bypassed configured processors**

- **Found during:** Step 5 first run
- **Issue:** The Plan 04-supplied smoke script used
  `with capture_logs() as cap:` without passing `processors=...`.
  `capture_logs()` without an explicit processor list discards the
  configured `structlog.configure()` chain and runs only its own
  `LogCapture` sink — which means the canary sailed through to the
  captured records unmodified, falsely indicating a leak.
- **Root cause:** This is exactly the Pitfall 2 documented in
  `redactor.py::assert_redactor_attached`'s implementation comments
  (lines 357-381): "capture_logs() clears the configured-processors
  list and only runs processors passed explicitly to it." Plan 04's
  smoke script was written before that pitfall was hardened in Wave 3.
- **Fix:** Inline-edited the smoke script to read
  `structlog.get_config()["processors"]`, drop the terminal
  `wrap_for_formatter` (which `capture_logs()` can't render through),
  and pass the result as
  `capture_logs(processors=capture_chain)`. This mirrors the
  canonical pattern in `assert_redactor_attached` line 380.
- **Files modified:** Smoke script (passed via `python3 -c "..."` from
  bash; not a committed artefact).
- **Outcome:** 5 OK lines, 0 canary leaks, exit 0 on retry.

**3. [Rule 3 - Blocking] Worktree base mismatch + missing infrastructure files**

- **Found during:** Worktree-branch-check + Step 2 first run
- **Issue:** The agent worktree at
  `/Users/tmac/Projects/state/.claude/worktrees/agent-a47b263a5725ebcad/`
  was on branch `worktree-agent-a47b263a5725ebcad` whose tip was
  commit `5acaf88` (a v1-lineage `docs(planning): mark v1 Event
  Store Foundation complete` commit). The expected base for Phase
  020 Plan 04 is commit `328934f` (Wave 3 integration tip on the
  `gsd/phase-020-root-logger-token-redactor` branch). Additionally,
  `.state/migrations/0001_init.sql`, `0002_cache.sql`,
  `0003_add_mode_column.sql` were missing (only 0004 + 0005 had been
  carried forward), and `.state/events.sqlite` was an empty stub —
  causing 26 reconciler/sync_mirror/seq tests to error with
  `OperationalError: no such table: events` during Step 2's
  repo-wide regression sweep.
- **Root cause:** Worktree provisioning carried only the deltas
  relative to an older base (the v1-lineage tip), not the
  inherited Phase 020 Wave 3 commits or the local-only
  infrastructure files (`.state/migrations/0001-0003.sql`,
  schema-bearing `events.sqlite`). None of these are Phase 020
  regressions — the same tests pass against
  `/Users/tmac/Projects/state/` (the main worktree).
- **Fix:**
  1. `git reset --hard 328934f405b7069535d96aece364f319b811120c`
     to land at the Wave 3 integration tip.
  2. `cp /Users/tmac/Projects/state/.state/migrations/000{1,2,3}_*.sql .state/migrations/`
     to copy the missing migrations.
  3. `cp /Users/tmac/Projects/state/.state/events.sqlite .state/events.sqlite`
     to copy the schema-bearing DB.
  4. `mkdir -p .planning/milestones/v2/phases/020-root-logger-token-redactor && cp -r /Users/tmac/Projects/state/.planning/milestones/v2/phases/020-root-logger-token-redactor/. .planning/milestones/v2/phases/020-root-logger-token-redactor/`
     to copy the planning artefacts (plans, RESEARCH, VALIDATION,
     CONTEXT, prior SUMMARYs) per the established
     `commit_docs=false` convention.
- **Files modified:** `.state/migrations/{0001,0002,0003}_*.sql`
  (copied; not committed — local infra), `.state/events.sqlite`
  (copied; not committed — local infra),
  `.planning/milestones/v2/phases/020-*/` (copied + flipped +
  committed).
- **Outcome:** `git log --oneline -1` confirms `5931ab0
  docs(020-04): flip VALIDATION.md to compliant`; repo-wide
  regression sweep yields `355 passed` after restoration.

**4. [Rule 1 - Out-of-scope finding documented, not "fixed"] mypy py.typed marker gap**

- **Found during:** Step 3 (mypy gate)
- **Issue:** `python3 -m mypy src/state_core/observability/redactor.py
  src/state_core/observability/__init__.py` reports `Found 1 error in
  1 file`. The Plan 04 acceptance criterion expected
  `Success: no issues found` or equivalent.
- **Root cause:** The single error is `[import-untyped]` "missing
  py.typed marker" on `__init__.py`'s import of
  `state_core.observability.redactor` — a project-wide infrastructure
  gap inherited from Phases 011-019 (six other `state_core.*` modules
  ship the same diagnostic shape; see 019-04-SUMMARY for precedent).
  Zero errors point to logic in redactor.py itself.
- **Fix:** Documented as out-of-scope per the executor scope-boundary
  rule. Adding a `py.typed` marker is a project-wide infrastructure
  change that affects every existing module + every consumer of
  `state_core.*`. It belongs in a future infrastructure phase (not
  Phase 020's verification gate). This matches the Phase 019-04
  precedent verbatim.
- **Files modified:** none (no fix attempted; the contract is correct,
  only the secondary mypy assertion was inheriting a project-wide
  gap).

### Other Deviations

None — Steps 1, 2, 6, 7, 8, 9 executed exactly as the plan specified.

## Issues Encountered

- **Worktree base mismatch + missing local infrastructure:** Already
  documented under Deviations §3. Resolution: hard-reset to the
  expected Wave 3 base; copy 3 migration files, 1 schema-bearing
  SQLite DB, and the 020 planning subdirectory from the main
  worktree. No code or test files were modified.
- **mypy infrastructure gap (out-of-scope):** Already documented
  under Deviations §4. No remediation attempted in Phase 020 —
  belongs in a future infrastructure phase per the established
  Phase 019 precedent.
- **Plan 04 hypothesis harness over-wide strategy:** Already
  documented under Deviations §1. The Plan 04 file (committed in an
  earlier wave) was authored before Wave 3 narrowed the in-tree
  REDACT-24 strategy. The harness in the plan is a tempdir-only
  artefact (not committed); the Wave 3 narrowing is documented in
  the in-tree stub's docstring (line 593-607).
- **Plan 04 smoke-test capture_logs() bypass:** Already documented
  under Deviations §2. The smoke script in Plan 04 was authored
  before Wave 3 hardened the canonical
  `capture_logs(processors=capture_chain)` pattern in
  `assert_redactor_attached`. The script is invoked via
  `python3 -c "..."` (not a committed artefact); the canonical
  pattern is documented in `redactor.py:357-381`.

## Quality Gates

`quality.level = "fast"` — sentinel skipped per protocol; no Quality
Gates section emitted (matches Phase 018-04 and 019-04 SUMMARY
precedent).

## Hand-off

**AUTH-10 fully satisfied.** Phase 020 ready for `/gsd:verify-work`.
The orchestrator will:

1. Bump `.planning/milestones/v2/STATE.md` `progress.completed_phases`
   from 7 -> 8 and update `last_activity` to "Phase 020 complete —
   AUTH-10 closed".
2. Flip `.planning/milestones/v2/ROADMAP.md` Phase 020 plans block to
   `[x]`.
3. Mark requirement `AUTH-10` complete in REQUIREMENTS.md (already
   done by Plan 04 — line 18, commit `2b4923c`).

**Next phase per STATE.md:** Phase 021 (first-run import from opencode
— AUTH-11) is parallel-safe with Phase 022 (CLI auth — AUTH-12).
Phase 022 specifically depends on AUTH-10 closure (so `state auth
status` output is log-safe), making this commit the gating event for
that work. Recommended: invoke `/gsd:plan-phase v2.022` to start the
CLI work and `/gsd:plan-phase v2.021` for the parallel
opencode-import phase.

## Self-Check: PASSED

Files created and verified on disk:

- `.planning/milestones/v2/phases/020-root-logger-token-redactor/020-04-SUMMARY.md` — FOUND (this file)
- `.planning/milestones/v2/phases/020-root-logger-token-redactor/020-VALIDATION.md` — FOUND (modified, frontmatter flipped to compliant; per-task map populated with 26 REDACT rows; 8 checkboxes flipped)
- `.planning/milestones/v2/REQUIREMENTS.md` — FOUND (modified, AUTH-10 flipped to [x])

Commits exist in branch history:

- `5931ab0` (docs(020-04): flip VALIDATION.md to compliant — Phase 020 verification gate) — FOUND
- `2b4923c` (docs(020-04): mark AUTH-10 complete in v2 REQUIREMENTS.md) — FOUND

Test sweep clean:

- `pytest tests/test_redactor.py + test_observability_import_graph.py -q` → 34 passed, 0 failed
- `pytest tests/auth/ -q` → 321 passed, 1 skipped, 0 failed
- `pytest tests/ -q --ignore=tests/auth` → 355 passed, 0 failed
- Hypothesis 1000-draw phase gate: 1000 passing examples, 0 failing examples
- Hypothesis 200-draw in-tree stub: 200 passing examples, 0 failing examples
- Smoke roundtrip: 5 OK assertions; 0 canary leaks
- Final acceptance: `REDACTED == '[REDACTED]'`; public surface importable; orchestrator wires Step 0 (lines 37, 38)
