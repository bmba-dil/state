"""Phase 020 — VALIDATION rows REDACT-01..REDACT-24, REDACT-26 (RED scaffolding).

Wave 1 — every test in this file MUST FAIL until Plan 02 (Wave 2) lands
`state_core.observability.redactor` AND Plan 03 (Wave 3) wires
`install()` + `assert_redactor_attached()` into the daemon orchestrator.
Failure modes:
  * ModuleNotFoundError on `from state_core.observability.redactor import …`
  * AttributeError on test bodies referencing not-yet-existent attributes
  * AssertionError when stub returns a placeholder value

REDACT-25 (mode isolation) lives in tests/test_observability_import_graph.py.
See 020-RESEARCH.md §Validation Architecture for the row→test mapping.

Row → test function mapping (canonical):
  REDACT-01  test_redacts_anthropic_oat
  REDACT-02  test_redacts_anthropic_api_key
  REDACT-03  test_redacts_openai_generic
  REDACT-04  test_redacts_opaque_refresh_by_key
  REDACT-05  test_redacts_google_ya29
  REDACT-06  test_redacts_google_refresh_1slash
  REDACT-07  test_redacts_github_copilot
  REDACT-08  test_redacts_opaque_antigravity_refresh
  REDACT-09  test_redacts_bearer_header_variants
  REDACT-10  test_redacts_authorization_header_dict
  REDACT-11  test_redacts_nested_dict_secret
  REDACT-12  test_redacts_list_value
  REDACT-13  test_redacts_stdlib_httpx_record
  REDACT-14  test_redacts_stdlib_litellm_record
  REDACT-15  test_redacts_exception_message
  REDACT-16  test_redacts_traceback_chain
  REDACT-17  test_jsonrenderer_output_clean
  REDACT-18  test_processor_at_position_zero
  REDACT-19  test_processorformatter_attached_to_root
  REDACT-20  test_selfcheck_passes_when_installed
  REDACT-21  test_selfcheck_fails_when_not_installed
  REDACT-22  test_negative_no_overredaction
  REDACT-23  test_install_idempotent
  REDACT-24  test_hypothesis_secrets_never_survive
  REDACT-25  → tests/test_observability_import_graph.py
  REDACT-26  test_existing_auth_log_calls_still_render

  Structural extras (cover REDACT-23 sub-row + public surface):
    test_pattern_set_compiled_at_import
    test_iter_token_patterns_returns_tuple
"""
from __future__ import annotations

import logging
import re
from typing import Any

import pytest
import structlog
from hypothesis import given, settings, strategies as st
from structlog.testing import capture_logs

# The next imports WILL FAIL in Wave 1. That is the RED signal.
from state_core.observability.redactor import (  # Plan 02 + Plan 03
    REDACTED,
    RedactorNotAttached,
    _PATTERNS,
    _SECRET_KEYS,
    _redact_string,
    _walk_value,
    assert_redactor_attached,
    install,
    iter_token_patterns,
    redact_processor,
)


