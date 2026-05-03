# Phase 015: Gemini CLI OAuth provider — Research

**Researched:** 2026-04-30
**Domain:** Google OAuth 2.0 Desktop-App pattern + loopback IP redirect (RFC 8252) + PKCE S256 + refresh-token rotation persistence; second concrete `AuthMethod` implementation (Anthropic was first, in 014).
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

None — `015-CONTEXT.md` was auto-generated with `workflow.skip_discuss: true`. There are no user-locked decisions for this phase. All implementation choices are at Claude's discretion (constrained by the hard project-level rules below).

### Claude's Discretion

All implementation choices are at Claude's discretion. The discretion bounds are:

- Project-level rules from `CLAUDE.md` (Python 3.12+, mode isolation, deterministic event payloads, chmod-0600 vault, `.state/events.sqlite` first).
- Already-pinned deps from `STACK.md` (`google-auth>=2.35`, `google-auth-oauthlib>=1.2`, `httpx>=0.28.1`, `pydantic>=2.13.2`, `filelock>=3.20.3`, `cryptography>=43.0`, `structlog>=25.1`, `pytest>=8.4.0`, `pytest-asyncio>=1.3.0`, `pytest-httpx>=0.35`).
- Phase 011/012/013 contracts (AuthMethod Protocol, OAuthCredential, AuthVault array shape, refresh.py filelock-guarded `refresh_credential` with double-check).
- P1-3 (plaintext client_secret with rationale comment — NOT base64/XOR).
- P2-2 (refresh-token rotation: persist new refresh_token if returned).
- AUTH-09 (5-minute expiry buffer applied at AuthMethod layer, not at storage).
- Phase 014 patterns (per-call `httpx.AsyncClient`, no module-level singleton, no own filelock, no retry layer, exception hierarchy `AuthError → AuthLoginError, AuthRefreshError`).

### Deferred Ideas (OUT OF SCOPE)

None explicitly deferred via CONTEXT — discuss was skipped. Implicit deferrals from sibling-phase scope:

