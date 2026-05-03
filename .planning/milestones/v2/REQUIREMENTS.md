# v2 — Auth Coverage (5 Methods + Multi-Cred) Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Kernel: Auth (A2)

- [x] **AUTH-01**: Anthropic OAuth stealth flow implemented byte-for-byte against `state-inputs/claude-oauth.md` — headers (`user-agent: claude-cli/<ver>`, `x-app: cli`, `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…`), PKCE verifier = OAuth `state`, client_id `9d1c250a-e61b-44d9-88ed-5944d1962f5e`, Bearer for `sk-ant-oat*`
- [x] **AUTH-02**: Gemini CLI free-tier OAuth (google-auth-oauthlib, PKCE, refresh rotation)
- [x] **AUTH-03**: Antigravity OAuth (custom flow, refresh handling)
- [x] **AUTH-04**: GitHub Copilot device-code flow (polling, grant-revocation handling)
- [x] **AUTH-05**: API key vault (plain keys for Anthropic, OpenAI, Google, DeepSeek, Groq, Together, Anyscale, Mistral, Cohere, OpenRouter, Grok, Cerebras)
- [x] **AUTH-06**: `.state/auth.json` created chmod 0600 via `os.open(..., 0o600)` + `os.fchmod`; chmod verified on every read
- [x] **AUTH-07**: Filelock-guarded refresh: acquire lock (10s timeout), re-read `auth.json`, double-check expiry, refresh only if stale, write, release
- [x] **AUTH-08**: Multi-cred round-robin across credentials of the same provider
- [x] **AUTH-09**: Access token renewal 5 minutes before `expires_in` (never verbatim)
- [ ] **AUTH-10**: Root-logger token redactor strips `sk-ant-*`, `sk-*`, `ya29.*`, etc. from every log record
- [ ] **AUTH-11**: First-run import from opencode's existing auth store when detected
- [ ] **AUTH-12**: `state auth login <provider>` / `state auth logout <provider>` / `state auth status` CLI
- [ ] **AUTH-13**: Captured-header regression test: golden-file compare of actual outbound HTTP headers against claude-oauth.md spec for every stealth request
