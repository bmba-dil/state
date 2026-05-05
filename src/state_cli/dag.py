"""`state dag show` CLI — colored box-drawing DAG visualization.

D-01: Unicode box-drawing with Rich markup; ascii_only=False default.
D-02: Status colors mapped per CONTEXT.md decision.
D-03: Input modes: --demo, --file, or default (.state/dag.json).
D-04: --arc, --phase, --slice are mutually exclusive kind filters.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.text import Text

from src.state_core.scheduler import Edge, Node, topo_sort

app = typer.Typer(name="dag", help="DAG visualization and debugging commands")

# -- Status → Rich markup tag mapping (D-02) -----------------------------------

STATUS_STYLE: dict[str, str] = {
    "idle": "dim",
    "pending": "yellow",
    "in_progress": "bold cyan",
    "done": "green",
    "blocked": "red",
    "failed": "bold red",
}

# -- Box-drawing character sets -------------------------------------------------

UNICODE_BOX = {
    "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
    "h": "─", "v": "│",
    "t_down": "┬", "t_up": "┴", "t_right": "├", "t_left": "┤",
    "cross": "┼",
    "arrow_right": "►", "arrow_down": "▼",
}

ASCII_BOX = {
    "tl": "+", "tr": "+", "bl": "+", "br": "+",
    "h": "-", "v": "|",
    "t_down": "+", "t_up": "+", "t_right": "+", "t_left": "+",
    "cross": "+",
    "arrow_right": ">", "arrow_down": "v",
}


def _box_chars(ascii_only: bool = False) -> dict[str, str]:
    """Return the active box-drawing character set."""
    return ASCII_BOX if ascii_only else UNICODE_BOX


def _compute_inner_width(nodes: list[Node]) -> int:
    """Compute the inner box width based on max content length."""
    max_len = 0
    for node in nodes:
        content = f"{node.id}  [{node.status}]"
        max_len = max(max_len, len(content))
    return min(max(max_len + 2, 8), 60)


def _compute_depths(nodes: list[Node], edges: list[Edge]) -> dict[str, int]:
    """Compute depth for each node via BFS from roots.

    Root nodes (no incoming edges) have depth 0.
    Other nodes have depth = 1 + max(pred_depth).
    """
    node_ids = {n.id for n in nodes}

    # Build predecessor map (filtered to valid edges only)
    preds: dict[str, list[str]] = {n.id: [] for n in nodes}
    for e in edges:
        if e.source_node in node_ids and e.target_node in node_ids:
            preds[e.target_node].append(e.source_node)

    depths: dict[str, int] = {}

    # Identify roots
    roots = [n.id for n in nodes if not preds[n.id]]
    for root in roots:
        depths[root] = 0

    # Process remaining nodes in topo order
    try:
        ordered = topo_sort(edges, nodes)
    except ValueError:
        ordered = nodes  # fallback if cycle exists; topo_sort raises

    for node in ordered:
        if node.id in depths:
            continue
        max_pred = -1
        for pid in preds[node.id]:
            if pid in depths:
                max_pred = max(max_pred, depths[pid])
        depths[node.id] = max_pred + 1 if max_pred >= 0 else 0

    return depths


def _render_box_lines(
    node: Node,
    inner_width: int,
    bc: dict[str, str],
) -> list[str]:
    """Render a single node as 3 box lines (top, content, bottom).

    Returns [top_line, content_line, bottom_line].
    """
    outer_w = inner_width + 2

    top = bc["tl"] + bc["h"] * inner_width + bc["tr"]
    bottom = bc["bl"] + bc["h"] * inner_width + bc["br"]

    status_str = f"[{node.status}]"
    content = f"{node.id}  {status_str}"
    # Pad to inner_width
    if len(content) > inner_width:
        content = content[: inner_width - 1] + "…"
    pad_total = inner_width - len(content)
    left_pad = pad_total // 2
    right_pad = pad_total - left_pad
    content_line = bc["v"] + " " * left_pad + content + " " * right_pad + bc["v"]

    return [top, content_line, bottom]


def _render_colored_box_lines(
    node: Node,
    inner_width: int,
    bc: dict[str, str],
) -> list[str]:
    """Render a single node as 3 pre-colored box lines.

    Returns [top_line, content_line, bottom_line] with Rich markup already
    applied. Literal brackets in node statuses are escaped so Rich does not
    interpret them as markup tags.
    """
    style = STATUS_STYLE.get(node.status, "dim")
    plain = _render_box_lines(node, inner_width, bc)
    # Escape literal [ in the box lines so Rich doesn't interpret
    # status values like [in_progress] as markup tags. Only [ needs
    # escaping (\] is not a Rich escape sequence and literal ] is fine).
    escaped = [line.replace("[", "\\[") for line in plain]
    return [f"[{style}]{line}[/{style}]" for line in escaped]


def render_dag(
    nodes: list[Node],
    edges: list[Edge],
    *,
    filter_kind: str | None = None,
    ascii_only: bool = False,
) -> str:
    """Render a DAG as colored box-drawing art.

    Returns a string suitable for terminal output. Uses Rich markup for
    status colors. Unicode box-drawing by default; ASCII fallback via
    ascii_only=True.

    Args:
        nodes: All nodes in the DAG.
        edges: Directed dependency edges.
        filter_kind: If set, show only nodes of this kind ("arc", "phase",
            "slice", "step"). Edges are included only if both endpoints
            pass the filter.
        ascii_only: If True, use ASCII box-drawing characters instead of
            Unicode.

    Returns:
        A string with Rich markup tags for terminal rendering.

    Raises:
        ValueError: If an edge references a node not in the nodes list.
    """
    # Filter by kind
    if filter_kind is not None:
        filtered_ids = {n.id for n in nodes if n.kind == filter_kind}
        nodes = [n for n in nodes if n.id in filtered_ids]
        edges = [e for e in edges
                 if e.source_node in filtered_ids and e.target_node in filtered_ids]

    if not nodes:
        return ""

    # Validate: all edge endpoints must exist in node list
    node_ids = {n.id for n in nodes}
    for edge in edges:
        if edge.source_node not in node_ids:
            raise ValueError(
                f"Edge source '{edge.source_node}' not found in node list"
            )
        if edge.target_node not in node_ids:
            raise ValueError(
                f"Edge target '{edge.target_node}' not found in node list"
            )

    bc = _box_chars(ascii_only)

    # Compute depths via BFS
    depths = _compute_depths(nodes, edges)
    max_depth = max(depths.values()) if depths else 0

    # Sort nodes within each depth by topological order
    try:
        ordered = topo_sort(edges, nodes)
    except ValueError:
        ordered = nodes
    depth_rows: list[list[Node]] = [[] for _ in range(max_depth + 1)]
    for node in ordered:
        d = depths.get(node.id, 0)
        if d < len(depth_rows):
            depth_rows[d].append(node)

    # Compute box dimensions
    inner_width = _compute_inner_width(nodes)
    outer_width = inner_width + 2
    gap = 3  # horizontal gap between boxes

    # Compute column start positions for each node (used for connector alignment)
    node_cols: dict[str, int] = {}
    for row_nodes in depth_rows:
        x = 2  # left margin
        for node in row_nodes:
            node_cols[node.id] = x
            x += outer_width + gap

    # Build output: render each depth as a band, then merge vertically.
    # Strategy: each depth band is 4 lines (3 box lines + 1 connector),
    # but we want to overlay connectors between bands.
    # Instead, build all bands separately, then stitch with connectors.

    # Render each depth band as a list of 3 colored text lines.
    # To merge them horizontally, we build each depth line by line,
    # joining box segments with gap spaces.
    box_lines_per_depth: list[list[str]] = []  # [depth][line_idx] = str
    for row_nodes in depth_rows:
        band: list[str] = []
        for line_idx in range(3):
            segments: list[str] = []
            for i, node in enumerate(row_nodes):
                colored = _render_colored_box_lines(node, inner_width, bc)
                segments.append(colored[line_idx])
                if i < len(row_nodes) - 1:
                    segments.append(" " * gap)
            band.append("  " + "".join(segments))  # 2-space left margin
        box_lines_per_depth.append(band)

    # Build connector rows between depth bands
    connector_lines: list[str] = []  # one per gap between depths
    for depth_idx in range(len(depth_rows) - 1):
        row_nodes = depth_rows[depth_idx]
        next_row_nodes = depth_rows[depth_idx + 1]

        # Build connector line using a character grid approach.
        # We need the max visual width (without Rich tags) for alignment.
        # Use the next row's text width as reference.
        max_next_line = max(
            (len(_render_box_lines(n, inner_width, bc)[0]) for n in next_row_nodes),
            default=0,
        )
        # Estimate width: 2 + sum(box widths + gaps)
        n_next = len(next_row_nodes)
        total_plain_width = 2 + n_next * outer_width + max(0, (n_next - 1) * gap)

        connector: list[str] = [" "] * total_plain_width

        for src_node in row_nodes:
            out_edges = [
                e for e in edges
                if e.source_node == src_node.id
                and depths.get(e.target_node) == depth_idx + 1
            ]
            if not out_edges:
                continue

            # Source center column (visual, not counting Rich tags)
            src_col_idx = depth_rows[depth_idx].index(src_node)
            src_center = 2 + src_col_idx * (outer_width + gap) + outer_width // 2

            if src_center < total_plain_width:
                connector[src_center] = bc["v"]

            for edge in out_edges:
                if edge.target_node not in node_cols:
                    continue
                tgt_col_idx = depth_rows[depth_idx + 1].index(
                    next(n for n in depth_rows[depth_idx + 1] if n.id == edge.target_node)
                )
                tgt_center = 2 + tgt_col_idx * (outer_width + gap) + outer_width // 2

                if tgt_center >= total_plain_width:
                    continue

                x_min = min(src_center, tgt_center)
                x_max = max(src_center, tgt_center)
                for cx in range(x_min, x_max + 1):
                    if cx == src_center:
                        continue
                    existing = connector[cx]
                    if existing == " " or existing == bc["v"]:
                        connector[cx] = bc["h"]
                    elif existing == bc["h"]:
                        pass
                    else:
                        connector[cx] = bc["cross"]

                # Junction at target
                existing = connector[tgt_center]
                if existing in (bc["h"], bc["cross"]):
                    if tgt_center == src_center:
                        connector[tgt_center] = bc["t_down"]
                    elif tgt_center > src_center:
                        connector[tgt_center] = bc["t_left"]
                    else:
                        connector[tgt_center] = bc["t_right"]
                elif existing == bc["v"]:
                    connector[tgt_center] = bc["t_up"]

        connector_lines.append("".join(connector).rstrip())

    # Stitch everything together
    result_lines: list[str] = []
    for depth_idx in range(len(depth_rows)):
        result_lines.extend(box_lines_per_depth[depth_idx])
        if depth_idx < len(depth_rows) - 1:
            result_lines.append(connector_lines[depth_idx])

    return "\n".join(result_lines)


# -- Demo DAG builder (D-03) --------------------------------------------------


def _build_demo_dag() -> tuple[list[Node], list[Edge]]:
    """Build a sample DAG covering all node kinds, statuses, and edge types.

    Returns (nodes, edges) representing a realistic multi-layer DAG
    with at least 5 nodes, mixed statuses, and 3+ edges.
    """
    nodes = [
        Node(id="arc-1", kind="arc", status="done"),
        Node(id="arc-2", kind="arc", status="idle"),
        Node(id="phase-1", kind="phase", status="done"),
        Node(id="phase-2", kind="phase", status="in_progress"),
        Node(id="phase-3", kind="phase", status="pending"),
        Node(id="slice-1", kind="slice", status="done"),
        Node(id="slice-2", kind="slice", status="blocked"),
        Node(id="slice-3", kind="slice", status="failed"),
        Node(id="step-1", kind="step", status="done"),
        Node(id="step-2", kind="step", status="in_progress"),
        Node(id="step-3", kind="step", status="idle"),
    ]

    edges = [
        Edge(source_node="arc-1", target_node="phase-1", kind="blocks"),
        Edge(source_node="arc-2", target_node="phase-2", kind="blocks"),
        Edge(source_node="arc-2", target_node="phase-3", kind="blocks"),
        Edge(source_node="phase-1", target_node="slice-1", kind="blocks"),
        Edge(source_node="phase-2", target_node="slice-2", kind="blocks"),
        Edge(source_node="phase-3", target_node="slice-3", kind="soft"),
        Edge(source_node="slice-1", target_node="step-1", kind="blocks"),
        Edge(source_node="slice-2", target_node="step-2", kind="blocks"),
        Edge(source_node="slice-3", target_node="step-3", kind="data"),
    ]

    return nodes, edges


# -- Typer show command (D-03, D-04) ------------------------------------------


@app.command(name="show")
def show(
    arc: bool = typer.Option(False, "--arc", help="Show only arc-level nodes"),
    phase: bool = typer.Option(False, "--phase", help="Show only phase-level nodes"),
    slice: bool = typer.Option(False, "--slice", help="Show only slice-level nodes"),
    file: str | None = typer.Option(None, "--file", help="Load DAG from JSON file"),
    demo: bool = typer.Option(False, "--demo", help="Show sample DAG for testing"),
) -> None:
    """Render current DAG state as colored box-drawing art."""
    # Validate mutual exclusion of filters
    active_filters = [f for f, flag in
                      [("arc", arc), ("phase", phase), ("slice", slice)]
                      if flag]
    if len(active_filters) > 1:
        typer.echo(
            f"Error: --arc, --phase, and --slice are mutually exclusive. "
            f"Only one filter may be specified at a time.",
            err=True,
        )
        raise typer.Exit(code=2)

    filter_kind: str | None = active_filters[0] if len(active_filters) == 1 else None

    # Determine input source
    if demo:
        nodes, edges = _build_demo_dag()
    elif file is not None:
        try:
            data = json.loads(Path(file).read_text(encoding="utf-8"))
        except FileNotFoundError:
            typer.echo(f"Error: File not found: {file}", err=True)
            raise typer.Exit(code=1)
        except json.JSONDecodeError as exc:
            typer.echo(f"Error: Invalid JSON in {file}: {exc}", err=True)
            raise typer.Exit(code=1)

        try:
            nodes = [Node(**n) for n in data.get("nodes", [])]
            edges = [Edge(**e) for e in data.get("edges", [])]
        except Exception as exc:
            typer.echo(f"Error: Invalid DAG data in {file}: {exc}", err=True)
            raise typer.Exit(code=1)
    else:
        dag_path = Path(".state/dag.json")
        if not dag_path.is_file():
            typer.echo(
                "No DAG state found. Use --demo or --file.",
                err=True,
            )
            raise typer.Exit(code=1)
        try:
            data = json.loads(dag_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            typer.echo(f"Error loading DAG state: {exc}", err=True)
            raise typer.Exit(code=1)
        try:
            nodes = [Node(**n) for n in data.get("nodes", [])]
            edges = [Edge(**e) for e in data.get("edges", [])]
        except Exception as exc:
            typer.echo(f"Error: Invalid DAG state: {exc}", err=True)
            raise typer.Exit(code=1)

    # Render
    try:
        result = render_dag(nodes, edges, filter_kind=filter_kind)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    console = Console(width=200, soft_wrap=True)
    if result:
        console.print(result)
    else:
        typer.echo("(empty DAG)")
