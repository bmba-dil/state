---
phase: 020-root-logger-token-redactor
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/state_core/observability/__init__.py
  - src/state_core/observability/redactor.py
  - src/state_daemon/orchestrator.py
  - tests/test_redactor.py
  - tests/test_observability_import_graph.py
findings:
  critical: 1
  warning: 4
  info: 6
  total: 11
status: issues_found
---

# Phase 020 — Code Review Report

**Reviewed:** 2026-04-30
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found (1 MUST-FIX security issue + 4 SHOULD-FIX + 6 WORTH-KNOWING)

## Summary

Phase 020 ships the root-logger token redactor (`state_core.observability.redactor`,
~450 LOC), the orchestrator Step-0 wiring (5 LOC), the 28-test redactor suite
(~700 LOC), and the mode-isolation lint (~100 LOC). All 26 VALIDATION rows
flipped to GREEN per `020-VALIDATION.md`. Functionality is solid for the
documented threat surfaces (T-020-1..7); the daemon refusal contract is
enforced via `assert_redactor_attached()` raising `RedactorNotAttached` when
the chain is missing or reordered; idempotency of `install()` holds for
single-process startup; the 12-pattern compiled regex set covers all 8
documented token shape families.

Cardinal-rule compliance is clean:

- **Mode isolation:** `redactor.py` imports only stdlib (`logging`, `re`,
  `uuid`, `typing`) and `structlog`. The allow-list in
  `tests/test_observability_import_graph.py::test_observability_imports_only_allowed_targets`
  permits `state_core.auth.providers.api_key` (per RESEARCH §Architecture
  Patterns) but the redactor does not currently use it — extra slack, fine.
  Forbidden-substring lint covers the four canonical mode-import shapes
  (`state_build`/`state_teach` × `from`/`import`) plus the dotted variants.
- **Determinism:** `_PATTERNS` is a module-level `tuple[re.Pattern, ...]`
  compiled at import. `_SECRET_KEYS` is a `frozenset`. `REDACTED` is a
  string constant. No `datetime.now()` / `random.*` reads. The only
  non-determinism inside the module is `uuid.uuid4().hex` inside
  `assert_redactor_attached()` — that is a one-shot startup
  self-check, not a per-record path, and is the canonical way to
  generate a unique canary.
- **Defense-in-depth:** the layer-1/layer-2 split is documented in the
  module docstring (lines 14-18, 22-24) with the explicit "Both required"
  emphasis. RESEARCH §Anti-Patterns rejection of "lull future callers"
  is honored.
- **Length-uniform replacement:** `REDACTED = "[REDACTED]"` (10 chars)
  satisfies RESEARCH §Anti-Patterns rejection of length-preserving
  placeholders (the length-as-side-channel concern).

Test coverage is comprehensive: 28 named tests cover REDACT-01..24, 26
plus the four structural extras (`test_pattern_set_compiled_at_import`,
`test_iter_token_patterns_returns_tuple`, `test_walk_value_and_secret_keys_imported`).
The hypothesis property at REDACT-24 covers all 12 prefix families with
200 examples per RESEARCH T-020-W0-4 (the 1000-draw target is a phase-gate
concern, not a per-test budget).

**However, one MUST-FIX security issue exists** in `_walk_value`'s
`BaseException` branch: the `except TypeError: return v` fallback path
returns the **live, unredacted exception object** for any exception
class with a non-`(str,)`-compatible `__init__`. Empirically verified
that `httpx.HTTPStatusError(request=..., response=...)` — a class used
by the entire provider routing surface — hits this path, and downstream
`str(walked)` contains the token bytes verbatim. This is a regression
of T-020-4 (Pitfall 5: exception repr carries plaintext token) for any
`BaseException` subclass with multi-arg `__init__`, which is common.

Three SHOULD-FIX items concern (a) the dropped `(?<!\w)` look-behind
boundary anchors that RESEARCH §Code Examples §1 specified — the
implementation uses pure shape patterns without word-boundary
anchoring, which means `aaask-` followed by 40 alnum chars matches
the OpenAI generic pattern and gets redacted as `aaa[REDACTED]`
(over-redaction in unusual but possible cases like base64-encoded
strings); (b) the `structlog>=25.1` pin is too loose for the
`capture_logs(processors=...)` API used inside `assert_redactor_attached()`
(that kwarg landed in 25.5.0 — a deploy on 25.1..25.4 would TypeError
at startup); (c) the orchestrator imports `from src.state_core...`
while observability and tests use `from state_core...` (existing
codebase inconsistency, but worth flagging).

Six WORTH-KNOWING items document smaller smells. None block landing;
verification is GREEN per `020-VALIDATION.md`.

## MUST-FIX

### MF-01: `_walk_value`'s BaseException fallback returns the live unredacted exception — defeats T-020-4 / Pitfall 5 for httpx.HTTPStatusError and similar multi-arg exception classes

**File:** `src/state_core/observability/redactor.py:170-179`

**Severity:** Security — secrets leak through exception repr.

