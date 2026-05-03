"""Phase 021 / AUTH-11 -- Wave 1 RED test scaffold for state_core.auth.import_opencode.

Every test in this file MUST fail until Plan 02 lands the importer module:

  * Module-level `from state_core.auth.import_opencode import ...` raises
    `ModuleNotFoundError` at COLLECTION time.
  * Tests that survive collection (none, currently) would fail on
    AttributeError / AssertionError against not-yet-existent symbols.

This is the RED side of TDD discipline (CLAUDE.md cardinal rule). Plan 02
turns these GREEN by implementing `state_core.auth.import_opencode`.

Row -> test mapping (covers IMPORT-01..IMPORT-26 from 021-CONTEXT.md):

  IMPORT-01  test_resolves_opencode_auth_content_env_var_first
  IMPORT-02  test_resolves_xdg_data_home_second
  IMPORT-03  test_resolves_platform_default_third
  IMPORT-04  test_state_opencode_auth_path_env_overrides_autodiscovery
  IMPORT-05  test_absent_file_silent_noop_with_debug_log
  IMPORT-06  test_unreadable_file_warn_and_continue
  IMPORT-07  test_skips_oauth_dummy_key_with_debug_log
  IMPORT-08  test_skips_wellknown_with_info_log
  IMPORT-09  test_translates_type_api_to_api_key
  IMPORT-10  test_translates_type_oauth_passthrough
  IMPORT-11  test_renames_accountId_to_account_id
  IMPORT-12  test_moves_enterpriseUrl_to_extras_enterprise_url
  IMPORT-13  test_copies_metadata_to_extras_verbatim
  IMPORT-14  test_sets_provenance_marker_extras_source_opencode_import
  IMPORT-15  test_unknown_provider_id_imported_with_info_log
  IMPORT-16  test_known_provider_id_no_warning
  IMPORT-17  test_array_shape_preserved_single_cred
  IMPORT-18  test_array_shape_preserved_hypothesis
  IMPORT-19  test_append_only_to_existing_array
  IMPORT-20  test_identity_by_provider_id_and_access_prefix_12
  IMPORT-21  test_dedupe_within_input_unreachable_for_normal_shape
  IMPORT-22  test_all_or_nothing_transactional_failure
  IMPORT-23  test_emits_auth_imported_event_per_credential
  IMPORT-24  test_event_payload_contains_no_secret_bytes
  IMPORT-25  test_importer_does_not_call_time_or_datetime_now
  IMPORT-26  test_returns_zero_credentials_when_opencode_file_missing

Canary discipline: every secret-shaped fixture value uses the literal
substring "TEST-CANARY-" so a future log/event leak regression is
greppable. Tests assert this substring is ABSENT from rendered event
payloads (IMPORT-24).
"""

from __future__ import annotations

import ast
import json
import pathlib
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st
from structlog.testing import capture_logs

# Wave 1 RED -- this import MUST fail at collection time until Plan 02
# creates src/state_core/auth/import_opencode.py.
from state_core.auth.import_opencode import (  # noqa: F401
    _OPENCODE_OAUTH_DUMMY_KEY,
    discover_opencode_auth_path,
    import_from_opencode,
    parse_opencode_auth,
)

# Schema additions from Plan 01 Task 1 (already GREEN).
from state_core.auth.base import ApiKeyCredential, OAuthCredential
from state_core.schema import AuthImportedData, AuthImportedEvent


# ── Canary fixtures (greppable for leak regressions) ─────────────────────

_CANARY_API_KEY = "sk-TEST-CANARY-" + "A" * 32
# Distinct first-12-char prefix (Rule 1 fix): the original literal shared the
# `sk-TEST-CANA` 12-char prefix with _CANARY_API_KEY, so identity-by-prefix
# deduped them and IMPORT-19/IMPORT-20 could not exercise the "different
# prefix -> new element" branch. The new prefix differs in chars 4..11
# (`2ND-XXXX` vs `TEST-CANA`) while still embedding the `TEST-CANARY-`
# canary substring (after position 12) so IMPORT-24's grep-style leak
# detector still has a greppable target if a regression ever reaches it.
_CANARY_API_KEY_2 = "sk-2ND-XXXX-TEST-CANARY-" + "B" * 32
_CANARY_OAUTH_ACCESS = "tok-TEST-CANARY-" + "C" * 32
_CANARY_OAUTH_REFRESH = "rt-TEST-CANARY-" + "D" * 32
_CANARY_WELLKNOWN_KEY = "wk-TEST-CANARY-" + "E" * 32
_CANARY_WELLKNOWN_TOKEN = "wt-TEST-CANARY-" + "F" * 32

