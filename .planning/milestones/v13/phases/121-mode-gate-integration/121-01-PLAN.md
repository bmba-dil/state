---
phase: 121
phase_name: mode-gate-integration
wave: 1
depends_on: ["097"]
files_modified:
  - src/state_teach/mcp.py
  - tests/test_state_teach_mcp.py
requirements:
  - MCP-T-01
  - MODE-03
autonomous: true
must_haves:
  truths:
    - "state-teach refuses to start when mode=build (exits 78)"
    - "state-teach starts normally when mode=teach or mode=both"
    - "state-teach starts normally when mode.json is missing or corrupt"
    - "Gate pattern matches Phase 112: lightweight inline JSON parse, sys.stderr.write(), sys.exit(78)"
    - "No state_core.schema dependency in the mode gate (pre-flight check stands alone)"
    - "MODE-03 satisfied: state-teach only starts when mode in {teach, both}"
  artifacts:
    - path: "src/state_teach/mcp.py"
      provides: "Lightweight mode-gate function _check_mode_gate() matching Phase 112 pattern"
      contains: "def _check_mode_gate"
    - path: "tests/test_state_teach_mcp.py"
      provides: "Updated mode-gate tests for new behavior"
      contains: "test_mode_gate"
  key_links:
    - from: "src/state_teach/mcp.py"
      to: "Phase 112 pattern in src/state_build/mcp.py"
      via: "mirrors"
      pattern: "_check_mode_gate() with inline json, sys.stderr.write, sys.exit(78)"
---

<objective>
Refactor the Phase 115 `check_mode_gate()` to match the Phase 112 pattern: lightweight inline JSON parsing, `sys.stderr.write()` for errors, `sys.exit(78)` for mode mismatch, no structlog or state_core.schema dependency. Ensure MODE-03 compliance — state-teach refuses to start when mode=build.
</objective>

<context>
@src/state_teach/mcp.py
@src/state_build/mcp.py (Phase 112 reference implementation)
@tests/test_state_teach_mcp.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Refactor check_mode_gate to match Phase 112 pattern</name>
  <files>src/state_teach/mcp.py</files>
  <action>
1. Rename `check_mode_gate` → `_check_mode_gate` (private function convention from Phase 112).

2. Remove structlog dependency:
   - Delete `import structlog` (line 10)
   - Delete `log = structlog.get_logger(__name__)` (line 16)

3. Remove state_core.schema dependency:
   - Delete `from state_core.schema import validate_mode_config` (line 14)

