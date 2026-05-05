---
phase: 27
slug: model-profile-resolver
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ with `asyncio_mode = "auto"` (already configured in `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run python3 -m pytest tests/test_model_profile.py tests/test_hooks.py -x -q` |
| **Full suite command** | `uv run python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python3 -m pytest tests/test_model_profile.py tests/test_hooks.py -x -q`
- **After every plan wave:** Run `uv run python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 027-01-01 | 01 | 0 | PRV-04 | unit | `uv run python3 -m pytest tests/test_model_profile.py -x -q` | ❌ W0 | ⬜ pending |
| 027-01-02 | 01 | 0 | PRV-04 | unit | `uv run python3 -m pytest tests/test_hooks.py -x -q` | ❌ W0 | ⬜ pending |
| 027-01-03 | 01 | 1 | PRV-04 | unit+property | `uv run python3 -m pytest tests/test_model_profile.py -x -q` | ❌ W0 | ⬜ pending |
| 027-01-04 | 01 | 1 | PRV-04 | unit | `uv run python3 -m pytest tests/test_hooks.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_model_profile.py` — 17 RED stubs for PRV-04 behavioral tests
- [ ] `tests/test_hooks.py` — 2 RED stubs for `/hook/chat-params`
- [ ] `src/state_core/providers/model_profile.py` — new file skeleton (Wave 1 implements GREEN)
- [ ] `src/state_daemon/hooks.py` — new file skeleton (Wave 1 implements GREEN)

*(No framework gaps — pytest, asyncio_mode, hypothesis all already installed and configured.)*

---

## Full Test Coverage Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| PRV-04 | `ModelProfile` enum has exactly `quality`, `balanced`, `budget`, `inherit` members | unit | `pytest tests/test_model_profile.py::test_model_profile_members -x` | ❌ Wave 0 |
| PRV-04 | `ResolvedProfile` is a frozen Pydantic model with required fields | unit | `pytest tests/test_model_profile.py::test_resolved_profile_frozen -x` | ❌ Wave 0 |
| PRV-04 | `_DEFAULTS` covers exactly the three non-inherit profiles | unit | `pytest tests/test_model_profile.py::test_defaults_coverage -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` never returns `profile=inherit` | property | `pytest tests/test_model_profile.py::test_resolve_never_returns_inherit -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` step-level non-inherit wins over all outer scopes | property | `pytest tests/test_model_profile.py::test_step_non_inherit_wins_over_all -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` phase-level profile applies when step/slice are inherit | unit | `pytest tests/test_model_profile.py::test_phase_profile_applies_when_step_inherit -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` arc-level profile applies when step/slice/phase are inherit | unit | `pytest tests/test_model_profile.py::test_arc_profile_applies_when_inner_inherit -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` all inherit/None falls back to `balanced` | unit | `pytest tests/test_model_profile.py::test_all_inherit_falls_back_to_balanced -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` global_profile override respected when all scopes are inherit | unit | `pytest tests/test_model_profile.py::test_global_profile_override -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile(overrides={"temperature": 0.9})` applies the field override | unit | `pytest tests/test_model_profile.py::test_overrides_applied -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile(overrides={"temperature": "warm"})` raises Pydantic ValidationError | unit | `pytest tests/test_model_profile.py::test_invalid_override_raises -x` | ❌ Wave 0 |
| PRV-04 | `build_chat_params()` returns camelCase keys (`topP`, `maxOutputTokens`) | unit | `pytest tests/test_model_profile.py::test_build_chat_params_camelcase_keys -x` | ❌ Wave 0 |
| PRV-04 | `build_chat_params()` quality profile includes `options.thinking_budget_tokens` | unit | `pytest tests/test_model_profile.py::test_quality_profile_includes_thinking_budget -x` | ❌ Wave 0 |
| PRV-04 | `build_chat_params()` balanced profile has empty `options` dict | unit | `pytest tests/test_model_profile.py::test_balanced_profile_empty_options -x` | ❌ Wave 0 |
| PRV-04 | `/hook/chat-params` HTTP stub returns JSON with correct shape | unit | `pytest tests/test_hooks.py::test_chat_params_handler_returns_valid_shape -x` | ❌ Wave 0 |
| PRV-04 | `/hook/chat-params` with no step_profile returns balanced defaults | unit | `pytest tests/test_hooks.py::test_chat_params_default_profile -x` | ❌ Wave 0 |
| PRV-04 | `/hook/chat-params` with step_profile=quality returns quality temperature (0.2) | unit | `pytest tests/test_hooks.py::test_chat_params_quality_profile -x` | ❌ Wave 0 |
| PRV-04 | Mode isolation: `state_core.providers.model_profile` does NOT import `state_build.*` or `state_teach.*` | import-graph | `pytest tests/test_model_profile.py::test_no_mode_silo_import -x` | ❌ Wave 0 |

**Total: 19 tests** — all RED in Wave 0; Wave 1 turns them GREEN.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Model string defaults match current Anthropic model IDs | PRV-04 | Model strings (`claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`) may change with Anthropic releases | Verify defaults in `_DEFAULTS` match current Anthropic model naming at Phase 031 parity-test time |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
