# Phase 112: mode-gate-integration — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (discuss skipped)

<domain>
## Phase Boundary

Server checks `.state/mode.json` at boot; exits with clear error if mode mismatch.

The `state-build` MCP server must refuse to start when the active project mode is `teach`. This is Layer 3 of the 6-layer mode-enforcement defense. The gate reads `.state/mode.json` (created by Phase 097), validates the mode field, and exits with a clear diagnostic if the mode is not `build` or `both`.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion.

Key decisions:
- Gate function `_check_mode_gate()` called in `if __name__ == "__main__"` before `mcp.run()`
- Exit code 78 (`EX_CONFIG` — configuration error) per sysexits convention
- Graceful handling: missing file → allow (development mode); corrupt file → allow with warning
- Allowed modes: `"build"` and `"both"`
- Error message written to stderr, includes current mode and required modes

### Why not use state_core.schema.ModeConfig
The schema module `ModeConfig` provides validation for internal use. At the MCP server boot level, a lightweight check with just `json.loads()` and dict access avoids the full pydantic parse overhead and keeps the import surface small.
</decisions>

<code_context>
## Existing Code Insights

### .state/mode.json format (Phase 097)
```json
{"mode": "build"}
```
Valid values: `"build"`, `"teach"`, `"both"`, `"kernel"` (kernel is internal-only)

### mcp.py entry point (post-Phase 110)
```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```
The gate must run before this line.

### Related tests
Phase 113 (`test_mcp_collision_regression.py`) already has `TestModeGate` class with 3 tests exercising the gate: allows build, rejects teach, allows both.
</code_context>

<specifics>
## Specific Ideas

```python
def _check_mode_gate() -> None:
    import json, sys
    from pathlib import Path
    mode_path = Path(".state/mode.json")
    if not mode_path.exists():
        return
    try:
        data = json.loads(mode_path.read_text())
        mode = data.get("mode")
    except (json.JSONDecodeError, OSError):
        return
    if mode not in ("build", "both"):
        sys.stderr.write(
            f"state-build: mode mismatch — .state/mode.json has mode={mode}, "
            f"but state-build requires mode=build or mode=both.\n"
        )
        sys.exit(78)
```

Called from:
```python
if __name__ == "__main__":
    _check_mode_gate()
    mcp.run(transport="stdio")
```
</specifics>

<deferred>
## Deferred Ideas

- Phase v13 (state-teach): Mirror gate for `state-teach` server (reject when mode=build)
- Phase 099: MCP registration toggle in plugin (Layer 3 of mode enforcement)
- Stderr logging via structlog instead of `sys.stderr.write` — deferred to observability pass
</deferred>