**Issue:** The `_walk_value` BaseException branch does:

```python
if isinstance(v, BaseException):
    try:
        return type(v)(_redact_string(str(v)))
    except TypeError:
        return v   # ← BUG: returns live exception, not a redacted string
```

The `try` block constructs a NEW instance of the exception class with
the redacted message — correct for single-arg exceptions like
`RuntimeError("bad token sk-ant-oat-...")`. But many production
exception classes have multi-arg `__init__`:

- `httpx.HTTPStatusError(message, *, request, response)` — used by
  every provider HTTP call;
- `httpx.RequestError(message, *, request)`;
- `litellm.exceptions.AuthenticationError(message, llm_provider, model, response)`;
- `subprocess.CalledProcessError(returncode, cmd, output, stderr)`;
- `pygit2.GitError(...)` (some variants);
- any custom exception in this codebase that takes structured kwargs.

For all of these, `type(v)(redacted_str)` raises `TypeError: __init__()
missing N required arguments`, the `except` clause fires, and the
**original exception object** is returned. Downstream renderers
(`structlog.processors.format_exc_info`, `traceback.format_exception`,
or any `str(event_dict["exception"])`) call `str(v)` on the original
object — which still contains the token bytes verbatim.

**Empirical verification:**

```python
class MultiArgExc(Exception):
    def __init__(self, request, response):
        super().__init__(f'request to {request} failed: {response}')

e = MultiArgExc('https://api/', 'sk-ant-oat-' + 'X'*30)
walked = _walk_value(e)
# walked is e (same object reference)
# str(walked) == 'request to https://api/ failed: sk-ant-oat-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
# token leaked.
```

This is precisely T-020-4 / RESEARCH §Pitfall 5 ("Exception `repr()`
carries plaintext token"). The defense was supposed to be the
`_walk_value` BaseException recursion; the fallback breaks it.

REDACT-15 passes only because its fixture uses `RuntimeError(...)`
(single-arg). REDACT-16 passes because `ValueError(...)` is also
single-arg AND because `format_exc_info` in the chain runs AFTER
`redact_processor` and re-walks the rendered traceback string. But a
real-world `httpx.HTTPStatusError` raised by an auth provider would
follow neither path: the exception object lives in
`event_dict["exception"]` until format_exc_info runs, but
format_exc_info's render-to-string step calls `str(exc)` (which has
the token) and then the rendered string is what gets walked — except
that walk only happens if the renderer runs **after** another
redact_processor call. In the current `install()` chain, the
processor list is:

```
[redact_processor, merge_contextvars, add_log_level, TimeStamper,
 StackInfoRenderer, format_exc_info, wrap_for_formatter]
```

`redact_processor` runs FIRST, walks `event_dict["exception"]`, hits
the TypeError fallback, returns the live exception. `format_exc_info`
then renders that exception to a string under
`event_dict["exception"]`. That rendered string contains the token
bytes — and there is no redactor downstream of `format_exc_info` to
catch it.

**Fix:** Replace the BaseException branch with a redacted-string
substitution that DOES NOT depend on the exception class accepting
a single string argument. Two options:

(a) **Replace with a redacted-string surrogate** (recommended):

```python
if isinstance(v, BaseException):
    # Construct a new instance only when safe; otherwise replace the
    # exception entirely with a redacted-string surrogate. This loses
    # the exception class identity but guarantees no live-object leak.
    redacted_msg = _redact_string(str(v))
    try:
        return type(v)(redacted_msg)
    except TypeError:
        # Multi-arg / signature-mismatched exception subclass.
        # Fall back to a plain RuntimeError carrying the redacted
        # message — downstream renderers see a redacted string, not
        # the original exception bytes.
        return RuntimeError(redacted_msg)
```

(b) **Use `args` substitution** (preserves class identity for richer
exception types like httpx.HTTPStatusError):

```python
if isinstance(v, BaseException):
    redacted_args = tuple(
        _redact_string(a) if isinstance(a, str) else _walk_value(a)
        for a in v.args
    )
    try:
        new_exc = type(v).__new__(type(v))
        new_exc.args = redacted_args
        # Preserve __cause__ / __context__ chain (recursively walked).
        if v.__cause__ is not None:
            new_exc.__cause__ = _walk_value(v.__cause__)
        return new_exc
    except Exception:
        return RuntimeError(_redact_string(str(v)))
```

(b) preserves richer exception state (request, response on httpx)
but is more complex. (a) is simpler and strictly safer (loses class
identity but never leaks). Recommend (a) for v1; (b) is a future
hardening if downstream consumers need the original exception class.

Either way: add a regression test `test_redacts_multi_arg_exception`
that constructs an exception class with non-`(str,)` `__init__` and
asserts the canary does not survive in the rendered output. The
suggested test:

