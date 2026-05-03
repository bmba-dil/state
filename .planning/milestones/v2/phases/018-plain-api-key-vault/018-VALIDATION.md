---
phase: 018
slug: plain-api-key-vault
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
completed: 2026-04-30
---

# Phase 018 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 018-RESEARCH.md `## Validation Architecture` section.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4 (+ pytest-asyncio 1.3 for symmetry; Phase 018 itself is sync) |
| **Config file** | `pyproject.toml` (existing repo-level pytest config) |
| **Quick run command** | `pytest tests/auth/test_api_key.py tests/auth/test_loader.py tests/auth/test_main_api_key.py -x -q` |
| **Full suite command** | `pytest tests/auth/ -q` |
| **Estimated runtime** | ~3 seconds (no network, no I/O beyond tmp_path) |

---

## Sampling Rate

- **After every task commit:** Run quick command (Phase 018 unit tests only)
- **After every plan wave:** Run full suite command (all `tests/auth/*`)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

All 21 rows GREEN as of 2026-04-30 (Plan 04 verification gate).
Source rows below come from RESEARCH.md `## Validation Architecture` (21 rows).

| # | Behavior under test | Requirement | Test Type | Plan/Task | Automated Command (target file) |
|---|---------------------|-------------|-----------|-----------|----------------------------------|
| 01 | empty / whitespace key rejected | AUTH-05 | unit | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_login_rejects_empty_key` PASS |
| 02 | prefix mismatch warns and stores | AUTH-05 | unit | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_login_warns_on_prefix_mismatch` PASS |
| 03 | unknown provider_id raises UnknownApiKeyProviderError | AUTH-05 | unit | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_get_api_key_auth_unknown_provider` PASS |
| 04 | vault non-empty wins over env | AUTH-05 | unit | 01-T3 + 03-T1 | `tests/auth/test_loader.py::test_vault_wins_over_env` PASS |
| 05 | vault empty list + env set → env synthesizes | AUTH-05 | unit | 01-T3 + 03-T1 | `tests/auth/test_loader.py::test_env_synthesizes_when_vault_empty` PASS |
| 06 | vault file missing + env set → env synthesizes | AUTH-05 | unit | 01-T3 + 03-T1 | `tests/auth/test_loader.py::test_env_synthesizes_when_vault_missing` PASS |
| 07 | vault missing + env unset → empty list | AUTH-05 | unit | 01-T3 + 03-T1 | `tests/auth/test_loader.py::test_returns_empty_when_no_creds_anywhere` PASS |
| 08 | empty-string env var treated as unset | AUTH-05 | unit | 01-T3 + 03-T1 | `tests/auth/test_loader.py::test_empty_env_treated_as_unset` PASS |
| 09 | append-default repeat login | AUTH-05 | unit | 01-T3 + 02-T2 | `tests/auth/test_main_api_key.py::test_login_appends_by_default` PASS |
| 10 | --replace truncates to single entry | AUTH-05 | unit | 01-T3 + 02-T2 | `tests/auth/test_main_api_key.py::test_login_replace_truncates` PASS |
| 11 | dedup on identical key string | AUTH-05 | unit | 01-T3 + 02-T2 | `tests/auth/test_main_api_key.py::test_login_dedups_identical_key` PASS |
| 12 | longest-prefix-first sniff resolves sk-ant-api03- vs sk-or- vs sk- | AUTH-05 | unit | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_sniff_resolves_sk_collision` PASS |
| 13 | http_headers Anthropic uses x-api-key | AUTH-05 | unit (parametrized) | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_http_headers[anthropic.api_key]` PASS |
| 14 | http_headers Google AI Studio uses x-goog-api-key | AUTH-05 | unit (parametrized) | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_http_headers[google.ai_studio]` PASS |
| 15 | http_headers all-others use Authorization Bearer | AUTH-05 | unit (parametrized) | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_http_headers[*]` (10 rows) PASS |
| 16 | is_expired always False | AUTH-05 | unit | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_is_expired_always_false` PASS |
| 17 | refresh(cred) returns cred unchanged | AUTH-05 | unit | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_refresh_returns_unchanged` PASS |
| 18 | _REGISTRY has all 12 expected provider_ids | AUTH-05 | unit | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_registry_has_12_providers` PASS |
| 19 | argv never contains the key (getpass / stdin only) | AUTH-05 | unit | 01-T3 + 02-T2 | `tests/auth/test_main_api_key.py::test_login_uses_getpass_or_stdin` PASS |
| 20 | ApiKeyCredential repr does not leak key (Field repr=False) | AUTH-05 | unit (Phase 011 regression) | 01-T2 + 02-T2 | `tests/auth/test_api_key.py::test_credential_repr_does_not_leak` PASS |
| 21 | import-graph: api_key.py does NOT import loader.py | AUTH-05 | architectural | 01-T3 + 02-T2 + 03-T1 | `tests/auth/test_import_graph.py::test_api_key_does_not_import_loader` PASS |

*All 21 rows GREEN — Plan 04 verification gate completed 2026-04-30.*

---

## Wave 0 Requirements

- [x] `tests/auth/test_api_key.py` — RED stubs for rows 01–03, 12–18, 20
- [x] `tests/auth/test_loader.py` — RED stubs for rows 04–08
- [x] `tests/auth/test_main_api_key.py` — RED stubs for rows 09–11, 19
- [x] `tests/auth/test_import_graph.py` — RED stub for row 21 (one-way import constraint)
- [x] `tests/auth/conftest.py` — extend if needed: tmp_path fixture for ephemeral auth.json + monkeypatched env

*Existing repo pytest infrastructure covers framework; no new framework install.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification. Live API verify against vendor endpoints is explicitly deferred to Phase 022 per CONTEXT.md `<deferred>`.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** auto-verified by Plan 04 — 2026-04-30
