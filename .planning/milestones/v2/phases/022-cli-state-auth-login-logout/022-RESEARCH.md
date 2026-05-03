# Phase 022: CLI `state auth login | logout | status` + AUTH-13 Goldens — Research

**Researched:** 2026-05-01  
**Domain:** Typer CLI + Rich rendering + pytest-httpx golden-file testing  
**Confidence:** HIGH

## Summary

Phase 022 ships a standalone Typer/Rich CLI for credential management (`state auth login <provider>`, `state auth logout <provider>`, `state auth status`) and a captured-header regression test suite (AUTH-13) covering P0-1..P0-8 + P0-13. The phase sits atop completed Phases 011–021 auth primitives and is an **integration phase** (no new OAuth/API-key implementations, no new auth methods). 

The research identifies three strategic assets: (1) a thin reusable ops layer (`state_core.auth.cli_ops`) that future TUI surfaces can import directly, (2) a pytest-httpx + JSON-golden-file regression pattern matching Phase 014's mitmproxy capture discipline, and (3) a Rich Table renderer with deterministic ordering and optional styling. **Phase 022 is feasible as a single 4-plan phase** — Typer commands are thin shells (Plan 1–2 total ~150 LOC), ops layer consolidates 6 scattered provider methods into 3 orchestrating functions (~250 LOC), golden-file harness is modular (~300 LOC infrastructure + 200 LOC per provider), and P0 regression tests are named behavioral assertions (~400 LOC). Total delivery: ~2000 LOC across 5 files.

**Primary recommendation:** Build `state_core.auth.cli_ops` first (reusable ops layer), then Typer commands as thin shells. Golden-file test infrastructure (pytest-httpx + JSON fixtures + `--update-goldens` flag) is self-contained; P0 regression suite is 9 separate test functions, each testing one pitfall per the locked list in CONTEXT.md.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CLI surface & verbs:**
- Trio only: `state auth login`, `state auth logout`, `state auth status`. No prune/refresh/list/import-opencode --force.
- Provider as positional arg, prompts when omitted. Alias table for normalization (claude→anthropic, gemini→google.gemini, antigravity→google.antigravity, copilot→github.copilot).
- Standalone CLI, filelock-coordinated. No daemon HTTP dependency.
- Provider name normalization via alias table. Unknown name → exit 64 with difflib.get_close_matches suggestion.

**Architectural seam:** Typer commands are thin shells over `state_core.auth.cli_ops` (placement TBD). The ops module exposes `login(provider_id, *, account_id=None, api_key=None, code_state=None, from_stdin=False) -> OAuthCredential | ApiKeyCredential`, `logout(provider_id, *, account_id=None, all_=False) -> int`, `status(*, provider_id=None) -> StatusReport`.

**Login UX:**
- Per-provider flows inherited as-is from existing implementations (Anthropic paste, Gemini loopback, Antigravity fixed-port, GitHub Copilot device-code, API keys getpass).
- Non-TTY login refuses (exit 64) unless --api-key/--code-state/--from-stdin supplied.
- Non-interactive flags: `--api-key <value>` (api-key providers only), `--code-state <code#state>` (Anthropic only), `--from-stdin` (provider-aware).
- Success message: "Logged in to <provider>: <account_label>" where account_label = extras["email_address"] or account_id or f"{prefix12}…".

**Logout UX:**
- Single-cred case: prompt for confirmation with --yes flag to skip.
- Multi-cred case: print indexed list, prompt for which to remove. Non-interactive without --account or --all is hard error (exit 64).
- `--account <id>` flag: matches against account_id, then email_address, then first-12 prefix.
- `--all` flag: wipes entire provider array.
- Audit: emit `auth.logged_out` domain event into .state/events.sqlite (dual-write to SyncEvent) per credential removed.

**Status output schema:**
- Row model: one row per credential.
- Default columns (5): `provider | type | account | expires | source`.
- Masking: never show token bytes by default. `--show-prefix` opt-in reveals first 12 chars.
- `--json` versioned envelope `state.auth.status/v1`.
- Filtering: `--provider <id>`, `--expired`. Sort: providers alphabetical; within provider, vault first, then opencode-import, then env; by expires_at ascending.
- Renderer: Rich Table for human, orjson for `--json`. `--no-color` respected.

**Exit-code policy:** 0/1/2/3/64/77/78/130 mapping (3 = StealthRejected distinct signal).

**AUTH-13 captured-header goldens:**
- Method: pytest-httpx + JSON golden files. Path layout: `tests/auth/golden/<provider>/<flow>.json`.
- Positive/negative allowlists of stealth-relevant headers + body-shape + URL invariants.
- P0 coverage: one named test per pitfall, all in `tests/auth/test_p0_regression.py`.
- Golden update flow: `--update-goldens` pytest CLI flag.

**Provider `_main()` argparse stubs — fate:**
- Keep all five stubs. Typer commands and `_main()` stubs both call into the same provider methods — two surfaces, one code-path.

**Daemon integration:** Phase 022 does not depend on a running daemon. All commands run in-process. Filelock serialises against any concurrent daemon refresh. `auth.logged_in` / `auth.logged_out` events are dual-written to .state/events.sqlite + SyncEvent regardless of daemon.

### Claude's Discretion

- Exact placement of the Typer sub-app (single file vs package).
- Exact placement of the reusable ops layer (filename/package structure).
- Exact alias table contents (minor api-key aliases beyond the locked four).
- Renderer details (Rich Table styling, color thresholds).
- Test fixture strategy for goldens.
- Whether `--update-goldens` is custom pytest_addoption or piggybacks on syrupy (recommend custom, no new dep).
- Exact event-schema field names for `auth.logged_in` / `auth.logged_out`.
- Whether `state auth status` queries env-var fallbacks and labels them `source: env` (recommend yes).

### Deferred Ideas (OUT OF SCOPE)

