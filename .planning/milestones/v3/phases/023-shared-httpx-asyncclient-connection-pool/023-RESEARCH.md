# Phase 023: Shared `httpx.AsyncClient` with Connection Pool + Proxy/TLS Config — Research

**Researched:** 2026-05-02
**Domain:** httpx AsyncClient lifecycle, connection pooling, proxy/TLS config, Anthropic SDK injection, litellm transport layer
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — discuss phase was skipped per `workflow.skip_discuss`. All implementation choices are at Claude's discretion.

### Claude's Discretion
All implementation choices. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None — discuss phase skipped.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRV-06 | Shared httpx client across daemon with connection pooling | httpx.AsyncClient with Limits, owned by daemon, injected via Deps container, wired to litellm via `litellm.aclient_session` and to Anthropic SDK via `AsyncAnthropic(http_client=...)` |
</phase_requirements>

---

## Summary

Phase 023 creates a single `httpx.AsyncClient` instance owned by the daemon, configured with connection pool limits, proxy support, and TLS/SSL options, and dep-injected via a `Deps` container/dataclass. This client must be shared across all provider HTTP traffic: the opencode sync mirror (already uses a per-instance client), litellm async completions, and the direct Anthropic SDK escape hatch.

The key architecture insight from STACK.md (pre-committed): "single `httpx.AsyncClient` owned by the daemon, injected via a `Deps` container into every caller. Litellm, the Anthropic SDK, and our opencode HTTP client all accept a user-provided httpx client — reuse the same one for connection pooling and unified proxy/TLS config." This phase delivers that pattern.

The critical constraint is that `litellm.aclient_session` is the global injection point for litellm (not a per-call parameter), and `AsyncAnthropic(http_client=...)` is the injection point for the Anthropic SDK. The `SyncEventMirror` already has `self._client = httpx.AsyncClient()` — this phase either migrates it to use the shared client or notes it uses a separate internal client for the opencode mirror path (lower priority, different traffic class).

**Primary recommendation:** Implement `state_core.http_client` module with a `SharedHttpxClient` class (or factory), create `state_core.deps.Deps` as a Pydantic BaseModel or dataclass holding the client, wire into daemon startup sequence after the existing step 3 (reconciler), and add `litellm.aclient_session` assignment + `AsyncAnthropic(http_client=...)` pattern. OAuth stealth traffic NEVER routes through litellm (per PRV-03) — the direct Anthropic path is the escape hatch, which still uses the shared httpx client.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | >=0.28.1 (already pinned) | Async HTTP client with connection pooling | Already in pyproject.toml; `AsyncClient` has `Limits`, proxy, TLS built-in |
| `ssl` (stdlib) | 3.12 built-in | Custom SSL contexts for TLS config | No extra dep; `ssl.create_default_context()` + `ssl.SSLContext` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | >=2.13.2 (already pinned) | `Deps` container model | Already pinned; `BaseModel` for the container is conventional in this codebase |
| `structlog` | >=25.1 (already pinned) | Lifecycle logging | Already pinned; consistent with rest of daemon startup |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic BaseModel for Deps | `dataclasses.dataclass` | Dataclass is lighter; but BaseModel is already used everywhere in this codebase and allows `model_config = ConfigDict(arbitrary_types_allowed=True)` for httpx.AsyncClient storage |
| Single global module-level client | Deps container injection | Global is simpler but untestable; Deps is the architecture mandate from STACK.md |

**Installation:** No new packages needed — `httpx>=0.28.1` already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Module Structure
```
src/state_core/
├── http_client.py        # SharedHttpxClient factory + config model
├── deps.py               # Deps container (holds http_client + future resources)
└── providers/
    └── router.py         # ProviderRouter: consumes Deps.http_client
```

The `Deps` container is owned by `state_daemon/orchestrator.py` (created during startup, stored on the orchestrator, passed to all subsystems that need it).

### Pattern 1: httpx.AsyncClient Construction with Limits

**What:** Create `httpx.AsyncClient` with explicit `Limits` for connection pooling.
**When to use:** Daemon startup, once.

