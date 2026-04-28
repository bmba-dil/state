"""Auth foundations: Credential discriminated union + AuthMethod Protocol.

This module is the contract every downstream auth phase consumes:

  * Phase 012 (auth.json vault) — uses CredentialAdapter for round-trip
  * Phase 013 (filelock refresh) — calls AuthMethod.refresh inside a lock
  * Phase 014..018 (provider impls) — each satisfies AuthMethod structurally
  * Phase 019 (multi-cred round-robin) — operates on lists of Credential
  * Phase 020 (root-logger redactor) — second layer of secret defense
  * Phase 022 (CLI + regression tests) — golden-file diff of http_headers

Cardinal rules enforced here:

  1. Mode isolation — this module imports ONLY from stdlib + pydantic.
     No mode-specific (build/teach) packages may be imported (BASE-08 test).
  2. Determinism — no datetime.now() / time.time() reads. The clock is
     injected via `now: float` parameters. (RESEARCH §Pattern 3)
  3. Secret hygiene — every secret field uses Field(repr=False). The
     structlog filter in Phase 020 is the second defense layer.
  4. Wire-shape expires — OAuthCredential.expires stores the epoch
     returned by the OAuth server. The 5-minute buffer (AUTH-09) is
     applied in provider-side AuthMethod.is_expired, never inside
     storage.

To add a new credential variant, edit BOTH the Credential union below
and any TypeAdapter[Credential] consumer. Adding a variant in a
provider module is a no-op until this union is updated.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

# ── Credential variants ──────────────────────────────────────────────────


class _CredentialBase(BaseModel):
    """Shared base for credential variants. Never instantiated directly.

    `extra="forbid"` rejects unknown fields (BASE-04).
    `frozen=True` makes instances immutable (BASE-05) — refresh creates
    new instances via model_copy rather than mutating in place.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


class OAuthCredential(_CredentialBase):
    """OAuth-issued tokens (Anthropic stealth, Gemini, Antigravity, Copilot).

    Used by phases 014–017. The `extras` dict carries provider-specific
    fields (enterprise_url, scope list, id_token, etc.) without forcing
    a new field per provider.
    """

    type: Literal["oauth"] = "oauth"
    access: str = Field(repr=False)
    """OAuth access token. SECRET — excluded from repr per AUTH-10 layer 1."""

    refresh: str = Field(repr=False)
    """OAuth refresh token. SECRET — excluded from repr per AUTH-10 layer 1."""

    expires: float
    """Epoch seconds — the WIRE VALUE returned by the OAuth server.

    No 5-minute buffer subtracted at storage. Buffer is applied in
    AuthMethod.is_expired (provider behavior) per AUTH-09. This keeps
    captured-header regression tests (Phase 022 / AUTH-13) tractable —
    cred.expires - issue_time == response.expires_in.
    """

    account_id: str | None = None
    """Optional account identifier. Anthropic uses this; plain API keys do not."""

    provider_id: str
    """Stable provider identifier ('anthropic', 'google.gemini_cli', …)."""

    extras: dict[str, Any] = Field(default_factory=dict)
    """Provider-specific extras (enterprise_url, scope, id_token, …).

    The dict reference is exposed; mutating it post-construction is
    undefined behavior. Use cred.model_copy(update={"extras": {...}})
    to amend.
    """


class ApiKeyCredential(_CredentialBase):
    """Plain API-key credential (12 providers per AUTH-05 + Anthropic-direct).

    No expiry, no refresh — `is_expired` always returns False and
    `refresh` returns the credential unchanged.
    """

    type: Literal["api_key"] = "api_key"
    key: str = Field(repr=False)
    """API key. SECRET — excluded from repr per AUTH-10 layer 1."""

    provider_id: str
    """Stable provider identifier ('anthropic', 'openai', 'google', …)."""

    extras: dict[str, Any] = Field(default_factory=dict)
    """Provider-specific extras. See OAuthCredential.extras for mutation contract."""