# ── Canary token literals (test-only; chosen to be NEVER produced by any real provider) ──
# Every canary either contains the literal "TEST-CANARY-" substring OR is
# documented with a "TEST-CANARY-marker" comment so a regression that leaks
# one substring is greppable by a single literal search across this file.
# Some shape regexes require alnum-only bodies (e.g. `sk-[A-Za-z0-9]{40,}`,
# `gho_[A-Za-z0-9]{20,}`); for those we use "TESTCANARY" in the value and
# keep the "TEST-CANARY-" greppable substring in the per-line comment.
_CANARY_ANTHROPIC_OAT = "sk-ant-oat-TEST-CANARY-" + "X" * 32
_CANARY_ANTHROPIC_API = "sk-ant-api03-TEST-CANARY-" + "X" * 32
_CANARY_OPENAI_GENERIC = "sk-" + "TESTCANARY" + "Y" * 50  # TEST-CANARY-marker; ≥40 alnum after "sk-"
_CANARY_OPENROUTER = "sk-or-v1-TEST-CANARY-" + "Z" * 32
_CANARY_GOOGLE_ACCESS = "ya29.TEST-CANARY-" + "A" * 32
_CANARY_GOOGLE_REFRESH = "1//TEST-CANARY-" + "B" * 32
_CANARY_GHO = "gho_" + "TESTCANARY" + "C" * 32  # TEST-CANARY-marker (alnum-only body)
_CANARY_GHU = "ghu_" + "TESTCANARY" + "D" * 32  # TEST-CANARY-marker (alnum-only body)
_CANARY_GHS = "ghs_" + "TESTCANARY" + "E" * 32  # TEST-CANARY-marker (alnum-only body)
_CANARY_GHP = "ghp_" + "TESTCANARY" + "F" * 32  # TEST-CANARY-marker (alnum-only body)
_CANARY_GROQ = "gsk_" + "TESTCANARY" + "G" * 32  # TEST-CANARY-marker (alnum-only body)
_CANARY_XAI = "xai-" + "TESTCANARY" + "H" * 32  # TEST-CANARY-marker (alnum-only body)
_CANARY_DEEPSEEK = "esecret_" + "TESTCANARY" + "I" * 32  # TEST-CANARY-marker (alnum-only body)
_CANARY_BEARER_VALUE = "TESTCANARY" + "J" * 40  # TEST-CANARY-marker; alone — NOT prefixed
_CANARY_OPAQUE_REFRESH = "opaque-TEST-CANARY-no-prefix-" + "K" * 40  # tests REDACT-04 / REDACT-08

# Strings that must NEVER be redacted (REDACT-22):
_NEGATIVES = (
    "sk-foundation",            # product name, no length
    "sk-2",                     # too short (< 20)
    "Bearer xyz",               # prefix but value < 20
    "Skill-1234",               # similar shape, not a token
    "sk-learn",                 # mistype / package name
)


@pytest.fixture(autouse=True)
def _isolate_structlog_for_redactor_tests() -> Any:
    """Snapshot + reset structlog config AND root logger handlers;
    restore on teardown.

    Mirrors tests/auth/conftest.py::_isolate_structlog_for_auth_tests
    but ALSO snapshots/restores stdlib root-logger handlers (added by
    Plan 03's `install()` ProcessorFormatter wiring) and the redactor's
    module-level `_INSTALLED` idempotency guard (so each test that
    relies on the `installed_redactor` fixture gets a clean install).
    Required for `capture_logs()` to behave deterministically across
    the redactor's `install()` calls (which mutate global structlog
    state AND stdlib root logger state).
    """
    import state_core.observability.redactor as _redactor_mod

    saved_struct = structlog.get_config()
    saved_root_handlers = list(logging.getLogger().handlers)
    saved_root_level = logging.getLogger().level
    saved_installed_flag = _redactor_mod._INSTALLED

    structlog.reset_defaults()
    # Reset _INSTALLED so the next install() in this test actually runs.
    _redactor_mod._INSTALLED = False
    # Clear any handlers a previous test's install() left on the root.
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    yield

    # Restore on teardown.
    structlog.configure(**saved_struct)
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in saved_root_handlers:
        root.addHandler(h)
    root.setLevel(saved_root_level)
    _redactor_mod._INSTALLED = saved_installed_flag


@pytest.fixture
def installed_redactor() -> Any:
    """Call install() once and yield. Used by REDACT-13..21 + REDACT-23."""
    install()
    yield
    # No explicit teardown; _isolate_structlog_for_redactor_tests resets defaults.


# ── REDACT-01 ──────────────────────────────────────────────────────────


def test_redacts_anthropic_oat() -> None:
    """REDACT-01 — Anthropic OAuth access token (`sk-ant-oat-…`) redacted in event_dict value."""
    event_dict = {"event": "auth refresh", "token": _CANARY_ANTHROPIC_OAT}
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_ANTHROPIC_OAT not in str(out), (
        f"sk-ant-oat canary leaked: {out!r}"
    )
    assert REDACTED in str(out), f"no [REDACTED] marker in {out!r}"


# ── REDACT-02 ──────────────────────────────────────────────────────────


def test_redacts_anthropic_api_key() -> None:
    """REDACT-02 — Anthropic API key (`sk-ant-api03-…`) redacted."""
    event_dict = {"event": "request", "api_key": _CANARY_ANTHROPIC_API}
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_ANTHROPIC_API not in str(out), (
        f"sk-ant-api03 canary leaked: {out!r}"
    )
    assert REDACTED in str(out), f"no [REDACTED] marker in {out!r}"


