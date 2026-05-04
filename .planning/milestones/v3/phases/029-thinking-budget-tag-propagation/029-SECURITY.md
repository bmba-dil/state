---
phase: 029
slug: thinking-budget-tag-propagation
status: secured
threats_open: 0
asvs_level: 1
created: 2026-05-04
---

# Phase 029 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Caller → build_thinking_param | Pure conversion utility; caller passes ResolvedProfile + max_tokens | No secrets, no credentials — profile config only |
| build_thinking_param → AnthropicClient | Returns ThinkingConfigEnabledParam dict; caller must gate on isinstance(client, AnthropicClient) | budget_tokens integer only |
| Test fixtures → Anthropic API (mocked) | HTTPXMock intercepts at transport layer; no real network calls in tests | Fake OAuth token literal, mock response body |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-029-01 | Tampering | Test stubs (Wave 0) | mitigate | Stubs confirmed fail with ModuleNotFoundError — not vacuous pass | closed |
| T-029-02 | Tampering | Wire-capture tests | mitigate | HTTPXMock intercepts at httpx transport layer (not mock.patch on create()) | closed |
| T-029-03 | Information Disclosure | Test OAuth fixture | mitigate | FAKE_OAUTH_CRED uses literal `"sk-ant-oat-fake"` — no env/vault reads | closed |
| T-029-04 | Tampering | Mode-silo test | mitigate | `test_no_mode_silo_import` uses `inspect.getsource()` — fails on any state_build/state_teach import | closed |
| T-029-05 | Elevation of Privilege | build_thinking_param routing | mitigate | Pure conversion utility — no client calls; module docstring documents caller responsibility to gate on isinstance(client, AnthropicClient) | closed |
| T-029-06 | Denial of Service | budget_tokens >= max_tokens | mitigate | Pre-flight: `if budget >= max_tokens: raise ProviderBadRequestError(...)` before any network call | closed |
| T-029-07 | Denial of Service | budget_tokens < 1024 | mitigate | Pre-flight: `if budget < 1024: raise ProviderBadRequestError(...)` before any network call | closed |
| T-029-08 | Tampering | Circular import | accept | model_profile.py uses `thinking_budget_tokens` as a data field only — no import of thinking_budget module; one-way dependency confirmed | closed |
| T-029-09 | Elevation of Privilege | Mode isolation | mitigate | thinking_budget.py imports only shared kernel (anthropic SDK, state_core.providers.*); test_no_mode_silo_import enforces at runtime | closed |
| T-029-10 | Tampering | type="adaptive" model confusion | accept | Phase 029 always returns type="enabled"; claude-opus-4-7 does not trigger SDK adaptive warning; documented in module; update scope is Phase 030+ | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-029-01 | T-029-08 | No circular import risk — model_profile.py references thinking_budget_tokens as a field name, not as an import path | Thomas | 2026-05-04 |
| AR-029-02 | T-029-10 | type="adaptive" only relevant for models not used by quality profile in Phase 029; deferred to Phase 030+ if model changes | Thomas | 2026-05-04 |

---

## Audit Trail

### Security Audit 2026-05-04

| Metric | Count |
|--------|-------|
| Threats found | 10 |
| Closed | 10 |
| Open | 0 |

All mitigations verified against implemented code:
- Pre-flight guards confirmed in `src/state_core/providers/thinking_budget.py:63-70`
- Mode isolation confirmed via grep + passing `test_no_mode_silo_import`
- Wire-capture pattern confirmed in `tests/test_thinking_budget_propagation.py` (HTTPXMock, 3 tests)
- Fake credential literal confirmed at `tests/test_thinking_budget_propagation.py:34`
- Post-review refactor (`bccbd29`) applied: `ThinkingConfigEnabledParam` constructor used — stronger type safety
