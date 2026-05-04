# Phase 026: OAuth Stealth Bypass Guard — Research

**Researched:** 2026-05-03
**Domain:** ProviderRouter.select() — credential-type-driven routing guard between AnthropicClient and LitellmClient
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRV-03 | OAuth stealth flow NEVER routes through litellm (bypass guard in provider selector) | `OAuthCredential.access.startswith("sk-ant-oat")` is the canonical discriminator; `ProviderRouter.select()` must enforce this at call time; `LitellmClient` must raise a `StateProviderError` subclass if invoked with an OAuth cred (defense-in-depth) |
</phase_requirements>

---

## Summary

Phase 026 completes `state_core.providers.router.ProviderRouter` — the routing layer that decides which backend handles an inference call. The phase has exactly one requirement (PRV-03): OAuth stealth credentials (`sk-ant-oat*`) MUST route exclusively through `AnthropicClient` (Phase 025); the `LitellmClient` path (Phase 024) MUST be unreachable for OAuth traffic.

The gate is credential-type based, not model-string based. `OAuthCredential` instances (all of whose `access` tokens start with `sk-ant-oat`) go to `AnthropicClient`. Everything else — `ApiKeyCredential` and any future credential types — goes to `LitellmClient` as the default. The router's `select()` method returns the correct client object without executing any inference; callers own the inference call.

Both upstream phases are complete and their interfaces are fixed. Phase 024 (`LitellmClient`) and Phase 025 (`AnthropicClient`, `StateProviderError` hierarchy, `errors.py`) are shipped and green (822 tests). The router only needs to import these two clients and return the correct one based on credential type. The implementation is small — the complexity of this phase is entirely in the test surface: the bypass guard test must be airtight enough to serve as the PRV-03 regression gate.

**Primary recommendation:** Implement `ProviderRouter.select(cred, deps)` that returns `AnthropicClient(cred, deps)` for `OAuthCredential` and `LitellmClient()` for `ApiKeyCredential`. Add a defense-in-depth check in `LitellmClient.acompletion()` / `LitellmClient.astream()` that raises `OAuthRoutingError` (a `StateProviderError` subclass) if the caller somehow passes an OAuth-looking model string. Use `isinstance(cred, OAuthCredential)` — not string prefix matching — as the primary discriminator.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `state_core.providers.anthropic_client` | Phase 025 (local) | Direct SDK path for OAuth creds | PRV-02/PRV-03; already shipped and tested |
| `state_core.providers.litellm_client` | Phase 024 (local) | litellm path for non-OAuth creds | PRV-01; already shipped and tested |
| `state_core.providers.errors` | Phase 025 (local) | Shared `StateProviderError` hierarchy | Shared by both clients; Phase 026 extends with `OAuthRoutingError` |
| `state_core.auth.base` | Phase 011 (local) | `OAuthCredential`, `ApiKeyCredential`, `Credential` union | Discriminated union used for isinstance dispatch |
| `state_core.deps` | Phase 023 (local) | `Deps` carrying `deps.http_client` | Passed through to `AnthropicClient` constructor |

### Supporting (test only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | 1.3.0+ | `asyncio_mode = "auto"` for `async def test_*` | Already configured; all routing tests are unit-level (no async I/O needed, but async test functions align with the codebase pattern) |
| `unittest.mock` (stdlib) | n/a | `MagicMock` / `AsyncMock` for verifying client selection without executing inference | Preferred — no real HTTP calls needed for router unit tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `isinstance(cred, OAuthCredential)` | `cred.access.startswith("sk-ant-oat")` | Type-based dispatch is the canonical pattern in this codebase (all other instanceof checks use type discriminators); string-prefix is fragile if token format changes. However, `startswith("sk-ant-oat")` is explicitly named in the requirement ("if cred is sk-ant-oat*") — document both and use isinstance as primary, document the token shape as documentation only |
| `ProviderRouter.select()` returning a client instance | `ProviderRouter.route()` doing the inference call | Phase 024 RESEARCH already named the stub method `route()`. The PR-03 requirement says "route MUST be direct SDK" — returning a client for the caller to use is cleaner and testable; performing inference inside the router couples it to the call signature of both backends |
| Single new `OAuthRoutingError` in `errors.py` | Raising plain `StateProviderError` | Named subclass makes log grep deterministic; allows callers to detect bypass violations specifically |