# ── REDACT-03 ──────────────────────────────────────────────────────────


def test_redacts_openai_generic() -> None:
    """REDACT-03 — Generic OpenAI key (`sk-` ≥ 40 chars) redacted via shape match.

    Note: the key `"auth"` is NOT in `_SECRET_KEYS` — this forces the shape-match
    path rather than the key-context path.
    """
    event_dict = {"event": "request", "auth": _CANARY_OPENAI_GENERIC}
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_OPENAI_GENERIC not in str(out), (
        f"OpenAI-generic canary leaked: {out!r}"
    )


# ── REDACT-04 ──────────────────────────────────────────────────────────


def test_redacts_opaque_refresh_by_key() -> None:
    """REDACT-04 — Anthropic OAuth refresh (opaque, no prefix) redacted via `refresh_token` key-context."""
    event_dict = {"refresh_token": _CANARY_OPAQUE_REFRESH}
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_OPAQUE_REFRESH not in str(out), (
        f"opaque refresh canary leaked: {out!r}"
    )


# ── REDACT-05 ──────────────────────────────────────────────────────────


def test_redacts_google_ya29() -> None:
    """REDACT-05 — Google OAuth access (`ya29.…`) redacted."""
    event_dict = {"event": "google_auth", "value": _CANARY_GOOGLE_ACCESS}
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_GOOGLE_ACCESS not in str(out), (
        f"ya29 canary leaked: {out!r}"
    )


# ── REDACT-06 ──────────────────────────────────────────────────────────


def test_redacts_google_refresh_1slash() -> None:
    """REDACT-06 — Google OAuth refresh (`1//…`) redacted via shape match.

    Key is `"raw"` (NOT in `_SECRET_KEYS`) — forces shape-match path.
    """
    event_dict = {"event": "google_refresh", "raw": _CANARY_GOOGLE_REFRESH}
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_GOOGLE_REFRESH not in str(out), (
        f"1// canary leaked: {out!r}"
    )


# ── REDACT-07 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "canary",
    [_CANARY_GHO, _CANARY_GHU, _CANARY_GHS, _CANARY_GHP],
)
def test_redacts_github_copilot(canary: str) -> None:
    """REDACT-07 — GitHub Copilot device-code token (`gho_/ghu_/ghs_/ghp_`) redacted."""
    event_dict = {"event": "copilot_auth", "value": canary}
    out = redact_processor(None, "info", event_dict)
    assert canary not in str(out), f"GitHub canary leaked: {out!r}"
    assert REDACTED in str(out), f"no [REDACTED] marker in {out!r}"


# ── REDACT-08 ──────────────────────────────────────────────────────────


def test_redacts_opaque_antigravity_refresh() -> None:
    """REDACT-08 — Antigravity / Copilot opaque refresh redacted via `access` key-context."""
    event_dict = {"access": _CANARY_OPAQUE_REFRESH}
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_OPAQUE_REFRESH not in str(out), (
        f"antigravity opaque canary leaked: {out!r}"
    )


# ── REDACT-09 ──────────────────────────────────────────────────────────


def test_redacts_bearer_header_variants() -> None:
    """REDACT-09 — Bearer header (`Bearer sk-ant-oat-…`) redacted including double-space variant."""
    payload_single = f"Bearer {_CANARY_ANTHROPIC_OAT}"
    payload_double = f"Bearer  {_CANARY_ANTHROPIC_OAT}"  # two spaces
    for payload in (payload_single, payload_double):
        event_dict = {"event": "http_call", "auth_header": payload}
        out = redact_processor(None, "info", event_dict)
        assert _CANARY_ANTHROPIC_OAT not in str(out), (
            f"Bearer variant leaked canary: {out!r} (payload={payload!r})"
        )


# ── REDACT-10 ──────────────────────────────────────────────────────────


def test_redacts_authorization_header_dict() -> None:
    """REDACT-10 — HTTP-header dict with `Authorization` key redacted via key-context (case-insensitive)."""
    event_dict = {
        "headers": {"Authorization": f"Bearer {_CANARY_ANTHROPIC_OAT}"},
    }
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_ANTHROPIC_OAT not in str(out), (
        f"Authorization-header canary leaked: {out!r}"
    )


