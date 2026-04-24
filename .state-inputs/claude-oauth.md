# Claude OAuth in GSD-pi

How GSD-pi authenticates users against Anthropic (Claude Pro/Max subscriptions), and what the Python rebuild (gsd-2Py) needs to preserve.

---

## TL;DR

GSD-pi piggybacks on **Claude Code's OAuth client ID and identity headers** to authenticate against a user's Claude Pro/Max subscription. The server issues a `sk-ant-oat…` token which GSD forwards as a Bearer on every request, with headers that make the request look like it's coming from Claude Code itself. That's what unlocks subscription-priced inference instead of API-key pricing.

Flow: PKCE + Authorization Code, manual paste of `code#state` (no local callback server), tokens stored in `~/.gsd/agent/auth.json` with file locking and auto-refresh.

---

## Flow, top to bottom

### 1. Entry point: `/login`

User runs `/login` in interactive mode → `packages/pi-coding-agent/src/modes/interactive/components/login-dialog.ts` → `components/oauth-selector.ts` lists providers registered in `@gsd/pi-ai/oauth`.

### 2. Provider registry

`packages/pi-ai/src/utils/oauth/index.ts` — central registry. Anthropic is one of 5 built-ins alongside GitHub Copilot, Gemini CLI, Google Antigravity, and OpenAI Codex. Registry is pluggable via `registerOAuthProvider()` so extensions can add their own.

### 3. Anthropic handshake

`packages/pi-ai/src/utils/oauth/anthropic.ts` — standard OAuth 2.0 Authorization Code + PKCE, masquerading as Claude Code:

| Field | Value |
|---|---|
| Client ID | `9d1c250a-e61b-44d9-88ed-5944d1962f5e` (base64-decoded at runtime — same ID Claude Code uses) |
| Authorize URL | `https://claude.ai/oauth/authorize` |
| Token URL | `https://platform.claude.com/v1/oauth/token` |
| Redirect URI | `https://platform.claude.com/oauth/code/callback` |
| Scopes | `org:create_api_key user:profile user:inference` |
| PKCE | S256 challenge, `state=<verifier>` (state doubles as verifier) |

User pastes `code#state` back from the browser (no local callback server — manual paste flow). `expires_in` is shaved by 5 minutes as a safety buffer.

### 4. Using the token

`packages/pi-ai/src/providers/anthropic.ts:50-121` — `isOAuthToken()` sniffs for `sk-ant-oat` prefix. If OAuth:

- Uses `authToken` (Bearer), **not** `x-api-key`.
- Adds Claude Code identity headers:
  - `user-agent: claude-cli/2.1.62`
  - `x-app: cli`
  - `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…`

The code comment literally says **"Stealth mode: mimic Claude Code's tool naming exactly"** — Anthropic's server accepts the OAuth token because the request looks like it came from Claude Code.

### 5. Storage and refresh

`packages/pi-coding-agent/src/core/auth-storage.ts`:

- Credentials persist to `~/.gsd/agent/auth.json`, chmod `0600`.
- File-locked via `acquireLockAsync` so concurrent pi instances don't race on refresh.
- `refreshOAuthTokenWithLock()` auto-refreshes when `Date.now() >= expires`, calling `refreshAnthropicToken()` against the same TOKEN_URL with `grant_type=refresh_token`.
- Supports multiple credentials per provider for round-robin + rate-limit backoff/fallback.

---

## Key files

- `packages/pi-ai/src/utils/oauth/anthropic.ts` — the handshake itself (~140 lines)
- `packages/pi-ai/src/utils/oauth/pkce.ts` — PKCE via Web Crypto API
- `packages/pi-ai/src/utils/oauth/index.ts` — provider registry + `getOAuthApiKey()` (refresh-on-read)
- `packages/pi-ai/src/utils/oauth/types.ts` — `OAuthCredentials`, `OAuthProviderInterface`
- `packages/pi-ai/src/providers/anthropic.ts` — where the token is actually used (stealth headers)
- `packages/pi-coding-agent/src/core/auth-storage.ts` — disk storage, locking, refresh orchestration

---

## Implications for the Python rewrite (gsd-2Py)

The whole flow is small and portable. Python port needs:

- `httpx` (async HTTP) for the token exchange and refresh
- Stdlib `secrets` + `hashlib.sha256` + `base64.urlsafe_b64encode` for PKCE (no extra deps)
- `filelock` or `fcntl` for the auth.json refresh lock
- An Anthropic SDK call path that supports `authToken` / Bearer + custom default headers

### Non-obvious things to preserve

1. **Stealth identity headers** — `user-agent: claude-cli/<version>`, `x-app: cli`, and the full `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…` string. Drop these and the OAuth token stops working for subscription inference.
2. **Client ID must match Claude Code's.** Don't register a new one — the whole model depends on identifying as Claude Code.
3. **`state = verifier`** — the auth flow reuses the PKCE verifier as the OAuth state parameter. Keep it; the server round-trips it.
4. **`code#state` paste format** — the manual paste is a single string split on `#`, not two prompts.
5. **5-minute expiry buffer** — subtract 5 minutes from `expires_in` before storing. Prevents edge-case refreshes mid-request.
6. **File locking on refresh** — without it, concurrent CLI instances double-refresh and one of the tokens gets invalidated. The GSD-pi implementation is careful here; the Python port must be too.
7. **`sk-ant-oat` prefix detection** — the provider code branches on token shape to decide between OAuth Bearer and API-key auth. Single code path won't work; you need both.
8. **Multi-credential round-robin** — auth.json stores an array per provider, and the refresh path updates in-place. Useful for rate-limit fallback; preserve the array shape even if you start with a single credential.

### Effort estimate

- Core OAuth module: ~1 day (handshake + PKCE + refresh)
- auth.json storage + locking + multi-credential handling: ~1 day
- Anthropic client integration with stealth headers: ~half day
- Tests (mock the token endpoint, verify header shape): ~1 day

Roughly **3–4 days** to port with parity. The risk isn't complexity — it's forgetting one of the stealth headers and silently dropping to API-key pricing.