- `state auth import-opencode [--force]`
- `state auth prune --expired`
- `state auth refresh <provider>`
- `state auth providers list`
- opencode-plugin TUI modal
- Daemon HTTP/JSONRPC API for auth
- Live mitmproxy capture replay in CI
- `--update-goldens` automation in CI
- Bidirectional sync to opencode auth.json
- Windows path/mode handling beyond Phase 012 warn-and-skip
- Color-blind/no-color theming polish
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-12 | `state auth login \| logout \| status` CLI with interactive + non-interactive flows | Complete Typer sub-app infrastructure identified; 3 commands are thin shells over `state_core.auth.cli_ops` ops layer; all provider flows (Anthropic, Gemini, Antigravity, Copilot, 12 API keys) are pre-implemented in Phases 014–018 |
| AUTH-13 | Captured-header regression test suite (P0-1..P0-8 + P0-13) with pytest-httpx golden-file diffs | pytest-httpx already a dev dep; golden-file pattern established in Phase 014; custom `--update-goldens` flag via pytest_addoption; 9 tests map 1:1 to pitfall IDs in CONTEXT.md |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Typer | 0.15+ | Sync CLI framework on top of Click | Async-via-asyncio.run pattern established in src/state_cli/main.py; sub-app pattern (db_app, events_app) ready for reuse |
| Rich | 13.9+ | Table rendering + `--no-color` detection | Confirmed in pyproject.toml; Rich.Console is thread-safe and stateful; standard for modern Python CLIs |
| httpx | 0.28.1+ | Async HTTP (already in stack) | Inherited from auth providers; pytest-httpx mocking is dev dep |
| pydantic | 2.13.2+ | Credential models (Phase 011 base) | Inherited; `BaseModel.model_validate`, `Field(repr=False)` patterns established |
| orjson | 3.11.8+ | JSON serialization for `--json` output | Deterministic (OPT_SORT_KEYS) + performance; used by vault, events |
| structlog | 25.1+ | Logging with redactor (Phase 020) | Root logger redactor already wired; safe to log provider_ids, account_labels |
| filelock | 3.20.3+ | Cross-process coordination | Phase 013 already uses AsyncFileLock; CLI takes same lock as daemon refresh |
| python3-ulid | 3.0+ | Event ID generation | Already in use in events schema (Phase 001) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-httpx | 0.35+ | Mock httpx requests for golden-file tests | Installed as dev dep; httpx.mock fixture for capturing requests deterministically |
| pytest-asyncio | 1.3.0+ | Async test execution | Already in place; `asyncio_mode = "auto"` in pyproject.toml |
| freezegun | 1.5+ | Clock mocking for tests (optional) | P0-7 test (5-min expiry buffer) can use `time.time()` monkeypatch instead |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Rich Table | Click's tabulate or bare print | Rich is richer (ANSI colors, alignment) + already in the stack; uninstalling is a net loss of polish |
| Custom pytest flag | syrupy snapshot library | syrupy adds a new dependency; custom flag is ~20 LOC pytest_addoption boilerplate, zero deps |
| Separate pytest fixture per provider | One fixture factory + parametrize | Factory pattern is more flexible; data-driven golden load pattern is clearer with explicit per-provider JSON files |
| Async/await at CLI layer | await directly in Typer commands | Typer is sync-first; `asyncio.run()` wrapper is the idiomatic pattern (confirms src/state_cli/main.py) |

**Installation:**
```bash
# Already in pyproject.toml. Confirm:
pip3 install typer>=0.15 rich>=13.9

# Dev deps:
pip3 install pytest-httpx>=0.35
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── state_cli/
│   ├── __init__.py
│   ├── main.py           # app = typer.Typer(); db_app, events_app, auth_app registered here
│   └── auth.py           # (or auth/__init__.py if >200 LOC) — Typer sub-app commands
│
├── state_core/
│   └── auth/
│       ├── __init__.py
│       ├── base.py       # (existing) Credential, AuthMethod protocol
│       ├── cli_ops.py    # (new) login(), logout(), status() ops layer
│       ├── store.py      # (existing) AuthVault, save_vault, load_vault
│       ├── refresh.py    # (existing) refresh_credential, filelock
│       ├── loader.py     # (existing) load_credentials (vault + env)
│       ├── errors.py     # (existing) AuthError hierarchy + new AuthVaultPermissionError, etc.
│       ├── import_opencode.py  # (Phase 021)
│       ├── rotation.py   # (Phase 019)
│       ├── providers/
│       │   ├── anthropic.py     # (existing) + exports constants for golden tests
│       │   ├── google_gemini.py # (existing)
│       │   ├── antigravity.py   # (existing)
│       │   ├── github_copilot.py # (existing)
│       │   ├── api_key.py       # (existing) + _REGISTRY
│       │   └── oauth_common/
│       │       ├── pkce.py      # (existing)
│       │       └── loopback.py  # (existing)
│       └── schema.py    # (Phase 021) — event-schema definitions
│
└── state_daemon/ or state_worker/ or state_events/
    └── schema.py         # (or wherever events are defined) — add auth.logged_in/logged_out event types
```

**Why this layout:**
- `state_cli/auth.py` follows the sub-app pattern (mirrors `state_cli/db.py` concept if it existed).
- `state_core/auth/cli_ops.py` is strategically placed as a sibling to `base.py` / `store.py` / `refresh.py` — orchestration layer, not a provider. Future TUI modal imports `cli_ops` directly; CLI is secondary.
- Keeps mode isolation clean: `state_cli.auth` imports `state_core.auth.*` (one-way); `state_core.auth.cli_ops` imports `state_core.auth.{base, store, refresh, loader, providers, errors}` (no state_cli).

### Pattern 1: Typer Sub-App Wiring (Established)
**What:** Typer allows `app.add_typer(sub_app)` to register command groups.
**When to use:** Organizing related commands (login, logout, status all sit under `auth`).
**Example:**
```python
# src/state_cli/main.py
import typer
from state_cli.auth import auth_app

app = typer.Typer(name="state", help="state: agentic state-machine workflow engine")
app.add_typer(auth_app)

# src/state_cli/auth.py
import typer

auth_app = typer.Typer(name="auth", help="Manage authentication credentials")

@auth_app.command(name="login")
def login(
    provider: str = typer.Argument(None, help="Provider ID (e.g., anthropic, openai)"),
    api_key: str = typer.Option(None, "--api-key", help="Non-interactive: API key value"),
    code_state: str = typer.Option(None, "--code-state", help="Non-interactive: Anthropic code#state"),
    from_stdin: bool = typer.Option(False, "--from-stdin", help="Read credential from stdin"),
) -> None:
    """Log in to a provider's credentials."""
    # Call into state_core.auth.cli_ops.login(...)
    pass

# Matches the pattern from src/state_cli/main.py:16-20
```

### Pattern 2: Async-via-asyncio.run() in Sync Typer Commands
**What:** Typer commands are synchronous functions; calling async provider methods requires `asyncio.run()`.
**When to use:** Wrapping provider `login()` and `refresh()` methods.
**Example:**
```python
# Inside src/state_cli/auth.py
import asyncio
from state_core.auth.cli_ops import login as ops_login

@auth_app.command(name="login")
def login(...) -> None:
    try:
        cred = asyncio.run(ops_login(provider_id=provider, ...))
        typer.echo(f"Logged in to {provider_id}")
    except AuthError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
```

