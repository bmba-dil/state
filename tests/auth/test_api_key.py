"""Phase 018 — VALIDATION rows 01–03, 12–18, 20 (RED scaffolding).

Wave 0 — every test in this file MUST FAIL until Wave 1 lands
`state_core.auth.providers.api_key`. Failure modes:
  * ImportError on the top-level `from state_core.auth.providers.api_key import …`
  * AttributeError when test bodies reference attributes that don't exist
  * AssertionError when a stub returns a placeholder value

See 018-VALIDATION.md for the full row→test mapping.

This file does NOT use `pytest.importorskip` — we WANT collection failure
to surface unmet dependencies loudly. The plan-checker enforces RED.
"""

from __future__ import annotations

import asyncio

import pytest
import structlog
from structlog.testing import capture_logs

from state_core.auth.base import ApiKeyCredential, AuthMethod
from state_core.auth.errors import AuthError, AuthLoginError

# The next two imports WILL FAIL in Wave 0. That is the RED signal.
from state_core.auth.providers.api_key import (
    _REGISTRY,
    ApiKeyProviderSpec,
    PlainApiKeyAuth,
    get_api_key_auth,
    iter_known_prefixes,
)
from state_core.auth.errors import UnknownApiKeyProviderError


# The 12 expected provider_ids in load-bearing insertion order
# (longest-prefix-first per RESEARCH §sk- Collision Resolution).
EXPECTED_PROVIDER_IDS: tuple[str, ...] = (
    "anthropic.api_key",  # sk-ant-api03- (longest sk- prefix)
    "openrouter",         # sk-or-v1-, sk-or-
    "openai",             # sk-proj-, sk-svcacct-, sk-None-, sk-
    "anyscale",           # esecret_
    "xai",                # xai-
    "groq",               # gsk_
    "google.ai_studio",   # ()
    "deepseek",           # ()
    "together",           # ()
    "mistral",            # ()
    "cohere",             # ()
    "cerebras",           # ()
)


# ── VALIDATION row 18 — _REGISTRY shape ───────────────────────────────────


def test_registry_has_12_providers() -> None:
    """VALIDATION row 18 — _REGISTRY has all 12 expected provider_ids in order."""
    assert set(_REGISTRY.keys()) == set(EXPECTED_PROVIDER_IDS)
    assert len(_REGISTRY) == 12
    # Insertion order is load-bearing for sk- collision resolution.
    assert tuple(_REGISTRY.keys()) == EXPECTED_PROVIDER_IDS


# ── VALIDATION row 13/14/15 — http_headers ────────────────────────────────


@pytest.mark.parametrize("provider_id", list(EXPECTED_PROVIDER_IDS))
def test_http_headers(provider_id: str) -> None:
    """VALIDATION rows 13/14/15 — three-bucket header assertion.

    Row 13: anthropic.api_key → ("x-api-key", "TESTKEY")
    Row 14: google.ai_studio → ("x-goog-api-key", "TESTKEY")
    Row 15: all others → ("Authorization", "Bearer TESTKEY")
    """
    auth = get_api_key_auth(provider_id)
    cred = ApiKeyCredential(key="TESTKEY", provider_id=provider_id)
    headers = auth.http_headers(cred)

    if provider_id == "anthropic.api_key":
        expected = {"x-api-key": "TESTKEY"}
    elif provider_id == "google.ai_studio":
        expected = {"x-goog-api-key": "TESTKEY"}
    else:
        expected = {"Authorization": "Bearer TESTKEY"}

    assert headers == expected


# ── VALIDATION row 16 — is_expired always False ──────────────────────────


@pytest.mark.parametrize("provider_id", list(EXPECTED_PROVIDER_IDS))
@pytest.mark.parametrize("now", [0.0, 1_000_000.0, 9_999_999_999.0])
def test_is_expired_always_false(provider_id: str, now: float) -> None:
    """VALIDATION row 16 — API keys never expire; is_expired ⟂ now."""
    auth = get_api_key_auth(provider_id)
    cred = ApiKeyCredential(key="k", provider_id=provider_id)
    assert auth.is_expired(cred, now) is False