# ── REDACT-11 ──────────────────────────────────────────────────────────


def test_redacts_nested_dict_secret() -> None:
    """REDACT-11 — Nested-dict secret (token inside `request.headers.x-api-key`) redacted."""
    event_dict = {
        "request": {
            "method": "POST",
            "headers": {"x-api-key": _CANARY_ANTHROPIC_API},
        },
    }
    out = redact_processor(None, "info", event_dict)
    assert _CANARY_ANTHROPIC_API not in str(out), (
        f"nested x-api-key canary leaked: {out!r}"
    )


# ── REDACT-12 ──────────────────────────────────────────────────────────


def test_redacts_list_value() -> None:
    """REDACT-12 — Secrets in `list` value all redacted."""
    event_dict = {
        "event": "tokens_seen",
        "tokens": [
            _CANARY_ANTHROPIC_OAT,
            _CANARY_OPENAI_GENERIC,
            _CANARY_GROQ,
        ],
    }
    out = redact_processor(None, "info", event_dict)
    rendered = str(out)
    for canary in (_CANARY_ANTHROPIC_OAT, _CANARY_OPENAI_GENERIC, _CANARY_GROQ):
        assert canary not in rendered, (
            f"list-value canary leaked: {canary!r} survived in {rendered!r}"
        )


# ── REDACT-13 ──────────────────────────────────────────────────────────


def test_redacts_stdlib_httpx_record(installed_redactor: Any) -> None:
    """REDACT-13 — Secret in stdlib `httpx`-style record redacted via ProcessorFormatter foreign_pre_chain.

    Wave 3 capture-point adjustment (per plan Wave 1 caveat): we
    render a synthetic LogRecord through the ProcessorFormatter
    that install() attached to the root logger, and assert the
    rendered output does not contain the canary. caplog captures
    raw LogRecords BEFORE the formatter runs and is therefore not
    a valid sink for verifying foreign_pre_chain redaction.
    """
    import structlog as _sl

    httpx_logger_name = "httpx"
    rec = logging.LogRecord(
        name=httpx_logger_name,
        level=logging.DEBUG,
        pathname=__file__,
        lineno=0,
        msg="request: POST https://api.anthropic.com headers=%s",
        args=({"Authorization": f"Bearer {_CANARY_ANTHROPIC_OAT}"},),
        exc_info=None,
    )
    root = logging.getLogger()
    rendered_outputs: list[str] = []
    for handler in root.handlers:
        fmt = handler.formatter
        if not isinstance(fmt, _sl.stdlib.ProcessorFormatter):
            continue
        rendered_outputs.append(fmt.format(rec))
    assert rendered_outputs, "no ProcessorFormatter attached to root after install()"
    for output in rendered_outputs:
        assert _CANARY_ANTHROPIC_OAT not in output, (
            f"Bearer leaked through stdlib httpx record: {output!r}"
        )


# ── REDACT-14 ──────────────────────────────────────────────────────────


def test_redacts_stdlib_litellm_record(installed_redactor: Any) -> None:
    """REDACT-14 — Secret in stdlib `litellm`-style record redacted.

    Wave 3 capture-point adjustment (same as REDACT-13): synthesize
    a LogRecord and run it through the install()-attached
    ProcessorFormatter directly.
    """
    import structlog as _sl

    rec = logging.LogRecord(
        name="LiteLLM",
        level=logging.DEBUG,
        pathname=__file__,
        lineno=0,
        msg="payload: %s",
        args=({"api_key": _CANARY_OPENAI_GENERIC},),
        exc_info=None,
    )
    root = logging.getLogger()
    rendered_outputs: list[str] = []
    for handler in root.handlers:
        fmt = handler.formatter
        if not isinstance(fmt, _sl.stdlib.ProcessorFormatter):
            continue
        rendered_outputs.append(fmt.format(rec))
    assert rendered_outputs, "no ProcessorFormatter attached to root after install()"
    for output in rendered_outputs:
        assert _CANARY_OPENAI_GENERIC not in output, (
            f"OpenAI-generic canary leaked through stdlib LiteLLM record: {output!r}"
        )


