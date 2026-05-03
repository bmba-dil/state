---
phase: 022-cli-state-auth-login-logout
plan: "03"
subsystem: auth-cli-typer
tags: [auth, typer, cli, login, logout, status, AUTH-12]
dependency_graph:
  requires:
    - "022-01: Wave 0 RED stubs (test_cli_typer.py)"
    - "022-02: cli_ops ops layer (login, logout, status, StatusReport, StatusRow)"
    - "src/state_cli/main.py (existing Typer app pattern)"
    - "src/state_core/auth/errors.py (AuthError, UnknownApiKeyProviderError)"
    - "src/state_core/auth/store.py (AuthVaultPermissionError, get_auth_json_path, load_vault)"
    - "src/state_core/auth/providers/anthropic.py (StealthRejected)"
  provides:
    - "src/state_cli/auth.py: auth_app Typer sub-app with login/logout/status"
    - "src/state_cli/main.py: auth_app registered via app.add_typer(auth_app)"
  affects:
    - "CLI entrypoint: 'state auth login|logout|status' commands now active"
    - "Future opencode-plugin TUI modal: same cli_ops seam"
tech_stack:
  added: []
  patterns:
    - "Typer sub-app with asyncio.run() wrapper (mirrors db_app/events_app pattern)"
    - "Rich Console(stderr=True) for error output; Console(no_color=True) for --no-color"
    - "Rich Table for human status output (5 columns, box=None for 80-col fit)"
    - "orjson dumps for --json output with OPT_INDENT_2 | OPT_SORT_KEYS"
    - "import path convention: state_core.* (without src. prefix) to match cli_ops"
    - "Lazy imports for get_auth_json_path/load_vault inside logout command body"
key_files:
  created:
    - src/state_cli/auth.py
  modified:
    - src/state_cli/main.py
    - tests/auth/test_cli_typer.py
decisions:
  - "Used state_core.auth.* imports (without src. prefix) to match cli_ops.py's import namespace — avoids module-identity mismatch in exception catch clauses"
  - "Interactive picker returns provider name only (not provider:kind) — simpler for callers; anthropic always resolves to canonical anthropic"
  - "get_auth_json_path/load_vault imported at module level in auth.py for vault peek in logout confirmation"
  - "test_cli_typer.py stubs turned GREEN in this plan (not test_p0_regression.py — those are Plan 04)"
  - "test_state_auth_login_stealth_rejected_exits_3: must import StealthRejected from state_core.auth.providers.anthropic (not src.state_core.*) to match auth.py's import namespace"
metrics:
  duration: "~9m"
  completed: "2026-05-01T23:08:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
---

# Phase 022 Plan 03: Typer CLI Sub-App Summary

**One-liner:** Typer auth sub-app (`auth_app`) with `login/logout/status` commands registered in `main.py`, all 15 `test_cli_typer.py` stubs turned GREEN via CliRunner-driven tests with mocked ops layer.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement src/state_cli/auth.py Typer sub-app | c4a557f | src/state_cli/auth.py, tests/auth/test_cli_typer.py |
| 2 | Register auth_app in src/state_cli/main.py | cf9ffb7 | src/state_cli/main.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Import path mismatch — `state_core.*` vs `src.state_core.*`**
- **Found during:** Task 1, running test_state_auth_login_unknown_provider_exits_64
- **Issue:** auth.py imported exceptions from `src.state_core.auth.*` but cli_ops.py uses `state_core.auth.*`. Python treats these as distinct module objects; `except UnknownApiKeyProviderError` in auth.py didn't catch the exception raised from cli_ops.py. Exit code was 1 (uncaught AuthError) instead of 64.
- **Fix:** Changed all imports in auth.py from `src.state_core.auth.*` to `state_core.auth.*` to share the same module namespace as cli_ops.py.
- **Files modified:** src/state_cli/auth.py
- **Commit:** c4a557f

**2. [Rule 1 - Bug] Typer CliRunner `mix_stderr=False` not supported in Typer 0.24.2**
- **Found during:** Task 1, initial test run
- **Issue:** Typer 0.24.2 CliRunner delegates to Click's CliRunner which doesn't accept `mix_stderr`. Plan's test specification assumed a newer API.
- **Fix:** Removed `mix_stderr=False` from all CliRunner() instantiations. CliRunner merges stdout+stderr by default, so assertions check `result.output` directly.
- **Files modified:** tests/auth/test_cli_typer.py
- **Commit:** c4a557f

**3. [Rule 3 - Blocking] Worktree branch at Phase 017 (62b3c76), not expected base (ca6a8038)**
- **Found during:** Pre-execution worktree check
- **Issue:** Worktree `agent-a60ce0be759f30c35` was at Phase 017 merge commit. Expected base `ca6a8038` (docs(022-01)) was not an ancestor. Test files from Plans 01 and 02 were absent.
- **Fix:** Ran `git reset --hard ca6a8038b08e8dbbe3bf5040f7586fc2eb18c33e` to bring the worktree to the correct base with all Wave 1 and Wave 2 files present.
- **Commit:** N/A (reset, not a new commit)

**4. [Rule 1 - Bug] `test_state_auth_login_stealth_rejected_exits_3` StealthRejected class identity**
- **Found during:** Task 1, test run after import path fix
- **Issue:** Test imported `StealthRejected` from `src.state_core.auth.providers.anthropic` but auth.py imports from `state_core.auth.providers.anthropic`. Raising the `src.*` version wasn't caught by auth.py's `except StealthRejected`.
- **Fix:** Changed test import to `from state_core.auth.providers.anthropic import StealthRejected`.
- **Files modified:** tests/auth/test_cli_typer.py
- **Commit:** c4a557f

## Issues Encountered

**Pre-existing `test_api_key.py` fixture gap:** `mock_api_key_getpass` fixture missing — identified in Plan 02 SUMMARY as pre-existing, not caused by Plan 03 changes.

**Pre-existing test failures in broader test suite:** 26 failures and 192 errors in `tests/` unrelated to auth CLI changes (test_sync_mirror.py, test_rotation.py fixture gaps, etc.). All pre-existing.

## Self-Check: PASSED

- src/state_cli/auth.py: FOUND
- src/state_cli/main.py: modified with app.add_typer(auth_app)
- tests/auth/test_cli_typer.py: FOUND (15 stubs GREEN)
- Commit c4a557f: FOUND
- Commit cf9ffb7: FOUND
- grep -c "app.add_typer(auth_app)" src/state_cli/main.py: 1
- pytest tests/auth/test_cli_typer.py: 15 PASSED
- pytest tests/auth/test_import_graph.py::test_state_cli_auth_one_way_edge: PASSED
- pytest tests/auth/test_cli_ops.py: 14 PASSED
- No state_build/state_teach imports in auth.py: VERIFIED
- No src.state_cli imports in auth.py: VERIFIED
