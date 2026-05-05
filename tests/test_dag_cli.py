"""Tests for state_cli.dag — CLI integration and Hypothesis property tests."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

import pytest
import structlog
from typer.testing import CliRunner

# Suppress structlog noise during CLI tests (matches test_cli.py pattern)
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
)

from hypothesis import given, settings
from hypothesis import strategies as st

from src.state_cli.dag import render_dag
from src.state_cli.main import app as main_app
from src.state_core.scheduler import Edge, Node

# ── Fixtures ──────────────────────────────────────────────────────────────

runner = CliRunner()


# ── TestShow — CLI integration tests ──────────────────────────────────────


class TestShow:
    """state dag show command — CLI integration tests."""

    def test_show_help(self) -> None:
        """--help shows expected options."""
        result = runner.invoke(main_app, ["dag", "show", "--help"])
        assert result.exit_code == 0
        assert "--demo" in result.stdout
        assert "--arc" in result.stdout
        assert "--phase" in result.stdout
        assert "--slice" in result.stdout
        assert "--file" in result.stdout

    def test_show_demo(self) -> None:
        """--demo exits 0 and produces output with status labels."""
        result = runner.invoke(main_app, ["dag", "show", "--demo"])
        assert result.exit_code == 0
        assert len(result.stdout) > 50
        # Should contain at least one status label
        assert "[done]" in result.stdout or "[idle]" in result.stdout

    def test_show_filter_arc(self) -> None:
        """--arc filter shows only arc-kind nodes."""
        result = runner.invoke(main_app, ["dag", "show", "--demo", "--arc"])
        assert result.exit_code == 0
        # Demo has 2 arcs; phase/slice/step should not appear
        assert "arc-1" in result.stdout
        assert "arc-2" in result.stdout
        # Step nodes should be filtered out (lenient — only check that
        # step-specific IDs aren't present when arcs are the only kind shown)
        assert "slice-" not in result.stdout

    def test_show_filter_phase(self) -> None:
        """--phase filter exits 0."""
        result = runner.invoke(main_app, ["dag", "show", "--demo", "--phase"])
        assert result.exit_code == 0
        assert "phase-" in result.stdout

    def test_show_filter_slice(self) -> None:
        """--slice filter exits 0."""
        result = runner.invoke(main_app, ["dag", "show", "--demo", "--slice"])
        assert result.exit_code == 0
        assert "slice-" in result.stdout

    def test_show_mutual_exclusion(self) -> None:
        """Multiple filter flags produce error."""
        result = runner.invoke(main_app, ["dag", "show", "--arc", "--phase"])
        assert result.exit_code == 2

    def test_show_file_not_found(self) -> None:
        """--file with nonexistent path exits 1."""
        result = runner.invoke(
            main_app, ["dag", "show", "--file", "/nonexistent/path.json"]
        )
        assert result.exit_code == 1

    def test_show_no_state_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default (no --demo/--file) with no .state/dag.json exits 1."""
        # Change to tmp directory where .state/dag.json doesn't exist
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main_app, ["dag", "show"])
        assert result.exit_code == 1
        assert "No DAG state found" in result.stderr or "No DAG state found" in result.stdout

    def test_show_file_valid_json(self, tmp_path: Path) -> None:
        """--file with valid JSON DAG renders correctly."""
        dag_data = {
            "nodes": [
                {"id": "n1", "kind": "step", "status": "done"},
                {"id": "n2", "kind": "step", "status": "idle"},
            ],
            "edges": [
                {"source_node": "n1", "target_node": "n2", "kind": "blocks"},
            ],
        }
        file_path = tmp_path / "test_dag.json"
        file_path.write_text(json.dumps(dag_data))

        result = runner.invoke(main_app, ["dag", "show", "--file", str(file_path)])
        assert result.exit_code == 0
        assert "n1" in result.stdout
        assert "n2" in result.stdout


# ── TestRenderDag — render_dag() unit tests ───────────────────────────────