### Pattern 3: Credential Account-Label Fallback Chain
**What:** Render a human-friendly account label from three tiers of preference.
**When to use:** Any output that names the credential (login success msg, logout prompt, status table).
**Example:**
```python
def account_label(cred: Credential) -> str:
    """Return a human-friendly account label."""
    if isinstance(cred, OAuthCredential) and cred.extras.get("email_address"):
        return cred.extras["email_address"]
    if cred.account_id:
        return cred.account_id
    # Fallback: first 12 chars of the key/token (not shown by default in status)
    if isinstance(cred, OAuthCredential):
        return f"{cred.access[:12]}…"
    if isinstance(cred, ApiKeyCredential):
        return f"{cred.key[:12]}…"
    return "<unknown>"
```

### Pattern 4: Rich Table Rendering with Deterministic Ordering
**What:** Rich.Table renders columns; ordering is deterministic when credentials are pre-sorted.
**When to use:** `state auth status` human output.
**Example:**
```python
from rich.console import Console
from rich.table import Table

def render_status_table(report: StatusReport, no_color: bool = False) -> None:
    """Render StatusReport as a Rich table."""
    console = Console(no_color=no_color, force_terminal=not no_color)
    table = Table(title="Credentials")
    table.add_column("Provider", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Account")
    table.add_column("Expires", style=_expires_style(cred))  # amber/<5min, red/expired
    table.add_column("Source", style="dim")
    
    for row in report.rows:
        expires_str = _format_expires(row.expires_at, row.expires_in_seconds)
        table.add_row(
            row.provider_id,
            row.type,
            row.account_label,
            expires_str,
            row.source,
        )
    
    console.print(table)
```

### Anti-Patterns to Avoid
- **CLI commands calling provider methods directly:** Creates import cycles and breaks the ops-layer abstraction. Route through `state_core.auth.cli_ops` always.
- **Calling `asyncio.run()` multiple times per command:** Creates separate event loops; reuse a single `asyncio.run()` call wrapping the entire operation.
- **Storing credentials in memory across command invocations:** Each `state auth` invocation is isolated; re-read auth.json for each operation.
- **Bypassing filelock on CLI writes:** Always use `save_vault()` which respects the filelock contract. Daemon and CLI race safety depends on it.
- **Rendering secret material by default:** Never show full tokens, access prefixes, or counts in human output. `--json` can include `prefix12` (machine-readable); `--show-prefix` is the opt-in flag for human output.
- **Golden-file tests without isolation:** Golden fixtures must not depend on real network state, live credentials, or mitmproxy captures. Use pytest-httpx mocks exclusively.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Provider login/refresh flows | Custom OAuth/device-code state machines | Existing Phase 014–018 implementations | Phases 014–018 own the mitmproxy capture gate; reusing them feeds the P0 regression suite directly. Reimplementing breaks the contract. |
| Credential round-robin selection on 429 | In-process cache + TTL | Phase 019's `select_credential()` + filelock | Phase 019 persists rotation state across processes; hand-rolling loses consistency across daemon + CLI. |
| Event emission (logged_in/logged_out) | Bare print + manual dict | Existing `state_core.events.SqliteEventStore` + SyncEvent | Events are authoritative; audit trail must be dual-written to sqlite + SyncEvent per the v1 cardinal rule. Don't sidestep. |
| Token-shape sniffing (is this OAuth or API key?) | Custom prefix matching | Phase 018's `iter_known_prefixes()` + provider `is_token()` methods | The token sniffer is load-bearing (Phase 020's redactor uses it, rotation uses it, status output uses it). Maintain a single source of truth. |
| HTTP header capture for testing | Hand-rolled request inspection | pytest-httpx's httpx.mock fixture + JSON golden files | pytest-httpx is battle-tested; hand-rolled mocks miss subtleties (redirect handling, content-type encoding, auth-header parsing). |
| Vault file locking | `os.flock()` / `fcntl` on first call | Phase 013's `filelock.AsyncFileLock(timeout=10.0)` | Daemon and CLI must use the same lock; Phase 013 owns this contract. Reimplementing creates lost-update / thundering-herd bugs. |

**Key insight:** Phases 014–021 have already solved the hard problems (OAuth state machines, filelock, token redaction, vault atomicity). Phase 022 is **integration + CLI packaging**, not re-solving those problems.

---

## Common Pitfalls

