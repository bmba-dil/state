"""Comprehensive tests for state_core.scheduler types.

Covers: EdgeKind literal, Edge pydantic model, Node pydantic model,
NodeRegistry in-memory storage class.

Requires: pytest. All tests are synchronous (no async needed).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.state_core.scheduler import Edge, EdgeKind, Node, NodeRegistry, topo_sort, frontier, detect_cycles


# -- Edge model tests ------------------------------------------------------------


class TestEdgeModel:
    """Tests for the Edge pydantic model."""

    def test_edge_creation_blocks(self) -> None:
        """Edge creation with kind='blocks' succeeds."""
        e = Edge(source_node="step-a", target_node="step-b", kind="blocks")
        assert e.source_node == "step-a"
        assert e.target_node == "step-b"
        assert e.kind == "blocks"

    def test_edge_creation_soft_and_data(self) -> None:
        """Edge creation with kind='soft' and kind='data' succeeds."""
        e_soft = Edge(source_node="a", target_node="b", kind="soft")
        assert e_soft.kind == "soft"
        e_data = Edge(source_node="a", target_node="b", kind="data")
        assert e_data.kind == "data"

    def test_edge_rejects_invalid_kind(self) -> None:
        """Edge construction with kind='invalid' raises ValidationError."""
        with pytest.raises(ValidationError):
            Edge(source_node="a", target_node="b", kind="invalid")  # type: ignore[arg-type]

    def test_edge_rejects_extra_fields(self) -> None:
        """Edge rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError):
            Edge(source_node="a", target_node="b", kind="blocks", extra_field=1)  # type: ignore[call-arg]

    def test_edge_is_frozen(self) -> None:
        """Edge model is frozen — setting .kind after construction raises error."""
        e = Edge(source_node="a", target_node="b", kind="blocks")
        with pytest.raises(ValidationError):
            e.kind = "soft"  # type: ignore[misc]


# -- Node model tests ------------------------------------------------------------