# ── REDACT-15 ──────────────────────────────────────────────────────────


def test_redacts_exception_message() -> None:
    """REDACT-15 — Secret in raised exception's `str()` redacted."""
    exc = RuntimeError(f"bad token {_CANARY_ANTHROPIC_OAT}")
    event_dict = {"event": "error", "exception": exc}
    out = redact_processor(None, "error", event_dict)
    assert _CANARY_ANTHROPIC_OAT not in str(out), (
        f"exception canary leaked: {out!r}"
    )


# ── REDACT-15 extension (MF-01 regression) ────────────────────────────


def test_redacts_multi_arg_exception() -> None:
    """REDACT-15 extension / MF-01 — token in multi-arg exception is redacted.

    Covers httpx.HTTPStatusError-shaped exceptions whose ``__init__``
    requires kwargs/positional args beyond a single message string.
    Before MF-01 was fixed, ``_walk_value``'s ``except TypeError``
    branch returned the **live** exception object, leaking token
    bytes through downstream ``str(exc)`` / ``format_exc_info``
    renderers (T-020-4 / RESEARCH §Pitfall 5).

    Post-fix invariant: the canary MUST NOT survive in the rendered
    output for ANY exception class, regardless of __init__ shape.
    """

    class MultiArgExc(Exception):
        """Stand-in for httpx.HTTPStatusError / subprocess.CalledProcessError."""

        def __init__(self, request: str, response: str) -> None:
            self.request = request
            self.response = response
            super().__init__(f"request to {request} failed: {response}")

    exc = MultiArgExc("https://api/", f"bad token {_CANARY_ANTHROPIC_OAT}")
    event_dict = {"event": "error", "exception": exc}
    out = redact_processor(None, "error", event_dict)
    assert _CANARY_ANTHROPIC_OAT not in str(out), (
        f"multi-arg exception leaked canary: {out!r}"
    )
    # Also assert that the str() of the resulting walked value is redacted —
    # downstream renderers (format_exc_info) will call str() on event_dict["exception"].
    walked = out["exception"]
    assert _CANARY_ANTHROPIC_OAT not in str(walked), (
        f"walked exception str() leaked canary: {str(walked)!r}"
    )
    assert REDACTED in str(walked), (
        f"no [REDACTED] marker in walked exception str(): {str(walked)!r}"
    )


# ── REDACT-16 ──────────────────────────────────────────────────────────


def test_redacts_traceback_chain(installed_redactor: Any) -> None:
    """REDACT-16 — Secret in exception traceback chain (`exc_info=True` path) redacted."""
    log = structlog.get_logger("test.traceback")
    with capture_logs() as cap:
        try:
            raise ValueError(f"oops {_CANARY_ANTHROPIC_OAT}")
        except ValueError:
            log.exception("caught")
    rendered = "\n".join(str(r) for r in cap)
    assert _CANARY_ANTHROPIC_OAT not in rendered, (
        f"traceback canary leaked: {rendered!r}"
    )


# ── REDACT-17 ──────────────────────────────────────────────────────────


def test_jsonrenderer_output_clean(installed_redactor: Any) -> None:
    """REDACT-17 — Final JSONRenderer output does not match any token-shape regex (belt-and-braces).

    Wave 3 capture-point: emit a structlog event, capture the actual
    final-stage JSON-rendered output by writing through the
    install()-attached StreamHandler (whose formatter is the
    ProcessorFormatter with JSONRenderer at the tail). capture_logs()
    is unsuitable here because it clears configured processors and
    bypasses the renderer entirely.
    """
    import io
    import structlog as _sl

    # Replace the install()-attached handler's stream with an in-memory
    # buffer for the duration of this test, so we can read back the
    # finally-rendered output without touching real stderr.
    root = logging.getLogger()
    target_handler = None
    for h in root.handlers:
        if isinstance(h.formatter, _sl.stdlib.ProcessorFormatter):
            target_handler = h
            break
    assert target_handler is not None, "install()-attached ProcessorFormatter handler missing"

    buf = io.StringIO()
    saved_stream = getattr(target_handler, "stream", None)
    target_handler.setStream(buf) if hasattr(target_handler, "setStream") else setattr(target_handler, "stream", buf)
    try:
        log = structlog.get_logger("test.json")
        log.info(
            "summary",
            a=_CANARY_ANTHROPIC_OAT,
            b=_CANARY_GOOGLE_ACCESS,
            c=_CANARY_BEARER_VALUE,
            d=_CANARY_GHO,
        )
    finally:
        if saved_stream is not None:
            target_handler.setStream(saved_stream) if hasattr(target_handler, "setStream") else setattr(target_handler, "stream", saved_stream)
    rendered = buf.getvalue()
    for pat in iter_token_patterns():
        assert not pat.search(rendered), (
            f"Pattern {pat.pattern!r} matched in rendered output: {rendered!r}"
        )