### Pitfall 1: Async/Sync Impedance — Event Loop Nesting
**What goes wrong:** Calling `asyncio.run()` inside a command that's itself called from an async context causes `RuntimeError: asyncio.run() cannot be called from a running event loop`.
**Why it happens:** Typer commands are sync; provider `login()` is async. Wrapping it in `asyncio.run()` works in isolation, but if the Typer command is ever called from an async context (e.g., from the daemon's HTTP handler in a future phase), the nested loop fails.
**How to avoid:** Document that Phase 022's Typer CLI is **sync-only** (no async at the CLI layer). Future phases that call these ops from async contexts (daemon, TUI modal) should NOT use asyncio.run(); they should call the async methods directly with `await`. The ops layer is async-native; the Typer shell adds the asyncio.run() bridge. Mark ops functions clearly: `login()` is async, Typer `@auth_app.command` is sync.
**Warning signs:** Tests that run Typer commands inside async fixtures fail with "RuntimeError: asyncio.run()".

### Pitfall 2: Rich + Typer Interleaving
**What goes wrong:** `typer.echo()` and `Rich.Console.print()` mix in the output stream, causing buffering issues or color-code leakage.
**Why it happens:** Typer's `echo` writes to stdout directly; Rich uses its own Console state. Mixing them confuses the terminal state machine.
**How to avoid:** Pick ONE output mechanism per command: **use Rich.Console for all table/styled output, reserve `typer.echo()` for simple status messages only**. Better: wrap typer.echo as a Console wrapper. Maintain a single `console = Console(force_terminal=not no_color)` per command. Example: `console.print(f"Logged in as {label}")` instead of `typer.echo()`.
**Warning signs:** Output looks garbled; ANSI color codes bleed into the terminal after the command finishes.

### Pitfall 3: Golden-File Drift (Undetectable Upstream Changes)
**What goes wrong:** Anthropic updates the stealth-header list (e.g., new `anthropic-beta` flag). Golden files are committed, tests pass (comparing old-golden to new-capture both wrong). Users' inference fails silently.
**Why it happens:** Golden files are snapshots frozen at capture time. If the upstream API changes and re-capture isn't triggered, the golden becomes stale.
**How to avoid:** (1) Document that goldens MUST be re-captured on every Anthropic stealth-header update (mitmproxy gate, Phase 014 established). (2) Phase 022 does NOT automate golden-capture (mitigation: `--update-goldens` flag for manual review). (3) Add a comment in every golden JSON file with the capture date. (4) Periodically (e.g., quarterly) re-run mitmproxy capture against live Claude Code to detect drift. (5) CI gate: if the test fails on a golden mismatch, emit a loud warning pointing to .planning/research/PITFALLS.md P0-1..P0-3 (stealth-header ownership).
**Warning signs:** Tests pass locally but fail in CI after a provider updates their API.

### Pitfall 4: Non-TTY Login Hanging (Detection Failure)
**What goes wrong:** User runs `state auth login anthropic` in a non-TTY context (CI, ssh session, pipe) without --from-stdin. The getpass prompt waits forever (or times out).
**Why it happens:** `sys.stdin.isatty()` check was skipped, or the check is wrong (e.g., checking `sys.stdout.isatty()` instead).
**How to avoid:** (1) CLI MUST check `not sys.stdin.isatty()` BEFORE entering the provider's login flow. (2) If non-TTY and no non-interactive flag (--api-key, --code-state, --from-stdin), emit the error message and exit 64 immediately. (3) Test: run `echo "" | state auth login anthropic` (no flag) → verify exit code is 64, no hang.
**Warning signs:** CI job hangs at credential input; local runs work because the dev box has a TTY.

### Pitfall 5: `--account` Flag Ambiguous Match (Plural Targets)
**What goes wrong:** User has two credentials with overlapping identifiers: account_id "user" and account_id "user2" (or email_address "user@org.com" and prefix "user@or…"). `--account user` matches both; CLI can't decide.
**Why it happens:** The account-label fallback chain (email > account_id > prefix12) creates collisions when multiple tiers are in play or when email/id prefixes overlap.
**How to avoid:** (1) On ambiguous match, print the candidate rows and exit 64 with "Ambiguous --account <id>; matched N credentials: [list]". (2) Require exact match or longest unambiguous prefix. (3) Test: create a multi-cred vault with overlapping identifiers, run logout with --account, verify error message.
**Warning signs:** Logout silently removes the wrong credential; user complains they lost credentials.

### Pitfall 6: Filelock Timeout on Concurrent Daemon Refresh
**What goes wrong:** CLI and daemon both try to refresh at the same time. One acquires the lock for 10s; the other hits the timeout (exit 77) and returns a stale credential.
**Why it happens:** Phase 013's filelock has a hard 10s timeout. If the daemon's refresh HTTP call is slow, the CLI's acquire call times out.
**How to avoid:** (1) This is expected behavior (P0-6 defense). (2) CLI should retry once after a brief backoff. (3) Tests: monkeypatch the lock timeout to 0.1s, simulate concurrent acquire, verify RefreshLockTimeout propagates. (4) Document: "On lock timeout, exit 77 (EX_NOPERM). If you see this, the daemon may be stuck; restart with `systemctl restart state-daemon`."
**Warning signs:** `state auth status` occasionally exits 77; retrying the same command succeeds.

### Pitfall 7: Event Dual-Write Ordering (SQLite First)
**What goes wrong:** Code writes to SyncEvent first, then hits an error writing to SQLite. SyncEvent state is committed; SQLite is missing. Replay is broken.
**Why it happens:** Reversed ordering violates the v1 cardinal rule ("SQLite is authoritative").
**How to avoid:** (1) ALWAYS write to `.state/events.sqlite` FIRST via `SqliteEventStore.append()`. (2) Only after SQLite succeeds, call `sync_event.send()`. (3) If SQLite fails, propagate the exception; SyncEvent side-effect is skipped (acceptable — replay starts from SQLite). (4) Tests: mock `sync_event.send()` to raise an exception AFTER SQLite write; verify the event is still in SQLite.
**Warning signs:** Missing events in SQLite when SyncEvent shows them; replay doesn't reconstruct state.

### Pitfall 8: Provider Alias Normalization Case Sensitivity
**What goes wrong:** User types `state auth login ANTHROPIC` (uppercase). Alias table has `"claude": "anthropic"` but lookup fails because the code forgot to `.lower()`.
**Why it happens:** The alias table is lowercase; user input is not normalized.
**How to avoid:** (1) Always `.lower()` the input before alias lookup. (2) After alias lookup, normalize to the canonical provider_id. (3) If the (lowercased) input is not in the alias table, run `difflib.get_close_matches(input, alias_table.keys(), n=3)` to suggest corrections. (4) Tests: try uppercase, mixed case, misspellings (e.g., "anthrpic"); verify exit 64 with suggestion or success after normalization.
**Warning signs:** `state auth login ANTHROPIC` exits 64 "unknown provider" even though "anthropic" works.

### Pitfall 9: Status Expires Rendering (Timestamp vs. Delta)
**What goes wrong:** `state auth status` shows `expires: 1751234567.0` (raw epoch). User can't interpret it.
**Why it happens:** Rendering the raw timestamp instead of a human-friendly delta ("4h12m" or "EXPIRED").
**How to avoid:** (1) Define a helper `_format_expires_delta(expires_at: float, now: float = None) -> str` that returns `"EXPIRED" | "valid Xd Xh Xm" | "—"` (for API keys). (2) For expires soon (< 1h), use amber color; for < 5 min or expired, use red. (3) Test: set expires_at to past, future, within 1h, within 5min; verify rendered strings and colors.
**Warning signs:** User is confused about expiry status; they check `state auth status --json` to parse timestamps manually.

### Pitfall 10: Mode Isolation — Importing state_cli from state_core.auth
**What goes wrong:** `state_core.auth.cli_ops` imports `from state_cli ...`. Tests detect the reverse edge, import-graph test fails.
**Why it happens:** Copy-paste from Typer command code into the ops layer without checking import directionality.
**How to avoid:** (1) `state_core.auth.cli_ops` MUST NOT import `state_cli.*`. (2) Ops layer is pure orchestration of `state_core.auth.{base, store, refresh, loader, providers, errors}` only. (3) All Typer-specific code (click decorators, typer.echo, typer.Exit) lives in `state_cli.auth`, not `state_core.auth.cli_ops`. (4) Extend `tests/auth/test_import_graph.py` with a row: `test_cli_ops_no_state_cli_imports()` — parse `state_core/auth/cli_ops.py`, assert no `state_cli` substring.
**Warning signs:** Import-graph test fails: "state_core.auth.cli_ops imports state_cli.*".

---

## Code Examples

### Example 1: state_core.auth.cli_ops Function Signatures (Proposed)
**Source:** None yet; this is the design surface for Phase 022.

```python
# src/state_core/auth/cli_ops.py
"""Reusable auth operations layer (state_cli.auth commands call this).

No Typer/Click/state_cli imports. Async-native. Future TUI modal
(opencode-plugin) will import these functions directly.
"""

from dataclasses import dataclass
from typing import Optional
import asyncio

from state_core.auth.base import Credential, OAuthCredential, ApiKeyCredential
from state_core.auth.providers.anthropic import AnthropicAuth
from state_core.auth.providers.google_gemini import GoogleGeminiAuth
from state_core.auth.providers.antigravity import AntigravityAuth
from state_core.auth.providers.github_copilot import GitHubCopilotAuth
from state_core.auth.providers.api_key import get_api_key_auth
from state_core.auth.store import save_vault, load_vault, get_auth_json_path, ensure_initialized
from state_core.auth.loader import load_credentials
from state_core.auth.refresh import refresh_credential
from state_core.auth.errors import AuthError, NoCredentialsAvailableError
from state_core.events import SqliteEventStore

@dataclass
class StatusReport:
    """Response from status(). Human/JSON renderers consume this."""
    providers: list[dict]  # [{"id": "anthropic", "creds": [...]}, ...]
    summary: str  # "16 providers configured · 23 credentials · 2 expired"

async def login(
    provider_id: str,
    *,
    account_id: Optional[str] = None,
    api_key: Optional[str] = None,
    code_state: Optional[str] = None,
    from_stdin: bool = False,
) -> OAuthCredential | ApiKeyCredential:
    """Log in to a provider; return new credential.
    
    Args:
        provider_id: Canonical ID (e.g., "anthropic", "openai").
        account_id: (unused in Phase 022 — placeholder for multi-account in future)
        api_key: Non-interactive: pre-supplied API key (api-key providers only).
        code_state: Non-interactive: Anthropic "code#state" paste.
        from_stdin: Read credential from stdin (provider-aware grammar).
    
    Raises:
        AuthError: any login failure (network, user cancel, invalid paste, etc.)
        UnknownApiKeyProviderError: provider_id not recognized.
    """
    # Dispatch to provider; save via filelock; emit auth.logged_in event

async def logout(
    provider_id: str,
    *,
    account_id: Optional[str] = None,
    all_: bool = False,
    yes: bool = False,
) -> int:
    """Remove credential(s) for provider; return count removed.
    
    Raises:
        NoCredentialsAvailableError: no creds for this provider.
        ValueError: ambiguous --account match.
    """
    # Load vault; filter; prompt if needed; save; emit auth.logged_out event

async def status(
    *,
    provider_id: Optional[str] = None,
    show_expired: bool = False,
    show_prefix: bool = False,
    env_synthesis: bool = True,
) -> StatusReport:
    """Gather all credentials; return structured report."""
    # load_credentials for each provider; build StatusReport with deterministic ordering
```

### Example 2: Typer Command Thin Shell
**Source:** Phase 022 `state_cli/auth.py`.

```python
# src/state_cli/auth.py
"""Typer sub-app for `state auth ...` commands."""

import asyncio
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from state_core.auth.cli_ops import login as ops_login, logout as ops_logout, status as ops_status
from state_core.auth.errors import AuthError, AuthVaultPermissionError
from state_core.auth.providers.anthropic import StealthRejected

auth_app = typer.Typer(name="auth", help="Manage authentication credentials")

# ── Provider alias table ────────────────────────────────────────────

_PROVIDER_ALIASES = {
    "claude": "anthropic",
    "gemini": "google.gemini",
    "antigravity": "google.antigravity",
    "copilot": "github.copilot",
}

def _normalize_provider(name: str) -> str:
    """Normalize provider name via alias table; raise if unknown."""
    if not name:
        return None  # prompt interactively
    normalized = _PROVIDER_ALIASES.get(name.lower(), name.lower())
    # Future: check against known registry; on miss, use difflib.get_close_matches
    return normalized

# ── login command ────────────────────────────────────────────────────

@auth_app.command(name="login")
def login(
    provider: Optional[str] = typer.Argument(None, help="Provider ID (e.g., anthropic, openai)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key (non-interactive)"),
    code_state: Optional[str] = typer.Option(None, "--code-state", help="Anthropic code#state (non-interactive)"),
    from_stdin: bool = typer.Option(False, "--from-stdin", help="Read credential from stdin"),
) -> None:
    """Log in to a provider."""
    try:
        if not provider:
            # TODO: interactive provider picker (numbered list)
            provider = "anthropic"  # placeholder
        
        provider_id = _normalize_provider(provider)
        
        # Non-TTY check
        if not sys.stdin.isatty() and not (api_key or code_state or from_stdin):
            typer.echo(
                "error: refusing interactive login on non-TTY. "
                "Use --api-key/--code-state/--from-stdin or pipe data into stdin.",
                err=True,
            )
            raise typer.Exit(code=64)
        
        cred = asyncio.run(
            ops_login(
                provider_id=provider_id,
                api_key=api_key,
                code_state=code_state,
                from_stdin=from_stdin,
            )
        )
        
        label = (
            cred.extras.get("email_address")
            or cred.account_id
            or f"{cred.access[:12] if hasattr(cred, 'access') else cred.key[:12]}…"
        )
        typer.echo(f"Logged in to {provider_id}: {label}")
        
    except StealthRejected as exc:
        typer.echo(f"Error (stealth header drift suspected): {exc}", err=True)
        raise typer.Exit(code=3)
    except AuthVaultPermissionError as exc:
        typer.echo(f"Error (vault permission): {exc}", err=True)
        raise typer.Exit(code=77)
    except AuthError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\nCancelled.", err=True)
        raise typer.Exit(code=130)

# ── logout command ───────────────────────────────────────────────────

@auth_app.command(name="logout")
def logout(
    provider: Optional[str] = typer.Argument(..., help="Provider ID"),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID/email (for multi-cred)"),
    all_: bool = typer.Option(False, "--all", help="Remove all credentials for this provider"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Log out (remove a credential)."""
    try:
        provider_id = _normalize_provider(provider)
        count = asyncio.run(ops_logout(provider_id=provider_id, account_id=account, all_=all_, yes=yes))
        if count:
            typer.echo(f"Removed {count} credential(s) for {provider_id}")
        else:
            typer.echo(f"No credentials removed (already logged out from {provider_id})")
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

# ── status command ───────────────────────────────────────────────────

@auth_app.command(name="status")
def status(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
    expired: bool = typer.Option(False, "--expired", help="Show expired only"),
    show_prefix: bool = typer.Option(False, "--show-prefix", help="Show first-12 token chars"),
    json_output: bool = typer.Option(False, "--json", help="JSON output (versioned envelope)"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable color output"),
) -> None:
    """Show credentials."""
    try:
        report = asyncio.run(ops_status(provider_id=provider, show_expired=expired))
        
        if json_output:
            import orjson
            output = {
                "schema": "state.auth.status/v1",
                "providers": report.providers,
            }
            typer.echo(orjson.dumps(output, option=orjson.OPT_INDENT_2).decode())
        else:
            console = Console(no_color=no_color, force_terminal=not no_color)
            table = Table(title="Credentials")
            table.add_column("Provider", style="cyan")
            table.add_column("Type")
            table.add_column("Account")
            table.add_column("Expires")
            table.add_column("Source", style="dim")
            
            # Add rows from report
            console.print(table)
            console.print(report.summary, style="dim")
    
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
```

### Example 3: pytest-httpx Golden-File Pattern
**Source:** Tests/auth/test_p0_regression.py (P0-1 example).

```python
# tests/auth/test_p0_regression.py
"""P0 pitfall regression suite — one named test per pitfall."""

import json
from pathlib import Path
import pytest
import httpx
from pytest_httpx import HTTPXMock

from state_core.auth.providers.anthropic import AnthropicAuth, _USER_AGENT

GOLDEN_DIR = Path(__file__).parent / "golden"

def test_p0_1_user_agent_stealth(httpx_mock: HTTPXMock) -> None:
    """P0-1: Outbound user-agent matches claude-cli/<version> (external, cli).
    
    Pitfall reference: .planning/research/PITFALLS.md P0-1
    Golden file: tests/auth/golden/anthropic/login_authorize.json
    """
    # Load golden fixture
    golden_path = GOLDEN_DIR / "anthropic" / "login_authorize.json"
    golden = json.loads(golden_path.read_text())
    
    # Mock the token endpoint to capture headers
    def capture_headers(request):
        # Validate user-agent
        assert request.headers.get("user-agent") == _USER_AGENT
        assert "(external, cli)" in request.headers.get("user-agent", "")
        
        # Compare against golden allowlist
        actual_headers = dict(request.headers)
        expected_keys = golden.get("positive_allowlist", [])
        for key in expected_keys:
            assert key in actual_headers, f"Missing stealth header: {key}"
        
        return httpx.Response(200, json={"access_token": "sk-test"})
    
    httpx_mock.add_callback(capture_headers, url="https://platform.claude.com/v1/oauth/token")
    
    # Run the test (provider method calls httpx under mock)
    # asyncio.run(AnthropicAuth().login(...))  # with mocked stdin, etc.

def test_p0_13_chmod_0600_verified_on_read() -> None:
    """P0-13: chmod 0o600 verified on every read; wrong mode raises AuthVaultPermissionError.
    
    Pitfall reference: .planning/research/PITFALLS.md P0-13
    """
    from state_core.auth.store import load_vault, AuthVaultPermissionError
    import tempfile
    import os
    
    # Create a vault file with wrong mode
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write('{"schema_version": 1, "providers": {}}')
        path = f.name
    
    try:
        os.chmod(path, 0o644)  # wrong mode
        with pytest.raises(AuthVaultPermissionError) as exc_info:
            load_vault(Path(path))
        assert "0o644" in str(exc_info.value)
        assert "0o600" in str(exc_info.value)
    finally:
        os.unlink(path)
```

---

## Validation Architecture

> **Note:** workflow.nyquist_validation is set to `true` in .planning/config.json, so this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.0+ with pytest-asyncio 1.3.0+ and pytest-httpx 0.35+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] with `asyncio_mode = "auto"` |
| Quick run command | `pytest tests/auth/test_p0_regression.py -v` (9 tests, ~5 seconds) |
| Full suite command | `pytest tests/auth/ -v --cov=src/state_core/auth --cov=src/state_cli/auth` (all auth tests + CLI tests, ~30 seconds) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-12 | `state auth login <provider>` interactive/non-interactive | integration | `pytest tests/state_cli/test_auth_login.py -v` | ❌ Wave 0 |
| AUTH-12 | `state auth logout <provider>` with prompts/--yes | integration | `pytest tests/state_cli/test_auth_logout.py -v` | ❌ Wave 0 |
| AUTH-12 | `state auth status` with table/--json/--provider/--expired | integration | `pytest tests/state_cli/test_auth_status.py -v` | ❌ Wave 0 |
| AUTH-13 P0-1 | User-agent header matches `claude-cli/<version> (external, cli)` | golden | `pytest tests/auth/test_p0_regression.py::test_p0_1_user_agent_stealth -v` | ❌ Wave 0 |
| AUTH-13 P0-2 | `anthropic-beta` header matches pinned string | golden | `pytest tests/auth/test_p0_regression.py::test_p0_2_anthropic_beta_full_string -v` | ❌ Wave 0 |
| AUTH-13 P0-3 | `x-app: cli` header present | golden | `pytest tests/auth/test_p0_regression.py::test_p0_3_x_app_cli -v` | ❌ Wave 0 |
| AUTH-13 P0-4 | Bearer token present, x-api-key NOT present | golden | `pytest tests/auth/test_p0_regression.py::test_p0_4_bearer_not_x_api_key -v` | ❌ Wave 0 |
| AUTH-13 P0-5 | CLIENT_ID base64-decoded to `9d1c250a-e61b-44d9-88ed-5944d1962f5e` | unit | `pytest tests/auth/test_p0_regression.py::test_p0_5_client_id_base64_decoded -v` | ❌ Wave 0 |
| AUTH-13 P0-6 | Filelock acquire timeout (10s) on concurrent refresh | integration | `pytest tests/auth/test_p0_regression.py::test_p0_6_filelock_acquire_timeout -v --slow` | ❌ Wave 0 |
| AUTH-13 P0-7 | 5-minute expiry buffer applied correctly | unit | `pytest tests/auth/test_p0_regression.py::test_p0_7_five_minute_expiry_buffer -v` | ❌ Wave 0 |
| AUTH-13 P0-8 | OAuth state parameter equals PKCE verifier (Anthropic only) | golden | `pytest tests/auth/test_p0_regression.py::test_p0_8_pkce_state_equals_verifier -v` | ❌ Wave 0 |
| AUTH-13 P0-13 | chmod 0o600 verified on vault read; wrong mode raises error | unit | `pytest tests/auth/test_p0_regression.py::test_p0_13_chmod_0600_verified_on_read -v` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/auth/test_p0_regression.py -x` (fast, early exit on first failure)
- **Per wave merge:** `pytest tests/auth/ tests/state_cli/ -v --cov` (all CLI + auth tests with coverage)
- **Phase gate:** Full suite green + import-graph test extends `tests/auth/test_import_graph.py` with CLI mode-isolation rows before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/state_cli/test_auth_login.py` — Typer login command integration tests (mocked providers, stdin handling, TTY detection, exit codes)
- [ ] `tests/state_cli/test_auth_logout.py` — Typer logout command (multi-cred selection, --all, --account, confirmation, event emission)
- [ ] `tests/state_cli/test_auth_status.py` — Typer status command (table rendering, --json envelope, filtering, sorting, color handling)
- [ ] `tests/auth/test_cli_ops.py` — ops-layer unit tests (credential round-trip, event emission, error handling)
- [ ] `tests/auth/golden/anthropic/login_authorize.json` — captured-header golden fixture (Anthropic authorize-URL headers)
- [ ] `tests/auth/golden/anthropic/login_token_exchange.json` — captured-header golden (Anthropic token endpoint)
- [ ] `tests/auth/golden/anthropic/inference_stealth_request.json` — captured-header golden (synthetic inference request with stealth headers)
- [ ] `tests/auth/golden/google.gemini/login_loopback.json` — loopback callback headers
- [ ] Similar golden fixtures for antigravity, copilot, api_key providers
- [ ] `tests/auth/conftest.py` — shared fixtures (monkeypatch clock, fixture for FakeCredential, golden-file loader helper)
- [ ] `pyproject.toml` — pytest_addoption hook for `--update-goldens` custom flag (implemented in conftest)
- [ ] `src/state_core/auth/cli_ops.py` — ops layer implementation (login, logout, status functions)
- [ ] `src/state_cli/auth.py` — Typer sub-app implementation (thin shells)
- [ ] Extension to `tests/auth/test_import_graph.py` — add rows for CLI mode isolation (state_cli.auth may import state_core.auth.*, state_core.auth.cli_ops must NOT import state_cli)

