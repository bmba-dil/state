# Phase 097: .state/mode.json schema + validator - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Pydantic `ModeConfig` with `mode: build|teach|both`; strict validation; CLI init.

**Note:** A `ModeConfig(BaseModel)` already exists in `src/state_daemon/middleware.py` (line 30) with `mode: Literal["build", "teach", "both"]` and file I/O (`load_mode_config()`). Phase 097 should extract/promote this to its canonical home in `src/state_core/schema.py` and add a standalone validator with CLI init for bootstrapping `.state/mode.json`.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Existing `ModeConfig` in `middleware.py` should be consolidated into `src/state_core/schema.py` (the canonical event schema file)
- Add `mode_validator()` standalone function for programmatic validation
- CLI init: `state mode init` that creates `.state/mode.json` with the specified mode
- Follow existing Pydantic patterns: `extra="forbid"`, `ConfigDict`, `field_validator`
</decisions>

<code_context>
## Existing Code Insights

### ModeConfig (already exists)
- `src/state_daemon/middleware.py:30` — `ModeConfig(BaseModel)` with `mode: Literal["build", "teach", "both"]`
- `src/state_daemon/middleware.py:48` — `load_mode_config(root)` reads/creates `.state/mode.json`
- Mode "kernel" is internal-only, not persistable

### Schema patterns
- `src/state_core/schema.py` — Central event schema file with 28+ event models, all using `BaseModel`, `ConfigDict(extra="forbid")`, `Field`, `field_validator`
- All models use `from __future__ import annotations`
- Import convention: `from pydantic import BaseModel, ConfigDict, Field, field_validator`

### CLI patterns
- `src/state_cli/main.py` — Root typer app with `app.add_typer()` composition
- Command pattern: `typer.Typer(name="..."), typer.Option(), raise typer.Exit()`
- Existing sub-commands: daemon, auth, snapshot, dag, db, events

### .state/ directory patterns
- `.state/mode.json` format: `{"mode": "build|teach|both"}`
- File permissions: `chmod 0o600` on creation
- Directory bootstrap: `os.makedirs(dirname, exist_ok=True)`
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Implement per ROADMAP phase goal and MODE-01 requirement.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
