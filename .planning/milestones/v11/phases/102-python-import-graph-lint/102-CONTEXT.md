# Phase 102: Python import-graph lint (CI) - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Ruff plugin or custom script; fails if state.build.* imports state.teach.* or vice versa.

**Goal:** CI enforcement that prevents cross-mode imports at the Python module level. This is layer 6 of 6 for mode enforcement — the final defense-in-depth gate. A custom script (or Ruff plugin rule) scans all imports and fails the build if state.build.* imports anything from state.teach.* or vice versa.
</domain>

<decisions>
## Implementation Decisions
All at AI's discretion.

Key considerations:
- Build mode: src/state_build/ — must not import from state_teach/
- Teach mode: src/state_teach/ — must not import from state_build/
- Shared kernel: src/state_core/ — may be imported by both
- Daemon: src/state_daemon/ — shared infrastructure, may import from both
- Should be runnable as `python3 -m state_core.import_lint` or similar
- Must integrate with CI (run during `ruff check` or separately)
</decisions>

<code_context>
- src/state_build/ — Build-mode packages
- src/state_teach/ — Teach-mode packages
- src/state_core/ — Shared kernel (importable by both)
- src/state_daemon/ — Daemon (shared infrastructure)
- pyproject.toml — Project config with ruff settings
</code_context>

<specifics>
Implement per ROADMAP phase goal, MODE-06 and TST-07 requirements.
</specifics>

<deferred>
None.
</deferred>