*(No existing test infrastructure — Phase 022 creates the CLI test surface from scratch. Phase 014 established golden-file patterns with mitmproxy; Phase 022 replaces live-cred capture with pytest-httpx mocks.)*

---

## Risks & Pitfalls Specific to 022

### Risk 1: Async/Sync Impedance (Mitigation: Established Pattern)
**Risk:** Event loop nesting if Typer command later called from async context.
**Mitigation:** Document Typer layer is sync-only; ops layer is async-native. Future phases call ops layer with `await` directly. Prevent nesting by keeping Typer as a thin shell. Tests: run Typer commands in isolation, never from async fixtures.
**Owner:** Phase 022 — enforce in code review.

### Risk 2: Golden-File Drift (Mitigation: Mitmproxy Gate Pre-Merge)
**Risk:** Anthropic stealth-headers change upstream; goldens become stale; users' inference fails.
**Mitigation:** CONTEXT.md mandates mitmproxy re-capture gate before merge (Phase 014 established). Goldens are NOT auto-updated in CI. `--update-goldens` flag requires manual review. Add capture-date comment to every golden JSON.
**Owner:** Phase 022 — document in RESEARCH.md that goldens are snapshots, not auto-refreshing.

### Risk 3: Non-TTY Login Hanging (Mitigation: Early Exit Gate)
**Risk:** User runs `state auth login` in CI without --from-stdin; process hangs waiting for input.
**Mitigation:** Check `not sys.stdin.isatty()` BEFORE entering provider logic. Exit 64 immediately if non-interactive flag is missing. Tests: `echo "" | state auth login anthropic` (no flag) must exit 64 immediately.
**Owner:** Phase 022 — implement in ops layer or Typer command, test early.

