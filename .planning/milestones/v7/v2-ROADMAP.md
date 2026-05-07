# v2 — Auth Coverage (5 Methods + Multi-Cred)

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 011–022 + 022.1–022.3 (12 phases + 3 gap-closure)

---

## Phases

#### Phase 011: `state_core.auth.base` (AuthMethod protocol + Credential container)
**Goal:** Pydantic `Credential` model, `AuthMethod` Protocol, `is_token`/`is_expired`/`http_headers`/`login`/`refresh` signatures.
**Depends on:** 001
**Requirements:** (foundational)
**Parallelizable:** no

#### Phase 012: `auth.json` vault (`store.py`) with chmod-0600 + array-per-provider
**Goal:** `os.open(..., 0o600)` + `os.fchmod`; array-shape preserved even for single credentials; refuse to proceed if mode wrong.
**Depends on:** 011
**Requirements:** AUTH-06
**Parallelizable:** no
**P0 pitfall:** P0-13
**Plans:** 2/2 plans complete
Plans:
- [x] 012-01-PLAN.md — Wave 0 RED test scaffold (test_store.py 22 stubs + conftest fixtures)
- [x] 012-02-PLAN.md — store.py implementation (AuthVault, atomic-write, mode-verify) + __init__ re-exports

#### Phase 013: Filelock-guarded refresh lock (`refresh.py`)
**Goal:** 10s acquire, re-read auth.json, double-check expiry, refresh only if still stale, write, release; reader-path blocks refresher.
**Depends on:** 012
**Requirements:** AUTH-07, AUTH-09
**Parallelizable:** no
**P0 pitfall:** P0-6, P0-7
**Plans:** 2/2 plans complete
Plans:
- [x] 013-01-PLAN.md — Wave 0 RED test scaffold (test_refresh.py 30 stubs + conftest fixtures + pytest markers)
- [x] 013-02-PLAN.md — refresh.py implementation (filelock + double-check + 5-min buffer + 15s wait_for) + __init__ re-exports

#### Phase 014: Anthropic OAuth provider (stealth flow, byte-for-byte vs claude-oauth.md)
**Goal:** PKCE verifier reused as `state`, client_id `9d1c250a-e61b-44d9-88ed-5944d1962f5e` (base64-decoded at runtime), Bearer for `sk-ant-oat*`, headers `user-agent: claude-cli/<ver>` + `x-app: cli` + `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…`, 5-min expiry buffer, token-shape sniffer first branch.
**Depends on:** 013
**Requirements:** AUTH-01
**Parallelizable:** yes with 015..P7
**P0 pitfalls:** P0-1, P0-2, P0-3, P0-4, P0-5, P0-7, P0-8
**Plans:** 3/3 plans complete
Plans:
- [x] 014-01-PLAN.md — Wave 0 RED test scaffold (test_pkce.py + test_anthropic.py — 17 stubs covering all VALIDATION.md rows + conftest fixtures)
- [x] 014-02-PLAN.md — Foundation (oauth_common/pkce.py + providers/anthropic.py constants/exceptions/token model/AnthropicAuth skeleton with sync methods GREEN, async raise NotImplementedError)
- [x] 014-03-PLAN.md — Implementation (login() + refresh() bodies + `python -m` argparse entry-point — turns remaining 5–7 Wave 0 tests GREEN)

