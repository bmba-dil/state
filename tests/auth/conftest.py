"""Shared fixtures for auth tests (Phase 011 + Phase 012 + Phase 018)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterator

import pytest
import structlog

from state_core.auth.base import ApiKeyCredential, OAuthCredential


@pytest.fixture(autouse=True)
def _isolate_structlog_for_auth_tests() -> Any:
    """Isolate structlog config for auth tests; restore after.

    ``tests/test_cli.py`` configures structlog with a CRITICAL-level
    filtering wrapper at module-import time (operational-log suppression
    from v1 010.1 gap closure). That filter drops events before
    ``capture_logs`` can intercept them, breaking REFRESH-29
    (``test_emits_acquisition_logs``) when the full suite runs in any
    order that loads test_cli.py first.

    We snapshot the global config, reset to defaults for the auth test,
    then restore — so auth tests get clean ``capture_logs`` semantics
    AND test_cli tests still see their CRITICAL-filtered config when
    they run after auth tests in the alphabetical order.
    """
    saved = structlog.get_config()
    structlog.reset_defaults()
    yield
    structlog.configure(**saved)


@pytest.fixture
def oauth_cred() -> OAuthCredential:
    """Deterministic OAuth credential for round-trip + redaction tests.

    `expires` is far-future (year 2033) so freshness checks against
    `now=time.time()` would always pass — but tests must inject `now`
    explicitly per the determinism rule (RESEARCH §Pattern 3).
    """
    return OAuthCredential(
        access="sk-ant-oat-test-token-do-not-redact-in-test-only",
        refresh="rt-test-refresh-token-do-not-redact-in-test-only",
        expires=2_000_000_000.0,
        provider_id="anthropic",
        account_id="acct-test-12345",
    )


@pytest.fixture
def api_key_cred() -> ApiKeyCredential:
    """Deterministic API-key credential."""
    return ApiKeyCredential(
        key="sk-ant-api03-test-key-do-not-redact-in-test-only",
        provider_id="anthropic",
    )


@pytest.fixture
def now_frozen() -> float:
    """Frozen 'now' value for is_expired tests. Year 2026."""
    return 1_770_000_000.0


# ── Phase 012 fixtures ────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_state_auth_json_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense against Pitfall 8: prevent STATE_AUTH_JSON leakage between tests.

    Autouse — fires for EVERY test in tests/auth/. Uses monkeypatch.delenv
    with raising=False so it is a no-op when the env var is unset.
    monkeypatch automatically restores the prior value at test teardown.
    """
    monkeypatch.delenv("STATE_AUTH_JSON", raising=False)


@pytest.fixture
def auth_json_path(tmp_path: Path) -> Path:
    """Per-test .state/auth.json path under pytest's tmp_path.

    Parent directory is pre-created so callers may write directly without
    needing to call mkdir themselves. Path is unique per-test (pytest-managed).
    """
    p = tmp_path / ".state" / "auth.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def vault_with_one_oauth(oauth_cred: OAuthCredential):  # type: ignore[no-untyped-def]
    """In-memory AuthVault with one anthropic OAuth credential.

    Uses pytest.importorskip so collection survives Plan 02 lag — when
    state_core.auth.store has not yet exposed AuthVault, every test
    consuming this fixture is SKIPPED rather than ERRORED at collect time.
    """
    store = pytest.importorskip("state_core.auth.store")
    return store.AuthVault(providers={"anthropic": [oauth_cred]})


# ── Phase 013 fixtures ────────────────────────────────────────────────────


@pytest.fixture
def expired_oauth_cred(
    oauth_cred: OAuthCredential, now_frozen: float
) -> OAuthCredential:
    """OAuth credential within the 5-min refresh buffer relative to now_frozen.

    expires = now_frozen + 10.0 → is_expired_buffered(cred, now_frozen)
    is True once Plan 02 ships state_core.auth.refresh (now is past
    expires - 300, so the 300 s buffer triggers refresh).
    """
    return oauth_cred.model_copy(update={"expires": now_frozen + 10.0})


@pytest.fixture
def vault_with_expired_oauth(expired_oauth_cred: OAuthCredential):  # type: ignore[no-untyped-def]
    """In-memory AuthVault containing one EXPIRED anthropic OAuth credential.

    Uses pytest.importorskip so collection survives the Plan 01→Plan 02 lag —
    when state_core.auth.store has not yet exposed AuthVault, every test
    consuming this fixture is SKIPPED rather than ERRORED at collect time.
    """
    store = pytest.importorskip("state_core.auth.store")
    return store.AuthVault(providers={"anthropic": [expired_oauth_cred]})


