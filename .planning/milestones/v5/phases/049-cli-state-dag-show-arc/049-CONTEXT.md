# Phase 049 — CONTEXT.md

**Phase:** `state dag show [--arc|--phase|--slice]` CLI with ASCII box-drawing + status colors
**Milestone:** v5 — DAG Scheduler
**Requirement:** DAG-07

---

## Decisions

### D-01: Box-drawing character set
**Decision:** Use Unicode box-drawing characters (┌─┐│└─┘├─┤┴─┬──►) via Rich markup, with pure-ASCII fallback in the render engine.
**Rationale:** All modern terminals support Unicode. The ROADMAP says "ASCII" informally — Unicode box-drawing is the standard for CLI tools in 2026. The render engine includes an `ascii_only=False` parameter for environments that truly need ASCII.

### D-02: Status color mapping
**Decision:** Use these Rich style mappings:
- `idle` → dim white
- `pending` → yellow
- `in_progress` → bold cyan
- `done` → green
- `blocked` → red
- `failed` → bold red

### D-03: DAG input source
**Decision:** The `show` command accepts three input modes:
1. `--demo` flag — renders a built-in sample DAG (for testing/demo)
2. `--file <path>` — loads nodes + edges from a JSON file
3. Default — reads from `.state/dag.json` if it exists, otherwise shows help
**Rationale:** No persistent DAG store exists yet (phases 045-048 build it). The CLI must be functional and testable now. When persistent state arrives, the default path upgrades naturally.

### D-04: Filter behavior
**Decision:** `--arc`, `--phase`, `--slice` are exclusive filters (only one may be specified). They filter displayed nodes to that `kind` value. Edges are included only if both endpoints pass the filter.
**Rationale:** Per requirement DAG-07, these are `[--arc|--phase|--slice]` — the bracket notation means mutually exclusive options.

### D-05: Property test scope
**Decision:** The Hypothesis property test covers the `render_dag()` function directly (not the CLI invocation). Strategy: generate valid `list[Node]` + `list[Edge]` pairs where all edge endpoints reference existing nodes, then assert the render function completes without raising an exception and returns a non-empty string.
**Rationale:** Testing via CLI runner would add irrelevant failure modes (Typer parsing, IO). Testing the pure function is the correct unit for "any valid graph renders without crash."

---

## Deferred Ideas

None — all requirements in scope.

## Claude's Discretion

- Exact box-drawing layout algorithm (vertical vs horizontal, indentation depth)
- Internal helper function structure in `dag.py`
- Rich Console configuration (width, color system)
- Edge representation style (arrows, lines, tree-drawing)