```python
def test_redacts_multi_arg_exception() -> None:
    """REDACT-15 extension: token in multi-arg exception is redacted.

    Covers httpx.HTTPStatusError-shaped exceptions where __init__
    requires kwargs beyond the message string.
    """
    class MultiArgExc(Exception):
        def __init__(self, request: str, response: str) -> None:
            self.request = request
            self.response = response
            super().__init__(f"request to {request} failed: {response}")

    exc = MultiArgExc("https://api/", f"bad token {_CANARY_ANTHROPIC_OAT}")
    event_dict = {"exception": exc}
    out = redact_processor(None, "error", event_dict)
    assert _CANARY_ANTHROPIC_OAT not in str(out), (
        f"multi-arg exception leaked canary: {out!r}"
    )
```

## SHOULD-FIX

### SF-01: `_PATTERNS` lacks `(?<!\w)` look-behind anchors that RESEARCH §1 specified — over-redacts identifier-prefixed shapes

**File:** `src/state_core/observability/redactor.py:67-92`

**Issue:** RESEARCH §Code Examples §1 specifies every shape pattern
should be wrapped with `(?<!\w)` look-behind and `(?!\w)` look-ahead
boundary anchors:

```python
# RESEARCH §1 (canonical):
re.compile(r"(?<!\w)sk-ant-oat-[A-Za-z0-9_-]{20,}(?!\w)"),
re.compile(r"(?<!\w)sk-[A-Za-z0-9]{40,}(?!\w)"),
# ...
```

The shipped implementation drops both anchors:

```python
# state_core/observability/redactor.py:69, 77
re.compile(r"sk-ant-oat-[A-Za-z0-9_-]{20,}"),
re.compile(r"sk-[A-Za-z0-9]{40,}"),
```

**Empirical impact:** without anchors, a string like `aaask-` followed
by 40+ alnum chars matches the OpenAI generic pattern and gets
redacted as `aaa[REDACTED]`. Verified:

```
input:  'aaask-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'  (3 + 'sk-' + 40 A's)
output: 'aaa[REDACTED]'
```

This is over-redaction, NOT under-redaction (so it is not a
security issue — secrets are still caught). The risk is that
diagnostic strings containing "sk-" embedded in larger tokens
(base64-encoded payloads, request IDs that happen to contain
the substring) get redacted, hiding non-auth debug info.

The negative tests in REDACT-22 still pass because they all use
short strings (`"sk-foundation"`, `"sk-2"`, `"Bearer xyz"` — none
≥40 chars after the prefix), so the length floor saves them. But
a longer false-positive — e.g. a UUID hex prefix `"abcsk-"` followed
by 40+ hex chars in a debug string — would over-redact.

The `Bearer` pattern correctly does NOT have the look-behind
(it has `(?i)` and `\s+`), and that is fine since "Bearer" embedded
in a word is implausible.

RESEARCH §Pitfall 6 (page 3-4 of the doc) explicitly motivates these
anchors. The 020-04-SUMMARY.md / Wave 3 narrowing of the hypothesis
strategy alphabet (from `_-` to alnum-only) suggests the implementer
hit falsifying examples and narrowed the **test** rather than fixing
the **patterns**.

**Fix:** Re-add the anchors per RESEARCH §1. For the 11 prefix-shape
patterns:

```python
_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<!\w)sk-ant-oat-[A-Za-z0-9_-]{20,}(?!\w)"),
    re.compile(r"(?<!\w)sk-ant-api03-[A-Za-z0-9_-]{20,}(?!\w)"),
    re.compile(r"(?<!\w)sk-or-v1-[A-Za-z0-9_-]{20,}(?!\w)"),
    re.compile(r"(?<!\w)sk-(?:proj|svcacct|None)-[A-Za-z0-9_-]{20,}(?!\w)"),
    re.compile(r"(?<!\w)sk-[A-Za-z0-9]{40,}(?!\w)"),
    re.compile(r"(?<!\w)ya29\.[A-Za-z0-9_-]{20,}(?!\w)"),
    re.compile(r"(?<!\w)1//[A-Za-z0-9_-]{20,}(?!\w)"),
    re.compile(r"(?<!\w)(?:gho|ghu|ghs|ghp)_[A-Za-z0-9]{20,}(?!\w)"),
    re.compile(r"(?<!\w)gsk_[A-Za-z0-9]{20,}(?!\w)"),
    re.compile(r"(?<!\w)xai-[A-Za-z0-9]{20,}(?!\w)"),
    re.compile(r"(?<!\w)esecret_[A-Za-z0-9]{20,}(?!\w)"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._\-/+=]{20,}"),
)
```

After the fix, the hypothesis strategy in REDACT-24 can also widen
its alphabet back to `[A-Za-z0-9_-]` for the prefixes that admit
underscores/hyphens (Anthropic / Google / OpenRouter), exercising
those characters that the shipped narrowing currently skips.

If the anchors break any existing tests, that is the test indicating
the implementation is over-redacting and the fix is correct.

### SF-02: `assert_redactor_attached()` uses `capture_logs(processors=...)` which requires structlog ≥25.5 — pyproject pin is `>=25.1`

**File:** `src/state_core/observability/redactor.py:380` + `pyproject.toml:23`