# ── Discriminated union + adapter ────────────────────────────────────────

Credential = Annotated[
    OAuthCredential | ApiKeyCredential,
    Field(discriminator="type"),
]
"""User-facing credential type.

Use CredentialAdapter to validate dicts and serialize instances.
Direct construction (OAuthCredential(...) / ApiKeyCredential(...)) is
fine when the variant is statically known.
"""

CredentialAdapter: TypeAdapter[OAuthCredential | ApiKeyCredential] = TypeAdapter(Credential)
"""Pre-built TypeAdapter for store.py (Phase 012) round-trips.

Usage:
    cred = CredentialAdapter.validate_python(some_dict)
    as_dict = CredentialAdapter.dump_python(cred, mode="json")
"""


# ── AuthMethod Protocol ──────────────────────────────────────────────────


@runtime_checkable
class AuthMethod(Protocol):
    """Contract every auth provider satisfies structurally.

    Sync methods are pure introspection (no I/O). Async methods perform
    network calls and MUST be awaited from inside Phase 013's filelock.

    @runtime_checkable enables `isinstance(obj, AuthMethod)` for plugin
    discovery — but it only checks attribute *presence*, not signatures
    (Pitfall 8). Pair with mypy strict for real safety.

    NEVER use AuthMethod as a field type on a Pydantic model — see
    Pitfall 1 (pydantic#10161). Pass providers as function arguments
    only.
    """

    provider_id: str
    """Stable provider identifier."""

    # ── Sync (pure) ──────────────────────────────────────────────────────

    def is_token(self, value: str) -> bool:
        """Return True iff *value* looks like a token THIS method issues.

        First branch of the token-shape sniffer. Each provider matches
        its own prefixes (Pitfall 5 — no central registry). Examples:
            Anthropic OAuth:    value.startswith('sk-ant-oat')
            Anthropic API key:  value.startswith('sk-ant-api03')
            Google OAuth:       value.startswith('ya29.')
        """
        ...

    def is_expired(self, cred: Credential, now: float) -> bool:
        """Return True iff *cred* should be refreshed before next use.

        Implementations MUST treat `now >= cred.expires - 300.0` as
        expired (5-minute buffer per AUTH-09 / P0-7). For
        ApiKeyCredential variants, return False unconditionally.

        `now` MUST be a parameter — never `time.time()` internally
        (cardinal determinism rule).
        """
        ...

    def http_headers(self, cred: Credential) -> dict[str, str]:
        """Return the exact header dict to merge into outbound HTTPS calls.

        This is the regression-test hook for AUTH-13 (Phase 022).
        Anthropic OAuth MUST return Bearer + the three stealth headers
        (user-agent, x-app, anthropic-beta) byte-for-byte against
        state-inputs/claude-oauth.md.
        """
        ...

    # ── Async (I/O-bound) ────────────────────────────────────────────────

    async def login(self) -> Credential | list[Credential]:
        """Run the interactive login flow; return one or more credentials.

        Most flows return a single Credential. Multi-account flows
        (rare) may return a list. Phase 012's store accepts both shapes.
        """
        ...

    async def refresh(self, cred: Credential) -> Credential:
        """Exchange *cred*'s refresh_token for a NEW credential.

        MUST return a new instance — frozen Pydantic models cannot be
        mutated, and Gemini's refresh-token rotation requires the new
        refresh token to replace the old one. Use:

            return cred.model_copy(update={
                "access": new_access,
                "refresh": new_refresh,
                "expires": new_expires,
            })

        For ApiKeyCredential, return *cred* unchanged.
        Raises AuthRefreshError on terminal failure (non-retryable).
        """
        ...


__all__ = [
    "ApiKeyCredential",
    "AuthMethod",
    "Credential",
    "CredentialAdapter",
    "OAuthCredential",
]