### Risk 4: Provider Picker Interactive UX (Mitigation: Out of Scope for 022)
**Risk:** Interactive provider list (numbered menu) is not in scope. Phase 022 defers this to follow-up or TUI modal.
**Mitigation:** For 022, when `provider` is omitted, default to "anthropic" or prompt with a simple text input (not a numbered menu). CONTEXT.md says "future TUI modal is where polished day-to-day UX lives; CLI is secondary."
**Owner:** Phase 022 — document in help text that provider is optional but interactive picker is future work.

### Risk 5: Event-Schema Versioning (Mitigation: Coordinate with Phase 021)
**Risk:** AUTH-13 golden files are frozen captures. If the auth.logged_in/logged_out event schema changes, existing goldens become stale.
**Mitigation:** Define event schema ONCE in Phase 022. Use a versioned envelope (e.g., "auth.logged_in/v1"). Tests assert the schema shape. Never change without bumping version.
**Owner:** Phase 022 — add auth.logged_in/auth.logged_out to state_core.schema or state_core.events.

### Risk 6: Test Fixture Import Pollution (Mitigation: Clear Boundaries)
**Risk:** Tests import from both `state_core.auth` and `state_cli.auth`. Accidentally importing a Typer command into an ops-layer test breaks mode isolation.
**Mitigation:** Keep tests separate: `tests/state_cli/test_auth_*.py` for Typer commands (import `state_cli.auth`), `tests/auth/test_cli_ops.py` for ops layer (import `state_core.auth.cli_ops` only). Run import-graph test to catch violations.
**Owner:** Phase 022 — enforce in conftest and test structure.