```python
# Source: https://www.python-httpx.org/advanced/resource-limits/
import httpx

def build_shared_client(
    *,
    max_connections: int = 100,
    max_keepalive_connections: int = 20,
    keepalive_expiry: float = 5.0,
    proxy: str | None = None,
    verify: bool | ssl.SSLContext = True,
) -> httpx.AsyncClient:
    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
        keepalive_expiry=keepalive_expiry,
    )
    return httpx.AsyncClient(
        limits=limits,
        proxy=proxy,          # None = no proxy; str = proxy URL
        verify=verify,        # True = system CAs; False = skip; SSLContext = custom
        trust_env=True,       # respects HTTP_PROXY / HTTPS_PROXY / ALL_PROXY env vars
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=False,
    )
```

**Default Limits values (verified from httpx docs):**
- `max_connections=100` — total concurrent connections
- `max_keepalive_connections=20` — idle connections in pool
- `keepalive_expiry=5.0` — seconds before idle connection is closed

For a daemon serving provider traffic, `max_connections=100` is reasonable. `max_keepalive_connections=20` allows reuse across concurrent litellm calls. These can be overridden via config.

### Pattern 2: Deps Container

**What:** A Pydantic model (or simple dataclass) holding daemon-level shared resources.
**When to use:** Created once at daemon startup; passed to every subsystem.

```python
# Source: project STACK.md + ARCHITECTURE.md conventions
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
import httpx

class Deps(BaseModel):
    """Daemon-level shared resources. Created once at startup; injected everywhere."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    http_client: httpx.AsyncClient

    async def aclose(self) -> None:
        """Graceful shutdown — close the shared HTTP client."""
        await self.http_client.aclose()
```

### Pattern 3: Anthropic SDK Injection

**What:** Pass the shared client to `AsyncAnthropic` via `http_client=` parameter.
**When to use:** When constructing the direct Anthropic SDK escape hatch (Phase 025).

```python
# Source: https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_client.py
import anthropic

# http_client parameter accepts httpx.AsyncClient | None
client = anthropic.AsyncAnthropic(
    auth_token=cred.access,    # OAuth token from AnthropicAuth
    http_client=deps.http_client,
)
```

**Key fact (HIGH confidence, verified from SDK source):** `AsyncAnthropic.__init__` signature is:
```
http_client: httpx.AsyncClient | None = None
```
The SDK accepts `httpx.AsyncClient` directly (not a wrapper class). The SDK doc says: "Configure a custom httpx client. We provide a `DefaultAsyncHttpxClient` class that you can pass to retain the default values we use for `limits`, `timeout` & `follow_redirects`." Since we construct our own client with explicit limits, passing our `AsyncClient` directly is correct.

### Pattern 4: litellm Global Client Assignment

**What:** Set `litellm.aclient_session` to the shared client.
**When to use:** Daemon startup, after client is created.

```python
# Source: https://docs.litellm.ai/docs/completion/http_handler_config
import litellm

async def setup_litellm(deps: Deps) -> None:
    litellm.aclient_session = deps.http_client
```

