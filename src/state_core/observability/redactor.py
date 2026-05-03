"""Root-logger token redactor — Phase 020 / AUTH-10 / P0-14 layer 2.

Compiled regex set + recursive value walker + structlog processor
callable. The processor at position 0 of the structlog chain
(after Plan 03's install()) walks every value in every event_dict
and substitutes secret-shaped substrings with [REDACTED].

Cardinal rules (per PROJECT.md / CLAUDE.md):

  1. Mode isolation — imports limited to stdlib (re, typing). NO
     state_build.*, state_teach.*, state.build.*, state.teach.*.
     Enforced by tests/test_observability_import_graph.py.

  2. Determinism — _PATTERNS compiled at module-import time. NO
     per-call re.compile. NO datetime.now() / random.* reads.

  3. Length-uniform replacement — substitution literal is "[REDACTED]"
     (10 chars). Length-preserving placeholders are REJECTED per
     RESEARCH §Anti-Patterns: token length is itself a side-channel
     ("redacted token has 56 chars → it's an `sk-ant-oat-…`").

  4. Defense-in-depth: layer 2. Per-call-site secret-slicing in
     auth providers (Phases 011-019) is layer 1; this module is
     the root-logger safety net. Both required.

  5. Circular-reference policy: _walk_value detects cycles via an
     id()-keyed visited set and substitutes `[CYCLE]` sentinel.
     WK-01 (Phase 022.3) closed the deferral — see 020-REVIEW.md
     §WK-01 for the reviewer's prescription.

Token shape provenance (every regex traceable to a source):
  * sk-ant-oat-       → .state-inputs/claude-oauth.md (Anthropic OAuth access)
  * sk-ant-api03-     → src/state_core/auth/providers/api_key.py::_REGISTRY (Phase 018)
  * sk-or-v1-         → src/state_core/auth/providers/api_key.py::_REGISTRY (OpenRouter)
  * sk-…              → OpenAI generic; ≥40 chars to dodge "sk-2" false positives
  * ya29.…            → src/state_core/auth/providers/google_gemini.py:456 (Google access)
  * 1//…              → src/state_core/auth/providers/google_gemini.py:456 (Google refresh)
  * gho_/ghu_/ghs_/ghp_ → upstream GitHub token-prefix announcement (2021)
  * gsk_              → Groq (Phase 018 _REGISTRY)
  * xai-              → xAI / Grok (Phase 018 _REGISTRY)
  * esecret_          → DeepSeek (Phase 018 _REGISTRY)
  * Bearer …          → RFC 6750 §2.1

See .planning/milestones/v2/phases/020-root-logger-token-redactor/
020-RESEARCH.md for the full rationale, 8 pitfalls, and 8 threat
rows.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any

import structlog

# ── Compile-at-import regex set (RESEARCH §Code Examples §1) ──────────
# Token shapes — anchored with  and  so we don't match inside
# identifiers or product names. Minimum length 20 chars on the value to
# dodge false positives like "sk-2" (RESEARCH §Pitfall 6).
#
# Pattern order matters: more-specific shapes (sk-ant-oat-, sk-ant-api03-,
# sk-or-v1-, sk-(proj|svcacct|None)-) BEFORE generic `sk-...{40,}` so the
# generic doesn't consume bytes a specific would have caught. Bearer is
# LAST so it doesn't shadow internal-prefix matches inside the value.
_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Anthropic OAuth access tokens.
    re.compile(r"(?<!\w)sk-ant-oat-[A-Za-z0-9_-]{20,}(?!\w)"),
    # Anthropic API keys (Claude API).
    re.compile(r"(?<!\w)sk-ant-api03-[A-Za-z0-9_-]{20,}(?!\w)"),
    # OpenRouter prefixed keys.
    re.compile(r"(?<!\w)sk-or-v1-[A-Za-z0-9_-]{20,}(?!\w)"),
    # OpenAI prefixed (proj/svcacct/None).
    re.compile(r"(?<!\w)sk-(?:proj|svcacct|None)-[A-Za-z0-9_-]{20,}(?!\w)"),
    # OpenAI generic ≥40 alnum (covers older 48-char keys + project keys).
    re.compile(r"(?<!\w)sk-[A-Za-z0-9]{40,}(?!\w)"),
    # Google OAuth access tokens.
    re.compile(r"(?<!\w)ya29\.[A-Za-z0-9_-]{20,}(?!\w)"),
    # Google OAuth refresh tokens.
    re.compile(r"(?<!\w)1//[A-Za-z0-9_-]{20,}(?!\w)"),
    # GitHub Copilot device-code tokens.
    re.compile(r"(?<!\w)(?:gho|ghu|ghs|ghp)_[A-Za-z0-9]{20,}(?!\w)"),
    # Groq plain API keys.
    re.compile(r"(?<!\w)gsk_[A-Za-z0-9]{20,}(?!\w)"),
    # xAI / Grok plain API keys.
    re.compile(r"(?<!\w)xai-[A-Za-z0-9]{20,}(?!\w)"),
    # DeepSeek plain API keys.
    re.compile(r"(?<!\w)esecret_[A-Za-z0-9]{20,}(?!\w)"),
    # RFC 6750 Bearer header values (one-or-more whitespace tolerance).
    # NOTE: no word-boundary anchor here — "Bearer" embedded inside a
    # word is implausible, and \s+ already provides a left boundary.
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._\-/+=]{20,}"),
)

# Keys whose VALUES are always secrets regardless of shape — covers
# opaque refresh tokens, Antigravity / Copilot opaque variants, and
# future shapes we haven't enumerated yet (RESEARCH §Pitfall 3).
# Lookups are LOWERCASED — see _walk_value's `key.lower() in _SECRET_KEYS`.
_SECRET_KEYS: frozenset[str] = frozenset({
    "access",
    "access_token",
    "refresh",
    "refresh_token",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "x-api-key",
    "x-goog-api-key",
    "client_secret",
    "code_verifier",
})

REDACTED: str = "[REDACTED]"
"""Replacement literal. Length-uniform; greppable; non-secret."""

CYCLE_SENTINEL: str = "[CYCLE]"
"""Cycle-detection sentinel emitted by _walk_value when a container
is encountered a second time on a single walk. WK-01 / Phase 022.3.
Length-uniform (7 chars), greppable, non-secret."""


def _redact_string(s: str) -> str:
    """Apply every pattern in _PATTERNS to *s*; replace each match with REDACTED.

    Pure function. Order of patterns is intentional: more-specific shapes
    (sk-ant-oat-, sk-ant-api03-, sk-or-v1-, sk-(proj|svcacct|None)-) run
    BEFORE the generic `sk-...{40,}` pattern so the generic doesn't
    consume bytes that a specific would have caught.
    """
    for pat in _PATTERNS:
        s = pat.sub(REDACTED, s)
    return s


def _walk_value(
    v: Any,
    key_hint: str | None = None,
    visited: set[int] | None = None,
) -> Any:
    """Recursive type-dispatch redactor — the redaction kernel.

    Args:
        v: The value to walk. Type-dispatched: str / dict / list / tuple
            / BaseException / arbitrary-passthrough.
        key_hint: When *v* lives under a dict key whose lowercased name
            is in _SECRET_KEYS, redact the WHOLE value regardless of
            shape (covers opaque refresh tokens — RESEARCH §Pitfall 3).
            None when called at the top of a call chain (e.g., a list
            element's first walk).
        visited: id()-keyed set of containers already encountered on
            this walk. Threaded through every recursive call inside
            container branches so a self-referencing dict / list /
            tuple produces `CYCLE_SENTINEL` instead of RecursionError.
            Containers only — strings, ints, etc. cannot self-reference
            and need not pay the visited-check cost. WK-01 / 022.3.

    Returns:
        A NEW structure with secrets replaced. Strings: regex-substituted.
        Dicts: every value walked, every dict-key passed as key_hint to
        recursive calls. Lists / tuples: every element walked (no
        key_hint propagation through index access). BaseException: a
        new instance of the same exception class with `_redact_string(str(v))`
        as the message — DOES NOT mutate the live exception object.
        Cyclic containers: `CYCLE_SENTINEL` literal on the second visit.
        Other types: returned as-is (no walk; caller handles repr if
        stringification matters).

    Empty / None values under a _SECRET_KEYS key are NOT redacted (the
    absent value is not a secret; redacting `None` to `[REDACTED]` would
    signal "there's a secret here, just not currently set" — worse than
    leaving the absence visible).
    """
    if visited is None:
        visited = set()
    # Only containers can self-reference. id()-keyed so identity, not equality.
    if isinstance(v, (dict, list, tuple, set, frozenset)):
        if id(v) in visited:
            return CYCLE_SENTINEL
        visited.add(id(v))
    if (
        key_hint
        and key_hint.lower() in _SECRET_KEYS
        and v not in (None, "")
    ):
        return REDACTED
    if isinstance(v, str):
        return _redact_string(v)
    if isinstance(v, dict):
        return {k: _walk_value(item, key_hint=str(k), visited=visited) for k, item in v.items()}
    if isinstance(v, list):
        return [_walk_value(item, visited=visited) for item in v]
    if isinstance(v, tuple):
        walked = [_walk_value(item, visited=visited) for item in v]
        cls = type(v)
        if cls is tuple:
            return tuple(walked)
        # NamedTuple convention: `cls._make(iterable)` is the canonical
        # constructor (per typing.NamedTuple docs).
        make = getattr(cls, "_make", None)
        if callable(make):
            try:
                return make(walked)
            except (TypeError, ValueError):
                pass  # fall through to *walked / plain tuple
        # Plain tuple subclass with positional __init__: try *walked.
        try:
            return cls(*walked)
        except TypeError:
            # Subclass with incompatible signature — surrender class
            # identity rather than crash. Returning a plain tuple keeps
            # the redacted contents flowing; downstream renderers see a
            # tuple, not a TypeError. WK-03 / Phase 022.3.
            return tuple(walked)
    if isinstance(v, BaseException):
        # Preserve the exception class for downstream renderers; redact str(v).
        # Construct a NEW instance so the live exception is unmutated.
        redacted_msg = _redact_string(str(v))
        try:
            return type(v)(redacted_msg)
        except TypeError:
            # Multi-arg / signature-mismatched exception subclass (e.g.
            # httpx.HTTPStatusError, subprocess.CalledProcessError, any
            # custom exception with structured kwargs). Returning the
            # live exception object would leak token bytes through any
            # downstream str(exc) / format_exc_info renderer (T-020-4 /
            # RESEARCH §Pitfall 5). Fall back to a plain RuntimeError
            # carrying ONLY the redacted message — downstream renderers
            # see a redacted string, never the original exception bytes.
            # See MF-01 in 020-REVIEW.md.
            return RuntimeError(redacted_msg)
    return v


def redact_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """structlog processor — install at position 0 of the chain.

    Walks every value in *event_dict* and substitutes secret-shaped
    substrings with REDACTED. Preserves event_dict KEYS verbatim (key
    names are public; values may be private).

    Per the structlog ≥25.1 processor contract:
      * Receives (logger, method_name, event_dict)
      * Returns the (possibly modified) event_dict
      * Modification of event_dict in place is allowed (we return a new
        dict instead — Pydantic-style immutability is easier to reason
        about; benchmarks show no measurable overhead for typical
        event-dict sizes <50 keys).

    Used by Plan 03's install() in BOTH:
      * structlog.configure(processors=shared_processors + [...])
      * ProcessorFormatter(foreign_pre_chain=shared_processors, ...)

    which makes it the universal redactor across structlog-native
    loggers AND stdlib loggers (httpx, litellm, pygit2, aiosqlite).
    """
    return {k: _walk_value(v, key_hint=str(k)) for k, v in event_dict.items()}


def iter_token_patterns() -> tuple[re.Pattern[str], ...]:
    """Public accessor for the compiled regex set.

    Phase 018's auth/providers/api_key.iter_known_prefixes() is the
    canonical precedent — exposing the prefix surface in one
    grep-visible location keeps the security-critical artifact
    auditable.

    Used by:
      * tests/test_redactor.py — REDACT-17 (final-render belt-and-braces),
        REDACT-24 (hypothesis fuzzer over prefix families).
      * Future phase research — when adding a new auth provider, the
        new prefix must be added to _PATTERNS in this module AND the
        new provider's research file must reference iter_token_patterns()
        as the verification surface.
    """
    return _PATTERNS


# ── Wiring layer (Plan 03) ────────────────────────────────────────────


class RedactorNotAttached(RuntimeError):
    """Raised when the redactor is not attached at daemon start.

    P0-14 / AUTH-10 defense layer 2: if install() did not run before
    assert_redactor_attached() (or if a future regression detached the
    processor), the canary survives the rendering pipeline and this
    exception fires. Fatal — caller must NOT catch this; let it
    propagate so the daemon process exits non-zero.

    See RESEARCH §Pitfall 2: structlog has no built-in
    "is-this-processor-in-the-chain?" assertion; this self-check is
    the only affirmative verification.
    """


# Idempotency guard for install(). Module-level so re-imports under
# importlib.reload() reset the guard (which is fine — install() will
# re-attach to the new structlog config).
_INSTALLED: bool = False


def install(level: int | None = logging.DEBUG) -> None:
    """Idempotently install the redactor at position 0 of the structlog chain
    AND attach a ProcessorFormatter to the stdlib root logger.

    After install(), every log record from BOTH:
      * structlog.get_logger("...").info(...)  — structlog-native
      * logging.getLogger("httpx").debug(...) — stdlib (third-party libs)
    flows through redact_processor before any renderer runs.

    Pattern source: structlog ≥25.1 stdlib-integration docs (canonical
    'shared_processors' wiring for unified coverage). See RESEARCH §Code
    Examples §4.

    Args:
        level: Stdlib root logger level to set after handler attachment.
            Defaults to `logging.DEBUG` (preserves Phase 020 behavior).
            Pass `None` to skip the setLevel call entirely (operators
            with pre-configured levels). WK-05 / Phase 022.3.

    Idempotency:
      * Calling install() multiple times is a no-op after the first.
      * The `_INSTALLED` module-level guard prevents duplicate handlers
        and duplicate redact_processor entries in the chain.
      * REDACT-23 verifies idempotency.

    Side effects (UNAVOIDABLE — install() is by definition imperative):
      * structlog.configure(...) replaces the global structlog config.
      * logging.getLogger().addHandler(...) appends a stream handler to
        the stdlib root logger.
      * logging.getLogger().setLevel(level) — when *level* is not None
        (default `logging.DEBUG`), install() sets the root logger
        level so third-party libraries at that level flow through the
        redactor. Pass `level=None` to skip the setLevel call entirely
        and leave any pre-existing root level intact (useful for tests
        and CLI tools that have already configured a level). The
        DEBUG default is intentional in production: at higher levels,
        DEBUG records from httpx/litellm/pygit2/aiosqlite are dropped
        before the redactor sees them, reducing redactor coverage —
        an operator-tunable tradeoff.

    Tests must use the `_isolate_structlog_for_redactor_tests` autouse
    fixture (tests/test_redactor.py) which snapshots and restores
    structlog config to keep install()'s mutations test-local.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    shared_processors: list[Any] = [
        redact_processor,                              # ← position 0: the redactor
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,           # exception → string AFTER redactor
    ]

    # structlog-native loggers — wrap_for_formatter sends events to the
    # stdlib root logger's ProcessorFormatter (below) for final rendering.
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # stdlib loggers (httpx / litellm / pygit2 / aiosqlite) — same
    # shared_processors list runs as foreign_pre_chain so third-party
    # records flow through redact_processor before final render.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    root = logging.getLogger()
    # SF-03: idempotency under `_INSTALLED` reset. If a test fixture or
    # importlib.reload() resets `_INSTALLED` to False, calling install()
    # again would otherwise add a SECOND ProcessorFormatter handler to
    # the root logger, doubling output. Detect a redactor-bearing
    # ProcessorFormatter already on the root and skip handler attachment
    # in that case. structlog.configure() above is naturally idempotent
    # (it replaces the global config, not appends).
    already_attached = any(
        isinstance(h.formatter, structlog.stdlib.ProcessorFormatter)
        and redact_processor in (getattr(h.formatter, "foreign_pre_chain", ()) or ())
        for h in root.handlers
    )
    if not already_attached:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    if level is not None:
        root.setLevel(level)

    _INSTALLED = True