### Risk 7: Goldens as the Source of Truth (Mitigation: Mitmproxy Capture Discipline)
**Risk:** If a golden file is wrong, all tests pass against a wrong standard. No catch.
**Mitigation:** Phase 014's mitmproxy gate ensures goldens match real Claude Code 2.1.121 behavior at merge time. Phase 022 treats goldens as immutable snapshots (read-only by default). Quarterly re-capture against live Claude Code detects drift. Document that golden drift is a security issue (stealth headers are the auth, not an optional nicety).
**Owner:** Phase 022 + Phase 014 (mitmproxy gate keeper).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| argparse CLI for auth | Typer sub-app CLI | Phase 022 | Terser, better help text, type-safe arguments |
| Each provider has its own smoke-test argparse (_main stub) | Kept as-is; Typer CLI is the public surface | Phase 022 | Two surfaces, one code path — backwards-compatible, developer-friendly |
| Manual mitmproxy capture; live-cred golden files | pytest-httpx mocks + JSON golden files | Phase 022 | Faster tests, CI-safe, no live creds, deterministic |
| Scattered provider login/refresh logic; no reusable ops layer | state_core.auth.cli_ops unifies 6 provider methods into 3 functions | Phase 022 | Future TUI modal can import ops layer directly; no duplication |
| In-process event publishing only | Dual-write to SQLite + SyncEvent (v1 cardinal rule) | Phase 021 + Phase 022 | Replay is authoritative, SyncEvent mirrors for live UI |

**Deprecated/outdated:**
- Plain argparse _main() stubs are NOT deprecated. They coexist with Typer CLI (both are first-class).

---

## Open Questions (Resolved via Research)

1. **Typer sub-app file layout:** Single `src/state_cli/auth.py` is recommended (mirrors db/events pattern). If login/logout/status exceed 200 LOC total (~130 expected), split into `src/state_cli/auth/__init__.py` + per-command modules. Establish a LOC threshold at planning time.