# ── REDACT-18 ──────────────────────────────────────────────────────────


def test_processor_at_position_zero(installed_redactor: Any) -> None:
    """REDACT-18 — `redact_processor` is at position 0 in `structlog.get_config()['processors']`."""
    cfg = structlog.get_config()
    processors = cfg["processors"]
    assert processors, "structlog has no processors after install()"
    assert processors[0] is redact_processor, (
        f"redact_processor not at position 0; chain is {processors!r}"
    )


# ── REDACT-19 ──────────────────────────────────────────────────────────


def test_processorformatter_attached_to_root(installed_redactor: Any) -> None:
    """REDACT-19 — `ProcessorFormatter` attached to stdlib root with `redact_processor` in foreign_pre_chain."""
    root = logging.getLogger()
    formatters = [h.formatter for h in root.handlers if h.formatter is not None]
    attached = False
    for fmt in formatters:
        chain = getattr(fmt, "foreign_pre_chain", None) or ()
        if redact_processor in chain:
            attached = True
            break
    assert attached, "redact_processor not in any root handler's foreign_pre_chain"


# ── REDACT-20 ──────────────────────────────────────────────────────────


def test_selfcheck_passes_when_installed(installed_redactor: Any) -> None:
    """REDACT-20 — `assert_redactor_attached()` returns successfully after install()."""
    try:
        result = assert_redactor_attached()
    except Exception as exc:  # pragma: no cover - failure path documented
        pytest.fail(
            f"assert_redactor_attached() raised {type(exc).__name__}: {exc!r} "
            "(expected: returns None)"
        )
    assert result is None, (
        f"assert_redactor_attached() returned {result!r}; expected None"
    )


# ── REDACT-21 ──────────────────────────────────────────────────────────


def test_selfcheck_fails_when_not_installed() -> None:
    """REDACT-21 — `assert_redactor_attached()` raises `RedactorNotAttached` when install() has NOT run."""
    # The autouse fixture already reset_defaults(); ensure no chain present.
    structlog.reset_defaults()
    with pytest.raises(RedactorNotAttached):
        assert_redactor_attached()


# ── REDACT-22 ──────────────────────────────────────────────────────────


def test_negative_no_overredaction() -> None:
    """REDACT-22 — Negative test: short / non-token strings are NOT redacted."""
    for negative in _NEGATIVES:
        event_dict = {"event": "diagnostic", "name": negative}
        out = redact_processor(None, "info", event_dict)
        assert negative in str(out), (
            f"redactor over-matched on {negative!r}: out={out!r}"
        )
        assert REDACTED not in str(out), (
            f"redactor produced [REDACTED] for non-secret {negative!r}: out={out!r}"
        )


# ── REDACT-23 ──────────────────────────────────────────────────────────


def test_install_idempotent() -> None:
    """REDACT-23 — `install()` is idempotent — calling it twice does not duplicate handlers/processors."""
    install()
    cfg_before = structlog.get_config()
    procs_before = list(cfg_before["processors"])
    root_handlers_before = len(logging.getLogger().handlers)
    install()
    cfg_after = structlog.get_config()
    procs_after = list(cfg_after["processors"])
    root_handlers_after = len(logging.getLogger().handlers)
    assert procs_before == procs_after, (
        f"processor chain changed after second install(): "
        f"before={procs_before!r}, after={procs_after!r}"
    )
    assert root_handlers_before == root_handlers_after, (
        f"root handler count changed: "
        f"before={root_handlers_before}, after={root_handlers_after}"
    )
    assert procs_after.count(redact_processor) == 1, (
        f"redact_processor appears {procs_after.count(redact_processor)} times in chain; "
        f"expected exactly 1"
    )