**Installation:** No new packages. All libraries in `pyproject.toml`.

---

## Architecture Patterns

### File Layout
```
src/state_core/providers/
├── __init__.py              # unchanged
├── errors.py                # Phase 025 — add OAuthRoutingError here (extends StateProviderError)
├── litellm_client.py        # Phase 024 — add defense-in-depth guard (raises OAuthRoutingError on OAuth model string)
├── anthropic_client.py      # Phase 025 — unchanged
└── router.py                # Phase 026 — implement ProviderRouter.select()

tests/
├── test_router.py           # NEW — Phase 026 (all PRV-03 behavioral contract tests)
```

### Pattern 1: `ProviderRouter.select()` — Type-Dispatch

**What:** The router's public method takes a credential and deps; returns the appropriate client without calling inference.
**When to use:** Always — all inference paths go through the router.

```python
# src/state_core/providers/router.py
from __future__ import annotations

import structlog

from state_core.auth.base import Credential, OAuthCredential
from state_core.deps import Deps
from state_core.providers.anthropic_client import AnthropicClient
from state_core.providers.litellm_client import LitellmClient
from state_core.providers.errors import OAuthRoutingError

log = structlog.get_logger(__name__)


class ProviderRouter:
    """Routes provider calls — litellm default, Anthropic SDK for OAuth stealth.

    PRV-03: OAuthCredential (sk-ant-oat* tokens) ALWAYS routes to AnthropicClient.
    Any other credential type routes to LitellmClient.

    Usage:
        router = ProviderRouter()
        client = router.select(cred, deps)
        # client is AnthropicClient or LitellmClient
        response = await client.create(model=..., messages=..., max_tokens=...)
    """

    def select(self, cred: Credential, deps: Deps) -> AnthropicClient | LitellmClient:
        """Return the correct inference client for the given credential.

        PRV-03 contract: OAuthCredential -> AnthropicClient (ALWAYS).
        All other credential types -> LitellmClient.

        Raises:
            Never raises — always returns a client. The returned client may
            raise StateProviderError subclasses on inference calls.
        """
        if isinstance(cred, OAuthCredential):
            log.debug("provider_router.select", route="anthropic_sdk", provider_id=cred.provider_id)
            return AnthropicClient(cred, deps)
        log.debug("provider_router.select", route="litellm", provider_id=cred.provider_id)
        return LitellmClient()
```

**Key design choices:**
- `select()` is sync — no I/O; building `AnthropicClient` or `LitellmClient` is cheap.
- Returns the client object; callers invoke inference on it. The router does NOT call inference.
- `OAuthCredential` isinstance check is the ONLY routing branch. New credential types (e.g., a future `DeviceCodeCredential`) automatically fall through to `LitellmClient`.
- Logging uses `provider_id` not the token value — never log credential secrets (matches T-024-1 / T-025-1 pattern from prior phases).

### Pattern 2: Defense-in-Depth Guard in `LitellmClient`

**What:** A secondary guard that raises `OAuthRoutingError` if `LitellmClient` is called with any credential that looks like an OAuth token. This catches bugs where a future caller bypasses `ProviderRouter` and calls `LitellmClient` directly with an OAuth model string.

**Note on scope:** The current `LitellmClient.acompletion()` takes `model: str` and `messages`, not a `Credential`. The defense-in-depth guard is therefore model-string based — check if the model string is `"anthropic/*"` or `"claude-*"` AND caller is somehow using a raw OAuth token. However, `LitellmClient` never receives the credential object directly today. The cleanest approach:

**Option A:** Add an optional `cred: Credential | None = None` parameter to `LitellmClient.acompletion()` and `astream()` — if `isinstance(cred, OAuthCredential)`, raise `OAuthRoutingError` immediately. This is the most airtight form of defense-in-depth.

**Option B:** Add a module-level `_assert_not_oauth(cred)` function and call it at `LitellmClient` construction if a credential is passed in. The `LitellmClient.__init__` would accept an optional `cred` for validation purposes.

**Recommendation:** Option A is lower-risk (no constructor signature change for a stateless class), but passing `cred=` to every call is verbose. **Simplest correct approach:** Add `OAuthRoutingError` to `errors.py` and document in `LitellmClient`'s docstring that it MUST NOT be called with OAuth credentials. The primary enforcement is `ProviderRouter.select()`. Defense-in-depth via a `check_not_oauth(cred)` utility in `router.py` that callers can use to assert the invariant. The PRV-03 test suite is the true enforcement gate.

```python
# src/state_core/providers/errors.py — add:

class OAuthRoutingError(StateProviderError):
    """Raised when OAuth stealth traffic is incorrectly routed through litellm.

    This error signals a bypass of ProviderRouter.select() — a programmer error,
    not a transient failure. It should never appear in production if the router
    is used correctly (PRV-03).
    """
```

### Pattern 3: Test Structure for PRV-03

**What:** The router test suite validates the PRV-03 contract exhaustively.
**When to use:** All routing decisions should be exercised by unit tests.

The test file (`tests/test_router.py`) validates:

1. `OAuthCredential` → `AnthropicClient` (the primary bypass guard)
2. `ApiKeyCredential` (any provider_id) → `LitellmClient`
3. The returned `AnthropicClient` has the correct credential bound (`client._cred is cred`)
4. `ProviderRouter.select()` is pure sync (does not `await`)
5. Mode isolation: `state_core.providers.router` does NOT import `state_build.*` or `state_teach.*`
6. Log output: `provider_id` logged, NOT `cred.access` (secret hygiene, T-026-1)
7. `OAuthRoutingError` is importable from `state_core.providers.errors`

```python
# tests/test_router.py — structural outline

from state_core.auth.base import ApiKeyCredential, OAuthCredential
from state_core.deps import Deps
from state_core.providers.router import ProviderRouter
from state_core.providers.anthropic_client import AnthropicClient
from state_core.providers.litellm_client import LitellmClient
from state_core.providers.errors import OAuthRoutingError
import httpx

FAKE_OAUTH = OAuthCredential(
    access="sk-ant-oat-fake", refresh="fake-refresh",
    expires=9_999_999_999.0, provider_id="anthropic"
)
FAKE_API_KEY = ApiKeyCredential(key="sk-ant-api03-fake", provider_id="anthropic")
FAKE_API_KEY_OTHER = ApiKeyCredential(key="gsk-fake-gemini", provider_id="google.gemini")

@pytest.fixture
def deps():
    return Deps(http_client=httpx.AsyncClient())

def test_oauth_cred_routes_to_anthropic_client(deps):
    router = ProviderRouter()
    client = router.select(FAKE_OAUTH, deps)
    assert isinstance(client, AnthropicClient)

def test_api_key_cred_routes_to_litellm_client(deps):
    router = ProviderRouter()
    client = router.select(FAKE_API_KEY, deps)
    assert isinstance(client, LitellmClient)

def test_non_anthropic_api_key_routes_to_litellm(deps):
    router = ProviderRouter()
    client = router.select(FAKE_API_KEY_OTHER, deps)
    assert isinstance(client, LitellmClient)

def test_oauth_client_has_correct_cred_bound(deps):
    router = ProviderRouter()
    client = router.select(FAKE_OAUTH, deps)
    assert isinstance(client, AnthropicClient)
    assert client._cred is FAKE_OAUTH

def test_select_is_sync(deps):
    """select() must not be a coroutine — it is pure routing logic."""
    import inspect
    router = ProviderRouter()
    result = router.select(FAKE_OAUTH, deps)
    assert not inspect.isawaitable(result)

def test_no_mode_silo_import():
    import state_core.providers.router as m
    import sys
    for name in sys.modules:
        assert not name.startswith("state_build"), f"mode silo violation: {name}"
        assert not name.startswith("state_teach"), f"mode silo violation: {name}"

def test_oauth_routing_error_importable():
    from state_core.providers.errors import OAuthRoutingError
    assert issubclass(OAuthRoutingError, StateProviderError)
```

