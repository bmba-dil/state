"""Comprehensive tests for state_core.scheduler types.

Covers: EdgeKind literal, Edge pydantic model, Node pydantic model,
NodeRegistry in-memory storage class.

Requires: pytest. All tests are synchronous (no async needed).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.state_core.scheduler import Edge, EdgeKind, Node, NodeRegistry


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
