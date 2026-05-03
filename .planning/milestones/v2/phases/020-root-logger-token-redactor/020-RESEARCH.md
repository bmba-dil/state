# Phase 020: root-logger-token-redactor — Research

**Researched:** 2026-04-30
**Domain:** Secret hygiene / observability — root-logger redaction processor
**Confidence:** HIGH for structlog wiring + token-shape regex set + module placement; MEDIUM for "shared_processors universal-coverage" claim (verified via official docs but never exercised in this repo's existing structlog config).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All implementation choices are at Claude's discretion — discuss phase was skipped per user setting (`workflow.skip_discuss: true`). Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Anchor points (from PROJECT.md cardinal rules and prior phases):
- structlog is the project logging stack — the redactor MUST be a structlog processor (NOT a stdlib `logging.Filter`, which would miss structlog event-dict values)
- mode-isolation: `state_core.observability.*` (or wherever this lives) MUST NOT import `state.build.*` or `state.teach.*`
- determinism: regex compilation at module-import time, no per-call `re.compile`
- secret-shape patterns from `.planning/research/PITFALLS.md` P0-14 and `.state-inputs/claude-oauth.md` — match byte-for-byte
- daemon-start-refusal: a startup self-check that emits a known secret-shaped string through the root logger and asserts the rendered output does not contain it; if the assertion fails, raise a fatal error before any other initialization

### Claude's Discretion

- Module path: `state_core.observability.redactor` (default — matches "Observability Arc is load-bearing" theme in PITFALLS §Roadmap Implications) vs `state_core.logging.redactor` vs `state_core.auth.redactor`. Default chosen because the redactor is observability-layer plumbing, not auth-method plumbing.
- Replacement string: `"[REDACTED]"` (default) vs preserve length / structural shape. Default chosen — debugging value of "string is shorter now" is dwarfed by the risk of a length-revealing oracle.
- Whether to expose `iter_token_patterns()` (mirrors Phase 018's `iter_known_prefixes()`) for downstream test reuse — default YES, costs ~6 LOC.
- Whether the startup self-check is a function the daemon orchestrator calls explicitly (`assert_redactor_attached()`) or a module-import side effect. Default: explicit function — side-effect imports collide with the `tests/auth/conftest.py` `reset_defaults()` pattern.

### Deferred Ideas (OUT OF SCOPE)

None — discuss phase was skipped, no deferrals captured.

(Implicit deferrals from PROJECT.md / PITFALLS.md scope discipline:
- OS-keychain integration (P2-4 — covered by AUTH vault Arc, not this phase)
- Encryption-at-rest of `auth.json` (deferred per Phase 018 user_constraints)
- OpenTelemetry trace attribute redaction (STACK.md: "OpenTelemetry deferred to v2")
- /proc / memory-dump / source-code-constant scrubbing — out of scope, see §Security Threat Model)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-10 | Root-logger token redactor strips `sk-ant-*`, `sk-*`, `ya29.*`, etc. from every log record | §Standard Stack pins `structlog>=25.1` (already in `pyproject.toml`); §Architecture Patterns gives the canonical `shared_processors` + `ProcessorFormatter` wiring that catches structlog event-dict values AND stdlib `logging.getLogger()` records (third-party libs); §Code Examples §1 provides the compiled-at-import regex set spanning all 8 token shape families pulled from `.state-inputs/claude-oauth.md` + `state_core.auth.providers.api_key._REGISTRY`; §Code Examples §2 gives the recursive `_walk_value()` function that mutates strings inside nested dicts / lists / tuples / exception `repr()`; §Code Examples §3 gives `assert_redactor_attached()` startup self-check that the daemon orchestrator calls before `migrate()` / `reconciler.start()`; §Validation Architecture enumerates 24 REDACT-NN rows covering every token shape × every wiring point × the failure-to-attach mode + a hypothesis property test row. |

</phase_requirements>

## Summary

Phase 020 is the second defense layer for the P0-14 secret-leak pitfall. Layer 1 (already shipped in Phases 011–018) is **per-call-site discipline**: every auth provider deliberately omits secret bytes from structlog event-dicts (`store.py`, `errors.py`, `api_key.py`, etc. all carry "Phase 020 redactor is layer 2" comments). Layer 2 is this phase: a single processor at the root of the structlog chain that turns every secret-shaped substring into `[REDACTED]` regardless of whether the caller remembered to slice it out.

The architectural shape is fully determined by structlog's official "stdlib + structlog universal coverage" pattern: a `shared_processors` list installed both into `structlog.configure(processors=...)` AND into `ProcessorFormatter(foreign_pre_chain=...)`, ensuring the redactor sees both `state_core.*` event-dicts (structlog-native) and `httpx`/`urllib3`/`asyncio`/etc. records (stdlib `logging.getLogger()` callers). The redactor walks every value in the event-dict — strings, nested dicts, lists, tuples, exception `repr()` — and applies a compiled regex set against each.

The non-trivial research deliverable is the **token-shape regex set**. Eight families cover everything currently in scope: Anthropic OAuth access (`sk-ant-oat-…`), Anthropic OAuth refresh (`sk-ant-rt-…` / opaque), Anthropic API keys (`sk-ant-api03-…`), generic OpenAI-shape (`sk-…` ≥ 20 chars to dodge false positives like `sk-2`), Google OAuth (`ya29.…`), Google refresh (`1//…`), GitHub Copilot device-code tokens (`gho_…` / `ghu_…` / `ghs_…` / `ghp_…`), and Bearer-prefixed values in HTTP header dumps. The compiled set is sourced byte-for-byte from `.state-inputs/claude-oauth.md` (Anthropic), `src/state_core/auth/providers/google_gemini.py:456` (Google), `src/state_core/auth/providers/api_key.py::_REGISTRY` (12 plain-key prefixes), and the upstream GitHub token-prefix announcement (gho/ghu/ghs/ghp).

The startup self-check is a five-line discipline: emit a known secret-shaped string through `structlog.get_logger("state_core.observability.redactor.selftest")`, capture the rendered output via `structlog.testing.capture_logs`, assert the secret bytes do not appear. If the assertion fails, raise a fatal `RedactorNotAttached` error before `migrate()` / `reconciler.start()` run. The daemon orchestrator (`src/state_daemon/orchestrator.py::startup`) is the right call site — Step 0, before the existing Step 1 "repair aggregate sequences."

**Primary recommendation:** Implement `state_core.observability.redactor` as a single ~250 LOC file containing (1) the 8-family compiled regex set frozen at module-import time, (2) `redact_processor(logger, method_name, event_dict)` that recursively walks values and substitutes, (3) `install(extra_processors=())` that idempotently inserts the redactor at position 0 of the structlog chain AND attaches a `ProcessorFormatter` to the stdlib root logger using the shared-processors pattern, (4) `assert_redactor_attached()` self-check that fails fatally if redaction is bypassable. Wire `install()` + `assert_redactor_attached()` into `src/state_daemon/orchestrator.py::startup` as Step 0 (before repair). Test via a single ~400 LOC `tests/test_redactor.py` covering the 24 REDACT-NN rows enumerated in §Validation Architecture, plus a `tests/test_observability_import_graph.py` that asserts `state_core.observability.*` does not import `state_build.*` / `state_teach.*`. No `pytest-httpx` or `freezegun` needed; one `hypothesis` strategy fuzzes secret-shaped strings.

## Standard Stack

### Core (already pinned in `pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `structlog` | **≥25.1** (pyproject:23) | Logging stack; processor chain is the redaction insertion point | Project-wide convention; STACK.md §Observability commits to it; every `state_core.*` module already imports it |
| `re` (stdlib) | 3.12 built-in | Compiled regex set for token shapes | Stdlib; deterministic; no per-call compile when patterns are module-level constants |
| `logging` (stdlib) | 3.12 built-in | Stdlib root logger that `httpx` / `litellm` / `pygit2` / `aiosqlite` write into | Required for universal coverage — third-party libs do NOT use structlog |

### Supporting (already pinned for tests)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `structlog.testing.capture_logs` | bundled with structlog≥25.1 | In-test capture of rendered log output | Every REDACT-NN row that asserts "rendered output does not contain SECRET" |
| `hypothesis` | ≥6.120 (pyproject:30) | Property-based fuzzing of secret-shaped strings | REDACT-24 row only — fuzz the regex set against generated `sk-ant-oat-[A-Za-z0-9_-]{40,200}`, etc., assert post-redactor output never contains the input |
| `pytest-mock` | ≥3.14 (pyproject:32) | Mock the orchestrator path for the `assert_redactor_attached()` failure-mode row | One row (REDACT-21) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| structlog processor | stdlib `logging.Filter` subclass attached to root logger | REJECTED. structlog event-dicts are constructed BEFORE the stdlib formatter runs — a stdlib-side filter would only see the post-rendered string, not the structured `event_dict["access_token"] = "sk-ant-oat-..."` value. Project-wide PROJECT.md cardinal rule "structlog is the logging stack" + STACK.md "Observability Arc is load-bearing" both reject this path. |
| structlog processor | OpenTelemetry log-record processor / span attribute redactor | REJECTED. STACK.md §Observability defers OTel to v2. Adding an OTel dep for redaction reverses that decision. |
| Compile-at-import regex set | `regex` package (third-party) | REJECTED. `regex` adds a new dep for features (atomic groups, possessive quantifiers) we don't need; stdlib `re` covers all 8 token-shape patterns. |
| `[REDACTED]` placeholder | length-preserving `***...***` | REJECTED. Length is itself a secret-leak channel ("the redacted token has 56 chars → it's an `sk-ant-oat-…`"). Also: `[REDACTED]` is greppable, length-preserved redaction is not. |
| One redactor module | Per-provider redactors (one in each `auth/providers/*.py`) | REJECTED. P0-14 prevention text is explicit: "Apply at the root logger — not per call site." Per-call-site is layer 1 (already done); root-logger is layer 2 (this phase). |

**No new pyproject.toml dependencies required.** Phase 020 ships entirely against existing pins.

## Architecture Patterns

### Recommended Project Structure

```
src/state_core/
├── observability/                  # NEW package — Phase 020 introduces it
│   ├── __init__.py
│   └── redactor.py                 # the only module this phase ships
└── auth/                           # existing — consumed by redactor for prefix list
    └── providers/
        └── api_key.py              # exposes iter_known_prefixes()

src/state_daemon/
└── orchestrator.py                 # MODIFIED — adds Step 0: install() + assert_redactor_attached()

tests/
├── test_redactor.py                # NEW — REDACT-01..24 rows
└── test_observability_import_graph.py   # NEW — mode-isolation lint
```

**Mode-isolation rule:** `state_core.observability.*` may import: stdlib (`re`, `logging`, `typing`), `structlog`, and `state_core.auth.providers.api_key` (for `iter_known_prefixes`). It MUST NOT import `state_build.*` or `state_teach.*`. Enforced by `test_observability_import_graph.py` (mirrors `tests/auth/test_import_graph.py` pattern).

### Pattern 1: Compile-at-import regex set

**What:** Eight `re.Pattern` objects compiled at module load, frozen in a `_PATTERNS: tuple[re.Pattern, ...]` constant. No runtime compile.
**When to use:** Every redaction call. The hot path is "every log record" — re-compiling per call would be observable in benchmarks.
**Example:** see §Code Examples §1.

### Pattern 2: Recursive value walker

**What:** `_walk_value(v)` dispatches on type — `str` → apply patterns; `dict` → recurse over `.values()`; `list`/`tuple` → recurse element-wise; `Exception` → recurse on `str(v)`; everything else → return as-is. Returns a new structure (immutable substitution).
**When to use:** The processor function's body. structlog event-dicts can carry arbitrarily nested Pydantic models, exception objects (under `event_dict["exception"]` when `format_exc_info` runs), and HTTP-header dicts.
**Example:** see §Code Examples §2.

### Pattern 3: Shared-processors universal coverage

**What:** A single `shared_processors: list[structlog.types.Processor]` list passed to BOTH `structlog.configure(processors=shared_processors + [renderer])` AND `structlog.stdlib.ProcessorFormatter(foreign_pre_chain=shared_processors, processors=[remove_processors_meta, renderer])`. The redactor lives in `shared_processors`, position 0 (first thing that runs, before any other processor can render to a string).
**When to use:** `install()`. This is the structlog-canonical pattern for "single redactor over both structlog and stdlib loggers" (verified against structlog ≥25.1 stdlib-integration docs).
**Example:** see §Code Examples §4.

### Pattern 4: Idempotent install + startup self-check

**What:** `install()` is callable multiple times without duplicating the redactor (re-installation is a no-op). `assert_redactor_attached()` is a separate function that emits a known secret through the root logger, captures rendered output via `capture_logs`, and raises `RedactorNotAttached` if the secret survives.
**When to use:** Daemon startup, before any other initialization. The orchestrator runs `install() → assert_redactor_attached()` as Step 0, then proceeds to Step 1 (repair) only if the assertion passes.
**Example:** see §Code Examples §3 + §5.

### Anti-Patterns to Avoid

- **stdlib `logging.Filter`-only redaction.** Misses structlog event-dict values entirely. P0-14 specifically calls out "Apply at the root logger" — that has to mean BOTH the stdlib root logger AND structlog's processor chain. Use the shared-processors pattern (Pattern 3).
- **Per-call-site `redact()` helpers.** Already covered by layer 1; phase 020 is layer 2. Adding more per-call-site discipline would make the layered defense weaker, not stronger, by lulling future callers into "I called `redact()` so it's fine" complacency.
- **Length-preserving placeholders.** Reveals token-family by length. Use literal `[REDACTED]`.
- **Non-greedy match without anchors.** A bare `sk-` regex matches `sk-` in `sk-foundation` (a hypothetical product name); anchor token-shape patterns to whitespace / quote / EOL boundaries with `(?<!\w)` look-behinds.
- **Recompile per call.** Phase 020 sees every log record; per-call `re.compile` is a JIT'd loop tax. Module-level constants only.
- **Side-effect-on-import `install()`.** Collides with `tests/auth/conftest.py`'s `reset_defaults()` fixture (which Phases 011–018 lean on for `capture_logs` semantics). `install()` MUST be an explicit function call, not a module-import side effect.
- **Logging the redaction itself.** A "redactor fired N times" log line in production would create a side-channel ("redaction count went up after that auth call → there were credentials in scope"). No instrumentation of the redactor's own behavior in production paths.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| stdlib + structlog unified processor chain | A custom `LogRecord` interceptor that calls structlog manually | `structlog.stdlib.ProcessorFormatter` + `foreign_pre_chain` (the documented canonical pattern) | structlog ≥25.1 already solves this; rolling your own re-implements the bridge incorrectly (misses `extra={}` kwargs, race conditions on `LogRecord.getMessage()`, etc.) |
| In-test capture of rendered output | A custom `io.StringIO` handler attached to root | `structlog.testing.capture_logs` (already used in `tests/auth/test_api_key.py:191`) | Repo convention; integrates with the existing `tests/auth/conftest.py::_isolate_structlog_for_auth_tests` fixture |
| Token-shape patterns | Hand-typed regex strings scattered across the redactor | Module-level `_PATTERNS` tuple compiled once at import + `iter_token_patterns()` accessor for tests | Mirrors Phase 018's `iter_known_prefixes()` discipline; keeps the regex surface auditable in one grep-visible location |
| Recursive event-dict walker | A `json.dumps` round-trip that redacts the serialized string | Type-dispatching `_walk_value()` (Pattern 2) | `json.dumps` would lose Pydantic models / Exception subclasses (the renderer downstream may want them); also `json.dumps(event_dict)` raises on non-JSON values, breaking the very logging path it's protecting |

**Key insight:** The structlog ecosystem already gives us all four primitives we need (processor signature, ProcessorFormatter bridge, capture_logs harness, `wrap_for_formatter`). The redactor is ~80 lines of glue + a regex table; everything else is borrowed from structlog ≥25.1.

## Common Pitfalls

### Pitfall 1: Redactor installed but bypassed by stdlib loggers
**What goes wrong:** `httpx` (and via litellm, the entire provider routing surface) emits `DEBUG` records like `request: POST https://api.anthropic.com/... headers={'Authorization': 'Bearer sk-ant-oat-XXXXX', ...}`. If the redactor only lives in `structlog.configure(processors=...)` and NOT in `ProcessorFormatter.foreign_pre_chain`, those records flow through the stdlib root handler unredacted.
**Why it happens:** structlog processors run only on logs originating from `structlog.get_logger()`. Third-party libraries use `logging.getLogger(__name__)`. Without ProcessorFormatter wiring, those two paths never converge.
**How to avoid:** The shared-processors pattern (Pattern 3 / §Code Examples §4) — same processor list passed to BOTH `structlog.configure()` AND `ProcessorFormatter(foreign_pre_chain=...)`. `install()` MUST do both.
**Warning signs:** REDACT-12, REDACT-13, REDACT-14 (stdlib `httpx.DEBUG` synthetic record rows) fail. `grep "Bearer sk-ant-oat" ~/.state/logs/*` returns hits in development.
**Source:** structlog ≥25.1 stdlib-integration docs (§Standard Library Logging) — verified via WebFetch 2026-04-30.

### Pitfall 2: Daemon starts but redactor silently absent (P0-14 root cause)
**What goes wrong:** A future refactor accidentally removes the `install()` call from `src/state_daemon/orchestrator.py::startup`, or moves it after the first log line; tokens leak silently into `~/.state/logs/*.jsonl` for weeks before someone runs `grep`.
**Why it happens:** structlog has no built-in "is this processor in the chain?" assertion; absent affirmative verification, the failure is silent.
**How to avoid:** Mandatory `assert_redactor_attached()` self-check in Step 0 of orchestrator startup. Self-check emits a synthetic `[REDACT-SELFCHECK] sk-ant-oat-canary-{uuid4}` string through both `structlog.get_logger()` AND `logging.getLogger("redactor.selftest")`, captures both, asserts `"sk-ant-oat-canary"` does not appear. On failure, raise `RedactorNotAttached` before `migrate()` runs.
**Warning signs:** REDACT-21 ("self-check fails fast when install() not called") row asserts the orchestrator refuses to advance to Step 1.
**Source:** PITFALLS.md P0-14 Prevention clause — verbatim "Refuse to start daemon if the redactor isn't attached."

### Pitfall 3: Refresh tokens missed because they don't match `sk-ant-*`
**What goes wrong:** Anthropic OAuth refresh tokens are NOT shaped like `sk-ant-rt-*` — claude-oauth.md and the live response from the token endpoint return opaque strings (no documented prefix). A regex set built only against access-token shapes lets refresh tokens through.
**Why it happens:** Refresh-token shape is undocumented and varies between providers. Google's refresh tokens start with `1//` (verified at `src/state_core/auth/providers/google_gemini.py:456`); Anthropic's are opaque; Antigravity and Copilot are also opaque.
**How to avoid:** Two complementary defenses. (a) Match-by-key-context: when a `dict` value lives under any key in `_SECRET_KEYS = {"refresh", "refresh_token", "access", "access_token", "token", "api_key", "authorization"}`, redact the entire value regardless of shape. (b) Match-by-shape: cover the 8 token-shape patterns for redundancy when secrets land in free-form strings (e.g., HTTP request bodies). Both are required; neither alone is sufficient.
**Warning signs:** REDACT-04 (Anthropic refresh — opaque) and REDACT-08 (Antigravity refresh — opaque) rows fail if only shape-matching is implemented.
**Source:** `src/state_core/auth/providers/anthropic.py:454` `isOAuthToken()` only sniffs `sk-ant-oat` (access-token prefix); refresh tokens carry no prefix. Cross-checked against `tests/auth/conftest.py::oauth_cred` fixture which uses `"rt-test-..."` as a placeholder, NOT a vendor format.

### Pitfall 4: Bearer headers get split across log records
**What goes wrong:** httpx renders headers as `{'Authorization': 'Bearer sk-ant-oat-XXX'}`. A regex anchored to start-of-string would miss this. A regex without space-tolerance would miss `Bearer  sk-ant-oat-XXX` (double-space). A regex without quote-tolerance would miss `'Authorization': 'Bearer "sk-ant-oat-XXX"'`.
**Why it happens:** Different formatters (Python `repr`, JSON, structlog ConsoleRenderer) emit different surrounding context; the redactor cannot rely on any specific framing.
**How to avoid:** Patterns include `(?<!\w)` look-behinds and `(?!\w)` look-aheads, NOT `^/$` anchors. The `Bearer\s+` prefix in the bearer-shape pattern matches one-or-more whitespace; a separate "value under Authorization key" rule (Pitfall 3a) catches the unprefixed case.
**Warning signs:** REDACT-09 ("Bearer with double space"), REDACT-10 ("Bearer in HTTP-header dict via httpx debug") fail.
**Source:** httpx ≥0.28.1 default `DEBUG` log format (verified via WebSearch 2025–2026 reports of httpx token-leak reports).

### Pitfall 5: Exception `repr()` carries plaintext token
**What goes wrong:** A provider raises `httpx.HTTPStatusError("Bad request: {'error': 'invalid token sk-ant-oat-XXX'}")`. structlog's `format_exc_info` processor calls `traceback.format_exception(...)` which includes `str(exc)` in the rendered string — verbatim, including the token bytes.
**Why it happens:** The exception is a `str`-able object whose `__str__` includes the token. The redactor's `_walk_value` must recurse into `event_dict["exception"]` and `event_dict["exc_info"]` and apply patterns to the rendered traceback string.
**How to avoid:** `_walk_value(v: BaseException)` returns `_redact_string(str(v))` — apply patterns to the exception's rendered representation. Also: install the redactor BEFORE structlog's `format_exc_info` processor in the chain, so the exception is already a redacted string by the time `format_exc_info` would render it. Position 0 in `shared_processors` covers both ordering concerns.
**Warning signs:** REDACT-15 ("token in raised exception message") and REDACT-16 ("token in exception traceback chain") fail.
**Source:** structlog ≥25.1 `format_exc_info` processor docs — exception-rendering happens after the redactor when the redactor is at position 0.

### Pitfall 6: Generic `sk-` matches non-secret strings
**What goes wrong:** `sk-` is a tiny prefix; matching `sk-\S+` would redact `sk-foundation` (hypothetical product name), `sk-learn` (mistype of scikit-learn), `Sk-2-3-4` (skill ID). Over-redaction is annoying but not security-breaking — except when it redacts diagnostic information needed to debug a non-auth bug.
**Why it happens:** Token shape requirements are necessarily fuzzy at the edges. The OpenAI generic `sk-` keys have variable suffix length (older keys: 48 chars; project keys: longer); a permissive regex over-matches.
**How to avoid:** Require minimum length (≥20 alphanum/underscore/dash chars after `sk-`) — verified against `src/state_core/auth/providers/api_key.py::_REGISTRY` where every `sk-` provider's keys are observed ≥40 chars. Combine with `(?<!\w)` look-behind to reject `Xsk-foo`. Run REDACT-22 ("does not redact `sk-foundation`, `Bearer xyz`, `sk-2`") as a negative test.
**Warning signs:** REDACT-22 fails (negative test catches over-redaction); developer complaints about diagnostic info being redacted.
**Source:** `src/state_core/auth/providers/api_key.py::_REGISTRY` survey of 12 vendors — minimum observed token length is `gsk_…` (Groq) at 56 chars. 20-char floor is conservative.

### Pitfall 7: JSON renderer round-trip leaks secrets
**What goes wrong:** Some structlog setups serialize the event-dict to JSON via `structlog.processors.JSONRenderer` (production daemon mode). If the redactor walks values BEFORE the renderer but the renderer happens to escape some token-shape-breaking character (`&` for `&`, double-encoded backslashes), a downstream string-match grep might miss leaked tokens that survived as JSON-escaped sequences.
**Why it happens:** None of the 8 token shapes contain JSON-escapable characters in their canonical form (Anthropic/Google/GitHub all use `[A-Za-z0-9_-]`), so this is a low-risk pitfall — but flagged here because future shapes might.
**How to avoid:** REDACT-17 row: assert the JSONRenderer-rendered output (final stage) does not contain any of the 8 token shape regexes. This is a belt-and-braces check on top of the per-value redaction.
**Warning signs:** REDACT-17 fails for a future token shape.
**Source:** structlog ≥25.1 JSONRenderer + `orjson` integration (`pyproject.toml:13`) — `orjson` is JSON-byte-clean for ASCII alphanumeric inputs.

### Pitfall 8: Test config bleed-through (Phases 011–018 conftest pattern)
**What goes wrong:** `tests/test_cli.py:26` configures structlog with a `CRITICAL`-level filtering wrapper at module-import time. `tests/auth/conftest.py:13` then `reset_defaults()` for auth tests. Phase 020's redactor MUST coexist with both: in the daemon, `install()` must be called once; in tests, `capture_logs()` must see redacted output.
**Why it happens:** Existing test infra was built before the redactor existed. Re-running tests after `install()` runs may alter structlog global state in ways that confuse downstream test ordering.
**How to avoid:** `install()` is idempotent (re-installation is a no-op); `tests/test_redactor.py` calls `install()` in a fixture that snapshots `structlog.get_config()` first and restores on teardown — exactly mirroring `tests/auth/conftest.py::_isolate_structlog_for_auth_tests`. REDACT-23 verifies the no-op semantics.
**Warning signs:** Random test failures in `tests/test_cli.py` or `tests/auth/*.py` after Phase 020 lands; CRITICAL-filter behavior changes.
**Source:** `tests/auth/conftest.py:13-32` (the existing reset/restore pattern) + `tests/test_cli.py:26` (the CRITICAL filter).

## Code Examples

### §1 — Compiled regex set at module-import time

```python
# Source: state_core/observability/redactor.py
# Token-shape provenance:
#   sk-ant-oat-       → .state-inputs/claude-oauth.md (Anthropic OAuth access)
#   sk-ant-api03-     → src/state_core/auth/providers/api_key.py::_REGISTRY (Phase 018)
#   sk-…              → src/state_core/auth/providers/api_key.py::_REGISTRY (OpenAI)
#   ya29.…            → src/state_core/auth/providers/google_gemini.py:456 (Google access)
#   1//…              → src/state_core/auth/providers/google_gemini.py:456 (Google refresh)
#   gho_/ghu_/ghs_/ghp_  → upstream GitHub token-prefix announcement (2021)
#   Bearer …          → RFC 6750 §2.1
from __future__ import annotations

import re

# Token shapes — anchored with (?<!\w) so we don't match inside identifiers.
# Minimum length 20 chars on the value to dodge false positives like "sk-2".
_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<!\w)sk-ant-oat-[A-Za-z0-9_-]{20,}(?!\w)"),       # Anthropic OAuth access
    re.compile(r"(?<!\w)sk-ant-api03-[A-Za-z0-9_-]{20,}(?!\w)"),     # Anthropic API key
    re.compile(r"(?<!\w)sk-or-v1-[A-Za-z0-9_-]{20,}(?!\w)"),         # OpenRouter
    re.compile(r"(?<!\w)sk-(?:proj|svcacct|None)-[A-Za-z0-9_-]{20,}(?!\w)"),  # OpenAI prefixed
    re.compile(r"(?<!\w)sk-[A-Za-z0-9]{40,}(?!\w)"),                 # OpenAI generic ≥40 chars
    re.compile(r"(?<!\w)ya29\.[A-Za-z0-9_-]{20,}(?!\w)"),            # Google OAuth access
    re.compile(r"(?<!\w)1//[A-Za-z0-9_-]{20,}(?!\w)"),               # Google OAuth refresh
    re.compile(r"(?<!\w)(?:gho|ghu|ghs|ghp)_[A-Za-z0-9]{20,}(?!\w)"), # GitHub Copilot device-code
    re.compile(r"(?<!\w)gsk_[A-Za-z0-9]{20,}(?!\w)"),                # Groq
    re.compile(r"(?<!\w)xai-[A-Za-z0-9]{20,}(?!\w)"),                # xAI / Grok
    re.compile(r"(?<!\w)esecret_[A-Za-z0-9]{20,}(?!\w)"),            # DeepSeek
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._\-/+=]{20,}"),             # RFC 6750 Bearer header
)

# Keys whose VALUES are always secrets regardless of shape — covers refresh
# tokens, opaque tokens, and future shapes we haven't enumerated yet.
_SECRET_KEYS: frozenset[str] = frozenset({
    "access", "access_token",
    "refresh", "refresh_token",
    "token", "api_key", "apikey",
    "authorization", "x-api-key", "x-goog-api-key",
    "client_secret", "code_verifier",
})

REDACTED = "[REDACTED]"


def iter_token_patterns() -> tuple[re.Pattern[str], ...]:
    """Phase 020 public surface — Phase 018 mirrors this pattern via
    iter_known_prefixes(). Tests use it to enumerate-and-assert."""
    return _PATTERNS
```

### §2 — Recursive value walker (the processor body)

```python
# Source: state_core/observability/redactor.py (continued)
from typing import Any
import structlog

def _redact_string(s: str) -> str:
    """Apply every pattern; replace match with [REDACTED]."""
    for pat in _PATTERNS:
        s = pat.sub(REDACTED, s)
    return s


def _walk_value(v: Any, key_hint: str | None = None) -> Any:
    """Recursive type-dispatch redactor.

    key_hint: when v lives under a dict key in _SECRET_KEYS, redact the
    whole value regardless of shape (covers opaque refresh tokens).
    """
    if key_hint and key_hint.lower() in _SECRET_KEYS and v not in (None, ""):
        return REDACTED
    if isinstance(v, str):
        return _redact_string(v)
    if isinstance(v, dict):
        return {k: _walk_value(item, key_hint=str(k)) for k, item in v.items()}
    if isinstance(v, (list, tuple)):
        walked = [_walk_value(item) for item in v]
        return type(v)(walked)
    if isinstance(v, BaseException):
        # Preserve the exception type for downstream renderers; redact str(v).
        # New instance avoids mutating the live exception object.
        return type(v)(_redact_string(str(v)))
    return v


def redact_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """structlog processor — position 0 in the chain.

    Walks every value in event_dict and substitutes secret-shaped
    substrings with [REDACTED]. Preserves event_dict keys verbatim
    (key names are public; values may be private)."""
    return {k: _walk_value(v, key_hint=str(k)) for k, v in event_dict.items()}
```

### §3 — Daemon startup self-check

```python
# Source: state_core/observability/redactor.py (continued)
import logging
import uuid

import structlog
from structlog.testing import capture_logs


class RedactorNotAttached(RuntimeError):
    """Fatal — daemon refuses to start. P0-14 / AUTH-10 defense layer 2."""


def assert_redactor_attached() -> None:
    """Emit a known secret-shaped string through BOTH structlog and stdlib
    loggers; assert the rendered output does not contain the secret bytes.

    Must be called by src/state_daemon/orchestrator.py::startup as Step 0,
    before migrate() / reconciler.start(). Raises RedactorNotAttached on
    any failure mode (processor missing, ProcessorFormatter not attached,
    foreign_pre_chain missing, etc.).
    """
    canary_id = uuid.uuid4().hex
    canary = f"sk-ant-oat-canary-{canary_id}-{'X' * 32}"

    # Path 1: structlog-native caller
    with capture_logs() as cap:
        structlog.get_logger("state_core.observability.redactor.selftest").info(
            "selfcheck", token=canary, msg=f"value is {canary}"
        )
    if any(canary in str(record) for record in cap):
        raise RedactorNotAttached(
            "structlog redactor failed to redact canary token; refusing to start"
        )

    # Path 2: stdlib caller (httpx / litellm / pygit2 path)
    stdlib_logger = logging.getLogger("state_core.observability.redactor.selftest.stdlib")
    # Implementation note: capturing stdlib output requires a memory handler;
    # the actual check uses logging.getLogger().handlers[0]'s formatter to
    # render the canary record and string-search the result.
    rendered = _render_stdlib_record_with_root_formatter(stdlib_logger, canary)
    if canary in rendered:
        raise RedactorNotAttached(
            "stdlib root-logger redactor failed to redact canary token; "
            "ProcessorFormatter.foreign_pre_chain not wired"
        )
```

### §4 — install() — shared-processors universal coverage

```python
# Source: state_core/observability/redactor.py (continued)
import logging
import structlog


_INSTALLED = False  # idempotency guard


def install() -> None:
    """Idempotently install the redactor at position 0 of the structlog
    chain AND attach a ProcessorFormatter to the stdlib root logger so
    third-party libraries (httpx, litellm, pygit2, aiosqlite, ...) flow
    through the same redactor.

    Pattern source: structlog ≥25.1 stdlib-integration docs (canonical
    'shared_processors' wiring for unified coverage).
    """
    global _INSTALLED
    if _INSTALLED:
        return

    shared_processors: list[structlog.types.Processor] = [
        redact_processor,                       # ← layer-2 secret defense, position 0
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,    # exception → string AFTER redactor
    ]

    # structlog-native loggers
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # stdlib loggers (httpx / litellm / etc.)
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,    # ← redactor runs here too
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(serializer=_json_serializer),
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    # Idempotency: clear any previous redactor handler before adding.
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    _INSTALLED = True
```

### §5 — Orchestrator wiring (Step 0)

```python
# Source: src/state_daemon/orchestrator.py — MODIFIED
from state_core.observability.redactor import install, assert_redactor_attached

async def startup() -> None:
    # Step 0 (NEW): install + verify redactor BEFORE any other I/O.
    install()
    assert_redactor_attached()      # raises RedactorNotAttached → daemon dies

    # Step 1: existing — repair aggregate sequences
    store = SqliteEventStore()
    log.info("startup: repairing aggregate sequences")
    repairs = await store.run_repair_now()
    # ... rest unchanged
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| stdlib `logging.Filter` subclass with regex `.sub()` on `record.msg` | structlog `Processor` callable on event-dict + ProcessorFormatter bridge to stdlib | structlog 21.x (2021) made stdlib bridge stable; stable through 25.1 | Single processor covers BOTH structlog and stdlib loggers; pre-renderer position means exception/traceback redaction works without separate hook |
| Per-call-site secret-slicing (auth providers manually elide tokens before logging) | Layered: per-call-site (layer 1, already done) + root-logger redactor (layer 2, this phase) | P0-14 documented 2026-04 | Defense-in-depth; future regressions in auth code don't leak secrets |
| `logging.basicConfig(level=DEBUG)` for development | `install()` (which sets level + redactor + formatter atomically) | Phase 020 | Developers can no longer accidentally set DEBUG without redaction; "the redactor is the logging config" |

**Deprecated/outdated:**
- **Manual `re.sub()` in every log call** — replaced by structlog processor at position 0.
- **Splunk/Datadog server-side redaction** — too late; the secret already left the host. Server-side scrubbing is a complement, not a substitute, for client-side redaction.
- **`logging.Formatter` subclass that overrides `format()`** — only sees the rendered string; misses structlog event-dict structure.

## Open Questions

1. **Should the canary self-check log lines be excluded from the daemon's permanent log?**
   - What we know: `assert_redactor_attached()` emits one structlog record + one stdlib record on every startup. They contain the literal string `[REDACT-SELFCHECK]` post-redaction (the secret canary itself is replaced with `[REDACTED]`).
   - What's unclear: whether a fresh-install user sees these lines as noise on first startup, or whether they're useful operational evidence ("redactor verified at boot").
   - Recommendation: leave them in; they cost ~2 lines per daemon boot and provide audit-trail evidence of redactor-attached. Mark with `event="redactor_selfcheck_passed"` so a future log filter can suppress if pain materializes.

2. **Does `litellm`'s internal logging use `logging.getLogger()` or a custom logger?**
   - What we know: STACK.md commits to `litellm>=1.80.0`; litellm has internal verbose-mode logging that dumps request bodies (including `Authorization` headers) at `DEBUG`.
   - What's unclear: whether litellm uses a single named logger (we can target `logging.getLogger("LiteLLM")` specifically) or scatters logs across many loggers (must rely on root-logger coverage).
   - Recommendation: REDACT-13 row uses `logging.getLogger("LiteLLM").debug(...)` with a Bearer-prefixed payload, asserts redaction. If litellm bypasses stdlib root logger entirely (uses print() or direct sys.stderr.write), file an upstream issue and add a litellm-specific patch.

3. **Should the redactor handle bytes-typed values?**
   - What we know: `httpx` request bodies can be `bytes` for binary uploads; `pygit2` can emit `bytes` log messages.
   - What's unclear: whether any auth-secret-shaped bytes flow through structlog/stdlib loggers in practice.
   - Recommendation: defer. `_walk_value` returns `bytes` unchanged today; if a regression test discovers a bytes-shaped leak, add a `bytes` branch. Out of scope for AUTH-10's "every log record" wording (records are str-typed by default).

## Validation Architecture

> Per `.planning/config.json::workflow.nyquist_validation: true`, this section is REQUIRED.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest>=8.4.0` + `pytest-asyncio>=1.3.0` (already in `pyproject.toml:29-30`) |
| Config file | `pyproject.toml::[tool.pytest.ini_options]` (testpaths=["tests"], asyncio_mode="auto") |
| Quick run command | `pytest tests/test_redactor.py tests/test_observability_import_graph.py -x` |
| Full suite command | `pytest -m "not e2e and not provider_parity and not slow" -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-10 / REDACT-01 | Anthropic OAuth access token (`sk-ant-oat-…`) redacted in event_dict value | unit | `pytest tests/test_redactor.py::test_redacts_anthropic_oat -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-02 | Anthropic API key (`sk-ant-api03-…`) redacted | unit | `pytest tests/test_redactor.py::test_redacts_anthropic_api_key -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-03 | Generic OpenAI key (`sk-` ≥40 chars) redacted | unit | `pytest tests/test_redactor.py::test_redacts_openai_generic -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-04 | Anthropic OAuth refresh (opaque, no prefix) redacted via key-context (`refresh_token` key) | unit | `pytest tests/test_redactor.py::test_redacts_opaque_refresh_by_key -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-05 | Google OAuth access (`ya29.…`) redacted | unit | `pytest tests/test_redactor.py::test_redacts_google_ya29 -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-06 | Google OAuth refresh (`1//…`) redacted | unit | `pytest tests/test_redactor.py::test_redacts_google_refresh_1slash -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-07 | GitHub Copilot device-code token (`gho_…` / `ghu_…` / `ghs_…` / `ghp_…`) redacted | unit | `pytest tests/test_redactor.py::test_redacts_github_copilot -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-08 | Antigravity / Copilot opaque refresh redacted via key-context | unit | `pytest tests/test_redactor.py::test_redacts_opaque_antigravity_refresh -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-09 | Bearer header (`Bearer sk-ant-oat-…`) redacted including double-space variant | unit | `pytest tests/test_redactor.py::test_redacts_bearer_header_variants -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-10 | HTTP-header dict with `Authorization` key redacted via key-context | unit | `pytest tests/test_redactor.py::test_redacts_authorization_header_dict -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-11 | Nested-dict secret (token inside `{"request": {"headers": {"x-api-key": "sk-ant-api03-..."}}}`) redacted | unit | `pytest tests/test_redactor.py::test_redacts_nested_dict_secret -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-12 | Secret in `list` value redacted (e.g. `event_dict["tokens_seen"] = ["sk-ant-oat-...", ...]`) | unit | `pytest tests/test_redactor.py::test_redacts_list_value -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-13 | Secret in stdlib `httpx`-style record (`logging.getLogger("httpx").debug(..., extra={"headers": {...}})`) redacted via ProcessorFormatter foreign_pre_chain | integration | `pytest tests/test_redactor.py::test_redacts_stdlib_httpx_record -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-14 | Secret in stdlib `litellm`-style record (`logging.getLogger("LiteLLM").debug("payload: ...")`) redacted | integration | `pytest tests/test_redactor.py::test_redacts_stdlib_litellm_record -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-15 | Secret in raised exception's `str()` redacted | unit | `pytest tests/test_redactor.py::test_redacts_exception_message -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-16 | Secret in exception traceback chain (`exc_info=True` path through `format_exc_info`) redacted | unit | `pytest tests/test_redactor.py::test_redacts_traceback_chain -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-17 | Final JSONRenderer output does not contain any token-shape regex match (belt-and-braces) | integration | `pytest tests/test_redactor.py::test_jsonrenderer_output_clean -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-18 | `redact_processor` is at position 0 in `structlog.get_config()["processors"]` after `install()` | structural | `pytest tests/test_redactor.py::test_processor_at_position_zero -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-19 | `ProcessorFormatter` is attached to the stdlib root logger after `install()`, with `redact_processor` in its `foreign_pre_chain` | structural | `pytest tests/test_redactor.py::test_processorformatter_attached_to_root -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-20 | `assert_redactor_attached()` returns successfully when `install()` has run | unit | `pytest tests/test_redactor.py::test_selfcheck_passes_when_installed -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-21 | `assert_redactor_attached()` raises `RedactorNotAttached` when `install()` has NOT run (resets defaults first); orchestrator startup aborts before Step 1 | unit | `pytest tests/test_redactor.py::test_selfcheck_fails_when_not_installed -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-22 | Negative test: `sk-foundation`, `sk-2`, `Bearer xyz` (length < 20), `Skill-1234` are NOT redacted | unit | `pytest tests/test_redactor.py::test_negative_no_overredaction -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-23 | `install()` is idempotent — calling it twice does not duplicate handlers or processors | unit | `pytest tests/test_redactor.py::test_install_idempotent -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-24 | Hypothesis property test: for any string generated by the secret-shaped strategy, `_redact_string(s)` does not contain the input | property | `pytest tests/test_redactor.py::test_hypothesis_secrets_never_survive -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-25 | Mode-isolation lint: `state_core.observability.*` does NOT import `state_build.*` or `state_teach.*` | structural | `pytest tests/test_observability_import_graph.py::test_no_mode_imports -x` | ❌ Wave 0 |
| AUTH-10 / REDACT-26 | Existing `tests/auth/conftest.py::_isolate_structlog_for_auth_tests` fixture still works after `install()` lands (regression check) | regression | `pytest tests/auth/ -q` | ✅ (existing) |

### Token-shape × wiring-point coverage matrix

(How REDACT-01..17 cover the cartesian product.)

| Token shape \ wiring point | event_dict str value | nested dict | list/tuple | exception repr | stdlib record | JSON renderer output |
|---|---|---|---|---|---|---|
| sk-ant-oat- (Anthropic access) | REDACT-01 | REDACT-11 | REDACT-12 | REDACT-15 | REDACT-13 | REDACT-17 |
| sk-ant-api03- (Anthropic API) | REDACT-02 | REDACT-11 | — | — | — | REDACT-17 |
| sk-… (OpenAI generic) | REDACT-03 | — | — | — | REDACT-14 | REDACT-17 |
| Anthropic refresh (opaque) | REDACT-04 (key-context) | — | — | — | — | REDACT-17 |
| ya29.… (Google access) | REDACT-05 | — | — | — | — | — |
| 1//… (Google refresh) | REDACT-06 | — | — | — | — | — |
| gho_/ghu_/ghs_/ghp_ (GitHub) | REDACT-07 | — | — | — | — | — |
| Antigravity/Copilot opaque | REDACT-08 (key-context) | — | — | — | — | — |
| Bearer header value | REDACT-09 | REDACT-10 (key-context) | — | — | REDACT-13 | REDACT-17 |

### Structural assertions (REDACT-18..21, 25)

| Assertion | What it verifies | Failure mode |
|---|---|---|
| Processor at position 0 (REDACT-18) | `structlog.get_config()["processors"][0] is redact_processor` | A future processor inserted before the redactor could render the event-dict to a string before redaction runs. |
| ProcessorFormatter on stdlib root (REDACT-19) | At least one handler on `logging.getLogger()` has a `ProcessorFormatter` whose `foreign_pre_chain` contains `redact_processor` | stdlib loggers (httpx/litellm) bypass the redactor entirely. |
| Self-check passes when installed (REDACT-20) | `assert_redactor_attached()` returns None (no exception) after `install()` | (Smoke test for the green path.) |
| Self-check fails when not installed (REDACT-21) | `RedactorNotAttached` raised when `structlog.reset_defaults()` is called BEFORE `assert_redactor_attached()` | The daemon-refusal contract is enforceable. |
| Mode-isolation (REDACT-25) | `state_core.observability.*` source files do not contain `import state_build` or `from state_teach` | Cardinal rule violation; would require a CI-level revert. |

### Hypothesis property test (REDACT-24)

```python
# Source: tests/test_redactor.py
from hypothesis import given, strategies as st
from state_core.observability.redactor import _redact_string, REDACTED, iter_token_patterns

@given(
    prefix=st.sampled_from([
        "sk-ant-oat-", "sk-ant-api03-", "sk-or-v1-",
        "ya29.", "1//", "gho_", "ghu_", "ghs_", "ghp_",
        "gsk_", "xai-", "esecret_",
    ]),
    body=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
        min_size=20, max_size=200,
    ),
    surround=st.text(min_size=0, max_size=20),
)
def test_hypothesis_secrets_never_survive(prefix, body, surround):
    """For ANY generated secret-shaped string in any surrounding text,
    the redactor's output must not contain the secret bytes verbatim."""
    secret = prefix + body
    blob = f"{surround}{secret}{surround}"
    out = _redact_string(blob)
    assert secret not in out, f"redactor missed: {secret} survived as {out!r}"
    assert REDACTED in out, f"redactor produced no [REDACTED] marker for {blob!r}"
```

### Sampling Rate
- **Per task commit:** `pytest tests/test_redactor.py tests/test_observability_import_graph.py -x`
- **Per wave merge:** `pytest -m "not e2e and not provider_parity and not slow" -q` (full Python suite minus e2e)
- **Phase gate:** Full suite green + `pytest tests/test_redactor.py --hypothesis-show-statistics` shows ≥1000 hypothesis draws on REDACT-24

### Wave 0 Gaps
- [ ] `tests/test_redactor.py` — covers REDACT-01..24 (NEW; no existing file)
- [ ] `tests/test_observability_import_graph.py` — covers REDACT-25 (NEW; mirrors `tests/auth/test_import_graph.py` pattern)
- [ ] `src/state_core/observability/__init__.py` — empty package marker (NEW)
- [ ] `src/state_core/observability/redactor.py` — module body (NEW; ~250 LOC)
- [ ] `src/state_daemon/orchestrator.py` — Step 0 wiring (MODIFIED; ~5 LOC inserted)

Framework install: not needed — `structlog`, `pytest`, `pytest-asyncio`, `hypothesis`, `pytest-mock` already pinned in `pyproject.toml`.

## Security Threat Model Inputs

### Threats this phase MITIGATES (in scope)

| # | Threat | Mitigation | Residual risk |
|---|--------|------------|---------------|
| T-020-1 | Plaintext token written to **stderr** in dev mode (developer reads logs casually) | `redact_processor` runs before any renderer; ConsoleRenderer / StreamHandler output passes through | LOW — covered by REDACT-01..09, 13, 14 |
| T-020-2 | Plaintext token written to **JSON log file** on disk (`~/.state/logs/*.jsonl` shared in bug reports) | Same processor chain emits redacted output; JSONRenderer is the last stage and never sees raw secrets | LOW — covered by REDACT-17 |
| T-020-3 | Plaintext token in **structlog event-dict value** (per-call-site discipline regressed in some auth provider after refactor) | Layer-2 root-logger redactor catches the leak even if layer-1 (per-call-site) is broken | LOW — covered by REDACT-01..08, 11, 12 |
| T-020-4 | Plaintext token in **exception message** (provider raises `RuntimeError(f"bad token {tok}")`) | `_walk_value` recurses into `BaseException`; `format_exc_info` runs after the redactor in the chain | LOW — covered by REDACT-15, 16 |
| T-020-5 | Plaintext token in **third-party library log record** (httpx/litellm/pygit2 DEBUG output) | `ProcessorFormatter.foreign_pre_chain` ensures stdlib records pass through the same redactor | MEDIUM — covered by REDACT-13, 14; depends on third-party libs using `logging.getLogger()` (not raw `print()`) |
| T-020-6 | Plaintext token in **JSON-embedded value** (e.g. `event_dict["request_body"] = '{"token": "sk-ant-oat-..."}'`) | Pattern-shape regex catches the embedded value as a string (not a structured dict, but the bytes match) | LOW — covered by REDACT-17 + the pattern set |
| T-020-7 | **Daemon starts with redactor not attached** (silent regression) | `assert_redactor_attached()` self-check refuses to advance past Step 0 | LOW — covered by REDACT-21 |
| T-020-8 | **Future token shape added** to a new auth provider, not added to the regex set | `iter_token_patterns()` is a single grep-visible surface; new providers' phase-research MUST update it (mirror Phase 018's `iter_known_prefixes()` extension protocol) | MEDIUM — process control, not technical control |

### Threats this phase does NOT mitigate (out of scope)

| # | Threat | Why out of scope | Where addressed |
|---|--------|------------------|-----------------|
| OOS-1 | **Memory dumps** (`/proc/$pid/mem`, core dumps) containing live token bytes | The token must exist in memory to be USED — redactor cannot prevent that. OS-level mitigation only. | Future hardening Arc (encryption-at-rest in `auth.json` is a related v2+ Arc; OS-level core-dump prevention is platform-specific). |
| OOS-2 | **Source-code constants** (test fixtures, hard-coded test tokens like `"sk-ant-oat-test-token-do-not-redact-in-test-only"` in `tests/auth/conftest.py:48`) | Source code is by definition pre-redactor; tests deliberately use shape-collision strings. | git pre-commit hook (separate phase / out of v2 milestone scope). |
| OOS-3 | **Token bytes in `auth.json` on disk** | That's WHERE the token is supposed to live. The vault uses chmod 0600 (Phase 012) + filelock (Phase 013) + (future) encryption-at-rest. | Phases 011/012/013 (already shipped) + future encryption Arc. |
| OOS-4 | **Token bytes in `events.sqlite`** | Domain events SHOULD NOT contain tokens (per CLAUDE.md: "Auth credentials live in `.state/auth.json`"); redactor doesn't run inside the event-store writer path. | Per-call-site discipline (already in place); event-schema `pydantic` validators flag fields named like secrets. |
| OOS-5 | **Server-side observability platforms** (Splunk, Datadog) inheriting un-redacted logs from a misconfigured forwarder | Phase 020 is client-side; we cannot reach into a downstream Splunk indexer. | Operational discipline + server-side scrubbing rules (out of project scope). |
| OOS-6 | **OS unified-log capture** (macOS `log stream`, Linux `journalctl`) of `stderr` written before `install()` runs | `install()` runs at Step 0 of `startup()`, but `python -X importtime` or early `print()` calls before `startup()` could leak. | Discipline: NO logging before `startup()` Step 0. CI grep for `print(` in `src/state_core/`. |
| OOS-7 | **Backups of `~/.state/logs/`** to cloud storage (Dropbox/iCloud) | Logs are already redacted before write; backup is moot for the in-scope token shapes. | P2-4 §PITFALLS.md (existing pitfall, not Phase 020's responsibility). |
| OOS-8 | **Side-channel analysis** (length of `[REDACTED]` blocks reveals token family) | Mitigated by uniform replacement; not perfectly mitigated (a token-context dict still reveals "auth happened"). | Acceptable residual; out of P0-14 scope. |

### Phase 020 ship criteria (security)

The phase is shippable when:
1. All 24 REDACT-NN positive rows pass (REDACT-01..17, 24).
2. All 5 structural rows pass (REDACT-18..21, 25).
3. All 2 negative rows pass (REDACT-22 over-redaction; REDACT-23 idempotency).
4. Manual smoke test: run `state-daemon` with `STATE_LOG_LEVEL=DEBUG`, exercise an auth refresh, `grep -E "sk-ant-oat-|sk-ant-rt-|ya29\.|1//|gho_|Bearer\s+\S{20}" ~/.state/logs/*.jsonl` returns ZERO hits.
5. PITFALLS.md P0-14 marked as "regression test committed: REDACT-01..24 in `tests/test_redactor.py`" (raises the `P0 pitfall regression tests committed` counter in `STATE.md` from 1/16 to 2/16).

## Sources

### Primary (HIGH confidence)

- `/Users/tmac/Projects/state/.planning/research/PITFALLS.md` lines 21, 185-191, 846 — P0-14 definition + Observability-Arc load-bearing claim
- `/Users/tmac/Projects/state/.planning/research/STACK.md` lines 405-426 — `structlog>=25.1` pin + observability strategy
- `/Users/tmac/Projects/state/pyproject.toml` lines 22-23, 30-32 — already-pinned `structlog>=25.1`, `hypothesis>=6.120`, `pytest-mock>=3.14`
- `/Users/tmac/Projects/state/.state-inputs/claude-oauth.md` lines 9, 42 — `sk-ant-oat-` shape (authoritative for Anthropic OAuth)
- `/Users/tmac/Projects/state/src/state_core/auth/providers/api_key.py` lines 137-237, 444-456 — `_REGISTRY` (12 plain-key prefixes) + `iter_known_prefixes()` precedent for `iter_token_patterns()` mirror
- `/Users/tmac/Projects/state/src/state_core/auth/providers/google_gemini.py` line 456 — `ya29.` access prefix + `1//` refresh prefix (authoritative for Google)
- `/Users/tmac/Projects/state/src/state_core/auth/providers/anthropic.py` line 454 — `sk-ant-oat` access-token prefix sniffer (`isOAuthToken`)
- `/Users/tmac/Projects/state/src/state_core/auth/errors.py` lines 10-11 — "Phase 020's structlog redactor is the second defense layer" anchor
- `/Users/tmac/Projects/state/src/state_daemon/orchestrator.py` lines 14-47 — existing startup sequence (Step 1 repair → Step 2 migrate → Step 3 reconciler); insertion point for Step 0
- `/Users/tmac/Projects/state/tests/auth/conftest.py` lines 13-32 — existing structlog reset/restore fixture pattern (Pitfall 8)
- `/Users/tmac/Projects/state/tests/auth/test_api_key.py` line 21, 191 — `from structlog.testing import capture_logs` precedent

### Secondary (MEDIUM-HIGH confidence — official docs verified live 2026-04-30)

- [structlog ≥25.1 — Processors](https://www.structlog.org/en/stable/processors.html) — processor signature `(logger, method_name, event_dict)`, return-value contract, "explicitly allowed to modify the event_dict parameter"
- [structlog ≥25.1 — Standard Library](https://www.structlog.org/en/stable/standard-library.html) — canonical `shared_processors` + `ProcessorFormatter` + `foreign_pre_chain` pattern for unified coverage; `wrap_for_formatter` semantics; `remove_processors_meta` invariant
- [PEP 8 / RFC 6750 §2.1](https://datatracker.ietf.org/doc/html/rfc6750) — Bearer header format (`Bearer SP <credential>`)
- GitHub token-prefix announcement (2021) — `gho_` / `ghu_` / `ghs_` / `ghp_` documented at `https://github.blog/2021-04-05-behind-githubs-new-authentication-token-formats/` — verified via existing prefix usage in CONTEXT.md ¶specifics

### Tertiary (LOW confidence — flagged for validation)

- Antigravity refresh-token shape: opaque (no published prefix) — verified via `src/state_core/auth/providers/antigravity.py` (which does not assert any prefix); FLAGGED for confirmation when Phase 016 verifier captures live response.
- GitHub Copilot device-code refresh-token shape: opaque (treated by `gho_…` access tokens) — refresh-token shape NOT verified live; flagged as "key-context redaction is the only defense" — REDACT-08 row covers it.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library already pinned in `pyproject.toml`; no new deps.
- Architecture (structlog `shared_processors` pattern): HIGH (official docs verified live) — but MEDIUM applied risk because the repo's existing structlog config (in tests only) does NOT yet exercise the ProcessorFormatter bridge; daemon never previously configured root logger.
- Token-shape regex set: HIGH for the 8 shapes pulled from PROJECT-internal sources (claude-oauth.md, api_key._REGISTRY, google_gemini); MEDIUM for the opaque-refresh path (we rely on key-context redaction, which depends on disciplined dict-key naming in callers).
- Pitfalls: HIGH for Pitfalls 1, 2, 5, 8 (sourced from official docs + existing repo state); MEDIUM for Pitfalls 3, 4, 6 (synthesized from cross-referencing api_key._REGISTRY + httpx default DEBUG format).
- Validation Architecture: HIGH — every row has a concrete file path + automated command; matches existing repo convention (`tests/auth/test_*.py` parametrized rows).
- Security threat model: HIGH for in-scope T-020-1..8 (each maps to a REDACT-NN row); HIGH for out-of-scope OOS-1..8 (explicit "where addressed" reference for each).

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30 days — structlog API is stable; only watch for `structlog.stdlib.ProcessorFormatter` API drift if structlog cuts a 26.x release).