- Polished `state auth login google.gemini_cli` Typer CLI — Phase 022.
- Free-tier quota-exhaustion 429 parsing + multi-cred handoff — Phase 019 (round-robin) + v3 provider routing (P1-4).
- First-run import from `~/.gemini/oauth_creds.json` — Phase 021.
- Structlog token redactor for `ya29.*` access tokens — Phase 020.
- Inference-call routing with id_token / x-goog-user-project headers — v3 provider routing.
- Antigravity OAuth (different client_id, extra scopes) — Phase 016.
- `cloudcode-pa.googleapis.com` API call wiring — v3 provider routing (this phase only owns auth, not inference).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-02 | Gemini CLI free-tier OAuth (google-auth-oauthlib, PKCE, refresh rotation) | Sections **Standard Stack** (google-auth, google-auth-oauthlib pins), **Architecture Patterns** §1–§5 (manual flow over `InstalledAppFlow.run_local_server`, loopback HTTP listener, PKCE S256 reuse from 014's `oauth_common/pkce.py`, refresh-rotation persistence, AuthMethod Protocol implementation, exception hierarchy), **Don't Hand-Roll** table (delegate token exchange + signature math to google-auth), **Common Pitfalls** §1–§9 (P1-3 plaintext rationale, P2-2 refresh rotation, scope set, port-binding races, headless fallback, `state` parameter CSRF, expiry datetime→epoch conversion, account-id sourcing, kebab-case provider_id), **Code Examples** §1–§7 (manual loopback server, PKCE reuse, OAuth body shape, Google `Credentials` → `OAuthCredential` adapter, refresh-rotation `model_copy`, http_headers Bearer + x-goog-user-project, token-shape sniffer). |

</phase_requirements>

## Summary

Phase 015 is the second concrete `AuthMethod` implementation. Where Anthropic (Phase 014) used a paste-flow (no callback server) and a stealth header set, Gemini uses Google's standard **Desktop App OAuth pattern with a loopback redirect** (RFC 8252) — a localhost HTTP listener that catches the authorization-code redirect from the user's browser. The technical surface is moderate: PKCE S256 (already shipped in `oauth_common/pkce.py`), one authorize URL, one localhost listener, one token-endpoint POST for `authorization_code`, and one for `refresh_token`. The challenging parts are (a) **refresh-token rotation** (Google sometimes issues a new `refresh_token` on refresh — silently dropping it breaks the next refresh, P2-2), (b) the **plaintext `client_secret`** rationale comment (P1-3 — base64/XOR is *not* a defence and trips AV scanners), and (c) **port handling** for the loopback redirect (port 0 + bind-then-read for race-free allocation; fixed-port fallback for users behind firewalls).

We **drive the loopback flow manually** rather than calling `InstalledAppFlow.run_local_server()`. Three reasons: (1) `run_local_server` is a synchronous blocking call that constructs its own `wsgiref` server — incompatible with our asyncio daemon model; (2) it hard-codes its own `state` generation and we want auditable parity with the gemini-cli reference (`state` is a CSRF guard, separate from PKCE `code_verifier` per RFC 6749 — UNLIKE Anthropic where `state == verifier`); (3) hand-rolling lets us share `oauth_common/pkce.py` with 014/016/017 instead of relying on `Flow.code_verifier` autogeneration. We use `google.oauth2.credentials.Credentials` for the *refresh* path only — the `.refresh(google.auth.transport.requests.Request())` call gives us automatic id_token re-validation and the rotated refresh_token (when present) on a single object.

The provider does NOT acquire its own filelock — Phase 013's `refresh_credential` already wraps `AuthMethod.refresh` in a 10s-budgeted `AsyncFileLock` with double-check semantics. Per-call `httpx.AsyncClient` for token exchange (no singleton), no retry layer, and `Timeout(10.0, connect=5.0)` keep us inside Phase 013's 15s `wait_for` cap. The Bearer-only outbound shape (`Authorization: Bearer ya29.…`) plus an optional `x-goog-user-project` header (when `extras["project_id"]` is set) is what `http_headers()` returns. Inference routing through `cloudcode-pa.googleapis.com` is OUT OF SCOPE — v3 provider routing wires that.

**Primary recommendation:** Land `providers/google_gemini.py` (~280 LOC) plus a small `oauth_common/loopback.py` (~80 LOC, async loopback HTTP listener) that 016 (Antigravity) will reuse byte-for-byte. Reuse `oauth_common/pkce.py` from 014 untouched. Mirror the gemini-cli reference for `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OAUTH_SCOPE`, `SIGN_IN_SUCCESS_URL`, `SIGN_IN_FAILURE_URL` byte-for-byte (these are the public, distributed-app credentials documented as plaintext per Google's Desktop App OAuth guidance). Use `google.oauth2.credentials.Credentials.refresh()` for the rotation path — it handles "refresh_token may or may not be returned" correctly.

## Standard Stack

### Core (already pinned in `pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.12+ | `asyncio` (event loop, `start_server`, `wait_for`), `secrets`, `urllib.parse` (`urlencode`, `parse_qs`), `webbrowser` (deferred to 022; we print URL in 015), `socket` (port 0 allocation), `time`, `datetime` (epoch conversion for Google's `expiry: datetime`) | Loopback HTTP listener + URL building stay stdlib. |
| `google-auth` | `>=2.35` | `google.oauth2.credentials.Credentials` (refresh path), `google.auth.transport.requests.Request` (sync transport for `Credentials.refresh`) | The canonical Python OAuth Credentials object. Using it for refresh handles refresh-token rotation, expiry datetime arithmetic, and id_token validation idiomatically. STACK.md pin. |
| `google-auth-oauthlib` | `>=1.2` | NOT used directly — `InstalledAppFlow.run_local_server` is sync-blocking and hard-codes its own `state`. We import the package only as a doc-link / version pin for the team's mental model. | Pinned by STACK.md but not load-bearing for the manual flow. |
| `httpx` | `>=0.28.1` | Async POST to Google's token endpoint (`https://oauth2.googleapis.com/token`) for the `authorization_code` exchange. The `refresh_token` exchange goes through `google-auth`'s sync `Credentials.refresh()` driven by `asyncio.to_thread`. | Same client choice as Phase 014. Per-call `AsyncClient`. |
| `pydantic` | `>=2.13.2` | `GoogleTokenResponse(BaseModel)` with `extra="ignore"` for token-endpoint response parsing. | Forward-compat with future Google fields. |
| `filelock` | `>=3.20.3` | Imported transitively via Phase 013's `refresh_credential` — provider does NOT touch it directly. | Hard CVE-2026-22701 floor. |
| `structlog` | `>=25.1` | Login/refresh observability. Phase 020 attaches the `ya29.*` redactor. | Project-wide logging substrate. |

### Supporting (test only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8.4.0` | Test runner | Always. |
| `pytest-asyncio` | `>=1.3.0` | Async test support | Every `login()` / `refresh()` test. |
| `pytest-httpx` | `>=0.35` | `httpx_mock` fixture: `add_response(match_url, match_headers, match_json, match_content, match_params)` for the token-endpoint POST. | Token-exchange tests. |
| `pytest-mock` | `>=3.14` | `monkeypatch.setattr` for `webbrowser.open`, `secrets.token_urlsafe`, `socket.socket`. | Login-flow tests. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual loopback HTTP listener (asyncio) | `google_auth_oauthlib.flow.InstalledAppFlow.run_local_server()` | `run_local_server` is synchronous (blocks the event loop), hard-codes `state` generation, and uses `wsgiref.simple_server`. Manual flow = asyncio-native, auditable parity with gemini-cli reference, shared with Phase 016 Antigravity. |
| `google.oauth2.credentials.Credentials.refresh()` for refresh | Hand-rolled httpx POST to `https://oauth2.googleapis.com/token` | google-auth handles the rotation contract correctly: response may or may not include `refresh_token`; if absent, the old one is preserved on the Credentials object. Hand-rolling re-introduces P2-2. We DO NOT hand-roll refresh. |
| Run `Credentials.refresh()` via `asyncio.to_thread` | Async refresh via httpx | google-auth's `Request` transport is blocking. `to_thread` is one line; matches Phase 013's 15s `wait_for` budget. |
| Manual httpx token exchange for `authorization_code` | google-auth-oauthlib's `Flow.fetch_token()` | We hand-roll login because (a) we want `match_json` byte-for-byte assertions for tests, (b) the body shape is small and stable, (c) we already do this in Phase 014 — consistent pattern across providers. |
| Plaintext client_id + client_secret in source | Base64 encode, XOR, env vars | **P1-3 explicitly forbids obfuscation**: AV scanners flag obfuscated literals as malicious. Plaintext + a rationale comment quoting Google's Desktop-App OAuth guidance is the correct answer. |
| Use `state == verifier` (Anthropic pattern, P0-8) | Independent random `state` for CSRF | **DO NOT REUSE** — Google does not require `state == verifier`. Use independent `state` per RFC 6749 §10.12 (CSRF) AND `code_verifier` per RFC 7636 (PKCE). Conflating them weakens CSRF protection on the loopback redirect. |
| Loopback port 0 (kernel-allocated) | Fixed port (e.g., 1455) | Port 0 avoids "port already in use" races between concurrent CLIs. We bind a socket with port 0, read the assigned port, close the probe socket, then construct the redirect URI — accepting the small race window since our daemon is single-user. Fall back to fixed-port pool if `OAUTH_CALLBACK_PORT` env is set (gemini-cli compat). |
| Per-call `httpx.AsyncClient` | Module-level singleton | Phase 014 pattern. Auth calls infrequent; pool-keepalive saves nothing; singletons leak across tests. |

**Installation:** No new dependencies required — every line above is already pinned.

## Architecture Patterns

### Recommended Project Structure

```
src/state_core/auth/
├── __init__.py
├── base.py                                  # (existing — Phase 011)
├── store.py                                 # (existing — Phase 012)
├── refresh.py                               # (existing — Phase 013)
├── oauth_common/
│   ├── __init__.py                          # (existing — empty)
│   ├── pkce.py                              # (existing — Phase 014; reused unchanged)
│   └── loopback.py                          # NEW — async loopback HTTP listener (~80 LOC)
│                                            #   shared with Phase 016 (Antigravity)
└── providers/
    ├── __init__.py                          # (existing — empty)
    ├── anthropic.py                         # (existing — Phase 014)
    └── google_gemini.py                     # NEW — ~280 LOC
                                              #   includes `if __name__ == "__main__": ...`
                                              #   so `python -m state_core.auth.providers.google_gemini login` works

tests/auth/
├── (existing fixtures in conftest.py)
├── oauth_common/
│   ├── test_pkce.py                         # (existing)
│   └── test_loopback.py                     # NEW — listener lifecycle, port allocation, state CSRF
└── providers/
    ├── test_anthropic.py                    # (existing)
    └── test_google_gemini.py                # NEW — pytest-httpx token-exchange + refresh-rotation
```

**provider_id naming:** `"google.gemini_cli"` — kebab-case-with-dot-namespace. Matches `base.py`'s example docstring (`'google.gemini_cli'`) AND distinguishes from Phase 016's `"google.antigravity"`. The dot is a namespace separator within the AuthVault `providers` dict; both Google variants live as siblings, never as sub-keys. Phase 019 round-robin rotates within a single `provider_id` bucket — Gemini and Antigravity are intentionally separate buckets.

### Pattern 1: Manual Loopback Redirect Flow

**What:** Bind a TCP listener on `127.0.0.1` at a kernel-allocated port; build the authorize URL with `redirect_uri=http://127.0.0.1:{port}/oauth2callback`; print URL (or `webbrowser.open` in 022); accept exactly ONE GET request; extract `code` and `state` from the query string; respond with a 302 redirect to Google's `SIGN_IN_SUCCESS_URL` (or 400 + redirect to `SIGN_IN_FAILURE_URL` on error); close the listener.

**When to use:** Both Phase 015 and Phase 016. Lives in `oauth_common/loopback.py`.

**Why manual (not `InstalledAppFlow.run_local_server`):** `run_local_server` is synchronous (`wsgiref.simple_server`), blocks the asyncio event loop, hard-codes `state` generation inside `Flow`, and does not expose the listening port until after `serve_forever` returns. Our daemon is asyncio-native; the loopback listener must be too.

**Skeleton:**
```python
# src/state_core/auth/oauth_common/loopback.py
import asyncio
import socket
from urllib.parse import urlparse, parse_qs

# Public Google sign-in result pages — match gemini-cli reference
SIGN_IN_SUCCESS_URL = "https://developers.google.com/gemini-code-assist/auth_success_gemini"
SIGN_IN_FAILURE_URL = "https://developers.google.com/gemini-code-assist/auth_failure_gemini"


def allocate_loopback_port() -> int:
    """Bind 127.0.0.1:0, read assigned port, close. Tiny TOCTOU window
    is acceptable on a single-user dev machine (matches gemini-cli)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


async def wait_for_oauth_callback(
    port: int,
    expected_state: str,
    *,
    timeout: float = 300.0,        # 5-min user attention budget
) -> str:
    """Listen on 127.0.0.1:{port}, accept ONE GET /oauth2callback?code=...&state=...,
    validate state (CSRF), redirect browser to SUCCESS_URL or FAILURE_URL,
    return the auth code. Raises asyncio.TimeoutError, AuthLoginError on
    state mismatch or error param.
    """
    code_future: asyncio.Future[str] = asyncio.get_event_loop().create_future()

    async def handle(reader, writer):
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            # parse "GET /oauth2callback?code=...&state=... HTTP/1.1"
            parts = request_line.decode("ascii", errors="replace").split(" ")
            if len(parts) < 2:
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                return
            url = urlparse(parts[1])
            qs = parse_qs(url.query)
            err = qs.get("error", [None])[0]
            code = qs.get("code", [None])[0]
            state = qs.get("state", [None])[0]
            if err:
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                if not code_future.done():
                    code_future.set_exception(
                        AuthLoginError(f"OAuth callback returned error: {err}")
                    )
                return
            if state != expected_state:                  # CSRF — RFC 6749 §10.12
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                if not code_future.done():
                    code_future.set_exception(
                        AuthLoginError("OAuth state mismatch (CSRF check failed)")
                    )
                return
            if not code:
                _respond_redirect(writer, SIGN_IN_FAILURE_URL)
                if not code_future.done():
                    code_future.set_exception(
                        AuthLoginError("OAuth callback missing 'code' param")
                    )
                return
            _respond_redirect(writer, SIGN_IN_SUCCESS_URL)
            if not code_future.done():
                code_future.set_result(code)
        finally:
            await reader.read(8192)                       # drain trailing headers
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, "127.0.0.1", port)
    try:
        return await asyncio.wait_for(code_future, timeout=timeout)
    finally:
        server.close()
        await server.wait_closed()
```

**Anti-pattern:** Letting the listener accept multiple connections. Browsers prefetch / hint at the redirect URL — only the first request with a non-empty `code` matters; subsequent ones must NOT clobber `code_future`. The `if not code_future.done()` guards are intentional.

### Pattern 2: Independent `state` (NOT verifier) — CSRF, NOT PKCE

**What:** Generate `state` and `code_verifier` as TWO independent strings. `state` defends RFC 6749 §10.12 (CSRF — does the redirect URL come from the same flow we initiated?). `code_verifier` defends RFC 7636 (PKCE — proves possession to the token endpoint).

**When to use:** Google OAuth (this phase) AND Antigravity (Phase 016). NEVER reuse Anthropic's `state == verifier` pattern (P0-8) — that pattern is Anthropic-specific and weakens Google's CSRF protection.

```python
from state_core.auth.oauth_common.pkce import generate_verifier, build_challenge

state = generate_verifier()       # 43-char base64url-no-pad — also valid as state
verifier = generate_verifier()    # SECOND independent call
challenge = build_challenge(verifier)
```

**Why two `secrets.token_urlsafe(32)` calls are fine:** Each call uses `os.urandom(32)` independently; they don't collide. We could use a shorter `state` (16 bytes is plenty for CSRF), but reusing `generate_verifier()` keeps `oauth_common/pkce.py` as the only entropy source — fewer review surfaces.

### Pattern 3: Authorize URL Construction

**What:** Build the URL Google's OAuth server expects, with PKCE S256, the loopback redirect, an independent `state`, and the three Cloud-Platform scopes.

```python
from urllib.parse import urlencode

_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"     # Google's OAuth 2.0 v2 endpoint
_TOKEN_URL = "https://oauth2.googleapis.com/token"                  # Google's token endpoint
_SCOPES = (
    "https://www.googleapis.com/auth/cloud-platform "
    "https://www.googleapis.com/auth/userinfo.email "
    "https://www.googleapis.com/auth/userinfo.profile"
)

# Public Desktop-App OAuth credentials — captured from
# google-gemini/gemini-cli@main packages/core/src/code_assist/oauth2.ts
# (commit-pinned in source comment). Plaintext per P1-3:
#   Google's Desktop App OAuth pattern relies on PKCE + loopback redirect
#   validation, not client_secret confidentiality. Obfuscation (base64/XOR)
#   is REJECTED — AV scanners flag obfuscated literals as malicious, and
#   Google's own gemini-cli ships them plaintext. See PITFALLS P1-3.
_CLIENT_ID = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
_CLIENT_SECRET = "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"

def _build_authorize_url(redirect_uri: str, state: str, challenge: str) -> str:
    qs = urlencode({
        "client_id":             _CLIENT_ID,
        "redirect_uri":          redirect_uri,             # http://127.0.0.1:{port}/oauth2callback
        "response_type":         "code",
        "scope":                 _SCOPES,
        "state":                 state,                    # independent of verifier (CSRF)
        "code_challenge":        challenge,
        "code_challenge_method": "S256",
        "access_type":           "offline",                # MUST — required for refresh_token
        "prompt":                "consent",                # force refresh_token issuance every login
    })
    return f"{_AUTHORIZE_URL}?{qs}"
```

**Why `access_type=offline` AND `prompt=consent`:** Without `access_type=offline`, Google does NOT issue a `refresh_token`. Without `prompt=consent`, Google may skip issuing a refresh_token on subsequent logins for the same account (because the user "already consented"). Both are required for the flow to work reliably the second time the same user logs in. Issue #62 in `google-auth-library-python-oauthlib` documents this; the gemini-cli reference includes both.

### Pattern 4: Token Exchange (`authorization_code` grant)

**What:** POST to Google's token endpoint with the `client_secret` (sent in body), the `code` from the loopback callback, and the `code_verifier` from PKCE. Per-call `httpx.AsyncClient` like Phase 014. Body is `application/x-www-form-urlencoded` (Google's documented preference, unlike Anthropic's JSON).

```python
async def _exchange_code(code: str, verifier: str, redirect_uri: str) -> GoogleTokenResponse:
    body = {
        "code":          code,
        "client_id":     _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "redirect_uri":  redirect_uri,
        "grant_type":    "authorization_code",
        "code_verifier": verifier,
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
        ) as client:
            resp = await client.post(
                _TOKEN_URL,
                data=body,                             # form-urlencoded
                headers={"accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise AuthLoginError(f"token exchange transport: {exc}") from exc

    if resp.status_code >= 400:
        raise AuthLoginError(
            f"token exchange http {resp.status_code}: {resp.text[:500]!r}"
        )
    try:
        return GoogleTokenResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        raise AuthLoginError(f"token exchange response shape: {exc}") from exc
```

### Pattern 5: Refresh via `google.oauth2.credentials.Credentials` (rotation handled)

**What:** Construct a `Credentials` object from the stored `OAuthCredential`, call `.refresh(google.auth.transport.requests.Request())` in a worker thread, and read back `.token`, `.refresh_token`, `.expiry`. The `refresh_token` field on the Credentials object is automatically updated if Google returned a new one; if not, it stays unchanged. We persist `creds.refresh_token` unconditionally to satisfy P2-2.

```python
import asyncio
from google.oauth2.credentials import Credentials as GoogleCredentials
from google.auth.transport.requests import Request as GoogleRequest

async def _refresh_via_google_auth(
    refresh_token: str,
    *,
    expires_in_hint: float | None = None,        # for test injection
) -> tuple[str, str, float]:
    """Returns (new_access, new_refresh, new_expires_epoch).

    new_refresh is the Google-returned refresh token if one was rotated,
    else the original token unchanged. P2-2 compliance.
    """
    creds = GoogleCredentials(
        token=None,                              # forces a refresh
        refresh_token=refresh_token,
        token_uri=_TOKEN_URL,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
        scopes=_SCOPES.split(),
    )
    # google-auth's Request transport is blocking. Run in a worker thread
    # so we don't block the event loop. asyncio.to_thread is 3.9+.
    try:
        await asyncio.to_thread(creds.refresh, GoogleRequest())
    except Exception as exc:                     # google.auth.exceptions.RefreshError, etc.
        raise AuthRefreshError(f"google refresh failed: {exc}") from exc

    # creds.expiry is a naive UTC datetime; convert to epoch float.
    if creds.expiry is None:
        # Google should always return expiry; defensive default to 1h.
        new_expires = (await asyncio.to_thread(time.time)) + 3600.0
    else:
        new_expires = creds.expiry.replace(tzinfo=timezone.utc).timestamp()

    return creds.token, creds.refresh_token or refresh_token, new_expires
```

**Why `creds.refresh_token or refresh_token`:** google-auth's behavior — when Google's response omits `refresh_token`, the Credentials object retains the original. The `or` is defensive belt-and-suspenders for the case where some upstream version sets it to None.

**Why `asyncio.to_thread`:** `Credentials.refresh` is sync (uses `urllib3` via `google.auth.transport.requests.Request`). `to_thread` keeps the event loop responsive. Phase 013 wraps this whole call in `asyncio.wait_for(method.refresh, timeout=15.0)` — well above the 10-15s typical Google response time.

### Pattern 6: HTTP Headers for Outbound API Calls

**What:** `Authorization: Bearer ya29.…` is the canonical Google-API auth header. `cloudcode-pa.googleapis.com` (the Code Assist endpoint that provides Gemini free-tier inference) expects Bearer + an optional `x-goog-user-project` header for quota attribution.

```python
def http_headers(self, cred: Credential) -> dict[str, str]:
    """Return Bearer + optional x-goog-user-project for outbound calls.

    cloudcode-pa.googleapis.com (the Code Assist API serving Gemini
    free-tier inference) expects:
        Authorization: Bearer <access_token>
        x-goog-user-project: <project_id>           # optional, for quota
        Content-Type: application/json              # caller's concern, not ours

    v3 provider-routing wires the actual request; this method only
    surfaces auth-derived headers.
    """
    if not isinstance(cred, OAuthCredential):
        return {}
    headers = {"authorization": f"Bearer {cred.access}"}
    project = cred.extras.get("project_id")
    if project:
        headers["x-goog-user-project"] = project
    return headers
```

**Source:** `gemini-cli/packages/core/src/code_assist/server.ts` — base URL `https://cloudcode-pa.googleapis.com/v1internal`, headers include `Content-Type: application/json` (caller-set) and Bearer (from AuthClient). The `x-goog-user-project` header pattern is documented in Google Cloud's quota guide; gemini-cli omits it (issue #26105 confirms it should be included for proper quota attribution).

### Pattern 7: Token-Shape Sniffer

**What:** First branch of the discriminator. Google access tokens begin `ya29.` — that's the canonical prefix.

```python
def is_token(self, value: str) -> bool:
    """First branch of token-shape sniffer (P1-1).

    Google OAuth access tokens begin `ya29.` (example fixture in
    base.py docstring). Refresh tokens begin `1//`. We sniff on
    access tokens since http_headers consumes the access token.
    """
    return value.startswith("ya29.")
```

### Anti-Patterns to Avoid

- **Reusing `state == verifier` (Anthropic pattern):** Google does not require it; reusing the verifier as state weakens CSRF protection on the loopback redirect. P0-8 is Anthropic-specific.
- **Acquiring a filelock in `refresh()`:** Phase 013 already wraps it. Double-locking deadlocks (refresh.py rule 9).
- **Calling `Credentials.refresh()` in the event loop (sync):** Blocks every other coroutine for the duration. Always wrap in `asyncio.to_thread`.
- **Persisting `creds.refresh_token` only when changed:** P2-2 says persist it on EVERY refresh, even if unchanged. Treat it as opaque — we don't compare; we always write.
- **Storing the client_secret in an environment variable or external file:** It's a public Desktop-App credential per Google's guidance. Environment-variable indirection adds a footgun (forgotten env var → silent failure) without security benefit. Source-of-truth is the Python module constant.
- **Letting the loopback listener accept multiple requests:** Browsers prefetch the redirect target. Future-result pattern (`if not code_future.done(): set_result(...)`) ensures only the first valid GET wins.
- **Hard-coding port 1455 (or any specific port):** Two `state` CLIs running concurrently → second one fails on `EADDRINUSE`. Port 0 + read-back is race-tolerant.
- **Reading `time.time()` inside `is_expired`:** AUTH-09 / P0-7 — `now` MUST be a parameter. Delegate to `is_expired_buffered` from `state_core.auth.refresh`.
- **Using `Field(repr=False)` only on `access_token`:** Both `access_token` AND `refresh_token` are secrets. Both need it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth refresh-token exchange | Hand-rolled httpx POST + JSON parsing | `google.oauth2.credentials.Credentials.refresh()` driven by `asyncio.to_thread` | Google's library handles refresh-token rotation correctly (preserves old token if response omits a new one, P2-2). Hand-rolling re-introduces the rotation bug. |
| PKCE verifier / challenge | Custom RNG + manual base64 padding | `oauth_common/pkce.py` (already shipped Phase 014) | RFC 7636 compliance verified by 014 tests. |
| Loopback HTTP server | `http.server.HTTPServer` (sync) or `wsgiref.simple_server` | `asyncio.start_server` (in `oauth_common/loopback.py`) | sync servers block the event loop; asyncio is asyncio-native and handles browser prefetch correctly. |
| `InstalledAppFlow.run_local_server()` | Calling it directly | Manual loopback flow with `oauth_common/loopback.py` | `run_local_server` is sync, hard-codes state, blocks the event loop. Manual flow is auditable + asyncio-native + sharable with Phase 016. |
| Port allocation | Trying ports 1455..1465 in a loop | `socket.bind(('127.0.0.1', 0))` + `getsockname()[1]` | Kernel-allocated ports avoid race conditions and don't require firewall rules for specific ports. |
| Refresh-token rotation tracking | Comparing old vs new refresh tokens before persisting | Always persist `creds.refresh_token or original_refresh_token` | Treating rotation as opaque is simpler and correct. P2-2 prevention. |
| Datetime → epoch conversion for expiry | Manual UTC offset math on `creds.expiry` | `creds.expiry.replace(tzinfo=timezone.utc).timestamp()` | google-auth returns naive UTC datetimes (documented). The replace+timestamp is the documented pattern. |
| Browser auto-open | Custom subprocess invocation | `print(authorize_url)` in 015; `webbrowser.open(url)` in Phase 022 | Phase 022 owns the polished CLI UX (browser open + `--no-browser` flag). 015 ships the manual print fallback so headless / SSH works. |
| `client_secret` obfuscation | base64, XOR, env var indirection | Plaintext source constant + rationale comment | P1-3: AV scanners flag obfuscated literals; Google's own gemini-cli ships plaintext. |

**Key insight:** The "interesting" parts of this phase are (a) the loopback listener (~80 LOC, asyncio-native, shared with 016) and (b) the rotation-aware refresh (delegated to google-auth). Everything else is constants, URL building, and the AuthMethod Protocol shape — same pattern as Phase 014.

## Common Pitfalls

(Each pitfall maps to a P0/P1 in `.planning/research/PITFALLS.md` where applicable.)

### Pitfall 1: client_secret obfuscation (P1-3)
**What goes wrong:** Developer tries to "be safe" by base64-encoding or XOR-ing the client_secret. AV scanners flag the obfuscated literal as malicious; corporate users' installs get quarantined; PyPI auto-checks may reject the package.
**Why it happens:** Intuition says "secrets shouldn't be plaintext in source." Wrong — public Desktop-App OAuth credentials are NOT secrets in the cryptographic sense. PKCE + loopback redirect validation are the actual defenses.
**How to avoid:** Plaintext `_CLIENT_ID` and `_CLIENT_SECRET` constants with a 4-line rationale comment. Document the same rationale in any AUTH.md / project docs Phase 022 produces. Add a structlog warning to login() if anyone monkey-patches them.
**Warning signs:** Snyk/Trivy flags; corporate AV blocks install; PyPI rejects.

### Pitfall 2: Refresh-token rotation silently dropped (P2-2)
**What goes wrong:** Developer's `refresh()` returns `cred.model_copy(update={"access": ..., "expires": ...})` and forgets `"refresh": ...`. Next refresh uses the old refresh token. Google's rotation invalidates the old one — refresh fails with `invalid_grant`, user re-logins.
**Why it happens:** OAuth 2.0 `refresh_token` grants don't always return a new refresh_token. The dev assumes "no new refresh_token = keep using the old one." Sometimes true (Google may keep it valid), sometimes false (Google rotates and the old one is now revoked).
**How to avoid:** Always persist `creds.refresh_token or original_refresh_token`. google-auth's Credentials object already handles this — read from `creds.refresh_token` after `.refresh()` and write that value back. Never compare-and-skip.
**Warning signs:** OAuth works for exactly one refresh cycle then fails; user must re-login; daily 12:00 UTC failures (clustered around access-token expiry).

### Pitfall 3: Missing `access_type=offline` (no refresh_token issued)
**What goes wrong:** `_build_authorize_url` omits `access_type=offline`; Google issues an access token but NO refresh token. `cred.refresh` is `""`; first refresh attempt 400s.
**Why it happens:** It's an authorize-URL parameter, not a token-endpoint parameter. Easy to miss reading the spec.
**How to avoid:** Hard-code `"access_type": "offline"` in `_build_authorize_url`. Pair with `"prompt": "consent"` to force refresh_token issuance even when the user has previously consented. Test asserts both are in the authorize URL via `match_params`.
**Warning signs:** Login succeeds, refresh fails; OAuthCredential.refresh is empty string.

### Pitfall 4: state parameter not validated (CSRF — RFC 6749 §10.12)
**What goes wrong:** Loopback handler accepts the auth code without comparing `qs["state"]` to the value from `_build_authorize_url`. Attacker can craft a malicious URL that injects an attacker-controlled `code` into the user's loopback listener; user's account gets bound to the attacker's auth code.
**Why it happens:** Google's docs emphasize PKCE so much that `state` feels redundant. PKCE proves possession to the TOKEN endpoint; `state` proves the redirect came from US to the LOOPBACK. They're orthogonal defenses.
**How to avoid:** Generate `state` with `secrets.token_urlsafe(32)` (independent of verifier). In the loopback handler, raise `AuthLoginError("OAuth state mismatch")` if `qs.get("state") != expected_state`. Test asserts a wrong-state callback rejects.
**Warning signs:** Successful login flows for users we don't control; account-takeover security report.

### Pitfall 5: Port 0 race vs gemini-cli's `OAUTH_CALLBACK_PORT` env
**What goes wrong:** Two CLIs running concurrently both pick port 0; OS gives them different ports — fine. But if a user sets `OAUTH_CALLBACK_PORT=1455` (gemini-cli compat), a second concurrent CLI sees `EADDRINUSE`.
**Why it happens:** Fixed-port mode disables kernel allocation.
**How to avoid:** Default to port 0. If `STATE_OAUTH_CALLBACK_PORT` env var is set, use that AND raise a clear `AuthLoginError("port {N} already in use; unset STATE_OAUTH_CALLBACK_PORT or close the other process")` on `OSError`.
**Warning signs:** `OSError: [Errno 48] Address already in use`.

### Pitfall 6: Headless / SSH environments break loopback redirect
**What goes wrong:** User runs `state auth login google.gemini_cli` on a remote SSH session. Browser opens locally (their laptop), tries to redirect to `http://127.0.0.1:{port}/oauth2callback` — but THAT port is on the SSH server, not the laptop. Loopback never receives the callback; user re-types the URL into a remote curl, doesn't work either.
**Why it happens:** Loopback flows assume browser and listener share a host.
**How to avoid:** Phase 015 prints the authorize URL for manual paste fallback. Document SSH port-forwarding (`ssh -L {port}:localhost:{port} server`) in Phase 022's `state auth login --help`. Future enhancement: device-code flow as fallback (gemini-cli has one for headless; out of scope here).
**Warning signs:** `asyncio.TimeoutError` on the loopback wait_for; user reports "browser opened but nothing happened."

### Pitfall 7: `expiry` is naive datetime — wrong epoch math
**What goes wrong:** Developer writes `cred.expires = creds.expiry.timestamp()` — which assumes local time. Subsequent `is_expired_buffered` checks fail in any timezone other than UTC.
**Why it happens:** google-auth returns `creds.expiry` as a naive `datetime` in UTC. Calling `.timestamp()` on a naive datetime treats it as LOCAL time.
**How to avoid:** `creds.expiry.replace(tzinfo=timezone.utc).timestamp()` (canonical pattern). Add a unit test that monkey-patches `time.tzset` or sets `TZ=America/Los_Angeles` and verifies the epoch is the same.
**Warning signs:** Tests pass in CI (UTC) but fail on developer laptops; expired-credential checks fire 8h early/late.

### Pitfall 8: account_id sourcing — userinfo vs id_token vs uuid
**What goes wrong:** Developer wants to display "Logged in as <email>" and calls `https://www.googleapis.com/oauth2/v2/userinfo` with the access token. Adds an extra HTTP call to login. If the call fails, login appears to succeed but the user has no `account_id`.
**Why it happens:** Google's token-endpoint response does NOT include account info by default — it returns `id_token` (a JWT) which does, but parsing it requires another dep (`PyJWT` / `google-auth-jwt`).
**How to avoid:** EITHER (a) decode `id_token` payload (already a base64url-no-pad JWT — middle section is JSON with `email`, `sub`, `email_verified`) using stdlib `base64` + `orjson`, NO crypto verification needed (we just trust Google issued it; signature verification is a v3 nice-to-have); OR (b) make ONE userinfo HTTP call with the new access token. Recommendation: stdlib id_token parse — zero extra deps, zero extra HTTP. Map `account_id = id_token_payload["sub"]`, `extras["email"] = id_token_payload["email"]`.
**Warning signs:** `cred.account_id is None`; UI shows "Logged in as None".

### Pitfall 9: kebab-case vs snake_case provider_id collision with Phase 016
**What goes wrong:** Phase 015 uses `"google"` as `provider_id`; Phase 016 also uses `"google"` for Antigravity. AuthVault stores both in the same bucket; Phase 019 round-robin alternates between Gemini and Antigravity tokens — wrong API receives wrong token; 401s.
**Why it happens:** Both are "Google OAuth" flows; instinct is one provider_id.
**How to avoid:** Use `"google.gemini_cli"` for Phase 015 and `"google.antigravity"` for Phase 016. The dot is a namespace separator; AuthVault treats them as completely separate buckets. Phase 011's `base.py` docstring already shows this exact format (`'google.gemini_cli'`).
**Warning signs:** Random 401s after a refresh cycle; multi-cred round-robin selects "wrong" token.

## Code Examples

Verified patterns from official sources.

### 1. Loopback Listener with State Validation

```python
# Source: state-inputs gemini-cli oauth2.ts L515-L600 (port allocation,
# state CSRF check, success/failure redirect).
# Combined with asyncio.start_server docs (verified 2026-04-30).

# In oauth_common/loopback.py — see Pattern 1 above for full skeleton.
```

### 2. Independent state + verifier

```python
# Source: RFC 6749 §10.12 (state for CSRF), RFC 7636 (PKCE).
# Verified 2026-04-30 — Anthropic's state==verifier reuse is provider-specific.

from state_core.auth.oauth_common.pkce import generate_verifier, build_challenge

state = generate_verifier()                # CSRF token (loopback redirect validation)
verifier = generate_verifier()             # PKCE verifier (token-endpoint proof)
challenge = build_challenge(verifier)
# state and verifier are TWO INDEPENDENT 43-char base64url-no-pad strings.
```

### 3. Google Token-Endpoint Body (form-urlencoded)

```python
# Source: https://developers.google.com/identity/protocols/oauth2/native-app
# (verified 2026-04-30 — Google documents form-urlencoded for Desktop apps).

body = {
    "code":          code,
    "client_id":     _CLIENT_ID,
    "client_secret": _CLIENT_SECRET,        # plaintext per P1-3
    "redirect_uri":  f"http://127.0.0.1:{port}/oauth2callback",
    "grant_type":    "authorization_code",
    "code_verifier": verifier,
}
async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
    resp = await client.post(_TOKEN_URL, data=body, headers={"accept": "application/json"})
```

### 4. Pydantic Token-Response Model

```python
# Source: Google OAuth response shape (verified via gemini-cli reference +
# https://developers.google.com/identity/protocols/oauth2 2026-04-30).
# extra="ignore" mirrors Phase 014's forward-compat pattern.

from pydantic import BaseModel, ConfigDict, Field

class GoogleTokenResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token:  str             = Field(repr=False)
    expires_in:    int                                       # seconds-from-now (wire shape)
    refresh_token: str | None      = Field(default=None, repr=False)  # may be absent on refresh response
    scope:         str | None      = None
    token_type:    str | None      = None                    # always "Bearer" in practice
    id_token:      str | None      = Field(default=None, repr=False)  # JWT — parse for account_id

class _GoogleIdTokenPayload(BaseModel):
    """Subset of OpenID Connect ID-Token claims we extract for account_id."""
    model_config = ConfigDict(extra="ignore")
    sub:            str                                       # stable user identifier
    email:          str | None = None
    email_verified: bool | None = None
```

### 5. id_token Parsing (stdlib only — no PyJWT dep)

```python
# Source: RFC 7519 §3 (compact serialization). We only need to read the
# payload; signature verification is deferred to v3 (we trust Google's TLS).

import base64
import orjson

def _parse_id_token_payload(id_token: str) -> _GoogleIdTokenPayload:
    """Parse a Google id_token JWT payload — no signature verification.

    JWT format: <header_b64url>.<payload_b64url>.<signature_b64url>
    Each part is base64url-no-pad. We pad with '=' to length % 4 == 0
    before decoding (Python's b64decode requires padding; b64url accepts it).
    """
    parts = id_token.split(".")
    if len(parts) != 3:
        raise AuthLoginError(f"id_token not a 3-part JWT: {len(parts)} parts")
    payload_b64 = parts[1]
    pad = "=" * (-len(payload_b64) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + pad)
        payload_json = orjson.loads(payload_bytes)
    except Exception as exc:
        raise AuthLoginError(f"id_token payload parse: {exc}") from exc
    return _GoogleIdTokenPayload.model_validate(payload_json)
```

**Why no signature verification:** We're not validating an ID token issued by a third party — we just received it over TLS from Google's token endpoint. Trusting `tls + token_uri == accounts.google.com` is sufficient at this layer. v3 inference routing can add `google.oauth2.id_token.verify_oauth2_token` if needed; for `account_id` extraction, the payload claim is fine.

### 6. Refresh Path with Rotation

```python
# Source: google-auth docs https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html
# (verified 2026-04-30) — Credentials.refresh updates .token, .refresh_token, .expiry in place.

import asyncio
import time
from datetime import timezone

from google.oauth2.credentials import Credentials as GoogleCredentials
from google.auth.transport.requests import Request as GoogleRequest
from google.auth.exceptions import RefreshError

class GoogleGeminiAuth:
    provider_id: str = "google.gemini_cli"

    async def refresh(self, cred: Credential) -> Credential:
        if not isinstance(cred, OAuthCredential):
            raise TypeError(f"GoogleGeminiAuth.refresh requires OAuthCredential, got {type(cred).__name__}")

        creds = GoogleCredentials(
            token=None,
            refresh_token=cred.refresh,
            token_uri=_TOKEN_URL,
            client_id=_CLIENT_ID,
            client_secret=_CLIENT_SECRET,
            scopes=_SCOPES.split(),
        )
        try:
            await asyncio.to_thread(creds.refresh, GoogleRequest())
        except RefreshError as exc:
            raise AuthRefreshError(f"refresh rejected: {exc}") from exc
        except Exception as exc:                          # transport, TLS, parse
            raise AuthRefreshError(f"refresh transport: {exc}") from exc

        # P2-2: persist NEW refresh_token (rotation), or fall back to old.
        new_refresh = creds.refresh_token or cred.refresh

        # Naive UTC datetime → epoch float (Pitfall 7).
        if creds.expiry is None:
            new_expires = time.time() + 3600.0
        else:
            new_expires = creds.expiry.replace(tzinfo=timezone.utc).timestamp()

        return cred.model_copy(update={
            "access":  creds.token,
            "refresh": new_refresh,
            "expires": new_expires,
        })
```

### 7. http_headers + provider_id Sniffer

```python
class GoogleGeminiAuth:
    provider_id: str = "google.gemini_cli"

    def is_token(self, value: str) -> bool:
        # Google access tokens begin "ya29.". Refresh tokens begin "1//".
        # Each provider owns its own sniffer (PITFALLS Pitfall 5).
        return value.startswith("ya29.")

    def is_expired(self, cred: Credential, now: float) -> bool:
        # Delegate to Phase 013 — never duplicate buffer math (P0-7).
        return is_expired_buffered(cred, now)

    def http_headers(self, cred: Credential) -> dict[str, str]:
        # Bearer for inference; x-goog-user-project iff project_id in extras.
        if not isinstance(cred, OAuthCredential):
            return {}
        headers = {"authorization": f"Bearer {cred.access}"}
        project = cred.extras.get("project_id")
        if project:
            headers["x-goog-user-project"] = project
        return headers
```

### 8. pytest-httpx Refresh-Rotation Test

```python
# Source: colin-b.github.io/pytest_httpx (verified 2026-04-28 in 014).
# This test asserts P2-2: rotated refresh_token replaces old.

import pytest
from pytest_httpx import HTTPXMock

@pytest.mark.asyncio
async def test_refresh_persists_rotated_refresh_token(httpx_mock: HTTPXMock) -> None:
    """P2-2: when Google returns a NEW refresh_token, we persist it."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        match_content=b"client_id=681255809395-...",       # form-urlencoded match
        json={
            "access_token":  "ya29.NEW-FIXTURE",
            "expires_in":    3599,
            "refresh_token": "1//ROTATED-FIXTURE",         # NEW refresh — must persist
            "scope":         "https://www.googleapis.com/auth/cloud-platform",
            "token_type":    "Bearer",
        },
    )
    old = OAuthCredential(
        access="ya29.OLD",
        refresh="1//OLD-FIXTURE",
        expires=0.0,
        provider_id="google.gemini_cli",
    )
    new = await GoogleGeminiAuth().refresh(old)
    assert new.refresh == "1//ROTATED-FIXTURE"             # P2-2 satisfied
    assert new.access  == "ya29.NEW-FIXTURE"


@pytest.mark.asyncio
async def test_refresh_preserves_unrotated_refresh_token(httpx_mock: HTTPXMock) -> None:
    """P2-2 inverse: when Google omits refresh_token, we keep the old one."""
    httpx_mock.add_response(
        method="POST",
        url="https://oauth2.googleapis.com/token",
        json={
            "access_token":  "ya29.NEW-FIXTURE",
            "expires_in":    3599,
            # NO refresh_token in response
            "token_type":    "Bearer",
        },
    )
    old = OAuthCredential(
        access="ya29.OLD",
        refresh="1//PRESERVED-FIXTURE",
        expires=0.0,
        provider_id="google.gemini_cli",
    )
    new = await GoogleGeminiAuth().refresh(old)
    assert new.refresh == "1//PRESERVED-FIXTURE"           # preserved
```

**Note on the test pattern:** google-auth's `Credentials.refresh` uses its own `urllib3` transport, not httpx. To unit-test rotation logic via `pytest-httpx`, we have TWO options:
- **Option A (preferred):** Replace the refresh implementation with a hand-rolled httpx POST (mirrors Phase 014). We lose google-auth's polished error handling but gain `pytest-httpx` testability.
- **Option B:** Mock `GoogleCredentials.refresh` directly via `monkeypatch.setattr` on the `google.oauth2.credentials.Credentials` class.

**Recommendation:** Option A. Hand-roll the refresh httpx POST, and apply the rotation logic (`response.refresh_token or original`) inline. This trades google-auth's Credentials class for ~20 LOC of explicit code that's easier to test and matches Phase 014's pattern. Use google-auth ONLY for the `Credentials.expiry` datetime parsing if needed (or skip it entirely and compute `expires = now + expires_in`). Update Pattern 5 accordingly during planning.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OOB (out-of-band) redirect URI (`urn:ietf:wg:oauth:2.0:oob`) | Loopback redirect (`http://127.0.0.1:port/`) | Google deprecated OOB Oct 2022 | Forces all desktop OAuth flows to use loopback + PKCE. |
| Fixed-port loopback redirect | Port 0 + kernel allocation | RFC 8252 §7.3 best practice | Avoids `EADDRINUSE` races; multi-instance safe. |
| `gcloud auth application-default login` for desktop apps | Per-app OAuth client + cached creds | Project-isolation best practice | Each tool gets its own Cloud-Platform consent prompt. |
| Storing refresh tokens unencrypted in `~/.gemini/oauth_creds.json` | Same (per gemini-cli reference) — chmod 0600 | gemini-cli reference (current) | Our `auth.json` already does chmod 0600 (Phase 012). |
| `wsgiref.simple_server` for loopback | `asyncio.start_server` for loopback | asyncio maturity (3.7+) | Asyncio-native; non-blocking; testable via `pytest-asyncio`. |

**Deprecated / outdated in this domain:**
- `urn:ietf:wg:oauth:2.0:oob` — fully deprecated October 2022.
- Implicit grant flow for desktop apps — superseded by authorization code + PKCE.
- `gcloud auth application-default login` for end-user desktop tools — replaced by per-app OAuth client.

## Open Questions (RESOLVED)

1. **Should refresh use google-auth or hand-rolled httpx?**
   - What we know: google-auth handles rotation correctly out-of-box. But it requires `asyncio.to_thread` and is not directly mockable via `pytest-httpx`.
   - What's unclear: which is cleaner long-term — leaning on google-auth for the polished refresh logic, or hand-rolling for testability + symmetry with Phase 014.
   - Recommendation: **Hand-roll the refresh** with an explicit `creds.refresh_token or original` rotation rule. Tradeoff is ~30 LOC of httpx + Pydantic vs ~5 LOC of google-auth + `asyncio.to_thread`. The 30-LOC version is testable via `pytest-httpx`, asymmetry-free with Phase 014, and the rotation rule is auditable in source. Document in `google_gemini.py` why we chose this path. (See Pattern 6 / §8 test-pattern note.)

2. **Should we ship the userinfo HTTP call OR id_token parse?**
   - What we know: id_token parse is zero-deps + zero-network; userinfo call costs +1 HTTP request but returns guaranteed-current email. id_token's `email` is what was on the account at issue time.
   - What's unclear: which the team prefers for `extras["email"]` UX.
   - Recommendation: **id_token parse** — zero-deps, zero-network, and the rare email change is acceptable until next refresh.

3. **Headless / SSH support — paste flow fallback?**
   - What we know: Loopback breaks on remote sessions; gemini-cli has a device-code fallback (out of scope for AUTH-04 / Phase 017 territory).
   - What's unclear: whether to ship a `--no-loopback` paste flow (mimic Phase 014's pattern) for headless users in 015 or defer to 022.
   - Recommendation: **Defer to Phase 022** — 015 ships loopback only; 022 wires `--no-browser` + paste fallback + ssh-port-forward hint into the polished CLI.

4. **Exception module factoring — inline vs `state_core.auth.errors`?**
   - What we know: Phase 014 left `AuthError`/`AuthLoginError`/`AuthRefreshError` inline in `providers/anthropic.py` and noted "promote to `state_core.auth.errors` only when phase 015 lands and confirms it wants the same hierarchy."
   - What's unclear: 015 here. We DO want the same hierarchy (`AuthError` → `AuthLoginError`, `AuthRefreshError`), minus `StealthRejected` (Anthropic-specific).
   - Recommendation: **Promote to `state_core.auth.errors`** during 015's planning. Move `AuthError`, `AuthLoginError`, `AuthRefreshError` to the shared module; keep `StealthRejected` inline in `anthropic.py` (truly provider-specific). Update 014's imports as part of this phase's planning. This is the YAGNI threshold satisfied — second consumer with same need.

5. **`provider_id` value: `"google.gemini_cli"` vs `"google.gemini-cli"` vs `"gemini"`?**
   - What we know: `base.py` docstring shows `'google.gemini_cli'` (snake_case after dot).
   - What's unclear: whether the dot+snake_case is actually the canonical project convention.
   - Recommendation: **Use `"google.gemini_cli"` exactly as shown in `base.py` docstring.** Phase 016 uses `"google.antigravity"`. Document in CONTEXT-update during planning.

6. **`x-goog-user-project` header — required or optional?**
   - What we know: gemini-cli omits it by default (issue #26105 documents the missing header → 403 errors). When `GOOGLE_CLOUD_PROJECT` env is set OR Cloud Project is selected, it should be sent for proper quota attribution.
   - What's unclear: whether 015 should default-set it from any heuristic, or wait for v3 routing to provide it.
   - Recommendation: **Optional, sourced from `cred.extras["project_id"]`.** Phase 015's `http_headers` returns it iff `extras["project_id"]` is truthy. Phase 022 CLI exposes `state auth login google.gemini_cli --project-id PROJECT` to populate the field. v3 routing reads it.

## Validation Architecture

> Phase config has `workflow.nyquist_validation: true` — section is included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest>=8.4.0` + `pytest-asyncio>=1.3.0` + `pytest-httpx>=0.35` + `pytest-mock>=3.14` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `pytest tests/auth/oauth_common/test_loopback.py tests/auth/providers/test_google_gemini.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| AUTH-02 | `GoogleGeminiAuth()` structurally satisfies `state_core.auth.base.AuthMethod` | unit | `pytest tests/auth/providers/test_google_gemini.py::test_satisfies_authmethod_protocol -x` | ❌ Wave 0 |
| AUTH-02 / P1-3 | `_CLIENT_ID` and `_CLIENT_SECRET` are PLAINTEXT module constants (no base64/XOR/env-var indirection) | unit | `pytest tests/auth/providers/test_google_gemini.py::test_client_credentials_plaintext -x` | ❌ Wave 0 |
| AUTH-02 | `provider_id == "google.gemini_cli"` | unit | `pytest tests/auth/providers/test_google_gemini.py::test_provider_id_dotted -x` | ❌ Wave 0 |
| AUTH-02 / P1-1 | `is_token()` returns True for `ya29.` access tokens, False for others | unit | `pytest tests/auth/providers/test_google_gemini.py::test_is_token_ya29_prefix -x` | ❌ Wave 0 |
| AUTH-02 / P0-7 | `is_expired(cred, now)` delegates to `is_expired_buffered` (5-min buffer at AuthMethod layer) | unit | `pytest tests/auth/providers/test_google_gemini.py::test_is_expired_uses_300s_buffer -x` | ❌ Wave 0 |
| AUTH-02 | `http_headers()` returns Bearer + (optional) `x-goog-user-project` from `extras["project_id"]` | unit | `pytest tests/auth/providers/test_google_gemini.py::test_http_headers_bearer_and_optional_project -x` | ❌ Wave 0 |
| AUTH-02 | Authorize URL contains `access_type=offline`, `prompt=consent`, `code_challenge_method=S256`, `state=<independent-of-verifier>`, the three Cloud-Platform scopes | unit | `pytest tests/auth/providers/test_google_gemini.py::test_authorize_url_shape -x` | ❌ Wave 0 |
| AUTH-02 | Token POST URL == `https://oauth2.googleapis.com/token`; body is form-urlencoded with `code`, `client_id`, `client_secret`, `redirect_uri`, `grant_type=authorization_code`, `code_verifier` | unit | `pytest tests/auth/providers/test_google_gemini.py::test_token_post_form_urlencoded_shape -x` | ❌ Wave 0 |
| AUTH-02 / P2-2 | Refresh response with NEW `refresh_token` → new value persisted in `OAuthCredential.refresh` | unit | `pytest tests/auth/providers/test_google_gemini.py::test_refresh_persists_rotated_refresh_token -x` | ❌ Wave 0 |
| AUTH-02 / P2-2 | Refresh response WITHOUT `refresh_token` → original value preserved in `OAuthCredential.refresh` | unit | `pytest tests/auth/providers/test_google_gemini.py::test_refresh_preserves_unrotated_refresh_token -x` | ❌ Wave 0 |
| AUTH-02 | `id_token` parse extracts `account_id` from JWT `sub` claim and `extras["email"]` from `email` claim | unit | `pytest tests/auth/providers/test_google_gemini.py::test_id_token_parse_account_email -x` | ❌ Wave 0 |
| AUTH-02 | Loopback listener accepts ONE valid GET `/oauth2callback?code=...&state=...` and returns the code | unit | `pytest tests/auth/oauth_common/test_loopback.py::test_loopback_accepts_valid_callback -x` | ❌ Wave 0 |
| AUTH-02 / RFC 6749 §10.12 | Loopback listener REJECTS callback with mismatched `state` (CSRF defense) | unit | `pytest tests/auth/oauth_common/test_loopback.py::test_loopback_rejects_state_mismatch -x` | ❌ Wave 0 |
| AUTH-02 | Loopback listener REJECTS callback with `error=` query param (user denied consent) | unit | `pytest tests/auth/oauth_common/test_loopback.py::test_loopback_rejects_error_param -x` | ❌ Wave 0 |
| AUTH-02 | Loopback listener responds with 302 redirect to `SIGN_IN_SUCCESS_URL` on success and `SIGN_IN_FAILURE_URL` on error | unit | `pytest tests/auth/oauth_common/test_loopback.py::test_loopback_redirects_to_google_pages -x` | ❌ Wave 0 |
| AUTH-02 | Port allocation via `socket.bind(('127.0.0.1', 0))` returns ephemeral port; second call returns DIFFERENT port | unit | `pytest tests/auth/oauth_common/test_loopback.py::test_port_allocation_ephemeral -x` | ❌ Wave 0 |
| AUTH-02 / Pitfall 7 | `expiry` UTC datetime → epoch conversion is timezone-invariant (test under `TZ=America/Los_Angeles`) | unit | `pytest tests/auth/providers/test_google_gemini.py::test_expiry_epoch_timezone_invariant -x` | ❌ Wave 0 |
| AUTH-02 | `state` and `verifier` are TWO INDEPENDENT strings (not `state == verifier`) — auth URL has `state` ≠ verifier | unit | `pytest tests/auth/providers/test_google_gemini.py::test_state_and_verifier_independent -x` | ❌ Wave 0 |
| AUTH-02 | `python -m state_core.auth.providers.google_gemini login` runs without ImportError (smoke) | unit | `pytest tests/auth/providers/test_google_gemini.py::test_module_main_imports -x` | ❌ Wave 0 |
| AUTH-02 | Refresh on `ApiKeyCredential` raises `TypeError` (caller programming error) | unit | `pytest tests/auth/providers/test_google_gemini.py::test_refresh_rejects_apikey -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/auth/oauth_common/test_loopback.py tests/auth/providers/test_google_gemini.py -x`
- **Per wave merge:** `pytest tests/auth/ -x`
- **Phase gate:** `pytest -x` (full suite green) before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `tests/auth/oauth_common/test_loopback.py` — covers AUTH-02 loopback listener primitives (5 rows above).
- [ ] `tests/auth/providers/test_google_gemini.py` — RED stubs for the 15 google-gemini-specific rows above.
- [ ] Optional fixtures in `tests/auth/providers/conftest.py` — fake id_token JWT (3-part base64url-no-pad with known payload), fake `ya29.…` access token, fake `1//…` refresh token, monkeypatched `secrets.token_urlsafe` for deterministic state/verifier, mock loopback callback simulator.
- [ ] No new framework / no new dependency installs — `pytest`, `pytest-asyncio`, `pytest-httpx`, `pytest-mock` already in `pyproject.toml`. `google-auth>=2.35` and `google-auth-oauthlib>=1.2` already pinned (still imported as a dep marker even though we hand-roll refresh — see Open Q1).

## Sources

### Primary (HIGH confidence)

- **`.planning/research/STACK.md`** — `google-auth>=2.35`, `google-auth-oauthlib>=1.2`, `httpx>=0.28.1`, `pydantic>=2.13.2`, `filelock>=3.20.3`, `cryptography>=43.0`, `pytest-httpx>=0.35` pins.
- **`.planning/research/PITFALLS.md`** — P0-7 (5-min buffer at AuthMethod layer), P0-13 (chmod 0600), P0-14 (token redactor), P1-1 (token-shape sniffer per provider), P1-3 (plaintext client_secret rationale), P1-4 (free-tier 429 quota), P2-2 (refresh-token rotation persistence).
- **`.state-inputs/gsd2-auth-analysis.md`** — gsd-pi `google-gemini-cli.ts` strategy + plaintext-credentials rationale ("Google's OAuth implementation requires client_secret for Desktop App OAuth clients even though it cannot be kept secret in distributed applications").
- **`https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/code_assist/oauth2.ts`** — canonical reference. Verbatim:
  - `OAUTH_CLIENT_ID = '681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com'`
  - `OAUTH_CLIENT_SECRET = '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'`
  - `OAUTH_SCOPE = ['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']`
  - `SIGN_IN_SUCCESS_URL = 'https://developers.google.com/gemini-code-assist/auth_success_gemini'`
  - `SIGN_IN_FAILURE_URL = 'https://developers.google.com/gemini-code-assist/auth_failure_gemini'`
  - `cacheCredentials` writes JSON to `Storage.getOAuthCredsPath()` with `mode: 0o600` (matches our Phase 012 `_atomic_write` exactly — useful for Phase 021 first-run import).
  - `client.on('tokens', async (tokens) => { ... await cacheCredentials(tokens); ...})` — rotation handler: persists EVERY tokens event, regardless of whether refresh_token changed (P2-2 ground truth).
  - State validation via `qs.get('state') !== state` (CSRF defense in loopback handler).
- **`https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/code_assist/server.ts`** — `https://cloudcode-pa.googleapis.com/v1internal` API base; methods `:loadCodeAssist`, `:generateContent`, `:streamGenerateContent`. Bearer auth via `AuthClient` dependency. (For v3 inference routing — informational only for 015.)
- **`https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html`** — `Credentials.refresh(request)` signature; `.token`, `.refresh_token`, `.expiry`, `.id_token`, `.token_uri`, `.client_id`, `.client_secret`, `.scopes` exposed; `from_authorized_user_info(info, scopes=None)` and `to_json(strip=None)` for round-trip; refresh updates token + refresh_token + expiry in place. (Verified 2026-04-30.)
- **`https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html`** — `InstalledAppFlow.from_client_config()` + `run_local_server(host='localhost', port=8080, success_message=..., open_browser=True, redirect_uri_trailing_slash=True, bind_addr=None, authorization_prompt_message=..., timeout_seconds=None, token_audience=None, browser=None)` returns `google.oauth2.credentials.Credentials`. PKCE auto-generated by default (`autogenerate_code_verifier=True`). (Verified 2026-04-30.)
- **`https://developers.google.com/identity/protocols/oauth2/native-app`** — Desktop-App OAuth 2.0 spec (loopback IP redirect, PKCE recommended, `access_type=offline`, `prompt=consent`).
- **`https://developers.google.com/identity/protocols/oauth2/resources/loopback-migration`** — Loopback IP migration guide (RFC 8252; deprecated for Android/Chrome-app/iOS, recommended for desktop).
- **In-tree code (HIGH — read directly):**
  - `src/state_core/auth/base.py` — `OAuthCredential`, `AuthMethod` Protocol, secret-hygiene rules, `account_id`/`extras` semantics, sniffer guidance.
  - `src/state_core/auth/store.py` — `AuthVault.providers` array-shape invariant + `chmod 0o600` enforcement.
  - `src/state_core/auth/refresh.py` — `is_expired_buffered`, `refresh_credential` 15s `wait_for` cap, double-check pattern, "DO NOT acquire your own filelock" rule.
  - `src/state_core/auth/oauth_common/pkce.py` — `generate_verifier()` + `build_challenge()` (reused unchanged from 014).
  - `src/state_core/auth/providers/anthropic.py` — Phase 014 reference: per-call `httpx.AsyncClient`, exception hierarchy, `_to_credential` epoch wire-shape, `python -m` argparse stub.
  - `.planning/milestones/v2/phases/014-anthropic-oauth-provider/014-RESEARCH.md` — full Phase 014 research, code-example patterns, validation-table format.

### Secondary (MEDIUM confidence — single source or community)

- **`https://medium.com/@developer_29635/...`** (Colin Hobday) — `flow.run_local_server(port=0)` + `creds.to_json()` typical pattern; community confirmation of port-0 usage.
- **`https://medium.com/@fourdollars/conquering-google-login-for-gemini-cli-on-headless-servers-3e9d2649790f`** — confirms loopback breaks on headless/SSH; ssh-port-forward workaround.
- **`https://github.com/jenslys/opencode-gemini-auth`** — opencode plugin that mirrors gemini-cli OAuth (informational; we don't import).
- **`https://github.com/google-gemini/gemini-cli/issues/26105`** — confirms `x-goog-user-project` quota header bug; informs our `extras["project_id"]` design.
- **`https://github.com/googleapis/google-auth-library-python-oauthlib/issues/62`** — `prompt=consent` required to force `refresh_token` on subsequent logins.
- **`https://deepwiki.com/google-gemini/gemini-cli/2.2-authentication`** — independent summary of the gemini-cli auth surface.

### Tertiary (LOW confidence — flagged for validation)

- Cache-file path `~/.gemini/oauth_creds.json` — used by Phase 021 first-run import. Confirmed via gemini-cli reference (`Storage.getOAuthCredsPath()`) but the actual constant is in a different file we didn't fetch. Phase 021 should re-verify.
- The exact `expires_in` value Google returns (typically 3599 = 1 hour). Most documentation says 3600; gemini-cli treats it as opaque. We use whatever `expires_in` Google returns; AUTH-09's 5-min buffer is the safety net.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep is already pinned in `pyproject.toml`; google-auth API verified against current docs.
- Architecture (manual loopback flow, state ≠ verifier, refresh rotation): HIGH — direct reads of gemini-cli reference + Google's official OAuth Desktop-App spec + RFC 8252.
- OAuth constants (CLIENT_ID, CLIENT_SECRET, SCOPES, SIGN_IN_*_URL): HIGH — verbatim from gemini-cli `oauth2.ts` (current main branch as of 2026-04-30 retrieval).
- Refresh-rotation semantics: HIGH — google-auth official docs confirm `Credentials.refresh` updates `.refresh_token` in place when Google returns one; gemini-cli reference confirms unconditional persistence.
- Pitfalls: HIGH — direct read of `.planning/research/PITFALLS.md` + cross-referenced gemini-cli + Google docs.
- v3 inference-routing API host (`cloudcode-pa.googleapis.com/v1internal`): MEDIUM — informational only for 015; v3 will re-verify.

**Research date:** 2026-04-30
**Valid until:** 2026-07-30 (90 days for the architecture findings; the gemini-cli OAuth constants need re-verification on every gemini-cli major release — track via `tools/check-gemini-cli-headers.py` analogous to Phase 022's claude-cli capture).

## RESEARCH COMPLETE
