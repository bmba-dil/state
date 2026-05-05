---
phase: 049-cli-state-dag-show-arc
plan: 01
subsystem: dag-cli
tags: [cli, visualization, rich, dag, box-drawing]
requires:
  provides: render_dag(), dag show CLI, Hypothesis property test
  affects: [dag-visualization, scheduler-ui, terminal-output]
tech-stack:
  added: [rich>=13.9, hypothesis>=6.120]
  patterns: [typer-sub-app, rich-console-markup, hypothesis-property-test, box-drawing-grid-layout]
key-files:
  created:
    - src/state_cli/dag.py (445 lines)
    - tests/test_dag_cli.py (269 lines)
  modified:
    - src/state_cli/main.py (+4 lines)
key-decisions:
  - "Rich markup applied per-box during rendering to avoid character-index shifting from nested style tags"
  - "Status brackets escaped with \\[ to prevent Rich from interpreting [in_progress] etc. as markup"
  - "Console(width=200) prevents Rich from wrapping wide DAG output at 80 columns in non-TTY (CliRunner)"
  - "Connector width computed as max(current_row_width, next_row_width) to handle wider source rows"
  - "Hypothesis generates edges deterministically (seed=42) within test body using generated node IDs"
patterns-established:
  - "CLI sub-app registration: import + app.add_typer() with # noqa: E402 comment, chronological ordering"
  - "Rich bracket escaping: use \\[ for literal [ in markup text (only opening brackets need escaping)"
  - "Box-drawing layout: BFS depths + topological sort order → grid-based row/column placement + connector rows"
requirements-completed:
  - DAG-07
metrics:
  duration: "~30m"
  completed: 2026-05-04
---

# Phase 049 Plan 01: `state dag show` CLI Summary

**One-liner:** Built a terminal DAG visualizer with Unicode box-drawing, Rich status colors, and Hypothesis-guaranteed crash-free rendering.

## Tasks Executed

| # | Name | Commit | Type |
|---|------|--------|------|
| 1 | Create dag CLI module with render_dag engine and show command | `63d0c97` | feat |
| 2 | Wire dag sub-app into state_cli main | `a71af1f` | feat |
| 3 | Create tests for dag CLI and Hypothesis property test | `98c64f1` | test |

## What Was Built

### `src/state_cli/dag.py` (443 lines)

**`render_dag(nodes, edges, *, filter_kind=None, ascii_only=False) -> str`**
Pure function that renders a DAG as colored box-drawing art:

1. **Filtering** — `filter_kind` selects only nodes of the given kind ("arc", "phase", "slice", "step"). Edges are included only if both endpoints pass the filter.
2. **Validation** — Raises `ValueError` if any edge endpoint references a node not in the list, matching the established `frontier()`/`topo_sort()` pattern.
3. **Layout** — BFS computes depths from root nodes (no incoming edges). Topological sort determines left-to-right order within each depth level. Nodes at the same depth render side-by-side; edges draw as connecting lines between rows.
4. **Box rendering** — Unicode box-drawing (┌─┐│└┘├┤┴┬) by default; ASCII (+-|) when `ascii_only=True`. Content shows `node_id [status]` centered in each box.
5. **Rich colors** — Each box is wrapped in Rich markup: `[dim]` (idle), `[yellow]` (pending), `[bold cyan]` (in_progress), `[green]` (done), `[red]` (blocked), `[bold red]` (failed).
6. **Bracket escaping** — Node statuses like `[in_progress]` are escaped to `\[in_progress]` so Rich doesn't interpret them as style tags.

**CLI sub-app (`dag`)**: Typer app with a single `show` command supporting:
- `--demo` — renders a built-in sample DAG (11 nodes, 9 edges, all statuses and edge kinds)
- `--file <path>` — loads nodes+edges from JSON
- Default — reads `.state/dag.json` (or shows help if absent)
- `--arc`, `--phase`, `--slice` — mutually exclusive kind filters