def assert_redactor_attached() -> None:
    """Emit a canary secret-shaped string through BOTH structlog and stdlib
    loggers; raise RedactorNotAttached if the canary survives in any
    rendered output.

    Called by `src/state_daemon/orchestrator.py::startup()` as Step 0,
    BEFORE any other I/O. If the redactor is not attached (or is
    attached but bypassed by a wiring bug), this function raises
    RedactorNotAttached — fatal — and the daemon process exits.

    A fresh canary is generated per call as
    `sk-ant-oat-canary-<uuid4-hex>-<32 X chars>`. The regex set
    matches it (sk-ant-oat- + ≥20 alnum chars). On success, the
    rendered output contains `[REDACTED]` instead of the canary
    bytes. The per-call freshness prevents an attacker who has read
    a previous canary from spoofing the self-check.

    Raises:
        RedactorNotAttached: if the canary survives in either:
            (a) the structlog event-dict produced by invoking
                redact_processor directly on a synthetic canary event
                (SF-02: no capture_logs(processors=...) dependency, so
                no structlog ≥25.5 floor required for the self-check), or
            (b) the stdlib root-logger formatter's rendered output.

    See RESEARCH §Code Examples §3.
    """
    canary_id = uuid.uuid4().hex
    canary = f"sk-ant-oat-canary-{canary_id}-" + ("X" * 32)

    # Path 1 — structlog-native caller path.
    #
    # SF-02: invoke redact_processor directly on a synthetic event_dict
    # rather than going through capture_logs(). The capture_logs(processors=...)
    # kwarg landed in structlog 25.5.0; relying on it forced a hard pin
    # that was looser than the actual API requirement, and a deploy on
    # 25.1..25.4 would TypeError at startup. Direct invocation removes
    # the version dependency and is strictly equivalent for the
    # redactor-attached self-check (we are verifying the function is
    # WIRED at position 0 and that running it produces a redacted
    # output — neither requires capture_logs).
    cfg = structlog.get_config()
    configured = list(cfg.get("processors", ()))
    if not configured or configured[0] is not redact_processor:
        raise RedactorNotAttached(
            "redact_processor not at position 0 of the structlog "
            "processor chain. install() did not run, or a future "
            "regression reordered shared_processors. Refusing to "
            "start daemon."
        )
    canary_event: dict[str, Any] = {
        "event": "selfcheck",
        "token": canary,
        "msg": f"value is {canary}",
    }
    redacted_event = redact_processor(None, "info", canary_event)
    if canary in str(redacted_event):
        raise RedactorNotAttached(
            "redact_processor failed to redact canary token in direct "
            "invocation; module is broken. Refusing to start daemon."
        )

    # Path 2 — stdlib caller path (httpx / litellm / pygit2 / aiosqlite).
    # Render a synthetic LogRecord through the root logger's formatter
    # and string-search the output for the canary bytes. We render via
    # the formatter directly (no I/O sink) so canary bytes never reach
    # a real sink even if redaction failed.
    stdlib_logger_name = "state_core.observability.redactor.selftest.stdlib"
    rec = logging.LogRecord(
        name=stdlib_logger_name,
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="selfcheck stdlib path: token=%s",
        args=(canary,),
        exc_info=None,
    )
    root = logging.getLogger()
    rendered_outputs: list[str] = []
    formatter_count = 0
    for handler in root.handlers:
        fmt = handler.formatter
        # Only audit ProcessorFormatter instances (the ones install()
        # attached). Other handlers — pytest's LogCaptureHandler,
        # 3rd-party plugins, OS-vendored basicConfig handlers — are
        # outside this redactor's responsibility surface; verifying
        # them would either false-positive (their formatter doesn't
        # know about foreign_pre_chain) or fail in confusing ways.
        if not isinstance(fmt, structlog.stdlib.ProcessorFormatter):
            continue
        formatter_count += 1
        try:
            rendered_outputs.append(fmt.format(rec))
        except Exception as exc:
            # WK-06: a misconfigured ProcessorFormatter that raises on
            # render is FATAL — we cannot verify redactor attachment
            # against its output. Distinguish from "no formatter present"
            # below. Chain via `from exc` to preserve traceback.
            raise RedactorNotAttached(
                f"ProcessorFormatter on root logger raised on canary "
                f"render: {type(exc).__name__}: {exc!r}. "
                "Cannot verify redactor attachment. Refusing to start."
            ) from exc
    if formatter_count == 0:
        raise RedactorNotAttached(
            "stdlib root logger has no ProcessorFormatter handler; "
            "install() did not attach a ProcessorFormatter. "
            "Refusing to start daemon."
        )
    for output in rendered_outputs:
        if canary in output:
            raise RedactorNotAttached(
                "stdlib root-logger redactor failed to redact canary "
                "token; ProcessorFormatter.foreign_pre_chain not wired. "
                "Refusing to start daemon."
            )


__all__ = [
    "CYCLE_SENTINEL",
    "REDACTED",
    "RedactorNotAttached",
    "assert_redactor_attached",
    "install",
    "iter_token_patterns",
    "redact_processor",
]
