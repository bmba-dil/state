---
milestone: v2
milestone_name: Auth Coverage
audited: 2026-05-02T23:30:00Z
status: tech_debt
scores:
  requirements: 13/13
  phases: 15/15
  integration: 5/5
  flows: 5/5
gaps: {}
tech_debt:
  - phase: 014-anthropic-oauth-provider
    items:
      - "Pre-merge mitmproxy capture gate (manual, owned by user; release-time)"
  - phase: 015-gemini-cli-oauth-provider
    items:
      - "Live Google OAuth login + refresh smoke (manual, deferred to release-smoke)"
  - phase: 016-antigravity-oauth-provider
    items:
      - "Live Antigravity OAuth login + refresh smoke (manual, deferred to release-smoke)"
  - phase: 017-github-copilot-device-code-flow
    items:
      - "Live device-code login smoke (optional, deferred to release-smoke)"
  - phase: 022.1-nyquist-typing-hygiene
    items:
      - "VALIDATION.md not authored (gap-closure phase ran without research; acceptable per plan-phase Step 5.5)"
  - phase: 022.2-deferred-low-auth-threats
    items:
      - "VALIDATION.md not authored (gap-closure phase ran without research; acceptable per plan-phase Step 5.5)"
  - phase: 022.3-reviewer-cleanup
    items:
      - "VALIDATION.md not authored (gap-closure phase ran without research; acceptable per plan-phase Step 5.5)"
  - project_wide:
      - "Retroactive SECURITY.md authoring for phases 011..022 + 022.1 + 022.2 (security_enforcement was enabled mid-milestone; only 022.3 has SECURITY.md so far)"
      - "Phase 022 P0-2: claude-code-20250219 anthropic-beta flag was removed in Claude Code 2.1.121 — captures live state, not a static spec (informational)"
nyquist:
  compliant_phases: [011, 012, 013, 014, 015, 016, 017, 018, 019, 020, 021, 022]
  partial_phases: []
  missing_phases: [022.1, 022.2, 022.3]
  overall: compliant_with_acceptable_exceptions
closed_since_prior_audit:
  - "WK-01..06 (Phase 020 worth-knowing items): closed in Phase 022.3 (commits 874a1ff..fa2ea7b, 2026-05-02)"
  - "WR-01..03 (Phase 021 warnings): already closed 2026-05-01 in commits bdbc271/3f86a9d/0cdb200 — prior audit was stale"
  - "T-018-8 (vault-file race): closed in Phase 022.2 (with_vault_lock + concurrent-writer regression suite)"
  - "T-018-9 (symlink attack on auth.json): closed in Phase 022.2"
  - "VALIDATION.md frontmatter flips on 014/015/016/017/022 (nyquist_compliant, wave_0_complete): closed in Phase 022.1"
  - "Phase 021 VALIDATION.md (was missing entirely): authored in Phase 022.1"
  - "py.typed marker on src/state_core/: present at src/state_core/py.typed"
  - "Phase 022 P0-3 conftest fixture drop: already fixed in commit 3cafc5a per prior audit"
---

# Milestone v2 — Audit Report

**Milestone:** v2 — Auth Coverage (5 Methods + Multi-Cred)
**Audited:** 2026-05-02 (re-audit after gap-closure phases 022.1, 022.2, 022.3)
**Status:** ⚡ **tech_debt** (no blockers; remaining items are intentionally-deferred release-time manual gates + retroactive SECURITY.md authoring)

All 13 AUTH-XX requirements satisfied. All 15 phases verified passed. All 5 cross-phase E2E flows wired end-to-end against live source. All 5 cardinal-rule grep gates PASS. The gap-closure phases (022.1 / 022.2 / 022.3) closed every code-quality and threat-model item flagged in the prior 2026-05-02 06:30 audit. The remaining `tech_debt` classification reflects exactly two categories: (a) release-process manual smoke gates that are intentional, and (b) retroactive SECURITY.md authoring for phases that completed before the security-enforcement gate was enabled.

---

## Requirements Coverage (3-Source Cross-Reference)