**Issue:** `capture_logs()`'s `processors=` keyword argument was added
in **structlog 25.5.0** (per the live `help(capture_logs)` docstring:
"versionadded:: 25.5.0 *processors* parameter"). The project pin is
`structlog>=25.1` (`pyproject.toml:23`).

A fresh `pip install` resolving structlog 25.1.x..25.4.x would land a
version where `capture_logs(processors=capture_chain)` raises
`TypeError: capture_logs() got an unexpected keyword argument 'processors'`.
This fires inside `assert_redactor_attached()`, which propagates up
through `startup()` and crashes the daemon at Step 0.

The daemon-refusal contract says "if redactor not attached, refuse
to start." It does NOT say "if redactor IS attached but the
self-check has a version-mismatch bug, refuse to start." The current
code conflates the two: a benign version-resolution outcome looks
identical to a redactor-missing failure.

**Fix:** Bump the floor pin in `pyproject.toml` to match the actually-
required API:

```toml
dependencies = [
    # ...
    "structlog>=25.5",  # 25.5+ adds capture_logs(processors=...) used by
                       # state_core.observability.redactor:assert_redactor_attached().
    # ...
]
```

OR rewrite `assert_redactor_attached()` to not depend on the
`processors=` kwarg. The simpler escape: synthesize the canary
event-dict, run it through `redact_processor` directly (without
capture_logs), and string-search the result. That removes the
structlog-version dependency entirely:

```python
# Path 1 alternative — direct invocation, no capture_logs:
canary_event = {"event": "selfcheck", "token": canary, "msg": f"value is {canary}"}
redacted = redact_processor(None, "info", canary_event)
if canary in str(redacted):
    raise RedactorNotAttached(
        "redact_processor failed to redact canary token in direct "
        "invocation; module is broken. Refusing to start daemon."
    )
# Path 1.5 — verify configured-chain has redact_processor at position 0:
cfg = structlog.get_config()
configured = list(cfg.get("processors", ()))
if not configured or configured[0] is not redact_processor:
    raise RedactorNotAttached(
        "redact_processor not at position 0 of the structlog "
        "processor chain. install() did not run, or a future "
        "regression reordered shared_processors. Refusing to start."
    )
```

The simpler version trades full-pipeline verification for
configuration-shape verification — but the existing Path 1.5
check (lines 363-371) already does the latter, so this isn't a
loss. The full-pipeline test in REDACT-17 (test code) already
covers the deeper end-to-end assertion.

Recommend the pin bump (pyproject.toml change) as the smaller
patch. The `capture_logs(processors=...)` kwarg is the cleaner
verification idiom.

### SF-03: `install()` lacks handler-deduplication when `_INSTALLED` is reset — second handler accumulates

**File:** `src/state_core/observability/redactor.py:255-327`

**Issue:** `install()` adds a `StreamHandler` with a `ProcessorFormatter`
to `logging.getLogger()` (line 321-324) gated by the module-level
`_INSTALLED` flag (lines 287-289, 327). If `_INSTALLED` is ever reset
externally — by `importlib.reload(state_core.observability.redactor)`,
by a test fixture (which `tests/test_redactor.py:128` does
deliberately), or by a future hot-reload path — calling `install()`
again ADDS a SECOND handler to the root logger. The
`structlog.configure(...)` call replaces the structlog config (no
duplication), but the stdlib root logger collects handlers
additively.

Empirical verification:

```python
import state_core.observability.redactor as M
install()  # handler count: 1
M._INSTALLED = False  # simulate reload
install()  # handler count: 2 — the original handler is still attached
```

Each handler renders the same event independently, so a doubled
handler means doubled log lines (and doubled token-bytes-on-disk
risk if something downstream of the handler somehow bypasses
redaction).

In production, `_INSTALLED` is only ever set, never reset, so this
is not a live-daemon hazard. The test fixture
`_isolate_structlog_for_redactor_tests` works around it by clearing
`root.handlers` directly (lines 130-132). But the **`install()`
function itself** is not idempotent under all circumstances — only
under the trivial "called twice in a row" case that REDACT-23
tests.

**Fix:** Make `install()` truly idempotent by checking root handlers
for an existing ProcessorFormatter before adding:

```python
def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    shared_processors: list[Any] = [
        redact_processor,
        # ...
    ]

    structlog.configure(...)

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        # ...
    )

    root = logging.getLogger()
    # Idempotent under _INSTALLED reset: only add a handler if the
    # root logger does not already have a redactor-bearing
    # ProcessorFormatter handler.
    already_attached = any(
        isinstance(h.formatter, structlog.stdlib.ProcessorFormatter)
        and redact_processor in (getattr(h.formatter, "foreign_pre_chain", ()) or ())
        for h in root.handlers
    )
    if not already_attached:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    _INSTALLED = True
```

This makes the function self-healing under accidental
`importlib.reload` AND removes the test-fixture's burden of
clearing handlers manually.

### SF-04: `from src.state_core.observability ...` in orchestrator vs `from state_core.observability ...` everywhere else

