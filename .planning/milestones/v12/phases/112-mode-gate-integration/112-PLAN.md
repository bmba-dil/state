---
phase: 112
phase_name: mode-gate-integration
wave: 1
depends_on: ["097"]
files_modified:
  - src/state_build/mcp.py
requirements_addressed: ["MCP-B-01", "MODE-03"]
autonomous: true
---

## Plan 01: Mode-Gate at Server Boot

**Goal:** Server reads `.state/mode.json` at boot, refuses to start if mode is not `build` or `both`.

### Tasks

#### 01.1 Add `_check_mode_gate()` function
**Acceptance:** Function reads `.state/mode.json`, exits 78 on mismatch, returns silently on match
**Estimated effort:** Small
**Dependencies:** Phase 097 (mode.json schema exists)

<action>
Add `_check_mode_gate()` to `src/state_build/mcp.py` before the `if __name__ == "__main__"` block.

The function:
1. Reads `.state/mode.json` using `pathlib.Path`
2. If file missing → return (development mode, allow startup)
3. If file corrupt/unreadable → return (allow startup with implied warning)
4. Parse JSON, extract `mode` field
5. If mode not in `("build", "both")` → write error to stderr, `sys.exit(78)`

Using `sys.stderr.write()` instead of `print()` to satisfy ruff T201. Using `sys.exit(78)` per sysexits convention (EX_CONFIG).

Consumed by: `if __name__ == "__main__"` block (called before `mcp.run()`), Phase 113 tests (TestModeGate class), Phase v13 (mirrored in state-teach).
</action>

<read_first>
- src/state_build/mcp.py
- .state/mode.json (verify current mode for test expectations)
</read_first>

<acceptance_criteria>
- `grep "_check_mode_gate" src/state_build/mcp.py` returns >=2 matches (def + call)
- Function exits 78 when mode=teach
- Function allows when mode=build
- Function allows when mode=both
- Function allows when mode.json is missing
- Function allows when mode.json is corrupt
- `ruff check` passes
</acceptance_criteria>

#### 01.2 Wire gate into server startup
**Acceptance:** `_check_mode_gate()` is called before `mcp.run(transport="stdio")` in `if __name__ == "__main__"`
**Estimated effort:** Small
**Dependencies:** 01.1

<action>
Modify the `if __name__ == "__main__"` block:

```python
if __name__ == "__main__":
    _check_mode_gate()
    mcp.run(transport="stdio")
```

This ensures the mode gate runs synchronously before the MCP server starts its asyncio event loop.

Consumed by: opencode MCP config (server command entry), CI integration tests (Phase 114).
</action>

<read_first>
- src/state_build/mcp.py (last 3 lines)
</read_first>

<acceptance_criteria>
- `grep "_check_mode_gate()" src/state_build/mcp.py` returns exactly 1 match (the call)
- Call appears on the line before `mcp.run(transport="stdio")`
- Server import still succeeds (gate is only called at runtime, not at import time)
</acceptance_criteria>

### Integration Notes
- The gate runs at import-time for the **main module** only — `from state_build.mcp import mcp` does NOT trigger the gate
- Phase 113 tests exercise the gate independently with temporary `.state/mode.json` files
- The gate does not depend on `state_core.schema.ModeConfig` — it's a lightweight pre-flight check