| REQ-ID | Description | Phase | VERIFICATION | SUMMARY tags | REQUIREMENTS.md | Final |
|---|---|---|---|---|---|---|
| AUTH-01 | Anthropic OAuth stealth (claude-cli, anthropic-beta, PKCE state==verifier, client_id 9d1c250a-…) | 014 | passed | 014-01,02,03 | `[x]` | **satisfied** |
| AUTH-02 | Gemini CLI OAuth (google-auth-oauthlib, refresh rotation) | 015 | passed | 015-01..04 | `[x]` | **satisfied** |
| AUTH-03 | Antigravity OAuth (FIXED port 51121, 5 scopes) | 016 | passed | 016-01..04 | `[x]` | **satisfied** |
| AUTH-04 | GitHub Copilot device-code (RFC 8628 polling) | 017 | passed | 017-01..04 | `[x]` | **satisfied** |
| AUTH-05 | Plain API-key vault (12 providers) | 018 | passed | 018-04 | `[x]` | **satisfied** |
| AUTH-06 | auth.json chmod 0600 (os.open + os.fchmod) | 012 | passed | 012-01,02 | `[x]` | **satisfied** |
| AUTH-07 | Filelock-guarded refresh (10s acquire, double-check) | 013 | passed | (013-02 frontmatter) | `[x]` | **satisfied** |
| AUTH-08 | Multi-cred round-robin across credentials | 019 | passed | 019-02,03,04 | `[x]` | **satisfied** |
| AUTH-09 | 5-min token expiry buffer | 013 | passed | 016-03, 017-02 | `[x]` | **satisfied** |
| AUTH-10 | Root-logger token redactor (12 regex shapes; WK-01..06 hardened in 022.3) | 020 + 022.3 | passed | 020-02,03,04; 022.3-01 | `[x]` | **satisfied** |
| AUTH-11 | First-run import from opencode auth.json | 021 | passed | 021-02,03 | `[x]` | **satisfied** |
| AUTH-12 | `state auth login\|logout\|status` CLI | 022 | passed | 022-01,02,03 | `[x]` | **satisfied** |
| AUTH-13 | Captured-header golden regression suite | 022 + 014 + 016 + 017 | passed | 022-01,04 + 014-02, 016-02, 017-04 | `[x]` | **satisfied** |

**Score: 13/13 requirements satisfied. No orphaned, unsatisfied, or partial requirements.**

---

## Phase Verification Summary

| Phase | Slug | Status | Score | Notes |
|---|---|---|---|---|
| 011 | state-core-auth-base | passed | 11/11 | Foundation contract (BASE-01..11) |
| 012 | auth-json-vault-chmod-0600 | passed | 6/6 | AUTH-06; P0-13 owned |
| 013 | filelock-guarded-refresh-lock | passed | 9/9 | AUTH-07, AUTH-09; P0-6, P0-7 owned |
| 014 | anthropic-oauth-provider | passed | 14/14 | AUTH-01; P0-1..5, P0-7, P0-8 owned |
| 015 | gemini-cli-oauth-provider | passed | 12/12 | AUTH-02; P1-3, P2-2 owned |
| 016 | antigravity-oauth-provider | passed | 11/11 | AUTH-03; FIXED port 51121 |
| 017 | github-copilot-device-code-flow | passed | 16/16 | AUTH-04; RFC 8628 §3.5 |
| 018 | plain-api-key-vault | passed | 9/9 | AUTH-05; 12-row registry |
| 019 | multi-cred-round-robin-across | passed | 8/8 | AUTH-08; 26 ROTATE rows |
| 020 | root-logger-token-redactor | passed | 9/9 | AUTH-10; 12-pattern regex set |
| 021 | first-run-import-opencode-local | passed | 23/23 | AUTH-11; daemon Step 0.5 wiring |
| 022 | cli-state-auth-login-logout | passed | 23/23 | AUTH-12, AUTH-13; 9 P0 + 6 goldens |
| 022.1 | nyquist-typing-hygiene | passed | 4/4 | mypy py.typed + frontmatter flips on 014/015/016/017/022; 021 VALIDATION.md authored |
| 022.2 | deferred-low-auth-threats | passed | 15/15 | T-018-8 (vault-file race), T-018-9 (symlink attack) closed |
| 022.3 | reviewer-cleanup | passed | 6/6 | WK-01..06 (cycle guard, pattern-order test, NamedTuple support, docstring polish, install level kwarg, formatter precision) |

**15/15 phases passed. Zero critical blockers, zero unverified phases.**

---

## Cross-Phase Integration

All five end-to-end flows verified by `gsd-integration-checker` against live source on 2026-05-02:

| Flow | Wiring Chain | Status |
|---|---|---|
| **F1: Login** | `state_cli/auth.py` → `cli_ops.login()` → `<Provider>Auth().login()` → `with_vault_lock` (T-018-8) → `save_vault()` (chmod 0600 + O_NOFOLLOW + os.fchmod) → `_emit_auth_event()` | ✓ COMPLETE |
| **F2: Status** | `state_cli/auth.py` → `cli_ops.status()` → `load_vault()` (`_verify_mode 0o600 + symlink reject`) → per-cred `is_expired_buffered(now=now)` → `state.auth.status/v1` envelope | ✓ COMPLETE |
| **F3: Import** | daemon `startup()` → `install()` → `assert_redactor_attached()` → `import_from_opencode()` (`_source=opencode-import`) → `auth.imported` events → CLI status surfaces source | ✓ COMPLETE |
| **F4: Refresh** | `is_expired_buffered(buffer=300.0)` → `refresh_credential()` (`new_async_lock` 10s + double-check) → `provider.refresh()` (15s timeout) → `save_vault()` | ✓ COMPLETE |
| **F5: Rate-limit** | `select_credential()` → `_pick_active_index` → `mark_rate_limited(until=...)` → next select skips → `NoCredentialsAvailableError(reason="all_cooled_down", earliest_available_at=...)` | ✓ COMPLETE |

**Daemon boot order (`src/state_daemon/orchestrator.py:48-86`):** `install()` → `assert_redactor_attached()` → `SqliteEventStore()` + `SyncEventMirror()` (constructors are effect-free; lazy connect) → `import_from_opencode(store, mirror)` → `store.run_repair_now()` → `migrate()` → `StartupReconciler().start()` ✓

**Cardinal-rule grep gates (all PASS):**
- `state_build` / `state_teach` imports under `src/state_core/auth/` → 0 ✓ (mode isolation)
- `state_build` / `state_teach` imports under `src/state_core/observability/` → 0 ✓
- `import litellm` / `from litellm` under `src/state_core/auth/` → 0 ✓ (CLAUDE.md rule)
- `import litellm` / `from litellm` under `src/state_core/observability/` → 0 ✓
- `import filelock` / `AsyncFileLock` under `src/state_core/auth/providers/` → 0 ✓ (Phase 013 owns the lock)

**Connected exports (sample):**

| Export | From | Consumed by |
|--------|------|-------------|
| `Credential`, `OAuthCredential`, `ApiKeyCredential`, `AuthMethod` | 011 base | refresh, rotation, store, cli_ops, all 5 providers, import_opencode, loader |
| `save_vault`, `load_vault`, `AuthVaultPermissionError`, `AuthVaultSymlinkError` | 012 store | refresh, rotation, cli_ops, import_opencode, all 5 providers, state_cli/auth.py |
| `is_expired_buffered`, `refresh_credential`, `with_vault_lock`, `new_async_lock` | 013 refresh | rotation, cli_ops, all 4 OAuth providers' CLI runners |
| `select_credential`, `mark_rate_limited`, `iter_active_credentials` | 019 rotation | re-exported via `state_core.auth.__init__`; primary v3 consumer (Provider Routing milestone) — full test surface in tests/auth/test_rotation.py |
| `install`, `assert_redactor_attached`, `redact_processor`, `CYCLE_SENTINEL`, `RedactorNotAttached` | 020 + 022.3 | `state_daemon.orchestrator` |
| `import_from_opencode` | 021 | `state_daemon.orchestrator.startup` |
| `auth_app` | 022 (`state_cli.auth`) | `state_cli.main` (`app.add_typer(auth_app)`) |

---

## Nyquist Compliance

| Phase | VALIDATION.md | nyquist_compliant | wave_0_complete | Action |
|---|---|---|---|---|
| 011 | ✓ exists | true | true | none |
| 012 | ✓ exists | true | true | none |
| 013 | ✓ exists | true | true | none |
| 014 | ✓ exists | true | true | flipped in 022.1 |
| 015 | ✓ exists | true | true | flipped in 022.1 |
| 016 | ✓ exists | true | true | flipped in 022.1 |
| 017 | ✓ exists | true | true | flipped in 022.1 |
| 018 | ✓ exists | true | true | none |
| 019 | ✓ exists | true | true | none |
| 020 | ✓ exists | true | true | none |
| 021 | ✓ exists | true | true | authored in 022.1 |
| 022 | ✓ exists | true | true | flipped in 022.1 |
| 022.1 | ✗ missing | n/a | n/a | gap-closure phase, no research → VALIDATION.md not required (acceptable per plan-phase Step 5.5) |
| 022.2 | ✗ missing | n/a | n/a | gap-closure phase, no research → not required |
| 022.3 | ✗ missing | n/a | n/a | gap-closure phase, no research → not required |