**File:** `src/state_daemon/orchestrator.py:7-11`

**Issue:** The orchestrator uses `from src.state_core.observability
import ...` (line 9), matching the surrounding lines (7, 8, 10, 11).
But the observability package itself uses `from state_core.observability.redactor
import ...` (`__init__.py:32`), and the test files use `from
state_core.observability.redactor import ...` (`test_redactor.py:58`,
`test_observability_import_graph.py` allow-list).

This is an **existing repo-wide inconsistency** — `src/state_cli/main.py`
and `src/state_core/projector.py` also use `from src.state_core...`
while `src/state_core/auth/__init__.py` and most newer code use
`from state_core...`. Phase 020 inherits the orchestrator file's
pre-existing convention, which is the right call (don't refactor
unrelated style on a security phase).

Two operational risks remain:

1. **Module caching:** if both `state_core.observability` AND
   `src.state_core.observability` are importable (same code,
   different sys.modules entries), the `_INSTALLED` flag could
   end up in the WRONG module copy. `install()` via
   `from src.state_core.observability...` mutates
   `src.state_core.observability.redactor._INSTALLED`, while a
   test importing via `from state_core.observability...` reads
   `state_core.observability.redactor._INSTALLED` — independent
   booleans. The daemon and the test fixture would disagree on
   whether the redactor is installed.

2. **`assert_redactor_attached()` Path 1.5** (line 365: `if
   configured[0] is not redact_processor`) compares by IDENTITY.
   If two module copies exist, two `redact_processor` function
   objects exist, and the `is` check fails — the daemon refuses
   to start with "redact_processor not at position 0" even though
   the chain has the OTHER copy of redact_processor at position 0.

**Fix:** No code change needed for Phase 020 (the existing
orchestrator convention is consistent within its file). Flag for
the cross-cutting cleanup phase that should standardize on `from
state_core...` everywhere. Until then, ensure tests use the SAME
import shape as the daemon — if they don't, REDACT-20 / REDACT-21
could pass / fail nondeterministically across pytest invocations.

Verified: `tests/test_redactor.py:58` uses `from state_core.observability.redactor`
(no `src.` prefix). `src/state_daemon/orchestrator.py:9` uses
`from src.state_core.observability`. These are different module
identities at runtime. If the test-suite ever imports the
orchestrator module directly to drive an integration test, the
identity mismatch would surface.

(Recording as SHOULD-FIX even though it requires no Phase 020 code
change — future test-import or refactor must reconcile, and silent
divergence is risky.)

## WORTH-KNOWING

### WK-01: `_walk_value` raises RecursionError on cyclic structures — documented as deferred but non-graceful

**File:** `src/state_core/observability/redactor.py:130-180`

**Issue:** Module docstring (lines 26-29) explicitly defers cycle
detection: "RESEARCH §Open Question 3 documents the deferral; not in
P0-14 scope." Empirically, a self-referencing dict raises
`RecursionError` rather than terminating gracefully:

```python
d = {}
d['self'] = d
_walk_value(d)  # RecursionError
```

In practice, structlog event-dicts come from auth providers + Pydantic
models, and Pydantic serialization breaks cycles on output. So the
deferral is reasonable. But if a future code path passes a cyclic
structure (e.g., a graph traversal logger, an `__repr__` that includes
self-reference), the redactor crashes the call stack.

**Fix:** No change required. If a cycle ever arises, add an `id(v)`
visited-set parameter to `_walk_value`. For now, the documented
deferral is acceptable.

### WK-02: `_redact_string` runs all 12 patterns sequentially — order-dependent and non-canonical for overlapping shapes

**File:** `src/state_core/observability/redactor.py:117-127`

**Issue:** `_redact_string` does `for pat in _PATTERNS: s = pat.sub(REDACTED, s)`.
This means a string that matches BOTH the specific `sk-ant-oat-...`
pattern (index 0) AND the generic `sk-[A-Za-z0-9]{40,}` (index 4) is
matched by index 0 first, replaced with `[REDACTED]`, and then index
4 cannot match `[REDACTED]` (no `sk-` prefix anymore). Good —
intentional, documented at lines 121-124.

The risk: a future contributor adds a NEW pattern between index 0
and index 4 that DOES match `[REDACTED]` (e.g., a regex matching
`[A-Za-z]+`). Currently no such pattern exists. The order discipline
is documented as load-bearing in the docstring (lines 64-66, 121-124)
but is not enforced by a test.

**Fix:** Optional — add a structural test `test_pattern_order_specific_before_generic`
that verifies the index of `sk-ant-oat-` < index of `sk-[A-Za-z0-9]{40,}`,
making the order contract a green/red signal:

```python
def test_pattern_order_specific_before_generic() -> None:
    """Order contract: more-specific shapes BEFORE generic sk-... pattern."""
    sources = [p.pattern for p in _PATTERNS]
    specific_idx = next(i for i, s in enumerate(sources) if "sk-ant-oat-" in s)
    generic_idx = next(i for i, s in enumerate(sources) if s.startswith("sk-[A-Za-z0-9]{40"))
    assert specific_idx < generic_idx, (
        f"order regression: specific (idx={specific_idx}) "
        f"must come before generic (idx={generic_idx})"
    )
```

