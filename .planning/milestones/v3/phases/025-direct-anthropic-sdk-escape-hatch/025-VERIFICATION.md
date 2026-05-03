---
phase: 025-direct-anthropic-sdk-escape-hatch
verified: 2026-05-03T17:30:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 025: Direct Anthropic SDK Escape Hatch Verification Report

**Phase Goal:** Implement the direct Anthropic SDK escape hatch (AnthropicClient) for OAuth stealth inference, extended thinking passthrough, and cache-control passthrough. Shared error hierarchy extracted from litellm_client to errors.py.
**Verified:** 2026-05-03T17:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AnthropicClient.create() sends POST to https://api.anthropic.com/v1/messages?beta=true using the shared httpx.AsyncClient | VERIFIED | test_uses_shared_http_client PASSED; test_create_posts_to_correct_url PASSED; http_client=deps.http_client on line 67 and 86 of anthropic_client.py |
| 2 | OAuthCredential path sends x-app: cli, user-agent: claude-cli/2.1.121 (external, cli), authorization: Bearer token, anthropic-beta: oauth-2025-04-20,... | VERIFIED | test_oauth_stealth_headers PASSED; User-Agent/x-app/anthropic-beta set from AnthropicAuth().http_headers(); auth_token=cred.access sets Bearer |
| 3 | X-Api-Key header is absent from OAuth requests even when ANTHROPIC_API_KEY env var is set | VERIFIED | test_no_x_api_key_with_oauth PASSED; "X-Api-Key": omit in default_headers (line 72 of anthropic_client.py) |
| 4 | ApiKeyCredential path sends x-api-key header, no stealth headers | VERIFIED | test_api_key_credential_headers PASSED; separate _build_sdk branch for ApiKeyCredential |
| 5 | thinking= param is passed through to messages.create(); ThinkingBlock in response is preserved in returned Message | VERIFIED | test_thinking_budget_passed_through, test_thinking_blocks_preserved, test_adaptive_thinking_accepted — all PASSED |
| 6 | cache_control= param is passed through; response.usage.cache_creation_input_tokens and cache_read_input_tokens are preserved | VERIFIED | test_cache_control_passed_through, test_cache_usage_preserved, test_cache_read_tokens_preserved — all PASSED |
| 7 | anthropic.APIConnectionError maps to ProviderTransientError; 401 maps to ProviderAuthError; 400 maps to ProviderBadRequestError | VERIFIED | test_connection_error_maps_to_transient, test_auth_error_maps_to_auth_error, test_bad_request_maps_to_bad_request — all PASSED |
| 8 | AnthropicClient never calls aclose() on the shared httpx client | VERIFIED | test_does_not_close_shared_client PASSED; grep for aclose/close() in anthropic_client.py returns empty |
| 9 | StateProviderError hierarchy is importable from state_core.providers.errors (not from litellm_client) | VERIFIED | test_errors_importable_from_errors_module PASSED; errors.py exists with all 5 classes; litellm_client.py imports from errors.py (no inline definitions) |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/state_core/providers/errors.py` | Shared StateProviderError hierarchy (5 classes) | VERIFIED | 49 lines; exports StateProviderError, ProviderTransientError, ProviderAuthError, ProviderBadRequestError, ProviderResponseError |
| `src/state_core/providers/anthropic_client.py` | AnthropicClient — direct SDK escape hatch | VERIFIED | 239 lines; AnthropicClient class with __init__, _build_sdk, create(), stream() |
| `src/state_core/providers/litellm_client.py` | Updated: imports from errors.py, no inline hierarchy | VERIFIED | `from state_core.providers.errors import (...)` at line 30; zero inline error class definitions remain |
| `tests/test_anthropic_client.py` | 18 test functions covering PRV-02, PRV-08, PRV-09 | VERIFIED | 512 lines; exactly 18 test functions confirmed by grep |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/state_core/providers/anthropic_client.py` | `state_core.providers.errors` | `from state_core.providers.errors import StateProviderError, ...` | WIRED | Line 37-42 of anthropic_client.py |
| `src/state_core/providers/anthropic_client.py` | `anthropic.AsyncAnthropic` | `AsyncAnthropic(auth_token=, http_client=deps.http_client, default_query={beta: true}, max_retries=0)` | WIRED | Lines 64-82 and 84-89 of anthropic_client.py |
| `src/state_core/providers/anthropic_client.py` | `state_core.auth.providers.anthropic.AnthropicAuth` | `AnthropicAuth().http_headers(cred)` in _build_sdk | WIRED | Line 62 of anthropic_client.py |
| `src/state_core/providers/litellm_client.py` | `state_core.providers.errors` | `from state_core.providers.errors import StateProviderError, ...` | WIRED | Lines 30-36 of litellm_client.py; inline class definitions removed |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PRV-02 | 025-01, 025-02 | Direct Anthropic SDK escape hatch for extended thinking and fine-grained cache-control | SATISFIED | AnthropicClient fully implemented; 11 tests cover transport, stealth headers, lifecycle, error mapping, import graph |
| PRV-08 | 025-01, 025-02 | Thinking-budget tag propagation (thinking.budget_tokens) for Anthropic extended thinking | SATISFIED | thinking= kwarg passed through create()/stream(); ThinkingBlock preserved in returned Message; 3 tests pass |
| PRV-09 | 025-01, 025-02 | Cache-control marker preservation end-to-end (client → provider → response accounting) | SATISFIED | cache_control= kwarg passed through; cache_creation_input_tokens and cache_read_input_tokens preserved in usage; 4 tests pass |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None found |

No TODO/FIXME/placeholder comments in any phase files. No empty implementations. No aclose() calls in anthropic_client.py.

### Human Verification Required

None. All goal behaviors are mechanically verifiable via pytest-httpx wire-level request interception:

- Stealth header correctness verified at the transport layer (not mocked)
- X-Api-Key suppression verified even when ANTHROPIC_API_KEY env var is present
- Shared client non-closure verified using real httpx.AsyncClient.is_closed property
- Error hierarchy verified via exception class assertions
- Thinking and cache-control passthrough verified by parsing request body JSON and response object attributes

## Step 7b: Quality Findings

Skipped (quality.level: fast)

### Gaps Summary

No gaps. All 9 observable truths are verified, all 4 artifacts substantively implemented and wired, all 3 requirements satisfied, and 820 unit tests pass with zero regressions.

**Full test suite:** 820 passed, 2 deselected (e2e/integration/provider_parity markers) in 61.81s.

---

_Verified: 2026-05-03T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