**Overall: compliant** — every phase that ran research and produced a planned validation strategy has `nyquist_compliant: true / wave_0_complete: true`. The three gap-closure phases (022.1, 022.2, 022.3) skipped research by design, so VALIDATION.md is not required (per plan-phase workflow Step 5.5: "if research disabled and has_research is false and no `--research` flag was provided, Nyquist artifacts are not required for this run").

---

## Tech Debt Summary

**Release-time manual smoke gates (intentionally deferred, owned by user):**
- Pre-merge mitmproxy capture for AUTH-01 (Phase 014)
- Live Google OAuth login/refresh smoke (Phases 015, 016)
- Live device-code login smoke (Phase 017)

**Retroactive SECURITY.md authoring (workflow.security_enforcement was enabled mid-milestone):**
- Only Phase 022.3 has a SECURITY.md (authored 2026-05-02). Phases 011..022 + 022.1 + 022.2 completed before the security gate was enabled. Recommend running `/gsd:secure-phase {N}` retroactively for each before the milestone is archived, OR documenting an audit-trail entry that the existing VERIFICATION.md + cardinal-rule grep gates substitute for SECURITY.md on these phases.

**Phase 022 informational note:**
- P0-2: `claude-code-20250219` anthropic-beta flag was removed in Claude Code 2.1.121 — golden captures live state, not a static spec (informational; does not affect AUTH-01 satisfaction).

**Total open items: 5 categories** (4 manual smoke gates + 1 retroactive SECURITY.md authoring set). All are intentionally deferred or process-level, not code or correctness gaps.

---

## Closed Since Prior Audit (2026-05-02 06:30)

The prior audit listed 18 items across 8 categories. After phases 022.1 / 022.2 / 022.3 shipped:

| Prior debt | Status | Resolution |
|---|---|---|
| Phase 020 WK-01..WK-06 (worth-knowing items) | ✓ closed | Phase 022.3 commits 874a1ff..fa2ea7b (2026-05-02) |
| Phase 021 WR-01..WR-03 (warnings) | ✓ closed | Already shipped 2026-05-01 (commits bdbc271, 3f86a9d, 0cdb200) — prior audit was stale on these |
| Phase 018 T-018-8 (vault-file race) | ✓ closed | Phase 022.2 — `with_vault_lock` + concurrent-writer regression suite |
| Phase 018 T-018-9 (symlink attack on auth.json) | ✓ closed | Phase 022.2 — `os.lstat` + `O_NOFOLLOW` reject |
| 014/015/016/017/022 VALIDATION.md frontmatter (`nyquist_compliant: false`) | ✓ closed | Phase 022.1 — frontmatter flipped to `true` |
| Phase 021 VALIDATION.md (missing) | ✓ closed | Phase 022.1 — VALIDATION.md authored |
| `py.typed` marker missing on `src/state_core/*` | ✓ closed | `src/state_core/py.typed` present |
| Phase 022 P0-3 conftest fixture drop (9 fixtures) | ✓ closed | Already fixed in commit 3cafc5a per prior audit (re-confirmed) |

**Net: 13 of 18 prior debt items closed; 5 remaining are intentional release-time manual gates + retroactive SECURITY.md authoring (process-level, not code).**

---

## Verdict

✓ All 13 requirements satisfied (AUTH-01..AUTH-13).
✓ All 15 phases verified passed (12 main + 3 gap closures).
✓ All 5 cross-phase E2E flows wired end-to-end (F1..F5).
✓ All 5 cardinal rules upheld (mode isolation × 2, no litellm × 2, no provider-side filelock).
✓ Daemon boot-order contract preserved and pinned by `tests/test_orchestrator_import_opencode.py`.
✓ Nyquist: 12/12 research-driven phases compliant; 3 gap-closure phases acceptably skip VALIDATION.md.
⚡ Accumulated tech debt is well-documented, intentionally deferred (or process-level), and non-blocking.

**Recommendation:** v2 is ready for `/gsd:complete-milestone v2`. Optionally run `/gsd:secure-phase {011..022,022.1,022.2}` retroactively before archive if you want a uniform SECURITY.md trail on every phase. Manual smoke gates (014..017) are release-process tasks and can be checked off during the v2 release branch cut, not blocking milestone-archive.

---

_Re-audited by Claude (gsd-orchestrator) on 2026-05-02 — supersedes 2026-05-02 06:30 snapshot_