Defer until a regression occurs.

### WK-03: `_walk_value` preserves `tuple` type but loses subclass identity for `NamedTuple` / `dict` subclasses

**File:** `src/state_core/observability/redactor.py:165-169`

**Issue:** For lists/tuples, `_walk_value` does `type(v)(walked)` — for
a vanilla `tuple`, this works. For a `NamedTuple` subclass, the
constructor expects positional args (`MyTuple(*walked)`), not a
single iterable, so `type(v)(walked)` raises TypeError. Same for
some `dict` subclasses with custom `__init__`.

In practice, structlog event-dicts rarely contain NamedTuples or
custom dict subclasses (Pydantic v2 models are walked as plain dicts
once serialized by `.model_dump()`). The narrow type check
`(list, tuple)` already excludes most subclass concerns.

**Fix:** No change required. If a NamedTuple-bearing event-dict ever
arises, change `type(v)(walked)` to `type(v)(*walked)` for tuples,
or handle NamedTuple specially via `_make`.

### WK-04: `assert_redactor_attached()` does not reset the canary's UUID on each call — multiple callers in one process see different canaries (good) but the function name suggests "the canary" singular

**File:** `src/state_core/observability/redactor.py:330-443`

**Issue:** Each call to `assert_redactor_attached()` generates a fresh
`uuid.uuid4().hex`-suffixed canary (line 352). This is correct —
prevents an attacker who has read a previous canary from spoofing the
self-check. The docstring (line 340-341) says "The canary is..."
(singular), implying a single fixed canary. Minor doc clarity issue.

**Fix:** Adjust the docstring wording — "A fresh canary is generated
per call as `sk-ant-oat-canary-<uuid4-hex>-<32 X chars>`. The regex set
matches it (sk-ant-oat- + ≥20 alnum chars)." Trivial.

### WK-05: `install()` calls `root.setLevel(logging.DEBUG)` unconditionally — clobbers existing log levels set by tests/CLI

**File:** `src/state_core/observability/redactor.py:325`

**Issue:** Line 325 sets the stdlib root logger level to DEBUG
unconditionally. This is documented as intentional (lines 278-281: 
"so third-party libraries at DEBUG can flow through the redactor").
The side effect: if a test or CLI tool previously called
`logging.getLogger().setLevel(logging.WARNING)` to suppress noisy
third-party logs, `install()` resets it to DEBUG, and that test/CLI
suddenly emits a flood of httpx/litellm DEBUG records.

In production this is the desired behavior — DEBUG records flow
through the redactor before final-stage filters elsewhere drop
them. In tests, the autouse fixture
`_isolate_structlog_for_redactor_tests` (lines 105-144) saves and
restores `root.level`, so test isolation holds.

**Fix:** No change required. Document the intentional level-clobber
in the daemon-startup runbook so operators with existing
`PYTHONLOGGING` env-var configs are not surprised. Optional: add an
`install(level: int = logging.DEBUG)` parameter so callers (e.g.,
tests, CLI) can explicitly request a different level. Defer until
an operator hits the surprise.

### WK-06: `assert_redactor_attached()` Path 2 silently treats "no ProcessorFormatter rendered" as failure but treats "ProcessorFormatter render raised Exception" as not-failure — inverted hierarchy

**File:** `src/state_core/observability/redactor.py:412-436`

**Issue:** Path 2 iterates root handlers, attempts to render the
canary record through each ProcessorFormatter, catches `Exception`
silently (line 425-430), and only fails if `rendered_outputs` is
empty after the loop (line 431-436) OR if a successful render
contains the canary (line 437-443).

A misconfigured ProcessorFormatter that ALWAYS raises on render
(e.g., a `JSONRenderer(serializer=broken_fn)`) would silently pass
the self-check: every iteration hits the `except Exception` branch,
`rendered_outputs` stays empty, but it stays empty because of the
exceptions, not because no formatter exists. The "no formatter"
branch then fires with the misleading message "stdlib root logger
has no ProcessorFormatter handler" — which is wrong. There IS one,
it's just broken.

This is unlikely in practice (the `install()` function constructs
the ProcessorFormatter inline and uses the standard JSONRenderer).
But the error message would mis-diagnose.

**Fix:** Distinguish "no ProcessorFormatter found" from "every
ProcessorFormatter raised on render":

```python
formatter_count = 0
for handler in root.handlers:
    fmt = handler.formatter
    if not isinstance(fmt, structlog.stdlib.ProcessorFormatter):
        continue
    formatter_count += 1
    try:
        rendered_outputs.append(fmt.format(rec))
    except Exception as exc:
        raise RedactorNotAttached(
            f"ProcessorFormatter on root logger raised on canary "
            f"render: {type(exc).__name__}: {exc!r}. "
            "Cannot verify redactor attachment. Refusing to start."
        ) from exc
if formatter_count == 0:
    raise RedactorNotAttached(
        "stdlib root logger has no ProcessorFormatter handler; ..."
    )
```

