"""Shared fixtures for auth tests (Phase 011 + Phase 012 + Phase 013 + Phase 022)."""

from __future__ import annotations

import json
import re
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


# ── Phase 022 fixtures — golden infrastructure ────────────────────────────

GOLDEN_DIR = Path(__file__).parent / "golden"

# Ensure golden directory structure exists (idempotent).
for _provider in ("anthropic", "google.gemini", "google.antigravity", "github.copilot", "api_key"):
    (GOLDEN_DIR / _provider).mkdir(parents=True, exist_ok=True)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help="Regenerate golden JSON fixtures in tests/auth/golden/ instead of comparing.",
    )


@pytest.fixture
def update_goldens(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--update-goldens", default=False))


@pytest.fixture
def golden_load():
    """Return a loader function: golden_load(provider_id, flow_name) -> dict.

    Returns the parsed JSON dict from tests/auth/golden/<provider>/<flow>.json.
    The returned dict has keys: positive_allowlist, negative_allowlist,
    body_invariants, url_invariants, headers (allowlist-filtered snapshot).
    Raises FileNotFoundError if golden does not exist yet.
    """
    def _load(provider_id: str, flow_name: str) -> dict:
        path = GOLDEN_DIR / provider_id / f"{flow_name}.json"
        if not path.exists():
            pytest.fail(
                f"Golden file missing: {path}. "
                f"Run pytest --update-goldens to generate it."
            )
        return json.loads(path.read_text())
    return _load


_SECRET_SCRUB_RE = re.compile(r"Bearer (sk-ant-|sk-)[A-Za-z0-9_\-]{4,}", re.IGNORECASE)


def json_dump_deterministic(
    data: dict,
    allowlist_filter: list[str] | None = None,
) -> str:
    """Serialize data to deterministic JSON (sorted keys, 2-space indent).

    Scrubs any 'Bearer sk-ant-*' or 'Bearer sk-*' values to 'Bearer <REDACTED>'
    before serialization. If allowlist_filter is provided, filters dict to
    only include those keys (case-insensitive header names).
    """
    if allowlist_filter is not None and isinstance(data, dict):
        lower_allow = {k.lower() for k in allowlist_filter}
        data = {k: v for k, v in data.items() if k.lower() in lower_allow}

    serialized = json.dumps(data, sort_keys=True, indent=2)
    return _SECRET_SCRUB_RE.sub("Bearer <REDACTED>", serialized)


@pytest.fixture
def fake_oauth_cred():
    """Return a safe OAuthCredential with no real secret bytes.

    access/refresh are clearly fake tokens that cannot be confused with
    real sk-ant-* / ya29.* values.
    expires is set to now+3600 (1 hour from the epoch 0 fixed clock).
    """
    from state_core.auth.base import OAuthCredential
    return OAuthCredential(
        provider_id="anthropic",
        access="test-access-token-not-real",
        refresh="test-refresh-token-not-real",
        expires=3600.0,
        account_id="test-account-id",
        extras={"email_address": "test@example.com", "_source": "vault"},
    )


@pytest.fixture
def fake_api_key_cred():
    """Return a safe ApiKeyCredential with no real secret bytes."""
    from state_core.auth.base import ApiKeyCredential
    return ApiKeyCredential(
        provider_id="openai",
        key="test-api-key-not-real",
        extras={"_source": "vault"},
    )
# Restored fixtures dropped by 022-01

# --- all_provider_ids ---
@pytest.fixture
def all_provider_ids() -> tuple[str, ...]:
    """The 12 canonical provider_ids per RESEARCH §Provider Registry Table.

    Test scaffolding may import _REGISTRY and assert keys == this tuple.
    Order is load-bearing for the sk- collision test (longest-prefix-first).
    """
    return _PHASE_018_PROVIDER_IDS



# --- provider_id_factory ---
@pytest.fixture
def provider_id_factory() -> Callable[[], Iterator[str]]:
    """Returns a callable that yields the 12 provider_ids on each call.

    Convenience for tests that want a fresh iterator without re-creating
    the tuple manually.
    """

    def _factory() -> Iterator[str]:
        return iter(_PHASE_018_PROVIDER_IDS)

    return _factory



# --- isolated_vault_path ---
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



# --- mock_stdin_pipe ---
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



# --- mock_api_key_getpass ---
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



# --- _clear_cool_down ---
@pytest.fixture(autouse=True)
def _clear_cool_down() -> Iterator[None]:
    """Clear state_core.auth.rotation._COOL_DOWN before AND after each test.

    Defense against Pitfall 14 (RESEARCH §Common Pitfalls): module-global
    cool-down state leaks across tests under random ordering.

    Late-bind safe: in Wave 0 the rotation module does not yet exist; the
    try/except ImportError fallback is a no-op so collection succeeds.
    """
    try:
        from state_core.auth import rotation as _rotation_mod

        _rotation_mod._COOL_DOWN.clear()
    except (ImportError, AttributeError):
        pass
    yield
    try:
        from state_core.auth import rotation as _rotation_mod

        _rotation_mod._COOL_DOWN.clear()
    except (ImportError, AttributeError):
        pass



# --- vault_with_three_oauth ---
@pytest.fixture
def vault_with_three_oauth(now_frozen: float):  # type: ignore[no-untyped-def]
    """In-memory AuthVault with three anthropic OAuth credentials.

    Far-future `expires` ensures freshness; provider_id="anthropic".
    Use for ROTATE-04, 07, 08, 09, 10, 16, 17.
    """
    store = pytest.importorskip("state_core.auth.store")
    return store.AuthVault(
        providers={
            "anthropic": [
                OAuthCredential(
                    access=f"sk-ant-oat-TEST-{i}",
                    refresh=f"rt-TEST-{i}",
                    expires=now_frozen + 86400.0,
                    provider_id="anthropic",
                    account_id=f"acct-TEST-{i}",
                )
                for i in range(3)
            ],
        },
        last_rotation={"anthropic": 0},
    )



# --- vault_with_three_api_keys ---
@pytest.fixture
def vault_with_three_api_keys():  # type: ignore[no-untyped-def]
    """In-memory AuthVault with three openai ApiKeyCredentials.

    Use for ROTATE-23 hypothesis (api keys never expire — pure rotation).
    """
    store = pytest.importorskip("state_core.auth.store")
    return store.AuthVault(
        providers={
            "openai": [
                ApiKeyCredential(key=f"TEST-key-{i}", provider_id="openai")
                for i in range(3)
            ],
        },
        last_rotation={"openai": 0},
    )





@pytest.fixture
async def busy_lock_holder():  # type: ignore[no-untyped-def]
    """Async context manager that holds `_new_async_lock(vault_path)` open.

    Used by ROTATE-19 (test_select_lock_timeout_raises) — the test enters
    this fixture's lock then calls `select_credential` from the same loop;
    the inner call must raise `RefreshLockTimeout` within ~10s (or sooner
    if the test passes a smaller `LOCK_TIMEOUT_SECONDS` patch).

    Mirrors the lock-busy pattern from tests/auth/test_refresh.py for
    REFRESH-25 / REFRESH-27.
    """
    import contextlib

    @contextlib.asynccontextmanager
    async def _hold(vault_path: "Path"):
        from state_core.auth.refresh import _new_async_lock

        lock = _new_async_lock(vault_path)
        await lock.acquire()
        try:
            yield lock
        finally:
            try:
                await lock.release()
            except Exception:
                pass

    return _hold