class TestRenderDag:
    """render_dag() pure function — unit tests."""

    def test_render_dag_empty(self) -> None:
        """Empty nodes/edges returns empty string."""
        assert render_dag([], []) == ""

    def test_render_dag_single_node(self) -> None:
        """One idle node renders a box containing the node ID."""
        nodes = [Node(id="test-node", kind="step", status="idle")]
        result = render_dag(nodes, [])
        assert "test-node" in result
        assert "idle" in result
        assert len(result) > 0

    def test_render_dag_two_nodes_with_edge(self) -> None:
        """Two nodes with blocks edge — both appear in output."""
        nodes = [
            Node(id="src", kind="step", status="done"),
            Node(id="tgt", kind="step", status="idle"),
        ]
        edges = [Edge(source_node="src", target_node="tgt", kind="blocks")]
        result = render_dag(nodes, edges)
        assert "src" in result
        assert "tgt" in result

    def test_render_dag_ghost_edge_raises(self) -> None:
        """Edge referencing nonexistent node raises ValueError."""
        nodes = [Node(id="a", kind="step", status="idle")]
        ghost_edge = Edge(source_node="a", target_node="ghost", kind="blocks")
        with pytest.raises(ValueError, match="ghost"):
            render_dag(nodes, [ghost_edge])

    def test_render_dag_ghost_source_raises(self) -> None:
        """Edge with nonexistent source raises ValueError."""
        nodes = [Node(id="a", kind="step", status="idle")]
        ghost_edge = Edge(source_node="ghost", target_node="a", kind="blocks")
        with pytest.raises(ValueError, match="ghost"):
            render_dag(nodes, [ghost_edge])

    def test_render_dag_status_colors(self) -> None:
        """All 6 statuses produce Rich markup tags."""
        nodes = [
            Node(id="a", kind="step", status="idle"),
            Node(id="b", kind="step", status="pending"),
            Node(id="c", kind="step", status="in_progress"),
            Node(id="d", kind="step", status="done"),
            Node(id="e", kind="step", status="blocked"),
            Node(id="f", kind="step", status="failed"),
        ]
        result = render_dag(nodes, [])
        # Rich style tags must appear in the output
        assert "[dim]" in result
        assert "[yellow]" in result
        assert "[bold cyan]" in result
        assert "[green]" in result
        assert "[red]" in result
        assert "[bold red]" in result

    def test_render_dag_ascii_only(self) -> None:
        """ascii_only=True uses no Unicode box-drawing characters."""
        nodes = [
            Node(id="x", kind="step", status="done"),
            Node(id="y", kind="step", status="idle"),
        ]
        edges = [Edge(source_node="x", target_node="y", kind="blocks")]
        result = render_dag(nodes, edges, ascii_only=True)
        # Must NOT contain Unicode box-drawing
        for ch in "┌─┐│└┘├┤┴┬┼►▼":
            assert ch not in result, f"Unicode char {ch!r} found in ASCII mode"
        # Must contain ASCII box chars
        assert "+" in result
        assert "-" in result
        assert "|" in result

    def test_render_dag_filter_kind(self) -> None:
        """filter_kind parameter filters both nodes and edges."""
        nodes = [
            Node(id="a1", kind="arc", status="done"),
            Node(id="p1", kind="phase", status="idle"),
        ]
        edges = [Edge(source_node="a1", target_node="p1", kind="blocks")]
        # Filter to arc only
        result = render_dag(nodes, edges, filter_kind="arc")
        assert "a1" in result
        assert "p1" not in result
        # Filter to phase only
        result = render_dag(nodes, edges, filter_kind="phase")
        assert "p1" in result
        assert "a1" not in result


# ── TestHypothesis — property test for render_dag ─────────────────────────


class TestHypothesis:
    """Hypothesis property test — render_dag never crashes on valid input."""

    @given(
        nodes=st.lists(
            st.builds(
                Node,
                id=st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(
                        whitelist_categories=("Lu", "Ll", "Nd"),
                        whitelist_characters="-",
                    ),
                ),
                kind=st.sampled_from(["arc", "phase", "slice", "step"]),
                status=st.sampled_from(
                    ["idle", "pending", "in_progress", "done", "blocked", "failed"]
                ),
            ),
            min_size=0,
            max_size=20,
            unique_by=lambda n: n.id,
        ),
    )
    @settings(max_examples=200, deadline=None)
    def test_render_dag_never_crashes(self, nodes: list[Node]) -> None:
        """Any valid graph (nodes + edges referencing existing nodes) renders without crash."""
        # Generate edges that only reference existing node IDs
        if len(nodes) < 2:
            edges: list[Edge] = []
        else:
            rng = random.Random(42)  # deterministic seed
            edges = []
            ids = [n.id for n in nodes]
            for _ in range(min(len(nodes) * 2, 30)):
                src = rng.choice(ids)
                tgt = rng.choice(ids)
                if src != tgt:
                    edges.append(
                        Edge(
                            source_node=src,
                            target_node=tgt,
                            kind=rng.choice(["blocks", "soft", "data"]),
                        )
                    )

        # This must never raise
        result = render_dag(nodes, edges)
        assert isinstance(result, str)

        # If nodes are non-empty, result should be non-empty (at least has boxes)
        if nodes:
            assert len(result) > 0