**IMPORTANT pitfall (verified from GitHub issues #13049, #7667):** litellm's cross-provider httpx injection is not uniform. The `litellm.aclient_session` global is supported but behavior varies by provider. For the Anthropic provider path, litellm may construct its own `AsyncHTTPHandler` internally and not respect the global client for all call paths. The safe pattern is:
1. Set `litellm.aclient_session` globally for the providers that respect it
2. For the Anthropic direct escape hatch (Phase 025), always pass `http_client=deps.http_client` explicitly to `AsyncAnthropic`
3. Never assume litellm transparently passes the client through to all SDKs

### Pattern 5: Proxy Configuration

**What:** Proxy via URL string or per-scheme mounts.
**When to use:** When `STATE_HTTP_PROXY` / `HTTP_PROXY` env is set.

```python
# Source: https://www.python-httpx.org/advanced/proxies/
# Single proxy:
client = httpx.AsyncClient(proxy="http://proxy.corp:8080")

# trust_env=True (default) automatically reads HTTP_PROXY, HTTPS_PROXY, ALL_PROXY
client = httpx.AsyncClient(trust_env=True)  # respects env vars

# Explicit per-scheme:
client = httpx.AsyncClient(
    mounts={
        "http://": httpx.AsyncHTTPTransport(proxy="http://proxy.corp:8080"),
        "https://": httpx.AsyncHTTPTransport(proxy="http://proxy.corp:8080"),
    }
)
```

For this phase, `trust_env=True` covers 95% of real proxy use cases (corporate proxies set via env vars). An explicit `proxy=` parameter can be wired to a `STATE_HTTP_PROXY` env var as a codebase-specific override.

### Pattern 6: TLS Configuration

**What:** Custom SSL context for enterprise CA trust or TLS verification override.
**When to use:** When `STATE_TLS_VERIFY=false` or `STATE_CA_BUNDLE=<path>` env is set.

```python
# Source: https://www.python-httpx.org/advanced/ssl/
import ssl

# Custom CA bundle:
ctx = ssl.create_default_context(cafile="/path/to/corporate-ca.pem")
client = httpx.AsyncClient(verify=ctx)

# Disable verification (dev/test only):
client = httpx.AsyncClient(verify=False)

# System cert store (truststore package — optional, not in current deps):
# import truststore
# ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
# client = httpx.AsyncClient(verify=ctx)
```

httpx also respects `SSL_CERT_FILE` and `SSL_CERT_DIR` env vars by default when `trust_env=True`.

### Pattern 7: Daemon Startup Integration

**What:** Wire client creation into the existing `startup()` sequence.
**When to use:** daemon/orchestrator.py.

The existing startup sequence (from `orchestrator.py`):
1. Step 0: `install()` + `assert_redactor_attached()`
2. Step 0.5: `import_from_opencode()`
3. Step 1: `store.run_repair_now()`
4. Step 2: `migrate()`
5. Step 3: `reconciler.start()`

New step (after step 0, before step 0.5 — shared client must be available for any step that might make HTTP calls):
```python
# Step -0.1: build shared HTTP client + Deps container
from state_core.http_client import build_shared_client
from state_core.deps import Deps
import litellm

deps = Deps(http_client=build_shared_client())
litellm.aclient_session = deps.http_client
log.info("startup: shared httpx client created")
```

### Anti-Patterns to Avoid

- **Per-call `async with httpx.AsyncClient()`:** The v2 auth providers do this deliberately (OAuth tokens; per-call lifecycle is intentional per rule 5 of Phase 014 comment). Do NOT change that. The shared client is only for provider inference traffic (litellm + direct Anthropic SDK), NOT for OAuth auth flows.
- **Module-level singleton:** `_client = httpx.AsyncClient()` at module top-level breaks testability (can't swap in tests) and is fragile with asyncio event loop lifetime.
- **Sharing the auth provider clients:** `AnthropicAuth`, `GoogleGeminiAuth`, etc. use per-call `async with httpx.AsyncClient()` for OAuth flows. This is correct (rule 5 from 014-CONTEXT) — OAuth token endpoints are low-frequency, session-scoped operations where per-call clients are appropriate. Do NOT migrate these.
- **Not closing on shutdown:** Always call `await deps.aclose()` on daemon shutdown. An unclosed `httpx.AsyncClient` leaks connections and generates asyncio "unclosed client session" warnings.
- **Trusting litellm to propagate the client universally:** litellm's `aclient_session` works for some providers and not others (GitHub issue #13049). The direct Anthropic SDK path (Phase 025) must use explicit `http_client=` injection.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection pooling | Custom pool manager | `httpx.Limits` | httpx handles connection lifecycle, keepalive, cleanup |
| Proxy support | Manual `CONNECT` tunneling | `httpx` proxy= / trust_env=True | httpx supports HTTP, HTTPS, SOCKS5 proxies natively |
| TLS config | Manual SSL handshake | `httpx verify=ssl.SSLContext` | httpx abstracts the full TLS negotiation |
| SDK transport injection | Monkey-patching SDKs | `AsyncAnthropic(http_client=...)` | Official SDK API; won't break on upgrades |

---

## Common Pitfalls

### Pitfall 1: litellm httpx Client Injection Is Provider-Dependent
**What goes wrong:** Setting `litellm.aclient_session = shared_client` and assuming all providers use it. Anthropic provider in litellm constructs its own `AsyncHTTPHandler`; OpenAI path may wrap in an `openai.AsyncOpenAI` client that has its own transport.
**Why it happens:** litellm is a multi-provider abstraction; each provider adapter has its own client construction logic.
**How to avoid:** Use `litellm.aclient_session` for the providers that support it (best effort for connection reuse); use explicit `http_client=` for the Anthropic direct SDK path (Phase 025).
**Warning signs:** Tests showing different response patterns when `aclient_session` is set vs. not set.

### Pitfall 2: Sharing httpx.AsyncClient Between Auth OAuth Flows and Inference Traffic
**What goes wrong:** Passing `deps.http_client` to `AnthropicAuth.login()` or `AnthropicAuth.refresh()`. These methods use `async with httpx.AsyncClient(...)` by design (Phase 014 rule 5: "Per-call AsyncClient — no module-level singleton"). Changing this breaks the per-call lifecycle guarantee.
**Why it happens:** Wanting to "unify" all HTTP traffic through one client.
**How to avoid:** Keep auth provider methods using per-call clients. The shared client is ONLY for provider inference (litellm + direct SDK calls). Document this boundary clearly.
**Warning signs:** Auth tests failing because httpx_mock intercepts shared client calls.

### Pitfall 3: asyncio Event Loop Binding
**What goes wrong:** `httpx.AsyncClient` created before the event loop starts, or used across multiple event loop lifetimes. Litellm has a known bug where it caches async clients across event loops (GitHub issue #7667).
**Why it happens:** httpx async clients are bound to the asyncio event loop at construction time.
**How to avoid:** Create `Deps` and the shared client inside an `async def startup()` coroutine, not at module import time. The current `orchestrator.startup()` is already an async function — put client creation there.
**Warning signs:** "Event loop is closed" or "is bound to a different event loop" errors in tests using `asyncio.run()` multiple times.

### Pitfall 4: Forgetting to Close on Shutdown
**What goes wrong:** Daemon exits without calling `await deps.http_client.aclose()`, causing "Unclosed client session" asyncio warnings or leaked OS socket descriptors.
**Why it happens:** The client has no automatic finalizer.
**How to avoid:** Add `await deps.aclose()` to the daemon shutdown path. Register it as an atexit-equivalent in the asyncio cleanup.
**Warning signs:** asyncio ResourceWarning in test teardown.

### Pitfall 5: SyncEventMirror Also Has Its Own Client
**What goes wrong:** Assuming the shared client covers ALL httpx usage. `SyncEventMirror.__init__` has `self._client = httpx.AsyncClient()`. This client is scoped to the mirror's lifecycle, not the daemon's shared pool.
**Why it happens:** The mirror predates Phase 023 and owns its own client for opencode sync traffic.
**How to avoid:** Decide explicitly: either (a) leave `SyncEventMirror` with its own client (it's a separate traffic class: internal opencode sync, not provider inference), or (b) migrate it to accept `deps.http_client` in its constructor. Option (a) is lower-risk for this phase; option (b) is cleaner but touches already-tested v2 code.
**Recommendation:** Option (a) for Phase 023 — leave SyncEventMirror alone. Note in code that the shared client is for provider inference; the mirror uses its own client for opencode sync. This can be unified in a later refactor.

---

## Code Examples

Verified patterns from official sources:

### httpx.AsyncClient Full Constructor (verified from official docs)
```python
# Source: https://www.python-httpx.org/api/#asyncclient
import httpx
import ssl

client = httpx.AsyncClient(
    # Connection pooling
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=5.0,
    ),
    # Proxy (or trust_env=True to read HTTP_PROXY/HTTPS_PROXY/ALL_PROXY)
    proxy=None,          # e.g. "http://proxy.corp:8080"
    trust_env=True,      # default; reads *_PROXY env vars
    # TLS
    verify=True,         # True=system CAs, False=skip, ssl.SSLContext=custom
    # Timeouts
    timeout=httpx.Timeout(30.0, connect=10.0),
    # Provider calls should not follow redirects
    follow_redirects=False,
)
```

### Anthropic SDK Injection (verified from SDK source)
```python
# Source: https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_client.py
import anthropic

# http_client: httpx.AsyncClient | None = None
# Passing our shared client:
sdk = anthropic.AsyncAnthropic(
    auth_token=cred.access,
    http_client=deps.http_client,
)
```

### litellm Global Async Client (verified from litellm docs)
```python
# Source: https://docs.litellm.ai/docs/completion/http_handler_config
import litellm

litellm.aclient_session = deps.http_client
# Then all acompletion() calls use the shared client for supported providers
response = await litellm.acompletion(model="anthropic/claude-...", messages=[...])
```

### pytest-httpx Test Pattern (from existing codebase tests)
```python
# Source: tests/test_sync_mirror.py — established pattern
from pytest_httpx import HTTPXMock

async def test_shared_client_used(httpx_mock: HTTPXMock, deps: Deps) -> None:
    httpx_mock.add_response(url="https://api.anthropic.com/v1/messages", status_code=200)
    # ... make call via deps.http_client ...
```

### Config-Driven Client Construction
```python
# Pattern for reading proxy/TLS from environment
import os
import ssl
import httpx

def build_shared_client() -> httpx.AsyncClient:
    proxy = os.environ.get("STATE_HTTP_PROXY")  # explicit override
    tls_verify_env = os.environ.get("STATE_TLS_VERIFY", "true").lower()
    ca_bundle = os.environ.get("STATE_CA_BUNDLE")  # path to custom CA

    if ca_bundle:
        verify: bool | ssl.SSLContext = ssl.create_default_context(cafile=ca_bundle)
    elif tls_verify_env == "false":
        verify = False
    else:
        verify = True  # trust_env=True will also read SSL_CERT_FILE/SSL_CERT_DIR

    return httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=5.0,
        ),
        proxy=proxy,
        verify=verify,
        trust_env=True,
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=False,
    )
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Per-call `async with httpx.AsyncClient()` for all HTTP | Shared daemon-owned `AsyncClient` for inference, per-call for OAuth auth | Connection reuse, lower latency |
| Provider clients constructing their own transport | `http_client=` injection into each SDK | Unified proxy/TLS/pool config |
| `litellm.session_client` (deprecated global) | `litellm.aclient_session` (current async global) | Correct async usage |

**Deprecated/outdated:**
- `litellm.session_client` — the sync global; not relevant for async usage
- `httpx.PoolLimits` — old class name; current API is `httpx.Limits`
- Per-call `async with httpx.AsyncClient()` for inference calls — replaced by shared client pattern

---

## Open Questions

1. **Should `SyncEventMirror` migrate to use `deps.http_client`?**
   - What we know: `SyncEventMirror` has `self._client = httpx.AsyncClient()` since v1/v2. It's for opencode sync, not provider inference.
   - What's unclear: Whether unified pool across all HTTP traffic (sync mirror + inference) is better than two separate clients with independent lifetimes.
   - Recommendation: Leave SyncEventMirror with its own client for Phase 023. The phase scope is provider inference traffic. This can be unified post-v3 if needed.

2. **litellm provider-specific httpx transport support**
   - What we know: `litellm.aclient_session` works for some providers; verified broken for Anthropic's internal path (uses `AsyncHTTPHandler`).
   - What's unclear: Whether litellm >=1.80.0 has improved cross-provider httpx client injection.
   - Recommendation: Set `litellm.aclient_session` as best-effort; always use explicit `http_client=` for the Anthropic SDK direct path (Phase 025). Phase 031 (parity matrix tests) can verify actual litellm routing behavior.

3. **`Deps` container scope — daemon only or also available to MCP servers?**
   - What we know: ARCHITECTURE.md says MCP servers (`state-build`, `state-teach`) call back to the daemon over HTTP; they don't own provider routing directly.
   - What's unclear: Whether Phase 023's `Deps` needs to be passed to MCP server processes or only to daemon-internal subsystems.
   - Recommendation: For Phase 023, `Deps` is daemon-internal only. MCP servers access provider routing via the daemon's HTTP API (the dependency injection problem is intra-daemon, not cross-process).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.0+ with pytest-asyncio 1.3.0+ |
| Config file | `pyproject.toml` — `asyncio_mode = "auto"` |
| Quick run command | `python3 -m pytest tests/test_http_client.py tests/test_deps.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q -m "not e2e and not integration"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRV-06 | `build_shared_client()` returns `AsyncClient` with correct `Limits` | unit | `pytest tests/test_http_client.py::test_build_shared_client_defaults -x` | ❌ Wave 0 |
| PRV-06 | `build_shared_client()` accepts `proxy=` string | unit | `pytest tests/test_http_client.py::test_build_shared_client_proxy -x` | ❌ Wave 0 |
| PRV-06 | `build_shared_client()` accepts `verify=False` for TLS skip | unit | `pytest tests/test_http_client.py::test_build_shared_client_tls_skip -x` | ❌ Wave 0 |
| PRV-06 | `build_shared_client()` reads `STATE_HTTP_PROXY` env var | unit | `pytest tests/test_http_client.py::test_build_shared_client_env_proxy -x` | ❌ Wave 0 |
| PRV-06 | `build_shared_client()` reads `STATE_CA_BUNDLE` env var | unit | `pytest tests/test_http_client.py::test_build_shared_client_env_ca -x` | ❌ Wave 0 |
| PRV-06 | `Deps.aclose()` calls `http_client.aclose()` | unit | `pytest tests/test_deps.py::test_deps_aclose -x` | ❌ Wave 0 |
| PRV-06 | `Deps` holds shared client, is injectable | unit | `pytest tests/test_deps.py::test_deps_holds_client -x` | ❌ Wave 0 |
| PRV-06 | `startup()` creates `Deps` and assigns `litellm.aclient_session` | unit | `pytest tests/test_deps.py::test_startup_creates_deps -x` | ❌ Wave 0 |
| PRV-06 | `AsyncAnthropic(http_client=deps.http_client)` passes client correctly | unit (smoke) | `pytest tests/test_deps.py::test_anthropic_client_injection -x` | ❌ Wave 0 |
| PRV-06 | `Deps` accessible via import — import graph lint passes | lint | `python3 -m pytest tests/test_imports.py -x -k http_client` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_http_client.py tests/test_deps.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q -m "not e2e and not integration"`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_http_client.py` — unit tests for `build_shared_client()` covering defaults, proxy, TLS, env vars
- [ ] `tests/test_deps.py` — unit tests for `Deps` container: construction, `aclose()`, litellm wiring, Anthropic SDK injection smoke test

*(Existing `tests/conftest.py` and `pytest.ini` config in `pyproject.toml` cover the infrastructure — no new framework install needed.)*

---

## Sources

### Primary (HIGH confidence)
- [httpx official docs — Resource Limits](https://www.python-httpx.org/advanced/resource-limits/) — `Limits` class, default values, configuration options
- [httpx official docs — AsyncClient API](https://www.python-httpx.org/api/#asyncclient) — full constructor signature verified
- [httpx official docs — SSL/TLS](https://www.python-httpx.org/advanced/ssl/) — `verify`, `ssl.SSLContext`, `SSL_CERT_FILE`, `truststore`
- [httpx official docs — Proxies](https://www.python-httpx.org/advanced/proxies/) — `proxy=`, `mounts=`, `trust_env`, env var support
- [httpx official docs — Environment Variables](https://www.python-httpx.org/environment_variables/) — `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `SSL_CERT_FILE`, `SSL_CERT_DIR`
- [anthropic-sdk-python `_client.py`](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_client.py) — `AsyncAnthropic.__init__` signature, `http_client: httpx.AsyncClient | None = None`
- `.planning/research/STACK.md` — "single `httpx.AsyncClient` owned by the daemon, injected via a `Deps` container" (architectural mandate)
- `src/state_core/sync_mirror.py` — existing `SyncEventMirror._client = httpx.AsyncClient()` pattern
- `src/state_daemon/orchestrator.py` — existing startup sequence to extend
- `tests/test_sync_mirror.py` — existing `pytest-httpx` `HTTPXMock` pattern

### Secondary (MEDIUM confidence)
- [litellm docs — Custom HTTP Handler](https://docs.litellm.ai/docs/completion/http_handler_config) — `litellm.aclient_session = httpx.AsyncClient(...)` global assignment
- [litellm GitHub issue #13049](https://github.com/BerriAI/litellm/issues/13049) — confirmed that litellm httpx injection is provider-dependent; Anthropic requires different path; issue closed as "not planned"
- [litellm GitHub issue #7667](https://github.com/BerriAI/litellm/issues/7667) — litellm caches async clients between calls; can cause cross-event-loop bugs

### Tertiary (LOW confidence — flag for validation)
- WebSearch results about litellm `aclient_session` — not verified against litellm 1.80.0 source directly; assume the pattern works for Gemini/OpenAI routes but not Anthropic routes

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — httpx >=0.28.1 already pinned; AsyncClient API verified from official docs
- Architecture: HIGH — `Deps` container pattern explicitly prescribed in STACK.md; injection points verified from SDK source
- Pitfalls: HIGH — litellm transport limitations verified from GitHub issues; async event loop binding is a well-known httpx constraint; auth provider per-call pattern is in-code comments (Phase 014)
- litellm aclient_session behavior: MEDIUM — confirmed global assignment pattern works but provider-specific behavior not fully verified for litellm 1.80.0

**Research date:** 2026-05-02
**Valid until:** 2026-06-01 (litellm transport API is fast-moving; re-verify at execute time)
