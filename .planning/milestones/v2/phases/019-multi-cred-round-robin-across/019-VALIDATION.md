---
phase: 019
slug: multi-cred-round-robin-across
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
completed: 2026-04-30
---

# Phase 019 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ + pytest-asyncio 1.3+ + hypothesis 6.120+ |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/auth/test_rotation.py -x -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~5–15 seconds |

---

## Sampling Rate

- **After every task commit:** pytest tests/auth/test_rotation.py -x -q
- **After every plan wave:** pytest tests/auth/ -x -q
- **Before `/gsd:verify-work`:** full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 019-01-ROTATE-01 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_select_n1_returns_idx0_and_bumps -x` | ✅ | ✅ green |
| 019-02-ROTATE-02 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_select_empty_raises -x` | ✅ | ✅ green |
| 019-03-ROTATE-03 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_select_missing_provider_raises -x` | ✅ | ✅ green |
| 019-04-ROTATE-04 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_bucket_advances_with_time -x` | ✅ | ✅ green |
| 019-05-ROTATE-05 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_last_rotation_persisted -x` | ✅ | ✅ green |
| 019-06-ROTATE-06 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_array_shape_preserved_after_selection -x` | ✅ | ✅ green |
| 019-07-ROTATE-07 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_cool_down_skipped_on_next_selection -x` | ✅ | ✅ green |
| 019-08-ROTATE-08 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_cool_down_auto_expires -x` | ✅ | ✅ green |
| 019-09-ROTATE-09 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_all_cooled_down_raises_with_earliest -x` | ✅ | ✅ green |
| 019-10-ROTATE-10 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_clear_rate_limited_removes_entry -x` | ✅ | ✅ green |
| 019-11-ROTATE-11 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_last_rotation_modulo_clamp -x` | ✅ | ✅ green |
| 019-12-ROTATE-12 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_mark_zero_until_clears -x` | ✅ | ✅ green |
| 019-13-ROTATE-13 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_bare_dict_coerced_p1_7 -x` | ✅ | ✅ green |
| 019-14-ROTATE-14 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_migration_preserves_last_rotation -x` | ✅ | ✅ green |
| 019-15-ROTATE-15 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_cool_down_lost_on_module_reimport -x` | ✅ | ✅ green |
| 019-16-ROTATE-16 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_iter_active_yields_bucket_order -x` | ✅ | ✅ green |
| 019-17-ROTATE-17 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_iter_active_skips_cool_down -x` | ✅ | ✅ green |
| 019-18-ROTATE-18 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_iter_active_does_not_lock -x` | ✅ | ✅ green |
| 019-19-ROTATE-19 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_select_lock_timeout_raises -x` | ✅ | ✅ green |
| 019-20-ROTATE-20 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_select_reentrant_deadlock_raises -x` | ✅ | ✅ green |
| 019-21-ROTATE-21 | 01-T3 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_import_graph.py::test_rotation_no_mode_imports -x` | ✅ | ✅ green |
| 019-22-ROTATE-22 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_select_calls_save_vault_once -x` | ✅ | ✅ green |
| 019-23-ROTATE-23 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_every_cred_selected_over_n_rounds -x` | ✅ | ✅ green |
| 019-24-ROTATE-24 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_last_rotation_invariant -x` | ✅ | ✅ green |
| 019-25-ROTATE-25 | 01-T2 + 03-T1 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_select_deterministic_for_fixed_now -x` | ✅ | ✅ green |
| 019-26-ROTATE-26 | 01-T2 + 03-T2 | 1+3 | AUTH-08 | unit | `pytest tests/auth/test_rotation.py::test_public_reexports -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] tests/auth/test_rotation.py — stubs for ROTATE-01..ROTATE-26
- [x] tests/auth/conftest.py — _clear_cool_down + busy_lock_holder + vault_with_three_oauth + vault_with_three_api_keys fixtures
- [x] tests/auth/test_import_graph.py — extended with test_rotation_no_mode_imports + test_rotation_imports_only_allowed_targets (ROTATE-21)

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** auto-verified by Plan 04 — 2026-04-30
