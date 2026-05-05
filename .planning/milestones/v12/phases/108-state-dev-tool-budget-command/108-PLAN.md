---
phase: 108
phase_name: state-dev-tool-budget-command
wave: 1
depends_on: ["107"]
files_modified:
  - src/state_cli/dev.py
  - src/state_cli/main.py
requirements_addressed: ["MCP-B-06"]
autonomous: true
---

## Plan 01: `state dev tool-budget` CLI Command

**Goal:** CLI command that sums tool-description tokens and refuses > budget with non-zero exit.

### Tasks

#### 01.1 Create `src/state_cli/dev.py` with tool-budget command
**Acceptance:** `state dev tool-budget` exits 0 when within budget, prints per-tool token table
**Estimated effort:** Medium
**Dependencies:** Phase 107 (15 tools defined)
**Details:**
- Create typer sub-app `dev_app` with `tool-budget` command
- Optional `--server` argument (default: `state-build`) to select which MCP server to audit
- Load tools by importing the server module and reading `_tool_manager._tools`
- Token count: simple word-count heuristic (split description on whitespace)
- Budget: number of tools × 80 tokens
- Print a table with per-tool token counts, budget, and pass/fail
- Exit 0 if total ≤ budget, exit 1 if exceeded

<action>
Create `src/state_cli/dev.py`:

```python
import importlib
import sys
import typer

dev_app = typer.Typer(name="dev", help="Development utility commands")

_SERVER_MODULES = {
    "state-build": "state_build.mcp",
    "state-teach": "state_teach.mcp",
}
_TOKEN_BUDGET_PER_TOOL = 80
_TOTAL_TOKEN_BUDGET = 15 * _TOKEN_BUDGET_PER_TOOL  # 1200


def _count_tokens(text: str) -> int:
    """Simple word-count heuristic for token estimation."""
    return len(text.split())


@dev_app.command(name="tool-budget")
def tool_budget(
    server: str = typer.Option(
        "state-build", "--server", "-s", help="MCP server to audit"
    ),
) -> None:
    """Sum tool-description tokens and check against budget.

    Exits 0 if within budget, 1 if exceeded.
    """
    if server not in _SERVER_MODULES:
        typer.echo(f"Unknown server: {server}", err=True)
        raise typer.Exit(code=2)

    try:
        mod = importlib.import_module(_SERVER_MODULES[server])
    except ImportError as exc:
        typer.echo(f"Cannot import {server}: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    tools = mod.mcp._tool_manager._tools
    if not tools:
        typer.echo("No tools registered.", err=True)
        raise typer.Exit(code=1)

    total = 0
    lines = []

    for name, tool in sorted(tools.items()):
        description = getattr(tool, "description", "") or ""
        tokens = _count_tokens(description)
        total += tokens
        status = "✓" if tokens <= _TOKEN_BUDGET_PER_TOOL else "✗ OVER"
        lines.append((name, tokens, status))

    header = f"{'Tool':<22} {'Tokens':>7} {'Budget':>7}  Status"
    sep = "─" * len(header)

    typer.echo(header)
    typer.echo(sep)
    for name, tokens, status in lines:
        typer.echo(f"{name:<22} {tokens:>7} {_TOKEN_BUDGET_PER_TOOL:>7}  {status}")
    typer.echo(sep)

    overall = "✓ PASS" if total <= _TOTAL_TOKEN_BUDGET else "✗ FAIL"
    typer.echo(f"{'TOTAL':<22} {total:>7} {_TOTAL_TOKEN_BUDGET:>7}  {overall}")

    if total > _TOTAL_TOKEN_BUDGET:
        typer.echo(f"\nBudget exceeded by {total - _TOTAL_TOKEN_BUDGET} tokens.", err=True)
        raise typer.Exit(code=1)
```

Consumed by: CI pipeline (pre-commit hook, GitHub Actions), developer workstation (manual check before committing tool changes).
</action>

<read_first>
- src/state_cli/main.py (CLI pattern)
- src/state_build/mcp.py (tool definitions to audit)
</read_first>

<acceptance_criteria>
- `test -f src/state_cli/dev.py` exits 0
- `grep "tool-budget" src/state_cli/dev.py` returns >=1 match
- `.venv/bin/python3 -m state_cli.main dev tool-budget` exits 0 (current tools within budget)
- `rtk grep "def tool_budget" src/state_cli/dev.py` returns 1 match
</acceptance_criteria>

#### 01.2 Register `dev` sub-app in main.py
**Acceptance:** `state dev --help` lists tool-budget command
**Estimated effort:** Small
**Dependencies:** 01.1
**Details:**
- Import `dev_app` from `state_cli.dev`
- Add to main `app` via `app.add_typer(dev_app)`
- Follow existing pattern used by auth, snapshot, dag, daemon, mode sub-apps

<action>
Add to `src/state_cli/main.py`:

```python
# Phase 108 — dev sub-app
from src.state_cli.dev import dev_app  # noqa: E402
app.add_typer(dev_app)
```

Consumed by: `state dev` command in CLI, CI validation scripts.
</action>

<read_first>
- src/state_cli/main.py
</read_first>

<acceptance_criteria>
- `grep "from src.state_cli.dev import dev_app" src/state_cli/main.py` returns 1 match
- `.venv/bin/python3 -m state_cli.main dev --help` exits 0 and lists tool-budget
</acceptance_criteria>

### Integration Notes
- Phase 108 enables CI assertion gating tool description growth
- The `_SERVER_MODULES` dict is forward-compatible with Phase 115 (state-teach MCP server)
