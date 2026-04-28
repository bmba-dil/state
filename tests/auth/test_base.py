"""Tests for state_core.auth.base — Credential variants + AuthMethod Protocol.

BASE-01..BASE-11 from .planning/milestones/v2/phases/011-state-core-auth-base/011-RESEARCH.md
These tests are RED until Plan 02 lands the implementation.
"""

from __future__ import annotations

import string
import sys
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from state_core.auth.base import (
    ApiKeyCredential,
    AuthMethod,
    Credential,
    CredentialAdapter,
    OAuthCredential,
)


# BASE-01: OAuthCredential round-trips through CredentialAdapter
def test_oauth_round_trip(oauth_cred: OAuthCredential) -> None:
    dumped = CredentialAdapter.dump_python(oauth_cred, mode="json")
    rebuilt = CredentialAdapter.validate_python(dumped)
    assert rebuilt == oauth_cred
    assert dumped["type"] == "oauth"


# BASE-02: ApiKeyCredential round-trips, omits OAuth-only fields
def test_api_key_round_trip(api_key_cred: ApiKeyCredential) -> None:
    dumped = CredentialAdapter.dump_python(api_key_cred, mode="json")
    rebuilt = CredentialAdapter.validate_python(dumped)
    assert rebuilt == api_key_cred
    assert dumped["type"] == "api_key"
    assert "access" not in dumped
    assert "refresh" not in dumped
    assert "expires" not in dumped


# BASE-03: Discriminator dispatch
def test_discriminator_dispatch() -> None:
    oauth_dict = {
        "type": "oauth",
        "access": "a",
        "refresh": "r",
        "expires": 1.0,
        "provider_id": "x",
    }
    api_dict = {"type": "api_key", "key": "k", "provider_id": "x"}
    assert isinstance(CredentialAdapter.validate_python(oauth_dict), OAuthCredential)
    assert isinstance(CredentialAdapter.validate_python(api_dict), ApiKeyCredential)


# BASE-04: extra="forbid" — unknown field raises
def test_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        OAuthCredential(  # type: ignore[call-arg]
            access="a",
            refresh="r",
            expires=1.0,
            provider_id="x",
            unknown_field="should_fail",
        )


# BASE-05: frozen=True — assignment raises
def test_frozen_immutable(oauth_cred: OAuthCredential) -> None:
    with pytest.raises(ValidationError):
        oauth_cred.access = "new"  # type: ignore[misc]


# BASE-06: Field(repr=False) — secrets do NOT appear in repr
def test_repr_redacts_secrets(
    oauth_cred: OAuthCredential, api_key_cred: ApiKeyCredential
) -> None:
    oauth_repr = repr(oauth_cred)
    assert oauth_cred.access not in oauth_repr
    assert oauth_cred.refresh not in oauth_repr
    # provider_id is non-secret and SHOULD appear
    assert "anthropic" in oauth_repr

    api_repr = repr(api_key_cred)
    assert api_key_cred.key not in api_repr
    assert "anthropic" in api_repr


# BASE-07: AuthMethod is runtime_checkable; structural conformance works
def test_protocol_runtime_checkable() -> None:
    class _StubProvider:
        provider_id = "stub"

        def is_token(self, value: str) -> bool:
            return False

        def is_expired(self, cred: Credential, now: float) -> bool:
            return False

        def http_headers(self, cred: Credential) -> dict[str, str]:
            return {}

        async def login(self) -> Credential:  # type: ignore[empty-body]
            ...

        async def refresh(self, cred: Credential) -> Credential:  # type: ignore[empty-body]
            ...

    assert isinstance(_StubProvider(), AuthMethod)


# BASE-08: Mode-isolation — no state_build / state_teach pulled in
def test_no_mode_imports() -> None:
    # Snapshot before — but we already imported at module top, so just verify
    leaked = [
        m for m in sys.modules
        if m.startswith(("state_build.", "state_teach."))
        or m in {"state_build", "state_teach"}
    ]
    assert not leaked, f"state_core.auth.base leaked mode imports: {leaked}"


# BASE-09: Deterministic serialization
def test_deterministic_serialization(oauth_cred: OAuthCredential) -> None:
    first = oauth_cred.model_dump_json()
    second = oauth_cred.model_dump_json()
    assert first == second
    # Two independent constructions also serialize identically:
    twin = OAuthCredential(
        access=oauth_cred.access,
        refresh=oauth_cred.refresh,
        expires=oauth_cred.expires,
        provider_id=oauth_cred.provider_id,
        account_id=oauth_cred.account_id,
    )
    assert twin.model_dump_json() == first


# BASE-10: model_copy returns NEW frozen instance
def test_model_copy_preserves_frozen(oauth_cred: OAuthCredential) -> None:
    new_cred = oauth_cred.model_copy(update={"access": "new-access"})
    assert new_cred is not oauth_cred
    assert new_cred.access == "new-access"
    # All other fields preserved
    assert new_cred.refresh == oauth_cred.refresh
    assert new_cred.expires == oauth_cred.expires
    assert new_cred.provider_id == oauth_cred.provider_id
    # The copy is also frozen
    with pytest.raises(ValidationError):
        new_cred.access = "tampered"  # type: ignore[misc]


# BASE-11: Hypothesis property — round-trip is lossless
_SAFE_TEXT = st.text(
    alphabet=string.ascii_letters + string.digits + "-_.",
    min_size=1,
    max_size=64,
)


@given(
    access=_SAFE_TEXT,
    refresh=_SAFE_TEXT,
    expires=st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
    provider_id=_SAFE_TEXT,
)
@settings(max_examples=50, deadline=1000)
def test_hypothesis_round_trip(
    access: str, refresh: str, expires: float, provider_id: str
) -> None:
    cred = OAuthCredential(
        access=access,
        refresh=refresh,
        expires=expires,
        provider_id=provider_id,
    )
    dumped = CredentialAdapter.dump_python(cred, mode="json")
    rebuilt = CredentialAdapter.validate_python(dumped)
    assert rebuilt == cred