# ── VALIDATION row 17 — refresh returns cred unchanged ───────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_id", list(EXPECTED_PROVIDER_IDS))
async def test_refresh_returns_unchanged(provider_id: str) -> None:
    """VALIDATION row 17 — refresh(cred) returns cred unchanged (frozen-equal)."""
    auth = get_api_key_auth(provider_id)
    cred = ApiKeyCredential(key="k", provider_id=provider_id)
    result = await auth.refresh(cred)
    # Frozen Pydantic model equality is structural.
    assert result == cred


# ── VALIDATION row 12 — sk- collision resolution ─────────────────────────


def test_sniff_resolves_sk_collision() -> None:
    """VALIDATION row 12 — longest-prefix-first sniff resolves sk- collisions.

    Walk _REGISTRY in insertion order; assert the FIRST is_token-match for
    each canonical key shape resolves to the documented winner. Then assert
    sk-* prefixes are listed in descending length order across the registry.
    """
    cases: list[tuple[str, str]] = [
        ("sk-ant-api03-XXXXXXX", "anthropic.api_key"),
        ("sk-or-v1-XXXXXXX", "openrouter"),
        ("sk-proj-XXXXXXX", "openai"),
        ("sk-XXXXXXX", "openai"),  # bare sk- → openai (last sk- registry entry)
    ]

    for key, expected_provider_id in cases:
        winner: str | None = None
        for provider_id in _REGISTRY:
            auth = get_api_key_auth(provider_id)
            if auth.is_token(key):
                winner = provider_id
                break
        assert winner == expected_provider_id, (
            f"key {key!r} resolved to {winner!r}, expected {expected_provider_id!r}"
        )

    # Within each provider, sk- prefixes MUST be longest-first so the local
    # is_token walk doesn't let a shorter prefix steal the match. Cross-
    # provider ordering is enforced by the cases-loop above (the registry
    # walk-order resolves each canonical key to the correct winner).
    for provider_id, spec in _REGISTRY.items():
        sk_prefixes = [p for p in spec.key_prefixes if p.startswith("sk-")]
        lengths = [len(p) for p in sk_prefixes]
        assert lengths == sorted(lengths, reverse=True), (
            f"{provider_id!r}: sk- prefixes not longest-first within provider: "
            f"{sk_prefixes}"
        )