4. Rewrite `_check_mode_gate` body to match Phase 112 pattern:
   ```python
   def _check_mode_gate(project_root: Path) -> None:
       """Verify mode.json allows state-teach to run.

       Reads .state/mode.json and exits with a clear error if the active
       mode is 'build'. Called before the server starts.

       Args:
           project_root: Project root directory (where .state/ lives).

       Raises:
           SystemExit(78): If mode is 'build'.
       """
       mode_path = project_root / ".state" / "mode.json"
       if not mode_path.exists():
           return  # No mode file — allow startup (development mode)

       try:
           data = json.loads(mode_path.read_text())
           mode = data.get("mode")
       except (json.JSONDecodeError, OSError):
           return  # Corrupt or unreadable — allow startup

       if mode not in ("teach", "both"):
           sys.stderr.write(
               f"state-teach: mode mismatch — .state/mode.json has mode={mode}, "
               f"but state-teach requires mode=teach or mode=both.\n",
           )
           sys.exit(78)  # EX_CONFIG: configuration error
   ```

   Key differences from current Phase 115 implementation:
   - Uses inline `json.loads()` instead of `validate_mode_config()` → no schema dependency
   - Uses `sys.stderr.write()` instead of `structlog` → no logging dependency
   - Uses `sys.exit(78)` instead of `sys.exit(1)` → sysexits convention (matches 112)
   - Corrupt/unreadable JSON → return silently (matches 112 leniency; was `sys.exit(1)` in 115)
   - Keeps `project_root: Path` parameter (better testability than 112's CWD-relative path)

5. Update the `if __name__ == "__main__"` block to call `_check_mode_gate`:
   ```python
   if __name__ == "__main__":
       _check_mode_gate(Path.cwd())
       asyncio.run(mcp.run_stdio_async())
   ```
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_state_teach_mcp.py -v</automated>
    <automated>python3 -m ruff check src/state_teach/mcp.py</automated>
  </verify>
  <done>_check_mode_gate uses lightweight inline JSON with no structlog/schema dependency. sys.stderr.write() + sys.exit(78) on build mode. Corrupt/missing mode.json allows startup. Called from __main__ block.</done>
</task>

<task type="auto">
  <name>Task 2: Update tests for the refactored mode gate</name>
  <files>tests/test_state_teach_mcp.py</files>
  <action>
Update all test references and assertions to match the refactored `_check_mode_gate`:

1. Update import (line 15): `check_mode_gate` → `_check_mode_gate`

2. Update all `check_mode_gate(tmp_path)` calls to `_check_mode_gate(tmp_path)` (5 occurrences at lines 32, 43, 53, 58, 69, 81, 183, 188)

3. Update exit code assertions:
   - `test_mode_gate_rejects_build` (line 33): `assert exc_info.value.code == 1` → `== 78`
   - `test_mode_gate_invalid_json` (line 68-70): This test should now expect the function to **return normally** (no SystemExit) since corrupt JSON now allows startup (matching Phase 112 leniency). Change from `pytest.raises(SystemExit)` to a simple call with no exception.
   - `test_mode_gate_invalid_mode_value` (line 82): `assert exc_info.value.code == 1` → `== 78`

4. `test_mode_gate_still_works_after_tool_registration` (line 183-184): Update exit code from `1` to `78`
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_state_teach_mcp.py -v</automated>
  </verify>
  <done>All 12 tests pass. Exit codes updated to 78. Corrupt JSON test now expects normal return. No stale references to check_mode_gate remain.</done>
</task>

<task type="auto">
  <name>Task 3: Verify MODE-03 compliance and code quality</name>
  <files>src/state_teach/mcp.py, tests/test_state_teach_mcp.py</files>
  <action>
Run comprehensive verification:

1. Full test suite: `python3 -m pytest tests/test_state_teach_mcp.py -v`
2. Ruff check: `python3 -m ruff check src/state_teach/mcp.py`
3. Import lint: `python3 -m pytest tests/test_state_teach_mcp.py::test_import_lint_clean -v`
4. Verify no structlog or validate_mode_config references remain in mcp.py:
   - `grep -c "structlog" src/state_teach/mcp.py` must be 0
   - `grep -c "validate_mode_config" src/state_teach/mcp.py` must be 0
5. MODE-03 verification: state-teach exits 78 when mode=build, starts when mode∈{teach,both}

MODE-03 requirement: "MCP server registration — state-build only started when mode in {build, both}; state-teach only when {teach, both}"
- ✓ state-teach mode gate rejects mode=build (exit 78)
- ✓ state-teach mode gate allows mode=teach
- ✓ state-teach mode gate allows mode=both
- ✓ state-build mode gate (Phase 112) rejects mode=teach
- ✓ Combined: each server only starts in its allowed mode set
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_state_teach_mcp.py -v</automated>
    <automated>python3 -m ruff check src/state_teach/mcp.py</automated>
  </verify>
  <done>All tests pass. Ruff clean. No structlog/validate_mode_config in mcp.py. MODE-03 satisfied.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| mode.json file → _check_mode_gate parser | Untrusted JSON from disk enters lightweight pre-flight check |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-121-01 | Tampering | mode.json content | mitigate | Inline JSON parsing checks mode field against allowlist ("teach", "both"); anything else triggers exit 78 |
| T-121-02 | Information Disclosure | Error message | accept | stderr message reveals current mode — this is intentional for debugging; mode is not a secret |
| T-121-03 | Denial of Service | mode.json | mitigate | Corrupt/missing files return silently — do not prevent startup in development mode |
</threat_model>

<verification>
```bash
# Full test suite for state-teach MCP
python3 -m pytest tests/test_state_teach_mcp.py -v

# Ruff lint
python3 -m ruff check src/state_teach/mcp.py

# Import lint (cross-mode violation check)
python3 -m pytest tests/test_state_teach_mcp.py::test_import_lint_clean -v

# Verify no stale dependencies
grep -c "structlog" src/state_teach/mcp.py        # Expected: 0
grep -c "validate_mode_config" src/state_teach/mcp.py  # Expected: 0
grep -c "_check_mode_gate" src/state_teach/mcp.py   # Expected: >=2 (def + call)
```
</verification>

<success_criteria>
1. `_check_mode_gate()` follows Phase 112 lightweight pattern (inline JSON, sys.stderr.write, sys.exit(78))
2. No structlog or state_core.schema dependency in the mode gate
3. state-teach refuses to start when mode=build (exit 78)
4. state-teach allows startup when mode=teach, mode=both, missing mode.json, or corrupt mode.json
5. All 12 existing tests pass with updated assertions
6. Ruff lint passes clean
7. Import lint passes (no cross-mode violations)
8. MODE-03 satisfied: state-teach only starts when mode ∈ {teach, both}
</success_criteria>

<output>
After completion, create `.planning/milestones/v13/phases/121-mode-gate-integration/121-SUMMARY.md`
</output>
