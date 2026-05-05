# Phase 098: Directory-presence signal (.state/build/ vs .state/teach/) - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Daemon refuses writes into the wrong subtree; `state mode init` bootstraps structure.

**Goal:** Physical directory structure (`/state/build/` and `/state/teach/`) serves as a visible, non-bypassable signal of the active mode. The daemon enforces that mode-specific operations only write to their respective subtrees.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Extend `state mode init` from Phase 097 to create `/state/build/` or `/state/teach/` subtrees
- Daemon middleware must validate write destinations against the active mode
- Directory structure is the 2nd layer of the 6-layer defense-in-depth
- Must integrate with existing daemon middleware (`src/state_daemon/middleware.py`)
</decisions>

<code_context>
## Existing Code Insights

### Mode config (Phase 097)
- `src/state_core/schema.py:111` — `ModeConfig` with `mode: Literal["build", "teach", "both"]`
- `src/state_cli/main.py` — `state mode init <mode>` CLI command
- `.state/mode.json` is the authoritative mode config file

### Daemon middleware
- `src/state_daemon/middleware.py` — ModeMiddleware validates `X-State-Mode` header
- `load_mode_config()` reads `.state/mode.json` on startup

### .state/ directory patterns
- `.state/` is relative to `Path.cwd()` in most cases
- Each subsystem uses `os.makedirs(parents=True, exist_ok=True)` at point-of-use
- File permissions: `chmod 0o600` for sensitive files
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Implement per ROADMAP phase goal and MODE-02 requirement.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