class TestNodeModel:
    """Tests for the Node pydantic model."""

    def test_node_creation_minimal(self) -> None:
        """Node creation with id and kind succeeds with default status='idle'."""
        n = Node(id="step-1", kind="step")
        assert n.id == "step-1"
        assert n.kind == "step"
        assert n.status == "idle"

    def test_node_creation_full(self) -> None:
        """Node creation with explicit status='in_progress' succeeds."""
        n = Node(id="slice-3", kind="slice", status="in_progress")
        assert n.id == "slice-3"
        assert n.kind == "slice"
        assert n.status == "in_progress"

    def test_node_rejects_invalid_kind(self) -> None:
        """Node construction with kind='invalid' raises ValidationError."""
        with pytest.raises(ValidationError):
            Node(id="x", kind="invalid")  # type: ignore[arg-type]

    def test_node_rejects_invalid_status(self) -> None:
        """Node construction with status='invalid' raises ValidationError."""
        with pytest.raises(ValidationError):
            Node(id="x", kind="step", status="invalid")  # type: ignore[arg-type]

    def test_node_rejects_extra_fields(self) -> None:
        """Node rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError):
            Node(id="x", kind="step", extra_field=1)  # type: ignore[call-arg]


# -- NodeRegistry tests ----------------------------------------------------------


class TestNodeRegistry:
    """Tests for the NodeRegistry in-memory storage class."""

    def test_registry_register_and_get(self) -> None:
        """register() then get() returns the same node instance."""
        node = Node(id="step-1", kind="step")
        registry = NodeRegistry()
        registry.register(node)
        assert registry.get("step-1") is node

    def test_registry_contains(self) -> None:
        """contains() returns True when node present, False when absent."""
        registry = NodeRegistry()
        registry.register(Node(id="step-1", kind="step"))
        assert registry.contains("step-1") is True
        assert registry.contains("nonexistent") is False

    def test_registry_duplicate_raises(self) -> None:
        """register() with duplicate ID raises ValueError."""
        registry = NodeRegistry()
        registry.register(Node(id="step-1", kind="step"))
        with pytest.raises(ValueError, match="step-1"):
            registry.register(Node(id="step-1", kind="slice"))

    def test_registry_remove_get_raises(self) -> None:
        """remove() then get() raises KeyError."""
        registry = NodeRegistry()
        registry.register(Node(id="step-1", kind="step"))
        registry.remove("step-1")
        with pytest.raises(KeyError, match="step-1"):
            registry.get("step-1")

    def test_registry_all_nodes(self) -> None:
        """all_nodes() returns a list of all registered nodes."""
        registry = NodeRegistry()
        n1 = Node(id="step-1", kind="step")
        n2 = Node(id="step-2", kind="step")
        registry.register(n1)
        registry.register(n2)
        nodes = registry.all_nodes()
        assert len(nodes) == 2
        assert n1 in nodes
        assert n2 in nodes

    def test_registry_len(self) -> None:
        """len(registry) returns the correct node count."""
        registry = NodeRegistry()
        assert len(registry) == 0
        registry.register(Node(id="step-1", kind="step"))
        assert len(registry) == 1
        registry.register(Node(id="step-2", kind="step"))
        assert len(registry) == 2

    def test_registry_contains_operator(self) -> None:
        """'id in registry' uses __contains__ correctly."""
        registry = NodeRegistry()
        registry.register(Node(id="step-1", kind="step"))
        assert "step-1" in registry
        assert "nonexistent" not in registry


# -- TopoSort tests --------------------------------------------------------------


class TestTopoSort:
    """Tests for topo_sort Kahn's algorithm with stable ordering."""

    def test_linear_chain(self) -> None:
        """a->b->c returns [a, b, c]."""
        a = Node(id="a", kind="step")
        b = Node(id="b", kind="step")
        c = Node(id="c", kind="step")
        e1 = Edge(source_node="a", target_node="b", kind="blocks")
        e2 = Edge(source_node="b", target_node="c", kind="blocks")
        result = topo_sort([e1, e2], [a, b, c])
        assert [n.id for n in result] == ["a", "b", "c"]

    def test_diamond_dag(self) -> None:
        """a->{b,c}->d: d last, a first, b and c between."""
        a = Node(id="a", kind="step")
        b = Node(id="b", kind="step")
        c = Node(id="c", kind="step")
        d = Node(id="d", kind="step")
        edges = [
            Edge(source_node="a", target_node="b", kind="blocks"),
            Edge(source_node="a", target_node="c", kind="blocks"),
            Edge(source_node="b", target_node="d", kind="blocks"),
            Edge(source_node="c", target_node="d", kind="blocks"),
        ]
        result = topo_sort(edges, [a, b, c, d])
        ids = [n.id for n in result]
        assert ids[0] == "a"
        assert ids[-1] == "d"
        assert set(ids[1:3]) == {"b", "c"}

    def test_empty_input(self) -> None:
        """No nodes, no edges returns empty list."""
        result = topo_sort([], [])
        assert result == []

    def test_single_node(self) -> None:
        """One node with no edges returns [node]."""
        n = Node(id="step-1", kind="step")
        result = topo_sort([], [n])
        assert len(result) == 1
        assert result[0].id == "step-1"

    def test_unconnected_nodes(self) -> None:
        """Two nodes, no edges — both returned (order stable)."""
        a = Node(id="a", kind="step")
        b = Node(id="b", kind="step")
        result = topo_sort([], [a, b])
        assert len(result) == 2
        assert {n.id for n in result} == {"a", "b"}

    def test_stable_frontier_ordering(self) -> None:
        """Nodes with no edges sort by (slice_id, step_id) from node.id."""
        arc = Node(id="arc-1", kind="arc")
        phase = Node(id="arc-1/phase-1", kind="phase")
        slice_ = Node(id="arc-1/phase-1/slice-1", kind="slice")
        step1 = Node(id="arc-1/phase-1/slice-1/step-1", kind="step")
        step2 = Node(id="arc-1/phase-1/slice-1/step-2", kind="step")
        nodes = [step2, slice_, arc, step1, phase]  # deliberate non-sorted input
        result = topo_sort([], nodes)
        assert [n.id for n in result] == [
            "arc-1",
            "arc-1/phase-1",
            "arc-1/phase-1/slice-1",
            "arc-1/phase-1/slice-1/step-1",
            "arc-1/phase-1/slice-1/step-2",
        ]

    def test_stable_frontier_steps_only(self) -> None:
        """Two steps with no edges — sorted by step_id."""
        step_b = Node(id="arc-1/phase-1/slice-1/step-b", kind="step")
        step_a = Node(id="arc-1/phase-1/slice-1/step-a", kind="step")
        result = topo_sort([], [step_b, step_a])
        assert [n.id for n in result] == [
            "arc-1/phase-1/slice-1/step-a",
            "arc-1/phase-1/slice-1/step-b",
        ]

    def test_cycle_triangle_raises(self) -> None:
        """a->b->c->a cycle raises ValueError."""
        a = Node(id="a", kind="step")
        b = Node(id="b", kind="step")
        c = Node(id="c", kind="step")
        edges = [
            Edge(source_node="a", target_node="b", kind="blocks"),
            Edge(source_node="b", target_node="c", kind="blocks"),
            Edge(source_node="c", target_node="a", kind="blocks"),
        ]
        with pytest.raises(ValueError, match="Cycle detected"):
            topo_sort(edges, [a, b, c])

    def test_cycle_self_loop_raises(self) -> None:
        """Self-loop n->n raises ValueError."""
        n = Node(id="n", kind="step")
        edge = Edge(source_node="n", target_node="n", kind="blocks")
        with pytest.raises(ValueError, match="Cycle detected"):
            topo_sort([edge], [n])

    def test_missing_source_node_raises(self) -> None:
        """Edge with source not in nodes raises ValueError."""
        a = Node(id="a", kind="step")
        edge = Edge(source_node="ghost", target_node="a", kind="blocks")
        with pytest.raises(ValueError, match="ghost"):
            topo_sort([edge], [a])

    def test_missing_target_node_raises(self) -> None:
        """Edge with target not in nodes raises ValueError."""
        a = Node(id="a", kind="step")
        edge = Edge(source_node="a", target_node="ghost", kind="blocks")
        with pytest.raises(ValueError, match="ghost"):
            topo_sort([edge], [a])


