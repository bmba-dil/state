---
phase: 020
slug: root-logger-token-redactor
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-01
completed: 2026-04-30
---

# Phase 020 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. The 26 REDACT-NN rows below come from `020-RESEARCH.md §Validation Architecture` (canonical source of truth). Each row is enforced by an automated test row (or marked manual with rationale).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ + hypothesis 6.120+ + structlog 25.1+ |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_redactor.py tests/test_observability_import_graph.py -x -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | quick ~5s · full ~50s |

---

## Sampling Rate

- After every task commit: pytest tests/test_redactor.py -x -q
- After every plan wave: pytest tests/ -q
- Before /gsd:verify-work: full suite must be green
- Max feedback latency: 15 seconds

---

## Per-Task Verification Map

| Task ID       | Plan         | Wave | Requirement | Test Type   | Automated Command                                                         | File Exists | Status   |
|---------------|--------------|------|-------------|-------------|---------------------------------------------------------------------------|-------------|----------|
| 020-01-REDACT-01 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_anthropic_oat -x`            | ✅           | ✅ green |
| 020-02-REDACT-02 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_anthropic_api_key -x`        | ✅           | ✅ green |
| 020-03-REDACT-03 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_openai_generic -x`           | ✅           | ✅ green |
| 020-04-REDACT-04 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_opaque_refresh_by_key -x`    | ✅           | ✅ green |
| 020-05-REDACT-05 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_google_ya29 -x`              | ✅           | ✅ green |
| 020-06-REDACT-06 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_google_refresh_1slash -x`    | ✅           | ✅ green |
| 020-07-REDACT-07 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_github_copilot -x`           | ✅           | ✅ green |
| 020-08-REDACT-08 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_opaque_antigravity_refresh -x` | ✅         | ✅ green |
| 020-09-REDACT-09 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_bearer_header_variants -x`   | ✅           | ✅ green |
| 020-10-REDACT-10 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_authorization_header_dict -x`| ✅           | ✅ green |
| 020-11-REDACT-11 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_nested_dict_secret -x`       | ✅           | ✅ green |
| 020-12-REDACT-12 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_list_value -x`               | ✅           | ✅ green |
| 020-13-REDACT-13 | 01-T2 + 03-T1 | 0+3  | AUTH-10     | integration | `pytest tests/test_redactor.py::test_redacts_stdlib_httpx_record -x`      | ✅           | ✅ green |
| 020-14-REDACT-14 | 01-T2 + 03-T1 | 0+3  | AUTH-10     | integration | `pytest tests/test_redactor.py::test_redacts_stdlib_litellm_record -x`    | ✅           | ✅ green |
| 020-15-REDACT-15 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_exception_message -x`        | ✅           | ✅ green |
| 020-16-REDACT-16 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_redacts_traceback_chain -x`          | ✅           | ✅ green |
| 020-17-REDACT-17 | 01-T2 + 03-T1 | 0+3  | AUTH-10     | integration | `pytest tests/test_redactor.py::test_jsonrenderer_output_clean -x`        | ✅           | ✅ green |
| 020-18-REDACT-18 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | structural  | `pytest tests/test_redactor.py::test_processor_at_position_zero -x`       | ✅           | ✅ green |
| 020-19-REDACT-19 | 01-T2 + 03-T1 | 0+3  | AUTH-10     | structural  | `pytest tests/test_redactor.py::test_processorformatter_attached_to_root -x` | ✅        | ✅ green |
| 020-20-REDACT-20 | 01-T2 + 03-T1 | 0+3  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_selfcheck_passes_when_installed -x`  | ✅           | ✅ green |
| 020-21-REDACT-21 | 01-T2 + 03-T1 | 0+3  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_selfcheck_fails_when_not_installed -x` | ✅         | ✅ green |
| 020-22-REDACT-22 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_negative_no_overredaction -x`        | ✅           | ✅ green |
| 020-23-REDACT-23 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | unit        | `pytest tests/test_redactor.py::test_install_idempotent -x`               | ✅           | ✅ green |
| 020-24-REDACT-24 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | property    | `pytest tests/test_redactor.py::test_hypothesis_secrets_never_survive -x` | ✅           | ✅ green |
| 020-25-REDACT-25 | 01-T1 + 02-T1 | 0+2  | AUTH-10     | structural  | `pytest tests/test_observability_import_graph.py::test_observability_no_mode_imports -x` | ✅ | ✅ green |
| 020-26-REDACT-26 | 01-T2 + 02-T2 | 0+2  | AUTH-10     | regression  | `pytest tests/test_redactor.py::test_existing_auth_log_calls_still_render -x` | ✅       | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Validation Architecture (REDACT-01..REDACT-26)

Source of truth: `020-RESEARCH.md §Validation Architecture`. Each row maps to a named test function in `tests/test_redactor.py` or `tests/test_observability_import_graph.py`. Row IDs and semantics MUST match RESEARCH byte-for-byte — Plan 01 named-test functions follow this mapping.

| ID | What it asserts | Wave | Test target | Test function |
|----|----------------|------|-------------|---------------|
| REDACT-01 | Anthropic OAuth access token (`sk-ant-oat-…`) redacted in event_dict value | 2 | unit | `test_redacts_anthropic_oat` |
| REDACT-02 | Anthropic API key (`sk-ant-api03-…`) redacted | 2 | unit | `test_redacts_anthropic_api_key` |
| REDACT-03 | Generic OpenAI key (`sk-` ≥ 40 chars) redacted | 2 | unit | `test_redacts_openai_generic` |
| REDACT-04 | Anthropic OAuth refresh (opaque, no prefix) redacted via key-context (`refresh_token` key) | 2 | unit | `test_redacts_opaque_refresh_by_key` |
| REDACT-05 | Google OAuth access (`ya29.…`) redacted | 2 | unit | `test_redacts_google_ya29` |
| REDACT-06 | Google OAuth refresh (`1//…`) redacted | 2 | unit | `test_redacts_google_refresh_1slash` |
| REDACT-07 | GitHub Copilot device-code token (`gho_…` / `ghu_…` / `ghs_…` / `ghp_…`) redacted | 2 | unit | `test_redacts_github_copilot` |
| REDACT-08 | Antigravity / Copilot opaque refresh redacted via key-context | 2 | unit | `test_redacts_opaque_antigravity_refresh` |
| REDACT-09 | Bearer header (`Bearer sk-ant-oat-…`) redacted including double-space variant | 2 | unit | `test_redacts_bearer_header_variants` |
| REDACT-10 | HTTP-header dict with `Authorization` key redacted via key-context | 2 | unit | `test_redacts_authorization_header_dict` |
| REDACT-11 | Nested-dict secret (token inside `{"request": {"headers": {"x-api-key": "sk-ant-api03-..."}}}`) redacted | 2 | unit | `test_redacts_nested_dict_secret` |
| REDACT-12 | Secret in `list` value redacted (e.g. `event_dict["tokens_seen"] = ["sk-ant-oat-...", ...]`) | 2 | unit | `test_redacts_list_value` |
| REDACT-13 | Secret in stdlib `httpx`-style record (`logging.getLogger("httpx").debug(..., extra={"headers": {...}})`) redacted via ProcessorFormatter foreign_pre_chain | 3 | integration | `test_redacts_stdlib_httpx_record` |
| REDACT-14 | Secret in stdlib `litellm`-style record (`logging.getLogger("LiteLLM").debug("payload: ...")`) redacted | 3 | integration | `test_redacts_stdlib_litellm_record` |
| REDACT-15 | Secret in raised exception's `str()` redacted | 2 | unit | `test_redacts_exception_message` |
| REDACT-16 | Secret in exception traceback chain (`exc_info=True` path through `format_exc_info`) redacted | 3 | unit | `test_redacts_traceback_chain` |
| REDACT-17 | Final JSONRenderer output does not contain any token-shape regex match (belt-and-braces) | 3 | integration | `test_jsonrenderer_output_clean` |
| REDACT-18 | `redact_processor` is at position 0 in `structlog.get_config()["processors"]` after `install()` | 3 | structural | `test_processor_at_position_zero` |
| REDACT-19 | `ProcessorFormatter` is attached to the stdlib root logger after `install()`, with `redact_processor` in its `foreign_pre_chain` | 3 | structural | `test_processorformatter_attached_to_root` |
| REDACT-20 | `assert_redactor_attached()` returns successfully when `install()` has run | 3 | unit | `test_selfcheck_passes_when_installed` |
| REDACT-21 | `assert_redactor_attached()` raises `RedactorNotAttached` when `install()` has NOT run (resets defaults first); orchestrator startup aborts before Step 1 | 3 | unit | `test_selfcheck_fails_when_not_installed` |
| REDACT-22 | Negative test: `sk-foundation`, `sk-2`, `Bearer xyz` (length < 20), `Skill-1234` are NOT redacted | 2 | unit | `test_negative_no_overredaction` |
| REDACT-23 | `install()` is idempotent — calling it twice does not duplicate handlers or processors | 3 | unit | `test_install_idempotent` |
| REDACT-24 | Hypothesis property test: for any string generated by the secret-shaped strategy, `_redact_string(s)` does not contain the input | 2 | property | `test_hypothesis_secrets_never_survive` |
| REDACT-25 | Mode-isolation lint: `state_core.observability.*` does NOT import `state_build.*` or `state_teach.*` (also `state.build` / `state.teach` dotted variants) | 1 | structural | `test_observability_no_mode_imports` |
| REDACT-26 | Existing `tests/auth/conftest.py::_isolate_structlog_for_auth_tests` fixture still works after `install()` lands (regression check on state_core.auth.* log calls rendering correctly) | 3 | regression | `test_existing_auth_log_calls_still_render` |