2. **`state_core.auth.cli_ops` module shape:** Three async functions (`login`, `logout`, `status`) returning Credential and StatusReport dataclass. All provider dispatch, event emission, vault I/O is in ops layer. Typer commands are thin shells (parse args, call ops, render/echo).

3. **Rich Table rendering for status:** Use Rich.Console + Rich.Table. Expires column shows "valid Xh Xm", "EXPIRED", or "—" (api_key). Color: amber <1h, red <5min/expired. `--no-color` is auto-detected via `NO_COLOR` env var (Rich's default) + explicit CLI flag. Rich version pinned at 13.9+.

4. **pytest-httpx golden-file pattern:** Fixtures are JSON files at `tests/auth/golden/<provider>/<flow>.json`. Each golden has `positive_allowlist`, `negative_allowlist`, `body_invariants`, `url_invariants` sections. Tests mock httpx requests, compare captured headers against golden allowlists, assert body/URL shapes. `--update-goldens` flag (custom pytest_addoption) regenerates in-place for manual review.

5. **"Inference stealth request" flow for AUTH-13 goldens:** P0-13 focuses on existing login + refresh flows (Anthropic OAuth, Gemini loopback, etc.). Synthetic "inference stealth request" is out of scope for Phase 022 (requires the v3 inference-routing layer). Recommend: add a single synthetic-inference golden that hand-crafts a request body with the stealth system prefix (from `inject_stealth_system_prefix`), runs it through the mocked httpx layer, and asserts stealth headers. This validates the injection path without a full inference API.

6. **P0-6 (filelock timeout) and P0-7 (5-min buffer) test strategy:** Both are behavioral (not header-shaped). P0-6: monkeypatch the lock timeout to 0.01s, simulate concurrent acquire, catch RefreshLockTimeout. P0-7: call `is_expired_buffered(cred, now=cred.expires - 299)` → False, then `now=cred.expires - 300` → True. Both are regular pytest assertions, no golden files.

7. **Event-schema versioning for `auth.logged_in` / `auth.logged_out`:** Recommend envelope structure matching Phase 021's `auth.imported`: `{type: "auth.logged_in", aggregate_id: "vault", ts: "2026-05-01T...", payload: {provider_id, cred_kind, source, account_label}}`. Define once, never change. Tests assert shape.

8. **Test fixture strategy for goldens:** Hand-rolled per flow. Hypothesis property-based testing is overkill (goldens are exact-byte snapshots, not probabilistic contracts). Recommendation: single `conftest.py` with a `golden_loader(provider_id, flow_name)` fixture that reads `tests/auth/golden/<provider>/<flow>.json`, parses it, returns `(positive_allowlist, negative_allowlist, body_invariants, url_invariants)`.

9. **Validation Architecture (Nyquist Dimension 8):** Strategy is: (1) 9 P0 regression tests pass (unit + golden); (2) 3 integration tests for Typer commands (login interactive, logout multi-cred, status rendering); (3) manual `state auth status` smoke test against the dev box's imported opencode creds (Phase 021 capture set). No golden re-capture automation; mitmproxy gate at Phase 014 + quarterly manual re-capture.

10. **Risks / pitfalls specific to 022:** Async/sync impedance (mitigated by thin shell pattern), rich+typer buffering (single Console per command), golden drift (mitmproxy gate), non-TTY hanging (early exit), provider picker deferred (simple fallback for 022), event schema (version once), test isolation (separate test modules), goldens as source-of-truth (mitmproxy gate pre-merge).

---

## Sources

### Primary (HIGH confidence)
- **CONTEXT.md** — Phase 022 locked decisions (Typer trio, ops-layer seam, exit codes, AUTH-13 method).
- **pyproject.toml** — confirmed Typer 0.15+, Rich 13.9+, pytest-httpx 0.35+, pytest-asyncio 1.3.0+.
- **src/state_cli/main.py** — established Typer sub-app pattern (db_app, events_app, asyncio.run wrapper).
- **src/state_core/auth/providers/anthropic.py** — _main() argparse stub at line 705, stealth-header constants, provider methods (login, refresh).
- **src/state_core/auth/store.py** — AuthVault shape, atomic write, chmod-0600 enforcement, exceptions.
- **src/state_core/auth/loader.py** — load_credentials orchestration (vault > env precedence).
- **src/state_core/auth/refresh.py** — filelock coordination, is_expired_buffered helper, AsyncFileLock config.
- **src/state_core/auth/errors.py** — exception hierarchy with exit-code mapping guidance.
- **.planning/config.json** — workflow.nyquist_validation = true (Validation Architecture section required).
- **tests/auth/test_import_graph.py** — mode-isolation test patterns; extension points for Phase 022.

### Secondary (MEDIUM confidence)
- **Phase 014–018 RESEARCH documents** (from .planning/milestones/v2/phases/) — auth implementation patterns, provider shapes, error handling.
- **Phase 021 import_opencode.py** — event emission pattern (auth.imported), SyncEvent dual-write.
- **Rich 13.9 documentation** (implicit in pyproject.toml pinning) — Table, Console API, color codes, NO_COLOR env var.
- **pytest-httpx documentation** (implicit in dev deps) — HTTPXMock fixture, request capture, callback patterns.

### Tertiary (Context / Confirmation)
- **ROADMAP.md** (Phase 022 section) — requirements mapping, dependency graph.
- **REQUIREMENTS.md** (AUTH-12, AUTH-13) — acceptance criteria.

---

## Metadata

**Confidence breakdown:**
- **Standard Stack:** HIGH — Typer/Rich already pinned in pyproject.toml; pytest-httpx is dev dep; all core libs are established.
- **Architecture:** HIGH — Typer sub-app pattern is proven (src/state_cli/main.py); ops-layer seam is locked in CONTEXT.md; provider methods are pre-built.
- **Pitfalls:** HIGH — Phase 014–021 identified and mitigated P0-1..P0-8, P0-13 pitfalls; Phase 022 validates them via regression tests.
- **Validation:** MEDIUM-HIGH — Nyquist Dimension 8 (test infrastructure) is new; pattern is sound but unproven at scale. Golden-file approach is lower-fidelity than live mitmproxy (mitigated by Phase 014 pre-merge gate).

**Research date:** 2026-05-01  
**Valid until:** 2026-05-15 (two weeks; auth stack is stable; revisit if Anthropic API changes)

**Confidence for planning:** HIGH — All locked decisions are understood, all reusable assets are catalogued, all pitfalls are documented. Planner can create 4–5 concrete plans immediately. Execution risk is low (tight reuse of existing code); UX polish (interactive provider picker) is explicitly deferred.
