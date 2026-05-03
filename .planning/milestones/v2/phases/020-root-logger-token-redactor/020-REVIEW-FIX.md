---
phase: 020-root-logger-token-redactor
fixed_at: 2026-04-30T00:00:00Z
review_path: .planning/milestones/v2/phases/020-root-logger-token-redactor/020-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
deferred: 6
status: all_fixed
---

# Phase 020 — Code Review Fix Report

**Fixed at:** 2026-04-30
**Source review:** `.planning/milestones/v2/phases/020-root-logger-token-redactor/020-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (MUST-FIX + SHOULD-FIX): 5
- Fixed: 5
- Skipped: 0
- Deferred (WORTH-KNOWING, per scope rule): 6

## Fixed Issues

### MF-01: `_walk_value`'s BaseException fallback returns the live unredacted exception

**Files modified:** `src/state_core/observability/redactor.py`, `tests/test_redactor.py`
**Commit:** `0e428d6`
**Applied fix:** Replaced `return v` in the `except TypeError` branch with `return RuntimeError(redacted_msg)`. Multi-arg / signature-mismatched exception subclasses (httpx.HTTPStatusError, subprocess.CalledProcessError, custom exceptions with structured kwargs) now flow through a redacted-string surrogate rather than the live exception object. Loses class identity for the multi-arg path but guarantees no token-byte leak through downstream `str(exc)` / `format_exc_info` renderers (T-020-4 / RESEARCH §Pitfall 5).

Added regression test `test_redacts_multi_arg_exception` in `tests/test_redactor.py` exercising an httpx.HTTPStatusError-shaped subclass (`MultiArgExc(request, response)`). Asserts the canary is absent from both the walked event-dict and from `str(walked_exception)`.

### SF-01: `_PATTERNS` lacks `(?<!\w)` look-behind anchors — over-redacts identifier-prefixed shapes

**Files modified:** `src/state_core/observability/redactor.py`, `tests/test_redactor.py`
**Commit:** `122d4f6`
**Applied fix:** Wrapped each of the 11 prefix-shaped patterns with `(?<!\w)` look-behind and `(?!\w)` look-ahead, per RESEARCH §Code Examples §1. Bearer pattern unchanged (its `\s+` already provides a left boundary; "Bearer" embedded in a word is implausible).

Re-widened the hypothesis strategy alphabet:
- Anthropic / Google / OpenRouter prefixes: body uses `[A-Za-z0-9_-]` (matches RESEARCH §1).
- GitHub Copilot / Groq / xAI / DeepSeek / OpenAI generic: body stays alnum-only (their regex bodies are alnum-only).
- Bumped `max_examples` from 200 → 1000 (Plan 04 phase-gate target).
- Surround alphabet excludes `\w`-class characters and `-` so generated surround can never form a token-extending boundary.

Hypothesis 1000-draw run with the broadened alphabet passes — confirmed no over-redaction at word boundaries.

### SF-02: `assert_redactor_attached()` uses `capture_logs(processors=...)` requiring structlog ≥25.5

**Files modified:** `src/state_core/observability/redactor.py`
**Commit:** `b241b3a`
**Applied fix:** Chose option (b) per the user's preference (no dep bump). Rewrote Path 1 to invoke `redact_processor` directly on a synthetic canary event_dict and string-search the result. Removed `from structlog.testing import capture_logs` (no longer used).

`pyproject.toml` floor stays at `structlog>=25.1`. The Path 1.5 identity check (`configured[0] is not redact_processor`) still verifies wiring; the new direct-invocation step verifies the function actually redacts. Strictly equivalent to the prior `capture_logs()` path for the self-check's purpose, with zero version-resolution risk on 25.1..25.4.

### SF-03: `install()` lacks handler-deduplication when `_INSTALLED` is reset

**Files modified:** `src/state_core/observability/redactor.py`, `tests/test_redactor.py`
**Commit:** `4c38208`
**Applied fix:** Before adding a new `StreamHandler` with the redactor `ProcessorFormatter`, scan `logging.getLogger().handlers` for an existing `ProcessorFormatter` whose `foreign_pre_chain` already contains `redact_processor`. If one is present, skip handler attachment. `structlog.configure()` is naturally idempotent (replaces global config), so no change needed for the structlog half.

Added regression test `test_install_self_heals_under_installed_reset` exercising the reset-and-reinstall path: `install()` → reset `_INSTALLED = False` → `install()` again. Asserts handler count unchanged AND exactly one redactor-bearing ProcessorFormatter handler remains.

### SF-04: Mixed `src.state_core` vs `state_core` imports in orchestrator

**Files modified:** `src/state_daemon/orchestrator.py`
**Commit:** `a955608`
**Applied fix:** Dropped the `src.` prefix on all 5 imports in `src/state_daemon/orchestrator.py`. Verified per the spec:

```
$ grep -n "from state_core\.\|from src\.state_core\." src/state_daemon/orchestrator.py
7:from state_core.events import SqliteEventStore
8:from state_core.migrations import migrate
9:from state_core.observability import assert_redactor_attached, install
10:from state_core.reconciler import StartupReconciler
11:from state_core.sync_mirror import SyncEventMirror
```

All 5 use `from state_core.*`. Verified `from state_daemon.orchestrator import startup` resolves under the uv-managed venv with no `src.*` module-identity ambiguity.

NOTE: 4 other files in the repo (`src/state_cli/main.py`, `src/state_core/reconciler.py`, `src/state_core/events.py`, `src/state_core/sync_mirror.py`, `src/state_core/projector.py`, `src/state_core/migrations.py`) still use `from src.state_core...`. Those are out-of-scope for Phase 020 and are flagged for the cross-cutting cleanup phase the reviewer mentioned. Phase 020's orchestrator is now consistent with the observability package and tests it cooperates with.

## Deferred Items (WORTH-KNOWING, out of scope per fix-scope policy)

The 6 WK items below are documented as deferred per the user's instruction to skip WORTH-KNOWING unless trivial. None block landing; all are documentation, future-hardening, or low-probability operational concerns.

- **WK-01:** `_walk_value` raises `RecursionError` on cyclic structures. Documented deferral in module docstring (lines 26-29). Cycle detection (`id(v)` visited-set) is a future hardening — none of the current event-dict producers (Pydantic v2, structlog) emit cycles.
- **WK-02:** `_redact_string` order discipline (specific-before-generic) is documented but not test-enforced. A structural test could assert `index(sk-ant-oat-) < index(sk-[A-Za-z0-9]{40,})`. Defer until a regression occurs.
- **WK-03:** `_walk_value` uses `type(v)(walked)` for tuples, which fails for `NamedTuple` subclasses. None of the current callers emit NamedTuples in event-dicts.
- **WK-04:** `assert_redactor_attached()` docstring says "the canary" (singular) but generates a fresh UUID per call. Docstring clarity only.
- **WK-05:** `install()` calls `root.setLevel(logging.DEBUG)` unconditionally. Documented as intentional (lines 286-289). Operator runbook concern.
- **WK-06:** `assert_redactor_attached()` Path 2 silently treats "every ProcessorFormatter raised on render" identically to "no ProcessorFormatter found." Error-message precision concern; doesn't affect correctness.

These remain candidates for a future cleanup phase; documenting here so they aren't lost.

## Verification Evidence

### Test suite (per the user's required gate)

```
$ uv run pytest tests/test_redactor.py tests/test_observability_import_graph.py tests/auth/ -q
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
.....................................................................s   [100%]
357 passed, 1 skipped in 47.15s
```

- `tests/test_redactor.py`: 32 tests pass (28 original REDACT-* + 4 structural extras + 2 new regression tests for MF-01 and SF-03).
- `tests/test_observability_import_graph.py`: 3 tests pass (REDACT-25 mode-isolation lint + import-allow-list + init-exists).
- `tests/auth/`: 322 tests pass + 1 skip (auth provider regression suite — confirms the redactor changes did not break the existing auth-side log calls).

### Hypothesis 1000-draw harness (Plan 04 phase-gate target)

`test_hypothesis_secrets_never_survive` runs at `max_examples=1000` (bumped from 200 in SF-01). Uses the per-prefix body alphabet matrix:

| Prefix | Body alphabet | Source |
|---|---|---|
| `sk-ant-oat-` | `[A-Za-z0-9_-]` | RESEARCH §1 |
| `sk-ant-api03-` | `[A-Za-z0-9_-]` | RESEARCH §1 |
| `sk-or-v1-` | `[A-Za-z0-9_-]` | RESEARCH §1 |
| `ya29.` | `[A-Za-z0-9_-]` | RESEARCH §1 |
| `1//` | `[A-Za-z0-9_-]` | RESEARCH §1 |
| `gho_` / `ghu_` / `ghs_` / `ghp_` | `[A-Za-z0-9]` | upstream regex |
| `gsk_` / `xai-` / `esecret_` | `[A-Za-z0-9]` | RESEARCH §1 |

1000-draw run completes in < 0.5s with no falsifying examples. Confirms no over-redaction at word boundaries (SF-01) and no under-redaction across the broadened alphabet.

### Direct verification commands (run during fix application)

```
$ python3 -c "import ast; ast.parse(open('src/state_core/observability/redactor.py').read())"
(no output — syntax OK)

$ python3 -c "import ast; ast.parse(open('tests/test_redactor.py').read())"
(no output — syntax OK)

$ uv run python3 -c "from state_daemon.orchestrator import startup; print(startup)"
<function startup at 0x100fcdd00>
```

### Commits applied

```
a955608 fix(020): SF-04 standardize orchestrator imports on state_core (drop src. prefix)
4c38208 fix(020): SF-03 install() self-heals under _INSTALLED reset
b241b3a fix(020): SF-02 invoke redact_processor directly in self-check (drop capture_logs)
122d4f6 fix(020): SF-01 add (?<!\w)/(?!\w) boundary anchors to prefix patterns
0e428d6 fix(020): MF-01 redact multi-arg BaseException via RuntimeError surrogate
```

5 atomic commits, each scoped to one finding. All used `--no-verify` per the parallel-executor protocol.

---

_Fixed: 2026-04-30_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
