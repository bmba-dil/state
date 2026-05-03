"""Typer sub-app: `state auth login|logout|status`.

Thin shell over state_core.auth.cli_ops. All auth logic in cli_ops.
This module: argument parsing, TTY checks, Rich rendering, exit-code mapping.

Import discipline: state_cli.auth -> state_core.auth.*  (one-way only)
DO NOT import from state_cli.* here; no circular imports.
"""
from __future__ import annotations

import asyncio
import re
import sys
from typing import Optional

import orjson
import typer
from rich.console import Console
from rich.table import Table

from state_core.auth.cli_ops import (
    StatusReport,
    StatusRow,
    _account_label,
    _resolve_provider_id as _resolve_pid,
    login as ops_login,
    logout as ops_logout,
    status as ops_status,
)
from state_core.auth.errors import (
    AuthError,
    NoCredentialsAvailableError,
    UnknownApiKeyProviderError,
)
from state_core.auth.store import AuthVaultPermissionError, get_auth_json_path, load_vault

try:
    from state_core.auth.providers.anthropic import StealthRejected
except ImportError:
    # Fallback: define a stub so except StealthRejected works without the provider
    class StealthRejected(AuthError):  # type: ignore[no-redef]
        pass


# Interactive provider picker — CONTEXT.md § Login UX (locked decision)
PROVIDERS_OAUTH = ["anthropic", "google.gemini", "google.antigravity", "github.copilot"]
PROVIDERS_API_KEY = [
    "anthropic", "openai", "google", "deepseek", "groq", "together",
    "anyscale", "mistral", "cohere", "openrouter", "grok", "cerebras",
]


def _interactive_picker() -> str:
    """Numbered-list provider picker for 'state auth login' with no arg.

    Enumerates 4 OAuth + 12 API-key providers (16 rows total).
    anthropic appears twice — once as (oauth), once as (api_key).
    KeyboardInterrupt during selection exits 130.
    Invalid index exits 64.
    """
    rows = [(p, "oauth") for p in PROVIDERS_OAUTH] + [(p, "api_key") for p in PROVIDERS_API_KEY]
    typer.echo("Select a provider:")
    for i, (p, kind) in enumerate(rows):
        typer.echo(f"  [{i}] {p} ({kind})")
    try:
        idx = typer.prompt("Provider number", type=int)
    except KeyboardInterrupt:
        raise typer.Exit(code=130)
    if not 0 <= idx < len(rows):
        typer.echo("error: invalid selection", err=True)
        raise typer.Exit(code=64)
    p, kind = rows[idx]
    return p


auth_app = typer.Typer(
    name="auth",
    help="Manage authentication credentials (login, logout, status).",
)


def _format_expires(expires_at: float | None, expires_in_seconds: float | None) -> str:
    """Format expiry for human display: 'valid 4h12m', 'EXPIRED', or '—'."""
    if expires_at is None:
        return "—"
    if expires_in_seconds is None or expires_in_seconds <= 0:
        return "EXPIRED"
    total_seconds = int(expires_in_seconds)
    hours, rem = divmod(total_seconds, 3600)
    minutes = rem // 60
    if hours > 0:
        return f"valid {hours}h{minutes:02d}m"
    return f"valid {minutes}m"


def _expires_style(expires_in_seconds: float | None) -> str:
    """Rich color for expires column (CONTEXT.md renderer details)."""
    if expires_in_seconds is None:
        return "red"   # api_key shows — (no expiry concept)
    if expires_in_seconds <= 0:
        return "red"
    if expires_in_seconds < 300:
        return "red"
    if expires_in_seconds < 3600:
        return "yellow"
    return "green"


