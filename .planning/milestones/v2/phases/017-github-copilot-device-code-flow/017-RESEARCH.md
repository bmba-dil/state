# Phase 017: GitHub Copilot device-code flow — Research

**Researched:** 2026-04-30
**Domain:** GitHub OAuth 2.0 Device Authorization Grant (RFC 8628) + two-tier token architecture (long-lived `gho_*` GitHub OAuth token → short-lived `tid_*` Copilot API session token, ~30 min TTL) + Copilot-specific stealth-style headers (User-Agent / Editor-Version / Editor-Plugin-Version). Fourth concrete `AuthMethod` implementation — the FIRST without a loopback HTTP listener.
**Confidence:** HIGH (cross-verified across opencode source, GitHub OAuth docs, RFC 8628, litellm docs, copilot-to-api / B00TK1D copilot-api Python references, hermes-agent issue #16551 client-ID compatibility analysis)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

None — `017-CONTEXT.md` was auto-generated with `workflow.skip_discuss: true`. There are no user-locked decisions for this phase. All implementation choices are at Claude's discretion (constrained by the hard project-level rules below).

### Claude's Discretion

All implementation choices are at Claude's discretion. The discretion bounds are:

- Project-level rules from `CLAUDE.md` (Python 3.12+, mode isolation, deterministic event payloads, chmod-0600 vault, OAuth NEVER through litellm, `.state/events.sqlite` first).
- Already-pinned deps from `STACK.md` (`httpx>=0.28.1`, `pydantic>=2.13.2`, `filelock>=3.20.3`, `cryptography>=43.0`, `structlog>=25.1`, `pytest>=8.4.0`, `pytest-asyncio>=1.3.0`, `pytest-httpx>=0.35`, `orjson>=3.11.8`).
- Phase 011/012/013 contracts: `AuthMethod` Protocol, `OAuthCredential` (frozen, `extra="forbid"`, `extras: dict[str, Any]`), `AuthVault` array shape, `refresh_credential` filelock-guarded with double-check + 10s acquisition timeout + 15s `wait_for` cap on `method.refresh`, `is_expired_buffered` 5-min buffer.
- `state_core.auth.errors` (Phase 015) — `AuthError` / `AuthLoginError` / `AuthRefreshError` reused; provider does NOT add a new exception class unless a Copilot-specific signal needs it (recommendation below: NO new class for v2; `AuthRefreshError("Copilot grant revoked")` is sufficient).
- `oauth_common/pkce.py` — **NOT used.** Device-code flow has no PKCE.
- `oauth_common/loopback.py` — **NOT used.** Device-code flow has no HTTP listener.
- Phase 014/015/016 patterns to **mirror byte-for-byte where applicable**: per-call `httpx.AsyncClient` (no module-level singleton), no own filelock acquisition, no retry layer at provider level, exception hierarchy via `state_core.auth.errors`, plaintext public client_id with rationale comment, argparse `_main` with `login` + `refresh` subcommands.
- Pitfalls inherited: P1-3 (plaintext client_id rationale), P0-7 / AUTH-09 (5-min buffer in `is_expired`, applied to the SHORT-lived `tid_*` token, NOT the long-lived OAuth token), P1-5 (device-code timeout UX), P1-6 (Copilot grant revocation — 200 with null token).
- Per the roadmap label, `Depends on: 013` (filelock refresh path). All other Phase 014/015/016 modules are reusable but `oauth_common/` modules are NOT applicable here.

### Deferred Ideas (OUT OF SCOPE)

None explicitly deferred via CONTEXT — discuss was skipped. Implicit deferrals (consistent with Phase 014/015/016 scope split) and items the planner MUST NOT pull into this phase:

- Polished `state auth login github.copilot` Typer CLI (browser-open, `--no-browser`, structured error rendering) — Phase 022.
- 429 / quota-exhaustion parsing + multi-cred handoff between Copilot accounts — Phase 019 (round-robin) + v3 provider routing.
- Structlog `gho_*` / `ghr_*` / `tid_*` token redactor — Phase 020.
- Inference-call routing to `api.githubcopilot.com/chat/completions` (or `/v1/messages` for Anthropic-shaped models) — v3 provider routing. **This phase only owns auth.**
- Live model-catalog fetch from `api.githubcopilot.com/models` — v3 provider routing. (The OpenCode plugin does this in `models.ts`; we do not.)
- GitHub Enterprise (GHE) `enterpriseUrl` prompt + `copilot-api.{enterprise}.com` base-URL substitution — recommendation: **scaffold the field shape** in `extras["enterprise_url"]` so v3 routing can use it; the login flow accepts `enterprise_url` as an optional kwarg but defaults to `github.com`. The interactive enterprise prompt is Phase 022's concern.
- First-run import from opencode's `auth.json` (`provider_id="github-copilot"` with `enterpriseUrl` field) — Phase 021. We MUST keep `extras` shape compatible.
- Browser auto-open (`webbrowser.open(verification_uri)` or `verification_uri_complete`) — Phase 022. 017 prints the URL + user_code for SSH-friendly fallback.
- Captured-header golden-file regression test (AUTH-13) — surfaces in Phase 022. We provide the `http_headers` byte-stable surface here; Phase 022 binds the snapshot.
- Multi-account / packed-refresh-string encoding — `OAuthCredential.extras` already supports separate keys (`enterprise_url`, `tid_token`, `tid_expires`). Phase 019 round-robin operates on the array.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-04 | GitHub Copilot device-code flow (polling, grant-revocation handling) | Sections **Standard Stack** (no new deps; `oauth_common/` NOT reused), **Architecture Patterns** §1–§9 (RFC 8628 device authorization request, polling state-machine with `authorization_pending`/`slow_down`/`expired_token`/`access_denied`/success branches, 15-min hard timeout via `time.monotonic()` deadline, two-tier token storage — `OAuthCredential.access` = `tid_*` session token, `OAuthCredential.refresh` = long-lived `gho_*` OAuth token, `OAuthCredential.expires` = `tid_*` expiry epoch from `expires_at`, `extras["oauth_token"]` mirror for clarity, mint-session-from-OAuth via `api.github.com/copilot_internal/v2/token`, Copilot-stealth headers byte-for-byte from copilot.vim reference, grant-revocation detection — 200 with null/missing access_token (login) or `not_found`/`copilot_disabled` 401/403 (refresh), pydantic validation of all three response shapes), **Don't Hand-Roll** table (RFC 8628 polling clock arithmetic, JSON parsing, exception precedence), **Common Pitfalls** §1–§14 (P1-3 client_id plaintext + obfuscation forbidden, P1-5 device-code 15-min countdown UX, P1-6 200-with-null-body grant revocation, P0-7 buffer applies to `tid_*` not `gho_*`, RFC 8628 slow_down increment-by-5, server-suggested interval override, deterministic clock via `time.monotonic()`, SAML/SSO org failure path, polling loop CancelledError handling, `Iv1.b507a08c87ecfe98` vs `Ov23li...` divergence — must use legacy OAuth App ID for `copilot_internal` access, two-tier expiry independence, GitHub Enterprise base-URL substitution, Editor-Version drift, no PKCE in device flow), **Code Examples** §1–§8 (constants block with discovery sources, `_request_device_code` POST body, `_poll_for_token` async state machine, `_mint_session_token` POST body + headers, `_to_credential` two-tier construction, `http_headers` Bearer + Copilot-stealth, token-shape sniffer, `_main` argparse). |

</phase_requirements>

## Summary

Phase 017 is the **fourth concrete `AuthMethod` implementation** (Anthropic Phase 014 paste-flow stealth, Gemini Phase 015 loopback, Antigravity Phase 016 fixed-port loopback, **Copilot 017 device-code**) and the **first without an HTTP listener**. The flow shape is fundamentally different from 015/016: there is no PKCE, no loopback redirect, no browser callback. Instead, RFC 8628 (OAuth 2.0 Device Authorization Grant) defines a polling protocol where the client (a) POSTs to a device-code endpoint, (b) prints `user_code` + `verification_uri` for the human, (c) polls the token endpoint at a server-suggested interval until the user authorizes the request out-of-band. Because there is nothing to listen for, we do not import `oauth_common/loopback.py` or `oauth_common/pkce.py`.

The non-obvious complexity is the **two-tier token architecture**:

1. **Long-lived OAuth token** (`gho_*`, sometimes `ghu_*` for user-to-server) — issued by `https://github.com/login/oauth/access_token` after device-code authorization completes. This token does NOT expire on the legacy OAuth App `Iv1.b507a08c87ecfe98` (no refresh_token rotation; the OAuth grant itself is what gets revoked). It is what gets persisted as the refresh-tier credential.
2. **Short-lived Copilot session token** (`tid_*`) — minted from the OAuth token via `POST https://api.github.com/copilot_internal/v2/token` with the `gho_*` token as Bearer. ~30-minute TTL, signaled by the `expires_at` Unix-timestamp field in the response. THIS is the token that gets sent to inference endpoints (`api.githubcopilot.com/chat/completions` etc.).

We map the two tiers onto `OAuthCredential` as follows: **`refresh` field stores the long-lived `gho_*` OAuth token** (it is not a literal refresh token in the OAuth sense, but it plays the same role — it is what we use to re-mint short-lived access tokens), **`access` field stores the short-lived `tid_*` session token**, **`expires` stores the `tid_*` expiry epoch** (from the response's `expires_at`), and **`extras["oauth_token"]`** mirrors `refresh` for read-clarity (provider-routing code reads `extras["oauth_token"]`, never `refresh`, so renames are easier later). The `refresh()` method does NOT call GitHub's OAuth endpoint at all — it calls `copilot_internal/v2/token` with the stored `gho_*` and re-mints a `tid_*`. The 5-minute buffer (AUTH-09) applies to the `tid_*` expiry.

Three other surface details require care:

- **client_id selection.** Two divergent client IDs circulate in the wild: `Iv1.b507a08c87ecfe98` (legacy OAuth App, used by copilot.vim, copilot.el, B00TK1D/copilot-api, litellm) and `Ov23li8tweQw6odWQebz` (opencode's GitHub App ID). Tokens minted from `Ov23li...` are NOT authorized for `copilot_internal/v2/token` (verified via hermes-agent issue #16551). **We MUST use `Iv1.b507a08c87ecfe98`** to support the two-tier mint; this also gives us the full live model catalog. P1-3 plaintext rule applies.
- **Polling state machine.** RFC 8628 §3.5 specifies four error codes the token endpoint may return at 200/400 status: `authorization_pending` (keep polling at current interval), `slow_down` (increase interval by 5 seconds, MUST persist for all subsequent requests), `expired_token` (terminal — start over), `access_denied` (terminal — user denied). GitHub additionally may return success at any poll, signaled by `access_token` field present. We add a 15-minute hard wall-clock deadline (matches `expires_in` from the device-code response) using `time.monotonic()` to avoid wall-clock drift / NTP jumps poisoning the timer. The `OAUTH_POLLING_SAFETY_MARGIN_MS = 3000` constant from opencode (3 seconds added to every sleep) is adopted to defend against clock skew between client and GitHub server.
- **Copilot-stealth headers.** The Copilot inference and `copilot_internal/v2/token` endpoints pattern-match on `User-Agent`, `Editor-Version`, `Editor-Plugin-Version` to allow specific clients. The canonical values across the community Copilot-CLI ecosystem (B00TK1D, Alorse/copilot-to-api, copilot.vim source) are `User-Agent: GithubCopilot/<editor-version>`, `Editor-Version: Neovim/0.6.1` (or VS Code analogue), `Editor-Plugin-Version: copilot.vim/1.16.0`. We hard-code these per-call inside `http_headers` and `_mint_session_token`, mirroring Phase 014's stealth-header discipline (this is why Anthropic stealth and Copilot stealth appear in the same milestone — both are header-signature-bound flows).

**Primary recommendation:** Land `providers/github_copilot.py` (~340 LOC — slightly larger than Antigravity's 310 because the two-tier mint adds one helper + one Pydantic model). Define a small `_CopilotPollingState` dataclass for the polling loop's interval / deadline / safety-margin tracking. Mirror Phase 015/016 module structure section-for-section so the diff is auditable. **No new modules under `oauth_common/`** — device-code is sui generis to this phase; there is no second consumer to justify extraction. Reuse `state_core.auth.errors` unchanged.

## Standard Stack

### Core (already pinned in `pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.12+ | `asyncio.sleep`, `time.monotonic` (polling deadline — NOT `time.time` for deadline math; see Pitfall 7), `time.time` (wire-shape `expires` epoch), `urllib.parse` (Phase 015/016 parity for any URL building), `argparse` (`_main` subcommands), `sys.platform` (NOT used here — no Client-Metadata; only Antigravity needs it) | Polling loop, monotonic deadline, JSON parse via orjson, no extra deps. |
| `httpx` | `>=0.28.1` | Per-call `AsyncClient` for device-code POST, polling POST, session-token mint POST | Same client choice as 014/015/016. |
| `pydantic` | `>=2.13.2` | Three response models — `DeviceCodeResponse`, `DeviceTokenResponse`, `CopilotSessionResponse` — all with `extra="ignore"` (forward-compat) | Mirrors Phase 015/016. |
| `orjson` | `>=3.11.8` | Already a project dep; `httpx.Response.json()` is used for the polling loop's typed-key reads but we ALSO do `model_validate_json(resp.content)` for Pydantic shape enforcement | Faster JSON; same as Phase 015/016. |
| `filelock` | `>=3.20.3` | Imported transitively via Phase 013's `refresh_credential` — provider does NOT touch it directly | CVE-2026-22701 floor. |
| `structlog` | `>=25.1` | Login/poll/refresh observability. Phase 020 attaches the `gho_*` / `ghr_*` / `tid_*` redactor. | Project-wide logging substrate. |
| `state_core.auth.errors` | (Phase 015) | `AuthLoginError`, `AuthRefreshError` re-imported from shared module | Promoted in Phase 015; reused here. |

### Supporting (test only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8.4.0` | Test runner | Always. |
| `pytest-asyncio` | `>=1.3.0` | Async test support | Every `login()` / `refresh()` / poll-loop test. |
| `pytest-httpx` | `>=0.35` | `httpx_mock.add_response(match_url, match_headers, match_json, match_content)` for all three endpoints (device-code, polling token, copilot_internal mint) | Token-exchange + polling-state-machine tests. |
| `pytest-mock` | `>=3.14` | `monkeypatch.setattr` for `asyncio.sleep` (compress 5-second waits in tests), `time.monotonic` (deterministic deadline), `time.time` (deterministic `expires` epoch) | Polling loop tests must run in milliseconds, not minutes. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Iv1.b507a08c87ecfe98` (legacy OAuth App) | `Ov23li8tweQw6odWQebz` (opencode's GitHub App) | **Tokens from `Ov23li...` are NOT authorized for `copilot_internal/v2/token`** (verified via hermes-agent issue #16551 + cherry-studio issue #11905 + opencode issue #20759). Using `Ov23li...` would force us to skip the `tid_*` mint and Bearer the `gho_*` directly to inference — works for some endpoints (api.githubcopilot.com/models, /chat/completions) but: (a) breaks Anthropic-shape `/v1/messages` proxying that gpt-5/claude-on-copilot routes through, (b) changes the model allowlist (different per-client-ID server-side allowlist), (c) does not match copilot.vim / copilot.el / litellm (we lose ecosystem support). **Use `Iv1.b507a08c87ecfe98`.** |
| Hand-roll polling loop with `asyncio.sleep` + state machine | Use `authlib.integrations.httpx_client.AsyncOAuth2Client` device-code flow | `authlib` is not in our pin set; pulling it for one provider violates STACK.md "no LangChain-class abstraction layer." Hand-rolled loop is ~40 LOC and visible in tests. |
| `time.monotonic()` deadline | `time.time()` deadline | NTP jumps + DST + container clock-resets can poison `time.time()` mid-15-minute window. `time.monotonic()` is wall-clock-independent (Pitfall 7 owns this). |
| Two-tier token mapped onto `OAuthCredential` (refresh = `gho_*`, access = `tid_*`) | Add a new Credential variant (e.g., `CopilotCredential`) | YAGNI — `OAuthCredential.extras: dict[str, Any]` is the right escape hatch. Adding a new variant requires touching the `Credential` discriminated union in `base.py`, every `CredentialAdapter` consumer, every store round-trip test. The semantic mismatch ("`refresh` is a long-lived OAuth token, not a refresh_token") is documented in the provider's docstring + `extras["oauth_token"]` mirror. **No new variant.** |
| Mint `tid_*` lazily in `http_headers` (or `extras["mint_session"]` hook) | Mint eagerly in `login()` and `refresh()` so `cred.access` is always a valid `tid_*` | Lazy minting requires a network call inside the sync `http_headers` method (impossible) OR a wrapper around the inference call (v3 provider routing's concern, but couples the auth contract to v3). **Eager minting** is consistent with Phase 014/015/016: `login()` and `refresh()` are the I/O entry points; `http_headers` is pure. |
| `User-Agent: GithubCopilot/1.155.0` (copilot.vim canonical) | `User-Agent: opencode/{InstallationVersion}` (opencode's pattern) | OpenCode uses its own UA and trades: it works for some endpoints but the documented working values (B00TK1D + copilot-to-api + Alorse community refs) all use `GithubCopilot/<editor-version>`. We adopt the canonical Copilot-CLI ecosystem UA: `GithubCopilot/1.155.0` (matches Editor-Plugin-Version) with `Editor-Version: Neovim/0.6.1` and `Editor-Plugin-Version: copilot.vim/1.16.0`. Phase 022 captured-header regression locks this; future drift = Pitfall 12. |
| Per-call `httpx.AsyncClient` | Module-level singleton | Phase 014/015/016 pattern. |
| New exception class `CopilotGrantRevoked(AuthRefreshError)` | Reuse `AuthRefreshError("Copilot grant revoked: …")` | YAGNI for v2. The grant-revocation signal (200-with-null-token on login, 401/403 with `not_found` body on refresh) maps cleanly to existing exceptions. Phase 022 CLI catches `AuthRefreshError`; the message string carries the actionable detail. **Add a class only if Phase 022 needs to discriminate.** |
| Validate device-code response with Pydantic | Use raw dict access | Pydantic validation catches GitHub's known shape drifts (e.g., `interval` returned as string in some enterprise responses, `expires_in` missing). `extra="ignore"` keeps us forward-compat. |

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
│   ├── pkce.py                              # (existing — Phase 014; NOT used by 017)
│   └── loopback.py                          # (existing — Phase 015; NOT used by 017)
└── providers/
    ├── __init__.py                          # (existing — empty)
    ├── anthropic.py                         # (existing — Phase 014)
    ├── google_gemini.py                     # (existing — Phase 015)
    ├── antigravity.py                       # (existing — Phase 016)
    └── github_copilot.py                    # NEW — ~340 LOC
                                              #   includes `if __name__ == "__main__": ...`
                                              #   so `python -m state_core.auth.providers.github_copilot login` works

tests/auth/
├── (existing fixtures in conftest.py)
├── oauth_common/
│   └── (no new tests — 017 doesn't use these)
└── providers/
    ├── test_anthropic.py                    # (existing)
    ├── test_google_gemini.py                # (existing)
    ├── test_antigravity.py                  # (existing — pending Phase 016 land)
    └── test_github_copilot.py               # NEW — ~22 tests
```

**provider_id naming:** `"github.copilot"` — kebab-case-with-dot-namespace, matching Phase 015's `"google.gemini_cli"` / Phase 016's `"google.antigravity"` convention. The dot is a namespace separator within `AuthVault.providers`. Note opencode uses `"github-copilot"` (single-token, hyphen). We diverge **deliberately** to keep the dotted-namespace pattern consistent across all four providers — Phase 021 (first-run import) is responsible for translating opencode's `"github-copilot"` → our `"github.copilot"` at import time.

### Pattern 1: RFC 8628 Device Authorization Request (no PKCE, no listener)

**What:** A single POST to `https://github.com/login/device/code` with `client_id` + `scope=read:user` returns a `device_code` + `user_code` + `verification_uri` + `interval` (polling pace, seconds) + `expires_in` (15 minutes — the wall-clock deadline before `expired_token` kicks in).

**When to use:** The first leg of every device-code login. NEVER reuse Phase 015/016's `_build_authorize_url` — that's loopback-flow. There is no authorize URL the user clicks; there is a `verification_uri` the user copy-pastes (or `verification_uri_complete` which embeds the user_code as a query param for one-click — GitHub's device-code response includes both).

**Why:** Designed for input-constrained devices (TV apps, CLIs, IoT). Eliminates the loopback callback dependency; there is no listening port.

**Skeleton:**

```python
# src/state_core/auth/providers/github_copilot.py — _request_device_code
async def _request_device_code(
    *,
    base_domain: str = "github.com",
) -> DeviceCodeResponse:
    """POST {base}/login/device/code with client_id + scope=read:user.

    base_domain is "github.com" for github.com or e.g. "company.ghe.com" for
    GitHub Enterprise (Phase 022 prompts; we accept it as a kwarg here).

    Raises AuthLoginError on transport / 4xx / shape errors.
    """
    url = f"https://{base_domain}/login/device/code"
    body = {"client_id": _CLIENT_ID, "scope": _SCOPE}
    headers = {
        "accept":       "application/json",
        "content-type": "application/json",
        "user-agent":   _USER_AGENT,         # Copilot-stealth — see Pattern 7
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
        ) as client:
            resp = await client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise AuthLoginError(f"device-code request transport: {exc}") from exc

    if resp.status_code >= 400:
        raise AuthLoginError(
            f"device-code request http {resp.status_code}: {resp.text[:500]!r}"
        )
    try:
        return DeviceCodeResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        raise AuthLoginError(f"device-code response shape: {exc}") from exc
```

**Anti-pattern:** Sending `Content-Type: application/x-www-form-urlencoded`. GitHub's docs accept both, but the community-validated path uses JSON; sticking with JSON keeps the body shape consistent with the polling and mint endpoints.

### Pattern 2: Polling State Machine (RFC 8628 §3.5)

**What:** Repeatedly POST to `https://github.com/login/oauth/access_token` with the `device_code` until the user completes (or denies, or the device_code expires). Five terminal/non-terminal outcomes:

| Response | Status | Body shape | Action |
|----------|--------|------------|--------|
| Success | 200 | `{"access_token": "gho_…", "token_type": "bearer", "scope": "read:user"}` | Return the token. |
| Pending | 200 (or 400 — GitHub returns 200 with `error` field) | `{"error": "authorization_pending"}` | Sleep `interval + safety_margin`; continue. |
| Slow down | 200 | `{"error": "slow_down", "interval": <new>?}` | Increase interval by 5s (RFC 8628 §3.5); use server-suggested `interval` if present; sleep + continue. |
| Expired | 200 | `{"error": "expired_token"}` | Terminal — `AuthLoginError("Device code expired; please re-run login")`. |
| Denied | 200 | `{"error": "access_denied"}` | Terminal — `AuthLoginError("User denied authorization")`. |
| Other error | 400/500 | various | Terminal — `AuthLoginError("Polling http {status}: {body}")`. |

Plus a 15-minute hard wall-clock deadline, computed via `time.monotonic()` (NOT `time.time()`):

```python
# Skeleton — _poll_for_token

@dataclass
class _PollingState:
    interval: float                # current poll cadence in seconds
    deadline: float                # time.monotonic() + expires_in
    safety_margin: float = 3.0     # OAUTH_POLLING_SAFETY_MARGIN_MS = 3000

    def remaining(self, now_mono: float) -> float:
        return max(0.0, self.deadline - now_mono)


async def _poll_for_token(
    device_code: str,
    initial_interval: int,
    expires_in: int,
    *,
    base_domain: str = "github.com",
    monotonic: Callable[[], float] = time.monotonic,    # injected for tests
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> str:
    """Poll the token endpoint until success or terminal error.

    Returns the long-lived OAuth token (gho_* or ghu_*). Raises AuthLoginError
    on terminal failure or 15-min timeout.

    Determinism: monotonic + sleep are injectable. The function NEVER reads
    time.time() for deadline math (Pitfall 7).
    """
    url = f"https://{base_domain}/login/oauth/access_token"
    body = {
        "client_id":   _CLIENT_ID,
        "device_code": device_code,
        "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
    }
    headers = {
        "accept":       "application/json",
        "content-type": "application/json",
        "user-agent":   _USER_AGENT,
    }
    state = _PollingState(
        interval=float(initial_interval),
        deadline=monotonic() + float(expires_in),
    )

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=False,
    ) as client:
        while True:
            # Wall-clock-independent deadline check.
            if state.remaining(monotonic()) <= 0.0:
                raise AuthLoginError(
                    f"Device-code authorization expired after {expires_in}s; "
                    f"please re-run login."
                )

            await sleep(state.interval + state.safety_margin)

            try:
                resp = await client.post(url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                raise AuthLoginError(f"polling transport: {exc}") from exc

            # GitHub returns 200 even for known error codes; only 5xx and
            # genuinely-unexpected 4xx raise.
            if resp.status_code >= 500 or (
                resp.status_code >= 400 and resp.status_code != 400
            ):
                raise AuthLoginError(
                    f"polling http {resp.status_code}: {resp.text[:500]!r}"
                )

            try:
                parsed = DeviceTokenResponse.model_validate_json(resp.content)
            except ValidationError as exc:
                raise AuthLoginError(f"polling response shape: {exc}") from exc

            if parsed.access_token:
                return parsed.access_token

            err = parsed.error
            if err == "authorization_pending":
                continue
            if err == "slow_down":
                # RFC 8628 §3.5: MUST increase by 5s, persist increase.
                # If server provided new interval, prefer it.
                if parsed.interval and parsed.interval > 0:
                    state.interval = float(parsed.interval)
                else:
                    state.interval += 5.0
                continue
            if err == "expired_token":
                raise AuthLoginError(
                    "Device code expired; please re-run login."
                )
            if err == "access_denied":
                raise AuthLoginError("User denied authorization.")

            # Unknown error — terminal.
            raise AuthLoginError(
                f"polling unexpected error: {err!r} body={resp.text[:500]!r}"
            )
```

**Anti-pattern:** Treating `slow_down` as a one-shot interval bump. The RFC requires the new interval to **persist for all subsequent requests**. We track this via mutating `state.interval`.

**Anti-pattern:** Using `time.time()` for the deadline. NTP / container time-resets / DST will skew. `time.monotonic()` is monotonically non-decreasing per process — exactly what we need.

**Anti-pattern:** Sleeping a full `interval` on the first iteration and ALSO sleeping after the device-code request. We sleep BEFORE each poll — the user needs at least `interval` seconds to walk to a browser anyway. (Opencode's reference does this; we mirror.)

### Pattern 3: Two-Tier Token Mint (`copilot_internal/v2/token`)

**What:** After the polling loop returns the long-lived OAuth token, we POST to `https://api.github.com/copilot_internal/v2/token` with the OAuth token as `Authorization: Bearer <gho_…>` and a triple of Copilot-stealth headers. The response contains a short-lived `tid_*` session token + `expires_at` (Unix timestamp) + `refresh_in` (seconds until recommended refresh).

**Why this is required:** The `Iv1.b507a08c87ecfe98` OAuth App grants `read:user` scope only. The `gho_*` token cannot directly call `api.githubcopilot.com/chat/completions` — that endpoint expects a `tid_*` session token. The session token is what carries the user's Copilot-plan entitlements. Server-side, GitHub binds the user's account → Copilot subscription tier → SKU-specific rate limits to the `tid_*` token's lifetime.

**Skeleton:**

```python
async def _mint_session_token(
    oauth_token: str,
    *,
    base_api: str = "https://api.github.com",
) -> CopilotSessionResponse:
    """POST {base_api}/copilot_internal/v2/token with Bearer <oauth_token>.

    For GitHub.com: base_api = "https://api.github.com".
    For GitHub Enterprise: base_api = f"https://copilot-api.{enterprise_domain}".
    (v3 provider routing handles the latter; here we accept it as a kwarg.)

    Returns CopilotSessionResponse with token / expires_at / refresh_in.
    Raises AuthRefreshError on transport / 4xx / 5xx / shape errors.

    Special case (P1-6): a 200 response WITHOUT a `token` field signals
    grant revocation (user revoked Copilot access in GitHub settings).
    Pydantic catches this — `token: str` is required, ValidationError fires.
    We re-raise as AuthRefreshError("Copilot grant revoked …").
    """
    url = f"{base_api}/copilot_internal/v2/token"
    headers = {
        "accept":                 "application/json",
        "authorization":          f"Bearer {oauth_token}",
        "user-agent":             _USER_AGENT,
        "editor-version":         _EDITOR_VERSION,
        "editor-plugin-version":  _EDITOR_PLUGIN_VERSION,
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
        ) as client:
            resp = await client.post(url, headers=headers)
    except httpx.HTTPError as exc:
        raise AuthRefreshError(f"copilot session-token transport: {exc}") from exc

    # 401/403: grant revoked, oauth token invalid, or Copilot subscription
    # lapsed. All terminal — caller re-runs login.
    if resp.status_code in (401, 403):
        raise AuthRefreshError(
            f"Copilot grant rejected (http {resp.status_code}): "
            f"{resp.text[:500]!r}"
        )
    if resp.status_code >= 400:
        raise AuthRefreshError(
            f"copilot session-token http {resp.status_code}: "
            f"{resp.text[:500]!r}"
        )

    try:
        return CopilotSessionResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        # P1-6: 200 with null/missing token → ValidationError because
        # `token` is required. Re-raise with a grant-revoked message.
        raise AuthRefreshError(
            f"Copilot session-token response shape (likely grant revoked): {exc}"
        ) from exc
```

**Anti-pattern:** Treating the `gho_*` token as the inference Bearer. It works for `api.githubcopilot.com/models` (model catalog — the opencode reference uses it this way) but does NOT work for `chat/completions` or `/v1/messages`. The two-tier mint is mandatory for inference.

**Anti-pattern:** Caching the `tid_*` token across credential lifetimes. It expires in ~30 minutes; persisting it on disk longer than that wastes vault space and risks stale-token 401s. The `expires` field on `OAuthCredential` enforces re-mint via Phase 013's filelock-guarded refresh path.

### Pattern 4: Mapping Two-Tier Tokens onto `OAuthCredential`

**What:** `OAuthCredential` has three secret-or-time-sensitive fields: `access`, `refresh`, `expires`. We map the two-tier architecture as follows:

| OAuthCredential field | Phase 017 semantic | Source | Lifecycle |
|----------------------|--------------------|--------|-----------|
| `access` | Short-lived `tid_*` Copilot session token | `_mint_session_token().token` | ~30 min (re-minted by `refresh()` whenever `is_expired` returns True) |
| `refresh` | Long-lived `gho_*` GitHub OAuth token | `_poll_for_token()` final return | Indefinite (no rotation on legacy OAuth App; revoked only when user revokes Copilot access in GitHub settings) |
| `expires` | `tid_*` expiry epoch | `CopilotSessionResponse.expires_at` (already a Unix timestamp, no math needed) | Updated on every `refresh()` |
| `account_id` | GitHub username (login) | Optional — fetched once via `GET /user` with the `gho_*` token; defer to Phase 022 for polish | Set at login() time |
| `extras["oauth_token"]` | Mirror of `refresh` for read-clarity | Same as `refresh` | Same |
| `extras["enterprise_url"]` | GHE enterprise domain (None for github.com) | Optional kwarg to `login()` | Set at login() time |
| `extras["editor_version"]` | Captured Editor-Version header at login (for header-drift forensics) | Constant `_EDITOR_VERSION` snapshot | Set at login() time |
| `extras["sku"]` | Copilot SKU from session response (free / individual / business / enterprise) | `CopilotSessionResponse.sku` if present | Updated on every `refresh()` |

The semantic mismatch — `refresh` is not a literal RFC 6749 refresh_token — is documented prominently in the provider's module docstring. The `extras["oauth_token"]` mirror exists so future code reads `cred.extras["oauth_token"]` (semantically clear) instead of `cred.refresh` (misleading). Both point to the same string.

**Why not a new `Credential` variant?**
1. YAGNI — `extras` solves the read-clarity problem.
2. Adding `CopilotCredential` cascades to `Credential` discriminated union, `CredentialAdapter`, every store round-trip test, every Phase 019 round-robin path. Cost outweighs benefit.
3. Phase 014's Anthropic also has a "long-lived OAuth token + refresh_token" two-token pattern; that fit `OAuthCredential` cleanly. The "refresh field stores a non-rotating credential" semantic is already precedent.

### Pattern 5: `login()` — Orchestrate Device → Poll → Mint → Persist

```python
async def login(
    self,
    *,
    enterprise_url: str | None = None,
) -> OAuthCredential:
    """Run the device-code login flow + immediately mint a Copilot session token.

    1. POST device-code endpoint → DeviceCodeResponse.
    2. Print user_code + verification_uri (SSH-friendly fallback;
       Phase 022 adds webbrowser.open + verification_uri_complete).
    3. Poll until success / denial / expiry — _poll_for_token.
    4. Mint tid_* session token — _mint_session_token.
    5. Construct OAuthCredential with tid_* in access, gho_* in refresh,
       expires from session-response expires_at.
    """
    base_domain = (
        normalize_domain(enterprise_url) if enterprise_url else "github.com"
    )
    base_api = (
        f"https://copilot-api.{normalize_domain(enterprise_url)}"
        if enterprise_url
        else "https://api.github.com"
    )

    device_resp = await _request_device_code(base_domain=base_domain)

    # Print outside any prompt — user_code must appear even if stdout is piped.
    # Phase 022 adds webbrowser.open(verification_uri_complete) + --no-browser.
    print(
        f"Open this URL in your browser to grant GitHub Copilot access:\n\n"
        f"  {device_resp.verification_uri}\n\n"
        f"And enter the code: {device_resp.user_code}\n\n"
        f"(Code expires in {device_resp.expires_in // 60} minutes; polling "
        f"every {device_resp.interval}s)\n"
    )

    log.info(
        "github_copilot.login.waiting_for_device",
        verification_uri=device_resp.verification_uri,
        expires_in=device_resp.expires_in,
        interval=device_resp.interval,
    )

    oauth_token = await _poll_for_token(
        device_code=device_resp.device_code,
        initial_interval=device_resp.interval,
        expires_in=device_resp.expires_in,
        base_domain=base_domain,
    )

    log.info(
        "github_copilot.login.minting_session",
    )

    session = await _mint_session_token(oauth_token, base_api=base_api)

    extras: dict[str, Any] = {
        "oauth_token":    oauth_token,
        "editor_version": _EDITOR_VERSION,
    }
    if enterprise_url:
        extras["enterprise_url"] = enterprise_url
    if session.sku:
        extras["sku"] = session.sku

    cred = OAuthCredential(
        access=session.token,
        refresh=oauth_token,
        expires=float(session.expires_at),
        provider_id="github.copilot",
        account_id=None,                # Phase 022 polishes via GET /user
        extras=extras,
    )

    log.info(
        "github_copilot.login.success",
        provider_id=cred.provider_id,
        sku=session.sku,
        expires_at=session.expires_at,
    )
    return cred
```

### Pattern 6: `refresh()` — Re-Mint `tid_*` from Stored `gho_*`

```python
async def refresh(self, cred: Credential) -> Credential:
    """Re-mint the short-lived Copilot session token from the stored OAuth token.

    Phase 013 wraps this in a 10s-budgeted async file lock + 15s asyncio.wait_for.
    This method MUST NOT acquire its own lock (refresh.py rule 9).
    Per-call AsyncClient (no singleton).

    P0-7 / AUTH-09: 5-min buffer applied at is_expired_buffered (Phase 013);
    THIS method is unconditional re-mint.

    P1-6 grant-revocation handling: _mint_session_token raises
    AuthRefreshError on 401/403 (grant revoked, OAuth token invalid).
    Caller (Phase 022 CLI) prompts user to re-login.

    Note: We do NOT call GitHub's OAuth refresh endpoint. The legacy OAuth
    App `Iv1.b507a08c87ecfe98` does not issue refresh_tokens; the gho_*
    token is the persistent grant. Re-minting tid_* is the only "refresh"
    operation Copilot supports.
    """
    if not isinstance(cred, OAuthCredential):
        raise TypeError(
            f"GitHubCopilotAuth.refresh() requires OAuthCredential, "
            f"got {type(cred).__name__} — Phase 013 should short-circuit "
            f"non-OAuth credentials before reaching this method."
        )

    base_api = (
        f"https://copilot-api.{cred.extras['enterprise_url']}"
        if cred.extras.get("enterprise_url")
        else "https://api.github.com"
    )

    log.info(
        "github_copilot.refresh.minting",
        provider_id=cred.provider_id,
        account_id=cred.account_id,
    )

    session = await _mint_session_token(cred.refresh, base_api=base_api)

    new_extras = dict(cred.extras)
    if session.sku:
        new_extras["sku"] = session.sku

    new_cred = cred.model_copy(
        update={
            "access":  session.token,
            # refresh stays the same — gho_* is long-lived; we are NOT
            # rotating it, only re-minting tid_*.
            "expires": float(session.expires_at),
            "extras":  new_extras,
        }
    )
    log.info(
        "github_copilot.refresh.success",
        provider_id=new_cred.provider_id,
        sku=session.sku,
        expires_at=session.expires_at,
    )
    return new_cred
```

**Anti-pattern:** Calling `https://github.com/login/oauth/access_token` with `grant_type=refresh_token`. The legacy OAuth App `Iv1.b507a08c87ecfe98` does not issue refresh_tokens. This will return `error=unsupported_grant_type` and waste a network call.

### Pattern 7: Copilot-Stealth Headers (constants block)

**What:** Three headers that GitHub's Copilot endpoints pattern-match against to decide whether the request is a "blessed" Copilot CLI client. These appear on `_mint_session_token` (the `copilot_internal/v2/token` POST), and on every outbound inference request that v3 provider routing makes (we surface them via `http_headers`).

```python
# ── Copilot-stealth headers ──────────────────────────────────────────────
# Captured from copilot.vim (canonical Copilot-CLI ecosystem reference)
# and verified via B00TK1D/copilot-api + Alorse/copilot-to-api +
# litellm github_copilot provider docs (all 2026-04-30 retrieval).
#
# Editor-Version drift: when GitHub upgrades Copilot's accepted client
# allowlist, these strings may need to advance. Phase 022's captured-header
# regression test (AUTH-13) is the trip-wire. P2-1 process applies (analogous
# to anthropic-beta drift): re-capture from a current copilot.vim release,
# diff, update.

_USER_AGENT: str             = "GithubCopilot/1.155.0"
_EDITOR_VERSION: str         = "Neovim/0.6.1"
_EDITOR_PLUGIN_VERSION: str  = "copilot.vim/1.16.0"
```

`http_headers` returns these three plus the Bearer:

```python
def http_headers(self, cred: Credential) -> dict[str, str]:
    """Bearer + Copilot-stealth triple for outbound inference requests.

    api.githubcopilot.com (the Copilot inference endpoint that v3 provider
    routing targets) requires:
        Authorization:          Bearer <tid_…>           # cred.access
        User-Agent:             GithubCopilot/1.155.0
        Editor-Version:         Neovim/0.6.1
        Editor-Plugin-Version:  copilot.vim/1.16.0
        Content-Type:           application/json         # caller's concern
        OpenAI-Intent:          conversation-edits       # opencode adds
                                                          this for chat/
                                                          completions; v3
                                                          should add it
                                                          per-call

    AUTH-13 (Phase 022) golden-files this dict.
    """
    if not isinstance(cred, OAuthCredential):
        return {}
    return {
        "authorization":          f"Bearer {cred.access}",
        "user-agent":              _USER_AGENT,
        "editor-version":          _EDITOR_VERSION,
        "editor-plugin-version":   _EDITOR_PLUGIN_VERSION,
    }
```

### Pattern 8: Token-Shape Sniffer (`is_token`)

**What:** GitHub OAuth tokens use distinctive prefixes (set in 2021 — see GitHub's "Authentication token format updates" changelog). Copilot session tokens use `tid_` (or sometimes `ghu_` for user tokens issued via certain paths). We accept all three.

```python
def is_token(self, value: str) -> bool:
    """First branch of token-shape sniffer.

    GitHub Copilot tokens come in three relevant shapes:
        gho_*   — OAuth App access tokens (legacy 'Iv1' clients)
        ghu_*   — GitHub App user-to-server tokens
        tid_*   — Copilot session tokens (minted via copilot_internal/v2/token)
        ghr_*   — GitHub OAuth refresh tokens (NOT issued by Iv1; only GitHub
                  Apps with expiring tokens)

    is_token returns True for any of the four prefixes; provider-level
    routing disambiguates Copilot vs GitHub-OAuth-only via cred.provider_id.

    Source: https://github.blog/changelog/2021-03-31-authentication-token-format-updates-are-generally-available/
    """
    return any(
        value.startswith(prefix)
        for prefix in ("gho_", "ghu_", "tid_", "ghr_")
    )
```

### Pattern 9: argparse `_main` (mirror Phase 015/016 — login + refresh subcommands)

```python
def _main() -> int:
    import argparse, asyncio
    parser = argparse.ArgumentParser(
        prog="python -m state_core.auth.providers.github_copilot",
        description="GitHub Copilot device-code OAuth — Phase 017 smoke surface.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    login_parser = sub.add_parser(
        "login",
        help="Run the interactive Copilot device-code login flow.",
    )
    login_parser.add_argument(
        "--enterprise-url",
        default=None,
        help="Optional GHE domain (e.g. company.ghe.com). Defaults to github.com.",
    )
    refresh_parser = sub.add_parser(
        "refresh",
        help="Re-mint the Copilot session token via Phase 013's filelock-guarded path.",
    )
    refresh_parser.add_argument(
        "provider_id",
        nargs="?",
        default="github.copilot",
        help="Provider ID (default: github.copilot).",
    )
    refresh_parser.add_argument("--idx", type=int, default=0)
    args = parser.parse_args()
    # … KeyboardInterrupt → 130, AuthLoginError/AuthRefreshError → 1, vault
    # persist via vault.providers.setdefault("github.copilot", []).append(cred).
    return 0
```

### Anti-Patterns to Avoid

- **Calling `oauth_common/loopback.py` or `oauth_common/pkce.py`:** device-code is a different flow shape; these modules are loopback-flow specific. Do not import them.
- **Using `Ov23li8tweQw6odWQebz` as the client_id:** breaks the `copilot_internal/v2/token` mint (verified via 3 sources). Use `Iv1.b507a08c87ecfe98`.
- **Wall-clock arithmetic for the 15-minute deadline:** use `time.monotonic()`. NTP / DST / container clock-resets poison `time.time()` mid-window.
- **Treating `slow_down` as one-shot:** RFC 8628 §3.5 mandates the increase persists for ALL subsequent requests.
- **Bearer-ing the `gho_*` token to inference endpoints:** works for `api.githubcopilot.com/models`, fails for `/chat/completions` and `/v1/messages`. The two-tier mint is mandatory.
- **Hand-rolling the polling loop with no clock injection:** tests need to compress 5-second waits to milliseconds. Inject `monotonic` and `sleep` callables.
- **Module-level singleton `httpx.AsyncClient`:** Phase 014/015/016 pattern.
- **`Field(repr=False)` only on `access` — forgetting `refresh`:** both `access` (`tid_*`) and `refresh` (`gho_*`) are secrets. Both need it. (The `OAuthCredential` model in `base.py` already enforces this — but the Pydantic response models in this phase ALSO need it on `access_token` and `token` fields.)
- **Routing OAuth traffic through litellm:** CLAUDE.md cardinal rule.
- **Persisting the `tid_*` session token without an `expires` value:** the 5-minute buffer logic in `is_expired_buffered` requires `cred.expires` to be the wire-shape `tid_*` expiry epoch. Setting `expires=0` (opencode's pattern, since they don't pre-mint) would force a refresh on every request.
- **Calling `https://github.com/login/oauth/access_token` with `grant_type=refresh_token`:** the legacy OAuth App doesn't issue refresh_tokens; this returns `unsupported_grant_type`.
- **Polling at the device-code response's `interval` without the safety margin:** 3-second clock-skew margin (opencode's `OAUTH_POLLING_SAFETY_MARGIN_MS`) prevents "polled too early" 400s in race conditions with GitHub's authorization-server clock.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RFC 8628 device-code state machine | Try to import `authlib.integrations.httpx_client.AsyncOAuth2Client` | Hand-rolled ~40-LOC loop with injectable `monotonic`/`sleep` | `authlib` is not in our pin set; the loop is small + must accept clock-injection for tests. |
| OAuth refresh-token rotation | Compare-and-skip / call GitHub's OAuth refresh endpoint | Re-mint `tid_*` from stored `gho_*` instead | Legacy OAuth App `Iv1.b507a08c87ecfe98` doesn't issue refresh_tokens. The `gho_*` IS the persistent credential. |
| Two-tier token storage | New `CopilotCredential` variant | `OAuthCredential` with `access=tid_*`, `refresh=gho_*`, `extras["oauth_token"]` mirror | YAGNI — `extras` solves read-clarity; no need to touch `Credential` discriminated union. |
| 15-minute deadline arithmetic | `time.time()` math | `time.monotonic()` deadline (Pitfall 7) | Wall-clock-independent; defends against NTP / DST / container clock-resets. |
| Polling-error-code → exception mapping | Custom error registry | Inline `if err == ...` ladder + `AuthLoginError` raises | The set is small (4 codes + success + transport error); a registry adds indirection without value. |
| Grant-revocation detection | `if resp.json()["access_token"] is None: ...` | Pydantic validation — `token: str` is required, ValidationError fires on null | P1-6 — Pydantic catches the shape drift idiomatically; we re-raise as `AuthRefreshError` with the grant-revoked message. |
| GitHub Enterprise URL normalization | Custom regex strip | A small `normalize_domain(url)` helper that mirrors opencode's pattern (`replace /^https?:\/\//, ''` + strip trailing slash) | Tiny utility; lives at module scope; tested with `("https://x.com", "x.com")` parametric. |
| `expires_at` epoch math | `datetime.fromisoformat(...)` | `float(session.expires_at)` — GitHub returns a Unix timestamp directly | No `datetime` import needed; consistent with Phase 015/016's `now + expires_in` (only here we get the absolute epoch directly). |
| User-Agent / Editor-Version constants | Run-time-detected from `state` package version | Hard-code the canonical Copilot-CLI ecosystem values (`GithubCopilot/1.155.0`, `Neovim/0.6.1`, `copilot.vim/1.16.0`) | These are stealth headers (analog to Anthropic's beta string). Server-side allowlist binds the strings; runtime-detection from our own version invalidates the allowlist match. P2-1 drift process applies. |
| Argparse subcommand wiring | Hand-roll `if/elif args` | Mirror Phase 015's `_main` line-for-line | Validated template; `KeyboardInterrupt → 130`, vault-persist via `setdefault("github.copilot", []).append(cred)`. |

**Key insight:** Phase 017 reuses ZERO `oauth_common/` modules but reuses EVERY other Phase 015/016 module structure (Pydantic response models, `_to_credential`-style adapter, argparse `_main`, exception hierarchy). The plan should be ~3 waves: (1) constants + Pydantic models + RED tests, (2) sync helpers + `is_token` / `is_expired` / `http_headers`, (3) async device-code request + polling loop + session mint + login/refresh + argparse.

## Common Pitfalls

(Each pitfall maps to a P0/P1/P2 in `.planning/research/PITFALLS.md` where applicable. Inherited pitfalls retain their owners; this phase's NEW owned pitfalls are flagged with **OWNED**.)

### Pitfall 1: client_id obfuscation (P1-3 — inherited)

**What goes wrong:** Engineer base64-encodes / XOR-obfuscates `_CLIENT_ID` "for security."
**Why it happens:** Intuition that "client IDs shouldn't be plaintext."
**How to avoid:** Plaintext `_CLIENT_ID = "Iv1.b507a08c87ecfe98"` with rationale comment block (mirror Phase 015/016 — AV scanners flag obfuscated literals; the security boundary is the device-flow user-consent step, not client_id confidentiality).
**Warning signs:** Snyk/Trivy flags; corporate AV blocks install.

### Pitfall 2: Wrong client_id breaks `copilot_internal/v2/token` (**NEW — OWNED**)

**What goes wrong:** Engineer adopts opencode's `Ov23li8tweQw6odWQebz` (GitHub App ID). Login + polling succeed; the `gho_*` token returns; then the `copilot_internal/v2/token` POST 401s with `not_found` or similar. The `tid_*` token never mints; inference is impossible.
**Why it happens:** GitHub maintains a per-client-ID server-side allowlist. Tokens minted from `Ov23li...` are NOT authorized for `copilot_internal`. Verified via hermes-agent issue #16551, cherry-studio issue #11905, opencode issue #20759.
**How to avoid:** Hard-code `_CLIENT_ID = "Iv1.b507a08c87ecfe98"` with comment block citing all three issues. Add a unit test asserting the literal value (regression catches accidental swap to opencode's value).
**Warning signs:** Login completes; refresh 401s on first call; user reports "auth says success but Copilot doesn't work."

### Pitfall 3: Device-code 15-minute timeout UX (P1-5 — inherited from roadmap)

**What goes wrong:** User walks away mid-auth; 15-min timeout hits; polling loop exits without clearing context. User returns and sees nothing useful.
**How to avoid:** Print explicit countdown info up-front (`Code expires in 15 minutes`); on timeout, raise `AuthLoginError("Device-code authorization expired after 900s; please re-run login.")`. Phase 022 polishes with a TUI countdown.
**Warning signs:** Users complain "I can't tell if auth worked"; stale device-code prompts in logs.

### Pitfall 4: 200-with-null-body grant revocation (P1-6 — inherited from roadmap)

**What goes wrong:** User revokes Copilot access in GitHub settings AFTER initial login. Next refresh: `copilot_internal/v2/token` returns 200 but with an empty / null `token` field. Naive code persists `null` as `cred.access` or crashes on `resp.json()["token"]` KeyError.
**How to avoid:** Pydantic `CopilotSessionResponse.token: str` (required). On `ValidationError`, re-raise as `AuthRefreshError("Copilot grant revoked or session response shape: …")`. Phase 022 CLI catches `AuthRefreshError` and prompts re-login.
**Warning signs:** Mysterious `ValidationError` on refresh; `cred.access` becomes `None` if validation isn't enforced.

### Pitfall 5: Two-tier expiry confusion — P0-7 buffer applies to `tid_*` only (P0-7 / AUTH-09 — inherited)

**What goes wrong:** Engineer thinks the 5-minute buffer applies to the `gho_*` long-lived token. Either (a) shaves 5 minutes off `gho_*`'s expiry (it has none — endless drift), or (b) skips the buffer entirely on the `tid_*` because "Copilot doesn't have refresh tokens."
**How to avoid:** `is_expired_buffered` (Phase 013) reads `cred.expires`, which we set to the `tid_*` expiry epoch. The buffer applies cleanly. Document in the provider docstring: `cred.expires` is the SHORT-lived expiry; `cred.refresh` (the `gho_*`) does not have a stored expiry because it is indefinite.
**Warning signs:** Refreshes fire too often (buffer applied to `gho_*`'s zero-expiry) or never (buffer skipped).

### Pitfall 6: RFC 8628 `slow_down` interval not persisted (**NEW — OWNED**)

**What goes wrong:** Engineer treats `slow_down` as a one-shot bump: bumps once, but next iteration uses the original interval. RFC 8628 §3.5 explicitly mandates the new interval persist for ALL subsequent requests; otherwise GitHub may issue another `slow_down` and eventually penalize the client (e.g., via `expired_token` early).
**How to avoid:** Mutate `state.interval` (the `_PollingState` dataclass field), not a local. Test: feed two `slow_down` responses and assert the third poll uses `initial_interval + 5 + 5` (or the server-suggested value).
**Warning signs:** Polling loops time out unexpectedly; GitHub returns `expired_token` significantly before 15 minutes.

### Pitfall 7: `time.time()` deadline poisoned by clock skew (**NEW — OWNED**)

**What goes wrong:** Engineer uses `time.time() + expires_in` as the deadline. NTP daemon adjusts wall-clock mid-flow (e.g., 30 seconds backward); deadline shifts; 15-minute window becomes 14:30 or 15:30; either expires too early (false-negative) or runs over (no expiry surfacing).
**How to avoid:** `time.monotonic()` for the deadline (it is process-local, monotonically non-decreasing, immune to NTP). Use `time.time()` only for the wire-shape `expires` epoch (where wall-clock is explicitly the contract — server-issued epoch).
**Warning signs:** Test flakes on machines with active NTP; deadline-related tests pass on dev laptops, fail in CI containers with clock-skew injection.

### Pitfall 8: SAML / SSO org failure path (informational — partially OWNED)

**What goes wrong:** User belongs to a GitHub org that requires SAML SSO. Device flow may complete, but the `gho_*` token is "unauthorized" for any org-scoped resource. The `copilot_internal/v2/token` mint may succeed (org-independent) OR may 403 with `saml_required` body (org-scoped).
**How to avoid:** Cannot avoid at the protocol layer. Surface SAML-required errors as `AuthRefreshError` with a remediation message linking to GitHub's SAML SSO docs. Document in Phase 022's CLI help: "If your org requires SAML, complete the device flow, then visit the SAML re-authorization URL before using Copilot."
**Warning signs:** Login succeeds; refresh 403s with `saml_required` body for users in SSO-enforced orgs.

### Pitfall 9: Polling loop CancelledError handling (**NEW — OWNED**)

**What goes wrong:** Daemon shutdown cancels the polling task mid-`asyncio.sleep`. Without proper handling, the cancellation propagates as `CancelledError` to the caller, who interprets it as a generic auth failure instead of a clean shutdown.
**How to avoid:** Let `asyncio.CancelledError` propagate naturally — DO NOT catch + re-raise as `AuthLoginError`. The Phase 013 outer `asyncio.wait_for` (15s cap on `method.refresh`) and the daemon's task-group shutdown handler are the right cancellation surfaces. Test: cancel a polling task in flight; assert `CancelledError` (not `AuthLoginError`) escapes.
**Warning signs:** Daemon shutdown produces "auth failed" error logs instead of clean cancellation traces.

### Pitfall 10: `OAuth-Polling-Safety-Margin` undocumented (**NEW — OWNED**)

**What goes wrong:** Engineer sleeps exactly `interval` seconds between polls. GitHub's authorization server clock is ~1-3 seconds ahead of the client; the client's "X seconds elapsed" is "X-2 seconds elapsed" server-side; GitHub returns `slow_down` because the request arrived too soon.
**How to avoid:** Add `OAUTH_POLLING_SAFETY_MARGIN_S = 3.0` to every sleep (matches opencode's 3000ms). Document the rationale in code comment.
**Warning signs:** Polling produces a `slow_down` response on the FIRST iteration; investigation reveals the client-server clock skew.

### Pitfall 11: GitHub Enterprise base-URL substitution (informational)

**What goes wrong:** Engineer hard-codes `https://github.com` and `https://api.github.com`. GHE users hit 404s because their endpoints are at `https://company.ghe.com/login/device/code` and `https://copilot-api.company.ghe.com/copilot_internal/v2/token`.
**How to avoid:** Accept `enterprise_url` as a kwarg to `login()`; derive `base_domain` and `base_api` from it; default to github.com when None. Persist `extras["enterprise_url"]` so `refresh()` reads it (it does NOT have access to the original kwarg). Phase 022 prompts for the GHE URL interactively.
**Warning signs:** GHE users report 404s on the device-code POST; refresh path still uses `api.github.com` even after GHE login.

### Pitfall 12: Editor-Version drift (P2-1 analog — informational)

**What goes wrong:** GitHub upgrades Copilot's accepted client allowlist; current `Editor-Version: Neovim/0.6.1` no longer matches; tokens authenticate but inference 401s with "client not authorized."
**How to avoid:** Maintain a `COPILOT_VERSION_LOCK.md` in `.state/` (analog to `CLAUDE_CODE_VERSION_LOCK.md` in P2-1). Phase 022's captured-header regression compares the `User-Agent` / `Editor-Version` / `Editor-Plugin-Version` triple against captured copilot.vim traffic. Periodic CI re-capture flags drift.
**Warning signs:** Inference 401s cluster after a Copilot server-side rollout; tokens still validate (login + refresh succeed).

### Pitfall 13: No PKCE in device-code flow (informational)

**What goes wrong:** Engineer assumes the loopback-flow `oauth_common/pkce.py` applies and adds `code_challenge` / `code_verifier` to the device-code POST.
**How to avoid:** Device-code flow does NOT use PKCE. The user-consent step (the human entering `user_code` at `verification_uri`) is the security boundary. `_request_device_code` body is JUST `{client_id, scope}`. Adding PKCE causes GitHub to reject the request with `invalid_request`.
**Warning signs:** Device-code POST returns 400 with `invalid_request`; reading the docs reveals no PKCE expected.

### Pitfall 14: Eager vs lazy `tid_*` mint timing (**NEW — OWNED**)

**What goes wrong:** Engineer chooses lazy minting (mint `tid_*` only on first inference call). This couples the auth contract to v3 provider routing's call lifecycle, breaks the AuthMethod contract that `cred.access` is "ready to use," and complicates `is_expired` (no `tid_*` means no `expires`).
**How to avoid:** Eager minting in `login()` and `refresh()`. `cred.access` always holds a fresh `tid_*` after a successful auth method call. Phase 013's filelock-guarded refresh path fires when `is_expired_buffered` says so.
**Warning signs:** Inference calls fail with "no session token" because v3 provider routing assumes `cred.access` is ready; tests against `cred.access` start with `tid_*` after `login()` but `gho_*` after a refresh path that forgot to mint.

## Code Examples

Verified patterns. All examples assume the planner mirrors `providers/google_gemini.py`'s structure section-for-section (with the `oauth_common/` imports REPLACED by inline RFC 8628 helpers).

### 1. Module Header (mirror google_gemini.py)

```python
"""GitHub Copilot device-code OAuth provider — RFC 8628 + two-tier token mint.

Phase 017 (M-A2 / AUTH-04 / P1-5 + P1-6 owner). Fourth concrete AuthMethod
implementation (after Phase 014 Anthropic, Phase 015 Gemini-CLI, Phase 016
Antigravity). FIRST without a loopback HTTP listener — device-code flow
(RFC 8628) replaces PKCE+loopback.

Two-tier token architecture:
  * Long-lived `gho_*` GitHub OAuth token — issued by device-code flow,
    no rotation on legacy OAuth App `Iv1.b507a08c87ecfe98`. Stored in
    OAuthCredential.refresh + extras["oauth_token"] (mirror).
  * Short-lived `tid_*` Copilot session token (~30 min) — minted from
    the gho_* via copilot_internal/v2/token. Stored in OAuthCredential.access.
    Expires field tracks tid_* expiry (NOT gho_*; Pitfall 5).

Module layout (mirrors providers/google_gemini.py):
  * Identity constants (client_id Iv1.b507a08c87ecfe98 plaintext per P1-3,
    Copilot-stealth headers per P2-1 analog, RFC 8628 endpoints + scope=read:user)
  * Pydantic models (DeviceCodeResponse, DeviceTokenResponse, CopilotSessionResponse)
  * _PollingState dataclass for the RFC 8628 state machine
  * Helpers (_request_device_code, _poll_for_token, _mint_session_token, normalize_domain)
  * GitHubCopilotAuth class (satisfies AuthMethod Protocol)
  * `if __name__ == '__main__'` argparse entry-point

Cardinal rules:
  - client_id MUST be Iv1.b507a08c87ecfe98 (Pitfall 2 — Ov23li... breaks copilot_internal mint)
  - time.monotonic() for deadline (Pitfall 7); time.time() ONLY for wire-shape expires
  - slow_down interval persists for all subsequent requests (Pitfall 6 / RFC 8628 §3.5)
  - 3-second polling safety margin (Pitfall 10)
  - Eager tid_* minting — login() and refresh() always leave cred.access valid (Pitfall 14)
  - 5-min buffer applies to tid_* (cred.expires); gho_* has no stored expiry (Pitfall 5)
  - No PKCE (Pitfall 13); no loopback listener
  - OAuth NEVER through litellm (CLAUDE.md cardinal rule)
  - No own filelock — Phase 013 owns coordination

See .planning/milestones/v2/phases/017-github-copilot-device-code-flow/
017-RESEARCH.md for full rationale, 14 pitfalls, downstream contracts.
"""
```

### 2. Constants Block

```python
# ── Identity constants — DO NOT obfuscate (P1-3) ─────────────────────────
# Sources cross-verified 2026-04-30:
#   * copilot.vim (canonical Copilot-CLI ecosystem reference)
#   * B00TK1D/copilot-api (Python reference)
#   * Alorse/copilot-to-api
#   * litellm github_copilot provider docs
#   * GSD2 gsd2-auth-analysis.md
#
# !! IMPORTANT — DO NOT swap to opencode's Ov23li8tweQw6odWQebz !!
# Tokens from Ov23li... GitHub App IDs are NOT authorized for
# copilot_internal/v2/token (verified hermes-agent#16551, cherry-studio#11905,
# opencode#20759). The legacy OAuth App `Iv1.b507a08c87ecfe98` is the only
# client_id that supports the two-tier mint we need. See Pitfall 2.

_CLIENT_ID: str = "Iv1.b507a08c87ecfe98"
_SCOPE: str     = "read:user"

# ── RFC 8628 endpoints (github.com — Enterprise overrides via base_domain) ──

# Device-code request (login leg 1):
#   POST https://{base_domain}/login/device/code
# Token polling (login leg 2):
#   POST https://{base_domain}/login/oauth/access_token
# Session-token mint (login leg 3 + every refresh):
#   POST {base_api}/copilot_internal/v2/token
#       base_api = https://api.github.com (default)
#                | https://copilot-api.{enterprise_domain} (GHE)

# ── Copilot-stealth headers (P2-1 analog — see Pitfall 12) ───────────────
# Captured from copilot.vim 1.16.0 + verified across community refs.

_USER_AGENT: str             = "GithubCopilot/1.155.0"
_EDITOR_VERSION: str         = "Neovim/0.6.1"
_EDITOR_PLUGIN_VERSION: str  = "copilot.vim/1.16.0"

# ── Polling-loop tuning ──────────────────────────────────────────────────

_POLLING_SAFETY_MARGIN_S: float = 3.0
"""Seconds added to every interval-based sleep to defend against client-server
clock skew (Pitfall 10). Mirrors opencode's OAUTH_POLLING_SAFETY_MARGIN_MS=3000."""

_SLOW_DOWN_BUMP_S: float = 5.0
"""RFC 8628 §3.5: minimum interval increase on `slow_down` response."""
```

### 3. Pydantic Response Models

```python
class DeviceCodeResponse(BaseModel):
    """200-OK payload from POST {base}/login/device/code.

    Forward-compat: extra='ignore'. GitHub may add fields (verification_uri_complete
    is in the spec; we don't depend on it for v2 — Phase 022 may use it).
    """
    model_config = ConfigDict(extra="ignore")
    device_code: str = Field(repr=False)        # secret-ish (single-use)
    user_code: str                                # human-readable, displayed
    verification_uri: str
    verification_uri_complete: str | None = None  # optional one-click variant
    expires_in: int                               # 900 = 15 minutes
    interval: int                                 # initial poll cadence (seconds)


class DeviceTokenResponse(BaseModel):
    """200-OK payload from POST {base}/login/oauth/access_token (poll endpoint).

    Either access_token is present (success) or error is present (pending/
    slow_down/expired_token/access_denied/other). Pydantic does NOT enforce
    "exactly one of" — caller checks .access_token first.
    """
    model_config = ConfigDict(extra="ignore")
    access_token: str | None = Field(default=None, repr=False)
    token_type:   str | None = None
    scope:        str | None = None
    error:        str | None = None
    error_description: str | None = None
    interval:     int | None = None  # server-suggested new interval on slow_down


class CopilotSessionResponse(BaseModel):
    """200-OK payload from POST {base_api}/copilot_internal/v2/token.

    `token` is REQUIRED — Pydantic ValidationError fires on null/missing,
    which the caller re-raises as AuthRefreshError("grant revoked …") (P1-6).
    """
    model_config = ConfigDict(extra="ignore")
    token:       str = Field(repr=False)         # tid_* short-lived session token
    expires_at:  int                              # Unix timestamp (absolute epoch)
    refresh_in:  int | None = None                # seconds until recommended refresh
    sku:         str | None = None                # free / individual / business / ent
    chat_enabled: bool | None = None              # informational
    # Many other fields exist (HasToken, ChatQuota, CompletionsQuota, …);
    # we ignore them via extra='ignore'.
```

### 4. `_PollingState` dataclass + RFC 8628 loop (skeleton — full body in Pattern 2)

```python
from dataclasses import dataclass

@dataclass
class _PollingState:
    interval: float
    deadline: float                  # time.monotonic() + expires_in
    safety_margin: float = _POLLING_SAFETY_MARGIN_S

    def remaining(self, now_mono: float) -> float:
        return max(0.0, self.deadline - now_mono)
```

### 5. `normalize_domain` helper (GHE support)

```python
def normalize_domain(url: str) -> str:
    """Strip protocol + trailing slash from a GitHub Enterprise URL.

    Mirrors opencode's pattern (copilot.ts:16):
        https://company.ghe.com/  → company.ghe.com
        company.ghe.com           → company.ghe.com
    """
    return url.replace("https://", "").replace("http://", "").rstrip("/")
```

### 6. `is_token` and `is_expired` (full implementations)

```python
def is_token(self, value: str) -> bool:
    return any(
        value.startswith(prefix)
        for prefix in ("gho_", "ghu_", "tid_", "ghr_")
    )


def is_expired(self, cred: Credential, now: float) -> bool:
    """Delegate to Phase 013's is_expired_buffered (5-min buffer per AUTH-09).

    `cred.expires` is the tid_* expiry epoch — buffer applies cleanly.
    `cred.refresh` (gho_*) does not have a stored expiry; it's checked at
    refresh time (Pitfall 5).
    """
    return is_expired_buffered(cred, now)
```

### 7. `http_headers` (regression-test surface — full body in Pattern 7)

```python
def http_headers(self, cred: Credential) -> dict[str, str]:
    if not isinstance(cred, OAuthCredential):
        return {}
    return {
        "authorization":           f"Bearer {cred.access}",   # tid_* session token
        "user-agent":               _USER_AGENT,
        "editor-version":           _EDITOR_VERSION,
        "editor-plugin-version":    _EDITOR_PLUGIN_VERSION,
    }
```

### 8. argparse `_main` (mirror Phase 015/016)

```python
# Identical shape to Phase 015's _main with these deltas:
#   - default provider_id = "github.copilot"
#   - login subcommand accepts --enterprise-url
#   - vault persistence: vault.providers.setdefault("github.copilot", []).append(cred)
#   - print user_code + verification_uri inside login() (already covered by Pattern 5)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Use `Ov23li8tweQw6odWQebz` (opencode's GitHub App) | `Iv1.b507a08c87ecfe98` (legacy OAuth App, copilot.vim canonical) | This phase | Unlocks `copilot_internal/v2/token` mint → access to full live model catalog and Anthropic-shaped `/v1/messages` proxying. |
| Bearer the `gho_*` directly to inference | Mint `tid_*` via `copilot_internal/v2/token` and Bearer that | This phase | Required for `/chat/completions` and `/v1/messages` endpoints; matches Copilot's per-call entitlement model. |
| `time.time()` deadline for 15-min window | `time.monotonic()` deadline with injectable callable | This phase | Wall-clock-independent; defends against NTP / DST / container clock-resets. |
| One-shot `slow_down` interval bump | RFC 8628 §3.5 persistent increment via mutable `_PollingState.interval` | This phase | Compliant with spec; avoids early `expired_token` from server-side rate-limit penalties. |
| No safety margin between polls | `OAUTH_POLLING_SAFETY_MARGIN_S = 3.0` per opencode reference | This phase | Defends against client-server clock skew. |
| Lazy `tid_*` mint inside inference call | Eager mint in `login()` and `refresh()` | This phase | Decouples auth contract from v3 provider routing's call lifecycle; Phase 013's filelock-guarded refresh path remains the single coordination point. |

**Deprecated / no longer recommended:**
- Polling without a hard 15-minute deadline — relies entirely on GitHub's `expired_token` response, which can be delayed if the server is overloaded.
- Storing `expires=0` on the credential (opencode's pattern, since they don't pre-mint) — forces refresh on every request; defeats the 5-minute buffer.
- Calling GitHub's OAuth refresh endpoint with `grant_type=refresh_token` for the legacy OAuth App — returns `unsupported_grant_type`. Use the session-token mint instead.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.0 + pytest-asyncio 1.3.0 (asyncio_mode=strict) |
| Config file | `pyproject.toml` (existing — `[tool.pytest.ini_options]` already configures `asyncio_mode = "strict"` and includes `tests/` in `testpaths`) |
| Quick run command | `PYTHONPATH=$PWD/src pytest tests/auth/providers/test_github_copilot.py -q` |
| Full suite command | `PYTHONPATH=$PWD/src pytest tests/auth -q` |

(The `PYTHONPATH=$PWD/src` prefix is a known worktree-vs-installed-package workaround documented in Phase 015's 015-04-SUMMARY §Deviations.)

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| AUTH-04 | `GitHubCopilotAuth` satisfies `AuthMethod` Protocol structurally (`isinstance` check) | unit | `pytest tests/auth/providers/test_github_copilot.py::test_satisfies_auth_method_protocol -x` | ❌ Wave 0 |
| AUTH-04 | `provider_id == "github.copilot"` (kebab-case-with-dot) | unit | `pytest tests/auth/providers/test_github_copilot.py::test_provider_id -x` | ❌ Wave 0 |
| AUTH-04 | `_CLIENT_ID == "Iv1.b507a08c87ecfe98"` (Pitfall 2 regression — NOT opencode's `Ov23li...`) | unit | `pytest tests/auth/providers/test_github_copilot.py::test_client_id_legacy_oauth_app -x` | ❌ Wave 0 |
| AUTH-04 | `_CLIENT_ID` is plaintext (P1-3 — no base64/XOR/env-var indirection) | unit (grep on source) | `pytest tests/auth/providers/test_github_copilot.py::test_client_id_plaintext_no_obfuscation -x` | ❌ Wave 0 |
| AUTH-04 | `_request_device_code` POSTs `{client_id, scope: "read:user"}` to `https://github.com/login/device/code` with JSON content-type + Copilot-stealth User-Agent | unit (pytest-httpx match_url + match_json + match_headers) | `pytest tests/auth/providers/test_github_copilot.py::test_request_device_code_body_and_headers -x` | ❌ Wave 0 |
| AUTH-04 | `_request_device_code` accepts GHE `base_domain` and routes to `https://{base}/login/device/code` | unit (pytest-httpx) | `pytest tests/auth/providers/test_github_copilot.py::test_request_device_code_enterprise_url -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` returns OAuth token on success branch | unit (pytest-httpx + injected sleep) | `pytest tests/auth/providers/test_github_copilot.py::test_poll_success -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` continues on `authorization_pending` (≥2 iterations) | unit (pytest-httpx + injected sleep, sequenced responses) | `pytest tests/auth/providers/test_github_copilot.py::test_poll_authorization_pending -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` increments interval by 5s on `slow_down` AND persists across iterations (Pitfall 6) — assert third sleep is `initial + 10` | unit (capture sleep call args) | `pytest tests/auth/providers/test_github_copilot.py::test_poll_slow_down_persistent_increment -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` adopts server-suggested `interval` on `slow_down` when present | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_slow_down_server_interval -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` raises `AuthLoginError` on `expired_token` | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_expired_token -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` raises `AuthLoginError` on `access_denied` | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_access_denied -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` raises `AuthLoginError` on 15-min `time.monotonic()` deadline (Pitfall 7) — uses injected monotonic that advances past deadline | unit (injected monotonic) | `pytest tests/auth/providers/test_github_copilot.py::test_poll_deadline_uses_monotonic -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` adds `_POLLING_SAFETY_MARGIN_S` (3s) to every sleep (Pitfall 10) | unit (capture sleep durations) | `pytest tests/auth/providers/test_github_copilot.py::test_poll_safety_margin -x` | ❌ Wave 0 |
| AUTH-04 | `_poll_for_token` allows `asyncio.CancelledError` to propagate (Pitfall 9) | unit (cancel task in flight) | `pytest tests/auth/providers/test_github_copilot.py::test_poll_cancelled_propagates -x` | ❌ Wave 0 |
| AUTH-04 | `_mint_session_token` POSTs to `https://api.github.com/copilot_internal/v2/token` with Bearer + Copilot-stealth triple headers | unit (pytest-httpx match_headers) | `pytest tests/auth/providers/test_github_copilot.py::test_mint_session_headers -x` | ❌ Wave 0 |
| AUTH-04 | `_mint_session_token` raises `AuthRefreshError` on 401/403 (grant revoked) | unit | `pytest tests/auth/providers/test_github_copilot.py::test_mint_session_grant_revoked_401 -x` | ❌ Wave 0 |
| AUTH-04 | `_mint_session_token` raises `AuthRefreshError` on 200-with-null-token (P1-6 — Pydantic ValidationError → wrapped) | unit (pytest-httpx returning `{}`) | `pytest tests/auth/providers/test_github_copilot.py::test_mint_session_null_token_grant_revoked -x` | ❌ Wave 0 |
| AUTH-04 | `_mint_session_token` enterprise base routes to `https://copilot-api.{domain}/copilot_internal/v2/token` | unit | `pytest tests/auth/providers/test_github_copilot.py::test_mint_session_enterprise_url -x` | ❌ Wave 0 |
| AUTH-04 | `login()` end-to-end: device-code → poll success → mint → OAuthCredential with `tid_*` in `access`, `gho_*` in `refresh`, `expires_at` in `expires`, `extras["oauth_token"]` mirror, `provider_id="github.copilot"` (Pattern 4 — two-tier mapping) | unit (pytest-httpx 3-stage sequence) | `pytest tests/auth/providers/test_github_copilot.py::test_login_two_tier_credential -x` | ❌ Wave 0 |
| AUTH-04 | `login(enterprise_url=...)` persists `extras["enterprise_url"]` (Pitfall 11) | unit | `pytest tests/auth/providers/test_github_copilot.py::test_login_enterprise_url_persisted -x` | ❌ Wave 0 |
| AUTH-04 | `refresh()` re-mints `tid_*` from stored `gho_*` (does NOT call GitHub OAuth refresh endpoint; uses `cred.refresh` as Bearer for `copilot_internal/v2/token`) | unit (pytest-httpx) | `pytest tests/auth/providers/test_github_copilot.py::test_refresh_remints_session_from_gho -x` | ❌ Wave 0 |
| AUTH-04 | `refresh()` returns new `OAuthCredential` via `model_copy` (frozen-model invariant; preserves `account_id` + non-rotated `extras`) | unit | `pytest tests/auth/providers/test_github_copilot.py::test_refresh_model_copy_preserves_extras -x` | ❌ Wave 0 |
| AUTH-04 | `refresh()` does NOT acquire its own filelock (refresh.py rule 9) | unit (grep for filelock imports) | `pytest tests/auth/providers/test_github_copilot.py::test_no_filelock_imports -x` | ❌ Wave 0 |
| AUTH-04 | `is_expired` delegates to `is_expired_buffered` (5-min buffer applies to `tid_*` expiry; Pitfall 5) | unit | `pytest tests/auth/providers/test_github_copilot.py::test_is_expired_uses_buffered -x` | ❌ Wave 0 |
| AUTH-04 | `is_token` returns True for `gho_`, `ghu_`, `tid_`, `ghr_` prefixes (4 cases) | unit (parametrize) | `pytest tests/auth/providers/test_github_copilot.py::test_is_token_prefixes -x` | ❌ Wave 0 |
| AUTH-04 | `http_headers` emits Bearer + User-Agent + Editor-Version + Editor-Plugin-Version (4 keys, byte-stable values) | unit | `pytest tests/auth/providers/test_github_copilot.py::test_http_headers_four_keys -x` | ❌ Wave 0 |
| AUTH-04 | `http_headers` returns `{}` for `ApiKeyCredential` | unit | `pytest tests/auth/providers/test_github_copilot.py::test_http_headers_non_oauth_returns_empty -x` | ❌ Wave 0 |
| AUTH-04 | `_main` argparse: `login` (with `--enterprise-url`) + `refresh` subcommands; KeyboardInterrupt → 130 | unit (capsys + monkeypatch) | `pytest tests/auth/providers/test_github_copilot.py::test_main_argparse_subcommands -x` | ❌ Wave 0 |
| AUTH-04 | Vault persistence in `_main login`: `setdefault("github.copilot", []).append(cred)` (P1-7 array invariant) | unit (mock vault) | `pytest tests/auth/providers/test_github_copilot.py::test_main_vault_persistence -x` | ❌ Wave 0 |
| AUTH-04 | Phase 013 integration: `_main refresh` drives `refresh_credential` (filelock + double-check) | integration | `pytest tests/auth/providers/test_github_copilot.py::test_main_refresh_drives_phase013 -x` | ❌ Wave 0 |
| AUTH-04 | NO `import litellm` / `from litellm` (cardinal rule grep gate) | unit (grep) | `pytest tests/auth/providers/test_github_copilot.py::test_no_litellm_imports -x` | ❌ Wave 0 |
| AUTH-04 | NO `state.build.*` / `state.teach.*` imports (mode isolation grep gate) | unit (grep) | `pytest tests/auth/providers/test_github_copilot.py::test_no_mode_specific_imports -x` | ❌ Wave 0 |
| AUTH-04 | NO `oauth_common.pkce` / `oauth_common.loopback` imports (Pitfall 13 — device-code uses neither) | unit (grep) | `pytest tests/auth/providers/test_github_copilot.py::test_no_oauth_common_imports -x` | ❌ Wave 0 |
| AUTH-04 | Captured-header golden-file (AUTH-13 v2 stub): `http_headers` matches expected dict byte-for-byte | unit (snapshot) | `pytest tests/auth/providers/test_github_copilot.py::test_http_headers_golden_file -x` | ❌ Wave 0 |

(All test files are NEW — Wave 0 must create them. Total: ~36 test cases — exceeds the 18-25 floor specified in the additional context.)

### Sampling Rate

- **Per task commit:** `PYTHONPATH=$PWD/src pytest tests/auth/providers/test_github_copilot.py -q`
- **Per wave merge:** `PYTHONPATH=$PWD/src pytest tests/auth -q` (full auth suite — must remain green; baseline is whatever Phase 016 lands at)
- **Phase gate:** `PYTHONPATH=$PWD/src pytest -q` (full project test suite — must exit 0 before `/gsd:verify-work`)

### Wave 0 Gaps

- [ ] `tests/auth/providers/test_github_copilot.py` — covers AUTH-04 (~36 tests; planner mirrors `test_google_gemini.py` shape for the conformance/sniffer/headers half + adds the polling-state-machine + two-tier mint half)
- [ ] `src/state_core/auth/providers/github_copilot.py` — the provider module itself (created during Wave 1 / 2 / 3 — RED → GREEN)
- [ ] No new framework install or fixtures needed — `tests/auth/conftest.py` already provides shared fixtures (vault setup, monkeypatch helpers). Tests must inject `monotonic` and `sleep` callables directly into `_poll_for_token` (no global monkeypatch needed since the function accepts them as kwargs).

## Open Questions (RESOLVED)

All open questions raised in the orchestrator's additional-context block have been resolved during this research pass. No items deferred to plan-phase.

1. **Exact GitHub OAuth device-code endpoints?**
   - **RESOLVED:** Device-code: `POST https://github.com/login/device/code`. Polling: `POST https://github.com/login/oauth/access_token` with `grant_type=urn:ietf:params:oauth:grant-type:device_code`. Both are JSON-bodied (Accept + Content-Type: application/json). Polling interval = server-returned `interval` field (typically 5s); expiry = server-returned `expires_in` (15 min = 900s). Verified opencode `copilot.ts:21–25` + B00TK1D + RFC 8628.

2. **Client ID for Copilot CLI?**
   - **RESOLVED:** `Iv1.b507a08c87ecfe98` (legacy OAuth App, used by copilot.vim, copilot.el, B00TK1D, litellm, gsd-2pi reference). NOT opencode's `Ov23li8tweQw6odWQebz` — that ID is a GitHub App and cannot mint `tid_*` via `copilot_internal/v2/token` (Pitfall 2). Source: hermes-agent issue #16551 + cherry-studio issue #11905 + opencode issue #20759.

3. **Scope list?**
   - **RESOLVED:** `read:user` only. No Copilot-specific scopes; the user's Copilot subscription is bound to the GitHub account, not a scope. Verified across opencode reference + B00TK1D + litellm.

4. **Token shapes?**
   - **RESOLVED:** Two-tier architecture confirmed.
     - **Long-lived OAuth token** — `gho_*` (or sometimes `ghu_*` for user-to-server in newer flows). Issued by `login/oauth/access_token`. Indefinite TTL on legacy OAuth App `Iv1...` (no refresh_token rotation; the OAuth grant itself is revocable). Stored in `OAuthCredential.refresh` + `extras["oauth_token"]` mirror.
     - **Short-lived Copilot session token** — `tid_*`. ~30 minutes TTL. Minted via `POST https://api.github.com/copilot_internal/v2/token` with `Bearer <gho_*>`. Stored in `OAuthCredential.access`. Expiry tracked in `OAuthCredential.expires` (from `expires_at` Unix timestamp).
     - Refresh token (`ghr_*`) — NOT issued by `Iv1...` (only GitHub Apps with expiring tokens issue these). Out of scope for Phase 017.

5. **Device-code polling protocol?**
   - **RESOLVED:** RFC 8628 §3.5 state machine with five outcomes (`authorization_pending` continue, `slow_down` increase interval persistently by 5s or server-suggested value, `expired_token` terminal, `access_denied` terminal, success). 15-min hard deadline via `time.monotonic()` (NOT `time.time()` — Pitfall 7). 3-second safety margin per opencode reference (`OAUTH_POLLING_SAFETY_MARGIN_MS = 3000` — Pitfall 10).

6. **Grant-revocation detection?**
   - **RESOLVED:** TWO surfaces.
     - During login polling: GitHub returns `error=access_denied` (RFC 8628 standard) → `AuthLoginError("User denied authorization")`.
     - During refresh / re-mint: `copilot_internal/v2/token` returns 401/403 (oauth token rejected) OR 200-with-null-token (P1-6 — user revoked Copilot access in GitHub settings). The 200-null case is caught by Pydantic's required-field validation on `CopilotSessionResponse.token: str`; the resulting `ValidationError` is re-raised as `AuthRefreshError("Copilot grant revoked or session response shape: …")`.

7. **Refresh handling?**
   - **RESOLVED:** "Refresh" in this provider means **re-minting `tid_*` from stored `gho_*`** — NOT calling GitHub's OAuth refresh-token endpoint (which is unsupported on `Iv1...`). The `refresh()` method accepts an `OAuthCredential` whose `refresh` field is the `gho_*`, calls `_mint_session_token`, and returns a new credential with updated `access` (`tid_*`) and `expires`. Pydantic validates the response. No refresh-token rotation (`gho_*` is indefinite) — this DEPARTS from Phase 015's P2-2 rotation rule.

8. **Headers GitHub expects?**
   - **RESOLVED:** Three Copilot-stealth headers + one Bearer.
     - `Accept: application/json` — standard; on device-code POST and polling POST and mint POST.
     - `Content-Type: application/json` — when the body is JSON; on device-code POST and polling POST (mint POST is body-less).
     - `User-Agent: GithubCopilot/1.155.0` — Copilot-stealth (mandatory; server allowlist matches).
     - `Editor-Version: Neovim/0.6.1` — Copilot-stealth (mandatory on `copilot_internal/v2/token` and on inference calls).
     - `Editor-Plugin-Version: copilot.vim/1.16.0` — Copilot-stealth.
     - `Authorization: Bearer <token>` — gho_* on `copilot_internal/v2/token` mint; `tid_*` on inference calls.

9. **provider_id naming?**
   - **RESOLVED:** `"github.copilot"` (kebab-case-with-dot, sibling to `"google.gemini_cli"` and `"google.antigravity"`). Diverges from opencode's `"github-copilot"` for namespace consistency; Phase 021 first-run import translates.

10. **Token-shape sniffer?**
    - **RESOLVED:** `is_token(value)` returns True for any of `gho_`, `ghu_`, `tid_`, `ghr_` prefixes. Both the long-lived (`gho_*`/`ghu_*`) and the short-lived (`tid_*`) are issued by this provider. `ghr_` is included for completeness (future-proofing if we ever add GitHub-App-based Copilot via expiring tokens). Provider-level routing disambiguates via `cred.provider_id`.

11. **`chmod 0600` vault?**
    - **RESOLVED:** Already enforced by Phase 012's `store.save_vault` and `_atomic_write` (chmod at create + fchmod + verified on every read). This phase does NOT touch vault internals; the credential is persisted via the `_main` script's `vault.providers.setdefault("github.copilot", []).append(cred)` line, then `save_vault` does the rest. No new logic needed.

12. **No litellm, no own `from filelock import`?**
    - **RESOLVED:** Confirmed via grep gates (test_no_litellm_imports + test_no_filelock_imports). Phase 013's `refresh_credential` is the only `filelock` consumer; this provider's `refresh()` is pure HTTP.

13. **Determinism?**
    - **RESOLVED:** All HTTP-bearing methods accept injectable clocks where applicable.
      - `_poll_for_token(monotonic, sleep, ...)` — clock + sleep are kwargs with `time.monotonic` / `asyncio.sleep` defaults.
      - `_to_credential(now=...)` — pattern from Phase 015.
      - `_mint_session_token` reads `time.time()` ONLY for the post-success `now` capture (no — actually we use `session.expires_at` which is the absolute server epoch; we never need `time.time()` for `_mint_session_token`).
      - `login()` and `refresh()` read the wall clock once at success time only via `_to_credential`'s `now` kwarg (or directly assign `expires_at` to `expires`, which is server-side absolute — no client clock involved at all). **Polling loop is the only legitimate clock-reader (`time.monotonic`); `time.time()` is unused.**

14. **Reusable scaffolding from Phase 015/016?**
    - **RESOLVED:**
      - `state_core.auth.errors` — DIRECTLY REUSED (`AuthLoginError`, `AuthRefreshError`).
      - `state_core.auth.refresh.refresh_credential` — DIRECTLY REUSED (the outer filelock-guarded path; provider's `refresh()` plugs into it).
      - `state_core.auth.refresh.is_expired_buffered` — DIRECTLY REUSED.
      - id_token JWT parser — NOT applicable. GitHub does not issue id_tokens in the device-code flow (no OpenID Connect).
      - `oauth_common.pkce` — NOT applicable (no PKCE in device-code flow).
      - `oauth_common.loopback` — NOT applicable (no loopback listener; user pastes the code).
      - Phase 014/015/016 module structure (constants → Pydantic models → helpers → AuthMethod class → argparse `_main`) — REUSED line-for-line as a structural template.

15. **Validation Architecture per VALIDATION.md template?**
    - **RESOLVED:** Section above provides ~36 test cases (exceeds the 18-25 minimum specified in additional context) covering: AuthMethod conformance (1), provider_id (1), client_id constants + plaintext (2), device-code request (2), polling state machine (9 — success / pending / slow_down increment + persistence + server-interval / expired / denied / monotonic deadline / safety margin / cancellation), session-token mint (4), login end-to-end + enterprise (2), refresh + model_copy + no-filelock (3), is_expired (1), is_token (1), http_headers (2), argparse `_main` + vault + Phase 013 integration (3), grep gates (3), captured-header golden-file (1).

16. **Pitfalls to consider?**
    - **RESOLVED:** 14 pitfalls catalogued above.
      - Inherited: P1-3 (client_id plaintext), P0-7 / AUTH-09 (5-min buffer applies to `tid_*` only — Pitfall 5), P1-5 (15-min UX), P1-6 (200-with-null-body), P2-1 analog (Editor-Version drift — Pitfall 12).
      - NEW owned: Pitfall 2 (wrong client_id breaks mint), Pitfall 6 (slow_down persistence), Pitfall 7 (monotonic deadline), Pitfall 9 (CancelledError propagation), Pitfall 10 (3s safety margin), Pitfall 14 (eager mint).
      - Informational: Pitfall 8 (SAML/SSO), Pitfall 11 (GHE base URL), Pitfall 13 (no PKCE).

## Sources

### Primary (HIGH confidence)

- **Phase 015 RESEARCH** (`/Users/tmac/Projects/state/.planning/milestones/v2/phases/015-gemini-cli-oauth-provider/015-RESEARCH.md`) — module structure template, AuthMethod Protocol contract, refresh-token rotation language (note: 017 departs from this for the gho_* tier).
- **Phase 016 RESEARCH** (`/Users/tmac/Projects/state/.planning/milestones/v2/phases/016-antigravity-oauth-provider/016-RESEARCH.md`) — argparse `_main` pattern, vault persistence, plaintext-constants discipline, captured-header regression test surface.
- **`src/state_core/auth/base.py`** — `OAuthCredential` shape (frozen, extras), `AuthMethod` Protocol, `provider_id` naming convention.
- **`src/state_core/auth/errors.py`** — `AuthLoginError` / `AuthRefreshError` reused.
- **`src/state_core/auth/refresh.py`** — `is_expired_buffered`, `refresh_credential` filelock-guarded path, 15s `wait_for` cap, refresh.py rule 9 (no nested locks).
- **`src/state_core/auth/store.py`** — `AuthVault.providers: dict[str, list[Credential]]`, chmod 0600 enforced via `_atomic_write`.
- **`src/state_core/auth/providers/google_gemini.py`** — direct structural template (constants → Pydantic → helpers → class → `_main`).
- **opencode reference: `state-inputs/opencode/packages/opencode/src/plugin/github-copilot/copilot.ts`** — `OAUTH_POLLING_SAFETY_MARGIN_MS=3000` constant, polling state-machine outline, slow_down handling, GHE `enterpriseUrl` + `copilot-api.{enterprise}` base substitution. NOTE: opencode uses `Ov23li8tweQw6odWQebz` (the wrong client_id for our use case — we deliberately diverge).
- **opencode reference: `state-inputs/opencode/packages/opencode/src/plugin/github-copilot/models.ts`** — confirms `api.githubcopilot.com/models` as the live model catalog endpoint.
- **`.planning/research/STACK.md`** — pinned dep floors.
- **`.planning/research/PITFALLS.md`** — P0-7, P1-3, P1-5, P1-6, P2-1 owners + reasoning.
- **`.state-inputs/gsd2-auth-analysis.md`** — confirms `Iv1.b507a08c87ecfe98` is the legacy OAuth App ID; "Copilot subscription → Claude + GPT" positioning.
- **RFC 8628 — OAuth 2.0 Device Authorization Grant** — <https://datatracker.ietf.org/doc/html/rfc8628> — §3.5 polling protocol + error codes (`authorization_pending`, `slow_down`, `expired_token`, `access_denied`).
- **GitHub Authentication Token Format updates (March 2026)** — <https://github.blog/changelog/2021-03-31-authentication-token-format-updates-are-generally-available/> — `gho_`, `ghu_`, `ghr_` prefix definitions.

### Secondary (MEDIUM-HIGH confidence — cross-verified across 3+ independent sources)

- **B00TK1D/copilot-api** (Python reference) — `https://github.com/B00TK1D/copilot-api/blob/main/api.py` — full Python device-code + two-tier mint implementation; canonical Editor-Version / User-Agent / Editor-Plugin-Version values.
- **Alorse/copilot-to-api** — `https://github.com/Alorse/copilot-to-api` — alternative Python implementation; verifies headers + endpoints.
- **litellm GitHub Copilot provider docs** — `https://docs.litellm.ai/docs/providers/github_copilot` — confirms device-code flow + customizable `GITHUB_COPILOT_DEVICE_CODE_URL` / `_ACCESS_TOKEN_URL` / `_API_KEY_URL` for GHE.
- **hermes-agent issue #16551** — `https://github.com/NousResearch/hermes-agent/issues/16551` — confirms `Ov23li...` cannot mint `tid_*`; `Iv1.b507a08c87ecfe98` is required.
- **CherryHQ/cherry-studio issue #11905** — `https://github.com/CherryHQ/cherry-studio/issues/11905` — additional confirmation of client-ID compatibility constraints.
- **anomalyco/opencode issue #20759** — `https://github.com/anomalyco/opencode/issues/20759` — Copilot Business/Enterprise three-issue compounding analysis (auth + endpoints + headers).
- **GitHub Docs: Authenticating GitHub Copilot CLI** — `https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli` — official device-flow positioning.
- **GitHub community discussion #136922** — `https://github.com/orgs/community/discussions/136922` — `copilot_internal/v2/token` endpoint timeout pattern; confirms 30-min `tid_*` TTL.
- **openclaw issue #8808** — `https://github.com/openclaw/openclaw/issues/8808` — "Copilot token expires after ~30 minutes with no refresh"; confirms two-tier architecture.

### Tertiary (LOW confidence — informational / context only)

- **GitHub OAuth refresh-token rotation docs** — `https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens` — applies to GitHub Apps with expiring tokens (NOT our `Iv1...` legacy OAuth App).
- **OpenClaw provider docs (GitHub Copilot)** — `https://docs.openclaw.ai/providers/github-copilot` — third-party docs; informational.

## Metadata

**Confidence breakdown:**

- Standard stack — HIGH (no new deps; `oauth_common/` correctly NOT used)
- Architecture / two-tier mapping — HIGH (cross-verified across opencode, B00TK1D, Alorse, litellm; `OAuthCredential.extras` precedent established by Phase 014/015/016)
- Pitfalls — HIGH (14 pitfalls catalogued; inherited owners + 6 new with HIGH-confidence ownership; informational items flagged)
- client_id (`Iv1.b507a08c87ecfe98`) — HIGH (cross-verified across 4 independent sources; the Ov23li alternative explicitly disconfirmed)
- RFC 8628 polling state machine — HIGH (RFC + opencode + B00TK1D + community verification)
- Two-tier token architecture (`gho_*` → `tid_*`) — HIGH (B00TK1D + Alorse + litellm + opencode discussion + GitHub community discussions)
- Copilot-stealth headers (User-Agent / Editor-Version / Editor-Plugin-Version) — HIGH-MEDIUM (canonical values from copilot.vim + B00TK1D; subject to drift per Pitfall 12)
- 200-with-null-body grant revocation (P1-6) — HIGH (catalogued in PITFALLS.md; Pydantic validation strategy is idiomatic)
- 15-min `time.monotonic()` deadline — HIGH (Python stdlib semantics; Pitfall 7 owns the gotcha)
- `_POLLING_SAFETY_MARGIN_S = 3.0` — HIGH (matches opencode's documented `OAUTH_POLLING_SAFETY_MARGIN_MS=3000`)
- Eager-mint architecture decision — HIGH (consistent with Phase 014/015/016 contract; lazy-mint trade-offs explicitly considered + rejected)
- No new `Credential` variant decision — HIGH (YAGNI; Phase 014's two-token Anthropic precedent maps cleanly)

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30-day window for stable GitHub OAuth + Copilot endpoints; sooner if GitHub flips the Editor-Version allowlist or rotates the `Iv1...` OAuth App's accepted client list — monitor the captured-header regression test in Phase 022)
