# Phase 014: Anthropic OAuth provider (stealth flow) — Research

**Researched:** 2026-04-28
**Domain:** OAuth 2.0 Authorization-Code + PKCE (no callback server) + byte-for-byte stealth identity headers; first concrete `AuthMethod` implementation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Module layout & PKCE sharing**
- Single file: `src/state_core/auth/providers/anthropic.py` (~250 LOC, mirrors milady's `claude-code-stealth.mjs` shape; byte-diffable against `.state-inputs/claude-oauth.md`).
- Shared PKCE extracted NOW: `src/state_core/auth/oauth_common/pkce.py` — stdlib only (`secrets`, `hashlib.sha256`, `base64.urlsafe_b64encode`), ~30 LOC. Lands here so phases 015/016/017 don't copy or block.
- `_CLIENT_ID = base64.b64decode("…").decode()` evaluated at module load (matches spec's "base64-decoded at runtime"; defeats secret scanners on the literal).
- Token response: Pydantic `AnthropicTokenResponse(BaseModel)` with `extra="ignore"` (NOT `forbid`).

**Login UX (Phase 014 only — polished CLI is Phase 022)**
- Two entry points: `async def login() -> OAuthCredential` (programmatic) AND `python -m state_core.auth.providers.anthropic login` (interactive).
- Paste flow: print authorize URL → `getpass.getpass("Paste code#state: ")` (hidden input).
- `login()` ALWAYS appends a new credential — store appends, preserves array shape (AUTH-08 / Phase 019 invariant).
- `account_id` parsed from token-response `account.uuid`; printed as `Logged in as <email_address or uuid>`.

**Stealth headers — pinned values**
```
_CLAUDE_CLI_VERSION = "2.1.92"
_USER_AGENT = f"claude-cli/{_CLAUDE_CLI_VERSION} (external, cli)"
_X_APP = "cli"
_ANTHROPIC_BETA = (
    "claude-code-20250219,oauth-2025-04-20,"
    "interleaved-thinking-2025-05-14,"
    "context-management-2025-06-27,"
    "prompt-caching-scope-2026-01-05,"
    "advanced-tool-use-2025-11-20,"
    "effort-2025-11-24"
)
```
Each constant carries a `# captured 2026-04 from milady-ai/milady#1910 against claude-cli 2.1.92` comment. Cross-verify with our own mitmproxy capture before merge.

**Stealth body mutation (SHIPS in this phase)**
- `def inject_stealth_system_prefix(body: dict) -> dict` — prepends `{"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."}` at `body["system"][0]` if not already present. Handles list / string / missing forms (mirrors milady `addSystemPrefix`).
- URL hardening: append `?beta=true` when not present.
- Defensive: `headers.pop("x-api-key", None)` before setting Bearer (P0-4 in disguise).

**HTTP client lifecycle**
- Per-call `httpx.AsyncClient` inside `login()` and `refresh()` (`async with httpx.AsyncClient(...) as c:`). No module-level singleton.
- `httpx.Timeout(10.0, connect=5.0)` per call. Aligns with Phase 013's 10s lock budget.
- No retry. No `tenacity`. Failures bubble.
- Exception hierarchy:
  ```python
  class AuthError(Exception): ...
  class AuthLoginError(AuthError): ...        # token exchange failed
  class AuthRefreshError(AuthError): ...      # refresh failed (invalid_grant, network)
  class StealthRejected(AuthError): ...       # 401/403 with stealth-shape signal — header drift
  ```

**Test strategy (Phase 014, in-CI)**
- `pytest-httpx` mock + header-shape assertions. No live-Anthropic CI tests (deferred to Phase 022).
- Asserts every outbound: `Authorization: Bearer sk-ant-oat<fixture>`, exact `user-agent`, exact `x-app`, exact `anthropic-beta`, `?beta=true` in URL, `system[0]` prefix, NO `x-api-key`.

### Claude's Discretion
- Exact ordering of `headers.set()` calls.
- Whether `errors.py` is split into its own module or kept inline (planner decides based on 015–017 sharing).
- Internal helper naming (`_build_authorize_url`, `_exchange_code`).
- structlog event naming for login/refresh observability (constrained only by Phase 020 redactor).
- Test fixture values for fake `sk-ant-oat*` tokens.

### Deferred Ideas (OUT OF SCOPE)
- Polished `state auth login` Typer CLI — Phase 022.
- AUTH-13 captured-header golden-file regression test — Phase 022.
- Multi-cred round-robin selection — Phase 019.
- Structlog token redactor — Phase 020 (this phase relies on `Field(repr=False)` only).
- First-run import from `~/.claude/.credentials.json` — Phase 021 (the `expiresAt` ms→s conversion lives there).
- Inference-call routing through stealth headers — v3 provider routing.
- Daemon-level proactive refresh timer (milady's 60-min systemd timer) — v4+ scheduler.
- Browser auto-open (`webbrowser.open`) — Phase 022 with `--no-browser` flag.
- Token-validation health-check at login — Phase 022.
- Live-against-real-Anthropic CI test (gated by `STATE_TEST_LIVE_ANTHROPIC=1`) — Phase 022.
- Automated traffic-capture / drift-detection capability — own future phase (v2.5 / v3).
- `oauth_common/` extras (shared http client factory, shared error base) — extract iff 015/016/017 want them.
- Pulling milady repo as submodule — rejected (733 MB).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | Anthropic OAuth stealth flow implemented byte-for-byte against `state-inputs/claude-oauth.md` — headers (`user-agent: claude-cli/<ver>`, `x-app: cli`, `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…`), PKCE verifier = OAuth `state`, client_id `9d1c250a-e61b-44d9-88ed-5944d1962f5e`, Bearer for `sk-ant-oat*` | Sections **PKCE Recipe**, **Authorize URL Construction**, **Token Endpoint Shape**, **Stealth Headers**, **Body-Shape Mutation**, **`AnthropicAuth` Class Skeleton**, **Code Examples** §§1–6 below — every primitive AUTH-01 names is materialized as either a constant, a helper, or an asserted test. P0-1..P0-5, P0-7, P0-8 each map to a Validation Architecture row. |

</phase_requirements>

## Summary

Phase 014 is the first concrete `AuthMethod` implementation, and it is also where Anthropic's "subscription-priced" Pro/Max inference is unlocked by perfectly mimicking Claude Code's outbound HTTPS shape. The technical surface is small (PKCE + two HTTP requests + a body-shape mutation), but the byte-for-byte requirement is unforgiving: a single missing header silently downgrades the user to API-key pricing, and a single wrong client_id can trip Anthropic's abuse-detection on the user's account.

The phase splits into three nearly-independent pieces: (a) a 30-LOC stdlib PKCE helper in `oauth_common/pkce.py` shared with phases 015/016/017; (b) a 250-LOC `providers/anthropic.py` containing constants, the `AnthropicAuth` class implementing the `AuthMethod` Protocol, login/refresh implementations, and the body-mutation helper `inject_stealth_system_prefix`; (c) a `python -m` entry-point shim for interactive smoke-testing before the Phase 022 CLI lands. All three lean on stdlib + already-pinned deps (`httpx>=0.28.1`, `pydantic>=2.13.2`, `pytest-httpx>=0.35`); zero new dependencies are needed.

The provider does NOT acquire its own filelock — Phase 013's `refresh_credential` already wraps `AuthMethod.refresh` in a 10s-budgeted `AsyncFileLock` with double-check semantics, so the provider's `refresh()` is a pure HTTP exchange. Per-call `httpx.AsyncClient` (no singleton), no retry layer, and a bounded `Timeout(10.0, connect=5.0)` keep the refresh path well inside the 15s `asyncio.wait_for` cap that Phase 013 enforces.

**Primary recommendation:** Land PKCE first (one Wave 0 file, importable by 015/016/017 in parallel), then the constants + `AnthropicAuth` skeleton (mypy-strict against the Protocol), then login/refresh wired through `pytest-httpx` matchers (`match_url`, `match_headers`, `match_json`, `match_params`) — the matcher API gives byte-for-byte assertions for free, which is exactly the AUTH-13 hook that Phase 022 will grow.

## Standard Stack

### Core (already pinned in `pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.12+ | `secrets`, `hashlib`, `base64.urlsafe_b64encode`, `getpass`, `urllib.parse.urlencode`, `asyncio.run`, `argparse` (or `if __name__`-dispatch) | Zero-dep PKCE + paste UX + `python -m` entrypoint. CLAUDE.md & spec call for stdlib here. |
| `httpx` | `>=0.28.1` | Async HTTP for token exchange + refresh | Already the project's HTTP client; `AsyncClient` + `Timeout` are the right primitives for one-shot calls. |
| `pydantic` | `>=2.13.2` | `AnthropicTokenResponse(BaseModel)` with `extra="ignore"`, optional nested `account` model, `Field(repr=False)` defense | Already the project's data layer; v2's `model_config = ConfigDict(extra="ignore")` is the supported way to allow forward-compatible upstream additions. |
| `filelock` | `>=3.20.3` | Imported transitively via Phase 013's `refresh_credential` — provider does NOT touch it directly | Hard CVE-2026-22701 floor. |
| `structlog` | `>=25.1` | Login/refresh observability | Project-wide logging substrate; Phase 020 will attach the redactor. |

### Supporting (test only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8.4.0` | Test runner | Always. |
| `pytest-asyncio` | `>=1.3.0` | Async test support | Every `login()` / `refresh()` test. |
| `pytest-httpx` | `>=0.35` | `httpx_mock` fixture: `add_response(match_url, match_headers, match_json, match_params)` + `get_request()` introspection | Every header/URL/body shape assertion. |
| `pytest-mock` | `>=3.14` | `monkeypatch.setattr` for `getpass.getpass` in interactive-flow tests | Login-flow test only. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `httpx.AsyncClient` per-call | Module-level singleton client | CONTEXT locked: per-call avoids shutdown choreography + test-isolation pain; pooling is near-zero-value for infrequent auth calls. |
| `getpass.getpass` for paste | `input()` | `input()` echoes the (short-lived) auth code to terminal scrollback. `getpass` hides it — treat in-transit auth code as a transient secret. |
| `ConfigDict(extra="ignore")` | `extra="forbid"` (matches `_CredentialBase`) | Anthropic can add response fields without breaking us. `forbid` would hard-fail on the next undocumented field; `ignore` is forward-compatible. |
| `argparse` for `python -m` | `typer` | Typer is the project CLI — but Phase 022 owns CLI proper. Stdlib `argparse` (or even `sys.argv` `if __name__`-dispatch) keeps Phase 014 free of premature CLI commitment. |
| Tenacity retry layer | None | CONTEXT locked: Phase 013 has a 10s lock budget; retries inside refresh would consume it. Failures bubble; the next caller naturally retries. |

**Installation:** No new dependencies required — every line above is already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

```
src/state_core/auth/
├── __init__.py                           # NO new re-exports (providers intentionally not re-exported)
├── base.py                               # (existing — Phase 011)
├── store.py                              # (existing — Phase 012)
├── refresh.py                            # (existing — Phase 013)
├── oauth_common/                         # NEW (this phase)
│   ├── __init__.py                       # empty (no re-exports — direct module imports)
│   └── pkce.py                           # NEW: generate_verifier(), build_challenge() — stdlib-only ~30 LOC
└── providers/                            # NEW dir (no other phases yet)
    ├── __init__.py                       # empty
    └── anthropic.py                      # NEW: ~250 LOC, see skeleton below
                                          #   includes `if __name__ == "__main__": ...`
                                          #   so `python -m state_core.auth.providers.anthropic login` works

tests/auth/
├── (existing fixtures in conftest.py)
├── providers/
│   └── test_anthropic.py                 # NEW: pytest-httpx assertions
└── oauth_common/
    └── test_pkce.py                      # NEW: PKCE verifier/challenge property tests
```

### Pattern 1: AuthMethod Protocol Implementation (mypy-strict)

**What:** Implement five attributes/methods that satisfy `state_core.auth.base.AuthMethod` structurally. `@runtime_checkable` only proves attribute *presence* — mypy strict catches signature mismatch.

**When to use:** Every concrete provider in phases 014–018.

**Skeleton:**
```python
# src/state_core/auth/providers/anthropic.py
from state_core.auth.base import AuthMethod, OAuthCredential, Credential
from state_core.auth.refresh import is_expired_buffered  # delegate, do not duplicate

class AnthropicAuth:
    """Anthropic OAuth stealth provider (claude-code-20250219).

    Implements state_core.auth.base.AuthMethod structurally.
    Self-check at module load time:
        assert isinstance(AnthropicAuth(), AuthMethod)
    """
    provider_id: str = "anthropic"

    def is_token(self, value: str) -> bool:
        # First branch of the token-shape sniffer (P1-1).
        return value.startswith("sk-ant-oat")

    def is_expired(self, cred: Credential, now: float) -> bool:
        # Delegate to Phase 013's pure helper — never duplicate buffer math (P0-7).
        return is_expired_buffered(cred, now)

    def http_headers(self, cred: Credential) -> dict[str, str]:
        # Returns the FOUR stealth headers + Bearer.
        # NEVER returns x-api-key for OAuth creds (P0-4).
        if not isinstance(cred, OAuthCredential):
            return {}
        return {
            "authorization": f"Bearer {cred.access}",
            "user-agent": _USER_AGENT,
            "x-app": _X_APP,
            "anthropic-beta": _ANTHROPIC_BETA,
        }

    async def login(self) -> OAuthCredential: ...
    async def refresh(self, cred: Credential) -> Credential: ...
```

**Anti-pattern:** Treating `AuthMethod` as a Pydantic field type — see `base.py` warning ("NEVER use AuthMethod as a field type on a Pydantic model — see Pitfall 1, pydantic#10161"). Pass providers as function arguments only.

### Pattern 2: Per-Call AsyncClient with Bounded Timeout

**What:** Construct `httpx.AsyncClient` inside the `async def` that needs it, scoped via `async with`. Pass `timeout` at construction; do NOT pass it again at `.post()`.

**When to use:** Every `login()` / `refresh()` HTTP call.

```python
# Source: https://www.python-httpx.org/async/ (verified 2026-04-28)
async with httpx.AsyncClient(
    timeout=httpx.Timeout(10.0, connect=5.0),
    follow_redirects=False,  # OAuth endpoints never redirect; if they do, it's an attack
) as client:
    response = await client.post(
        _TOKEN_URL,
        json={...},                    # Anthropic accepts application/json (verified)
        headers={"accept": "application/json"},
    )
    response.raise_for_status()        # network/HTTP failures → AuthLoginError/AuthRefreshError at caller
    payload = AnthropicTokenResponse.model_validate(response.json())
```

**Why per-call (CONTEXT-locked):** Auth calls are infrequent; pool-keepalive saves nothing. A module-level singleton would (a) need shutdown choreography across the codebase and (b) leak state across tests. Phase 013 `wait_for` caps total wall-time at 15 s — well above the per-call 10 s timeout.

### Pattern 3: PKCE State == Verifier

**What:** Generate ONE high-entropy string; pass it as PKCE `code_verifier` AND OAuth `state`. The server round-trips `state` and we accept the round-trip as verifier proof. (P0-8 owner.)

**When to use:** ALL Anthropic stealth login flows. NEVER use a separate `state` value.

```python
# src/state_core/auth/oauth_common/pkce.py
import base64
import hashlib
import secrets

def generate_verifier(nbytes: int = 32) -> str:
    """Return a URL-safe PKCE verifier string (RFC 7636 §4.1).

    32 bytes → 43 base64url-without-padding chars. Falls inside the
    [43, 128] length window RFC 7636 mandates.
    """
    # token_urlsafe(32) yields a 43-char string that is already
    # base64url-no-pad — perfect for both the verifier AND the state.
    return secrets.token_urlsafe(nbytes)

def build_challenge(verifier: str) -> str:
    """Return the S256 challenge for *verifier* (RFC 7636 §4.2)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
```

**Anti-pattern:** Generating two independent strings (one for `state`, one for `code_verifier`). Anthropic's server checks `state == verifier` round-trip; mismatched values → `invalid_grant`.

### Pattern 4: Body-Shape Mutation (`addSystemPrefix` in Python)

**What:** Insert `{"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."}` as `body["system"][0]`, handling all three pre-existing shapes (list / string / missing). Idempotent — never double-prepend.

**When to use:** Any inference-shape outbound that we own. Phase 014 provides the helper; v3 provider-routing wires it into the actual inference path.

```python
_CLAUDE_CODE_SYSTEM_PREFIX = (
    "You are Claude Code, Anthropic's official CLI for Claude."
)

def inject_stealth_system_prefix(body: dict) -> dict:
    """Mutate *body* in place to begin `system` with the Claude-Code prefix.

    Mirrors milady's `addSystemPrefix` (claude-code-stealth.mjs L38–L51).
    Idempotent: a `system` array whose first entry text begins with
    "You are Claude Code" is left untouched.
    """
    prefix = {"type": "text", "text": _CLAUDE_CODE_SYSTEM_PREFIX}
    sys_val = body.get("system")
    if isinstance(sys_val, list):
        if not (
            sys_val
            and isinstance(sys_val[0], dict)
            and isinstance(sys_val[0].get("text"), str)
            and sys_val[0]["text"].startswith("You are Claude Code")
        ):
            sys_val.insert(0, prefix)
    elif isinstance(sys_val, str):
        body["system"] = [prefix, {"type": "text", "text": sys_val}]
    else:  # None / missing
        body["system"] = [prefix]
    return body
```

### Pattern 5: `python -m` Entry Point (no Typer)

**What:** Append a `if __name__ == "__main__":` block at the end of `providers/anthropic.py` so `python -m state_core.auth.providers.anthropic login` runs the interactive flow without invoking the (Phase 022) Typer CLI.

```python
# (end of providers/anthropic.py)
def _main() -> int:
    import argparse
    p = argparse.ArgumentParser(prog="python -m state_core.auth.providers.anthropic")
    p.add_subparsers(dest="cmd", required=True).add_parser(
        "login",
        help="Run the interactive Anthropic OAuth stealth login flow.",
    )
    args = p.parse_args()
    if args.cmd == "login":
        try:
            cred = asyncio.run(AnthropicAuth().login())
        except KeyboardInterrupt:
            print("\nLogin cancelled.", file=sys.stderr)
            return 130
        label = (cred.extras.get("email_address") or cred.account_id or "?")
        print(f"Logged in as {label}")
        return 0
    return 2

if __name__ == "__main__":
    sys.exit(_main())
```

**Why `argparse`, not `typer`:** Typer is the project CLI surface (Phase 022). Adding it here would conflate phases and seed an import dependency. Stdlib `argparse` keeps the entry-point minimal and removable when 022 lands.

**KeyboardInterrupt handling:** `getpass.getpass` propagates `KeyboardInterrupt`; catch at the `asyncio.run` boundary and exit 130 (POSIX SIGINT convention). Do NOT catch inside `login()` — programmatic callers want the exception.

### Anti-Patterns to Avoid

- **Holding the filelock yourself:** Phase 013 already wraps `refresh()` calls. Acquiring a second filelock in the provider deadlocks (refresh.py docstring rule 9 / Pitfall 6).
- **Reading the wall clock:** `is_expired(cred, now)` MUST take `now` as a parameter (base.py / Phase 011 cardinal rule). Use `is_expired_buffered` for the actual math.
- **Mutating frozen credentials:** `OAuthCredential` is `frozen=True`. Use `cred.model_copy(update={...})` to swap tokens.
- **Returning `x-api-key` from `http_headers`:** P0-4. Always `headers.pop("x-api-key", None)` defensively before setting Bearer in any merging code path.
- **Centralizing token-shape sniffing:** Each provider owns its own `is_token()` (PITFALLS Pitfall 5).
- **Using `print()` for credential confirmation that includes secrets:** `f"Logged in as {label}"` is fine (label is email or uuid). Never `print(cred)` — `Field(repr=False)` plus structlog Phase 020 are the layers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PKCE verifier / challenge generation | A custom RNG + manual base64 padding | `secrets.token_urlsafe(32)` + `hashlib.sha256` + `base64.urlsafe_b64encode(...).rstrip(b"=")` | RFC 7636 mandates URL-safe-no-pad; `token_urlsafe(32)` returns exactly 43 chars (within the [43,128] window). Pure stdlib. |
| Form-urlencoding the authorize URL | Manual `&`-joining | `urllib.parse.urlencode({...}, quote_via=quote)` | Stdlib handles space-encoding (`%20` vs `+`) and special-character escaping. Both encodings work for OAuth `state`/scope per spec, but `quote` (default `quote_plus`) gives `+` for spaces — Anthropic accepts either. Confirm via mitmproxy capture. |
| Hidden-input prompt | `input()` + post-strip | `getpass.getpass("Paste code#state: ")` | `getpass` disables tty echo; falls back to a warning + `input()` if no tty (`GetPassWarning`). Treat the auth code as a transient secret in scrollback. |
| Refresh-token exchange retry | `tenacity` | None — bubble | CONTEXT locked: Phase 013 has a 10 s lock budget; retry inside the provider would consume it. Caller naturally retries on the next request. |
| Filelock around refresh | Acquiring `filelock.AsyncFileLock` here | Trust `state_core.auth.refresh.refresh_credential` to wrap us | Double-locking deadlocks (refresh.py rule 9). |
| 5-minute-buffer math | Recomputing `now >= cred.expires - 300` in `is_expired` | `is_expired_buffered(cred, now)` from `state_core.auth.refresh` | Single source of truth for AUTH-09 / P0-7. |
| Pydantic body-shape "addSystemPrefix" | A pydantic model for the request body | A plain `dict[str, Any]` mutator (`inject_stealth_system_prefix`) | Anthropic Messages API body shape varies (`system` is `str | list[dict] | absent`); a strict pydantic model would fight the mutation. Plain dict is the wire shape. |
| Token endpoint URL parsing | A second URL-builder for the token endpoint | A module constant `_TOKEN_URL` | Two endpoints total (authorize + token); constants are clearer than helpers. |

**Key insight:** Every "primitive" this phase needs already exists either in stdlib or in a Phase 011/012/013 helper. The provider is mostly orchestration, plus four constants and one body-mutator. Resist the urge to extract `oauth_common/http_client.py` or `oauth_common/errors.py` until phases 015/016/017 demonstrate concrete duplication.

## Common Pitfalls

(Each pitfall maps to a P0/P1 in `.planning/research/PITFALLS.md`.)

### Pitfall 1: Forgetting the `(external, cli)` parenthetical (P0-1)
**What goes wrong:** `user-agent: claude-cli/2.1.92` (no parenthetical) is rejected as not-Claude-Code; Anthropic silently downgrades to API-key pricing.
**Why it happens:** The spec doc historically wrote `claude-cli/<version>`; milady's reference and our 2026-04 capture both include `(external, cli)`. Reading only the spec leads to a missing parenthetical.
**How to avoid:** Pin `_USER_AGENT = f"claude-cli/{_CLAUDE_CLI_VERSION} (external, cli)"` as a single constant; assert it in test as the literal string.
**Warning signs:** OAuth tokens validate but inference 401s with `invalid authentication`; user's billing dashboard shows API-key usage despite Pro/Max subscription.

### Pitfall 2: PKCE state ≠ verifier (P0-8)
**What goes wrong:** Two independent random strings; `state` round-trips fine, but token exchange returns `invalid_grant` because the server expects `state` to BE the verifier.
**Why it happens:** RFC 7636 doesn't require `state == verifier`; it's a Claude-Code-specific reuse pattern.
**How to avoid:** ONE `secrets.token_urlsafe(32)` call; reuse the result in BOTH the authorize URL `state=` param AND the token exchange `code_verifier` body field.
**Warning signs:** Token exchange always returns `invalid_grant`.

### Pitfall 3: Buffer math duplicated in provider (P0-7)
**What goes wrong:** `is_expired` reads `time.time()` internally OR subtracts 300 with a different constant than refresh.py.
**Why it happens:** Tempting to be self-contained.
**How to avoid:** `from state_core.auth.refresh import is_expired_buffered` and delegate. `now: float` MUST be a parameter.
**Warning signs:** REFRESH-03 / Phase 013 determinism test fails when injected `now` disagrees with wall clock.

### Pitfall 4: Using `x-api-key` instead of Bearer (P0-4)
**What goes wrong:** Single code path tries `x-api-key` for all Anthropic tokens; OAuth tokens always 401.
**Why it happens:** API-key path is the older default; easy to forget the branch.
**How to avoid:** `is_token()` is the FIRST branch (P0-4 prevention). `http_headers()` for OAuth NEVER returns `x-api-key` and the planning code path SHOULD `headers.pop("x-api-key", None)` defensively before setting Bearer.
**Warning signs:** Every OAuth request 401s; pytest-httpx assertion `match_headers` finds `x-api-key` in outbound.

### Pitfall 5: `extra="forbid"` on `AnthropicTokenResponse` (CONTEXT-decided)
**What goes wrong:** Anthropic adds a new field (e.g., `id_token`); next refresh call hard-fails with `ValidationError` and users are locked out.
**Why it happens:** Pydantic v2's default for our `_CredentialBase` is `extra="forbid"` (BASE-04). Symmetric instinct says do the same here.
**How to avoid:** `model_config = ConfigDict(extra="ignore")` on `AnthropicTokenResponse` AND its nested `AnthropicAccount`. ConfigDict does NOT inherit from a sibling model; declare it on each.
**Warning signs:** Refresh works in May, breaks in November after Anthropic ships a server update; `pydantic.ValidationError: extra fields not permitted` in logs.

### Pitfall 6: Stale `claude-cli` version (P2-1)
**What goes wrong:** Claude Code ships 2.2.0; Anthropic's killswitch starts disambiguating on UA version; users below `claude-cli/2.2.x` lose access.
**Why it happens:** Hard-coded constant; no automated drift detection until the deferred capture phase.
**How to avoid:** `_CLAUDE_CLI_VERSION = "2.1.92"` carries a `# captured 2026-04` comment. Phase 022 owns the golden-file diff. Schedule a manual mitmproxy re-capture on every `claude-cli` major release.
**Warning signs:** Sudden 401 wave coincident with a Claude Code release.

### Pitfall 7: `getpass` falls back to plaintext on a non-tty
**What goes wrong:** Running under pytest / CI without a tty, `getpass.getpass` emits `GetPassWarning` and falls back to `input()`. The auth code paste echoes to the test log.
**Why it happens:** Documented stdlib behavior.
**How to avoid:** In tests, ALWAYS monkeypatch `getpass.getpass` to return a fixture string — never let the real `getpass` run in CI. Document in the `python -m` entrypoint: "interactive use only; CI tests must mock getpass.getpass."
**Warning signs:** `pytest -s` shows the auth-code prompt waiting for stdin; test hangs.

### Pitfall 8: `httpx_mock` not asserting URL query params
**What goes wrong:** Test passes "the URL is right" but doesn't catch a missing `?beta=true`.
**Why it happens:** `add_response(url=...)` is a string equality match — `?beta=true` is a separate concern.
**How to avoid:** Use `match_params={"beta": "true"}` explicitly when registering the mock for any inference-shape outbound. For the OAuth token-endpoint POST itself, `?beta=true` is NOT applied (it's an inference-call concern); assert ABSENCE there too.
**Warning signs:** Phase 022 golden-file test catches a regression Phase 014 missed.

### Pitfall 9: Silent shutdown deadlock (P1-9)
**What goes wrong:** `httpx` request hangs on a stalled TCP connection; outer `asyncio.wait_for(method.refresh, timeout=15)` (Phase 013) eventually fires, but the AsyncClient's connection pool isn't closed cleanly because we used a singleton.
**Why it happens:** Module-level singletons cross test boundaries and process-shutdown signals.
**How to avoid:** Per-call `async with httpx.AsyncClient(...)`. The `__aexit__` closes connections deterministically. Phase 013's 15 s `wait_for` cap is the hard ceiling.
**Warning signs:** Daemon hangs on shutdown; pid-file lingers.

## Code Examples

Verified patterns from official sources.

### 1. Authorize URL Construction

```python
# Source: claude-oauth.md (state-inputs/) + milady reference
from urllib.parse import urlencode

_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
_REDIRECT_URI  = "https://platform.claude.com/oauth/code/callback"
_SCOPES        = "org:create_api_key user:profile user:inference"

def _build_authorize_url(verifier: str, challenge: str) -> str:
    qs = urlencode(
        {
            "client_id":             _CLIENT_ID,
            "response_type":         "code",
            "redirect_uri":          _REDIRECT_URI,
            "scope":                 _SCOPES,
            "state":                 verifier,        # state == verifier (P0-8)
            "code_challenge":        challenge,
            "code_challenge_method": "S256",
        },
        # quote_plus default → spaces become '+'. Anthropic accepts both
        # '+' and '%20'; mitmproxy capture confirms claude-cli emits '+'.
    )
    return f"{_AUTHORIZE_URL}?{qs}"
```

### 2. Token-Endpoint Request (authorization_code grant)

```python
# Source: claude-oauth.md + cross-verified body shape
# https://www.python-httpx.org/async/ + pyproject httpx>=0.28.1
_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"

async def _exchange_code(code: str, verifier: str) -> AnthropicTokenResponse:
    body = {
        "grant_type":   "authorization_code",
        "code":         code,
        "redirect_uri": _REDIRECT_URI,
        "client_id":    _CLIENT_ID,
        "code_verifier": verifier,
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=False,
    ) as client:
        try:
            resp = await client.post(
                _TOKEN_URL,
                json=body,                                # application/json
                headers={"accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise AuthLoginError(f"token exchange transport: {exc}") from exc
    if resp.status_code >= 400:
        raise AuthLoginError(
            f"token exchange http {resp.status_code}: {resp.text[:200]}"
        )
    try:
        return AnthropicTokenResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        raise AuthLoginError(f"token exchange shape: {exc}") from exc
```

> **Content-Type note:** Two sources disagree.
> - `claude-oauth.md` (this repo) is silent on Content-Type.
> - A 2026 third-party article (alif.web.id) shows `Content-Type: application/json` against `https://console.anthropic.com/api/oauth/token` (note different host).
>
> The host in the spec doc + milady evidence is `platform.claude.com`; we keep that. **Verification gate (CONTEXT-locked):** the pre-merge mitmproxy capture MUST confirm Content-Type AND host. If capture shows `application/x-www-form-urlencoded`, swap `json=body` for `data=body` and add `headers={"content-type": "application/x-www-form-urlencoded"}`. Document the captured value in a `# verified 2026-04 via mitmproxy` comment.

### 3. Refresh Token Exchange

```python
async def _refresh_token(refresh_token: str) -> AnthropicTokenResponse:
    body = {
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "client_id":     _CLIENT_ID,
    }
    # Same client construction as #2 — extract a private helper
    # if the duplication smells; but two call sites is below the
    # rule-of-three threshold.
    ...
```

### 4. Pydantic Token-Response Model (extra="ignore" both layers)

```python
# Source: pydantic.dev/docs (verified 2026-04-28)
# Re #2: ConfigDict does NOT inherit from a parent class — declare on each model.
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field

class AnthropicAccount(BaseModel):
    model_config = ConfigDict(extra="ignore")            # forward-compat
    uuid: str
    email_address: str | None = None

class AnthropicTokenResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")            # forward-compat
    access_token:  str           = Field(repr=False)     # SECRET — never repr
    refresh_token: str           = Field(repr=False)     # SECRET — never repr
    expires_in:    int                                    # seconds-from-now (wire shape)
    token_type:    str | None = None
    account:       AnthropicAccount | None = None
```

**Conversion to `OAuthCredential`** (Phase 011 wire-shape rule: store `expires` as absolute epoch seconds, NO buffer applied here):
```python
def _to_credential(resp: AnthropicTokenResponse, now: float) -> OAuthCredential:
    return OAuthCredential(
        access     = resp.access_token,
        refresh    = resp.refresh_token,
        expires    = now + float(resp.expires_in),   # wire shape: epoch sec
        provider_id = "anthropic",
        account_id = resp.account.uuid if resp.account else None,
        extras     = (
            {"email_address": resp.account.email_address}
            if resp.account and resp.account.email_address
            else {}
        ),
    )
```

### 5. pytest-httpx Header / URL / Body Assertions

```python
# Source: colin-b.github.io/pytest_httpx (verified 2026-04-28)
# pyproject pytest-httpx>=0.35
import pytest
from pytest_httpx import HTTPXMock

@pytest.mark.asyncio
async def test_login_emits_byte_for_byte_token_request(
    httpx_mock: HTTPXMock, monkeypatch
) -> None:
    # Mock the token endpoint with a positive response.
    httpx_mock.add_response(
        method="POST",
        url="https://platform.claude.com/v1/oauth/token",
        match_json={                                     # body equality — every field
            "grant_type":   "authorization_code",
            "code":         "fixture-code",
            "redirect_uri": "https://platform.claude.com/oauth/code/callback",
            "client_id":    "9d1c250a-e61b-44d9-88ed-5944d1962f5e",
            "code_verifier": "fixture-verifier-43chars-aaaaaaaaaaaaaaaaaaaa",
        },
        json={
            "access_token":  "sk-ant-oat01-FIXTURE",
            "refresh_token": "sk-ant-ort01-FIXTURE",
            "expires_in":    28_800,
            "token_type":    "Bearer",
            "account":       {"uuid": "u-1", "email_address": "x@y.z"},
        },
    )
    # Suppress the print prompt + replace getpass.
    monkeypatch.setattr(
        "state_core.auth.providers.anthropic.getpass.getpass",
        lambda _prompt: "fixture-code#fixture-verifier-43chars-aaaaaaaaaaaaaaaaaaaa",
    )
    monkeypatch.setattr(
        "state_core.auth.oauth_common.pkce.generate_verifier",
        lambda *_: "fixture-verifier-43chars-aaaaaaaaaaaaaaaaaaaa",
    )

    cred = await AnthropicAuth().login()

    assert cred.access     == "sk-ant-oat01-FIXTURE"
    assert cred.account_id == "u-1"
    # match_json above already failed the test if any body field disagreed.

@pytest.mark.asyncio
async def test_http_headers_contain_full_stealth_quad(
    oauth_cred: OAuthCredential,
) -> None:
    h = AnthropicAuth().http_headers(oauth_cred)
    assert h["authorization"]    == f"Bearer {oauth_cred.access}"
    assert h["user-agent"]       == "claude-cli/2.1.92 (external, cli)"
    assert h["x-app"]            == "cli"
    assert h["anthropic-beta"].startswith("claude-code-20250219,oauth-2025-04-20,")
    assert "x-api-key" not in h                          # P0-4
```

### 6. Body-Mutation Idempotency Test

```python
def test_inject_stealth_system_prefix_is_idempotent() -> None:
    body = {"system": [{"type": "text", "text": "You are Claude Code, …"}]}
    before = body["system"][0]
    inject_stealth_system_prefix(body)
    assert body["system"][0] is before                   # no double-prepend
    assert len(body["system"]) == 1

def test_inject_stealth_system_prefix_handles_string_form() -> None:
    body = {"system": "Existing system message."}
    inject_stealth_system_prefix(body)
    assert body["system"][0]["text"].startswith("You are Claude Code")
    assert body["system"][1] == {"type": "text", "text": "Existing system message."}

def test_inject_stealth_system_prefix_handles_missing() -> None:
    body: dict = {}
    inject_stealth_system_prefix(body)
    assert body["system"] == [
        {"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."}
    ]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requests` + thread pool | `httpx.AsyncClient` (per-call context manager) | httpx 0.27+ matured | Native async; avoids GIL contention with daemon's asyncio loop. |
| Pydantic v1 `class Config: extra = "ignore"` | Pydantic v2 `model_config = ConfigDict(extra="ignore")` | pydantic 2.0 (mid-2023) | Project pinned to 2.13.2; v1 syntax silently ignored — easy mistake. |
| `unittest.mock.patch` of `httpx.AsyncClient` | `pytest-httpx` `httpx_mock` fixture with `match_url`/`match_headers`/`match_json`/`match_params` | pytest-httpx 0.30+ | Declarative byte-for-byte assertions; less brittle than `mock.call_args` introspection. |
| Local OAuth callback HTTP server | Manual `code#state` paste | Claude Code original choice | Works headless / over SSH; avoids port-binding races. |
| `Content-Type: application/x-www-form-urlencoded` token POST | `Content-Type: application/json` token POST | Anthropic platform launch | Verified by 2026-04 third-party (cross-check via mitmproxy pre-merge). |

**Deprecated / outdated in this domain:**
- `class Config:` Pydantic v1 inner-class style — silently no-op under v2.
- `unittest.mock` for httpx — `pytest-httpx` is now the standard.
- Pre-PKCE OAuth 2.0 (no `code_challenge`) — superseded by RFC 7636 (mandatory for public clients).

## Open Questions (RESOLVED)

1. **Token-endpoint Content-Type is JSON vs form-urlencoded — which does Anthropic accept TODAY?**
   - What we know: milady's reference is a fetch-shim (doesn't construct token POST itself); a 2026 third-party shows JSON; the spec doc is silent.
   - What's unclear: whether Anthropic accepts BOTH or has tightened to JSON only.
   - Recommendation: code path uses `json=body` (matches third-party). Pre-merge mitmproxy capture is a CONTEXT-locked gate; if capture shows form-urlencoded, swap `json=` → `data=` in two places (token exchange + refresh). Test fixture covers both via `match_json` (current) or `match_content` (form-urlencoded variant).

2. **Authorize URL host: `claude.ai` or `platform.claude.com`?**
   - What we know: spec says `https://claude.ai/oauth/authorize` for the AUTHORIZE URL; `https://platform.claude.com/v1/oauth/token` for the TOKEN URL. `redirect_uri` is `https://platform.claude.com/oauth/code/callback`.
   - What's unclear: whether Anthropic has consolidated hosts since the spec was written.
   - Recommendation: keep spec values verbatim; mitmproxy capture confirms.

3. **Scope-list separator: `+` or `%20`?**
   - What we know: `urllib.parse.urlencode` default is `quote_plus` → spaces become `+`. RFC 3986 allows both; OAuth 2.0 servers should accept either.
   - What's unclear: whether Anthropic's parser is permissive.
   - Recommendation: use `urlencode` default (`+`). Mitmproxy capture verifies; if `%20` is required, pass `quote_via=quote`.

4. **Should `_to_credential` accept `now` as a parameter?**
   - What we know: provider methods are pure-introspection if sync; `login()` is async I/O. The wire shape `expires = now + expires_in` requires SOME clock read.
   - What's unclear: whether to inject `now` (testability win) or read once at the top of `login()` (simpler).
   - Recommendation: read `time.time()` ONCE inside `login()` / `refresh()` and pass it down to `_to_credential(resp, now=time.time())`. Tests can monkeypatch `time.time` in `state_core.auth.providers.anthropic` if needed. This matches Phase 013's `refresh_credential` pattern (single clock read at function entry).

5. **Where do `AuthError` / `AuthLoginError` / `AuthRefreshError` / `StealthRejected` LIVE?**
   - What we know: CONTEXT marks "Claude's discretion at planning time" — inline in `anthropic.py` OR `state_core.auth.errors`.
   - Recommendation: start INLINE in `providers/anthropic.py`. Promote to `state_core.auth.errors` only when phase 015 lands and confirms it wants the same hierarchy. YAGNI.

6. **Does `python -m state_core.auth.providers.anthropic` need a `__main__.py`?**
   - What we know: a module's `if __name__ == "__main__":` block runs under `python -m <pkg.module>`. A separate `__main__.py` is only needed for packages (directories), not modules.
   - Recommendation: `if __name__ == "__main__":` at the end of `anthropic.py`. No extra file.

## Validation Architecture

> Phase config has `workflow.nyquist_validation: true` — section is included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest>=8.4.0` + `pytest-asyncio>=1.3.0` + `pytest-httpx>=0.35` + `pytest-mock>=3.14` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `pytest tests/auth/oauth_common/ tests/auth/providers/test_anthropic.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| AUTH-01 | PKCE verifier is stdlib-only, base64url-no-pad, length ∈ [43,128] | unit | `pytest tests/auth/oauth_common/test_pkce.py::test_verifier_format -x` | ❌ Wave 0 |
| AUTH-01 / P0-8 | `state == verifier` round-trip (single string used in both places) | unit | `pytest tests/auth/providers/test_anthropic.py::test_state_equals_verifier -x` | ❌ Wave 0 |
| AUTH-01 / P0-5 | `client_id == "9d1c250a-e61b-44d9-88ed-5944d1962f5e"` after base64-decode at module load | unit | `pytest tests/auth/providers/test_anthropic.py::test_client_id_matches_claude_code -x` | ❌ Wave 0 |
| AUTH-01 / P0-1 | Outbound `user-agent: claude-cli/2.1.92 (external, cli)` (with parenthetical) | unit | `pytest tests/auth/providers/test_anthropic.py::test_http_headers_user_agent_exact -x` | ❌ Wave 0 |
| AUTH-01 / P0-2 | Outbound `anthropic-beta` equals the full pinned 6-flag string | unit | `pytest tests/auth/providers/test_anthropic.py::test_http_headers_anthropic_beta_exact -x` | ❌ Wave 0 |
| AUTH-01 / P0-3 | Outbound `x-app: cli` | unit | `pytest tests/auth/providers/test_anthropic.py::test_http_headers_x_app -x` | ❌ Wave 0 |
| AUTH-01 / P0-4 | OAuth path uses `Authorization: Bearer …` AND `x-api-key` is absent | unit | `pytest tests/auth/providers/test_anthropic.py::test_http_headers_no_x_api_key -x` | ❌ Wave 0 |
| AUTH-01 / P0-7 | `is_expired(cred, now)` delegates to `is_expired_buffered` (5-min buffer applied at AuthMethod layer) | unit | `pytest tests/auth/providers/test_anthropic.py::test_is_expired_uses_300s_buffer -x` | ❌ Wave 0 |
| AUTH-01 | Token POST URL == `https://platform.claude.com/v1/oauth/token`; body shape == authorization_code grant fields verbatim | unit | `pytest tests/auth/providers/test_anthropic.py::test_login_token_post_shape -x` | ❌ Wave 0 |
| AUTH-01 | Refresh POST body shape == refresh_token grant fields verbatim | unit | `pytest tests/auth/providers/test_anthropic.py::test_refresh_post_shape -x` | ❌ Wave 0 |
| AUTH-01 | `AnthropicTokenResponse` accepts an unknown field (`extra="ignore"` forward-compat) | unit | `pytest tests/auth/providers/test_anthropic.py::test_token_response_ignores_unknown_field -x` | ❌ Wave 0 |
| AUTH-01 | `inject_stealth_system_prefix` handles list / string / missing forms AND is idempotent | unit | `pytest tests/auth/providers/test_anthropic.py::test_inject_stealth_system_prefix -x` | ❌ Wave 0 |
| AUTH-01 | URL has `?beta=true` when invoked against the inference endpoint | unit | `pytest tests/auth/providers/test_anthropic.py::test_url_has_beta_true -x` | ❌ Wave 0 |
| AUTH-01 | `AnthropicAuth()` structurally satisfies `state_core.auth.base.AuthMethod` | unit | `pytest tests/auth/providers/test_anthropic.py::test_satisfies_authmethod_protocol -x` | ❌ Wave 0 |
| AUTH-01 | `paste.partition("#")` correctly splits `code#state`; missing `#` raises `AuthLoginError` | unit | `pytest tests/auth/providers/test_anthropic.py::test_paste_format_required -x` | ❌ Wave 0 |
| AUTH-01 | 401 with stealth-shape signal raises `StealthRejected` (not `AuthLoginError`) | unit | `pytest tests/auth/providers/test_anthropic.py::test_401_raises_stealth_rejected -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/auth/oauth_common/ tests/auth/providers/test_anthropic.py -x`
- **Per wave merge:** `pytest tests/auth/ -x`
- **Phase gate:** `pytest -x` (full suite green) before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `tests/auth/oauth_common/__init__.py` — empty marker.
- [ ] `tests/auth/oauth_common/test_pkce.py` — covers AUTH-01 (PKCE primitives).
- [ ] `tests/auth/providers/__init__.py` — empty marker.
- [ ] `tests/auth/providers/test_anthropic.py` — RED stubs for all 16 rows above (one test per row).
- [ ] `tests/auth/providers/conftest.py` (optional) — fixtures: pinned-fixture verifier, fake `code#state` string, mock `getpass.getpass`, common token-endpoint mock-response factory. May be folded into `tests/auth/conftest.py` if no naming clashes.
- [ ] No new framework / no new dependency installs — `pytest`, `pytest-asyncio`, `pytest-httpx`, `pytest-mock` already in `pyproject.toml`.

## Sources

### Primary (HIGH confidence)
- `.state-inputs/claude-oauth.md` — repo-canonical stealth spec; CLIENT_ID, scopes, URLs, paste format, 5-min buffer, `state==verifier`, `sk-ant-oat` token-shape sniffer, multi-cred array shape.
- `.state-inputs/references/milady/claude-code-stealth.mjs` (MIT, captured 2026-04 from milady-ai/milady#1910 SHA `55665598132a15ae6a91a13d803919a2192137fd`) — full anthropic-beta string, `(external, cli)` parenthetical, system-prefix injection (`addSystemPrefix` L38–L51), `?beta=true`, `x-api-key` defensive deletion, claude-cli 2.1.92.
- `.state-inputs/references/milady/NOTICE.md` — attribution + capture date.
- `https://www.python-httpx.org/async/` — AsyncClient lifecycle (verified 2026-04-28).
- `https://www.python-httpx.org/advanced/timeouts/` — `httpx.Timeout(default, connect=, read=, write=, pool=)` signature; per-call vs construction-time `timeout=` kwarg; `TimeoutException` subclasses (`ConnectTimeout`, `ReadTimeout`, `WriteTimeout`, `PoolTimeout`).
- `https://colin-b.github.io/pytest_httpx/` — `httpx_mock.add_response(match_url=, match_headers=, match_json=, match_params=, match_content=)`; `httpx_mock.get_request()` / `get_requests()`; async usage with `async with httpx.AsyncClient()`.
- `https://pydantic.dev/docs/validation/latest/concepts/models/` — `model_config = ConfigDict(extra="ignore")`; nested-model semantics; `field: NestedModel | None = None` accepts None or full schema.
- Existing in-tree code (HIGH — read directly):
  - `src/state_core/auth/base.py` — `OAuthCredential`, `AuthMethod` Protocol, secret hygiene rules.
  - `src/state_core/auth/store.py` — `AuthVault` array-per-provider invariant.
  - `src/state_core/auth/refresh.py` — `is_expired_buffered`, `refresh_credential`, 15s `wait_for` cap.
  - `tests/auth/conftest.py` — `oauth_cred`, `auth_json_path`, `now_frozen`, `mock_auth_method` fixture conventions.
- `.planning/research/PITFALLS.md` — P0-1..P0-5, P0-6, P0-7, P0-8, P0-13, P0-14, P1-1, P1-2, P1-9, P2-1.

### Secondary (MEDIUM confidence)
- `https://www.alif.web.id/posts/claude-oauth-api-key` — refresh POST body shape with `Content-Type: application/json` against `https://console.anthropic.com/api/oauth/token` (different host than spec; cross-check via mitmproxy gate).
- `https://hexdocs.pm/claude_code_sdk/ClaudeCodeSDK.Auth.Providers.Anthropic.html` — confirms `sk-ant-oat01-...` access token format and `claude.ai/oauth/authorize` authorize URL.

### Tertiary (LOW confidence — flagged for validation)
- WebSearch results re: token endpoint host (`platform.claude.com` vs `console.anthropic.com`) — Anthropic may have consolidated hosts since spec was authored. Mitmproxy capture is the binding pre-merge gate (CONTEXT-locked).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep is already pinned in `pyproject.toml`; no decisions to validate.
- Architecture (per-call AsyncClient, Protocol implementation, body-mutator helper, `python -m` entry): HIGH — direct reads of in-tree code (Phase 011/012/013) + httpx/pytest-httpx/pydantic official docs verified 2026-04-28.
- Stealth header values + `_CLAUDE_CLI_VERSION = "2.1.92"`: HIGH from milady reference + repo spec; MEDIUM until cross-verified via mitmproxy capture (CONTEXT-locked pre-merge gate).
- Token endpoint Content-Type (JSON vs form-urlencoded): MEDIUM — third-party source says JSON; spec doc silent. Mitmproxy capture decides at merge time. Plan code for JSON; document the swap.
- Pitfalls: HIGH — direct read of `.planning/research/PITFALLS.md` + cross-referenced milady evidence.

**Research date:** 2026-04-28
**Valid until:** 2026-07-28 (90 days for the architecture findings; the stealth constants need re-capture on every claude-cli major release per Pitfall 6 / P2-1).

## RESEARCH COMPLETE