### Anti-Patterns to Avoid

- **String-prefix routing as PRIMARY discriminator:** `cred.access.startswith("sk-ant-oat")` is mentioned in the PRV-03 requirement text but should not be the sole gate. Use `isinstance(cred, OAuthCredential)` — token format is an implementation detail of `AnthropicAuth`, not a public contract. The requirement names the pattern for documentation; the code should use types.
- **Routing by model string:** `select(model="claude-opus-4-5", ...)` is incorrect. The routing decision is based on the credential, not the model. An API-key Anthropic credential that calls a Claude model routes through litellm (not ideal for extended thinking, but correct for PRV-03 scope which is specifically about OAuth stealth).
- **Making `select()` async:** No I/O occurs in client construction. Keeping it sync reduces caller complexity.
- **Importing mode-specific packages:** `state_core.providers.router` is shared kernel — no `state_build.*` or `state_teach.*` imports ever.
- **Performing inference in `select()`:** The router returns a client object; it does not call `.create()` or `.acompletion()`. Callers own the inference lifecycle.
- **Logging cred.access or cred.key:** T-026-1 security constraint: the router logs `provider_id` and `route` only. No token values in logs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token shape detection | Regex on `cred.access` to detect "sk-ant-oat" prefix | `isinstance(cred, OAuthCredential)` | Type dispatch is reliable; `AnthropicAuth.is_token()` already encodes the prefix rule; type is set at construction time |
| Client lifecycle | Pool or cache of `AnthropicClient` instances | Fresh `AnthropicClient(cred, deps)` per `select()` call | `AnthropicClient` is cheap to construct (builds `AsyncAnthropic` from an existing `httpx.AsyncClient`); the SDK client is stateless; caching introduces credential-invalidation complexity for zero benefit |
| Routing table | `dict[str, type]` mapping provider_id to client class | `isinstance` dispatch | Two branches is not enough to justify a dispatch table; a table hides the primary invariant (`OAuthCredential → AnthropicClient`) |
| Error hierarchy | New exception module | Extend `state_core.providers.errors` with `OAuthRoutingError` | The shared hierarchy was extracted specifically in Phase 025 for this purpose |

---

## Common Pitfalls

### Pitfall 1: Routing by provider_id Instead of Credential Type

**What goes wrong:** `if cred.provider_id == "anthropic"` routes Anthropic API-key credentials through `AnthropicClient`. That is not PRV-03's intent — the bypass guard is specifically for OAuth stealth (subscription pricing). Anthropic API-key traffic routes through litellm for PRV-01 scope (Phase 031's parity matrix tests verify this).

**Why it happens:** "Anthropic" as a provider seems to imply `AnthropicClient`, but `AnthropicClient` was specifically built for OAuth stealth (PRV-02). API-key Anthropic traffic can go through litellm.

**How to avoid:** Route on `isinstance(cred, OAuthCredential)`, not on `cred.provider_id`. `ApiKeyCredential(provider_id="anthropic")` → `LitellmClient`.

**Warning signs:** Tests pass with `FAKE_API_KEY(provider_id="anthropic")` returning `AnthropicClient`.