@pytest.fixture
def mock_auth_method():  # type: ignore[no-untyped-def]
    """Counting-mock AuthMethod for double-check / concurrency proofs.

    Each call to ``refresh(cred)`` increments ``refresh_calls`` and returns
    a refreshed credential (expires bumped by +3600). ``asyncio.sleep(0.01)``
    in refresh allows other coroutines to queue behind the lock.

    Satisfies @runtime_checkable AuthMethod (5-method Protocol).
    """
    import asyncio

    from state_core.auth.base import AuthMethod, Credential, OAuthCredential

    class CountingMethod:
        provider_id: str = "anthropic"
        refresh_calls: int = 0

        def is_token(self, value: str) -> bool:
            return value.startswith("sk-ant-oat")

        def is_expired(self, cred: Credential, now: float) -> bool:
            if isinstance(cred, OAuthCredential):
                return now >= cred.expires - 300.0
            return False

        def http_headers(self, cred: Credential) -> dict[str, str]:
            if isinstance(cred, OAuthCredential):
                return {"authorization": f"Bearer {cred.access}"}
            return {}

        async def login(self) -> Credential:  # pragma: no cover - unused in 013
            raise NotImplementedError(
                "login is not exercised in Phase 013 tests"
            )

        async def refresh(self, cred: Credential) -> Credential:
            self.refresh_calls += 1
            await asyncio.sleep(0.01)
            if isinstance(cred, OAuthCredential):
                return cred.model_copy(
                    update={"expires": cred.expires + 3600.0}
                )
            return cred

    instance = CountingMethod()
    # Self-check the Protocol satisfaction at fixture build time.
    assert isinstance(instance, AuthMethod), (
        "CountingMethod must structurally satisfy AuthMethod (5-method Protocol)"
    )
    return instance


# ── Phase 018 fixtures ────────────────────────────────────────────────────

# The 12 canonical provider_ids per RESEARCH §Provider Registry Table.
# Order is load-bearing for the sk- collision test (longest-prefix-first).
_PHASE_018_PROVIDER_IDS: tuple[str, ...] = (
    "anthropic.api_key",
    "openrouter",
    "openai",
    "anyscale",
    "xai",
    "groq",
    "google.ai_studio",
    "deepseek",
    "together",
    "mistral",
    "cohere",
    "cerebras",
)


@pytest.fixture
def all_provider_ids() -> tuple[str, ...]:
    """The 12 canonical provider_ids per RESEARCH §Provider Registry Table.

    Test scaffolding may import _REGISTRY and assert keys == this tuple.
    Order is load-bearing for the sk- collision test (longest-prefix-first).
    """
    return _PHASE_018_PROVIDER_IDS


@pytest.fixture
def provider_id_factory() -> Callable[[], Iterator[str]]:
    """Returns a callable that yields the 12 provider_ids on each call.

    Convenience for tests that want a fresh iterator without re-creating
    the tuple manually.
    """

    def _factory() -> Iterator[str]:
        return iter(_PHASE_018_PROVIDER_IDS)

    return _factory


@pytest.fixture
def isolated_vault_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test .state/auth.json path PLUS STATE_AUTH_JSON env override.

    Differs from `auth_json_path` (above): this fixture ALSO sets
    STATE_AUTH_JSON so `state_core.auth.store.get_auth_json_path()`
    resolves to this exact path. Required for `test_main_api_key.py`
    which calls __main__ that itself calls get_auth_json_path().
    """
    p = tmp_path / ".state" / "auth.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("STATE_AUTH_JSON", str(p))
    return p


@pytest.fixture
def mock_stdin_pipe(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """Patch sys.stdin to simulate a non-TTY pipe with a single key line.

    Returned callable accepts a key string (without trailing newline);
    applies the patch when invoked. Use for the non-TTY login path
    per CONTEXT.md "single-line stdin on non-TTY".

    Also sets sys.stdin.isatty() to return False (the os.isatty branch
    gate Phase 018's __main__ uses to decide getpass-vs-stdin).
    """
    import io
    import sys

    def _apply(key: str) -> None:
        fake = io.StringIO(key + "\n")
        # Provide isatty() returning False (StringIO normally raises).
        fake.isatty = lambda: False  # type: ignore[method-assign]
        monkeypatch.setattr(sys, "stdin", fake)

    return _apply


@pytest.fixture
def mock_api_key_getpass(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """Patch state_core.auth.providers.api_key.getpass.getpass.

    Returned callable accepts a key string; applies the patch when
    invoked. Late-bind safe: in Wave 0 the api_key module does not
    yet exist; the patch falls back to a no-op so collection succeeds.

    Also forces the TTY-detection branch (os.isatty(0) → True) inside
    the api_key module so login() takes the getpass path. Under pytest,
    sys.stdin is replaced by DontReadFromInput whose fd-0 isatty is
    False; without this patch the login() flow would try to read from
    pytest's captured stdin and OSError.
    """

    def _apply(key: str) -> None:
        try:
            monkeypatch.setattr(
                "state_core.auth.providers.api_key.getpass.getpass",
                lambda _prompt="": key,
            )
            # Force the getpass branch in PlainApiKeyAuth.login().
            monkeypatch.setattr(
                "state_core.auth.providers.api_key.os.isatty",
                lambda _fd: True,
            )
        except (AttributeError, ModuleNotFoundError):
            # Wave 0: module not yet created. Late-bind silently.
            pass

    return _apply