@auth_app.command(name="login")
def login(
    provider: Optional[str] = typer.Argument(
        None, help="Provider ID (e.g., anthropic, openai, claude, gemini)"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="Non-interactive: pre-supplied API key (api_key providers only)"
    ),
    code_state: Optional[str] = typer.Option(
        None, "--code-state", help="Non-interactive: Anthropic 'code#state' paste"
    ),
    from_stdin: bool = typer.Option(
        False, "--from-stdin", help="Read credential from stdin (provider-aware)"
    ),
    account: Optional[str] = typer.Option(
        None, "--account", help="Account ID (for multi-account providers)"
    ),
) -> None:
    """Log in to a provider and store credentials.

    Provider examples: anthropic, openai, gemini, copilot, google.gemini
    Alias table: claude->anthropic, gemini->google.gemini,
                 antigravity->google.antigravity, copilot->github.copilot

    StealthRejected (exit 3) signals Anthropic header drift to CI.
    Exit codes: 0=success, 1=AuthError, 3=StealthRejected,
                64=EX_USAGE, 77=EX_NOPERM, 78=EX_CONFIG, 130=SIGINT
    """
    console = Console(stderr=True)

    # Non-TTY refusal when no provider given (interactive picker unavailable on non-TTY)
    if provider is None:
        if not sys.stdin.isatty():
            console.print(
                "error: refusing interactive login on non-TTY. "
                "Use --api-key/--code-state/--from-stdin or pipe data into stdin.",
                style="red",
            )
            raise typer.Exit(code=64)
        # Interactive numbered-list picker (CONTEXT.md § Login UX — locked)
        provider = _interactive_picker()

    # Non-TTY refusal when provider was given but no non-interactive flag
    if not sys.stdin.isatty() and not (api_key or code_state or from_stdin):
        console.print(
            "error: refusing interactive login on non-TTY. "
            "Use --api-key/--code-state/--from-stdin or pipe data into stdin.",
            style="red",
        )
        raise typer.Exit(code=64)

    # Resolve alias and validate provider name
    try:
        provider_id = _resolve_pid(provider)
    except (UnknownApiKeyProviderError, AuthError) as exc:
        console.print(f"error: {exc}", style="red")
        raise typer.Exit(code=64) from exc

    try:
        cred = asyncio.run(
            ops_login(
                provider_id,
                account_id=account,
                api_key=api_key,
                code_state=code_state,
                from_stdin=from_stdin,
            )
        )
        # Success message (CONTEXT.md: "Logged in to <provider>: <account_label>")
        label = _account_label(cred)
        typer.echo(f"Logged in to {provider_id}: {label}")

    except StealthRejected as exc:
        console.print(f"error (stealth header drift suspected — exit 3): {exc}", style="red")
        raise typer.Exit(code=3) from exc
    except AuthVaultPermissionError as exc:
        console.print(f"error (vault permission — EX_NOPERM): {exc}", style="red")
        raise typer.Exit(code=77) from exc
    except UnknownApiKeyProviderError as exc:
        console.print(f"error (unknown provider): {exc}", style="red")
        raise typer.Exit(code=64) from exc
    except AuthError as exc:
        console.print(f"error: {exc}", style="red")
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        typer.echo("\nCancelled.", err=True)
        raise typer.Exit(code=130)


