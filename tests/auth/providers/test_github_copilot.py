"""Phase 017 RED test stubs for GitHubCopilotAuth — Wave 0 (AUTH-04).

Test names map 1:1 to VALIDATION.md row IDs (017-02-01..017-04-10).
Plan 02 turns Wave-2 sync helper tests GREEN (constants, models, sync
class methods). Plan 03 turns Wave-3 device-code polling state-machine
tests GREEN. Plan 04 turns Wave-4 mint/login/refresh/argparse tests
GREEN.

The 27th VALIDATION row (017-01-01) is the *collection gate* satisfied
by ``pytest --collect-only`` succeeding on this file at all — Task 1 of
Plan 01 (extending conftest.py with copilot fixtures) and Task 2 of
Plan 01 (this file) together discharge that row.

RED-state strategy:

    Plan 01 ships these stubs BEFORE
    ``state_core.auth.providers.github_copilot`` exists. The module is
    imported via ``pytest.importorskip`` so collection always succeeds —
    every test is SKIPPED (with a clear reason) until Plans 02/03/04
    land. Each test body is DRAFTED (not stubbed ``pass``) so later
    plans only delete the ``pytest.xfail`` line to flip XFAIL → GREEN.

The Copilot-specific constants asserted below are HARD-CODED in this
test file — they are NOT imported from the not-yet-existing source
module. This decouples the verification contract from implementation
order: the test file IS the spec.

Verified-source constants (RESEARCH §Pattern 1, §Pattern 7, §Code
Examples §1; cross-checked against copilot.vim, B00TK1D/copilot-api,
litellm, hermes-agent #16551):

  _CLIENT_ID              = "Iv1.b507a08c87ecfe98"   # legacy OAuth App
  _SCOPE                  = "read:user"
  _USER_AGENT             = "GithubCopilot/1.155.0"
  _EDITOR_VERSION         = "Neovim/0.6.1"
  _EDITOR_PLUGIN_VERSION  = "copilot.vim/1.16.0"
  _POLLING_SAFETY_MARGIN_S = 3.0
  _SLOW_DOWN_BUMP_S        = 5.0
  provider_id              = "github.copilot"        # dotted-namespace

Reference: 017-RESEARCH.md §Code Examples §1-§8, §Common Pitfalls 1-14.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

# Direct ImportError on collection would also be acceptable RED, but the
# preferred shape is collection-passes-then-skips so the
# `--collect-only` catalogue surfaces every stub by name (matches
# Phase 015/016 pattern).

try:
    from state_core.auth.providers import github_copilot  # type: ignore[import-not-found]

    _COPILOT_AVAILABLE = True
    _IMPORT_ERROR: ImportError | None = None
except ImportError as _e:  # pragma: no cover — RED state for Wave 0
    _COPILOT_AVAILABLE = False
    _IMPORT_ERROR = _e
    github_copilot = None  # type: ignore[assignment]


pytestmark = pytest.mark.skipif(
    not _COPILOT_AVAILABLE,
    reason=f"Plans 02+ not yet landed: {_IMPORT_ERROR}",
)


# Pinned constants the test file owns directly so Plan 02 can land the
# source module without re-deriving these values from RESEARCH.md.
_CLIENT_ID = "Iv1.b507a08c87ecfe98"
_SCOPE = "read:user"
_USER_AGENT = "GithubCopilot/1.155.0"
_EDITOR_VERSION = "Neovim/0.6.1"
_EDITOR_PLUGIN_VERSION = "copilot.vim/1.16.0"
_PROVIDER_ID = "github.copilot"


# ── Wave 2 (Plan 02) — pure helpers + constants ──────────────────────────


def test_constants() -> None:
    """VALIDATION row 017-02-01 — P1-3 + Pitfall 2 client_id pinning.

    All Copilot-stealth constants are PLAINTEXT module-level literals.
    No base64.b64decode, no XOR, no os.environ indirection (P1-3 — AV
    scanners flag obfuscated literals as malicious).

    Pitfall 2 regression: ``_CLIENT_ID == "Iv1.b507a08c87ecfe98"`` (the
    legacy OAuth App). Tokens minted from the alternate
    ``Ov23li8tweQw6odWQebz`` (opencode's GitHub App) are NOT authorized
    for ``copilot_internal/v2/token`` — the entire two-tier flow breaks
    if the wrong client_id is used. Verified via hermes-agent #16551
    + cherry-studio #11905 + opencode #20759.

    Device-code flow is a PUBLIC client — there is NO _CLIENT_SECRET
    constant.
    """
    import re
    from pathlib import Path

    src = Path("src/state_core/auth/providers/github_copilot.py").read_text()

    # Pitfall 2 regression — exact legacy OAuth App ID, not opencode's.
    assert '_CLIENT_ID: str = "Iv1.b507a08c87ecfe98"' in src
    assert "Ov23li8tweQw6odWQebz" not in src  # opencode's ID — wrong for two-tier mint

    # P1-3: no obfuscation, no env-var indirection
    assert not re.search(r"_CLIENT_ID\s*=.*b64decode", src)
    assert not re.search(r"_CLIENT_ID\s*=.*environ", src)
    assert not re.search(r"_CLIENT_ID\s*=.*getenv", src)

    # Device-code is a public client — no client_secret exists at all.
    assert not hasattr(github_copilot, "_CLIENT_SECRET")
    assert "_CLIENT_SECRET" not in src

    # Module-level attribute checks
    assert github_copilot._CLIENT_ID == "Iv1.b507a08c87ecfe98"
    assert github_copilot._SCOPE == "read:user"
    assert github_copilot._USER_AGENT == "GithubCopilot/1.155.0"
    assert github_copilot._EDITOR_VERSION == "Neovim/0.6.1"
    assert github_copilot._EDITOR_PLUGIN_VERSION == "copilot.vim/1.16.0"

    # Polling-loop tuning constants (Pattern 2 + Pitfall 6 + Pitfall 10).
    assert github_copilot._POLLING_SAFETY_MARGIN_S == 3.0
    assert github_copilot._SLOW_DOWN_BUMP_S == 5.0


def test_provider_id_dotted() -> None:
    """VALIDATION row 017-02-02 — Pitfall 9-info dotted namespace.

    provider_id == 'github.copilot' (dotted), NOT opencode's
    'github-copilot' (hyphenated). Phase 021 (first-run import)
    translates opencode's identifier at import time. The dotted-
    namespace pattern is consistent across Phase 015 (google.gemini_cli)
    and Phase 016 (google.antigravity).
    """
    assert github_copilot.GitHubCopilotAuth.provider_id == _PROVIDER_ID
    assert github_copilot.GitHubCopilotAuth().provider_id == _PROVIDER_ID
    # Negative: must NOT be opencode's hyphenated form.
    assert github_copilot.GitHubCopilotAuth().provider_id != "github-copilot"


def test_is_token_oauth_long_lived() -> None:
    """VALIDATION row 017-02-03 — is_token recognises gho_/ghu_/ghr_ prefixes.

    Long-lived GitHub OAuth tokens have three documented prefixes:
      - gho_ : OAuth App user-to-server token (legacy OAuth App)
      - ghu_ : User-to-server (GitHub App)
      - ghr_ : Refresh token (some flows)

    is_token must NOT match other providers' prefixes (sk-ant-*, ya29.*).
    """
    auth = github_copilot.GitHubCopilotAuth()

    # All three GitHub OAuth prefixes recognised.
    assert auth.is_token("gho_FOO") is True
    assert auth.is_token("ghu_BAR") is True
    assert auth.is_token("ghr_BAZ") is True

    # Other-provider prefixes rejected.
    assert auth.is_token("sk-ant-foo") is False
    assert auth.is_token("ya29.foo") is False
    assert auth.is_token("") is False
    # Case-sensitive (GitHub ships lowercase).
    assert auth.is_token("GHO_UPPER") is False
    # No leading whitespace tolerated.
    assert auth.is_token(" gho_x") is False


def test_is_token_session_token() -> None:
    """VALIDATION row 017-02-04 — is_token also recognises tid_* session tokens.

    The two-tier architecture means the provider issues both flavours:
      - access field: short-lived tid_* Copilot session token (~30 min)
      - refresh field: long-lived gho_*/ghu_* GitHub OAuth token

    is_token must return True for ALL FOUR Copilot-related prefixes so
    the token-shape sniffer in Phase 019 routing recognises both tiers.
    """
    auth = github_copilot.GitHubCopilotAuth()

    assert auth.is_token("tid_FIXTURE") is True
    assert auth.is_token("tid_") is True  # bare prefix accepted (degenerate)

    # All four Copilot-related prefixes return True.
    for prefix in ("gho_", "ghu_", "ghr_", "tid_"):
        assert auth.is_token(f"{prefix}xxxxx") is True, f"{prefix} not recognised"

    # Negative cases.
    assert auth.is_token("TID_UPPER") is False
    assert auth.is_token("xtid_") is False


def test_is_expired_5min_buffer_session() -> None:
    """VALIDATION row 017-02-05 — Pitfall 5 + P0-7/AUTH-09 buffer applies to tid_*.

    The 5-minute buffer applies to the SHORT-lived tid_* session token
    (cred.expires tracks tid_* expiry), NOT to the long-lived gho_*
    OAuth token in cred.refresh. (gho_* on the legacy OAuth App
    Iv1.b507a08c87ecfe98 does not rotate; it has no expiry until the
    user revokes it.)

    Boundary semantics: ``now >= cred.expires - 300.0`` → expired.
    """
    from state_core.auth.base import OAuthCredential

    auth = github_copilot.GitHubCopilotAuth()
    now = 1_770_000_000.0

    # Cred expires 200s after now → INSIDE 5-min buffer → expired.
    cred_inside = OAuthCredential(
        access="tid_x",
        refresh="gho_x",
        expires=now + 200.0,
        provider_id=_PROVIDER_ID,
    )
    assert auth.is_expired(cred_inside, now=now) is True

    # Cred expires 400s after now → OUTSIDE 5-min buffer → not expired.
    cred_outside = OAuthCredential(
        access="tid_y",
        refresh="gho_y",
        expires=now + 400.0,
        provider_id=_PROVIDER_ID,
    )
    assert auth.is_expired(cred_outside, now=now) is False

    # Boundary at exactly now == expires - 300 → expired (>= boundary).
    cred_boundary = OAuthCredential(
        access="tid_z",
        refresh="gho_z",
        expires=now + 300.0,
        provider_id=_PROVIDER_ID,
    )
    assert auth.is_expired(cred_boundary, now=now) is True


def test_http_headers_copilot_stealth() -> None:
    """VALIDATION row 017-02-06 — Pitfall 12 byte-stable Copilot stealth headers.

    http_headers must return EXACTLY four keys for an OAuthCredential:
      - authorization: Bearer <cred.access>
      - user-agent: GithubCopilot/1.155.0
      - editor-version: Neovim/0.6.1
      - editor-plugin-version: copilot.vim/1.16.0

    The ``cred.access`` value is the short-lived tid_* (NOT the gho_*
    in cred.refresh). Phase 022 captured-header regression locks this
    byte-for-byte; future drift is Pitfall 12.

    For ApiKeyCredential the method returns {} (caller decides for
    non-OAuth — mirrors Phase 015 pattern).
    """
    from state_core.auth.base import ApiKeyCredential, OAuthCredential

    auth = github_copilot.GitHubCopilotAuth()
    cred = OAuthCredential(
        access="tid_SESSION_TOKEN",
        refresh="gho_OAUTH_TOKEN",
        expires=99_999_999_999.0,
        provider_id=_PROVIDER_ID,
    )
    headers = auth.http_headers(cred)

    # Exactly four keys.
    assert set(headers.keys()) == {
        "authorization",
        "user-agent",
        "editor-version",
        "editor-plugin-version",
    }
    # Byte-stable values — Bearer carries the tid_*, not gho_*.
    assert headers["authorization"] == "Bearer tid_SESSION_TOKEN"
    assert headers["user-agent"] == _USER_AGENT
    assert headers["editor-version"] == _EDITOR_VERSION
    assert headers["editor-plugin-version"] == _EDITOR_PLUGIN_VERSION

    # ApiKeyCredential → empty dict
    api = ApiKeyCredential(key="sk-test", provider_id=_PROVIDER_ID)
    assert auth.http_headers(api) == {}


def test_satisfies_authmethod_protocol() -> None:
    """VALIDATION row 017-02-07 — structural conformance to AuthMethod.

    isinstance check exercises the @runtime_checkable Protocol — every
    documented method (is_token, is_expired, http_headers, login,
    refresh) plus the provider_id attribute must be present.
    """
    from state_core.auth.base import AuthMethod

    assert isinstance(github_copilot.GitHubCopilotAuth(), AuthMethod) is True


# ── Wave 3 (Plan 03) — device-code polling state machine ────────────────


@pytest.mark.asyncio
async def test_request_device_code(
    httpx_mock,
    mock_device_code_response: dict[str, Any],
) -> None:
    """VALIDATION row 017-03-01 — POST /login/device/code with JSON body.

    _request_device_code POSTs to https://github.com/login/device/code
    with body {"client_id": _CLIENT_ID, "scope": "read:user"} and
    headers accept/content-type/user-agent. Returns DeviceCodeResponse.
    """
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/device/code",
        json=mock_device_code_response,
    )

    resp = await github_copilot._request_device_code()

    # Returned shape
    assert resp.device_code == mock_device_code_response["device_code"]
    assert resp.user_code == "ABCD-1234"
    assert resp.verification_uri == "https://github.com/login/device"
    assert resp.expires_in == 900
    assert resp.interval == 5

    # Request shape: JSON body + correct headers
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.headers.get("accept") == "application/json"
    assert req.headers.get("content-type", "").startswith("application/json")
    assert req.headers.get("user-agent") == _USER_AGENT

    import orjson
    body = orjson.loads(req.content)
    assert body == {"client_id": _CLIENT_ID, "scope": _SCOPE}


@pytest.mark.asyncio
async def test_poll_authorization_pending(
    httpx_mock,
    mock_token_poll_responses: dict[str, dict[str, Any]],
) -> None:
    """VALIDATION row 017-03-02 — RFC 8628 §3.5 authorization_pending continues.

    Poll loop receives ``{"error":"authorization_pending"}`` then
    success. Use sequenced httpx_mock + injected monotonic (advances 5s
    per call) + injected sleep (records durations). Asserts ≥ 2
    iterations and final return is the access_token from the success
    response.
    """
    # Sequenced responses: pending then success.
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["authorization_pending"],
    )
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["success"],
    )

    monotonic_calls = iter([0.0, 5.0, 10.0, 15.0])
    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    token = await github_copilot._poll_for_token(
        device_code="FIXTURE-DEVICE-CODE",
        initial_interval=5,
        expires_in=900,
        monotonic=lambda: next(monotonic_calls),
        sleep=fake_sleep,
    )

    # Final return is the gho_* OAuth token from the success response.
    assert token == "gho_FIXTURE-LONG-LIVED-OAUTH-TOKEN-aaaaaaaaaaaaaaaaaa"
    # At least 2 sleeps (one before each poll).
    assert len(sleep_calls) >= 2
    # First sleep == initial interval + safety margin = 5 + 3 = 8s.
    assert sleep_calls[0] == 8.0


@pytest.mark.asyncio
async def test_poll_slow_down_increases_interval(
    httpx_mock,
    mock_token_poll_responses: dict[str, dict[str, Any]],
) -> None:
    """VALIDATION row 017-03-03 — Pitfall 6 RFC §3.5 slow_down +5s bump.

    First poll → slow_down (no server interval). Capture sleep call
    args. Assert second sleep is (initial + 5) + safety_margin = 8 + 3
    = 11 seconds (initial=5, +5 RFC bump, +3 safety margin).
    """
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["slow_down_no_interval"],
    )
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["success"],
    )

    monotonic_calls = iter([0.0, 11.0, 22.0, 33.0])
    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    token = await github_copilot._poll_for_token(
        device_code="FIXTURE-DEVICE-CODE",
        initial_interval=5,
        expires_in=900,
        monotonic=lambda: next(monotonic_calls),
        sleep=fake_sleep,
    )

    assert token == "gho_FIXTURE-LONG-LIVED-OAUTH-TOKEN-aaaaaaaaaaaaaaaaaa"
    # First sleep: initial interval (5) + safety margin (3) = 8s.
    assert sleep_calls[0] == 8.0
    # Second sleep AFTER slow_down: bumped interval (5+5=10) + safety (3) = 13s.
    # NOTE the RFC §3.5 bump is +5 to the INTERVAL state; safety margin
    # is added on top — total = (initial + 5) + 3 = 11s when computed
    # as (initial + slow_down_bump + safety) = 5 + 5 + 3 = 13s.
    assert sleep_calls[1] == 13.0


@pytest.mark.asyncio
async def test_poll_slow_down_persists(
    httpx_mock,
    mock_token_poll_responses: dict[str, dict[str, Any]],
) -> None:
    """VALIDATION row 017-03-04 — Pitfall 6 (NEW OWNED) slow_down persistence.

    Two consecutive slow_down responses then success. Record all sleep
    durations. Assert THIRD sleep uses interval = initial + 5 + 5 + 3
    = 18 seconds (each slow_down bumps the persisted interval by 5;
    interval does NOT reset between iterations — RFC §3.5 mandates
    persistence).
    """
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["slow_down_no_interval"],
    )
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["slow_down_no_interval"],
    )
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["success"],
    )

    monotonic_calls = iter([0.0, 11.0, 22.0, 40.0, 60.0])
    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    token = await github_copilot._poll_for_token(
        device_code="FIXTURE-DEVICE-CODE",
        initial_interval=5,
        expires_in=900,
        monotonic=lambda: next(monotonic_calls),
        sleep=fake_sleep,
    )

    assert token == "gho_FIXTURE-LONG-LIVED-OAUTH-TOKEN-aaaaaaaaaaaaaaaaaa"
    # First sleep: interval=5 + safety=3 → 8s.
    assert sleep_calls[0] == 8.0
    # Second sleep AFTER first slow_down: interval=5+5=10 + safety=3 → 13s.
    assert sleep_calls[1] == 13.0
    # Third sleep AFTER second slow_down: interval=5+5+5=15 + safety=3 → 18s
    # — interval persists across iterations, NOT reset to initial.
    assert sleep_calls[2] == 18.0


@pytest.mark.asyncio
async def test_poll_access_denied(
    httpx_mock,
    mock_token_poll_responses: dict[str, dict[str, Any]],
) -> None:
    """VALIDATION row 017-03-05 — terminal access_denied raises AuthLoginError.

    Poll receives {"error":"access_denied"} → raises AuthLoginError
    with a message containing "denied" or "User denied".
    """
    from state_core.auth.errors import AuthLoginError

    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["access_denied"],
    )

    monotonic_calls = iter([0.0, 5.0, 10.0])
    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    with pytest.raises(AuthLoginError, match=r"(?i)denied"):
        await github_copilot._poll_for_token(
            device_code="FIXTURE-DEVICE-CODE",
            initial_interval=5,
            expires_in=900,
            monotonic=lambda: next(monotonic_calls),
            sleep=fake_sleep,
        )


@pytest.mark.asyncio
async def test_poll_expired_token(
    httpx_mock,
    mock_token_poll_responses: dict[str, dict[str, Any]],
) -> None:
    """VALIDATION row 017-03-06 — Pitfall 3 expired_token raises AuthLoginError.

    Poll receives {"error":"expired_token"} → raises AuthLoginError
    with a message containing "expired" or "Device code expired".
    """
    from state_core.auth.errors import AuthLoginError

    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["expired_token"],
    )

    monotonic_calls = iter([0.0, 5.0, 10.0])
    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    with pytest.raises(AuthLoginError, match=r"(?i)expired"):
        await github_copilot._poll_for_token(
            device_code="FIXTURE-DEVICE-CODE",
            initial_interval=5,
            expires_in=900,
            monotonic=lambda: next(monotonic_calls),
            sleep=fake_sleep,
        )


@pytest.mark.asyncio
async def test_poll_monotonic_deadline(
    httpx_mock,
    mock_token_poll_responses: dict[str, dict[str, Any]],
) -> None:
    """VALIDATION row 017-03-07 — Pitfall 7 (NEW OWNED) monotonic deadline.

    Inject monotonic callable that starts at 0.0 then advances by
    1000.0 (>900s expires_in) on subsequent call. After the deadline
    check fires, raises AuthLoginError containing "expired" or
    "deadline".

    Source-level grep gate: implementation NEVER reads time.time() for
    deadline math — only time.monotonic(). (time.time may appear in
    expires-epoch wire-shape construction; we tolerate ≤ 1 occurrence
    for that.)
    """
    from pathlib import Path

    from state_core.auth.errors import AuthLoginError

    # First poll returns pending; second monotonic() call exceeds deadline.
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["authorization_pending"],
    )

    monotonic_calls = iter([0.0, 1000.0, 2000.0])
    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    with pytest.raises(AuthLoginError, match=r"(?i)expired|deadline"):
        await github_copilot._poll_for_token(
            device_code="FIXTURE-DEVICE-CODE",
            initial_interval=5,
            expires_in=900,
            monotonic=lambda: next(monotonic_calls),
            sleep=fake_sleep,
        )

    # Source-level grep gate: time.time() should appear at most once
    # (only for wire-shape `expires` epoch construction in _to_credential).
    src = Path("src/state_core/auth/providers/github_copilot.py").read_text()
    assert src.count("time.time") <= 1, (
        "Pitfall 7: deadline math must use time.monotonic, not time.time"
    )
    # Positive: time.monotonic IS used.
    assert "time.monotonic" in src or "monotonic" in src


@pytest.mark.asyncio
async def test_poll_safety_margin_3s(
    httpx_mock,
    mock_token_poll_responses: dict[str, dict[str, Any]],
) -> None:
    """VALIDATION row 017-03-08 — Pitfall 10 (NEW OWNED) 3-second safety margin.

    Capture all sleep call args. Initial interval=5. Assert FIRST sleep
    is 5 + 3 = 8 seconds (the 3-second safety margin
    OAUTH_POLLING_SAFETY_MARGIN_MS=3000 from opencode is added to every
    sleep — defends against client/server clock skew).
    """
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["success"],
    )

    monotonic_calls = iter([0.0, 8.0, 16.0])
    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    await github_copilot._poll_for_token(
        device_code="FIXTURE-DEVICE-CODE",
        initial_interval=5,
        expires_in=900,
        monotonic=lambda: next(monotonic_calls),
        sleep=fake_sleep,
    )

    # First sleep MUST be initial interval (5) + safety margin (3) = 8.0s.
    assert sleep_calls[0] == 8.0


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_poll_cancelled_via_signal(
    httpx_mock,
    mock_token_poll_responses: dict[str, dict[str, Any]],
) -> None:
    """VALIDATION row 017-03-09 — Pitfall 9 (NEW OWNED) CancelledError propagates.

    Inject sleep callable that raises asyncio.CancelledError. Assert
    _poll_for_token propagates CancelledError (NOT wrapped as
    AuthLoginError). Long-running polling loops must respect SIGINT /
    asyncio task cancellation; swallowing CancelledError leaves zombie
    tasks alive.

    Note: ``assert_all_responses_were_requested=False`` because sleep
    raises CancelledError BEFORE the first HTTP call, so the registered
    response is never consumed — that's the whole point of the test.
    """
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["authorization_pending"],
    )

    monotonic_calls = iter([0.0, 5.0, 10.0])

    async def cancelling_sleep(d: float) -> None:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await github_copilot._poll_for_token(
            device_code="FIXTURE-DEVICE-CODE",
            initial_interval=5,
            expires_in=900,
            monotonic=lambda: next(monotonic_calls),
            sleep=cancelling_sleep,
        )


# ── Wave 4 (Plan 04) — mint / login / refresh / argparse ────────────────


@pytest.mark.asyncio
async def test_mint_session_token(
    httpx_mock,
    captured_session_mint_post: dict[str, Any],
) -> None:
    """VALIDATION row 017-04-01 — POST /copilot_internal/v2/token with stealth headers.

    _mint_session_token POSTs to https://api.github.com/copilot_internal/v2/token
    with Authorization: Bearer <gho_*> and the three Copilot-stealth
    headers. Returns CopilotSessionResponse.
    """
    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/copilot_internal/v2/token",
        json=captured_session_mint_post,
    )

    resp = await github_copilot._mint_session_token("gho_FIXTURE")

    # Response shape
    assert resp.token.startswith("tid_")
    assert resp.expires_at == 1893456000
    assert resp.refresh_in == 1500
    assert resp.sku == "copilot-individual"

    # Request shape: Bearer + Copilot-stealth headers.
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.headers.get("accept") == "application/json"
    assert req.headers.get("authorization") == "Bearer gho_FIXTURE"
    assert req.headers.get("user-agent") == _USER_AGENT
    assert req.headers.get("editor-version") == _EDITOR_VERSION
    assert req.headers.get("editor-plugin-version") == _EDITOR_PLUGIN_VERSION


@pytest.mark.asyncio
async def test_mint_grant_revoked_200_null_body(httpx_mock) -> None:
    """VALIDATION row 017-04-02 — Pitfall 4 / P1-6 grant-revocation detection.

    httpx_mock returns 200 with body {} (no `token` field). Pydantic
    ValidationError fires (token is required) → re-raised as
    AuthRefreshError containing "grant revoked" or "session response
    shape".

    This is the primary grant-revocation signal — when the user
    revokes Copilot access in GitHub settings, the legacy OAuth App
    keeps issuing 200s with empty bodies for `copilot_internal/v2/token`
    rather than 401s. We MUST treat 200-with-null-body as terminal.
    """
    from state_core.auth.errors import AuthRefreshError

    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/copilot_internal/v2/token",
        json={},  # empty body — no `token` field
    )

    with pytest.raises(AuthRefreshError, match=r"(?i)grant revoked|session.*shape"):
        await github_copilot._mint_session_token("gho_FIXTURE")


@pytest.mark.asyncio
async def test_mint_grant_revoked_401(httpx_mock) -> None:
    """VALIDATION row 017-04-03 — 401 response raises AuthRefreshError.

    httpx_mock returns 401 with body {"message":"Bad credentials"}.
    _mint_session_token raises AuthRefreshError with a message
    containing "401" or "grant rejected".
    """
    from state_core.auth.errors import AuthRefreshError

    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/copilot_internal/v2/token",
        status_code=401,
        json={"message": "Bad credentials"},
    )

    with pytest.raises(AuthRefreshError, match=r"401|grant rejected"):
        await github_copilot._mint_session_token("gho_FIXTURE_INVALID")


@pytest.mark.asyncio
async def test_mint_pydantic_validation(httpx_mock) -> None:
    """VALIDATION row 017-04-04 — Pydantic shape validation of mint response.

    httpx_mock returns 200 with {"token":"tid_x","expires_at":"not-an-int"}
    (wrong type). _mint_session_token raises AuthRefreshError
    containing "session-token response shape" or "ValidationError".
    """
    from state_core.auth.errors import AuthRefreshError

    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/copilot_internal/v2/token",
        json={"token": "tid_x", "expires_at": "not-an-int"},
    )

    with pytest.raises(
        AuthRefreshError, match=r"(?i)session.?token response shape|ValidationError"
    ):
        await github_copilot._mint_session_token("gho_FIXTURE")


@pytest.mark.asyncio
async def test_login_full_device_flow(
    httpx_mock,
    monkeypatch,
    mock_device_code_response: dict[str, Any],
    mock_token_poll_responses: dict[str, dict[str, Any]],
    captured_session_mint_post: dict[str, Any],
) -> None:
    """VALIDATION row 017-04-05 — end-to-end login: device → poll → mint.

    Three sequenced httpx_mock responses (device-code, poll-success,
    session-mint). cred = await GitHubCopilotAuth().login() returns
    OAuthCredential with:
      - provider_id == "github.copilot"
      - access starts with "tid_"  (short-lived session token)
      - refresh starts with "gho_" (long-lived OAuth token)
      - expires == captured_session_mint_post["expires_at"] (server
        epoch, NOT now+expires_in)
      - extras["oauth_token"] == cred.refresh (mirror)
    """
    # 1. Device-code endpoint
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/device/code",
        json=mock_device_code_response,
    )
    # 2. Polling token endpoint — success on first poll.
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json=mock_token_poll_responses["success"],
    )
    # 3. Copilot session-token mint
    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/copilot_internal/v2/token",
        json=captured_session_mint_post,
    )

    # Suppress the print() of verification_uri + user_code during test.
    monkeypatch.setattr(
        "state_core.auth.providers.github_copilot.print",
        lambda *_a, **_kw: None,
    )
    # Patch sleep to no-op so polling doesn't actually wait.
    async def _fast_sleep(_d: float) -> None:
        return None

    monkeypatch.setattr(
        "state_core.auth.providers.github_copilot.asyncio.sleep",
        _fast_sleep,
        raising=False,
    )

    cred = await github_copilot.GitHubCopilotAuth().login()

    assert cred.provider_id == _PROVIDER_ID
    assert cred.access.startswith("tid_")
    assert cred.refresh.startswith("gho_")
    # expires uses the server-returned epoch DIRECTLY — no now+expires_in math.
    assert cred.expires == float(captured_session_mint_post["expires_at"])
    # extras["oauth_token"] mirrors cred.refresh for read-clarity.
    assert cred.extras["oauth_token"] == cred.refresh
    # Editor-version captured into extras for header-drift forensics.
    assert cred.extras.get("editor_version") == _EDITOR_VERSION


@pytest.mark.asyncio
async def test_refresh_remints_session_no_oauth_call(
    httpx_mock,
    captured_session_mint_post: dict[str, Any],
) -> None:
    """VALIDATION row 017-04-06 — refresh re-mints tid_*, NEVER hits OAuth endpoint.

    Original cred has refresh="gho_OLD", access="tid_OLD". httpx_mock
    for /copilot_internal/v2/token returns new tid + new expires_at.
    Asserts NO httpx call ever goes to /login/oauth/access_token —
    refresh does NOT call GitHub's OAuth refresh endpoint (legacy
    OAuth App Iv1.b507a08c87ecfe98 doesn't issue refresh_tokens, so
    the gho_* is permanent until revoked).

    After refresh: new access (new tid), refresh="gho_OLD" (unchanged
    — gho_* is long-lived).
    """
    from state_core.auth.base import OAuthCredential

    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/copilot_internal/v2/token",
        json=captured_session_mint_post,
    )

    old = OAuthCredential(
        access="tid_OLD",
        refresh="gho_OLD",
        expires=0.0,
        provider_id=_PROVIDER_ID,
        extras={"oauth_token": "gho_OLD", "editor_version": _EDITOR_VERSION},
    )
    new = await github_copilot.GitHubCopilotAuth().refresh(old)

    # New access is the freshly-minted tid_*.
    assert new.access == captured_session_mint_post["token"]
    assert new.access != "tid_OLD"
    # Refresh field unchanged — gho_* is long-lived.
    assert new.refresh == "gho_OLD"
    # Expires updated from server response.
    assert new.expires == float(captured_session_mint_post["expires_at"])

    # Crucial: NO call to /login/oauth/access_token.
    requests = httpx_mock.get_requests()
    for req in requests:
        assert "login/oauth/access_token" not in str(req.url), (
            "refresh() must NOT call GitHub's OAuth refresh endpoint; "
            "legacy OAuth App does not issue refresh_tokens."
        )
    # All requests went to copilot_internal/v2/token.
    assert len(requests) == 1
    assert "copilot_internal/v2/token" in str(requests[0].url)


@pytest.mark.asyncio
async def test_refresh_persists_extras_oauth_token(
    httpx_mock,
    captured_session_mint_post: dict[str, Any],
) -> None:
    """VALIDATION row 017-04-07 — refresh preserves extras across model_copy.

    Original cred has extras={"oauth_token":"gho_OLD","editor_version":
    "Neovim/0.6.1","sku":"copilot-individual"}. After refresh,
    extras["oauth_token"] is still the gho_* (unchanged) and
    extras["editor_version"] is preserved (frozen-model-safe via
    model_copy).
    """
    from state_core.auth.base import OAuthCredential

    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/copilot_internal/v2/token",
        json=captured_session_mint_post,
    )

    old = OAuthCredential(
        access="tid_OLD",
        refresh="gho_OLD",
        expires=0.0,
        provider_id=_PROVIDER_ID,
        extras={
            "oauth_token": "gho_OLD",
            "editor_version": _EDITOR_VERSION,
            "sku": "copilot-individual",
        },
    )
    new = await github_copilot.GitHubCopilotAuth().refresh(old)

    # oauth_token mirror preserved.
    assert new.extras["oauth_token"] == "gho_OLD"
    assert new.extras["oauth_token"] == new.refresh
    # editor_version preserved.
    assert new.extras["editor_version"] == _EDITOR_VERSION
    # sku may be updated from response, but original key still present.
    assert "sku" in new.extras


def test_main_argparse_login(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    tmp_path,
) -> None:
    """VALIDATION row 017-04-08 — `python -m ... github_copilot login` argparse path.

    Patch login() to return canned cred, patch vault to redirect to
    tmp_path. Assert exit code 0 and stdout contains "Logged in as".
    Verify --enterprise-url argument is accepted by argparse.
    """
    pytest.xfail("Plan 04 implements _main argparse login subcommand")
    import sys as _sys

    from state_core.auth.base import OAuthCredential

    monkeypatch.setenv("STATE_AUTH_JSON", str(tmp_path / "auth.json"))
    monkeypatch.setattr(_sys, "argv", ["github_copilot.py", "login"])

    canned = OAuthCredential(
        access="tid_canned",
        refresh="gho_canned",
        expires=99_999_999_999.0,
        provider_id=_PROVIDER_ID,
        account_id="canned-user",
        extras={"oauth_token": "gho_canned", "editor_version": _EDITOR_VERSION},
    )

    async def _fake_login(self, *, enterprise_url: str | None = None):
        return canned

    monkeypatch.setattr(
        github_copilot.GitHubCopilotAuth, "login", _fake_login
    )

    rc = github_copilot._main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "Logged in as" in captured.out

    # Verify --enterprise-url is an accepted argument.
    monkeypatch.setattr(
        _sys, "argv", ["github_copilot.py", "login", "--enterprise-url", "company.ghe.com"]
    )
    rc2 = github_copilot._main()
    assert rc2 == 0


def test_main_argparse_refresh(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    tmp_path,
) -> None:
    """VALIDATION row 017-04-09 — `python -m ... github_copilot refresh github.copilot`.

    Patch refresh_credential to a no-op coroutine. Assert exit code 0
    and stdout contains "Refreshed access_token for github.copilot".
    """
    pytest.xfail("Plan 04 implements _main argparse refresh subcommand")
    import sys as _sys

    monkeypatch.setenv("STATE_AUTH_JSON", str(tmp_path / "auth.json"))
    monkeypatch.setattr(
        _sys, "argv", ["github_copilot.py", "refresh", _PROVIDER_ID]
    )

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "state_core.auth.refresh.refresh_credential",
        _noop,
        raising=False,
    )

    rc = github_copilot._main()
    assert rc == 0
    captured = capsys.readouterr()
    assert f"Refreshed access_token for {_PROVIDER_ID}" in captured.out


def test_no_oauth_common_imports() -> None:
    """VALIDATION row 017-04-10 — Pitfall 13 source-level import gates.

    Three grep gates against src/state_core/auth/providers/github_copilot.py:
      1. NO ``from state_core.auth.oauth_common`` imports (device-code
         uses neither PKCE nor loopback — those are loopback-flow
         helpers).
      2. NO ``import litellm`` / ``from litellm`` (CLAUDE.md cardinal
         rule: OAuth flows NEVER route through litellm).
      3. NO ``from filelock`` / ``import filelock`` / ``AsyncFileLock``
         (refresh.py rule 9: provider does NOT acquire its own
         filelock; Phase 013's refresh_credential owns the lock).
    """
    pytest.xfail("Plan 04 lands the source module that satisfies these gates")
    from pathlib import Path

    src_path = Path("src/state_core/auth/providers/github_copilot.py")
    assert src_path.exists(), (
        "Plan 02 must create src/state_core/auth/providers/github_copilot.py"
    )
    src = src_path.read_text()

    # Gate 1: oauth_common (PKCE / loopback) NOT imported.
    assert "from state_core.auth.oauth_common" not in src, (
        "Pitfall 13: device-code flow has no PKCE and no loopback listener"
    )

    # Gate 2: litellm NEVER imported.
    assert "import litellm" not in src
    assert "from litellm" not in src

    # Gate 3: filelock NEVER acquired by provider.
    assert "from filelock" not in src
    assert "import filelock" not in src
    assert "AsyncFileLock" not in src