# ── REDACT-23 extension (SF-03 regression) ────────────────────────────


def test_install_self_heals_under_installed_reset() -> None:
    """SF-03 — install() is idempotent even when _INSTALLED is reset externally.

    Test fixtures, importlib.reload(), or a future hot-reload path can
    reset `_INSTALLED` to False between install() calls. Before SF-03,
    that path would add a SECOND ProcessorFormatter handler to the root
    logger, doubling output. Post-fix, install() detects an existing
    redactor-bearing ProcessorFormatter handler and skips re-attachment.
    """
    import state_core.observability.redactor as _redactor_mod

    install()
    handlers_after_first = len(logging.getLogger().handlers)

    # Simulate a reload / fixture-induced reset.
    _redactor_mod._INSTALLED = False
    install()
    handlers_after_second = len(logging.getLogger().handlers)

    assert handlers_after_first == handlers_after_second, (
        f"install() added a duplicate handler under _INSTALLED reset: "
        f"first={handlers_after_first}, second={handlers_after_second}"
    )

    # Verify exactly one ProcessorFormatter with redact_processor remains.
    matching = [
        h for h in logging.getLogger().handlers
        if isinstance(h.formatter, structlog.stdlib.ProcessorFormatter)
        and redact_processor in (getattr(h.formatter, "foreign_pre_chain", ()) or ())
    ]
    assert len(matching) == 1, (
        f"expected exactly 1 redactor-bearing ProcessorFormatter handler, "
        f"got {len(matching)}: {matching!r}"
    )


# ── REDACT-24 ──────────────────────────────────────────────────────────


# Prefix → body alphabet mapping per RESEARCH §1's regex bodies. Some
# shapes admit `_` and `-` in the body (Anthropic / Google / OpenRouter),
# others restrict to alnum only (GitHub Copilot, Groq, xAI, DeepSeek,
# OpenAI generic). Per-prefix bodies keep the property check faithful to
# what the regex set actually accepts post-SF-01.
_ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
_ALNUM_UNDERSCORE_DASH = _ALNUM + "_-"
_PREFIX_BODY_ALPHABET: dict[str, str] = {
    # Anthropic / Google / OpenRouter — body admits _-
    "sk-ant-oat-": _ALNUM_UNDERSCORE_DASH,
    "sk-ant-api03-": _ALNUM_UNDERSCORE_DASH,
    "sk-or-v1-": _ALNUM_UNDERSCORE_DASH,
    "ya29.": _ALNUM_UNDERSCORE_DASH,
    "1//": _ALNUM_UNDERSCORE_DASH,
    # Alnum-only bodies per RESEARCH §1.
    "gho_": _ALNUM,
    "ghu_": _ALNUM,
    "ghs_": _ALNUM,
    "ghp_": _ALNUM,
    "gsk_": _ALNUM,
    "xai-": _ALNUM,
    "esecret_": _ALNUM,
}


@settings(max_examples=1000, deadline=None)
@given(
    prefix=st.sampled_from(list(_PREFIX_BODY_ALPHABET.keys())),
    # Body length window covers both the minimum-floor edge case (20)
    # and large drafts (200) — exercises overlapping-pattern behavior
    # across the 12 shapes.
    body_len=st.integers(min_value=20, max_value=200),
    body_seed=st.text(
        alphabet=st.characters(
            whitelist_categories=(),
            whitelist_characters=_ALNUM_UNDERSCORE_DASH,
        ),
        min_size=20,
        max_size=200,
    ),
    # Surround alphabet excludes `\w` characters and `-` so the
    # generated surround can never form a token-extending boundary
    # — keeps the property check sharp on the redactor (not on the
    # interaction between surround + token shape).
    surround=st.text(
        alphabet=st.characters(
            whitelist_categories=(),
            whitelist_characters=" .,!?:;()[]{}<>\"'\\/|=+*&^%$#@~`\n\t",
        ),
        min_size=0,
        max_size=20,
    ),
)
def test_hypothesis_secrets_never_survive(
    prefix: str, body_len: int, body_seed: str, surround: str
) -> None:
    """REDACT-24 — Hypothesis property: any secret-shaped string is redacted.

    SF-01 fix: alphabet widened to RESEARCH §1's `[A-Za-z0-9_-]` for
    prefixes that admit underscores/hyphens (Anthropic / Google /
    OpenRouter); kept alnum-only for prefixes whose regex body is
    alnum-only (GitHub / Groq / xAI / DeepSeek / OpenAI generic).
    max_examples bumped to 1000 to satisfy the Plan 04 phase-gate
    target. Boundary anchors `(?<!\\w)` / `(?!\\w)` on the 11 prefix
    patterns guarantee no over-redaction at word boundaries.
    """
    # Project body_seed onto the per-prefix alphabet by character mapping.
    # Keeps shrinking determinism while honoring per-prefix constraints.
    allowed = _PREFIX_BODY_ALPHABET[prefix]
    projected = "".join(c if c in allowed else allowed[ord(c) % len(allowed)] for c in body_seed)
    body = projected[:body_len].ljust(body_len, allowed[0])
    secret = prefix + body
    blob = f"{surround}{secret}{surround}"
    out = _redact_string(blob)
    assert secret not in out, (
        f"redactor missed: {secret!r} survived as {out!r}"
    )
    assert REDACTED in out, f"no [REDACTED] marker in {out!r}"