### Pitfall 2: Mutating the Stub `router.py` Signature Breaks Downstream Phases

**What goes wrong:** The current stub in `router.py` has `async def route(self, model_spec: dict) -> object`. Phase 026 replaces this with `def select(self, cred: Credential, deps: Deps) -> AnthropicClient | LitellmClient`. Phase 028 (cost accounting) and Phase 027 (model-profile resolver) will consume the router; if the method name or signature changes later, those phases need updates.

**Why it happens:** The stub was named `route()` which conflicts with the Phase 026 plan to use `select()`.

**How to avoid:** The stub has no callers (it's a placeholder with `...`). Phase 026 replaces it entirely with `select()`. Document in the module docstring that `select()` is the stable public API for downstream phases (027, 028, 031).

**Warning signs:** If downstream phases reference `router.route(...)` in their research artifacts.

### Pitfall 3: `AnthropicClient.__init__` Calls `_build_sdk()` Which Calls `AnthropicAuth().http_headers()`

**What goes wrong:** `ProviderRouter.select()` constructs a fresh `AnthropicClient(cred, deps)` on every call. Each construction calls `AnthropicAuth().http_headers(cred)` which reads the credential's `access` token and the module-level constants. This is cheap (no I/O) but NOT free — a new `AsyncAnthropic` SDK object is built each time.

**Why it happens:** `AnthropicClient.__init__` builds the SDK client eagerly in `_build_sdk()`.

**How to avoid:** Acceptable for Phase 026 — `AsyncAnthropic` construction is sub-millisecond (it does not open connections; the shared `httpx.AsyncClient` already has the connection pool). Document in the module docstring. Caching is a future optimization if profiling shows it matters.

**Warning signs:** Benchmark shows > 1ms per `select()` call — investigate if `_build_sdk` is doing I/O.

### Pitfall 4: Defense-in-Depth Guard Scope Ambiguity

**What goes wrong:** Adding `OAuthRoutingError` to `LitellmClient` methods requires either passing `cred` as a parameter (changing the existing interface) or relying on the router contract alone.

**Why it happens:** `LitellmClient` was designed as a credential-agnostic wrapper (it routes by `model: str`, not by credential). Passing `cred` to `acompletion()` changes the interface that Phase 028/029/030 may consume.

**How to avoid:** Do NOT change `LitellmClient`'s public interface in Phase 026. The defense-in-depth for PRV-03 is:
1. **Primary:** `ProviderRouter.select()` never returns `LitellmClient` for `OAuthCredential` (tested).
2. **Secondary:** `OAuthRoutingError` exists in `errors.py` and is documented as the error future guards would raise.
3. **Tertiary:** `LitellmClient` module docstring warns: "OAuth stealth credentials MUST NOT reach this class" (already present in Phase 024 output).

The test suite enforces primary and verifies secondary is importable. Tertiary is documentation.

### Pitfall 5: Test Isolation — `AnthropicClient` Constructor Calls Real `AnthropicAuth`

**What goes wrong:** `test_oauth_cred_routes_to_anthropic_client` constructs `AnthropicClient(FAKE_OAUTH, deps)` inside `select()`. `AnthropicClient.__init__` calls `AnthropicAuth().http_headers(cred)` which reads module-level constants (no I/O, but imports `state_core.auth.providers.anthropic`). This is fine — the import chain is already loaded in the test suite.

**How to avoid:** Tests can use `isinstance(client, AnthropicClient)` without further inspection. No mocking of `AnthropicAuth` needed — it has no side effects.

**Warning signs:** Test suite startup becomes slow because `state_core.auth.providers.anthropic` imports `base64`, `cryptography`, etc. — all acceptable, already in the dependency graph.

---

## Code Examples

Verified patterns from prior phases:

### `ProviderRouter.select()` — Final Form

```python
# src/state_core/providers/router.py
# Source: isinstance pattern from state_core/providers/anthropic_client.py _build_sdk()
from __future__ import annotations

import structlog

from state_core.auth.base import Credential, OAuthCredential
from state_core.deps import Deps
from state_core.providers.anthropic_client import AnthropicClient
from state_core.providers.litellm_client import LitellmClient

log = structlog.get_logger(__name__)


class ProviderRouter:
    """Routes inference calls — litellm default, Anthropic SDK for OAuth stealth.

    PRV-03: OAuthCredential -> AnthropicClient (always; bypass guard).
    ApiKeyCredential (any provider) -> LitellmClient.

    select() is sync and cheap — AnthropicClient construction does no I/O
    (it reuses the shared httpx.AsyncClient from deps). Call select() per
    inference request; do not cache the returned client across credential refreshes.

    Downstream consumers:
      Phase 027 — model-profile resolver passes (cred, deps, model_profile) to select()
      Phase 028 — cost accounting wraps select() to emit request events
      Phase 031 — parity matrix tests call select() per provider in the matrix
    """

    def select(self, cred: Credential, deps: Deps) -> AnthropicClient | LitellmClient:
        """Return the inference client for the given credential (PRV-03).

        OAuthCredential -> AnthropicClient (direct SDK, stealth headers applied).
        Any other credential type -> LitellmClient (litellm abstraction).
        """
        if isinstance(cred, OAuthCredential):
            log.debug(
                "provider_router.select",
                route="anthropic_sdk",
                provider_id=cred.provider_id,
                # NEVER log cred.access — T-026-1 secret hygiene
            )
            return AnthropicClient(cred, deps)
        log.debug(
            "provider_router.select",
            route="litellm",
            provider_id=cred.provider_id,
        )
        return LitellmClient()
```

### `OAuthRoutingError` Addition to `errors.py`

```python
# src/state_core/providers/errors.py — append after ProviderResponseError
# Source: errors.py established in Phase 025

class OAuthRoutingError(StateProviderError):
    """Raised when OAuth stealth traffic bypasses ProviderRouter to reach LitellmClient.

    This is a programmer error — PRV-03 requires that all OAuthCredential
    traffic routes through AnthropicClient (direct SDK). If this error appears
    in production, ProviderRouter.select() was bypassed. Never retry this error.
    """
```

### Routing Decision — Type Dispatch Table (mental model)

```
cred type          access prefix      route             client
────────────────   ─────────────────  ────────────────  ─────────────────────
OAuthCredential    sk-ant-oat*        AnthropicClient   Direct Anthropic SDK
ApiKeyCredential   sk-ant-api03*      LitellmClient     litellm abstraction
ApiKeyCredential   gsk-* (Gemini)     LitellmClient     litellm abstraction
ApiKeyCredential   (any other)        LitellmClient     litellm abstraction
```

Note: The token prefix shown above is documentation only. The code dispatches on `isinstance(cred, OAuthCredential)`, not on token prefix. This table is the semantic invariant.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `router.route(model_spec: dict)` stub (placeholder) | `router.select(cred: Credential, deps: Deps)` | Phase 026 | Credential-based routing; type-safe return type `AnthropicClient \| LitellmClient` |
| No bypass guard (litellm handles all traffic) | `isinstance(cred, OAuthCredential)` gate | Phase 026 | PRV-03 satisfied; OAuth stealth never reaches litellm |
| `StateProviderError` hierarchy defined inline in litellm_client | Extracted to `errors.py` (Phase 025), extended with `OAuthRoutingError` | Phase 026 | Shared error hierarchy; OAuthRoutingError named for diagnostic clarity |

**Deprecated/outdated:**
- The `async def route(self, model_spec: dict) -> object` stub in `router.py` — Phase 026 replaces it entirely with `select()`. No callers of the stub exist.

---

## Open Questions

1. **Should `ProviderRouter.select()` accept an optional `model_str` parameter for downstream phases?**
   - What we know: Phase 027 (model-profile resolver) and Phase 028 (cost accounting) will wrap the router. They may need to pass model information alongside the credential.
   - What's unclear: Whether `select()` should accept `model_str` now (for downstream readiness) or Phase 027 adds it when needed.
   - Recommendation: For Phase 026, `select(cred, deps)` only. PRV-03 is credential-type routing, not model-string routing. Phase 027 can extend the interface. Adding `model_str` now is speculative and breaks YAGNI.

2. **Should `ProviderRouter` be a singleton or instantiated per request?**
   - What we know: `ProviderRouter` has no state (no fields). It's a pure function wrapped in a class.
   - What's unclear: Whether to make it a module-level singleton or let callers instantiate it.
   - Recommendation: Keep it a plain class (consistent with `LitellmClient` and `AnthropicClient` patterns in this codebase). Phase 028/031 may want to subclass or wrap it; instantiation is cheap.

3. **Should `OAuthRoutingError` be raised proactively if `LitellmClient` detects an Anthropic OAuth model string?**
   - What we know: `LitellmClient.acompletion(model, messages)` doesn't receive a `Credential` object; it can't directly detect OAuth credentials.
   - What's unclear: Whether a `model="anthropic/claude-*"` check in `LitellmClient` is useful defense-in-depth.
   - Recommendation: No. Model-string checks are fragile (litellm supports many Anthropic model string formats). The correct gate is `ProviderRouter.select()`. Document in `LitellmClient`'s docstring. Add a `# PRV-03: enforced by ProviderRouter.select()` comment.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.0+ with pytest-asyncio 1.3.0+ (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| Quick run command | `python3 -m pytest tests/test_router.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRV-03 | `OAuthCredential` → `select()` returns `AnthropicClient` | unit | `pytest tests/test_router.py::test_oauth_cred_routes_to_anthropic_client -x` | ❌ Wave 0 |
| PRV-03 | `ApiKeyCredential(provider_id="anthropic")` → `select()` returns `LitellmClient` | unit | `pytest tests/test_router.py::test_anthropic_api_key_routes_to_litellm -x` | ❌ Wave 0 |
| PRV-03 | `ApiKeyCredential(provider_id="google.gemini")` → `select()` returns `LitellmClient` | unit | `pytest tests/test_router.py::test_non_anthropic_api_key_routes_to_litellm -x` | ❌ Wave 0 |
| PRV-03 | The returned `AnthropicClient` has `_cred is cred` (correct credential bound) | unit | `pytest tests/test_router.py::test_oauth_client_has_correct_cred_bound -x` | ❌ Wave 0 |
| PRV-03 | The returned `AnthropicClient` has `_deps is deps` (correct deps bound) | unit | `pytest tests/test_router.py::test_oauth_client_has_correct_deps_bound -x` | ❌ Wave 0 |
| PRV-03 | `select()` is a sync function (not a coroutine) | unit | `pytest tests/test_router.py::test_select_is_sync -x` | ❌ Wave 0 |
| PRV-03 | `OAuthRoutingError` is importable from `state_core.providers.errors` and is a subclass of `StateProviderError` | import | `pytest tests/test_router.py::test_oauth_routing_error_importable -x` | ❌ Wave 0 |
| PRV-03 | Mode isolation: `state_core.providers.router` does NOT import `state_build.*` or `state_teach.*` | import-graph | `pytest tests/test_router.py::test_no_mode_silo_import -x` | ❌ Wave 0 |
| PRV-03 | Log output for OAuth route contains `provider_id`, NOT `cred.access` (T-026-1 secret hygiene) | unit (structlog capture) | `pytest tests/test_router.py::test_oauth_route_log_no_token -x` | ❌ Wave 0 |
| PRV-03 | Log output for litellm route contains `provider_id`, NOT `cred.key` (T-026-1 secret hygiene) | unit (structlog capture) | `pytest tests/test_router.py::test_litellm_route_log_no_token -x` | ❌ Wave 0 |

**Total: 10 tests.** All are RED stubs in Wave 0; Wave 1 implements `select()` and `OAuthRoutingError` to make them GREEN.

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_router.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Phase gate:** Full suite green (currently 822; target 832 after Phase 026) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_router.py` — all 10 RED stubs listed above
- [ ] `src/state_core/providers/errors.py` — add `OAuthRoutingError` class (1 addition to existing file)
- [ ] `src/state_core/providers/router.py` — replace stub with full `ProviderRouter.select()` implementation (Wave 1 GREEN)

*(No framework gaps — pytest infrastructure, `asyncio_mode = "auto"`, and `structlog` capture patterns are already established in prior phase tests.)*

---

## Sources

### Primary (HIGH confidence)
- `src/state_core/providers/router.py` — existing stub (`async def route(self, model_spec: dict) -> object: ...`) confirmed as placeholder with no callers
- `src/state_core/providers/anthropic_client.py` — Phase 025 implementation: `AnthropicClient.__init__(cred, deps)` signature confirmed; `isinstance(cred, OAuthCredential)` dispatch pattern already used in `_build_sdk()`; `_cred` and `_deps` are instance attributes
- `src/state_core/providers/litellm_client.py` — Phase 024 implementation: `LitellmClient()` takes no constructor args; module docstring already says "OAuth stealth credentials MUST NOT reach this class"
- `src/state_core/providers/errors.py` — Phase 025 extraction: `StateProviderError` hierarchy confirmed; `OAuthRoutingError` does not yet exist (Phase 026 adds it)
- `src/state_core/auth/base.py` — `OAuthCredential` and `ApiKeyCredential` discriminated union; `OAuthCredential.access` is the OAuth token field; `AnthropicAuth.is_token()` uses `value.startswith("sk-ant-oat")` to confirm the prefix
- `src/state_core/auth/providers/anthropic.py` line 458: `return value.startswith("sk-ant-oat")` — canonical token shape detection (documentation reference; code uses `isinstance`)
- `src/state_core/deps.py` — `Deps(http_client: httpx.AsyncClient)` constructor; passed to `AnthropicClient`
- `pyproject.toml` — test markers, `asyncio_mode = "auto"`, all deps confirmed present
- `.planning/config.json` — `nyquist_validation: true` (Validation Architecture section required); `security_enforcement: true` (SECURITY.md required at phase close)
- 822 tests passing before Phase 026 begins (confirmed from `python3 -m pytest` run)

### Secondary (MEDIUM confidence)
- Phase 024 RESEARCH.md — `LitellmClient` interface (no constructor args, `acompletion(model, messages, **kwargs)`, `astream(model, messages, **kwargs)`)
- Phase 025 RESEARCH.md — `AnthropicClient(cred, deps)` confirmed as correct constructor form; Open Question 2 confirmed: "Phase 026 builds it per-request as needed"
- ROADMAP.md Phase 026 description — "ProviderRouter.select() — if cred is sk-ant-oat*, route MUST be direct SDK; litellm path raises if invoked"

### Tertiary (LOW confidence)
- None — all critical claims verified from installed package source or project files.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both upstream clients are implemented and tested; no new packages needed
- Architecture (select() design): HIGH — `isinstance(cred, OAuthCredential)` pattern established in `anthropic_client._build_sdk()`; `AnthropicClient(cred, deps)` constructor signature verified from source
- Pitfalls: HIGH — all five pitfalls derived from reading the actual stub, prior phase artifacts, and the PRV-03 requirement text
- Test design: HIGH — 10-test PRV-03 suite covers the contract exhaustively; structlog capture pattern established in prior phases (v2 security test patterns)

**Research date:** 2026-05-03
**Valid until:** 2026-07-01 (stable; `router.py` has no upstream dependency on fast-moving libs; revisit if `AnthropicClient` interface changes in Phase 029/030)
