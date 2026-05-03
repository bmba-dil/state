---
phase: "010.1"
plan: "A"
type: "gap_closure"
autonomous: false
wave: 1
depends_on: []
files_modified:
  - "src/state_cli/main.py"
requirements:
  - "EVT-04"
  - "EVT-05"
---

<objective>
Add a Typer callback to validate the `--mode` flag against the `Mode` literal (`"build"`, `"teach"`, `"kernel"`) in `src/state_cli/main.py`. All three CLI commands (`tail`, `replay`, `export`) currently accept any string for `--mode`; invalid modes silently return 0 rows instead of raising an error. This plan adds a shared `_validate_mode()` callback and wires it as a Typer `callback` parameter on the `mode` option of all three commands.
</objective>

<tasks>

### Task 1: Add `_validate_mode` callback and wire into all three `--mode` options

<read_first>
- `src/state_cli/main.py` (full file — understand current structure)
- `src/state_core/schema.py` (line 17: `Mode = Literal["build", "teach", "kernel"]` definition)
- `tests/test_cli.py` (lines 302–316: `test_invalid_mode_rejected` — existing test that documents current behavior)
</read_first>

<action>
1. Add a `_validate_mode` function to `src/state_cli/main.py` that:
   - Accepts an optional `str | None` value
   - If `None`, returns `None` (no flag passed — no validation needed)
   - If the value is not one of `"build"`, `"teach"`, `"kernel"`, raises `typer.BadParameter(f"Invalid mode: {value!r}. Must be 'build', 'teach', or 'kernel'.")`
   - Otherwise returns the value unchanged

2. Wire `_validate_mode` into all three `--mode` Typer options:
   - `tail()`: `mode: str = typer.Option(None, "--mode", help=..., callback=_validate_mode)`
   - `replay()`: `mode: str = typer.Option(None, "--mode", help=..., callback=_validate_mode)`
   - `export()`: `mode: str = typer.Option(None, "--mode", help=..., callback=_validate_mode)`
   - Keep existing help text on each.

3. **Update `test_cli.py`** — Change `test_invalid_mode_rejected` to assert `exit_code == 2` (Typer exits with code 2 on `BadParameter`) for all three commands instead of the current `exit_code in (0, 2)`.

4. Run `ruff check src/state_cli/main.py tests/test_cli.py --fix` and `mypy src/state_cli/main.py` to confirm no lint or type errors.
</action>

<acceptance_criteria>
- `grep -c "def _validate_mode" src/state_cli/main.py` returns 1
- `grep -c "callback=_validate_mode" src/state_cli/main.py` returns 3 (one per command)
- `pytest tests/test_cli.py::TestEdgeCases::test_invalid_mode_rejected -x` passes (exit_code == 2 for all three)
- `python3 -c "from typer.testing import CliRunner; from src.state_cli.main import app; r=CliRunner().invoke(app, ['events','tail','--no-follow','--mode','invalid']); assert r.exit_code == 2"` exits 0
</acceptance_criteria>

</tasks>

<verification>
1. Run the full CLI test suite: `pytest tests/test_cli.py -x -v`
2. Manual: `python3 -m src.state_cli.main events tail --no-follow --mode invalid` must exit with code 2 and print an error.
3. Manual: `python3 -m src.state_cli.main events tail --no-follow --mode build` must succeed (exit 0).
4. Confirm `ruff check src/state_cli/main.py` passes.
</verification>

<must_haves>
- A single `_validate_mode` callback function, not duplicated per command
- Typer's `BadParameter` exception used (not a custom exception or manual `sys.exit`)
- Existing `test_invalid_mode_rejected` test updated to assert `exit_code == 2` for all three commands
- No changes to `src/state_core/` files
</must_haves>

<threat_model>
**ASVS L1 coverage:**
- **V5.1 (Input Validation):** The `_validate_mode` callback ensures that `--mode` values are constrained to the `Mode` literal set. Invalid values raise `BadParameter` before any query executes, preventing SQL injection via the `mode` parameter (though SQLite parameterized queries already provide defense-in-depth).
- **V7.1 (Error Handling):** Typer's built-in error output for `BadParameter` discloses the valid set via the error message. This is intentional — mode values are not secrets.
- No secrets, credentials, or PII flow through `--mode`. No escalation risk.
</threat_model>