# ── REDACT-26 ──────────────────────────────────────────────────────────


def test_existing_auth_log_calls_still_render(installed_redactor: Any) -> None:
    """REDACT-26 — Regression: existing auth-style log calls still render correctly after install()."""
    log = structlog.get_logger("state_core.auth.refresh")
    with capture_logs() as cap:
        log.info("refresh.completed", provider_id="anthropic", expires=1.5)
    # The captured event should have the public keys preserved
    # and no redaction (no secret-shaped values present).
    assert any(rec.get("event") == "refresh.completed" for rec in cap), (
        f"refresh.completed event missing from capture: {cap!r}"
    )
    assert any(rec.get("provider_id") == "anthropic" for rec in cap), (
        f"provider_id missing from capture: {cap!r}"
    )


# ── Structural extras ──────────────────────────────────────────────────


def test_pattern_set_compiled_at_import() -> None:
    """REDACT-23-substructure — `_PATTERNS` is a tuple of compiled re.Pattern objects (not lazy)."""
    assert isinstance(_PATTERNS, tuple), (
        f"_PATTERNS is {type(_PATTERNS).__name__}, expected tuple"
    )
    assert len(_PATTERNS) >= 12, (
        f"_PATTERNS has {len(_PATTERNS)} entries; expected >= 12 (one per token shape family)"
    )
    for pat in _PATTERNS:
        assert isinstance(pat, re.Pattern), (
            f"Not compiled: {pat!r} (type={type(pat).__name__})"
        )


def test_iter_token_patterns_returns_tuple() -> None:
    """REDACT-public-surface — `iter_token_patterns()` returns a tuple of compiled patterns."""
    patterns = iter_token_patterns()
    assert isinstance(patterns, tuple), (
        f"iter_token_patterns() returned {type(patterns).__name__}, expected tuple"
    )
    assert all(isinstance(p, re.Pattern) for p in patterns), (
        f"iter_token_patterns() includes non-Pattern entries: {patterns!r}"
    )
    assert len(patterns) >= 12, (
        f"iter_token_patterns() returned {len(patterns)} entries; expected >= 12"
    )


# ── Sanity check on _SECRET_KEYS / _walk_value access ───────────────────
# (These references silence "unused import" complaints and re-document
# the public surface that Plan 02 must ship.)


def test_walk_value_and_secret_keys_imported() -> None:
    """Public-surface smoke: `_walk_value` callable and `_SECRET_KEYS` populated."""
    assert callable(_walk_value), f"_walk_value not callable: {_walk_value!r}"
    assert isinstance(_SECRET_KEYS, frozenset), (
        f"_SECRET_KEYS is {type(_SECRET_KEYS).__name__}, expected frozenset"
    )
    # Spot-check known keys (RESEARCH §1):
    for k in ("token", "api_key", "authorization", "refresh_token", "access_token"):
        assert k in _SECRET_KEYS, (
            f"{k!r} missing from _SECRET_KEYS={_SECRET_KEYS!r}"
        )