#### Phase 015: Gemini CLI OAuth provider (google-auth + google-auth-oauthlib, PKCE, refresh rotation)
**Goal:** Desktop OAuth pattern, plaintext client_secret with rationale comment (NOT base64/XOR — P1-3), refresh-token rotation persisted on every refresh.
**Depends on:** 013
**Requirements:** AUTH-02
**Parallelizable:** yes with 014, P6, P7
**P1 pitfalls:** P1-3, P2-2 (plus P0-7 inherited from 013, Pitfall 4 CSRF on loopback)
**Plans:** 4/4 plans complete
Plans:
- [ ] 015-A-tests-and-errors-module.md — Wave 0 RED test scaffold (test_loopback.py + test_google_gemini.py — 20 stubs covering all VALIDATION.md rows + conftest fixtures + promote AuthError/AuthLoginError/AuthRefreshError to state_core.auth.errors)
- [x] 015-B-oauth-common-loopback.md — Wave 1 shared loopback module (oauth_common/loopback.py — async listener, port allocation, state CSRF check, success/failure redirects; reusable by Phase 016 Antigravity) (completed 2026-04-30)
- [ ] 015-C-gemini-provider-helpers.md — Wave 2 provider helpers (providers/google_gemini.py — constants block with plaintext _CLIENT_ID/_CLIENT_SECRET + P1-3 rationale, GoogleTokenResponse model, _parse_id_token_payload, _to_credential, _build_authorize_url, _exchange_code, GoogleGeminiAuth class with sync methods GREEN, async raises NotImplementedError)
- [ ] 015-D-gemini-login-refresh-and-cli.md — Wave 3 orchestration (login() with TWO independent generate_verifier() calls — state != verifier, refresh() with hand-rolled httpx + P2-2 rotation rule, _main argparse with login + refresh subcommands wiring Phase 013's refresh_credential)


#### Phase 016: Antigravity OAuth provider (PKCE + loopback, FIXED port 51121)
**Goal:** Google Antigravity / Cloud Code Assist Companion API OAuth client. PKCE+loopback flow (RFC 8252) with FIXED port 51121 + literal localhost redirect_uri, 5 scopes (Gemini-3 + cclog + experimentsandconfigs), Antigravity-specific outbound headers (User-Agent: antigravity, X-Goog-Api-Client, Client-Metadata JSON), refresh-token rotation (P2-2), provider_id="google.antigravity".
**Depends on:** 013, 015 (oauth_common.loopback + state_core.auth.errors reused)
**Requirements:** AUTH-03
**Parallelizable:** yes with 014, P5, P7
**P1/P2 pitfalls:** P1-3 (plaintext client_secret), P2-2 (refresh rotation), P2-3 (Antigravity scope drift — OWNED), Pitfalls 4 (port 51121 collision — OWNED), 5 (localhost vs 127.0.0.1 — OWNED), 6 (ya29-prefix collision with Gemini — OWNED), 7 (headless SSH inherited)
**Plans:** 4/4 plans complete
Plans:
- [x] 016-01-PLAN.md — Wave 0 RED test scaffold (test_antigravity.py 22 stubs covering all VALIDATION.md rows + conftest fixtures)
- [x] 016-02-PLAN.md — Constants + Pydantic models + sync helpers (_parse_id_token_payload, _to_credential, _build_authorize_url, _platform_for_client_metadata, _build_client_metadata, _exchange_code) — turns 8 Wave-2 tests GREEN
- [x] 016-03-PLAN.md — AntigravityAuth class with sync methods (is_token, is_expired delegation, http_headers with 4-header dict) — turns 7 Wave-3 tests GREEN; async methods raise NotImplementedError
- [x] 016-04-PLAN.md — login() body (FIXED port + port-collision OSError catch) + refresh() body (P2-2 rotation) + _main argparse (login + refresh subcommands wiring Phase 013 refresh_credential) — turns 7 Wave-4 tests GREEN; AUTH-03 satisfied

#### Phase 017: GitHub Copilot device-code flow
**Goal:** Device-code endpoint polling with 15-min countdown, grant-revocation detection (200-with-null-body), pydantic validation of refresh responses.
**Depends on:** 013
**Requirements:** AUTH-04
**Parallelizable:** yes with 014, P5, P6

**Plans:** 4/4 plans complete
Plans:
- [x] 017-01-PLAN.md — Wave 0 RED test scaffold (test_github_copilot.py 26 stubs covering all VALIDATION.md rows + conftest fixtures)
- [x] 017-02-PLAN.md — Constants + Pydantic models + _PollingState dataclass + GitHubCopilotAuth class with sync methods GREEN; async raises NotImplementedError
- [x] 017-03-PLAN.md — _request_device_code body + _poll_for_token RFC 8628 §3.5 state machine (monotonic deadline, persistent slow_down, 3s safety margin, CancelledError propagation) — turns 9 Wave-3 tests GREEN
- [x] 017-04-PLAN.md — _mint_session_token body + login() + refresh() (re-mint via copilot_internal/v2/token) + _main argparse — turns 10 Wave-4 tests GREEN; AUTH-04 satisfied
#### Phase 018: Plain API-key vault (12 providers)
**Goal:** API-key storage for Anthropic/OpenAI/Google/DeepSeek/Groq/Together/Anyscale/Mistral/Cohere/OpenRouter/Grok/Cerebras; env var fallback.
**Depends on:** 012
**Requirements:** AUTH-05
**Parallelizable:** yes with 014..P7
**Plans:** 4/4 plans complete
Plans:
- [x] 018-01-PLAN.md — Wave 0 RED test scaffold (test_api_key.py + test_loader.py + test_main_api_key.py + test_import_graph.py — 21 VALIDATION-row stubs + conftest fixtures)
- [x] 018-02-PLAN.md — providers/api_key.py impl (12-row _REGISTRY verbatim from RESEARCH, ApiKeyProviderSpec frozen Pydantic, PlainApiKeyAuth class, get_api_key_auth factory, iter_known_prefixes, _main argparse) + UnknownApiKeyProviderError added to errors.py
- [x] 018-03-PLAN.md — state_core.auth.loader (load_credentials with vault > env precedence, ephemeral env synthesis, T-018-5 + T-018-7 + T-018-10 mitigations) + auth/__init__ re-export
- [x] 018-04-PLAN.md — Verification gate (full pytest green, __main__ smoke test via stdin pipe, VALIDATION.md frontmatter flipped to compliant, 21/21 GREEN)

#### Phase 019: Multi-cred round-robin across a provider's credential array
**Goal:** Rotation index persisted in `last_rotation`; fallback on 429 + on rate-limit-seen flags; array-shape preserved across migrations.
**Depends on:** 012
**Requirements:** AUTH-08
**Parallelizable:** yes with 018
**Plans:** 4/4 plans complete
Plans:
- [x] 019-01-PLAN.md — Wave 0 RED test scaffold (test_rotation.py 25 stubs + conftest fixtures + test_import_graph.py extension for ROTATE-21)
- [x] 019-02-PLAN.md — Errors + lock surface prep (NoCredentialsAvailableError in errors.py + new_async_lock public alias in refresh.py)
- [x] 019-03-PLAN.md — rotation.py implementation (time-bucketed select_credential + cool-down map + iter_active_credentials + __init__ re-exports)
- [x] 019-04-PLAN.md — Verification gate (26/26 ROTATE GREEN, mypy clean, smoke test, VALIDATION.md flipped, REQUIREMENTS.md AUTH-08 [x])

#### Phase 020: Root-logger token redactor (structlog filter, `sk-ant-*` / `sk-*` / `ya29.*` / device-code patterns)
**Goal:** Compiled regex set, applied at root logger, refuse-daemon-start if not attached.
**Depends on:** 011
**Requirements:** AUTH-10
**Parallelizable:** yes with most
**P0 pitfall:** P0-14
**Plans:** 4/4 plans complete
Plans:
- [x] 020-01-PLAN.md — Wave 0 RED test scaffold (tests/test_redactor.py 24 stubs + tests/test_observability_import_graph.py 3 mode-isolation stubs)
- [x] 020-02-PLAN.md — Wave 1 GREEN core (state_core/observability/__init__.py + redactor.py — 12-pattern regex set, _SECRET_KEYS frozenset, _walk_value walker, redact_processor, iter_token_patterns)
- [x] 020-03-PLAN.md — Wave 2 GREEN wiring (RedactorNotAttached + install() + assert_redactor_attached() + Step 0 wiring in src/state_daemon/orchestrator.py)
- [x] 020-04-PLAN.md — Verification gate (full pytest green, smoke test, VALIDATION.md flipped to compliant, REQUIREMENTS.md AUTH-10 [x])

#### Phase 021: First-run import from opencode `~/.local/share/opencode/auth.json`
**Goal:** Detect + import into `.state/auth.json`, preserving array shape (P1-7 defence).
**Depends on:** 012, 011, 020
**Requirements:** AUTH-11
**Parallelizable:** yes with 019
**P1 pitfall:** P1-7
**Plans:** 3/3 plans complete
Plans:
- [x] 021-01-PLAN.md — Wave 1 RED test scaffold (tests/auth/test_import_opencode.py 22+ stubs covering all CONTEXT.md decisions + tests/auth/test_import_graph.py mode-isolation extension) + state.auth.imported event-type addition to state_core.schema
- [x] 021-02-PLAN.md — Wave 2 GREEN implementation (state_core.auth.import_opencode — path resolution, opencode-shape parsing, type/field translation, all-or-nothing transactional import, dual-write of auth.imported events) + auth/__init__ re-export
- [x] 021-03-PLAN.md — Wave 3 GREEN wiring (Step 0.5 in src/state_daemon/orchestrator.py — install → assert_attached → importer → store-driven steps; importer failure non-fatal) + 3 integration tests + REQUIREMENTS.md AUTH-11 flip

#### Phase 022: CLI: `state auth login|logout|status` + captured-header regression tests
**Goal:** Typer commands with interactive + non-interactive flows; golden-file header diffs for every stealth request; P0 regression test (one per P0-1..P0-8 + P0-13).
**Depends on:** 014, 015, 016, 017, 018, 020
**Requirements:** AUTH-12, AUTH-13
**Parallelizable:** no (integration)
**Plans:** 4/4 plans complete
Plans:
- [x] 022-01-PLAN.md — Wave 1: test scaffold + golden infrastructure (conftest golden_load/update-goldens, 9 P0 RED stubs, ops/typer stubs, import-graph extensions)
- [x] 022-02-PLAN.md — Wave 2: state_core.auth.cli_ops (login/logout/status ops layer + StatusReport/StatusRow + dual-write events + auth/__init__ re-exports)
- [x] 022-03-PLAN.md — Wave 3: state_cli/auth.py Typer sub-app (login/logout/status commands, exit-code mapping, Rich table, --json, register in main.py)
- [x] 022-04-PLAN.md — Wave 3: P0 regression tests GREEN + golden JSON fixtures committed + full auth suite gate

#### Phase 022.1: Nyquist + typing hygiene (gap closure from `v2-MILESTONE-AUDIT.md`)
**Goal:** Close documentation-state hygiene category from v2 audit (2026-05-02): (A) flip VALIDATION.md frontmatter (`nyquist_compliant: true`, `wave_0_complete: true`) on phases 014, 015, 016, 017, 022 — all tests already GREEN, frontmatter never updated; (B) author missing VALIDATION.md for Phase 021 via `/gsd:validate-phase 021`; (C) add `py.typed` marker to `src/state_core/` to silence mypy `[import-untyped]` warnings surfaced in 011 + 019 caveats.
**Depends on:** 011, 014, 015, 016, 017, 021, 022 (all already complete)
**Requirements:** (none — closes audit tech debt, no AUTH-XX impact)
**Parallelizable:** no (gap closure)
**Audit reference:** `.planning/v2-MILESTONE-AUDIT.md` § Nyquist Compliance + § Tech Debt Summary (project_wide py.typed)

#### Phase 022.2: Deferred LOW-severity auth threats (gap closure)
**Goal:** Close two LOW-severity threats deferred from Phase 018, expected to land in Phase 022, did not: T-018-8 (vault-file race condition between concurrent reads/writes outside the existing filelock window) and T-018-9 (symlink-attack mitigation on `auth.json` — refuse to follow symlinks when opening the vault).
**Depends on:** 012, 013 (vault + filelock surfaces)
**Requirements:** AUTH-06 (extends chmod-0600 vault hardening)
**Parallelizable:** no (gap closure; touches `state_core.auth.store`)
**Audit reference:** `.planning/v2-MILESTONE-AUDIT.md` § Tech Debt Summary (Phase 018 deferred LOW threats)

#### Phase 022.3: Reviewer worth-knowing cleanup (gap closure)
**Goal:** Close 6 WORTH-KNOWING reviewer items from Phase 020's redactor review (`020-REVIEW-FIX.md` `deferred: 6`): WK-01 cycle-detection guard for `_walk_value`, WK-02 pattern-order regression test, WK-03 NamedTuple / tuple-subclass support, WK-04 `assert_redactor_attached` docstring polish, WK-05 `install(level=…)` parameter to avoid log-level clobber, WK-06 `RedactorNotAttached` precision when ProcessorFormatter render raises. (Note: Phase 021 WR-01..03 — originally batched here in the milestone audit — were already shipped on 2026-05-01 in commits bdbc271, 3f86a9d, 0cdb200; only WK-01..06 remain in scope.)
**Depends on:** 020 (already complete)
**Requirements:** AUTH-10 (redactor hardening — re-affirmed, not new requirement coverage)
**Parallelizable:** n/a (single-file gap closure on `src/state_core/observability/redactor.py`)
**Audit reference:** `.planning/v2-MILESTONE-AUDIT.md` § Tech Debt Summary (Phase 020 WK-01..06)
**Plans:** 1/1 plans complete
Plans:
- [x] 022.3-01-redactor-worth-knowing-cleanup-PLAN.md — Close all 6 WK items (WK-01..06) in `src/state_core/observability/redactor.py` + add 12 regression tests in `tests/test_redactor.py` + final phase-verification gate (full redactor suite GREEN, cardinal-rule grep gates intact, mypy clean)

---