# -- Frontier tests --------------------------------------------------------------


class TestFrontier:
    """Tests for frontier() — unblocked-node calculator.

    Covering: empty/trivial, blocks/data/soft edge semantics,
    multiple predecessors, edge cases, and validation.
    """

    # --- Empty / trivial -------------------------------------------------------

    def test_frontier_empty_graph(self) -> None:
        """frontier([], []) returns []."""
        result = frontier([], [])
        assert result == []

    def test_frontier_single_idle(self) -> None:
        """Single idle node, no edges → returns [node]."""
        n = Node(id="a", kind="step", status="idle")
        result = frontier([n], [])
        assert [n.id for n in result] == ["a"]

    def test_frontier_single_done_excluded(self) -> None:
        """Single done node, no edges → [] (done excluded)."""
        n = Node(id="a", kind="step", status="done")
        result = frontier([n], [])
        assert result == []

    def test_frontier_single_failed_excluded(self) -> None:
        """Single failed node, no edges → [] (failed excluded)."""
        n = Node(id="a", kind="step", status="failed")
        result = frontier([n], [])
        assert result == []

    def test_frontier_single_in_progress(self) -> None:
        """Single in_progress node, no edges → [node] (only done/failed excluded)."""
        n = Node(id="a", kind="step", status="in_progress")
        result = frontier([n], [])
        assert [n.id for n in result] == ["a"]

    # --- blocks edge semantics -------------------------------------------------

    def test_frontier_blocks_edge_done_unblocks(self) -> None:
        """A(done) -blocks→ B(idle) → [B] (B unblocked, A excluded as done)."""
        a = Node(id="a", kind="step", status="done")
        b = Node(id="b", kind="step", status="idle")
        e = Edge(source_node="a", target_node="b", kind="blocks")
        result = frontier([a, b], [e])
        assert [n.id for n in result] == ["b"]

    def test_frontier_blocks_edge_not_done_blocks(self) -> None:
        """A(idle) -blocks→ B(idle) → [A] (B blocked by A not done)."""
        a = Node(id="a", kind="step", status="idle")
        b = Node(id="b", kind="step", status="idle")
        e = Edge(source_node="a", target_node="b", kind="blocks")
        result = frontier([a, b], [e])
        assert [n.id for n in result] == ["a"]

    # --- data edge semantics (same blocking as blocks) ------------------------

    def test_frontier_data_edge_done_unblocks(self) -> None:
        """A(done) -data→ B(idle) → [B]."""
        a = Node(id="a", kind="step", status="done")
        b = Node(id="b", kind="step", status="idle")
        e = Edge(source_node="a", target_node="b", kind="data")
        result = frontier([a, b], [e])
        assert [n.id for n in result] == ["b"]

    def test_frontier_data_edge_not_done_blocks(self) -> None:
        """A(idle) -data→ B(idle) → [A] (B blocked by A not done)."""
        a = Node(id="a", kind="step", status="idle")
        b = Node(id="b", kind="step", status="idle")
        e = Edge(source_node="a", target_node="b", kind="data")
        result = frontier([a, b], [e])
        assert [n.id for n in result] == ["a"]

    # --- soft edge semantics (does NOT block) ----------------------------------

    def test_frontier_soft_edge_does_not_block(self) -> None:
        """A(idle) -soft→ B(idle) → [A, B] (both unblocked)."""
        a = Node(id="a", kind="step", status="idle")
        b = Node(id="b", kind="step", status="idle")
        e = Edge(source_node="a", target_node="b", kind="soft")
        result = frontier([a, b], [e])
        assert [n.id for n in result] == ["a", "b"]

    def test_frontier_soft_edge_done_excluded(self) -> None:
        """A(done) -soft→ B(idle) → [B] (A excluded as done)."""
        a = Node(id="a", kind="step", status="done")
        b = Node(id="b", kind="step", status="idle")
        e = Edge(source_node="a", target_node="b", kind="soft")
        result = frontier([a, b], [e])
        assert [n.id for n in result] == ["b"]

    # --- Multiple predecessors --------------------------------------------------

    def test_frontier_multiple_predecessors_all_done(self) -> None:
        """A(done)+B(done) both → C(idle) → [C] (all done)."""
        a = Node(id="a", kind="step", status="done")
        b = Node(id="b", kind="step", status="done")
        c = Node(id="c", kind="step", status="idle")
        e1 = Edge(source_node="a", target_node="c", kind="blocks")
        e2 = Edge(source_node="b", target_node="c", kind="blocks")
        result = frontier([a, b, c], [e1, e2])
        assert [n.id for n in result] == ["c"]

    def test_frontier_multiple_predecessors_one_not_done(self) -> None:
        """A(done)+B(idle) both → C(idle) → [B] (C blocked by B not done)."""
        a = Node(id="a", kind="step", status="done")
        b = Node(id="b", kind="step", status="idle")
        c = Node(id="c", kind="step", status="idle")
        e1 = Edge(source_node="a", target_node="c", kind="blocks")
        e2 = Edge(source_node="b", target_node="c", kind="blocks")
        result = frontier([a, b, c], [e1, e2])
        assert [n.id for n in result] == ["b"]

    # --- Edge cases -------------------------------------------------------------

    def test_frontier_failed_predecessor_blocks(self) -> None:
        """A(failed) -blocks→ B(idle) → [] (both excluded)."""
        a = Node(id="a", kind="step", status="failed")
        b = Node(id="b", kind="step", status="idle")
        e = Edge(source_node="a", target_node="b", kind="blocks")
        result = frontier([a, b], [e])
        assert result == []

    def test_frontier_mixed_block_soft(self) -> None:
        """A(done)-blocks→C(idle), B(idle)-soft→C(idle) → [B, C].
        
        C unblocked because only blocks/data edges matter;
        soft edge from B to C does not block C.
        """
        a = Node(id="a", kind="step", status="done")
        b = Node(id="b", kind="step", status="idle")
        c = Node(id="c", kind="step", status="idle")
        e1 = Edge(source_node="a", target_node="c", kind="blocks")
        e2 = Edge(source_node="b", target_node="c", kind="soft")
        result = frontier([a, b, c], [e1, e2])
        assert [n.id for n in result] == ["b", "c"]

    def test_frontier_diamond_middle_only(self) -> None:
        """Diamond A(done)→B,C(idle), B,C→D(idle) → [B, C].
        
        D blocked — both B and C must be done first.
        """
        a = Node(id="a", kind="step", status="done")
        b = Node(id="b", kind="step", status="idle")
        c = Node(id="c", kind="step", status="idle")
        d = Node(id="d", kind="step", status="idle")
        edges = [
            Edge(source_node="a", target_node="b", kind="blocks"),
            Edge(source_node="a", target_node="c", kind="blocks"),
            Edge(source_node="b", target_node="d", kind="blocks"),
            Edge(source_node="c", target_node="d", kind="blocks"),
        ]
        result = frontier(edges=edges, nodes=[a, b, c, d])
        assert [n.id for n in result] == ["b", "c"]

    # --- Validation (matching topo_sort pattern) -------------------------------

    def test_frontier_missing_source_node_raises(self) -> None:
        """Edge references source_node not in nodes → raises ValueError."""
        a = Node(id="a", kind="step", status="idle")
        bad_edge = Edge(source_node="ghost", target_node="a", kind="blocks")
        with pytest.raises(ValueError, match="ghost"):
            frontier([a], [bad_edge])