This makes the daemon-refusal contract more precise: ANY render
failure is fatal, not just "no formatter present." Defer until a
broken formatter shows up in the wild.

---

## Cardinal-Rule Spot Check (all PASS)

| Rule | File | Status |
|---|---|---|
| Mode isolation: no `state.build.*` / `state.teach.*` imports | redactor.py | PASS (line 50-56 stdlib + structlog only; REDACT-25 lint enforces) |
| Mode isolation: redactor.py imports only allowed targets | redactor.py | PASS (allow-list `state_core.auth.providers.api_key` is permitted but unused — extra slack) |
| Determinism: `_PATTERNS` compiled at import (no per-call `re.compile`) | redactor.py:67-92 | PASS |
| Determinism: `_SECRET_KEYS` is `frozenset` (immutable) | redactor.py:98 | PASS |
| Determinism: `REDACTED` is module constant | redactor.py:113 | PASS |
| Length-uniform replacement (rejects length oracle) | redactor.py:113 | PASS (`"[REDACTED]"` is 10 chars; not length-preserving) |
| Defense-in-depth (layer 1 + layer 2 documented) | redactor.py:14-18 + 22-24 | PASS |
| Daemon refusal contract enforced | orchestrator.py:37-38 + redactor.py:330-443 | PASS (REDACT-21 verifies fail-fast) |
| Position 0 of structlog chain | redactor.py:292 + REDACT-18 | PASS |
| Foreign pre-chain wires the same shared_processors | redactor.py:315 + REDACT-19 | PASS |
| `install()` is idempotent under "called twice" | redactor.py:287-289 + REDACT-23 | PASS (under `_INSTALLED` reset: see SF-03 above) |
| 12 token-shape families covered | redactor.py:67-92 | PASS (Anthropic OAuth, Anthropic API, OpenRouter, OpenAI prefixed, OpenAI generic, Google access, Google refresh, GitHub copilot ×4, Groq, xAI, DeepSeek, Bearer header) |
| 12-key SECRET_KEYS frozenset | redactor.py:98-111 | PASS (access, access_token, refresh, refresh_token, token, api_key, apikey, authorization, x-api-key, x-goog-api-key, client_secret, code_verifier) |
| Lowercase key-context lookup | redactor.py:159 | PASS (`key_hint.lower() in _SECRET_KEYS`) |
| Empty/None values not redacted under SECRET key | redactor.py:160 | PASS (`v not in (None, "")`) |
| `_walk_value` recurses into dicts | redactor.py:165-166 | PASS |
| `_walk_value` recurses into lists/tuples | redactor.py:167-169 | PASS |
| `_walk_value` recurses into BaseException | redactor.py:170-179 | PARTIAL (see MF-01: multi-arg subclasses leak through fallback) |
| Public API surface in `__all__` | redactor.py:446-453 | PASS (6 symbols: REDACTED, RedactorNotAttached, assert_redactor_attached, install, iter_token_patterns, redact_processor) |
| Re-export at `state_core.observability.__init__` | __init__.py:32-48 | PASS (same 6 symbols) |
| Docstrings on all 6 public symbols | redactor.py | PASS (REDACTED line 113-114; redact_processor 188-208; iter_token_patterns 213-227; install 256-285; assert_redactor_attached 331-350; RedactorNotAttached 235-246) |

## Security Spot Check

- **No hardcoded secrets** — module contains regex literals matching
  shape-prefixes only; the canary in `assert_redactor_attached()` is a
  test sentinel string. Test fixtures use `_CANARY_*` prefixes
  (greppable, never produced by real providers).
- **No `eval()` / `exec()` / `os.system()` / `subprocess`** use.
- **No SQL / shell injection** surfaces (no DB / shell calls).
- **No path traversal** — module does not open files.
- **No insecure crypto** (no crypto in this phase).
- **No `dangerouslySetInnerHTML` / XSS** surfaces (Python backend
  module).
- **T-020-1..3, 5..7 verified** by REDACT-01..14, 17, 19, 21 GREEN.
- **T-020-4 PARTIALLY broken** — see MF-01. Single-arg exceptions
  (REDACT-15, REDACT-16) pass; multi-arg subclasses leak through the
  TypeError fallback.
- **T-020-8 (future shape addition)** — `iter_token_patterns()` is
  exposed as the canonical extension surface (line 212-228), mirroring
  Phase 018's `iter_known_prefixes()` precedent.
- **Canary attack surface:** the canary is randomized per call
  (`uuid.uuid4().hex`), so an attacker who scrapes a previous canary
  cannot replay it. PASS.
- **Canary leak:** the canary itself is shape-matched by the regex set
  (`sk-ant-oat-canary-...`), so even if the self-check raises, the
  canary bytes have already been redacted before any sink sees them.
  Path 2 (line 412-443) renders through the formatter directly without
  touching real I/O sinks — canary never touches disk even on
  redactor failure. PASS.