---

## Token-shape × wiring-point coverage matrix

(How REDACT-01..17 cover the cartesian product. Mirrors RESEARCH §Validation Architecture matrix.)

| Token shape \ wiring point | event_dict str value | nested dict | list/tuple | exception repr | stdlib record | JSON renderer output |
|---|---|---|---|---|---|---|
| sk-ant-oat- (Anthropic access) | REDACT-01 | REDACT-11 | REDACT-12 | REDACT-15 | REDACT-13 | REDACT-17 |
| sk-ant-api03- (Anthropic API) | REDACT-02 | REDACT-11 | — | — | — | REDACT-17 |
| sk-… (OpenAI generic) | REDACT-03 | — | — | — | REDACT-14 | REDACT-17 |
| Anthropic refresh (opaque) | REDACT-04 (key-context) | — | — | — | — | REDACT-17 |
| ya29.… (Google access) | REDACT-05 | — | — | — | — | — |
| 1//… (Google refresh) | REDACT-06 | — | — | — | — | — |
| gho_/ghu_/ghs_/ghp_ (GitHub) | REDACT-07 | — | — | — | — | — |
| Antigravity/Copilot opaque | REDACT-08 (key-context) | — | — | — | — | — |
| Bearer header value | REDACT-09 | REDACT-10 (key-context) | — | — | REDACT-13 | REDACT-17 |

---

## Wave 1 Requirements

(Test scaffolds — the RED stubs that drive the GREEN implementation.)

- [x] tests/test_redactor.py — RED stubs for REDACT-01..REDACT-24, REDACT-26
- [x] tests/test_observability_import_graph.py — RED stub for REDACT-25

*Existing infrastructure: pytest, hypothesis, structlog all already pinned and used in `tests/auth/`. No framework install needed.*

---

## Manual-Only Verifications

Daemon-start refusal banner is verified by smoke step in Plan 04 Step 5 (negative path raises RedactorNotAttached); live OAuth refresh log inspection deferred to Phase 022 captured-header regression tests.

---

## Validation Sign-Off

- [x] All tasks have <automated> verify or Wave 1 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 1 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] nyquist_compliant: true set in frontmatter

**Approval:** auto-verified by Plan 04 — 2026-04-30