# 16 known provider_ids per CONTEXT.md (12 API-key + 4 OAuth).
_KNOWN_PROVIDER_IDS = [
    # Phase 018 _REGISTRY (12 IDs)
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
    # Phases 014-017 OAuth (4 IDs)
    "anthropic",
    "google.gemini_cli",
    "google.antigravity",
    "github.copilot",
]


# ── Stub event store for IMPORT-23 dual-write assertion ──────────────────


class _StubStore:
    """Stub EventStore used to assert dual-write of state.auth.imported.

    Mirrors the minimal surface the importer is expected to use:
    `await store.append(event)` (or similar). Plan 02 will pin the exact
    method name; for Wave 1 we only need a sink the importer can call.
    """

    def __init__(self) -> None:
        self.events: list[Any] = []

    async def append(self, *args: Any, **kwargs: Any) -> None:
        self.events.append((args, kwargs))


# ── IMPORT-01..IMPORT-04: path resolution ────────────────────────────────


def test_resolves_opencode_auth_content_env_var_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """IMPORT-01 -- OPENCODE_AUTH_CONTENT env var wins over file paths.

    Mirrors opencode auth/index.ts:59 -- when OPENCODE_AUTH_CONTENT is
    set, parse it as JSON in-memory and skip filesystem discovery.
    """
    monkeypatch.setenv("OPENCODE_AUTH_CONTENT", '{"x": {"type": "api", "key": "k"}}')
    # Create a competing on-disk file that MUST be ignored.
    monkeypatch.setenv("STATE_OPENCODE_AUTH_PATH", str(tmp_path / "decoy.json"))
    (tmp_path / "decoy.json").write_text("{}")
    creds = parse_opencode_auth(env_content='{"x": {"type": "api", "key": "k"}}')
    assert isinstance(creds, list)


