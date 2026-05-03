# Phase 016: Antigravity OAuth provider — Research

**Researched:** 2026-04-30
**Domain:** Google Antigravity Cloud Code Assist OAuth (PKCE-with-loopback, RFC 8252) — sibling of Phase 015's Gemini-CLI flow with a different `client_id`, two **extra** scopes (`cclog`, `experimentsandconfigs`), and Antigravity-specific outbound HTTP headers (`User-Agent: antigravity`, `X-Goog-Api-Client`, `Client-Metadata`).
**Confidence:** HIGH (cross-verified across three independent sources: NoeFabris/opencode-antigravity-auth source files, PicoClaw provider docs, taoalpha/22773d2132519e55a4c7427fd3e96d8e quota-skill gist).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

None — `016-CONTEXT.md` was auto-generated with `workflow.skip_discuss: true`. There are no user-locked decisions for this phase. All implementation choices are at Claude's discretion (constrained by the hard project-level rules below).

### Claude's Discretion

All implementation choices are at Claude's discretion. The discretion bounds are:

- Project-level rules from `CLAUDE.md` (Python 3.12+, mode isolation, deterministic event payloads, chmod-0600 vault, OAuth NEVER through litellm, `.state/events.sqlite` first).
- Already-pinned deps from `STACK.md` (`google-auth>=2.35`, `google-auth-oauthlib>=1.2`, `httpx>=0.28.1`, `pydantic>=2.13.2`, `filelock>=3.20.3`, `cryptography>=43.0`, `structlog>=25.1`, `pytest>=8.4.0`, `pytest-asyncio>=1.3.0`, `pytest-httpx>=0.35`).
- Phase 011/012/013/014/015 contracts: AuthMethod Protocol, `OAuthCredential` (frozen, `extra="forbid"`), AuthVault array shape, `refresh_credential` filelock-guarded with double-check + 10s timeout + 15s `wait_for` cap, `oauth_common/pkce.py` (PKCE S256), `oauth_common/loopback.py` (asyncio loopback listener with CSRF state gate), `state_core.auth.errors` (`AuthError` / `AuthLoginError` / `AuthRefreshError`).
- Phase 015 patterns to **mirror byte-for-byte where applicable**: TWO independent `generate_verifier()` calls (state ≠ verifier — Anthropic's P0-8 reuse is Anthropic-only), hand-rolled httpx refresh with `parsed.refresh_token or cred.refresh` rotation rule (P2-2), `_to_credential` with `original_refresh: str` kwarg + injected `now: float`, `_main` argparse with `login` + `refresh` subcommands.
- Pitfalls inherited: P1-3 (plaintext client_secret with rationale comment — NEVER base64/XOR), P2-2 (refresh-token rotation), P2-3 (Antigravity scope drift — this phase OWNS this pitfall), P0-7 / AUTH-09 (5-minute buffer in `is_expired`, NOT in storage).
- Phase 014 patterns (no own filelock, per-call `httpx.AsyncClient`, no retry layer).
- Per the roadmap label, the phase title says "device-code"; **research disconfirms this**: every public Antigravity OAuth implementation in the wild uses **PKCE-with-loopback** (RFC 8252), not RFC 8628 device-code. The roadmap label is treated as imprecise; the verified flow shape governs the plan.

### Deferred Ideas (OUT OF SCOPE)

None explicitly deferred via CONTEXT — discuss was skipped. Implicit deferrals (consistent with Phase 015's scope split) and items the planner MUST NOT pull into this phase:

- Polished `state auth login google.antigravity` Typer CLI — Phase 022.
- 429 quota-exhaustion parsing + multi-cred handoff between Antigravity accounts — Phase 019 (round-robin) + v3 provider routing.
- First-run import from `~/.config/opencode/antigravity-accounts.json` (or any other host's Antigravity vault) — Phase 021.
- Structlog `ya29.*` token redactor — Phase 020 (already-known to apply to Antigravity tokens — same `ya29.*` shape as Gemini).
- Inference-call routing to `cloudcode-pa.googleapis.com/v1internal:streamGenerateContent` (Antigravity's actual model API) — v3 provider routing. This phase only owns auth.
- Quota-status fetching against `cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels` — v3 provider routing.
- Project-ID resolution (`loadCodeAssist` boot call to bind a free-tier user to a Google Cloud project) — v3 provider routing.
- Refactoring `_parse_id_token_payload` from `google_gemini.py` into `oauth_common/idtoken.py` — addressed below as a **structural recommendation** for the planner; planner may keep it inline (duplicated) if cycle pressure is high.
- The "managed_project_id / packed-refresh-string" multi-account encoding from `opencode-antigravity-auth/auth.ts` (`<refresh>|<projectId>|<managedProjectId>`) — `OAuthCredential.extras` already supports `project_id` + `managed_project_id` as separate keys; we do NOT recreate the packing scheme. (Phase 019 round-robin will operate on the array, not on packed strings.)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-03 | Antigravity OAuth (custom flow, refresh handling) | Sections **Standard Stack** (no new deps; reuse `oauth_common/loopback.py` + `oauth_common/pkce.py` from Phase 015 byte-for-byte), **Architecture Patterns** §1–§7 (PKCE+loopback structure verbatim from Phase 015, FIXED-PORT redirect_uri 51121 due to Google's exact-match rule, additional `cclog` + `experimentsandconfigs` scopes, Antigravity-specific `User-Agent: antigravity` + `X-Goog-Api-Client` + `Client-Metadata` outbound headers, `provider_id="google.antigravity"` namespacing, refresh-token rotation per P2-2, project_id stored in `extras["project_id"]`), **Don't Hand-Roll** table (loopback flow + refresh body + ID-token parse all exist in `oauth_common/` or `google_gemini.py`), **Common Pitfalls** §1–§11 (P1-3 plaintext rationale, P2-2 rotation, P2-3 scope drift this phase OWNS, port-51121 collision, ya29-prefix-collision-with-Gemini, headless SSH, `expires` epoch math, account_id sourcing, kebab-case provider_id, Antigravity ToS warning, account-pool packed-refresh-string drift), **Code Examples** §1–§7 (constants block with discovery-doc URL, authorize URL builder, token exchange POST body, refresh body, headers, sniffer, `_to_credential` adaptation). |

</phase_requirements>

## Disambiguation

**"Antigravity"** in this phase refers exclusively to **Google's Antigravity IDE / Cloud Code Assist Companion API**, NOT the get-shit-done CLI runtime that uses the same name (which appears in `.state-inputs/get-shit-done/tests/antigravity-install.test.cjs` and is unrelated). The Google Antigravity product is a unified gateway exposing Gemini 3 + Claude Opus + GPT-OSS through a single Cloud Code Assist endpoint.

The roadmap phase label says "custom OAuth2 device-code". **Research disconfirms the device-code claim**: every observed Antigravity OAuth client in the wild (NoeFabris/opencode-antigravity-auth v2026.2.x source, shekohex/opencode-google-antigravity-auth, PicoClaw provider docs, taoalpha gist) uses **PKCE-with-loopback (RFC 8252)** — exactly the same flow shape as Gemini-CLI (Phase 015), differing only in `client_id`/`client_secret`, scope list, fixed redirect-URI port (51121, not kernel-allocated), and outbound HTTP headers. The roadmap label is treated as imprecise; this RESEARCH binds the implementation to the loopback flow.

**Terms-of-service caveat:** Multiple sources warn that using third-party Antigravity OAuth proxies violates Google's ToS, and several users have reported Google account bans (NoeFabris/opencode-antigravity-auth was archived 2026-03-30; the analogous `google-antigravity-auth` opencode plugin was removed in opencode 2026.2.23; January 2026 saw account-wide `IAM_PERMISSION_DENIED` revocations on Antigravity Cloud AI Companion API). This is a project-level decision concern (not a research blocker): the user has explicitly chosen to ship `state` with Antigravity OAuth support per AUTH-03 and `.planning/PROJECT.md` Key Decision row 14 ("All five auth methods ship day one"). Phase 016 implements the technical surface; the user accepts the ToS risk. The `state-inputs/gsd2-auth-analysis.md` document confirms this is a deliberate "sleeper-path" choice for Gemini 3 + Claude + GPT-OSS coverage.

## Summary

Phase 016 is the **third concrete `AuthMethod` implementation** (Anthropic Phase 014, Gemini Phase 015, **Antigravity 016**). The technical surface is **near-identical to Phase 015**: PKCE S256, loopback HTTP listener on `127.0.0.1`, one authorize URL, one localhost listener, one token-endpoint POST for `authorization_code`, one for `refresh_token`. The structural template `google_gemini.py` is reusable verbatim; the diffs are surgical (constants + scopes + headers + `provider_id` + a fixed-port redirect + a sniffer that disambiguates Gemini vs Antigravity).

**Five concrete diffs vs Phase 015:**

1. **Identity constants** — different `_CLIENT_ID` (`1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`), different `_CLIENT_SECRET` (`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`). Both still PUBLIC Desktop-App OAuth credentials per Google's distributable-app guidance. P1-3 plaintext rule applies identically.
2. **Scopes** — Gemini's three scopes (`cloud-platform`, `userinfo.email`, `userinfo.profile`) PLUS two Antigravity-specific scopes (`cclog`, `experimentsandconfigs`). The `cclog` scope unlocks Cloud Code log telemetry the Antigravity backend reads to attribute usage; `experimentsandconfigs` carries A/B-test overrides. **Both are MANDATORY** — omitting either causes the loadCodeAssist boot call (v3 provider routing's concern) to 403.
3. **Redirect URI port — FIXED, not kernel-allocated** — `http://localhost:51121/oauth-callback`. Google requires the redirect_uri to **exactly match** one of the URIs pre-registered in the Google Cloud Console for the OAuth client; pre-registration is per-client, and the Antigravity client was registered with `localhost:51121/oauth-callback` (NOT `127.0.0.1`, NOT `/oauth2callback`, NOT port 0). Phase 015's `allocate_loopback_port()` does NOT apply here. Port collisions surface as `OSError [Errno 48] Address already in use` and require explicit user remediation (close the conflicting CLI / restart). This is a fundamental flow difference and the planner must NOT try to apply Phase 015's port-0 logic.
4. **Outbound HTTP headers** — Antigravity's Cloud Code Assist endpoint (`cloudcode-pa.googleapis.com/v1internal`) requires THREE custom headers in addition to the Bearer (verified via taoalpha gist + ANTIGRAVITY_API_SPEC.md):
   - `User-Agent: antigravity` (literal — NOT a version string; Antigravity backends pattern-match on this prefix to route to Cloud AI Companion API quota buckets)
   - `X-Goog-Api-Client: google-cloud-sdk vscode_cloudshelleditor/0.1`
   - `Client-Metadata: {"ideType":"ANTIGRAVITY","platform":"<MACOS|LINUX|WINDOWS>","pluginType":"GEMINI"}` (JSON-encoded; `platform` is run-time-detected from `sys.platform`)
   These are **set by `http_headers(cred)` on the AuthMethod**, not by v3 provider routing — the captured-header regression test (AUTH-13, Phase 022) golden-files them and the planner MUST verify byte-for-byte parity.
5. **Token-shape sniffer is structurally indistinguishable from Gemini** — Antigravity access tokens also start `ya29.…` (it IS Google OAuth, with the same token format). `is_token(value)` returning `value.startswith("ya29.")` would match BOTH providers. The intentional design: **`is_token` is provider-affirmative**, not exclusive. Each provider says "yes, this is shape I issue" and the discriminator at the routing level is `provider_id`, never the token shape. Phase 016's `is_token` returns the same boolean Phase 015's does — by design. Phase 019 round-robin disambiguates by `provider_id` bucket, never by token sniffing.

The other big similarity to Phase 015: refresh-token rotation rule is **identical** (`parsed.refresh_token or cred.refresh`, P2-2), id_token JWT parse pattern is identical (Google issues an id_token with `sub` + `email`), and the outer Phase-013 filelock-guarded `refresh_credential` integration is identical (provider does NOT acquire its own lock; Phase 013 owns coordination).

**Primary recommendation:** Land `providers/antigravity.py` (~310 LOC — slightly larger than Gemini's 280 LOC due to the three-header `Client-Metadata` builder + the platform sniff). Reuse `oauth_common/pkce.py` and `oauth_common/loopback.py` from Phase 015 untouched. Mirror `providers/google_gemini.py`'s file structure section-for-section so the diff is auditable line-by-line. Refactor `_parse_id_token_payload` into `oauth_common/idtoken.py` IFF the planner deems duplication aesthetically loud (acceptable to keep duplicated for v2 — YAGNI — and promote in a v3 hygiene pass; the function is 30 LOC and the second-consumer threshold is met but cycle pressure is real).

## Standard Stack

### Core (already pinned in `pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.12+ | `asyncio`, `base64`, `secrets` (transitively via `oauth_common.pkce`), `socket` (NOT used — fixed port; see below), `time`, `urllib.parse`, `sys.platform` (for `Client-Metadata` `platform` field) | Loopback HTTP, URL building, JWT parse, platform sniff stay stdlib. Notably `socket.bind(('', 0))` is NOT used — Antigravity requires the fixed port 51121. |
| `httpx` | `>=0.28.1` | Per-call `AsyncClient` for token exchange + refresh | Same client as Phase 014/015. |
| `pydantic` | `>=2.13.2` | `AntigravityTokenResponse(BaseModel)` with `extra="ignore"` (forward-compat) | Mirrors `GoogleTokenResponse` from Phase 015. |
| `orjson` | `>=3.11.8` | id_token JWT payload JSON parse, `Client-Metadata` JSON serialization | Already required by `google_gemini._parse_id_token_payload`. |
| `filelock` | `>=3.20.3` | Imported transitively via Phase 013's `refresh_credential` — provider does NOT touch it directly | CVE-2026-22701 floor. |
| `structlog` | `>=25.1` | Login/refresh observability | Phase 020 attaches the `ya29.*` redactor; same redactor covers Antigravity. |
| `state_core.auth.errors` | (Phase 015) | `AuthLoginError`, `AuthRefreshError` re-imported from `state_core.auth.errors` | Already promoted to shared module in Phase 015. |
| `state_core.auth.oauth_common.pkce` | (Phase 014) | `generate_verifier`, `build_challenge` | Reused unchanged — RFC 7636 compliance carried forward. |
| `state_core.auth.oauth_common.loopback` | (Phase 015) | `wait_for_oauth_callback`, `SIGN_IN_SUCCESS_URL`, `SIGN_IN_FAILURE_URL` | Reused unchanged. **`allocate_loopback_port` is NOT used** — port is the FIXED constant 51121. |

### Supporting (test only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8.4.0` | Test runner | Always. |
| `pytest-asyncio` | `>=1.3.0` | Async test support | Every `login()` / `refresh()` test. |
| `pytest-httpx` | `>=0.35` | `httpx_mock.add_response(match_url, match_headers, match_content, match_data)` for token-endpoint POST | Token-exchange + refresh tests. |
| `pytest-mock` | `>=3.14` | `monkeypatch.setattr` for `state_core.auth.providers.antigravity.print` (authorize URL capture), `wait_for_oauth_callback` (return scripted code), `sys.platform` (test the three `Client-Metadata` platform branches) | Login-flow tests + header-builder branch coverage. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Mirror `google_gemini.py` structurally (same constants/helpers/class layout) | Extract a `GoogleOAuthBase` class and inherit | YAGNI — two providers do not justify an abstract base; the diff between Gemini and Antigravity is contained in module-level constants + one method (`http_headers`). Inheritance hides the diff and complicates the captured-header regression test (AUTH-13) — golden-file diffs work better against flat modules. **Keep flat, mirror line-for-line.** |
| FIXED port 51121 | `allocate_loopback_port()` as in Phase 015 | Google rejects redirect_uri mismatch with `redirect_uri_mismatch` error before token exchange. The Antigravity OAuth client is pre-registered against `http://localhost:51121/oauth-callback` (verified across PicoClaw docs, taoalpha gist). Kernel-allocated ports require Cloud-Console pre-registration of every possible port — impossible. **Fixed port is mandatory.** |
| `localhost` (DNS) vs `127.0.0.1` (literal) in redirect_uri | Use `127.0.0.1:51121/oauth-callback` for parity with Phase 015 | Google's pre-registered URI for the Antigravity client is **literal `localhost:51121/oauth-callback`** (verified). Substituting `127.0.0.1` causes `redirect_uri_mismatch`. The planner MUST send the URL with `localhost`. The asyncio listener still binds `127.0.0.1` (because that's what `wait_for_oauth_callback` does), and `localhost` resolves to `127.0.0.1` on every common OS; only the URL string differs. |
| Antigravity-specific outbound headers in `http_headers` | Set them in v3 provider routing | AUTH-13 (Phase 022) golden-file regression test compares **the AuthMethod's `http_headers` output** against captured Antigravity-IDE outbound traffic. Setting headers in v3 puts them outside the test surface. **Headers belong in `http_headers` for the regression test to bind.** |
| Compute `Client-Metadata.platform` once at module load | Compute per-call inside `http_headers` | Per-call: `sys.platform` is stable in a single process but tests need to monkey-patch it across the three branches (MACOS / LINUX / WINDOWS). Module-load locks out testing. **Compute per-call.** |
| `User-Agent: antigravity/1.15.8 windows/amd64` (gemini-cli reference style) | `User-Agent: antigravity` (the literal string from taoalpha gist) | Cross-source verification: PicoClaw docs say `antigravity/1.15.8 windows/amd64` OR `antigravity` (depending on context — the longer string is for the IDE; the short string is for the Cloud Companion API). taoalpha gist (most recent, 2026 quota tooling) uses `antigravity` literal for the quota endpoint. **Use the literal `antigravity` for the Cloud Companion API; the version-suffixed variant is the desktop-IDE shape used for IDE registration only**, not what we send. |
| Refactor `_parse_id_token_payload` to `oauth_common/idtoken.py` | Duplicate it in `antigravity.py` verbatim | Either is fine. Duplication is ~30 LOC; refactor adds one module + 6 import-site updates. Recommendation: **keep duplicated for v2; promote in a v3 hygiene pass** — second-consumer threshold is met but cycle pressure on this phase is real and the function is small + self-contained. |
| Use `webbrowser.open(authorize_url)` | `print(authorize_url)` | Phase 022 owns polished UX (browser open + `--no-browser`). 015 ships print-only fallback for SSH; 016 mirrors. |
| Per-call `httpx.AsyncClient` | Module-level singleton | Phase 014/015 pattern. Auth calls infrequent; pool-keepalive saves nothing; singletons leak across tests. |

**Installation:** No new dependencies required — every line above is already pinned.

## Architecture Patterns

### Recommended Project Structure

```
src/state_core/auth/
├── __init__.py
├── base.py                                  # (existing — Phase 011)
├── store.py                                 # (existing — Phase 012)
├── refresh.py                               # (existing — Phase 013)
├── errors.py                                # (existing — Phase 015)
├── oauth_common/
│   ├── __init__.py                          # (existing — empty)
│   ├── pkce.py                              # (existing — Phase 014; reused unchanged)
│   ├── loopback.py                          # (existing — Phase 015; reused unchanged
│   │                                          — but `allocate_loopback_port` NOT called here)
│   └── idtoken.py                           # OPTIONAL — extract `_parse_id_token_payload`
│                                              from google_gemini.py + antigravity.py.
│                                              Planner discretion: ship duplicated or
│                                              promote. Recommendation: ship duplicated.
└── providers/
    ├── __init__.py                          # (existing — empty)
    ├── anthropic.py                         # (existing — Phase 014)
    ├── google_gemini.py                     # (existing — Phase 015)
    └── antigravity.py                       # NEW — ~310 LOC
                                              #   includes `if __name__ == "__main__": ...`
                                              #   so `python -m state_core.auth.providers.antigravity login` works

tests/auth/
├── (existing fixtures in conftest.py)
├── oauth_common/
│   ├── test_pkce.py                         # (existing)
│   ├── test_loopback.py                     # (existing — covers shared listener)
│   └── test_idtoken.py                      # OPTIONAL — IFF idtoken.py extraction
└── providers/
    ├── test_anthropic.py                    # (existing)
    ├── test_google_gemini.py                # (existing)
    └── test_antigravity.py                  # NEW — ~30 tests mirroring test_google_gemini.py
```

**provider_id naming:** `"google.antigravity"` — kebab-case-with-dot-namespace, sibling to `"google.gemini_cli"`. `base.py` docstring already advertises `'google.gemini_cli'` as the canonical example; `'google.antigravity'` slots in naturally. The dot is a namespace separator within the AuthVault `providers` dict; **both Google variants live as siblings, never as sub-keys**. Phase 019 round-robin will rotate within a single `provider_id` bucket — Gemini and Antigravity are intentionally separate buckets so a Gemini token never tries to call the Antigravity API and vice versa.

### Pattern 1: PKCE + Loopback with FIXED port (vs Phase 015's kernel-allocated)

**What:** Identical to Phase 015 except the port is the literal constant `51121` and the redirect_uri uses `localhost` (not `127.0.0.1`) to satisfy Google's exact-match pre-registration on the Antigravity OAuth client.

**When:** Phase 016 only. Phase 015 stays kernel-allocated (Gemini-CLI's pre-registration accepts any localhost port).

**Why fixed:**
1. Google's OAuth server enforces redirect_uri exact-string match against the pre-registered URI on the OAuth client. The Antigravity client (`1071006060591-…`) was registered against `http://localhost:51121/oauth-callback`. ANY deviation (`127.0.0.1` instead of `localhost`, port 51122 instead of 51121, `/oauth2callback` instead of `/oauth-callback`) → token endpoint returns `redirect_uri_mismatch` 400.
2. Kernel-allocated ports are impossible because pre-registration would require enumerating every port 1024–65535 (Google rejects URIs with `:0` or wildcards).
3. Multi-CLI race: if a second `state` process tries to login while a first is mid-flow, the second fails with `OSError [Errno 48] Address already in use`. This is acceptable behavior — surfacing via `AuthLoginError("port 51121 is already in use; close the other state CLI or wait for it to finish")` is the documented remediation.

**Skeleton (planner copies into `antigravity.py`):**

```python
# src/state_core/auth/providers/antigravity.py — login() body
_REDIRECT_PORT: int = 51121
_REDIRECT_PATH: str = "/oauth-callback"
_REDIRECT_HOST_LITERAL: str = "localhost"   # Google pre-registration uses literal "localhost"

# In login():
state    = generate_verifier()              # 43-char base64url, CSRF (RFC 6749 §10.12)
verifier = generate_verifier()              # SECOND independent draw, PKCE (RFC 7636)
challenge = build_challenge(verifier)

# NOTE: redirect_uri uses literal "localhost" string (Google pre-registration).
# Listener binds 127.0.0.1 (loopback.py default) — DNS resolves localhost→127.0.0.1.
redirect_uri = f"http://{_REDIRECT_HOST_LITERAL}:{_REDIRECT_PORT}{_REDIRECT_PATH}"

authorize_url = _build_authorize_url(redirect_uri, state, challenge)
print(f"Open this URL in your browser:\n\n  {authorize_url}\n")

try:
    code = await wait_for_oauth_callback(
        port=_REDIRECT_PORT,                # FIXED, not allocate_loopback_port()
        expected_state=state,
        timeout=300.0,
    )
except OSError as exc:
    # Errno 48 (Darwin/BSD), 98 (Linux): EADDRINUSE
    raise AuthLoginError(
        f"Antigravity login: port {_REDIRECT_PORT} is already in use. "
        f"Close any other state-cli antigravity-login process or wait for "
        f"it to finish, then retry. Underlying: {exc}"
    ) from exc
```

**Anti-patterns:**
- Substituting `127.0.0.1` for `localhost` in the URL string (causes `redirect_uri_mismatch`).
- Calling `allocate_loopback_port()` (the kernel-allocated port will not match Google's pre-registration).
- Catching `OSError` silently and retrying on a different port (every other port also fails Google's pre-registration check).

### Pattern 2: Five-scope authorize URL (Gemini's three + `cclog` + `experimentsandconfigs`)

**What:** Same authorize URL builder as Phase 015 with two extra scopes appended. `access_type=offline` + `prompt=consent` remain mandatory (refresh-token issuance + force-consent for repeat logins).

**Scope source-of-truth (Google discovery doc link per CONTEXT.md mandate):**

The OAuth scopes list is documented at:
- Google's OAuth 2.0 scopes catalog: <https://developers.google.com/identity/protocols/oauth2/scopes>
- Specifically `cloud-platform` + `userinfo.email` + `userinfo.profile` are the three canonical Cloud Code Assist scopes (Gemini-CLI free-tier shape).
- `cclog` (Cloud Code Log) and `experimentsandconfigs` are Google-internal scopes used by Antigravity / Cloud Code Assist Companion API; they are NOT individually documented in Google's public scopes catalog (they are part of an internal OAuth scope set Google issues for Antigravity-class clients), but they are observed in production via the verified plugin sources cited under **Sources** below.

**Code (planner copies into `antigravity.py`):**

```python
_SCOPES: str = (
    "https://www.googleapis.com/auth/cloud-platform "
    "https://www.googleapis.com/auth/userinfo.email "
    "https://www.googleapis.com/auth/userinfo.profile "
    "https://www.googleapis.com/auth/cclog "
    "https://www.googleapis.com/auth/experimentsandconfigs"
)
# Antigravity-specific scope additions (vs Gemini-CLI):
#   cclog                  — Cloud Code Log telemetry attribution
#   experimentsandconfigs  — A/B test override resolution
# Both are MANDATORY: the loadCodeAssist boot call (v3 provider routing) 403s
# without them. Source: PicoClaw docs (verified 2026-04-30) +
# taoalpha gist (verified 2026-04-30) + NoeFabris/opencode-antigravity-auth
# constants.ts (cross-referenced).

_AUTHORIZE_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
# Same as Gemini — Google's universal OAuth 2.0 v2 endpoint.
# (PicoClaw doc shows /o/oauth2/v2/auth; gsd2-auth-analysis.md shows /o/oauth2/auth.
# The /v2/ variant is the current canonical endpoint per Google's docs;
# the unversioned variant is a deprecated alias that Google still honors.
# Use /v2/ for consistency with Phase 015.)

_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
# Identical to Gemini.
```

### Pattern 3: Plaintext identity constants with discovery-doc rationale comment (P1-3 / P2-3)

**What:** Two PUBLIC Desktop-App OAuth credentials, plaintext, with a 12-line comment explaining why and citing source.

```python
# ── Identity constants ───────────────────────────────────────────────────
# From NoeFabris/opencode-antigravity-auth `src/plugin/constants.ts` (verified
# 2026-04-30 against the archived main branch). Cross-checked against
# taoalpha/22773d2132519e55a4c7427fd3e96d8e (Antigravity quota-skill gist,
# 2026-04-30) and PicoClaw provider docs. These are PUBLIC distributed-app
# credentials — Google's Desktop-App OAuth pattern relies on PKCE + loopback
# redirect validation, not client_secret confidentiality.
#
# !! IMPORTANT — DO NOT obfuscate (P1-3) !!
# Base64-encoding, XOR, env-var indirection, or any other "defensive" transform
# is REJECTED:
#   1. AV scanners flag obfuscated literals in source as malicious;
#      corporate users' installs get quarantined.
#   2. Every observed Antigravity OAuth client ships these plaintext.
#   3. The actual security boundary is PKCE + loopback redirect validation
#      (RFC 8252) — NOT client_secret secrecy.
# See .planning/research/PITFALLS.md P1-3.
#
# ⚠️ Terms-of-Service note: third-party Antigravity OAuth clients have been
# observed to attract Google account moderation. The user has accepted this
# risk per .planning/PROJECT.md Key Decision row 14 ("All five auth methods
# day one"). This module IS the implementation; the policy decision lives
# at the project level.

_CLIENT_ID: str     = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
_CLIENT_SECRET: str = "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"
```

**P2-3 (Antigravity scope drift) is THIS phase's owned pitfall.** Document the scope list in code with a permanent-link to the Google OAuth scopes catalog and a CI check that diffs `_SCOPES` against the live discovery document. The planner MUST include a test that asserts the scope string contains all five entries; the test docstring should reference P2-3.

### Pattern 4: Token exchange + refresh (verbatim from Phase 015 with constant swap)

**Token exchange body** (same form-urlencoded shape as Gemini; only the constants change):

```python
body = {
    "code":          code,
    "client_id":     _CLIENT_ID,
    "client_secret": _CLIENT_SECRET,
    "redirect_uri":  redirect_uri,                        # http://localhost:51121/oauth-callback
    "grant_type":    "authorization_code",
    "code_verifier": verifier,
}
```

**Refresh body** (verbatim Gemini shape):

```python
body = {
    "grant_type":    "refresh_token",
    "refresh_token": cred.refresh,
    "client_id":     _CLIENT_ID,
    "client_secret": _CLIENT_SECRET,
}
# Same per-call AsyncClient(Timeout(10.0, connect=5.0), follow_redirects=False).
# Same precedence: invalid_grant first → AuthRefreshError("Refresh token rejected: ...");
# else generic AuthRefreshError(f"refresh http {status}: {body[:500]!r}").
# Same P2-2 rotation rule: new_refresh = parsed.refresh_token or cred.refresh.
```

**Critical reminder:** Both POSTs go through `httpx.AsyncClient`, NOT through litellm — CLAUDE.md cardinal rule: "OAuth traffic NEVER routes through litellm." The provider does NOT acquire its own filelock; Phase 013's `refresh_credential` owns that.

### Pattern 5: `http_headers(cred)` returns FOUR headers (Bearer + 3 Antigravity-specific)

**What:** The captured-header regression-test surface for AUTH-13 (Phase 022). Mirror the Antigravity-IDE byte-for-byte against verified sources.

```python
import orjson
import sys

def _platform_for_client_metadata() -> str:
    """Map sys.platform → Client-Metadata `platform` value.

    Antigravity's backend pattern-matches on the literal strings
    MACOS / LINUX / WINDOWS (uppercase, no separator). Computed per-call
    so tests can monkey-patch sys.platform across all three branches.
    """
    p = sys.platform
    if p == "darwin":
        return "MACOS"
    if p.startswith("linux"):
        return "LINUX"
    if p.startswith("win"):                                # win32 / cygwin / msys
        return "WINDOWS"
    return "LINUX"                                         # defensive fallback


# Module-level constant — referenced in the captured-header regression test.
# Use orjson.dumps(separators=(",", ":")) to produce a byte-stable JSON string
# (no whitespace) that matches the gemini-cli reference exactly.
_X_GOOG_API_CLIENT: str = "google-cloud-sdk vscode_cloudshelleditor/0.1"
_USER_AGENT_LITERAL: str = "antigravity"


def _build_client_metadata(platform: str) -> str:
    """Compose the Client-Metadata header value as deterministic JSON.

    orjson default key order is insertion-order; we explicitly insert
    ideType → platform → pluginType to match the IDE wire format.
    """
    return orjson.dumps(
        {"ideType": "ANTIGRAVITY", "platform": platform, "pluginType": "GEMINI"},
        # No fancy options — orjson emits compact JSON by default.
    ).decode("ascii")


# In AntigravityAuth class:

def http_headers(self, cred: Credential) -> dict[str, str]:
    """Bearer + three Antigravity-specific headers.

    cloudcode-pa.googleapis.com/v1internal (the Cloud Code Assist Companion
    API serving Antigravity inference) requires:
        Authorization:    Bearer <ya29.…>
        User-Agent:       antigravity
        X-Goog-Api-Client: google-cloud-sdk vscode_cloudshelleditor/0.1
        Client-Metadata:  {"ideType":"ANTIGRAVITY","platform":"<MACOS|LINUX|WINDOWS>","pluginType":"GEMINI"}
        Content-Type:     application/json   (caller's concern, not ours)

    AUTH-13 (Phase 022) golden-files this dict. Mutating it in v3 provider
    routing would break the regression test.
    """
    if not isinstance(cred, OAuthCredential):
        return {}
    return {
        "authorization":   f"Bearer {cred.access}",
        "user-agent":      _USER_AGENT_LITERAL,
        "x-goog-api-client": _X_GOOG_API_CLIENT,
        "client-metadata": _build_client_metadata(_platform_for_client_metadata()),
    }
```

**Note on `x-goog-user-project`:** Phase 015's `http_headers` returns `x-goog-user-project` IFF `cred.extras["project_id"]` is set. Antigravity also accepts that header for project-scoped quota attribution, but the verified Antigravity-IDE traffic does NOT include it (the project ID is encoded inside `Client-Metadata` via the loadCodeAssist boot, not in the Authorization-adjacent headers). **Phase 016's `http_headers` does NOT emit `x-goog-user-project`.** If v3 provider routing later needs it, that's v3's concern.

### Pattern 6: Token-shape sniffer is intentionally Gemini-shape-equivalent

**What:** `is_token(value)` returns `value.startswith("ya29.")` — same as Phase 015. This is BY DESIGN.

```python
def is_token(self, value: str) -> bool:
    """First branch of token-shape sniffer (Pitfall 5 / P1-1).

    Antigravity access tokens are Google OAuth tokens — they begin `ya29.`
    just like Gemini-CLI tokens. This method returns True for ANY ya29.*
    token; provider-level routing disambiguates Antigravity vs Gemini via
    the credential's `provider_id` field, NEVER via token sniffing.

    Each provider's is_token is INDEPENDENTLY AFFIRMATIVE:
        google_gemini.is_token("ya29.…")    → True
        antigravity.is_token("ya29.…")      → True
        anthropic.is_token("ya29.…")        → False  (Anthropic tokens are sk-ant-oat*)

    Phase 019 round-robin operates on (provider_id, idx) tuples — token
    sniffing is for boundary cases (e.g., "did the user paste an Anthropic
    token into the Gemini prompt?"), NOT for Gemini/Antigravity disambiguation.
    """
    return value.startswith("ya29.")
```

**Anti-pattern:** trying to disambiguate Gemini vs Antigravity tokens by inspecting the access-token string. The two providers issue tokens that are byte-for-byte identical in shape (same `ya29.` prefix, same opaque body). The Pydantic discriminator `provider_id` on `OAuthCredential` is the only correct disambiguator.

### Pattern 7: `_to_credential` adaptation (verbatim from Phase 015 with `provider_id` swap)

**What:** Mirror Phase 015's `_to_credential` exactly — id_token sub → `account_id`, id_token email → `extras["email"]` — with the provider_id constant updated.

```python
def _to_credential(
    resp: AntigravityTokenResponse,
    *,
    original_refresh: str,
    now: float,
) -> OAuthCredential:
    """Convert token-endpoint response → wire-shape OAuthCredential.

    Identical to google_gemini._to_credential except provider_id="google.antigravity".
    Same Phase 011 invariant: expires = now + expires_in (5-min buffer in
    is_expired layer, NOT in storage).

    Same P2-2 rotation rule (caller's concern in refresh()):
        new_refresh = parsed.refresh_token or original_refresh

    extras may include `project_id` once v3 provider routing fetches it via
    loadCodeAssist; for the login() call path, extras starts with email +
    email_verified only.
    """
    if resp.id_token:
        payload = _parse_id_token_payload(resp.id_token)
        account_id: str | None = payload.sub
        extras: dict[str, Any] = {}
        if payload.email:
            extras["email"] = payload.email
        if payload.email_verified is not None:
            extras["email_verified"] = payload.email_verified
    else:
        account_id = None
        extras = {}

    return OAuthCredential(
        access=resp.access_token,
        refresh=resp.refresh_token or original_refresh,
        expires=now + float(resp.expires_in),
        provider_id="google.antigravity",
        account_id=account_id,
        extras=extras,
    )
```

### Anti-Patterns to Avoid

- **Reusing `state == verifier` (Phase 014 / P0-8 — Anthropic-only):** identical reasoning as Phase 015. Two independent `generate_verifier()` calls.
- **Acquiring a filelock in `refresh()`:** Phase 013 already wraps it (refresh.py rule 9 — deadlock).
- **Persisting `parsed.refresh_token` only when changed:** P2-2 — always write whatever the response returned, falling back to `cred.refresh` only on omission.
- **Calling `allocate_loopback_port()`:** breaks Google's redirect_uri pre-registration — `redirect_uri_mismatch` 400.
- **Substituting `127.0.0.1` for `localhost` in the redirect_uri URL string:** same — `redirect_uri_mismatch`.
- **Setting `User-Agent: antigravity/<version>` instead of literal `antigravity`:** the IDE uses the version-suffixed form for IDE registration; the Cloud Companion API uses the literal. Mismatched UA → quota attribution lands in the wrong bucket; tokens authenticate but inference 403s with `IAM_PERMISSION_DENIED` (the January 2026 mass-revocation event).
- **Module-level singleton `httpx.AsyncClient`:** identical reasoning to Phase 014/015.
- **`Field(repr=False)` only on `access_token`:** both `access_token` AND `refresh_token` are secrets. Both need it. (The Pydantic model in this phase is `AntigravityTokenResponse`, structurally identical to `GoogleTokenResponse`.)
- **Computing `Client-Metadata.platform` at module load:** locks out test coverage of all three branches.
- **Routing OAuth traffic through litellm:** CLAUDE.md cardinal rule.
- **Treating the get-shit-done `antigravity` runtime as related to this phase:** unrelated product (npm CLI runtime). The Google Antigravity / Cloud Code Assist Companion API is the only relevant referent.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth refresh-token POST + JSON parse | Hand-roll a fresh httpx flow | Mirror `google_gemini.GoogleGeminiAuth.refresh` line-for-line, swap constants | Phase 015's refresh body already encodes the rotation rule, the `invalid_grant` precedence, and the per-call AsyncClient. Re-deriving it invites P2-2 regressions. |
| PKCE verifier / challenge generation | Custom RNG + manual base64 padding | `oauth_common/pkce.py` (Phase 014) | RFC 7636 compliance verified by 014 tests. |
| Loopback HTTP listener | `http.server.HTTPServer` (sync) or write a fresh asyncio listener | `oauth_common/loopback.wait_for_oauth_callback` (Phase 015, reused unchanged) | The listener already handles browser prefetch (`if not code_future.done()`), CSRF state validation, and success/failure URL redirect. **DO NOT** duplicate it in `antigravity.py`. |
| Port allocation | Calling `allocate_loopback_port()` | The literal constant `_REDIRECT_PORT = 51121` | Google's redirect_uri pre-registration mandates the fixed port. |
| id_token JWT payload parse | PyJWT or `google-auth-jwt` | Stdlib `base64.urlsafe_b64decode` + `orjson.loads` (mirror `google_gemini._parse_id_token_payload`) | Trust boundary is TLS to oauth2.googleapis.com; signature verification is a v3 nice-to-have. |
| Refresh-token rotation tracking | Compare-and-skip (`if new == old: skip`) | `parsed.refresh_token or cred.refresh` (P2-2 verbatim) | Treating rotation as opaque is simpler and correct. |
| Datetime → epoch conversion | Manual UTC offset math | `now + float(resp.expires_in)` (we never receive a `datetime` from the token endpoint — Google returns `expires_in: int` seconds) | Wire-shape epoch math is trivial; don't import `datetime`. |
| Browser auto-open | Custom subprocess | `print(authorize_url)` in 016; Phase 022 adds `webbrowser.open` + `--no-browser` | Same split as Phase 015. |
| `client_secret` obfuscation | base64 / XOR / env var | Plaintext source constant + rationale comment | P1-3. |
| `Client-Metadata` JSON serialization | Manual `'{"ideType":"ANTIGRAVITY",…}'` string concatenation | `orjson.dumps({...}).decode("ascii")` | Deterministic key order + escape correctness. orjson is already a dep (Phase 015 `_parse_id_token_payload`). |
| Argparse subcommand wiring | Hand-roll `if/elif args` | Mirror `google_gemini._main` line-for-line | Phase 015's argparse pattern (login + refresh subcommands, KeyboardInterrupt → 130, AuthLoginError → stderr+exit 1) is the validated template. |
| Vault persistence in `_main login` | Direct dict assignment | `vault.providers.setdefault("google.antigravity", []).append(cred)` | Preserves P1-7 array invariant; supports Phase 019 round-robin. |

**Key insight:** Phase 016 is structurally Phase 015 with constant swaps + one extra section (Antigravity outbound headers). The plan should be ~3 waves (constants + RED tests, helpers + sync methods, async login/refresh + argparse) — same shape as Phase 015's 4-plan progression but compressed because the loopback module already exists.

## Common Pitfalls

(Each pitfall maps to a P0/P1/P2 in `.planning/research/PITFALLS.md` where applicable. Inherited pitfalls retain their owners; this phase's NEW owned pitfalls are flagged with **OWNED**.)

### Pitfall 1: client_secret obfuscation (P1-3 — inherited from Phase 015)

**What goes wrong:** Same as Phase 015. AV scanners flag obfuscated literals; corporate AV blocks install.
**Why it happens:** Intuition that "secrets shouldn't be plaintext."
**How to avoid:** Plaintext `_CLIENT_ID` + `_CLIENT_SECRET` with rationale comment block (see Pattern 3 above). NEVER base64/XOR/env-var.
**Warning signs:** Snyk/Trivy flags; corporate AV blocks install.

### Pitfall 2: Refresh-token rotation silently dropped (P2-2 — inherited from Phase 015)

**What goes wrong:** Developer's `refresh()` returns `cred.model_copy(update={"access": ..., "expires": ...})` and forgets `"refresh": ...`. Next refresh uses the stale token; Google may have rotated (and revoked the old one).
**Why it happens:** The rotation contract is silent — Google's response may or may not include a new refresh_token.
**How to avoid:** Verbatim `new_refresh = parsed.refresh_token or cred.refresh` line. NEVER compare-and-skip.
**Warning signs:** OAuth works for exactly one refresh cycle then 401s; clustered around the 5-min-buffer-fire window.

### Pitfall 3: Antigravity scope drift (P2-3 — **OWNED by this phase**)

**What goes wrong:** Google adds a required scope (e.g., a new `cclog` variant or splits `experimentsandconfigs` into two scopes); our list is stale; auth succeeds (token exchange OK) but inference returns `IAM_PERMISSION_DENIED` 403 on the loadCodeAssist boot or first inference call.
**Why it happens:** `cclog` and `experimentsandconfigs` are Google-internal scopes not on the public OAuth scopes catalog. Drift is silent — only inference 403s reveal it.
**How to avoid:** Hard-code `_SCOPES` with all 5 entries + comment block citing the verified plugin sources (see Pattern 2). Phase 022's CI golden-file regression compares scope string against captured Antigravity-IDE traffic. Periodic CI check (quarterly) re-verifies against the live PicoClaw / NoeFabris / taoalpha sources.
**Warning signs:** `IAM_PERMISSION_DENIED` clustered after a Google-side rollout; tokens still validate, login still completes.

### Pitfall 4: Port 51121 collision (**NEW — OWNED by this phase**)

**What goes wrong:** Two `state` CLIs running concurrently both try to bind `:51121`; second fails with `OSError [Errno 48] Address already in use` (Darwin) / `Errno 98` (Linux).
**Why it happens:** Antigravity's pre-registered redirect_uri pins the port — kernel-allocation is impossible.
**How to avoid:** Catch `OSError` from `wait_for_oauth_callback`, raise `AuthLoginError` with explicit remediation: "port 51121 is already in use; close any other state-cli antigravity-login process or wait for it to finish, then retry." Document in error message that this is a fundamental constraint of Google's redirect_uri pre-registration, NOT a `state` bug.
**Warning signs:** `EADDRINUSE` on the loopback listener; user retries immediately and it works (because the first CLI completed).

### Pitfall 5: `localhost` vs `127.0.0.1` in redirect_uri (**NEW — OWNED by this phase**)

**What goes wrong:** Developer "improves" the redirect_uri by substituting `127.0.0.1` (intuitive — IP literal is more deterministic than DNS); token exchange returns 400 with `redirect_uri_mismatch`.
**Why it happens:** Google's OAuth server enforces redirect_uri exact-string match. The Antigravity OAuth client was pre-registered with the literal `localhost:51121/oauth-callback`; ANY deviation 400s.
**How to avoid:** Pin `_REDIRECT_HOST_LITERAL = "localhost"` (NOT `127.0.0.1`) and use it in the URL string. The asyncio listener's bind address is independent — `wait_for_oauth_callback` binds `127.0.0.1` regardless because that's what the underlying `asyncio.start_server` does, and `localhost` resolves to `127.0.0.1` on every common OS. Add a unit test: `_build_authorize_url(redirect_uri=...)` with `127.0.0.1` substituted should be detectable in a regression test (assert `"localhost"` in the constructed URL).
**Warning signs:** `redirect_uri_mismatch` 400 from token endpoint.

### Pitfall 6: ya29-prefix collision with Gemini in token sniffer (**NEW — OWNED by this phase**)

**What goes wrong:** Engineer assumes `is_token` is the canonical disambiguator and writes a routing layer that picks the provider by sniffing the access token. Antigravity tokens are byte-for-byte identical in shape to Gemini tokens (same `ya29.` prefix). Result: a Gemini token gets routed to the Antigravity inference endpoint or vice versa; `IAM_PERMISSION_DENIED` (because the Antigravity-scoped token doesn't authorize the Gemini-CLI free-tier endpoint, and vice versa).
**Why it happens:** Cargo-culting Anthropic's `is_token` discriminator pattern (where `sk-ant-oat*` distinguishes OAuth from `sk-ant-api*` API key) — a different problem domain.
**How to avoid:** **`is_token` is provider-affirmative, NOT provider-exclusive.** Both `google_gemini.is_token("ya29.…")` and `antigravity.is_token("ya29.…")` MUST return True. The discriminator at the routing layer is `cred.provider_id`, never the token shape. Document this in the `is_token` docstring (see Pattern 6 above). Phase 019 round-robin operates on `(provider_id, idx)` tuples — never on token sniffing.
**Warning signs:** Random `IAM_PERMISSION_DENIED` after multi-cred config with both Gemini + Antigravity tokens.

### Pitfall 7: Headless / SSH environments break loopback redirect (inherited from Phase 015)

**What goes wrong:** User runs `state auth login google.antigravity` on a remote SSH session; browser opens locally; redirect to `http://localhost:51121/oauth-callback` lands on the laptop, not the SSH server. Loopback never receives the callback.
**Why it happens:** Loopback flows assume browser and listener share a host.
**How to avoid:** Phase 016 prints the URL for manual fallback (Phase 022 will add `webbrowser.open` + `--no-browser`). Document SSH port-forwarding (`ssh -L 51121:localhost:51121 server`) in Phase 022's help text. Note that `OPENCODE_ANTIGRAVITY_OAUTH_BIND` (NoeFabris's env-var override for binding `0.0.0.0` in WSL/Docker) is OUT OF SCOPE for v2 — defer to Phase 022 if user demand arises.
**Warning signs:** `asyncio.TimeoutError` on the loopback `wait_for`; user reports "browser opened but nothing happened."

### Pitfall 8: `expires` epoch math wrong on non-UTC machines (inherited from Phase 015)

**What goes wrong:** Same as Phase 015. We don't get a `datetime` from Google's token endpoint — we get `expires_in: int`. The math `now + float(resp.expires_in)` is correct universally; this pitfall surfaces ONLY if a developer "improves" by reading `resp.expiry` (there is no such field in our `AntigravityTokenResponse`) or applies a `datetime` conversion.
**How to avoid:** Use the verbatim Phase 015 helper: `expires = now + float(resp.expires_in)`. Don't introduce `datetime`.
**Warning signs:** Tests pass in CI (UTC) but fail on developer laptops in non-UTC timezones — same as Phase 015 §Pitfall 7.

### Pitfall 9: `account_id` sourcing — id_token JWT vs userinfo HTTP call (inherited from Phase 015)

**What goes wrong:** Developer adds an extra HTTP call to `https://www.googleapis.com/oauth2/v2/userinfo` to populate `account_id`. Adds latency, adds a failure mode (login appears to succeed but `account_id` is None), adds an extra dep on `accounts.google.com` reachability.
**How to avoid:** Decode the id_token JWT payload (already a base64url-no-pad JWT — middle section is JSON with `sub` + `email`); zero extra deps, zero extra HTTP. **Reuse `google_gemini._parse_id_token_payload` verbatim** (or duplicate it inline; see "Recommended Project Structure" — both are acceptable).
**Warning signs:** `cred.account_id is None` after a successful login; UI shows "Logged in as None".

### Pitfall 10: kebab-case `provider_id` collision with Phase 015 (Pitfall 9 from Phase 015 — inherited)

**What goes wrong:** Both Gemini and Antigravity stored under the same provider_id key in AuthVault → Phase 019 round-robin alternates between Gemini and Antigravity tokens → wrong API receives wrong token → `IAM_PERMISSION_DENIED`.
**How to avoid:** `provider_id="google.antigravity"` (sibling to `"google.gemini_cli"`). The dot is a namespace separator; AuthVault treats them as completely separate buckets.
**Warning signs:** Random 401s/403s after a refresh cycle in a multi-cred (Gemini + Antigravity) config.

### Pitfall 11: Antigravity ToS / IAM_PERMISSION_DENIED revocation events (**NEW — informational**)

**What goes wrong:** Google has previously (January 2026) revoked Antigravity Cloud AI Companion API access for ALL third-party OAuth clients en masse. The NoeFabris plugin was archived 2026-03-30 in response. Tokens authenticate (login + refresh succeed) but inference 403s with `IAM_PERMISSION_DENIED`.
**Why it happens:** Google's ToS forbid third-party use of the Antigravity OAuth client; mass revocations are a moderation lever.
**How to avoid:** **Cannot avoid at the protocol layer.** The user has accepted this risk per `.planning/PROJECT.md` Key Decision row 14 ("All five auth methods day one"). Phase 016 implements the technical surface; if Google flips the kill switch again, Phase 022's CLI surfaces `IAM_PERMISSION_DENIED` as a structured error (`AuthError`) with a remediation message linking to the discovery doc + a note that the user may need to switch to the Gemini-CLI free-tier flow. This is project-level policy, NOT something the auth provider can transparently handle.
**Warning signs:** Login + refresh succeed; inference 403s with `IAM_PERMISSION_DENIED` for all users simultaneously (correlated event, not per-user).

### Pitfall 12: Packed-refresh-string drift from `opencode-antigravity-auth` (informational — explicitly NOT inherited)

**What goes wrong:** NoeFabris's plugin packs `<refreshToken>|<projectId>|<managedProjectId>` into a single string in its on-disk vault. A future first-run-import (Phase 021) might naively import the plugin's `~/.config/opencode/antigravity-accounts.json` and store the packed string as `cred.refresh` — breaking the plain-token contract.
**How to avoid:** `OAuthCredential.extras` already has `project_id` + `managed_project_id` as separate keys (per `OAuthCredential.extras: dict[str, Any]` shape). Phase 021's import logic MUST split the packed string and store the components correctly. **This is documented here for Phase 021's planner; Phase 016's `refresh` field stores the raw refresh token only.**
**Warning signs:** `cred.refresh` contains pipe characters; refresh POST returns 400 (`invalid_grant` because the token is malformed).

## Code Examples

Verified patterns. All examples assume the planner mirrors `providers/google_gemini.py`'s structure section-for-section.

### 1. Module Header (mirror google_gemini.py)

```python
"""Antigravity (Google Cloud Code Assist Companion) OAuth provider.

Phase 016 (M-A2 / AUTH-03 / P2-3 owner). Third concrete AuthMethod
implementation (after Phase 014 Anthropic, Phase 015 Gemini-CLI).
Mirrors NoeFabris/opencode-antigravity-auth's flow byte-for-byte to
unlock the Cloud Code Assist Companion API at cloudcode-pa.googleapis.com/
v1internal — Google's unified gateway for Gemini 3 + Claude Opus +
GPT-OSS via Antigravity rate limits.

⚠️ Terms-of-Service: third-party Antigravity OAuth clients have been
observed to attract Google account moderation. The user has accepted
this risk per .planning/PROJECT.md Key Decision row 14 ('All five auth
methods day one'). This module IS the implementation; the policy
decision lives at the project level.

Module layout (mirrors providers/google_gemini.py):
  * Identity constants (URLs, scopes, plaintext client_id/secret with P1-3 rationale,
    Antigravity-specific outbound headers)
  * Pydantic models (AntigravityTokenResponse, _GoogleIdTokenPayload — duplicated from Phase 015)
  * Helpers (_parse_id_token_payload, _to_credential, _build_authorize_url,
    _exchange_code, _platform_for_client_metadata, _build_client_metadata)
  * AntigravityAuth class (satisfies AuthMethod Protocol)
  * `if __name__ == '__main__'` argparse entry-point

Cardinal rules — IDENTICAL to Phase 015 with these deltas:
  - provider_id = 'google.antigravity' (Pitfall 10)
  - FIXED port 51121 + literal 'localhost' redirect_uri (Pitfalls 4, 5)
  - 5 scopes (Gemini's 3 + cclog + experimentsandconfigs)
  - http_headers emits 4 headers (Bearer + User-Agent + X-Goog-Api-Client + Client-Metadata)
  - is_token returns True for ya29.* — by design (Pitfall 6); provider_id disambiguates

See .planning/milestones/v2/phases/016-antigravity-oauth-provider/
016-RESEARCH.md for full rationale, 12 pitfalls, downstream contracts.
"""
```

### 2. Constants Block (full)

```python
# ── Identity constants — DO NOT obfuscate (P1-3) ─────────────────────────
# Sources cross-verified 2026-04-30:
#   * NoeFabris/opencode-antigravity-auth src/plugin/constants.ts (archived main)
#   * https://docs.picoclaw.io/docs/providers/antigravity/
#   * https://gist.github.com/taoalpha/22773d2132519e55a4c7427fd3e96d8e

_CLIENT_ID: str     = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
_CLIENT_SECRET: str = "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"

# ── URL constants ────────────────────────────────────────────────────────

_AUTHORIZE_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL: str     = "https://oauth2.googleapis.com/token"

# ── Loopback redirect (FIXED — pre-registered with Google's OAuth client) ───

_REDIRECT_HOST_LITERAL: str = "localhost"      # NOT '127.0.0.1' — exact-match (Pitfall 5)
_REDIRECT_PORT: int         = 51121            # NOT kernel-allocated (Pitfall 4)
_REDIRECT_PATH: str         = "/oauth-callback"

# ── OAuth scopes (5: Gemini's 3 + cclog + experimentsandconfigs) ─────────
# P2-3 owns this list. Drift surfaces as IAM_PERMISSION_DENIED on inference.
# Discovery doc: https://developers.google.com/identity/protocols/oauth2/scopes

_SCOPES: str = (
    "https://www.googleapis.com/auth/cloud-platform "
    "https://www.googleapis.com/auth/userinfo.email "
    "https://www.googleapis.com/auth/userinfo.profile "
    "https://www.googleapis.com/auth/cclog "
    "https://www.googleapis.com/auth/experimentsandconfigs"
)

# ── Antigravity-specific outbound headers (AUTH-13 regression-test surface) ──

_USER_AGENT_LITERAL: str   = "antigravity"
_X_GOOG_API_CLIENT: str    = "google-cloud-sdk vscode_cloudshelleditor/0.1"
# Client-Metadata is built per-call so sys.platform monkeypatch works in tests.
```

### 3. Authorize URL Builder (mirror Phase 015, swap constants + scopes)

```python
def _build_authorize_url(redirect_uri: str, state: str, challenge: str) -> str:
    qs = urlencode({
        "client_id":             _CLIENT_ID,
        "redirect_uri":          redirect_uri,                # http://localhost:51121/oauth-callback
        "response_type":         "code",
        "scope":                 _SCOPES,                     # 5 scopes (vs Gemini's 3)
        "state":                 state,                       # independent of verifier
        "code_challenge":        challenge,
        "code_challenge_method": "S256",
        "access_type":           "offline",                   # mandatory for refresh_token
        "prompt":                "consent",                   # force refresh_token issuance
    })
    return f"{_AUTHORIZE_URL}?{qs}"
```

### 4. Token Exchange + Refresh Bodies

```python
# In _exchange_code():
body = {
    "code":          code,
    "client_id":     _CLIENT_ID,
    "client_secret": _CLIENT_SECRET,
    "redirect_uri":  redirect_uri,
    "grant_type":    "authorization_code",
    "code_verifier": verifier,
}
# POST to _TOKEN_URL with data=body, headers={"accept": "application/json"}.
# Per-call AsyncClient(Timeout(10.0, connect=5.0), follow_redirects=False).
# Same error precedence as Phase 015.

# In refresh():
body = {
    "grant_type":    "refresh_token",
    "refresh_token": cred.refresh,
    "client_id":     _CLIENT_ID,
    "client_secret": _CLIENT_SECRET,
}
# Same per-call AsyncClient. Same invalid_grant precedence.
# Same P2-2 rotation: new_refresh = parsed.refresh_token or cred.refresh.
# Same model_copy(update={...}) construction — preserves account_id + extras.
```

### 5. Client-Metadata + Platform Sniff

```python
def _platform_for_client_metadata() -> str:
    p = sys.platform
    if p == "darwin":              return "MACOS"
    if p.startswith("linux"):      return "LINUX"
    if p.startswith("win"):        return "WINDOWS"   # win32 / cygwin / msys
    return "LINUX"                                    # defensive fallback


def _build_client_metadata(platform: str) -> str:
    return orjson.dumps(
        {"ideType": "ANTIGRAVITY", "platform": platform, "pluginType": "GEMINI"},
    ).decode("ascii")
```

### 6. http_headers (regression-test surface)

```python
def http_headers(self, cred: Credential) -> dict[str, str]:
    if not isinstance(cred, OAuthCredential):
        return {}
    return {
        "authorization":     f"Bearer {cred.access}",
        "user-agent":        _USER_AGENT_LITERAL,
        "x-goog-api-client": _X_GOOG_API_CLIENT,
        "client-metadata":   _build_client_metadata(_platform_for_client_metadata()),
    }
```

### 7. argparse `_main` (mirror Phase 015 — only the default `provider_id` and import path change)

```python
# In _main():
sub.add_parser("login", help="Run the interactive Antigravity OAuth loopback login flow.")
refresh_parser = sub.add_parser(
    "refresh",
    help="Refresh an existing Antigravity credential via Phase 013's filelock-guarded path.",
)
refresh_parser.add_argument(
    "provider_id",
    nargs="?",
    default="google.antigravity",            # ← was "google.gemini_cli" in Phase 015
    help="Provider ID to refresh (default: google.antigravity).",
)
# … rest is identical to Phase 015's _main. KeyboardInterrupt → 130, AuthLoginError → 1, etc.
# Vault persistence: vault.providers.setdefault("google.antigravity", []).append(cred)
```

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.0 + pytest-asyncio 1.3.0 (asyncio_mode=strict) |
| Config file | `pyproject.toml` (existing — `[tool.pytest.ini_options]` already configures `asyncio_mode = "strict"` and includes `tests/` in `testpaths`) |
| Quick run command | `PYTHONPATH=$PWD/src pytest tests/auth/providers/test_antigravity.py -q` |
| Full suite command | `PYTHONPATH=$PWD/src pytest tests/auth -q` |

(The `PYTHONPATH=$PWD/src` prefix is a known worktree-vs-installed-package workaround documented in Phase 015's 015-04-SUMMARY §Deviations — the same fix applies to this phase if executed in a worktree.)

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| AUTH-03 | `AntigravityAuth` satisfies `AuthMethod` Protocol structurally | unit | `pytest tests/auth/providers/test_antigravity.py::test_satisfies_auth_method_protocol -x` | ❌ Wave 0 |
| AUTH-03 | `provider_id == "google.antigravity"` | unit | `pytest tests/auth/providers/test_antigravity.py::test_provider_id -x` | ❌ Wave 0 |
| AUTH-03 | Plaintext `_CLIENT_ID` + `_CLIENT_SECRET` literals present (P1-3 enforcement) | unit | `pytest tests/auth/providers/test_antigravity.py::test_client_secret_plaintext_no_obfuscation -x` | ❌ Wave 0 |
| AUTH-03 | `_SCOPES` contains all 5 scopes (cloud-platform, userinfo.email, userinfo.profile, cclog, experimentsandconfigs) — P2-3 owned | unit | `pytest tests/auth/providers/test_antigravity.py::test_scopes_includes_cclog_and_experiments -x` | ❌ Wave 0 |
| AUTH-03 | `_build_authorize_url` includes `access_type=offline` AND `prompt=consent` | unit | `pytest tests/auth/providers/test_antigravity.py::test_authorize_url_offline_consent -x` | ❌ Wave 0 |
| AUTH-03 | `_build_authorize_url` uses literal `localhost:51121/oauth-callback` (NOT `127.0.0.1`) — Pitfall 5 | unit | `pytest tests/auth/providers/test_antigravity.py::test_redirect_uri_uses_localhost_literal -x` | ❌ Wave 0 |
| AUTH-03 | `state` and `verifier` are TWO independent `generate_verifier()` calls (P0-8 reuse forbidden) | unit | `pytest tests/auth/providers/test_antigravity.py::test_state_and_verifier_independent -x` | ❌ Wave 0 |
| AUTH-03 | `_exchange_code` POSTs form-urlencoded body with all 6 fields | unit (pytest-httpx) | `pytest tests/auth/providers/test_antigravity.py::test_exchange_code_body -x` | ❌ Wave 0 |
| AUTH-03 | `_to_credential` populates `account_id` from id_token sub | unit | `pytest tests/auth/providers/test_antigravity.py::test_to_credential_account_id_from_id_token -x` | ❌ Wave 0 |
| AUTH-03 | `_to_credential` sets `provider_id="google.antigravity"` | unit | `pytest tests/auth/providers/test_antigravity.py::test_to_credential_provider_id -x` | ❌ Wave 0 |
| AUTH-03 | `refresh()` sends correct refresh-grant body (4 fields) | unit (pytest-httpx) | `pytest tests/auth/providers/test_antigravity.py::test_refresh_body -x` | ❌ Wave 0 |
| AUTH-03 | Refresh-token rotation: persist new token IFF returned, else preserve original (P2-2 verbatim) | unit (pytest-httpx — both branches) | `pytest tests/auth/providers/test_antigravity.py::test_refresh_rotation_when_returned tests/auth/providers/test_antigravity.py::test_refresh_rotation_when_omitted -x` | ❌ Wave 0 |
| AUTH-03 | `refresh()` raises `AuthRefreshError` on `invalid_grant` with precedence-first parsing | unit (pytest-httpx) | `pytest tests/auth/providers/test_antigravity.py::test_refresh_invalid_grant -x` | ❌ Wave 0 |
| AUTH-03 | `refresh()` does NOT acquire its own filelock (refresh.py rule 9) | unit (grep gate) | `pytest tests/auth/providers/test_antigravity.py::test_no_filelock_imports -x` | ❌ Wave 0 |
| AUTH-03 | `is_expired` delegates to `is_expired_buffered` (5-min buffer; no internal `time.time()`) | unit | `pytest tests/auth/providers/test_antigravity.py::test_is_expired_uses_buffered -x` | ❌ Wave 0 |
| AUTH-03 | `is_token` returns True for `ya29.…` (Pitfall 6 — by-design Gemini-shape collision) | unit | `pytest tests/auth/providers/test_antigravity.py::test_is_token_ya29_prefix -x` | ❌ Wave 0 |
| AUTH-03 | `http_headers` emits Bearer + User-Agent + X-Goog-Api-Client + Client-Metadata | unit | `pytest tests/auth/providers/test_antigravity.py::test_http_headers_four_keys -x` | ❌ Wave 0 |
| AUTH-03 | `Client-Metadata` `platform` is correct on darwin/linux/win32 (3 branches) | unit (monkeypatch sys.platform) | `pytest tests/auth/providers/test_antigravity.py::test_client_metadata_platform_branches -x` | ❌ Wave 0 |
| AUTH-03 | `User-Agent` is the literal `antigravity` (NOT version-suffixed) | unit | `pytest tests/auth/providers/test_antigravity.py::test_user_agent_literal -x` | ❌ Wave 0 |
| AUTH-03 | `login()` calls `wait_for_oauth_callback(port=51121, ...)` (FIXED port — Pitfall 4) | unit (mock loopback) | `pytest tests/auth/providers/test_antigravity.py::test_login_uses_fixed_port -x` | ❌ Wave 0 |
| AUTH-03 | `login()` raises `AuthLoginError` on `OSError` (port 51121 in use) | unit | `pytest tests/auth/providers/test_antigravity.py::test_login_port_in_use -x` | ❌ Wave 0 |
| AUTH-03 | `login()` end-to-end: state CSRF + token exchange + credential construction | unit (mock loopback + pytest-httpx) | `pytest tests/auth/providers/test_antigravity.py::test_login_happy_path -x` | ❌ Wave 0 |
| AUTH-03 | `_main` argparse: `login` + `refresh` subcommands; KeyboardInterrupt → 130 | unit (capsys + monkeypatch) | `pytest tests/auth/providers/test_antigravity.py::test_main_argparse_subcommands -x` | ❌ Wave 0 |
| AUTH-03 | Vault persistence in `_main login`: `setdefault("google.antigravity", []).append(cred)` (P1-7) | unit (mock vault) | `pytest tests/auth/providers/test_antigravity.py::test_main_vault_persistence -x` | ❌ Wave 0 |
| AUTH-03 | Phase 013 integration: `_main refresh` drives `refresh_credential` (filelock + double-check) | integration | `pytest tests/auth/providers/test_antigravity.py::test_main_refresh_drives_phase013 -x` | ❌ Wave 0 |
| AUTH-03 | NO `import litellm` / `from litellm` (cardinal rule grep gate) | unit (grep) | `pytest tests/auth/providers/test_antigravity.py::test_no_litellm_imports -x` | ❌ Wave 0 |
| AUTH-03 | NO `state.build.*` / `state.teach.*` imports (mode isolation grep gate) | unit (grep) | `pytest tests/auth/providers/test_antigravity.py::test_no_mode_specific_imports -x` | ❌ Wave 0 |
| AUTH-03 | P1-3 rationale comment block present in source (regression test) | unit (grep) | `pytest tests/auth/providers/test_antigravity.py::test_p1_3_rationale_present -x` | ❌ Wave 0 |
| AUTH-03 | Captured-header golden-file (AUTH-13 v2 stub): `http_headers` matches expected dict byte-for-byte | unit (snapshot) | `pytest tests/auth/providers/test_antigravity.py::test_http_headers_golden_file -x` | ❌ Wave 0 |

(All test files are NEW — Wave 0 must create them.)

### Sampling Rate

- **Per task commit:** `PYTHONPATH=$PWD/src pytest tests/auth/providers/test_antigravity.py -q`
- **Per wave merge:** `PYTHONPATH=$PWD/src pytest tests/auth -q` (full auth suite — must remain green; current baseline 124 passed / 1 skipped at end of Phase 015)
- **Phase gate:** `PYTHONPATH=$PWD/src pytest -q` (full project test suite — must exit 0 before `/gsd:verify-work`)

### Wave 0 Gaps

- [ ] `tests/auth/providers/test_antigravity.py` — covers AUTH-03 (~30 tests, mirroring `test_google_gemini.py` shape; planner copies and adapts)
- [ ] `src/state_core/auth/providers/antigravity.py` — the provider module itself (created during Wave 1 / 2 / 3 — RED → GREEN)
- [ ] (OPTIONAL) `src/state_core/auth/oauth_common/idtoken.py` + `tests/auth/oauth_common/test_idtoken.py` IFF planner chooses to extract `_parse_id_token_payload`. Recommendation: ship duplicated; promote in v3.
- [ ] No new framework install or fixtures needed — `tests/auth/conftest.py` already provides shared fixtures (vault setup, monkeypatch helpers).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-roll the loopback HTTP listener per provider | Reuse `oauth_common/loopback.py` from Phase 015 | 2026-04-30 (Phase 015 shipped) | Phase 016 saves ~80 LOC + tests; sole shared module across Google providers. |
| Compute `Client-Metadata.platform` at module load | Compute per-call inside `http_headers` | This phase | Enables monkey-patch testing across all 3 platform branches. |
| Conflate `state` and `verifier` (Anthropic P0-8 carryover) | Two independent `generate_verifier()` calls | Phase 015 (2026-04-30) | Correct CSRF protection on the loopback redirect. |
| Use `127.0.0.1` in the redirect_uri URL | Use literal `localhost` (Antigravity-specific) | This phase | Avoids `redirect_uri_mismatch` 400. |
| Kernel-allocate the loopback port | FIXED port 51121 (Antigravity-specific) | This phase | Required by Google's redirect_uri pre-registration on the Antigravity client. |

**Deprecated / no longer recommended:**
- `User-Agent: antigravity/1.15.8 windows/amd64` — old IDE-registration shape; the Cloud Companion API uses literal `antigravity` (verified taoalpha 2026-04-30).
- Packed-refresh-string `<refresh>|<projectId>|<managedProjectId>` (NoeFabris encoding) — `OAuthCredential.extras` accepts the components as separate keys.

## Open Questions (RESOLVED)

All open questions have been resolved during this research pass. No items deferred to plan-phase.

1. **Is the flow device-code or loopback?**
   - **RESOLVED:** PKCE-with-loopback (RFC 8252). Cross-verified across NoeFabris/opencode-antigravity-auth source (token.ts, server.ts), shekohex/opencode-google-antigravity-auth README, PicoClaw provider docs, and taoalpha quota-skill gist. Roadmap label "device-code" is imprecise.

2. **Which client_id does Antigravity use? Same as Gemini's `681255809395-...`?**
   - **RESOLVED:** Different. Antigravity client_id is `1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`; client_secret is `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`. Verified across three independent sources (NoeFabris source, PicoClaw docs, taoalpha gist).

3. **Exact scope list and discovery-doc URL?**
   - **RESOLVED:** Five scopes — `cloud-platform`, `userinfo.email`, `userinfo.profile`, `cclog`, `experimentsandconfigs`. Discovery-doc link: <https://developers.google.com/identity/protocols/oauth2/scopes>. Note: `cclog` and `experimentsandconfigs` are Google-internal and NOT individually documented in the public catalog (P2-3 — the planner MUST capture this in the `_SCOPES` rationale comment with explicit citation to the verified plugin sources).

4. **Refresh-token rotation behavior?**
   - **RESOLVED:** Same as Gemini. Google sometimes rotates the refresh_token on refresh, sometimes does not. P2-2 rule applies verbatim: `new_refresh = parsed.refresh_token or cred.refresh`. NoeFabris token.ts confirms: `refreshToken: payload.refresh_token ?? parts.refreshToken` — same opaque-rotation pattern.

5. **provider_id naming?**
   - **RESOLVED:** `"google.antigravity"` — sibling to `"google.gemini_cli"`. Dot-separated namespace within AuthVault `providers` dict. Confirmed by Phase 015 RESEARCH §Pitfall 9 and `base.py` docstring.

6. **Reusable scaffolding from Phase 015?**
   - **RESOLVED:**
     - `oauth_common/pkce.py` — reused unchanged (RFC 7636 PKCE).
     - `oauth_common/loopback.py` — reused unchanged (`wait_for_oauth_callback`, `SIGN_IN_*_URL`). Note `allocate_loopback_port` is NOT called here (port is FIXED 51121).
     - `state_core.auth.errors` — reused unchanged (`AuthLoginError`, `AuthRefreshError`).
     - `_parse_id_token_payload` — duplicated inline OR extracted to `oauth_common/idtoken.py`. Planner discretion; recommendation: duplicate inline for v2 hygiene velocity.

7. **Token shape sniffer disambiguation?**
   - **RESOLVED:** `is_token("ya29.…")` returns True for BOTH Gemini and Antigravity by design (Pitfall 6). The discriminator at routing layer is `cred.provider_id`, NEVER token sniffing. Phase 019 round-robin operates on `(provider_id, idx)` tuples.

8. **Custom HTTP headers required?**
   - **RESOLVED:** Three Antigravity-specific headers in addition to Bearer:
     - `User-Agent: antigravity` (literal — NOT version-suffixed; Cloud Companion API uses literal)
     - `X-Goog-Api-Client: google-cloud-sdk vscode_cloudshelleditor/0.1`
     - `Client-Metadata: {"ideType":"ANTIGRAVITY","platform":"<MACOS|LINUX|WINDOWS>","pluginType":"GEMINI"}` (per-call platform sniff)
     `x-goog-user-project` is NOT emitted (project_id lives in `Client-Metadata` and the loadCodeAssist boot, not in Authorization-adjacent headers).

9. **Pitfalls inherited from 014/015?**
   - **RESOLVED:** Inherited: P1-3 (plaintext client_secret), P2-2 (refresh rotation), P0-7 / AUTH-09 (5-min buffer in is_expired), Pitfall 4 (state CSRF), Pitfall 7 (`expires` epoch math), Pitfall 8 (id_token JWT parse). NEW owned: P2-3 (Antigravity scope drift), Pitfall 4 (port 51121 collision), Pitfall 5 (`localhost` vs `127.0.0.1`), Pitfall 6 (ya29 prefix collision with Gemini), Pitfall 11 (ToS / IAM revocation events — informational), Pitfall 12 (packed-refresh-string drift — flagged for Phase 021).

10. **Is "Antigravity" the same as get-shit-done's antigravity CLI?**
    - **RESOLVED:** No. Disambiguated in the **Disambiguation** section above. The phase targets Google's Antigravity IDE / Cloud Code Assist Companion API (Cloud-Platform-priced multi-model gateway). The get-shit-done references in `state-inputs/get-shit-done/tests/antigravity-*.test.cjs` are an unrelated npm CLI runtime.

11. **Redirect URI host: `localhost` or `127.0.0.1`?**
    - **RESOLVED:** Literal `localhost` (Pitfall 5). Listener still binds `127.0.0.1` (loopback.py default); only the URL string sent to Google differs.

12. **Loopback port: kernel-allocated or fixed?**
    - **RESOLVED:** FIXED 51121 (Pitfall 4). Required by Google's redirect_uri pre-registration on the Antigravity OAuth client.

13. **Should `_parse_id_token_payload` be promoted to `oauth_common/idtoken.py`?**
    - **RESOLVED:** Planner discretion. Recommendation: ship duplicated for v2 (YAGNI; cycle pressure on this phase is real); promote in a v3 hygiene pass. Both options are acceptable.

14. **What about the project_id / managed_project_id packed-refresh-string from NoeFabris's plugin?**
    - **RESOLVED:** OUT OF SCOPE for Phase 016. `OAuthCredential.extras` already supports `project_id` + `managed_project_id` as separate keys; Phase 021 (first-run import) will split the packed string at import time.

## Sources

### Primary (HIGH confidence)

- **Phase 015 RESEARCH** (`/Users/tmac/projects/state/.planning/milestones/v2/phases/015-gemini-cli-oauth-provider/015-RESEARCH.md`) — flow shape, refresh-rotation rule, id_token JWT parse, AuthMethod Protocol contract, oauth_common modules.
- **Phase 015 SUMMARY** (`/Users/tmac/projects/state/.planning/milestones/v2/phases/015-gemini-cli-oauth-provider/015-04-SUMMARY.md`) — argparse `_main` pattern, vault persistence, Phase 013 integration.
- **`src/state_core/auth/oauth_common/loopback.py`** — verified reusable as-is (Phase 015 cardinal rule: NO provider-specific behavior in this module).
- **`src/state_core/auth/errors.py`** — `AuthLoginError` / `AuthRefreshError` re-imported.
- **`src/state_core/auth/providers/google_gemini.py`** — direct structural template; planner copies + adapts.
- **`src/state_core/auth/base.py`** — `OAuthCredential` shape, `AuthMethod` Protocol, `provider_id` naming convention.
- **`src/state_core/auth/refresh.py`** — `is_expired_buffered` import path, `refresh_credential` invariants.
- **`.planning/research/STACK.md`** — pinned dep floors.
- **`.planning/research/PITFALLS.md`** — P0-7, P1-3, P2-2, P2-3 owners + reasoning.
- **`.state-inputs/gsd2-auth-analysis.md`** — Antigravity flow positioning + plaintext client_secret rationale.
- **Google OAuth 2.0 scopes catalog** — <https://developers.google.com/identity/protocols/oauth2/scopes>

### Secondary (MEDIUM-HIGH confidence — cross-verified across 3+ independent sources)

- **NoeFabris/opencode-antigravity-auth** — <https://github.com/NoeFabris/opencode-antigravity-auth> — token.ts source (refresh body shape + rotation rule), README (loopback flow, port discovery), constants references in search results. Repository archived 2026-03-30.
- **shekohex/opencode-google-antigravity-auth** — <https://github.com/shekohex/opencode-google-antigravity-auth> — alternative implementation cross-check.
- **PicoClaw Antigravity provider docs** — <https://docs.picoclaw.io/docs/providers/antigravity/> — full constants block including all 5 scopes + 3 outbound headers + endpoints.
- **taoalpha Antigravity quota-skill gist** — <https://gist.github.com/taoalpha/22773d2132519e55a4c7427fd3e96d8e> — quota endpoint + headers (User-Agent literal, refresh body shape, client_id + client_secret cross-check).
- **Antigravity API spec doc** — <https://github.com/NoeFabris/opencode-antigravity-auth/blob/main/docs/ANTIGRAVITY_API_SPEC.md> — endpoint + headers (Authorization, User-Agent: antigravity/1.15.8 desktop variant, X-Goog-Api-Client, Client-Metadata).

### Tertiary (LOW confidence — informational / context only)

- **Google AI Developers Forum — OAuth Authentication Failure in Antigravity** — <https://discuss.ai.google.dev/t/oauth-authentication-failure-in-antigravity/118420> — context on user-side OAuth failures.
- **Bug Report: Google Antigravity API Permission Denied** — <https://github.com/NoeFabris/opencode-antigravity-auth/issues/191> — January 2026 mass-revocation event documentation.

## Metadata

**Confidence breakdown:**

- Standard stack — HIGH (no new deps; all Phase 015 modules reused unchanged)
- Architecture — HIGH (Phase 015 is the structural template; deltas surgical and verified)
- Pitfalls — HIGH (P1-3, P2-2, P2-3 carried forward; new pitfalls 4–6 verified via 3-source cross-check; pitfalls 11–12 informational/forward-looking)
- Identity constants (`_CLIENT_ID`, `_CLIENT_SECRET`) — HIGH (cross-verified across NoeFabris source, PicoClaw docs, taoalpha gist)
- Scopes — HIGH (cross-verified across PicoClaw docs, taoalpha gist, NoeFabris references; published `cclog` + `experimentsandconfigs` not in Google's public catalog → P2-3 stewardship)
- Endpoints (`_AUTHORIZE_URL`, `_TOKEN_URL`) — HIGH (Google standard endpoints + sources confirm)
- Redirect URI literal `localhost` and FIXED port 51121 — HIGH (verified across 3 sources; explicit pre-registration constraint)
- Outbound HTTP headers (`User-Agent`, `X-Goog-Api-Client`, `Client-Metadata`) — HIGH-MEDIUM (cross-verified; the literal-vs-versioned User-Agent split documented)
- ToS / IAM revocation pattern — HIGH (publicly documented via NoeFabris archive + Google AI forums; informational only)

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30-day window for stable Google OAuth + Antigravity endpoints; sooner if Google flips another mass-revocation kill switch — monitor `IAM_PERMISSION_DENIED` cluster alerts in v3 provider routing)