### `src/state_cli/main.py` (+4 lines)

Registered `dag_app` via `app.add_typer(dag_app)` following the established `auth_app`/`snapshot_app` pattern. `state --help` now lists `dag` subcommand.

### `tests/test_dag_cli.py` (269 lines)

**18 tests, all passing:**
- **9 CLI integration tests** (TestShow): help output, demo rendering, filter flags, mutual exclusion, file not found, no-state default, valid JSON file
- **7 render_dag unit tests** (TestRenderDag): empty input, single node, two-node edge, ghost edge validation (both source and target), Rich markup presence for all 6 statuses, ASCII-only mode verification
- **1 Hypothesis property test** (TestHypothesis): `@given` generates up to 20 random nodes with valid edges, asserts `render_dag()` never crashes — 200 examples, zero failures
- **1 bug found by Hypothesis**: Connector width calculation used only the next row's width, causing `IndexError` when source row was wider. Fixed by computing `max(current_width, next_width)`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Connector width calculation caused IndexError on wider source rows**
- **Found during:** Task 3 (Hypothesis test)
- **Issue:** `total_plain_width` was computed from the next row's node count only. When the current (source) row had more nodes, `src_center` positions exceeded the connector array bounds.
- **Fix:** Changed `total_plain_width = max(cur_width, next_width)` where both are computed as `2 + n * outer_width + max(0, (n-1) * gap)`.
- **Files modified:** `src/state_cli/dag.py`
- **Commit:** `98c64f1`

**2. [Rule 1 - Bug] Rich markup bracket escaping needed only opening brackets**
- **Found during:** Task 1 (demo output showed `[done\]` with trailing backslash)
- **Issue:** Escaping both `[` and `]` caused `\]` to appear literally in non-TTY output. Rich only recognises `\[` as an escape sequence.
- **Fix:** Changed to escape only opening brackets: `line.replace("[", "\\[")`.
- **Files modified:** `src/state_cli/dag.py`
- **Commit:** `63d0c97`

**3. [Rule 1 - Bug] Rich Console wrapped box-drawing art at 80 columns**
- **Found during:** Task 1 (--demo output showed split box lines in CliRunner)
- **Issue:** Default `Console()` has width=80 in non-TTY mode, causing Rich to insert line breaks mid-box.
- **Fix:** Set `Console(width=200, soft_wrap=True)` in the `show` command.
- **Files modified:** `src/state_cli/dag.py`
- **Commit:** `63d0c97`

**4. [Rule 2 - Missing] Status labels interpreted as Rich markup tags**
- **Found during:** Task 1 (statuses like `[in_progress]` were stripped from CliRunner output)
- **Issue:** Rich interpreted `[in_progress]`, `[done]`, etc. as style tags and stripped them in non-TTY rendering.
- **Fix:** Added `\[` escaping for literal brackets in `_render_colored_box_lines()` before wrapping in style tags.
- **Files modified:** `src/state_cli/dag.py`
- **Commit:** `63d0c97`

## Known Stubs

None — all data sources are wired. The demo DAG is self-contained. File-based and default-path loading are fully functional.

## Threat Flags

None — all threats from the plan's threat model are mitigated:
- T-049-01 (JSON tampering): pydantic validation on file input
- T-049-02 (ghost references): ValueError raised on missing edge endpoints
- T-049-03 (DoS): iterative loops, no recursion
- T-049-04 (info disclosure): node IDs are project-internal identifiers
- T-049-05 (EoP): read-only command, no mutation

## Self-Check: PASSED

- `src/state_cli/dag.py` exists (443 lines)
- `src/state_cli/main.py` modified (dag import + add_typer)
- `tests/test_dag_cli.py` exists (269 lines)
- Commits verified: `63d0c97`, `a71af1f`, `98c64f1`
- All 18 tests pass
- `state dag show --demo` renders colored box-drawing DAG
