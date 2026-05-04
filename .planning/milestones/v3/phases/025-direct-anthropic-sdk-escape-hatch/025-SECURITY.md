---
phase: 025
slug: direct-anthropic-sdk-escape-hatch
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-03
---

# Phase 025 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| AnthropicClient → Anthropic API | OAuth Bearer or API key sent over TLS | access token / API key (HIGH sensitivity) |
| AnthropicClient ← Anthropic API | Message response received | model output (LOW sensitivity) |
| Deps.http_client | Shared transport owned by orchestrator | all HTTP traffic; must not be closed by consumers |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-025-1 | Information Disclosure | AnthropicClient logging | mitigate | `log.debug` at `create()` logs only `model=` and `max_tokens=`. Credential fields (`access`, `key`) have `Field(repr=False)` — suppressed from structlog output. No inline string literals with credential values in tests. | closed |
| T-025-2 | Spoofing / Info Disclosure | SDK env-var fallback | mitigate | `"X-Api-Key": omit` in `default_headers` suppresses SDK env-var fallback (`api_key=None` + `ANTHROPIC_API_KEY` set). `test_no_x_api_key_with_oauth` verifies header absent under monkeypatch. | closed |
| T-025-3 | Elevation of Privilege | Credential type dispatch | mitigate | `_build_sdk()` dispatches `isinstance(cred, OAuthCredential)` first, `ApiKeyCredential` second, `TypeError` for unknown types. `test_oauth_stealth_headers` + `test_api_key_credential_headers` assert mutually exclusive header sets. | closed |
| T-025-4 | Denial of Service | Shared httpx client lifecycle | mitigate | `AnthropicClient` never calls `aclose()` or `.close()`. Grep verified: no call sites. `test_does_not_close_shared_client` asserts `is_closed is False` after `create()`. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-03 | 4 | 4 | 0 | gsd-security-auditor (automated) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter
