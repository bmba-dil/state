---
phase: 022
slug: cli-state-auth-login-logout
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-01
---

# Phase 022 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ with pytest-asyncio 1.3+, pytest-httpx 0.35+ |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/auth -x -q` |
| **Full suite command** | `pytest tests/auth -v` |
| **Estimated runtime** | ~30 seconds (no live network — pytest-httpx mocks) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/auth -x -q`
- **After every plan wave:** Run `pytest tests/auth -v`
- **Before `/gsd:verify-work`:** Full suite must be green + golden-file diff clean
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Filled in during planning by gsd-planner. Each task gets a row mapped to AUTH-12 / AUTH-13 + a quick automated command.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 022-01-* | 01 | 1 | AUTH-13 | unit/integration | `pytest tests/auth/test_p0_regression.py -x` | ❌ W0 | ⬜ pending |
| 022-02-* | 02 | 2 | AUTH-12 | unit | `pytest tests/auth/test_cli_ops.py -x` | ❌ W0 | ⬜ pending |
| 022-03-* | 03 | 3 | AUTH-12 | integration | `pytest tests/auth/test_cli_typer.py -x` | ❌ W0 | ⬜ pending |
| 022-04-* | 04 | 3 | AUTH-12, AUTH-13 | gate | `pytest tests/auth -v` + import-graph check | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

**P0 regression stubs (AUTH-13)** — all 9 must be in `tests/auth/test_p0_regression.py` with exact names:

- [ ] `test_p0_1_user_agent_stealth` — defends against user-agent header drift on Anthropic stealth calls
- [ ] `test_p0_2_anthropic_beta_full_string` — defends against anthropic-beta value truncation
- [ ] `test_p0_3_x_app_cli` — defends against x-app header omission
- [ ] `test_p0_4_bearer_not_x_api_key` — defends against x-api-key leakage on OAuth calls
- [ ] `test_p0_5_client_id_base64_decoded` — defends against _CLIENT_ID constant corruption
- [ ] `test_p0_6_filelock_acquire_timeout` — defends against filelock TOCTOU / non-termination
- [ ] `test_p0_7_five_minute_expiry_buffer` — defends against expiry-buffer regression (5-min window)
- [ ] `test_p0_8_pkce_state_equals_verifier` — defends against Anthropic PKCE state/verifier split
- [ ] `test_p0_13_chmod_0600_verified_on_read` — defends against chmod-0600 bypass on vault read

**CLI ops-layer stubs (AUTH-12)** — `tests/auth/test_cli_ops.py`:

- [ ] `test_login_anthropic_oauth_returns_credential` — turns GREEN in Plan 02
- [ ] `test_login_openai_api_key_returns_api_key_credential` — turns GREEN in Plan 02
- [ ] `test_login_unknown_provider_raises_unknown_error` — turns GREEN in Plan 02
- [ ] `test_login_emits_auth_logged_in_event` — turns GREEN in Plan 02
- [ ] `test_logout_removes_credential_from_vault` — turns GREEN in Plan 02
- [ ] `test_logout_all_flag_wipes_provider_array` — turns GREEN in Plan 02
- [ ] `test_logout_emits_auth_logged_out_event` — turns GREEN in Plan 02
- [ ] `test_logout_no_creds_returns_zero` — turns GREEN in Plan 02
- [ ] `test_status_returns_status_report` — turns GREEN in Plan 02
- [ ] `test_status_provider_id_filter` — turns GREEN in Plan 02
- [ ] `test_status_source_column_from_extras` — turns GREEN in Plan 02
- [ ] `test_status_expired_only_filter` — turns GREEN in Plan 02
- [ ] `test_status_ordering_alphabetical_then_source` — turns GREEN in Plan 02
- [ ] `test_cli_ops_import_succeeds` — turns GREEN in Plan 02

**Typer command stubs (AUTH-12)** — `tests/auth/test_cli_typer.py`, all turn GREEN in Plan 03:

- [ ] `test_state_auth_login_exits_64_on_non_tty`
- [ ] `test_state_auth_login_alias_claude_normalizes_to_anthropic`
- [ ] `test_state_auth_login_unknown_provider_exits_64`
- [ ] `test_state_auth_login_exits_130_on_keyboard_interrupt`
- [ ] `test_state_auth_login_stealth_rejected_exits_3`
- [ ] `test_state_auth_login_vault_permission_error_exits_77`
- [ ] `test_state_auth_logout_single_cred_prompts_confirmation`
- [ ] `test_state_auth_logout_yes_flag_skips_prompt`
- [ ] `test_state_auth_logout_all_flag_requires_yes`
- [ ] `test_state_auth_status_human_table_5_columns`
- [ ] `test_state_auth_status_json_schema_field`
- [ ] `test_state_auth_status_provider_filter`
- [ ] `test_state_auth_status_no_color_disables_ansi`
- [ ] `test_auth_app_registered_in_main`
- [ ] `test_login_no_arg_shows_picker` (CONTEXT.md picker, 16 rows, anthropic twice, exit 130 on ^C)

**Import-graph extension** — `tests/auth/test_import_graph.py`:

- [ ] `test_state_cli_auth_one_way_edge` (VALIDATION 022-row-A) — `state_cli.auth` may import `state_core.auth.*` but NOT `state_build.*`/`state_teach.*`
- [ ] `test_cli_ops_no_state_cli_imports` (VALIDATION 022-row-B) — `state_core.auth.cli_ops` must NOT import `state_cli.*`

**Infrastructure:**

- [ ] `tests/auth/golden/<provider>/` — directory layout for golden JSON fixtures
- [ ] `tests/auth/conftest.py` — `golden_load`, `--update-goldens` pytest_addoption hook, `json_dump_deterministic` (Bearer scrubber), `fake_oauth_cred`, `fake_api_key_cred`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive provider picker (numbered list, KeyboardInterrupt → 130) | AUTH-12 | TTY interaction; pytest-httpx cannot mock stdin gracefully | Run `state auth login` in a real terminal, hit Ctrl-C at picker, confirm exit 130 |
| Real opencode-import smoke (3 creds: opencode, openrouter, deepseek on dev box) | AUTH-12 | Depends on `~/.local/share/opencode/auth.json` actual state | Run `state auth status` after Phase 021 importer runs; confirm 3 rows with `source: opencode-import` |
| Live mitmproxy capture vs goldens | AUTH-13 | Confirms goldens match real upstream — pytest-httpx mocks could drift | Pre-merge: capture one anthropic refresh through mitmproxy, byte-compare to `tests/auth/golden/anthropic/refresh.json` |
| Rich Table rendering (color thresholds, `--no-color`, 80-col fit) | AUTH-12 | Visual; terminal width + color env-var sensitive | Run `state auth status` with/without `NO_COLOR=1`; visual inspect at 80 cols |
| `--from-stdin` per-provider grammar (api-key vs anthropic code#state vs copilot device-code answer) | AUTH-12 | Pipe input + non-TTY detection — partially automated, full coverage needs shell pipes | `echo $KEY \| state auth login openai --from-stdin` etc. for each provider class |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test stubs + golden fixture skeletons + conftest hooks)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
