---
phase: 027-model-profile-resolver
security_auditor: gsd-security-auditor
asvs_level: 1
block_on: high
audited: 2026-05-03
result: SECURED
threats_open: 0
threats_total: 9
---

# SECURITY.md — Phase 027: Model Profile Resolver

**Result: SECURED**
**Threats Closed:** 9/9
**ASVS Level:** 1
**block_on:** high (no high-severity threats open)

---

## Threat Verification

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-027-P1-1 | Test integrity | mitigate | CLOSED — Wave 0 stubs used `pytest.fail("RED: ...")` pattern. SUMMARY 027-01 confirms "17 FAILED, 0 passed" RED state before implementation. |
| T-027-P1-2 | Import safety | accept | CLOSED — ImportError on missing modules is an accepted RED-state condition, documented in Plan 01 threat model. No mitigation required. |
| T-027-P1-3 | Test isolation | mitigate | CLOSED — `test_no_mode_silo_import` uses `inspect.getsource()` pattern (src/state_core/providers/model_profile.py line 229). Verified: passes GREEN with real assertion, no pytest.fail(). |
| T-027-1 | Input injection | mitigate | CLOSED — `handle_chat_params` catches `ValueError` from `ModelProfile(step_profile_raw)` coercion; falls back to `step_profile = None`. Verified live: `handle_chat_params({'step_profile': 'malicious_payload'})` returns temperature=0.5, options={} (balanced fallback). src/state_daemon/hooks.py lines 53-62. |
| T-027-2 | Proto pollution | mitigate | CLOSED — `ResolvedProfile` has `ConfigDict(extra="forbid", frozen=True)`. Verified live: `ResolvedProfile(..., __class__='injected')` raises `ValidationError`. src/state_core/providers/model_profile.py line 55. Overrides are NOT accepted via HTTP body in Phase 027. |
| T-027-3 | Integer overflow | accept | CLOSED — `thinking_budget_tokens=4000` comes from hardcoded `_DEFAULTS` (model_profile.py line 94), not HTTP input. Accepted risk in Phase 027; Phase 029 adds Anthropic-SDK-level validation. Docstring note at line 82-84 documents this. |
| T-027-4 | Mode isolation | mitigate | CLOSED — grep of both implementation files returns no `state_build` or `state_teach` strings. `test_no_mode_silo_import` enforces at test-run time. src/state_core/providers/model_profile.py lines 12-14 (docstring uses "imports are limited to stdlib, pydantic, pydantic_settings, and structlog only"). |
| T-027-5 | KeyError / inherit propagation | mitigate | CLOSED — Explicit guard in `resolve_profile()`: `if resolved_name == ModelProfile.inherit: resolved_name = ModelProfile.balanced` (model_profile.py lines 153-154). Verified live: `resolve_profile(global_profile=ModelProfile.inherit)` returns profile=balanced. Hypothesis test `test_resolve_never_returns_inherit` exhaustively confirms this. |

### Plan 01 threats (test-only wave)

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-027-P1-1 | Test integrity | mitigate | CLOSED — pytest.fail() pattern confirmed in test_model_profile.py; all non-mode-isolation stubs used this form. |
| T-027-P1-2 | Import safety | accept | CLOSED — accepted by design; ImportError is expected RED state. |
| T-027-P1-3 | Test false-positive | mitigate | CLOSED — test_no_mode_silo_import (test_model_profile.py line 225) uses inspect.getsource() real assertion, not pytest.fail(). |

---

## Accepted Risks

| Threat ID | Risk | Rationale | Future Phase |
|-----------|------|-----------|--------------|
| T-027-P1-2 | ImportError on missing modules during Wave 0 | Expected TDD RED state; no security surface — test runner never reaches handler logic | N/A |
| T-027-3 | `thinking_budget_tokens` has no negative/overflow guard in Phase 027 | Value sourced from hardcoded `_DEFAULTS` (4000), not HTTP input. AnthropicClient rejects negatives at SDK level. | Phase 029 |

---

## Unregistered Flags

None. No `## Threat Flags` section was present in either 027-01-SUMMARY.md or 027-02-SUMMARY.md.

---

## Verification Commands Run

All commands executed against the live codebase on 2026-05-03:

| Command | Result |
|---------|--------|
| `handle_chat_params({'step_profile': 'malicious_payload'})` | temperature=0.5, options={} (balanced fallback) — T-027-1 CLOSED |
| `ResolvedProfile(..., __class__='injected')` | ValidationError raised — T-027-2 CLOSED |
| `grep "state_build\|state_teach" model_profile.py hooks.py` | No output — T-027-4 CLOSED |
| `resolve_profile(global_profile=ModelProfile.inherit)` | profile=balanced — T-027-5 CLOSED |
| `pytest tests/test_model_profile.py tests/test_hooks.py -q` | 20 passed in 0.85s — all mitigations test-verified |
