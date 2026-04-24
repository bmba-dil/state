# GSD 2 Auth Analysis — How It Covers Every Plan

Analysis of how `gsd-pi` (GSD 2, built on Pi SDK) authenticates users across OpenAI, Google, GitHub, and Anthropic subscription plans without violating any vendor's Terms of Service.

---

## The strategy: four different methods, one coverage outcome

GSD 2 doesn't have a single "auth everything" trick. It has a **coverage strategy** — use the right method for each vendor based on what that vendor officially permits.

### Method 1: Direct OAuth for providers that allow it

`packages/pi-ai/src/utils/oauth/` — four built-in OAuth providers:

| Provider | File | Flow | What it gets you |
|---|---|---|---|
| **OpenAI Codex** | `openai-codex.ts` | PKCE OAuth at `auth.openai.com`, callback on `localhost:1455` | ChatGPT Plus/Pro/Team subscription |
| **GitHub Copilot** | `github-copilot.ts` | Device-code flow with public client ID `Iv1.b507a08c87ecfe98` | Copilot subscription → Claude + GPT |
| **Google Gemini CLI** | `google-gemini-cli.ts` | Google OAuth with Desktop client credentials (client_id + secret embedded in source), free-tier Code Assist | Standard Gemini 2.x access, free tier |
| **Google Antigravity** | `google-antigravity.ts` | Another Google OAuth flow with different client ID + extra scopes (`cclog`, `experimentsandconfigs`) | **Gemini 3 + Claude + GPT-OSS** via Google Cloud — the sleeper path |

Google's OAuth credentials (CLIENT_ID + CLIENT_SECRET) are deliberately committed in plain text with a comment explaining why:

> "Google's OAuth implementation requires client_secret for Desktop App OAuth clients even though it cannot be kept secret in distributed applications. The actual security relies on PKCE, redirect URI validation (localhost only), and user consent."

They also note: "They should NOT be obfuscated because security scanners flag obfuscated data as potentially malicious."


### Method 2: Standard API keys
Anthropic direct (console.anthropic.com key), Azure, Bedrock, Vertex, Mistral — `env-api-keys.ts` + `api-registry.ts` handle the plain-key path.

### Method 3: Bearer-token Anthropic variants
`providers/anthropic.ts:65` — `usesAnthropicBearerAuth()` detects providers that use `Bearer` auth instead of `x-api-key` (e.g., Copilot's Claude access, OpenRouter's Anthropic endpoints). Same Anthropic protocol, different auth header. Auto-detected and handled.

---

## Applied to opencode

Opencode has Codex + Copilot + Gitlab + Poe + Cloudflare built-in but is missing:

- Google Code Assist OAuth (gemini-cli free-tier)
- Google Antigravity OAuth (Claude via Google Cloud)
- Claude Code OAuth

All three are straightforwardly portable as opencode plugins because:

1. Opencode's plugin API has `auth: AuthHook` with `type: "oauth"` method support — full OAuth flow registration (`packages/plugin/src/index.ts:89-163`)
2. For the Claude Code, refer to the claude-oauth.md

If you want opencode to "auth everything like GSD 2," the port is:

- **Copy `google-gemini-cli.ts` + `google-antigravity.ts` + `google-oauth-utils.ts` + `pkce.ts`** from GSD 2 into an opencode plugin (MIT-licensed, drop-in).

Three plugins, maybe ~1500 lines total, and opencode would match GSD 2's auth coverage: Claude Max (via delegation), Gemini free-tier, Gemini 3 + Claude + GPT-OSS via Antigravity, plus ChatGPT Plus + Copilot it already has.


