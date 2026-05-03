# Phase 011: state_core.auth.base (AuthMethod protocol + Credential container) — Research

**Researched:** 2026-04-28
**Domain:** Foundational auth abstractions — Pydantic credential container + Protocol surface that all six auth providers (014-018) consume
**Confidence:** HIGH

## Summary

Phase 011 lays down the contracts (`Credential` Pydantic model + `AuthMethod` Protocol) that every downstream auth phase (012 vault, 013 refresh, 014–018 providers, 019 round-robin, 022 CLI) imports. Get this shape wrong and we either (a) break 9-of-16 P0 pitfalls in a way that's expensive to refactor, or (b) build provider implementations against a contract too narrow to express Anthropic's stealth headers, Gemini's `id_token`, Copilot's device-code, and plain API keys all at once.

The primary tension is that the six providers have radically different shapes:

- **Anthropic OAuth** — `sk-ant-oat*` Bearer + 3 mandatory custom headers (`user-agent`, `x-app`, `anthropic-beta`), refresh_token, `expires` epoch, account_id, optional enterprise_url
- **Gemini CLI / Antigravity** — Google OAuth (refresh-token rotation, scope list, `id_token` payload)
- **Copilot device-code** — exchange flow yields a different opaque token shape, GitHub-style refresh
- **Plain API keys** — single `key` string, no expiry, no refresh
- **Round-robin** — a *list* of credentials per provider with a `last_rotation` index

A single rigid `Credential` schema cannot capture all of this without becoming a flat bag-of-Optionals. The recommendation is a **discriminated-union credential family** (`OAuthCredential | ApiKeyCredential`, with `type` as the discriminator), bound together by a shared base class. The `AuthMethod` Protocol stays narrow and cleanly typed.