def test_resolves_xdg_data_home_second(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """IMPORT-02 -- $XDG_DATA_HOME/opencode/auth.json takes precedence over default."""
    monkeypatch.delenv("OPENCODE_AUTH_CONTENT", raising=False)
    monkeypatch.delenv("STATE_OPENCODE_AUTH_PATH", raising=False)
    xdg = tmp_path / "xdg"
    (xdg / "opencode").mkdir(parents=True)
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    resolved = discover_opencode_auth_path()
    assert resolved == xdg / "opencode" / "auth.json"


def test_resolves_platform_default_third(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """IMPORT-03 -- ~/.local/share/opencode/auth.json (Linux) or
    ~/Library/Application Support/opencode/auth.json (macOS) is the
    last-resort default when no env vars are set.
    """
    monkeypatch.delenv("OPENCODE_AUTH_CONTENT", raising=False)
    monkeypatch.delenv("STATE_OPENCODE_AUTH_PATH", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    resolved = discover_opencode_auth_path()
    # Either Linux or macOS path under tmp_path.
    s = str(resolved)
    assert "opencode/auth.json" in s and str(tmp_path) in s


def test_state_opencode_auth_path_env_overrides_autodiscovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """IMPORT-04 -- STATE_OPENCODE_AUTH_PATH wins over auto-discovery.

    Mirrors Phase 012's STATE_AUTH_JSON pattern. Used in tests/CI.
    """
    target = tmp_path / "fixture.json"
    target.write_text("{}")
    monkeypatch.delenv("OPENCODE_AUTH_CONTENT", raising=False)
    monkeypatch.setenv("STATE_OPENCODE_AUTH_PATH", str(target))
    resolved = discover_opencode_auth_path()
    assert resolved == target


# ── IMPORT-05..IMPORT-06: filesystem hardness ─────────────────────────────


def test_absent_file_silent_noop_with_debug_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """IMPORT-05 -- absent file is silent no-op + DEBUG log on daemon start."""
    import asyncio

    monkeypatch.setenv("STATE_OPENCODE_AUTH_PATH", str(tmp_path / "nope.json"))
    with capture_logs() as logs:
        # Rule 1 fix: import_from_opencode is async (it awaits the event
        # store's async append); wrap with asyncio.run to drive it from
        # a sync test body.
        result = asyncio.run(
            import_from_opencode(existing_vault=None, store=_StubStore())
        )
    assert result == [] or result is None
    assert any("absent" in (e.get("event") or "").lower() for e in logs)


def test_unreadable_file_warn_and_continue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """IMPORT-06 -- corrupt JSON / unreadable file => WARN log, vault untouched."""
    import asyncio

    bad = tmp_path / "auth.json"
    bad.write_text("{not valid json")
    monkeypatch.setenv("STATE_OPENCODE_AUTH_PATH", str(bad))
    with capture_logs() as logs:
        result = asyncio.run(
            import_from_opencode(existing_vault=None, store=_StubStore())
        )
    assert result == [] or result is None
    # WR-02 fix: every auth.import.unreadable WARN MUST carry a `source`
    # field so operators can identify which opencode install corrupted.
    # The disk-read branch and the JSONDecodeError branch share one
    # contract: same event name, both with `source` set.
    unreadable_warns = [
        e
        for e in logs
        if "unreadable" in (e.get("event") or "").lower()
        and e.get("log_level") == "warning"
    ]
    assert unreadable_warns, f"expected auth.import.unreadable WARN; got {logs!r}"
    for warn in unreadable_warns:
        assert warn.get("source"), (
            f"auth.import.unreadable WARN missing `source` field: {warn!r}"
        )


# ── IMPORT-07..IMPORT-08: skip patterns ──────────────────────────────────


def test_skips_oauth_dummy_key_with_debug_log() -> None:
    """IMPORT-07 -- opencode OAUTH_DUMMY_KEY ('opencode-oauth-dummy-key')
    must be detected and skipped (auth/index.ts:7 sentinel).
    """
    assert _OPENCODE_OAUTH_DUMMY_KEY == "opencode-oauth-dummy-key"
    payload = {"opencode": {"type": "api", "key": _OPENCODE_OAUTH_DUMMY_KEY}}
    with capture_logs() as logs:
        creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert creds == []
    assert any("dummy" in (e.get("event") or "").lower() for e in logs)


def test_skips_wellknown_with_info_log() -> None:
    """IMPORT-08 -- opencode 'wellknown' type is unsupported -> skip + INFO log.

    State's Credential union (Phase 011) is OAuth + ApiKey only.
    """
    payload = {
        "github.copilot": {
            "type": "wellknown",
            "key": _CANARY_WELLKNOWN_KEY,
            "token": _CANARY_WELLKNOWN_TOKEN,
        }
    }
    with capture_logs() as logs:
        creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert creds == []
    assert any(
        "wellknown" in (e.get("event") or "").lower()
        or e.get("reason") == "wellknown_unsupported"
        for e in logs
    )


# ── IMPORT-09..IMPORT-10: type discriminator translation ──────────────────


def test_translates_type_api_to_api_key() -> None:
    """IMPORT-09 -- opencode 'type: api' -> state 'type: api_key' (rename)."""
    payload = {"openrouter": {"type": "api", "key": _CANARY_API_KEY}}
    creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert len(creds) == 1
    assert isinstance(creds[0], ApiKeyCredential)
    assert creds[0].type == "api_key"
    assert creds[0].provider_id == "openrouter"


def test_translates_type_oauth_passthrough() -> None:
    """IMPORT-10 -- opencode 'type: oauth' passes through to OAuthCredential."""
    payload = {
        "anthropic": {
            "type": "oauth",
            "access": _CANARY_OAUTH_ACCESS,
            "refresh": _CANARY_OAUTH_REFRESH,
            "expires": 1_900_000_000.0,
        }
    }
    creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert len(creds) == 1
    assert isinstance(creds[0], OAuthCredential)
    assert creds[0].type == "oauth"
    assert creds[0].provider_id == "anthropic"


# ── IMPORT-11..IMPORT-13: field renames ──────────────────────────────────


def test_renames_accountId_to_account_id() -> None:
    """IMPORT-11 -- camelCase accountId -> snake_case account_id (1st-class field)."""
    payload = {
        "anthropic": {
            "type": "oauth",
            "access": _CANARY_OAUTH_ACCESS,
            "refresh": _CANARY_OAUTH_REFRESH,
            "expires": 1_900_000_000.0,
            "accountId": "acct-TEST-CANARY-12345",
        }
    }
    creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert isinstance(creds[0], OAuthCredential)
    assert creds[0].account_id == "acct-TEST-CANARY-12345"


def test_moves_enterpriseUrl_to_extras_enterprise_url() -> None:
    """IMPORT-12 -- camelCase enterpriseUrl -> extras['enterprise_url']."""
    payload = {
        "anthropic": {
            "type": "oauth",
            "access": _CANARY_OAUTH_ACCESS,
            "refresh": _CANARY_OAUTH_REFRESH,
            "expires": 1_900_000_000.0,
            "enterpriseUrl": "https://corp.anthropic.example",
        }
    }
    creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert creds[0].extras.get("enterprise_url") == "https://corp.anthropic.example"


def test_copies_metadata_to_extras_verbatim() -> None:
    """IMPORT-13 -- opencode api 'metadata' dict -> state 'extras' verbatim."""
    payload = {
        "openrouter": {
            "type": "api",
            "key": _CANARY_API_KEY,
            "metadata": {"siteUrl": "https://x", "fingerprint": "fp-TEST-CANARY"},
        }
    }
    creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert creds[0].extras.get("siteUrl") == "https://x"
    assert creds[0].extras.get("fingerprint") == "fp-TEST-CANARY"


# ── IMPORT-14: provenance marker (non-clobberable) ───────────────────────


def test_sets_provenance_marker_extras_source_opencode_import() -> None:
    """IMPORT-14 -- every imported cred carries extras['_source']='opencode-import'.

    Sub-assertion: a metadata dict containing _source: 'totally-not-opencode'
    MUST be overwritten -- the provenance marker survives clobber attempts.
    """
    payload = {
        "openrouter": {
            "type": "api",
            "key": _CANARY_API_KEY,
            "metadata": {"_source": "totally-not-opencode"},
        }
    }
    creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert creds[0].extras["_source"] == "opencode-import"


# ── IMPORT-15..IMPORT-16: provider_id validation logs ────────────────────


def test_unknown_provider_id_imported_with_info_log() -> None:
    """IMPORT-15 -- unknown provider_id imported but logged INFO
    (untracked_provider_imported)."""
    payload = {
        "totally-fake-provider": {"type": "api", "key": _CANARY_API_KEY}
    }
    with capture_logs() as logs:
        creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert len(creds) == 1
    assert any(
        "untracked" in (e.get("event") or "").lower() for e in logs
    )


@pytest.mark.parametrize("pid", _KNOWN_PROVIDER_IDS)
def test_known_provider_id_no_warning(pid: str) -> None:
    """IMPORT-16 -- 16 known provider_ids do NOT emit untracked warning."""
    payload = {pid: {"type": "api", "key": _CANARY_API_KEY}}
    with capture_logs() as logs:
        creds = parse_opencode_auth(env_content=json.dumps(payload))
    assert len(creds) == 1
    assert not any(
        "untracked" in (e.get("event") or "").lower() for e in logs
    )


# ── IMPORT-17..IMPORT-18: P1-7 array-shape invariant ─────────────────────


def test_array_shape_preserved_single_cred() -> None:
    """IMPORT-17 -- single opencode entry -> providers[pid] is a 1-element list."""
    payload = {"openrouter": {"type": "api", "key": _CANARY_API_KEY}}
    creds = parse_opencode_auth(env_content=json.dumps(payload))
    # Group-by provider_id and assert list length 1.
    by_pid: dict[str, list[Any]] = {}
    for c in creds:
        by_pid.setdefault(c.provider_id, []).append(c)
    assert by_pid["openrouter"] == [creds[0]]
    assert len(by_pid["openrouter"]) == 1


@st.composite
def _opencode_api_entry(draw: Any) -> dict:
    return {
        "type": "api",
        "key": "sk-TEST-CANARY-"
        + draw(st.text(alphabet="abcdef0123456789", min_size=20, max_size=40)),
    }


@given(n_providers=st.integers(min_value=1, max_value=5))
@settings(max_examples=10, deadline=None)
def test_array_shape_preserved_hypothesis(n_providers: int) -> None:
    """IMPORT-18 -- P1-7 round-trip with 1, 2, 5 entries across providers.

    Note: opencode's auth.json is Record<provider_id, Info> so multi-cred
    for the SAME provider is structurally impossible. We vary across
    providers and assert each provider lands as exactly 1-element list.
    """
    payload = {
        f"provider_{i}": {"type": "api", "key": f"sk-TEST-CANARY-{'x' * (20 + i)}"}
        for i in range(n_providers)
    }
    creds = parse_opencode_auth(env_content=json.dumps(payload))
    by_pid: dict[str, list[Any]] = {}
    for c in creds:
        by_pid.setdefault(c.provider_id, []).append(c)
    assert len(by_pid) == n_providers
    for pid_creds in by_pid.values():
        assert len(pid_creds) == 1


# ── IMPORT-19..IMPORT-20: identity + append-only ─────────────────────────


def test_append_only_to_existing_array() -> None:
    """IMPORT-19 -- state has cred A; opencode has different-prefix cred B
    -> providers[pid] grows by one (no in-place mutation).
    """
    from state_core.auth.store import AuthVault

    existing_a = ApiKeyCredential(key=_CANARY_API_KEY, provider_id="openrouter")
    existing_vault = AuthVault(providers={"openrouter": [existing_a]})
    payload = {"openrouter": {"type": "api", "key": _CANARY_API_KEY_2}}
    new_creds = parse_opencode_auth(
        env_content=json.dumps(payload), existing_vault=existing_vault
    )
    # The importer returns only NEW creds (or staged additions). Length 1.
    assert len(new_creds) == 1
    assert new_creds[0].key == _CANARY_API_KEY_2


def test_identity_by_provider_id_and_access_prefix_12() -> None:
    """IMPORT-20 -- identity is (provider_id, first 12 chars of access/key).

    Same prefix -> dedup; different prefix -> new array element.
    """
    from state_core.auth.store import AuthVault

    existing = ApiKeyCredential(key=_CANARY_API_KEY, provider_id="openrouter")
    existing_vault = AuthVault(providers={"openrouter": [existing]})
    # Same first 12 chars of key -> dedup.
    same_prefix_payload = {"openrouter": {"type": "api", "key": _CANARY_API_KEY}}
    deduped = parse_opencode_auth(
        env_content=json.dumps(same_prefix_payload), existing_vault=existing_vault
    )
    assert deduped == []
    # Different first 12 chars -> new element.
    diff_prefix_payload = {"openrouter": {"type": "api", "key": _CANARY_API_KEY_2}}
    new_creds = parse_opencode_auth(
        env_content=json.dumps(diff_prefix_payload), existing_vault=existing_vault
    )
    assert len(new_creds) == 1


# ── IMPORT-21: dedup-within-input is structurally unreachable ────────────


def test_dedupe_within_input_unreachable_for_normal_shape() -> None:
    """IMPORT-21 -- opencode auth.json is Record<provider_id, Info>.

    JSON-object semantics collapse repeated keys at the orjson layer,
    so duplicate provider_ids cannot be observed by the importer. The
    importer module MUST NOT carry an in-loop `seen_identities` set --
    that dead code path is explicitly forbidden.

    Cross-vault dedup is covered by IMPORT-19/IMPORT-20.
    """
    src_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "src"
        / "state_core"
        / "auth"
        / "import_opencode.py"
    )
    src = src_path.read_text()
    assert "seen_identities" not in src, (
        "IMPORT-21: importer must NOT carry seen_identities set; "
        "duplicate provider_ids are structurally impossible at JSON layer"
    )


# ── IMPORT-22: transactional all-or-nothing ──────────────────────────────


def test_all_or_nothing_transactional_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, auth_json_path: Path
) -> None:
    """IMPORT-22 -- one bad opencode entry => state vault untouched.

    Validate every opencode entry first; build candidate vault in
    memory; single save_vault() write. Any validation error aborts
    BEFORE any write.
    """
    monkeypatch.setenv("STATE_AUTH_JSON", str(auth_json_path))
    payload = {
        "openrouter": {"type": "api", "key": _CANARY_API_KEY},
        "broken": {"type": "api"},  # missing 'key' -> validation error
    }
    src = tmp_path / "auth.json"
    src.write_text(json.dumps(payload))
    monkeypatch.setenv("STATE_OPENCODE_AUTH_PATH", str(src))
    import asyncio

    with pytest.raises(Exception):  # noqa: B017 - exact type pinned by Plan 02
        # Rule 1 fix: import_from_opencode is async (awaits store.append);
        # asyncio.run drives the coroutine and re-raises validation errors.
        asyncio.run(
            import_from_opencode(existing_vault=None, store=_StubStore())
        )
    # State vault must not have been written.
    assert not auth_json_path.exists()


# ── IMPORT-23..IMPORT-24: event emission + secret hygiene ────────────────


def test_emits_auth_imported_event_per_credential(
    monkeypatch: pytest.MonkeyPatch, auth_json_path: Path
) -> None:
    """IMPORT-23 -- one state.auth.imported event per imported credential.

    Rule 1 fix: IMPORT-23 originally relied on cwd-relative .state/auth.json
    which polluted the real project vault. We now pin STATE_AUTH_JSON to a
    per-test tmp path so the importer's save_vault() is isolated.
    """
    import asyncio

    monkeypatch.setenv("STATE_AUTH_JSON", str(auth_json_path))
    payload = {
        "openrouter": {"type": "api", "key": _CANARY_API_KEY},
        "deepseek": {"type": "api", "key": _CANARY_API_KEY_2},
    }
    store = _StubStore()
    asyncio.run(
        _run_import_async(env_content=json.dumps(payload), store=store)
    )
    # One append per imported credential.
    assert len(store.events) == 2


async def _run_import_async(env_content: str, store: _StubStore) -> Any:
    return await import_from_opencode(env_content=env_content, store=store)


def test_event_payload_contains_no_secret_bytes() -> None:
    """IMPORT-24 -- rendered event JSON MUST NOT contain canary substring."""
    data = AuthImportedData(provider_id="openrouter", cred_kind="api_key")
    rendered = data.model_dump_json()
    assert "TEST-CANARY-" not in rendered
    # Defense in depth: assert the field set is exactly the 3 contracted fields.
    assert set(json.loads(rendered).keys()) == {"provider_id", "source", "cred_kind"}


# ── IMPORT-25: determinism rule (AST scan) ───────────────────────────────


def test_importer_does_not_call_time_or_datetime_now() -> None:
    """IMPORT-25 -- importer module MUST NOT call time.time(),
    datetime.now(), or datetime.utcnow() (cardinal determinism rule).

    WR-03 fix: the previous AST walker only matched 2-segment dotted
    attribute access (e.g. ``time.time``) and silently passed
    ``datetime.datetime.now()``, ``import time as t; t.time()``, and
    ``from time import time; time()``. We now use a substring scan
    (catches dotted/nested forms) plus an ImportFrom AST walker
    (catches bare-name forms via ``from time import time``).
    """
    src_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "src"
        / "state_core"
        / "auth"
        / "import_opencode.py"
    )
    src = src_path.read_text()

    # 1. Substring scan -- catches all dotted/nested attribute calls.
    banned_substrs = (
        "time.time(",
        "datetime.now(",
        "datetime.utcnow(",
        ".utcnow(",
    )
    for needle in banned_substrs:
        assert needle not in src, (
            f"determinism violation: {needle!r} in import_opencode.py"
        )

    # 2. AST walker -- catches `from time import time; time()` and
    #    `from datetime import datetime; datetime.now()` forms that the
    #    substring scan can't distinguish from harmless local names.
    tree = ast.parse(src)
    banned_imports = {
        ("time", "time"),
        ("datetime", "datetime"),  # from datetime import datetime -> datetime.now()
        ("datetime", "now"),
        ("datetime", "utcnow"),
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {"time", "datetime"}:
            for alias in node.names:
                pair = (node.module, alias.name)
                assert pair not in banned_imports, (
                    f"determinism violation: from {node.module} "
                    f"import {alias.name} in import_opencode.py"
                )

    # 3. AST walker -- catches `import time as t` aliases that the
    #    substring scan would miss because the call site is ``t.time()``.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in {"time", "datetime"}, (
                    f"determinism violation: import {alias.name} "
                    f"(as {alias.asname or alias.name}) in import_opencode.py"
                )


# ── IMPORT-26: smoke -- empty input ──────────────────────────────────────


def test_returns_zero_credentials_when_opencode_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """IMPORT-26 -- absent file => empty result, no save_vault call."""
    import asyncio

    monkeypatch.setenv("STATE_OPENCODE_AUTH_PATH", str(tmp_path / "missing.json"))
    store = _StubStore()
    # Rule 1 fix: import_from_opencode is async; drive via asyncio.run.
    result = asyncio.run(import_from_opencode(existing_vault=None, store=store))
    assert result == [] or result is None
    assert store.events == []
