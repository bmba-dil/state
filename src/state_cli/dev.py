"""Development utility commands for the state workflow engine."""

from __future__ import annotations

import importlib

import typer

dev_app = typer.Typer(name="dev", help="Development utility commands")

_SERVER_MODULES = {
    "state-build": "state_build.mcp",
    "state-teach": "state_teach.mcp",
}
_TOKEN_BUDGET_PER_TOOL = 80
_TOTAL_TOKEN_BUDGET = 15 * _TOKEN_BUDGET_PER_TOOL


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
    lines: list[tuple[str, int, str]] = []

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
        typer.echo(
            f"\nBudget exceeded by {total - _TOTAL_TOKEN_BUDGET} tokens.", err=True
        )
        raise typer.Exit(code=1)