A second tension is **Protocol satisfaction**. Pydantic v2 BaseModel cannot be used as a `Protocol` field type (validation breaks per [pydantic#10161](https://github.com/pydantic/pydantic/issues/10161)), but Pydantic models *can* satisfy a structural Protocol when passed *to* methods. We exploit this: providers implement `AuthMethod` as plain classes (not Pydantic models); only the data containers (`Credential` variants) are Pydantic.

**Primary recommendation:** Define one abstract `Credential` base + two concrete subclasses (`OAuthCredential`, `ApiKeyCredential`) with a `type` literal discriminator; expose them via a Pydantic `TypeAdapter[Credential]`. Define `AuthMethod` as a `@runtime_checkable` Protocol with **async** `login`/`refresh` (matches Phase 013 filelock-async path) and **sync** `is_token`/`is_expired`/`http_headers` (pure introspection, no I/O). All times are stored as `epoch_seconds: float` for determinism — never `datetime.now()`. Providers live in `state_core.auth.providers.*` and never import `state.build.*` or `state.teach.*`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
*(none — discuss phase was skipped via `workflow.skip_discuss`)*

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None — discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

The ROADMAP lists this phase as `Requirements: (foundational)` — it carries **no** AUTH-XX IDs of its own. Instead, it must enable every downstream auth phase to satisfy theirs. The mapping below is the contract the planner must respect:

| Downstream ID | Where consumed | What Phase 011 must provide |
|---|---|---|
| AUTH-01 (Anthropic stealth, P0-1..P0-5, P0-7, P0-8) | Phase 014 | `OAuthCredential` schema with `access`, `refresh`, `expires` (5-min-buffered), `account_id`, optional `enterprise_url`; `http_headers()` signature returns `dict[str, str]` (Anthropic provider injects stealth headers); `is_token()` for `sk-ant-oat*` prefix sniff; Bearer (not `x-api-key`) is the default for OAuth |
| AUTH-02 (Gemini OAuth + refresh rotation) | Phase 015 | Same `OAuthCredential` shape; `refresh()` returns a *new* `Credential` (refresh-token rotation requires we do not mutate in place) |
| AUTH-03 (Antigravity device-code) | Phase 016 | Same shape + `extras: dict[str, Any]` for scope-list and antigravity-specific fields |
| AUTH-04 (Copilot device-code) | Phase 017 | Same shape; `login()` is async (15-min device-code polling fits async natively) |
| AUTH-05 (12 plain API keys) | Phase 018 | `ApiKeyCredential` variant — no `expires`, no `refresh_token`, just `key`; `is_expired()` returns `False`; `refresh()` returns self |
| AUTH-06 (chmod 0600, array-per-provider) | Phase 012 | `Credential` MUST be Pydantic-serializable to/from the JSON shape `{"providers": {"<provider>": [Credential, …]}}` (array shape preserved even for n=1) |
| AUTH-07 (filelock refresh, double-check) | Phase 013 | `is_expired(now)` is a *pure* function (no I/O, no clock read inside the model) so the filelock holder can re-check after acquiring |
| AUTH-08 (round-robin) | Phase 019 | `Credential` is independent of position-in-array; the array is owned by `store.py` |
| AUTH-09 (5-min expiry buffer) | Phase 014/015/016 | `is_expired(now)` MUST treat `now >= expires - 300s` as expired; the 5-min buffer is built into the comparison, not into `expires` itself (to keep `expires` matching the wire value) |
| AUTH-10 (root-logger redactor) | Phase 020 | `Credential.__repr__`/`__str__` must redact secrets (`access`, `refresh`, `key`); Pydantic v2 `repr=False` field option is the mechanism |
| AUTH-11 (first-run import) | Phase 021 | Schema must accept opencode's existing `auth.json` shape without lossy migration |
| AUTH-13 (captured-header regression) | Phase 022 | `http_headers(cred)` is the testable hook — returns the *exact* dict that gets merged into outbound HTTPS requests |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---|---|---|---|
| `pydantic` | **>=2.13.2** (project pin) | `Credential` BaseModel + discriminated-union container | Already pinned in `pyproject.toml`; v2.13 is stable; matches `state_core.schema` conventions (BaseModel + ConfigDict + Field) |
| `typing.Protocol` (stdlib) | 3.12+ | `AuthMethod` interface | Stdlib, no new dep; `@runtime_checkable` lets `isinstance(p, AuthMethod)` work for plugin discovery |

### Supporting
| Library | Version | Purpose | When to Use |
|---|---|---|---|
| `typing.Annotated` + `Field(discriminator=…)` | 3.12+ stdlib | Discriminated-union dispatch on `type` field | Required for `Credential = Annotated[OAuthCredential \| ApiKeyCredential, Field(discriminator="type")]` |
| `pydantic.TypeAdapter` | 2.13 | Validate/serialize the union without a wrapper model | Used by `store.py` (Phase 012) for `auth.json` round-trip |
| `pydantic.SecretStr` | 2.13 | Wrap `access`, `refresh`, `key` to redact in repr | Optional — alternative to `Field(repr=False)`; **recommend Field(repr=False)** for simpler JSON serialization (SecretStr serializes as `**********` by default which breaks round-trip) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| Pydantic discriminated union | Single flat `Credential` with `Optional[…]` for every variant field | Rejected: bag-of-Optionals defeats type safety; downstream providers would all need to defensive-check before each access |
| `typing.Protocol` | Abstract base class (`abc.ABC` + `abstractmethod`) | Rejected: Protocol's structural typing is a better fit for a plugin architecture (providers don't need to import the base); ABCs force inheritance. Also matches the existing stub at `src/state_core/auth/base.py` |
| `epoch_seconds: float` | `expires_at: datetime` | Rejected: deterministic serialization is a cardinal rule (events.sqlite is authoritative). `datetime` round-trips depend on tzinfo; `float` epoch is byte-identical across platforms. Matches `state_core.schema.AuthRefreshedData` style |
| sync `login`/`refresh` | async | Rejected: device-code polling, OAuth callback waits, and httpx token exchanges are all I/O-bound. Async matches the daemon's asyncio mandate (per STACK.md "asyncio over anyio") |
| async `is_expired` | sync | Async would force every call site to await; the function is pure arithmetic |
| `SecretStr` for tokens | `str` with `Field(repr=False)` | `Field(repr=False)` keeps JSON round-trip clean; redaction concerns are handled by Phase 020's structlog filter (defense in depth) |

**Installation:** No new deps. All required libraries are already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

```
src/state_core/auth/
├── __init__.py              # Re-export Credential, AuthMethod, OAuthCredential, ApiKeyCredential
├── base.py                  # ← THIS PHASE: Credential + AuthMethod Protocol
├── store.py                 # Phase 012 (already a stub)
├── refresh.py               # Phase 013
└── providers/               # Phases 014–018 (do not create here)
    ├── __init__.py
    ├── anthropic_oauth.py
    ├── gemini_cli.py
    ├── antigravity.py
    ├── copilot_device.py
    └── api_key.py
```

**Constraint:** `state_core.auth.base` MUST NOT import from `state_build.*` or `state_teach.*`. It lives in the shared kernel and is consumed by both modes.

### Pattern 1: Discriminated-Union Credential Family

**What:** A single user-facing `Credential` type that resolves at runtime to one of two concrete subclasses based on a `type` literal. Inspired by the existing `state_core.schema` discriminated-union pattern (29 events all use `Field(discriminator="type")`).

**When to use:** Every site that loads/saves credentials should accept the union; only provider implementations narrow to a specific variant.

**Example:**

```python
# src/state_core/auth/base.py
from __future__ import annotations

from typing import Annotated, Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

# ── Credential variants ──────────────────────────────────────────────────────


class _CredentialBase(BaseModel):
    """Shared base; never instantiated directly."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class OAuthCredential(_CredentialBase):
    """OAuth-issued tokens (Anthropic stealth, Gemini CLI, Antigravity, Copilot)."""

    type: Literal["oauth"] = "oauth"
    access: str = Field(repr=False)             # Bearer token, secret
    refresh: str = Field(repr=False)            # Refresh token, secret
    expires: float                              # Epoch seconds, wire-shape value
    account_id: str | None = None
    provider_id: str                            # "anthropic" | "google.gemini_cli" | …
    extras: dict[str, Any] = Field(default_factory=dict)
    """Provider-specific fields: enterprise_url, scope, id_token, etc."""


class ApiKeyCredential(_CredentialBase):
    """Plain API key (12 providers per AUTH-05 + Anthropic-direct fallback)."""

    type: Literal["api_key"] = "api_key"
    key: str = Field(repr=False)
    provider_id: str
    extras: dict[str, Any] = Field(default_factory=dict)


# ── Discriminated union ──────────────────────────────────────────────────────

Credential = Annotated[
    OAuthCredential | ApiKeyCredential,
    Field(discriminator="type"),
]
"""User-facing credential type. Use TypeAdapter for validation/serialization."""

CredentialAdapter: TypeAdapter[OAuthCredential | ApiKeyCredential] = TypeAdapter(Credential)
"""Pre-built adapter for store.py (Phase 012) round-trips."""
```

### Pattern 2: AuthMethod Protocol (sync + async split)

**What:** A `@runtime_checkable` Protocol that every provider satisfies structurally (no inheritance required).

**When to use:** Type-annotate every site that consumes a provider (e.g., `def get_provider(name: str) -> AuthMethod`).

**Example:**

```python
@runtime_checkable
class AuthMethod(Protocol):
    """Contract every auth provider satisfies.

    Sync methods are pure introspection (no I/O). Async methods perform
    network calls and MUST be awaited from inside Phase 013's filelock.
    """

    provider_id: str
    """Stable identifier — 'anthropic', 'google.gemini_cli', etc."""

    # ── Sync (pure) ─────────────────────────────────────────────────────────

    def is_token(self, value: str) -> bool:
        """Return True iff *value* looks like a token this method issues.

        Used as the first branch of the token-shape sniffer (see Pitfall 5).
        Anthropic OAuth: value.startswith('sk-ant-oat').
        API-key: value.startswith('sk-ant-api03') / 'sk-' / 'AIza' / etc.
        """
        ...

    def is_expired(self, cred: Credential, now: float) -> bool:
        """Return True iff *cred* should be refreshed before next use.

        Implementations MUST treat `now >= cred.expires - 300` as expired
        (5-minute buffer per AUTH-09 / P0-7). For ApiKeyCredential, always
        returns False.
        """
        ...

    def http_headers(self, cred: Credential) -> dict[str, str]:
        """Return the exact header dict to merge into outbound HTTPS requests.

        Anthropic OAuth MUST return:
            {
                "authorization": f"Bearer {cred.access}",
                "user-agent": f"claude-cli/{CLAUDE_CLI_VERSION}",
                "x-app": "cli",
                "anthropic-beta": "claude-code-20250219,oauth-2025-04-20,…",
            }
        Plain API key (Anthropic): {"x-api-key": cred.key}
        """
        ...

    # ── Async (I/O-bound) ───────────────────────────────────────────────────

    async def login(self) -> Credential | list[Credential]:
        """Run the interactive login flow; return one or more credentials.

        Most flows return a single Credential. Multi-account flows (rare)
        may return a list. Phase 012's store accepts both shapes.
        """
        ...

    async def refresh(self, cred: Credential) -> Credential:
        """Exchange *cred*'s refresh_token for a new credential.

        MUST return a NEW Credential (Pydantic frozen models are immutable;
        refresh-token rotation in Gemini requires the new refresh value to
        replace the old one).
        For ApiKeyCredential, return *cred* unchanged.
        Raises: AuthRefreshError on terminal failure (non-retryable).
        """
        ...
```

### Pattern 3: Determinism — never call `datetime.now()` in models

**What:** `Credential.expires` is a wire-value epoch float. The clock is never read inside the model.

**Why:** `events.sqlite` is authoritative; replay must be bit-identical. A `Credential.is_expired_now()` that reads `time.time()` would make replay non-deterministic.

**Implementation:** All time-aware methods take `now: float` as an explicit parameter. The daemon's HTTP middleware (or filelock holder in Phase 013) injects the current time once.

```python
# Good:
def is_expired(self, cred: Credential, now: float) -> bool:
    return now >= cred.expires - 300.0

# BAD:
def is_expired_now(self, cred: Credential) -> bool:
    import time
    return time.time() >= cred.expires - 300.0  # ← non-deterministic
```

### Anti-Patterns to Avoid

- **Inheriting Pydantic from Protocol:** `class OAuthCredential(BaseModel, AuthMethod)` — a Pydantic model is data, not behavior; a provider is behavior, not data. Keep them disjoint. The Protocol is satisfied by `OAuthProvider`, not by `OAuthCredential`.
- **Single flat `Credential` with all fields Optional:** Defeats the type system. Use the discriminated union.
- **`Credential` in `state_core.schema`:** Don't pollute the event schema module. Auth lives in `state_core.auth.base`. The `AuthRefreshedData` event in `schema.py` already uses `provider: str` — no coupling needed.
- **Passing `time.time()` as default arg:** `def is_expired(self, cred, now: float = time.time()):` — Python evaluates default args at *function-definition time*, freezing now to import-time forever. Use `Optional[float] = None` + late binding if a default is truly needed (it isn't here).
- **Using `datetime` in fields:** Round-trip across timezones is a footgun. Stay on epoch float to match `gsd2-auth-analysis.md` and the wire shape of every OAuth token endpoint (`expires_in` → `expires_at_epoch`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Discriminated-union dispatch | Manual `if/elif` on `type` field with `cast()` | `Annotated[A \| B, Field(discriminator="type")]` + `TypeAdapter` | Pydantic generates the dispatcher, validates the discriminator, and produces correct JSON Schema for free |
| JSON round-trip | `json.dumps`/`json.loads` with manual key fixups | `CredentialAdapter.dump_python(cred)` / `validate_python(d)` | Handles discriminated unions, frozen models, field aliases, and `repr=False` correctly |
| Token shape sniffer | A regex catalog inside `base.py` | `is_token()` per provider, dispatched by `state_core.auth.providers.match()` | Each provider knows its own prefixes; a central registry creates a coupling point that breaks Phase 014–018 parallelism |
| Field redaction in logs | Custom `__repr__` per Credential class | `Field(repr=False)` on every secret field + structlog filter (Phase 020) | Pydantic's repr generation respects `repr=False`; the structlog filter in Phase 020 is the second layer of defense |
| Cross-process refresh coordination | A class-level lock | `filelock.FileLock` (Phase 013) | We are *explicitly* not solving this in 011; the Protocol exposes `refresh()` and Phase 013 wraps it |

**Key insight:** Phase 011 deliberately solves *less* than it could. It owns the data shape and the contract; every behavioral concern (locking, persistence, refresh orchestration, redaction filtering) belongs to a later phase. Resist the urge to add helpers.

## Common Pitfalls

### Pitfall 1: Protocol-as-field-type breaks Pydantic validation
**What goes wrong:** Declaring `provider: AuthMethod` as a field on a Pydantic model raises `PydanticSchemaGenerationError` ([pydantic#10161](https://github.com/pydantic/pydantic/issues/10161)).
**Why it happens:** Pydantic v2 needs a concrete type to generate a core schema; structural Protocols don't expose one.
**How to avoid:** Never put `AuthMethod` inside a Pydantic model. The Protocol is a *function-signature* type, not a *field* type. Keep providers in plain Python classes/modules; pass them as function arguments only.
**Warning signs:** mypy passes but `Credential.model_rebuild()` raises at import time.

### Pitfall 2: `frozen=True` + `extras: dict` lets callers mutate the dict
**What goes wrong:** `cred.extras["scope"] = "evil"` succeeds even on a frozen model — `frozen` only blocks attribute reassignment, not mutation of mutable values.
**Why it happens:** Python frozen-ness is shallow.
**How to avoid:** Type `extras` as `Mapping[str, Any]` in the Protocol's view, and accept the leak in the model itself. If strict immutability is required, use `frozenset`/tuple values, but the cost (forcing every provider to coerce) is rarely worth it. Document the contract: "do not mutate `cred.extras`."
**Warning signs:** A test that mutates `extras` and expects a `ValidationError` passes silently.

### Pitfall 3: `expires` includes vs. excludes the 5-minute buffer
**What goes wrong:** Two reasonable readings of "5-min buffer":
  - (a) Subtract 300 from `expires_in` *before* storing, so `cred.expires = (now + raw_expires_in) - 300`.
  - (b) Store `expires = now + raw_expires_in` (the wire value) and subtract 300 inside `is_expired`.
  
The original GSD-pi did (a). Doing both = 10-minute buffer = ineffective. Doing neither = mid-request 401 (P0-7).
**Why it happens:** The 5-min math lives in two places (token storage + expiry check) and one of them gets refactored without the other.
**How to avoid:** **Choose (b)** — store the wire value, subtract in `is_expired`. The model field then matches what the OAuth server returned (verifiable in tests via `expires_in == cred.expires - issue_time`). Document this in a docstring on `OAuthCredential.expires`.
**Warning signs:** Captured-header regression test (AUTH-13) shows `expires` 300s lower than the OAuth response.

### Pitfall 4: `refresh()` mutates rather than returning a new Credential
**What goes wrong:** Frozen models can't be mutated, but a careless implementation does `cred.access = new_access` and silently fails (raises) on a frozen model — or, worse, on a non-frozen model, mutates in place but the file lock holder doesn't see the change because it loaded a copy.
**Why it happens:** Idiomatic Python is "modify in place"; Phase 013's lock-and-replace flow needs a new instance.
**How to avoid:** Make the Protocol explicit: `async def refresh(self, cred) -> Credential` returns a NEW credential. Document: "the old credential is invalidated by the OAuth server after refresh." Pydantic `model_copy(update=...)` is the pattern.
**Warning signs:** Gemini refresh-token rotation test fails (the *new* refresh token is dropped).

### Pitfall 5: First-branch token-shape sniffer co-located with `Credential`
**What goes wrong:** Putting a single `is_token(s) -> "oauth" | "api_key" | None` function in `base.py` creates a central registry of prefixes that every provider phase (014–018) must edit. Defeats parallelism.
**Why it happens:** It seems natural — "the model knows its own shape."
**How to avoid:** Each provider implements `is_token(value: str) -> bool` for its OWN prefixes. A `state_core.auth.providers.match(value) -> AuthMethod | None` dispatcher iterates registered providers — but lives in `providers/__init__.py` (created in Phase 014, not 011). Phase 011 just declares the *signature* on the Protocol.
**Warning signs:** Phase 011's PR touches a file in `providers/`.

### Pitfall 6: `__repr__` leaks secrets in tracebacks
**What goes wrong:** Default Pydantic repr includes every field. A `ValidationError` that includes the failing model dumps `access='sk-ant-oat-…'` into stderr / structured logs.
**Why it happens:** Pydantic's default repr is helpful for debugging but dangerous for secrets. Phase 020's redactor catches log records but not exception strings.
**How to avoid:** `Field(repr=False)` on every secret field (`access`, `refresh`, `key`). Add a unit test that constructs a Credential and asserts `"sk-ant-" not in repr(cred)`.
**Warning signs:** Test logs from a CI failure contain real-looking token prefixes.

### Pitfall 7: Mode-isolation violation through eager imports
**What goes wrong:** A naive `state_core.auth.providers.__init__` imports every provider eagerly; one of them transitively imports `state_build.something` (e.g., a logger configured in build kernel); CI's import-graph linter fails. Or worse, it doesn't fail and `state_teach` accidentally pulls in `state_build` via auth.
**Why it happens:** Auth touches "everything"; convenient to import freely.
**How to avoid:** Phase 011's `base.py` imports ONLY from stdlib and `pydantic`. Add an explicit assertion in the phase's tests:
```python
def test_no_mode_imports():
    import state_core.auth.base
    import sys
    leaked = [m for m in sys.modules if m.startswith(("state_build", "state_teach"))]
    assert not leaked, f"state_core.auth.base leaked mode imports: {leaked}"
```
**Warning signs:** Import-graph CI check (specified in PROJECT.md) fails on phase 011 PR.

### Pitfall 8: `runtime_checkable` Protocol false-positives
**What goes wrong:** `@runtime_checkable` only checks method *names*, not signatures. A class with a synchronous `def login(self)` that returns `None` will pass `isinstance(obj, AuthMethod)` even though it violates the contract.
**Why it happens:** Python's runtime checks are nominal-on-attribute-presence.
**How to avoid:** Treat `runtime_checkable` as a sanity gate, not a contract. Type-check with mypy strict (already enabled in `pyproject.toml`). Add a test that invokes each provider's full surface against a typed harness.
**Warning signs:** `isinstance(obj, AuthMethod)` returns True but `await obj.refresh(cred)` raises `TypeError: object NoneType can't be used in 'await' expression`.

## Code Examples

### Example 1: Provider satisfaction (Phase 014 preview)

```python
# Phase 014: src/state_core/auth/providers/anthropic_oauth.py
from state_core.auth.base import AuthMethod, Credential, OAuthCredential

CLAUDE_CLI_VERSION = "2.1.62"
ANTHROPIC_BETA = "claude-code-20250219,oauth-2025-04-20,…"


class AnthropicOAuth:
    """Concrete provider — structurally satisfies AuthMethod."""

    provider_id = "anthropic"

    def is_token(self, value: str) -> bool:
        return value.startswith("sk-ant-oat")

    def is_expired(self, cred: Credential, now: float) -> bool:
        if cred.type != "oauth":
            return False
        return now >= cred.expires - 300.0  # 5-min buffer (AUTH-09 / P0-7)

    def http_headers(self, cred: Credential) -> dict[str, str]:
        if cred.type != "oauth":
            return {"x-api-key": cred.key}  # type: ignore[union-attr]
        return {
            "authorization": f"Bearer {cred.access}",
            "user-agent": f"claude-cli/{CLAUDE_CLI_VERSION}",
            "x-app": "cli",
            "anthropic-beta": ANTHROPIC_BETA,
        }

    async def login(self) -> Credential:
        # PKCE flow → paste code#state → token exchange → return:
        return OAuthCredential(
            access="sk-ant-oat-…",
            refresh="…",
            expires=…,  # epoch seconds, wire value (no buffer subtracted)
            provider_id="anthropic",
            account_id="…",
        )

    async def refresh(self, cred: Credential) -> Credential:
        assert cred.type == "oauth"
        # POST to token endpoint with grant_type=refresh_token …
        return cred.model_copy(update={"access": new_access, "expires": new_expires})
```

### Example 2: TypeAdapter round-trip (used by Phase 012's store.py)

```python
from state_core.auth.base import CredentialAdapter

# Load
data = orjson.loads(auth_json_path.read_bytes())
creds = {
    provider: [CredentialAdapter.validate_python(c) for c in arr]
    for provider, arr in data["providers"].items()
}

# Save (deterministic, sorted keys for diff-stability)
serialized = {
    "providers": {
        provider: [CredentialAdapter.dump_python(c, mode="json") for c in arr]
        for provider, arr in creds.items()
    }
}
auth_json_path.write_bytes(orjson.dumps(serialized, option=orjson.OPT_SORT_KEYS))
```

### Example 3: Test harness (Wave 0 fixture)

```python
# tests/auth/conftest.py
import pytest
from state_core.auth.base import OAuthCredential, ApiKeyCredential


@pytest.fixture
def oauth_cred() -> OAuthCredential:
    return OAuthCredential(
        access="sk-ant-oat-test-token-do-not-redact-in-test-only",
        refresh="rt-test",
        expires=2_000_000_000.0,  # Far future, deterministic
        provider_id="anthropic",
        account_id="acct-test",
    )


@pytest.fixture
def api_key_cred() -> ApiKeyCredential:
    return ApiKeyCredential(
        key="sk-ant-api03-test",
        provider_id="anthropic",
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Pydantic v1 `Config` inner class | `model_config = ConfigDict(...)` | Pydantic v2 (2023) | `state_core.schema` already uses v2 idiom; mirror it |
| `BaseSettings` from pydantic | `pydantic_settings.BaseSettings` | Pydantic v2 split (2023) | Not relevant here — `Credential` is a domain model, not settings |
| `Union[A, B]` + `__root__` model | `Annotated[A \| B, Field(discriminator="type")]` + `TypeAdapter` | Pydantic v2.0 | Used pervasively in `state_core.schema` (Arc/Phase/Slice/Step events) — copy that pattern |
| `from pydantic.types import SecretStr` for tokens | `Field(repr=False)` on plain `str` | Project decision (this phase) | Avoids `SecretStr`'s opinionated serialization breaking JSON round-trip in `auth.json` |
| Async-everywhere (sync `is_expired` is "boring") | Sync for pure functions, async for I/O | Asyncio-best-practice consensus 2024+ | Lets the daemon HTTP middleware call `is_expired` without `await` propagation |

**Deprecated/outdated:**
- Storing `expires_at: datetime` — non-deterministic across timezones; replaced by `expires: float` (epoch).
- Using `typing.Union` syntax — replaced by `|` in 3.10+; project mandates 3.12.
- `pydantic.BaseModel.copy()` — deprecated in v2; use `model_copy()`.

## Open Questions (RESOLVED)

1. **Should `extras` be typed per provider?**
   - What we know: Anthropic needs `account_id` + optional `enterprise_url`; Gemini needs `id_token` + `scope`; Antigravity needs `cclog`/`experimentsandconfigs` scope strings.
   - What's unclear: Whether to type these as fields on `OAuthCredential` (one-Optional-per-provider creep) or keep them in `extras: dict[str, Any]` (loses type safety).
   - Recommendation: Promote `account_id` to a typed Optional field (used by 4 of 5 OAuth providers). Leave the rest in `extras`. Phase 014–017 may push back; revisit at Phase 014's plan.
   - **RESOLVED:** Plan 02 Task 1 promotes `account_id: str | None` to a typed Optional field on `OAuthCredential`; remaining provider-specific fields stay in `extras: dict[str, Any]`. Revisitable at Phase 014.

2. **Should `AuthMethod` be a class or a module-level interface?**
   - What we know: GSD-pi's TS implementation uses a registry of objects (`OAuthProviderInterface`).
   - What's unclear: In Python, a module of free functions (`anthropic_oauth.is_token(s)`, `anthropic_oauth.login()`) is also valid.
   - Recommendation: Use a class. Stateful providers (e.g., Copilot polling state during device-code) need instance fields. Modules-of-functions force module-level globals. Document: "providers are typically singletons; the daemon instantiates each one once at boot."
   - **RESOLVED:** Plan 02 Task 1 declares `AuthMethod` as a class-form `@runtime_checkable Protocol` with 5 methods; the daemon will instantiate concrete providers once at boot per Phase 014.

3. **Where does `match(value: str) -> AuthMethod | None` live?**
   - What we know: It must iterate every registered provider's `is_token`.
   - What's unclear: `state_core.auth.providers.__init__` (eager registry) vs. `state_core.auth.base` (lazy lookup) vs. Phase 014.
   - Recommendation: Defer to Phase 014. Phase 011 only declares `is_token` on the Protocol. The dispatcher is a Phase 014 concern (the first provider needs it).
   - **RESOLVED:** Deferred to Phase 014. Phase 011 declares `is_token(value: str) -> bool` on the Protocol only; no dispatcher / no `providers/` package created here.

4. **Captured-header regression for OAuth (AUTH-13) — golden file format?**
   - What we know: Phase 022 owns this; Phase 014 produces the headers.
   - What's unclear: Whether `http_headers()` should sort keys (deterministic golden file) or preserve insertion order.
   - Recommendation: Sort case-insensitively in tests, not in production; HTTP header order is server-tolerant.
   - **RESOLVED:** Deferred to Phase 022. Phase 011's `http_headers()` returns a `dict[str, str]` (insertion order preserved); golden-file sorting is a test-only concern owned by Phase 022 (AUTH-13).

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | `pytest>=8.4.0` + `pytest-asyncio>=1.3.0` (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/auth/ -x -q` |
| Full suite command | `python3 -m pytest -q` |

### Phase Requirements → Test Map

This phase has no AUTH-XX requirement IDs of its own. Instead, the test map verifies the *contract* that downstream providers depend on.

| Test ID (provisional) | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| BASE-01 | `OAuthCredential` round-trips through `CredentialAdapter` (validate ↔ dump_python) | unit | `pytest tests/auth/test_base.py::test_oauth_round_trip -x` | Wave 0 |
| BASE-02 | `ApiKeyCredential` round-trips, omits OAuth-only fields | unit | `pytest tests/auth/test_base.py::test_api_key_round_trip -x` | Wave 0 |
| BASE-03 | Discriminator dispatch — `validate_python({"type": "oauth", …})` returns `OAuthCredential` | unit | `pytest tests/auth/test_base.py::test_discriminator_dispatch -x` | Wave 0 |
| BASE-04 | `extra="forbid"` — unknown field raises `ValidationError` | unit | `pytest tests/auth/test_base.py::test_extra_forbid -x` | Wave 0 |
| BASE-05 | `frozen=True` — assignment to `cred.access` raises | unit | `pytest tests/auth/test_base.py::test_frozen_immutable -x` | Wave 0 |
| BASE-06 | `Field(repr=False)` — `repr(cred)` does NOT contain `cred.access` substring | unit | `pytest tests/auth/test_base.py::test_repr_redacts_secrets -x` | Wave 0 |
| BASE-07 | `AuthMethod` is `runtime_checkable`; a stub class with the 5 methods passes `isinstance` | unit | `pytest tests/auth/test_base.py::test_protocol_runtime_checkable -x` | Wave 0 |
| BASE-08 | Mode-isolation — importing `state_core.auth.base` does NOT pull `state_build.*` or `state_teach.*` into `sys.modules` | unit | `pytest tests/auth/test_base.py::test_no_mode_imports -x` | Wave 0 |
| BASE-09 | Determinism — `OAuthCredential(...).model_dump_json()` is byte-identical across two calls | unit (property) | `pytest tests/auth/test_base.py::test_deterministic_serialization -x` | Wave 0 |
| BASE-10 | `model_copy(update={"access": ...})` returns a NEW frozen instance with all other fields preserved | unit | `pytest tests/auth/test_base.py::test_model_copy_preserves_frozen -x` | Wave 0 |
| BASE-11 | Hypothesis property: any valid `OAuthCredential` round-trips through `dump_python` → `validate_python` losslessly | unit (property) | `pytest tests/auth/test_base.py::test_hypothesis_round_trip -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/auth/ -x -q` (< 2 seconds expected)
- **Per wave merge:** `python3 -m pytest -q` (full suite)
- **Phase gate:** Full suite green + `mypy src/state_core/auth/` clean before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/auth/__init__.py` — new test package
- [ ] `tests/auth/conftest.py` — shared fixtures (`oauth_cred`, `api_key_cred`)
- [ ] `tests/auth/test_base.py` — covers BASE-01..BASE-11
- [ ] No framework install needed — `pytest`, `pytest-asyncio`, `hypothesis` already in `pyproject.toml [project.optional-dependencies] dev`

## Sources

### Primary (HIGH confidence)
- `/Users/tmac/Projects/state/.planning/PROJECT.md` — cardinal rules (mode isolation, determinism, library locks)
- `/Users/tmac/Projects/state/.planning/research/STACK.md` — pinned versions, rejected alternatives
- `/Users/tmac/Projects/state/.planning/research/ARCHITECTURE.md` §10 — auth layer architecture, `auth.json` layout, refresh-lock mechanism
- `/Users/tmac/Projects/state/.planning/research/PITFALLS.md` — P0-1..P0-8, P0-13, P0-14, P1-3, P1-7
- `/Users/tmac/Projects/state/.state-inputs/claude-oauth.md` — Anthropic OAuth stealth byte-for-byte spec (8 non-obvious things)
- `/Users/tmac/Projects/state/.state-inputs/gsd2-auth-analysis.md` — five-method coverage strategy
- `/Users/tmac/Projects/state/.planning/milestones/v2/REQUIREMENTS.md` — AUTH-01..AUTH-13
- `/Users/tmac/Projects/state/src/state_core/schema.py` — existing discriminated-union pattern (29 events) to mirror
- `/Users/tmac/Projects/state/src/state_core/auth/base.py` — existing stub (≈20 LOC) to expand
- `/Users/tmac/Projects/state/pyproject.toml` — confirmed `pydantic>=2.13.2`, mypy strict, pytest-asyncio auto

### Secondary (MEDIUM confidence)
- [Pydantic v2 — Models docs (frozen, extra, model_config)](https://docs.pydantic.dev/latest/concepts/models/) — verified frozen + computed_field interaction
- [Pydantic v2 — Fields docs (repr, discriminator)](https://docs.pydantic.dev/latest/concepts/fields/)
- [Pydantic Migration Guide](https://docs.pydantic.dev/latest/migration/) — v1→v2 idioms

### Tertiary (LOW confidence — verified by independent reasoning + Pydantic issue tracker)
- [pydantic#10161 — Add support for `Protocol` type](https://github.com/pydantic/pydantic/issues/10161) — confirms Protocol-as-field-type is unsupported (Pitfall 1)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — every library and version is already pinned in `pyproject.toml`; no new deps proposed
- Architecture (Credential discriminated union): **HIGH** — direct mirror of existing `state_core.schema` pattern (29 events)
- AuthMethod Protocol shape: **HIGH** — derived from explicit signatures in `claude-oauth.md` + `ARCHITECTURE.md` §10.1
- Async/sync split decision: **MEDIUM** — defensible but a judgment call; may revisit if Phase 013 surfaces a need for async `is_expired` (e.g., reading from a remote clock service — unlikely)
- Pitfalls: **HIGH** — 5 of 8 are direct echoes of P0/P1 catalogue; the other 3 are general Pydantic/Python-3.12 gotchas
- Open questions 1 (`extras` typing) and 4 (header golden format): **LOW** — deferred to downstream phases

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (Pydantic 2.x is stable; the only fast-moving piece is Anthropic's beta header value, which is owned by Phase 014, not 011)

## RESEARCH COMPLETE