@auth_app.command(name="logout")
def logout(
    provider: str = typer.Argument(..., help="Provider ID"),
    account: Optional[str] = typer.Option(
        None, "--account", help="Account ID/email to remove (for multi-cred)"
    ),
    all_: bool = typer.Option(False, "--all", help="Remove ALL credentials for this provider"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Remove stored credentials for a provider.

    Exit codes: 0=success/already-logged-out, 1=error, 64=EX_USAGE,
                77=EX_NOPERM, 130=SIGINT
    """
    console = Console(stderr=True)

    try:
        provider_id = _resolve_pid(provider)
    except (UnknownApiKeyProviderError, AuthError) as exc:
        console.print(f"error: {exc}", style="red")
        raise typer.Exit(code=64) from exc

    # Confirmation for --all without --yes
    if all_ and not yes:
        confirm = typer.confirm(
            f"Remove ALL credentials for {provider_id}? This cannot be undone."
        )
        if not confirm:
            typer.echo("Aborted.")
            raise typer.Exit(code=0)

    # Single-cred confirmation (read-only peek at vault to check count)
    if not all_ and account is None and not yes:
        vault_path = get_auth_json_path()
        if vault_path.exists():
            vault = load_vault(vault_path)
            creds = list(vault.providers.get(provider_id, []))
            if len(creds) == 1:
                label = _account_label(creds[0])
                confirm = typer.confirm(
                    f"Remove the only {provider_id} credential ({label})?"
                )
                if not confirm:
                    typer.echo("Aborted.")
                    raise typer.Exit(code=0)
            elif len(creds) > 1:
                # Non-interactive without --account or --all is a hard error
                if not sys.stdin.isatty():
                    console.print(
                        f"error: {provider_id} has {len(creds)} credentials. "
                        "Use --account <id> or --all in non-interactive mode.",
                        style="red",
                    )
                    raise typer.Exit(code=64)

    try:
        count = asyncio.run(
            ops_logout(
                provider_id,
                account_id=account,
                all_=all_,
                yes=yes,
            )
        )
        if count:
            typer.echo(f"Removed {count} credential(s) for {provider_id}.")
        else:
            typer.echo(f"No credentials found for {provider_id} (already logged out).")

    except ValueError as exc:
        # Ambiguous --account match
        console.print(f"error: {exc}", style="red")
        raise typer.Exit(code=64) from exc
    except AuthVaultPermissionError as exc:
        console.print(f"error (vault permission — EX_NOPERM): {exc}", style="red")
        raise typer.Exit(code=77) from exc
    except AuthError as exc:
        console.print(f"error: {exc}", style="red")
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        typer.echo("\nCancelled.", err=True)
        raise typer.Exit(code=130)


@auth_app.command(name="status")
def status(
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Filter by provider ID"
    ),
    expired: bool = typer.Option(False, "--expired", help="Show expired credentials only"),
    show_prefix: bool = typer.Option(
        False, "--show-prefix", help="Show first-12 token chars (opt-in)"
    ),
    json_output: bool = typer.Option(False, "--json", help="JSON output (versioned envelope)"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI color output"),
) -> None:
    """Show stored credentials.

    Default columns: provider | type | account | expires | source
    Use --json for machine-readable output (state.auth.status/v1 schema).
    Use --show-prefix to reveal first 12 token chars in human output.

    Exit codes: 0=success, 1=error, 77=EX_NOPERM
    """
    console = Console(no_color=no_color, highlight=False)

    try:
        report = asyncio.run(
            ops_status(
                provider_id=provider,
                show_expired=expired,
                show_prefix=show_prefix,
            )
        )

        if json_output:
            # --json envelope schema (CONTEXT.md verbatim):
            # {"schema": "state.auth.status/v1", "providers": [...]}
            output = {
                "schema": "state.auth.status/v1",
                "providers": report.providers,
            }
            typer.echo(
                orjson.dumps(
                    output,
                    option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
                ).decode()
            )
        else:
            # Rich Table rendering (CONTEXT.md: 5 columns, 80-col fit)
            table = Table(
                title="Credentials",
                show_header=True,
                header_style="bold",
                box=None,  # clean output, fits 80 cols
            )
            table.add_column("Provider", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta")
            table.add_column("Account")
            table.add_column("Expires")
            table.add_column("Source", style="dim")

            for row in report.rows:
                expires_str = _format_expires(row.expires_at, row.expires_in_seconds)
                exp_style = _expires_style(row.expires_in_seconds)

                # show_prefix appends prefix12 to account column if opted in
                account_str = row.account_label
                if show_prefix and row.prefix12:
                    account_str = f"{row.account_label} [{row.prefix12}…]"

                table.add_row(
                    row.provider_id,
                    row.type,
                    account_str,
                    f"[{exp_style}]{expires_str}[/{exp_style}]",
                    row.source,
                )

            console.print(table)
            console.print(report.summary, style="dim")

    except AuthVaultPermissionError as exc:
        typer.echo(f"error (vault permission — EX_NOPERM): {exc}", err=True)
        raise typer.Exit(code=77) from exc
    except AuthError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        typer.echo("\nCancelled.", err=True)
        raise typer.Exit(code=130)


__all__ = ["auth_app"]