# ── VALIDATION row 01 — login rejects empty key ──────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_key", ["", " ", "\n", "\t\t", "  \t\n  "])
async def test_login_rejects_empty_key(
    bad_key: str,
    mock_api_key_getpass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VALIDATION row 01 — empty / whitespace key raises AuthLoginError."""
    mock_api_key_getpass(bad_key)
    auth = PlainApiKeyAuth(_REGISTRY["openai"])
    with pytest.raises(AuthLoginError):
        await auth.login()


# ── VALIDATION row 02 — login warns on prefix mismatch ───────────────────


@pytest.mark.asyncio
async def test_login_warns_on_prefix_mismatch(
    mock_api_key_getpass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VALIDATION row 02 — prefix mismatch warns + stores; key never logged.

    T-018-3 mitigation: full key string MUST NOT appear in any captured log.
    """
    bad_prefix_key = "completely-wrong-prefix-XXXXXX"
    mock_api_key_getpass(bad_prefix_key)
    auth = PlainApiKeyAuth(_REGISTRY["openai"])

    with capture_logs() as logs:
        result = await auth.login()

    # Warn-and-store: the credential IS persisted with the original key.
    assert isinstance(result, ApiKeyCredential)
    assert result.provider_id == "openai"
    assert result.key == bad_prefix_key

    # Exactly one structlog event signals the prefix mismatch (accept either
    # `event` or `log_method` keys to be permissive of structlog versions).
    mismatch_events = [
        rec
        for rec in logs
        if (
            rec.get("event") == "api_key.prefix_mismatch"
            or rec.get("log_method") == "api_key.prefix_mismatch"
        )
    ]
    assert len(mismatch_events) == 1, f"expected 1 mismatch event, got {mismatch_events!r}"

    # The warning carries `observed_prefix` field equal to first 8 chars.
    assert mismatch_events[0].get("observed_prefix") == bad_prefix_key[:8]

    # T-018-3 mitigation: full key MUST NOT leak into any log record.
    for rec in logs:
        assert bad_prefix_key not in str(rec.values()), (
            f"full key leaked into log record: {rec!r}"
        )


# ── VALIDATION row 03 — unknown provider_id raises ───────────────────────


def test_get_api_key_auth_unknown_provider() -> None:
    """VALIDATION row 03 — unknown provider_id raises UnknownApiKeyProviderError.

    Exception MUST also subclass AuthError so callers catching the broad
    family still trip.
    """
    with pytest.raises(UnknownApiKeyProviderError) as exc_info:
        get_api_key_auth("not-a-real-provider")

    assert "not-a-real-provider" in str(exc_info.value)
    assert isinstance(exc_info.value, AuthError)


# ── VALIDATION row 20 — repr does not leak key ───────────────────────────


def test_credential_repr_does_not_leak(api_key_cred: ApiKeyCredential) -> None:
    """VALIDATION row 20 — ApiKeyCredential repr does not include the key.

    Pydantic Field(repr=False) behavior — Phase 011 regression guard.
    """
    repr_str = repr(api_key_cred)
    assert api_key_cred.key not in repr_str
    assert "key=" not in repr_str


# ── RESEARCH-mandated additional tests ───────────────────────────────────


def test_registry_provenance_comments() -> None:
    """RESEARCH §Provider Registry Table — every spec must carry a provenance comment.

    Wave 0 RED: file does not exist.
    """
    from pathlib import Path

    src_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "state_core"
        / "auth"
        / "providers"
        / "api_key.py"
    )
    if not src_path.exists():
        pytest.fail(
            "Wave 0 RED: src/state_core/auth/providers/api_key.py does not exist yet"
        )

    src_lines = src_path.read_text().splitlines()
    # Match ApiKeyProviderSpec(...) call sites, NOT the class definition
    # (the line `class ApiKeyProviderSpec(BaseModel):` also contains the
    # substring `ApiKeyProviderSpec(`). The 12 registry rows have form
    # `"<provider_id>": ApiKeyProviderSpec(` — anchor on that pattern.
    spec_indices = [
        i
        for i, line in enumerate(src_lines)
        if "ApiKeyProviderSpec(" in line and not line.lstrip().startswith("class ")
    ]
    assert spec_indices, "no ApiKeyProviderSpec(...) literals found in api_key.py"
    assert len(spec_indices) == 12, (
        f"expected 12 ApiKeyProviderSpec(...) call sites, got {len(spec_indices)}"
    )
    for idx in spec_indices:
        window = src_lines[max(0, idx - 5) : idx + 6]
        joined = "\n".join(window)
        assert "# captured 2026-04-30 from " in joined, (
            f"missing provenance comment near line {idx + 1} of api_key.py:\n{joined}"
        )


@pytest.mark.parametrize("provider_id", list(EXPECTED_PROVIDER_IDS))
def test_get_api_key_auth_returns_auth_method(provider_id: str) -> None:
    """Every provider's auth must structurally satisfy AuthMethod (5-method Protocol).

    @runtime_checkable Protocol — attribute-presence check (Phase 011 pattern).
    """
    auth = get_api_key_auth(provider_id)
    assert isinstance(auth, AuthMethod)


# Smoke test: iter_known_prefixes is exposed.
def test_iter_known_prefixes_is_callable() -> None:
    """Smoke — iter_known_prefixes() yields a non-empty stream of prefixes."""
    prefixes = list(iter_known_prefixes())
    # At least the documented sk- variants + xai- + esecret_ + gsk_ are expected.
    assert len(prefixes) >= 5
    # Every yielded item is a non-empty string.
    for p in prefixes:
        assert isinstance(p, str) and p, f"bad prefix: {p!r}"
