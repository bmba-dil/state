---
phase: 025-direct-anthropic-sdk-escape-hatch
security_audit: true
asvs_level: L1
audited: 2026-05-03
auditor: gsd-secure-phase
result: SECURED
threats_total: 4
threats_closed: 4
threats_open: 0
---

# Phase 025 Security Audit

**Phase:** 025 — direct-anthropic-sdk-escape-hatch
**ASVS Level:** L1
**Threats Closed:** 4/4
**Threats Open:** 0/4
**Result:** SECURED

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-025-1 | Credential logging | mitigate | CLOSED | `log.debug` at line 150 logs only `model=` and `max_tokens=`; no `cred.access` or `cred.key` in any log call. `OAuthCredential.access` and `ApiKeyCredential.key` both carry `Field(repr=False)` (auth/base.py lines 59, 97). `cred.access` and `cred.key` appear only as constructor arguments to `AsyncAnthropic()` (lines 65, 85), never in structlog calls. |
| T-025-2 | X-Api-Key env-var leak | mitigate | CLOSED | `"X-Api-Key": omit` in `default_headers` at anthropic_client.py line 72 suppresses SDK env-var fallback for OAuth path. `test_no_x_api_key_with_oauth` sets `ANTHROPIC_API_KEY` via monkeypatch and asserts `"x-api-key" not in {k.lower() for k in req.headers}` — PASSED. |
| T-025-3 | OAuth credential routed through API-key path | mitigate | CLOSED | `_build_sdk()` (lines 61-94) dispatches on `isinstance(cred, OAuthCredential)` as the explicit first branch; `isinstance(cred, ApiKeyCredential)` is the second; `else: raise TypeError(...)` guards unknown types. `test_oauth_stealth_headers` asserts `authorization == "Bearer sk-ant-oat-fake-token"` and `test_api_key_credential_headers` asserts `x-api-key` present and `x-app` absent — both PASSED. Header sets are mutually exclusive. |
| T-025-4 | Shared httpx client closed prematurely | mitigate | CLOSED | Grep for `aclose\|\.close()` in anthropic_client.py returns only docstring comment lines (12-13); no call sites. `test_does_not_close_shared_client` asserts `real_client.is_closed is False` after `create()` — PASSED. |

## Test Execution Evidence

```
tests/test_anthropic_client.py::test_no_x_api_key_with_oauth PASSED
tests/test_anthropic_client.py::test_oauth_stealth_headers PASSED
tests/test_anthropic_client.py::test_api_key_credential_headers PASSED
tests/test_anthropic_client.py::test_does_not_close_shared_client PASSED

4 passed in 0.38s
```

## Unregistered Threat Flags

None. SUMMARY.md for Plan 025-02 records two auto-fixed bugs during implementation
(User-Agent casing and `inspect.isawaitable()` for stream mock compatibility); neither
constitutes a new security threat — both are correctness issues in test infrastructure,
not attack surface.

## Accepted Risks Log

None. All four threats are mitigated with code evidence and passing tests.