## Concurrency Spot Check

- **`_INSTALLED` flag race:** Python module globals are set
  atomically under the GIL. Single-process daemon startup is
  serialized; multi-thread callers (none in current architecture)
  would have a TOCTOU window between line 288 (read `_INSTALLED`)
  and 327 (write True), but the worst case is double-installation
  → mitigated by SF-03's handler-dedup proposal.
- **`_PATTERNS` immutability:** `tuple` is immutable; `re.Pattern`
  objects are thread-safe (CPython documents `re.compile` results
  as safe to share). PASS.
- **`_SECRET_KEYS` immutability:** `frozenset` is immutable. PASS.
- **`_walk_value` purity:** no module-global writes; allocates new
  structures (dict comprehension, list comprehension); does not
  share state with the caller. Thread-safe.
- **`redact_processor` purity:** ditto. Thread-safe.
- **`assert_redactor_attached()` thread-safety:** uses
  `capture_logs()` which structlog ≥25 docs explicitly say is NOT
  thread-safe. Daemon startup is single-thread, so this is fine.
  PASS.

## Performance Spot Check (out-of-scope-for-v1)

- Pattern compilation at import: 12 `re.compile` calls. Sub-millisecond.
- Per-record overhead: 12 `pat.sub(REDACTED, s)` calls per string
  value, plus 1 `dict.get()` against `_SECRET_KEYS` per dict-key. For
  a typical event-dict with ~10 string values × 12 patterns × ~50
  chars/value, this is ~6000 char-level regex tests per record.
  Sub-microsecond per record on modern hardware. Not a hot-path
  concern.
- Recursion: `_walk_value` allocates a new dict / list / tuple for
  every walked container. For a deeply-nested event-dict, this is
  O(N) allocations where N = total container nodes. Acceptable.
- `iter_token_patterns()` returns the live `_PATTERNS` tuple — no
  copy, no per-call allocation.
- Memory: `_PATTERNS` holds 12 compiled `re.Pattern` objects;
  `_SECRET_KEYS` holds 12 strings. Negligible (<2KB).

## Maintainability Spot Check

- **Public API surface:** 6 symbols in `__all__` — `REDACTED`,
  `RedactorNotAttached`, `assert_redactor_attached`, `install`,
  `iter_token_patterns`, `redact_processor`. Re-exported at
  `state_core.observability.__init__`. Clean.
- **Docstring completeness:** every public symbol has a substantive
  docstring with Args / Returns / Raises / cardinal-rule
  cross-references. Excellent provenance — every regex pattern
  cites its source file (`.state-inputs/claude-oauth.md`,
  `state_core/auth/providers/api_key.py`, etc.), every cardinal
  rule names its enforcement test (REDACT-25), every pitfall is
  cross-referenced to RESEARCH.
- **Test coverage:** 28 named tests covering REDACT-01..24, 26 plus
  4 structural extras. REDACT-25 lives in the import-graph file.
  VALIDATION matrix all GREEN per `020-VALIDATION.md`.
- **Hypothesis property:** REDACT-24 covers all 12 prefix families
  with 200 examples. The narrowed alphabet (alnum-only, no `_-`)
  is documented as deliberate (line 596-599 of test file) but
  reduces coverage relative to RESEARCH §1's `[A-Za-z0-9_-]`
  body — see SF-01 for why.
- **Cross-references:** every cardinal rule, every pitfall, every
  threat-model row is named in code via comments. RESEARCH.md is
  the authoritative source — no doc drift in the regex set
  (verified line-by-line against §1).

## No-Regression Confirmation

Per `020-VALIDATION.md`:
- All 26 REDACT rows GREEN.
- Wave 0 RED → Wave 2 GREEN (Plan 02) → Wave 3 GREEN (Plan 03).
- Mode-isolation guard (REDACT-25) GREEN — no `state_build` /
  `state_teach` import shapes in `redactor.py`.
- `tests/auth/conftest.py::_isolate_structlog_for_auth_tests` still
  works after `install()` lands (REDACT-26 verifies via a
  `refresh.completed` log-call regression check).

## Recommended Next Steps

1. **MUST-FIX MF-01** before any `httpx.HTTPStatusError`-bearing code
   path can land. The auth providers raise httpx exceptions; this is
   load-bearing for AUTH-08 / AUTH-10 closure.
2. **SHOULD-FIX SF-01** to honor RESEARCH §1's `(?<!\w)` boundary
   anchors. Bonus: re-widen the hypothesis alphabet to `[A-Za-z0-9_-]`
   in REDACT-24.
3. **SHOULD-FIX SF-02** — bump `pyproject.toml` floor to
   `structlog>=25.5` (one-line change).
4. **SHOULD-FIX SF-03** — make `install()` self-healing under
   `_INSTALLED` reset.
5. SF-04 is informational; defer to a cross-cutting import-style
   cleanup phase.
6. WK-01..06 are documentation / future-hardening notes; defer
   pending operational signals.

---

_Reviewed: 2026-04-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
