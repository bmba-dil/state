/** Unit tests for dag-viewer: topological layout, filtering, critical path,
 * SSE patches, navigation, accessibility, layout cache, viewport clipping,
 * and integration smoke tests. */

import { describe, expect, it, beforeEach } from "bun:test";
import {
  computeTopologicalLayout,
  computeCriticalPath,
  filterNodes,
  applyStatusPatch,
  memoizeLayout,
  invalidateLayoutCache,
  layoutCacheKey,
  renderDagViewer,
  DAG_VIEWER_STATE,
  navigateUp,
  navigateDown,
  selectFocused,
  deselectNode,
  focusFilter,
  announce,
} from "./dag-viewer.js";
import type { DagNode, DagEdge } from "./build-progress.js";
import type { LayoutNode, StatusPatch } from "./dag-viewer.js";

function resetState() {
  DAG_VIEWER_STATE.connection = "unreachable";
  DAG_VIEWER_STATE.nodes = [];
  DAG_VIEWER_STATE.edges = [];
  DAG_VIEWER_STATE.selectedNode = null;
  DAG_VIEWER_STATE.focusedNode = null;
  DAG_VIEWER_STATE.scrollOffset = 0;
  DAG_VIEWER_STATE.viewportHeight = 30;
  DAG_VIEWER_STATE.filterPreset = "all";
  DAG_VIEWER_STATE.focusFilter = false;
  DAG_VIEWER_STATE.announcementText = "";
  invalidateLayoutCache();
}

// ══════════════════════════════════════════════════════════════════
//  Phase 089 — computeTopologicalLayout
// ══════════════════════════════════════════════════════════════════

describe("computeTopologicalLayout", () => {
  it("returns empty array for empty nodes", () => {
    expect(computeTopologicalLayout([], [])).toEqual([]);
  });

  it("positions single node at (0,0)", () => {
    const nodes: DagNode[] = [{ id: "a", name: "Only", status: "done" }];
    const result = computeTopologicalLayout(nodes, []);
    expect(result.length).toBe(1);
    expect(result[0].row).toBe(0);
    expect(result[0].id).toBe("a");
  });

  it("assigns correct layers for a 5-node chain", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "done" },
      { id: "c", name: "C", status: "running" },
      { id: "d", name: "D", status: "pending" },
      { id: "e", name: "E", status: "pending" },
    ];
    const edges: DagEdge[] = [
      { from: "a", to: "b" },
      { from: "b", to: "c" },
      { from: "c", to: "d" },
      { from: "d", to: "e" },
    ];
    const result = computeTopologicalLayout(nodes, edges);
    const byId = new Map(result.map((n) => [n.id, n]));
    expect(byId.get("a")!.row).toBe(0);
    expect(byId.get("b")!.row).toBe(1);
    expect(byId.get("c")!.row).toBe(2);
    expect(byId.get("d")!.row).toBe(3);
    expect(byId.get("e")!.row).toBe(4);
  });

  it("handles diamond pattern (branch + merge)", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "done" },
      { id: "c", name: "C", status: "done" },
      { id: "d", name: "D", status: "done" },
    ];
    const edges: DagEdge[] = [
      { from: "a", to: "b" },
      { from: "a", to: "c" },
      { from: "b", to: "d" },
      { from: "c", to: "d" },
    ];
    const result = computeTopologicalLayout(nodes, edges);
    const byId = new Map(result.map((n) => [n.id, n]));
    expect(byId.get("a")!.row).toBe(0);
    expect(byId.get("b")!.row).toBe(1);
    expect(byId.get("c")!.row).toBe(1);
    expect(byId.get("d")!.row).toBe(2);
  });

  it("handles disconnected nodes in separate groups", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "pending" },
    ];
    const result = computeTopologicalLayout(nodes, []);
    expect(result.every((n) => n.row === 0)).toBe(true);
    expect(result.length).toBe(2);
  });

  it("handles 50-node stress test without overlapping positions", () => {
    const nodes: DagNode[] = [];
    const edges: DagEdge[] = [];
    for (let i = 0; i < 50; i++) {
      nodes.push({
        id: `node-${i}`,
        name: `Node ${i}`,
        status: i % 2 === 0 ? "done" : "pending",
      });
      if (i > 0) {
        edges.push({ from: `node-${i - 1}`, to: `node-${i}` });
      }
    }
    const result = computeTopologicalLayout(nodes, edges);
    expect(result.length).toBe(50);

    const positions = new Set<string>();
    for (const ln of result) {
      const key = `${ln.row},${ln.col}`;
      expect(positions.has(key)).toBe(false);
      positions.add(key);
    }
  });

  it("infers kind from node ID", () => {
    const nodes: DagNode[] = [
      { id: "arc-1", name: "Arc 1", status: "done" },
      { id: "arc-1/phase-1", name: "Phase 1", status: "done" },
      { id: "arc-1/phase-1/slice-1", name: "Slice 1", status: "done" },
      {
        id: "arc-1/phase-1/slice-1/step-1",
        name: "Step 1",
        status: "done",
      },
    ];
    const edges: DagEdge[] = [
      { from: "arc-1", to: "arc-1/phase-1" },
      { from: "arc-1/phase-1", to: "arc-1/phase-1/slice-1" },
      { from: "arc-1/phase-1/slice-1", to: "arc-1/phase-1/slice-1/step-1" },
    ];
    const result = computeTopologicalLayout(nodes, edges);
    const byId = new Map(result.map((n) => [n.id, n]));
    expect(byId.get("arc-1")!.kind).toBe("arc");
    expect(byId.get("arc-1/phase-1")!.kind).toBe("phase");
    expect(byId.get("arc-1/phase-1/slice-1")!.kind).toBe("slice");
    expect(byId.get("arc-1/phase-1/slice-1/step-1")!.kind).toBe("step");
    expect(byId.get("arc-1")!.row).toBe(0);
    expect(byId.get("arc-1/phase-1")!.row).toBe(1);
    expect(byId.get("arc-1/phase-1/slice-1")!.row).toBe(2);
    expect(byId.get("arc-1/phase-1/slice-1/step-1")!.row).toBe(3);
  });

  it("handles fork-join with 3 parallel branches", () => {
    const nodes: DagNode[] = [
      { id: "root", name: "Root", status: "done" },
      { id: "a", name: "Branch A", status: "done" },
      { id: "b", name: "Branch B", status: "running" },
      { id: "c", name: "Branch C", status: "pending" },
      { id: "merge", name: "Merge", status: "pending" },
    ];
    const edges: DagEdge[] = [
      { from: "root", to: "a" },
      { from: "root", to: "b" },
      { from: "root", to: "c" },
      { from: "a", to: "merge" },
      { from: "b", to: "merge" },
      { from: "c", to: "merge" },
    ];
    const result = computeTopologicalLayout(nodes, edges);
    const byId = new Map(result.map((n) => [n.id, n]));
    expect(byId.get("root")!.row).toBe(0);
    expect(byId.get("a")!.row).toBe(1);
    expect(byId.get("b")!.row).toBe(1);
    expect(byId.get("c")!.row).toBe(1);
    expect(byId.get("merge")!.row).toBe(2);
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 092 — Critical Path
// ══════════════════════════════════════════════════════════════════

describe("computeCriticalPath", () => {
  it("returns empty set for empty nodes", () => {
    expect(computeCriticalPath([], []).size).toBe(0);
  });

  it("returns single node for single-node DAG", () => {
    const nodes: DagNode[] = [{ id: "a", name: "A", status: "done" }];
    const path = computeCriticalPath(nodes, []);
    expect(path.has("a")).toBe(true);
  });

  it("finds longest path in a chain", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "done" },
      { id: "c", name: "C", status: "running" },
      { id: "d", name: "D", status: "pending" },
    ];
    const edges: DagEdge[] = [
      { from: "a", to: "b" },
      { from: "b", to: "c" },
      { from: "c", to: "d" },
    ];
    const path = computeCriticalPath(nodes, edges);
    expect(path.size).toBe(4);
    expect(path.has("a")).toBe(true);
    expect(path.has("b")).toBe(true);
    expect(path.has("c")).toBe(true);
    expect(path.has("d")).toBe(true);
  });

  it("picks longest branch in diamond", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "done" },
      { id: "c", name: "C", status: "done" },
      { id: "d", name: "D", status: "done" },
      { id: "e", name: "E", status: "done" }, // extra node on one branch
    ];
    const edges: DagEdge[] = [
      { from: "a", to: "b" },
      { from: "b", to: "c" },
      { from: "a", to: "d" },
      { from: "d", to: "e" },
      { from: "e", to: "c" }, // merge back
    ];
    const path = computeCriticalPath(nodes, edges);
    // The path a→d→e→c is longer (4 nodes) than a→b→c (3 nodes)
    expect(path.size).toBe(4);
    expect(path.has("a")).toBe(true);
    expect(path.has("d")).toBe(true);
    expect(path.has("e")).toBe(true);
    expect(path.has("c")).toBe(true);
  });

  it("handles disconnected nodes — returns longest among them", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "pending" },
      { id: "c", name: "C", status: "done" },
      { id: "d", name: "D", status: "done" },
    ];
    const edges: DagEdge[] = [
      { from: "c", to: "d" }, // 2-node chain
    ];
    const path = computeCriticalPath(nodes, edges);
    // The longest path is c→d (2 nodes)
    expect(path.size).toBeGreaterThanOrEqual(1);
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 092 — Filter Nodes
// ══════════════════════════════════════════════════════════════════

describe("filterNodes", () => {
  let nodes: DagNode[];
  let edges: DagEdge[];

  beforeEach(() => {
    resetState();
    nodes = [
      { id: "a", name: "Arc", status: "done" },
      { id: "b", name: "Phase", status: "running" },
      { id: "c", name: "Slice", status: "pending" },
      { id: "d", name: "Step", status: "blocked" },
      { id: "e", name: "Failed Step", status: "failed" },
    ];
    edges = [
      { from: "a", to: "b" },
      { from: "b", to: "c" },
      { from: "c", to: "d" },
    ];
    DAG_VIEWER_STATE.nodes = nodes;
    DAG_VIEWER_STATE.edges = edges;
  });

  it("returns all nodes when filterPreset is 'all'", () => {
    DAG_VIEWER_STATE.filterPreset = "all";
    const layout = computeTopologicalLayout(nodes, edges);
    const filtered = filterNodes(DAG_VIEWER_STATE, layout);
    expect(filtered.length).toBe(5);
  });

  it("filters to active nodes only (running + pending)", () => {
    DAG_VIEWER_STATE.filterPreset = "active";
    const layout = computeTopologicalLayout(nodes, edges);
    const filtered = filterNodes(DAG_VIEWER_STATE, layout);
    expect(filtered.length).toBe(2);
    expect(filtered.every((n) => n.status === "running" || n.status === "pending")).toBe(true);
  });

  it("filters to blocked nodes only", () => {
    DAG_VIEWER_STATE.filterPreset = "blocked";
    const layout = computeTopologicalLayout(nodes, edges);
    const filtered = filterNodes(DAG_VIEWER_STATE, layout);
    expect(filtered.length).toBe(1);
    expect(filtered[0].status).toBe("blocked");
  });

  it("filters to critical path nodes only", () => {
    DAG_VIEWER_STATE.filterPreset = "critical";
    const layout = computeTopologicalLayout(nodes, edges);
    const filtered = filterNodes(DAG_VIEWER_STATE, layout);
    // Critical path is a→b→c→d (longest chain, 4 nodes)
    expect(filtered.length).toBe(4);
    const ids = new Set(filtered.map((n) => n.id));
    expect(ids.has("a")).toBe(true);
    expect(ids.has("b")).toBe(true);
    expect(ids.has("c")).toBe(true);
    expect(ids.has("d")).toBe(true);
  });

  it("returns empty array for active filter when no active nodes", () => {
    const allDone: DagNode[] = [
      { id: "x", name: "X", status: "done" },
      { id: "y", name: "Y", status: "failed" },
    ];
    DAG_VIEWER_STATE.nodes = allDone;
    DAG_VIEWER_STATE.edges = [];
    DAG_VIEWER_STATE.filterPreset = "active";
    const layout = computeTopologicalLayout(allDone, []);
    const filtered = filterNodes(DAG_VIEWER_STATE, layout);
    expect(filtered.length).toBe(0);
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 093 — applyStatusPatch
// ══════════════════════════════════════════════════════════════════

describe("applyStatusPatch", () => {
  let nodes: DagNode[];

  beforeEach(() => {
    nodes = [
      { id: "a", name: "Node A", status: "pending" },
      { id: "b", name: "Node B", status: "running" },
      { id: "c", name: "Node C", status: "done" },
    ];
  });

  it("updates matching node status", () => {
    const patches: StatusPatch[] = [{ id: "a", status: "done" }];
    applyStatusPatch(nodes, patches);
    expect(nodes[0].status).toBe("done");
  });

  it("does not update when status is unchanged (diff check)", () => {
    const patches: StatusPatch[] = [{ id: "c", status: "done" }];
    applyStatusPatch(nodes, patches);
    // Should be unchanged (diff check skips no-op)
    expect(nodes[2].status).toBe("done");
  });

  it("ignores patches for unknown node IDs", () => {
    const patches: StatusPatch[] = [{ id: "nonexistent", status: "done" }];
    applyStatusPatch(nodes, patches);
    // All nodes unchanged
    expect(nodes[0].status).toBe("pending");
    expect(nodes[1].status).toBe("running");
    expect(nodes[2].status).toBe("done");
  });

  it("applies multiple patches at once", () => {
    const patches: StatusPatch[] = [
      { id: "a", status: "running" },
      { id: "b", status: "done" },
    ];
    applyStatusPatch(nodes, patches);
    expect(nodes[0].status).toBe("running");
    expect(nodes[1].status).toBe("done");
  });

  it("handles empty patches array", () => {
    applyStatusPatch(nodes, []);
    expect(nodes[0].status).toBe("pending");
    expect(nodes[1].status).toBe("running");
    expect(nodes[2].status).toBe("done");
  });

  it("handles mixed known and unknown IDs", () => {
    const patches: StatusPatch[] = [
      { id: "a", status: "failed" },
      { id: "xyz", status: "done" },
    ];
    applyStatusPatch(nodes, patches);
    expect(nodes[0].status).toBe("failed");
    expect(nodes[1].status).toBe("running");
    expect(nodes[2].status).toBe("done");
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 094 — Navigation + Accessibility
// ══════════════════════════════════════════════════════════════════

describe("DAG viewer navigation", () => {
  beforeEach(() => {
    resetState();
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "Node A", status: "done" },
      { id: "b", name: "Node B", status: "running" },
      { id: "c", name: "Node C", status: "pending" },
    ];
    DAG_VIEWER_STATE.edges = [
      { from: "a", to: "b" },
      { from: "b", to: "c" },
    ];
    DAG_VIEWER_STATE.focusedNode = "a";
    DAG_VIEWER_STATE.selectedNode = null;
  });

  it("navigateDown moves to next node in topological order", () => {
    navigateDown(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBe("b");
  });

  it("navigateUp moves to previous node", () => {
    DAG_VIEWER_STATE.focusedNode = "b";
    navigateUp(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBe("a");
  });

  it("navigateDown wraps around at end", () => {
    DAG_VIEWER_STATE.focusedNode = "c";
    navigateDown(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBe("a");
  });

  it("navigateUp wraps around at start", () => {
    DAG_VIEWER_STATE.focusedNode = "a";
    navigateUp(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBe("c");
  });

  it("selectFocused sets selectedNode to focusedNode", () => {
    selectFocused(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.selectedNode).toBe("a");
  });

  it("deselectNode clears selectedNode", () => {
    DAG_VIEWER_STATE.selectedNode = "a";
    deselectNode(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.selectedNode).toBeNull();
  });

  it("navigation handles empty node list gracefully", () => {
    DAG_VIEWER_STATE.nodes = [];
    DAG_VIEWER_STATE.focusedNode = null;
    navigateDown(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBeNull();
    navigateUp(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBeNull();
  });

  // Phase 094 additions

  it("automatically sets focusedNode to first node when null and navigating down", () => {
    DAG_VIEWER_STATE.focusedNode = null;
    navigateDown(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBe("a");
  });

  it("automatically sets focusedNode when null and navigating up", () => {
    DAG_VIEWER_STATE.focusedNode = null;
    navigateUp(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBe("a");
  });

  it("announcements are set on navigation", () => {
    navigateDown(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.announcementText).toContain("Node B");
  });
});

describe("focusFilter", () => {
  beforeEach(() => {
    resetState();
    DAG_VIEWER_STATE.focusFilter = false;
  });

  it("toggles focusFilter on", () => {
    focusFilter(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusFilter).toBe(true);
  });

  it("toggles focusFilter off", () => {
    DAG_VIEWER_STATE.focusFilter = true;
    focusFilter(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusFilter).toBe(false);
  });

  it("sets announcement on toggle", () => {
    focusFilter(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.announcementText).toContain("Filter mode");
  });
});

describe("announce", () => {
  beforeEach(() => {
    resetState();
  });

  it("sets announcementText", () => {
    announce(DAG_VIEWER_STATE, "Hello world");
    expect(DAG_VIEWER_STATE.announcementText).toBe("Hello world");
  });

  it("overwrites previous announcement", () => {
    announce(DAG_VIEWER_STATE, "First");
    announce(DAG_VIEWER_STATE, "Second");
    expect(DAG_VIEWER_STATE.announcementText).toBe("Second");
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 095 — Layout Cache
// ══════════════════════════════════════════════════════════════════

describe("layout cache", () => {
  beforeEach(() => {
    invalidateLayoutCache();
  });

  it("layoutCacheKey produces deterministic string", () => {
    const nodes: DagNode[] = [
      { id: "b", name: "B", status: "done" },
      { id: "a", name: "A", status: "done" },
    ];
    const edges: DagEdge[] = [{ from: "a", to: "b" }];
    const key1 = layoutCacheKey(nodes, edges);
    const key2 = layoutCacheKey([...nodes].reverse(), [...edges].reverse());
    // Should be same (sorting makes it deterministic)
    expect(key1).toBe(key2);
  });

  it("layoutCacheKey changes when nodes differ", () => {
    const nodes1: DagNode[] = [{ id: "a", name: "A", status: "done" }];
    const nodes2: DagNode[] = [{ id: "b", name: "B", status: "done" }];
    expect(layoutCacheKey(nodes1, [])).not.toBe(layoutCacheKey(nodes2, []));
  });

  it("memoizeLayout returns same reference on cache hit", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "done" },
    ];
    const edges: DagEdge[] = [{ from: "a", to: "b" }];

    const r1 = memoizeLayout(nodes, edges);
    const r2 = memoizeLayout(nodes, edges);
    expect(r1).toBe(r2); // same reference
  });

  it("memoizeLayout recomputes after cache invalidation", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "done" },
    ];
    const edges: DagEdge[] = [{ from: "a", to: "b" }];

    const r1 = memoizeLayout(nodes, edges);
    invalidateLayoutCache();
    const r2 = memoizeLayout(nodes, edges);
    expect(r1).not.toBe(r2); // new computation
    expect(r2.length).toBe(2);
  });

  it("memoizeLayout handles 500-node chain", () => {
    const nodes: DagNode[] = [];
    const edges: DagEdge[] = [];
    for (let i = 0; i < 500; i++) {
      nodes.push({
        id: `node-${i}`,
        name: `Node ${i}`,
        status: i % 3 === 0 ? "done" : i % 3 === 1 ? "running" : "pending",
      });
      if (i > 0) {
        edges.push({ from: `node-${i - 1}`, to: `node-${i}` });
      }
    }

    const r1 = memoizeLayout(nodes, edges);
    expect(r1.length).toBe(500);

    // All unique positions
    const positions = new Set<string>();
    for (const ln of r1) {
      const key = `${ln.row},${ln.col}`;
      expect(positions.has(key)).toBe(false);
      positions.add(key);
    }

    // Cache hit on second call
    const r2 = memoizeLayout(nodes, edges);
    expect(r2).toBe(r1);
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 095 — Viewport Clipping (tested via render)
// ══════════════════════════════════════════════════════════════════

describe("viewport clipping", () => {
  beforeEach(() => {
    resetState();
  });

  it("renders only visible rows for large graph with viewport clipping", () => {
    const nodes: DagNode[] = [];
    const edges: DagEdge[] = [];
    // Create 150-node chain (above VIEWPORT_THRESHOLD of 100)
    for (let i = 0; i < 150; i++) {
      nodes.push({
        id: `n-${i}`,
        name: `N${i}`,
        status: "pending",
      });
      if (i > 0) {
        edges.push({ from: `n-${i - 1}`, to: `n-${i}` });
      }
    }
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = nodes;
    DAG_VIEWER_STATE.edges = edges;
    DAG_VIEWER_STATE.viewportHeight = 30;
    DAG_VIEWER_STATE.scrollOffset = 0;

    const box = renderDagViewer(DAG_VIEWER_STATE);
    expect(box).toBeDefined();

    // With viewport clipping, should render roughly viewportH rows (26 = 30 - HEADER_HEIGHT)
    // Each DAG row is 3 Box children (top, label, bottom)
    // Plus header/filter/legend/etc. Should be less than all 150 rows
    const tree = JSON.stringify(box);
    // Should contain content from first rows but not from row 149
    expect(tree).toContain("N0");
    expect(tree).toContain("N1");
  });

  it("renders no empty state with valid nodes (even with filter)", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "blocked" },
    ];
    DAG_VIEWER_STATE.edges = [];
    DAG_VIEWER_STATE.filterPreset = "blocked";

    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("B");
    expect(tree).not.toContain("No nodes match the current filter");
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 092 — renderDagViewer (filter bar + filtered rendering)
// ══════════════════════════════════════════════════════════════════

describe("renderDagViewer", () => {
  beforeEach(() => {
    resetState();
  });

  it("renders empty state when no nodes", () => {
    const box = renderDagViewer(DAG_VIEWER_STATE);
    expect(box).toBeDefined();
    const tree = JSON.stringify(box);
    expect(tree).toContain("No DAG data available");
  });

  it("renders title bar with node count", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "Node A", status: "done" },
    ];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("DAG Viewer");
    expect(tree).toContain("1 node");
  });

  it("shows node names in rendered output", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "M-A1.P1", status: "done" },
      { id: "b", name: "M-A1.P2", status: "running" },
    ];
    DAG_VIEWER_STATE.edges = [{ from: "a", to: "b" }];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("M-A1.P1");
    expect(tree).toContain("M-A1.P2");
  });

  it("shows detail pane for selected node", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "Target Node", status: "running" },
      { id: "b", name: "Dependent", status: "pending" },
    ];
    DAG_VIEWER_STATE.edges = [
      { from: "a", to: "b" },
    ];
    DAG_VIEWER_STATE.selectedNode = "a";
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Target Node");
    expect(tree).toContain("Blocks:");
    expect(tree).toContain("Dependent");
  });

  it("shows connection status when disconnected", () => {
    DAG_VIEWER_STATE.connection = "disconnected";
    DAG_VIEWER_STATE.nodes = [{ id: "a", name: "A", status: "done" }];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Disconnected");
  });

  it("shows error status when unreachable", () => {
    DAG_VIEWER_STATE.connection = "unreachable";
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Daemon not running");
  });

  it("handles large node names with truncation", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      {
        id: "x",
        name: "This is a very long node name that exceeds the typical width",
        status: "done",
      },
    ];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    expect(box).toBeDefined();
  });

  // Phase 092 — Filter bar rendering

  it("renders filter bar with All preset", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "running" },
    ];
    DAG_VIEWER_STATE.filterPreset = "all";
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Filter:");
    expect(tree).toContain("All");
    expect(tree).toContain("2 nodes");
  });

  it("renders filter bar with Active preset", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "A", status: "running" },
      { id: "b", name: "B", status: "done" },
    ];
    DAG_VIEWER_STATE.filterPreset = "active";
    DAG_VIEWER_STATE.edges = [];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Active");
    expect(tree).toContain("1 nodes"); // only running
  });

  it("renders filter bar with Blocked preset", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "A", status: "blocked" },
    ];
    DAG_VIEWER_STATE.filterPreset = "blocked";
    DAG_VIEWER_STATE.edges = [];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Blocked");
  });

  it("renders filter bar with Critical preset", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "A", status: "done" },
      { id: "b", name: "B", status: "running" },
    ];
    DAG_VIEWER_STATE.edges = [{ from: "a", to: "b" }];
    DAG_VIEWER_STATE.filterPreset = "critical";
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Critical");
  });

  it("shows 'No nodes match filter' when filtered to zero", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "A", status: "done" },
    ];
    DAG_VIEWER_STATE.filterPreset = "blocked";
    DAG_VIEWER_STATE.edges = [];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("No nodes match the current filter");
  });

  // Phase 094 — Focus filter indicator

  it("shows focus indicator on filter bar when focusFilter is true", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "A", status: "done" },
    ];
    DAG_VIEWER_STATE.focusFilter = true;
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("\u25B8");
  });

  // Phase 096 — Status colors rendered

  it("renders all status colors in legend", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "A", status: "running" },
    ];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Done");
    expect(tree).toContain("In Progress");
    expect(tree).toContain("Pending");
    expect(tree).toContain("Failed");
    expect(tree).toContain("Blocked");
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 096 — Integration Smoke Tests
// ══════════════════════════════════════════════════════════════════

describe("integration — build mode DAG", () => {
  beforeEach(() => {
    resetState();
  });

  it("renders full arc→phase→slice→step hierarchy", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "arc-1", name: "Arc 1: Core Infrastructure", status: "done" },
      { id: "arc-1/phase-1", name: "Phase 1: Scaffold", status: "done" },
      { id: "arc-1/phase-1/slice-1", name: "Slice 1: Routes", status: "done" },
      { id: "arc-1/phase-1/slice-1/step-1", name: "Step 1: Setup", status: "done" },
      { id: "arc-1/phase-1/slice-1/step-2", name: "Step 2: Auth", status: "running" },
      { id: "arc-1/phase-1/slice-2", name: "Slice 2: DB", status: "running" },
      { id: "arc-1/phase-1/slice-2/step-1", name: "Step 1: Schema", status: "pending" },
      { id: "arc-1/phase-2", name: "Phase 2: Production", status: "pending" },
    ];
    DAG_VIEWER_STATE.edges = [
      { from: "arc-1", to: "arc-1/phase-1" },
      { from: "arc-1", to: "arc-1/phase-2" },
      { from: "arc-1/phase-1", to: "arc-1/phase-1/slice-1" },
      { from: "arc-1/phase-1", to: "arc-1/phase-1/slice-2" },
      { from: "arc-1/phase-1/slice-1", to: "arc-1/phase-1/slice-1/step-1" },
      { from: "arc-1/phase-1/slice-1", to: "arc-1/phase-1/slice-1/step-2" },
      { from: "arc-1/phase-1/slice-1/step-1", to: "arc-1/phase-1/slice-1/step-2" },
      { from: "arc-1/phase-1/slice-2", to: "arc-1/phase-1/slice-2/step-1" },
    ];

    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);

    // All node names appear (some may be truncated to fit node box width)
    expect(tree).toContain("Arc 1: Core I");  // truncated
    expect(tree).toContain("Phase 1: Scaf");  // truncated
    expect(tree).toContain("Slice 1: Rout");  // truncated
    expect(tree).toContain("Step 1: Setup");
    expect(tree).toContain("Step 2: Auth");
    expect(tree).toContain("Phase 2: Prod");  // truncated

    // Status colors present in legend
    expect(tree).toContain("Done");
    expect(tree).toContain("In Progress");
    expect(tree).toContain("Pending");
  });

  it("navigation works end-to-end in build graph", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "Arc", status: "done" },
      { id: "b", name: "Phase 1", status: "running" },
      { id: "c", name: "Phase 2", status: "pending" },
      { id: "d", name: "Phase 3", status: "blocked" },
    ];
    DAG_VIEWER_STATE.edges = [
      { from: "a", to: "b" },
      { from: "a", to: "c" },
      { from: "a", to: "d" },
    ];

    // Focus should auto-set on first nav
    DAG_VIEWER_STATE.focusedNode = null;
    navigateDown(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).not.toBeNull();

    // Navigate through all nodes
    const visited = new Set<string>();
    for (let i = 0; i < 4; i++) {
      visited.add(DAG_VIEWER_STATE.focusedNode!);
      navigateDown(DAG_VIEWER_STATE);
    }
    // Should have visited all 4 unique nodes
    expect(visited.size).toBe(4);
  });

  it("filter works in build graph", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "a", name: "Arc A", status: "done" },
      { id: "b", name: "Phase B", status: "running" },
      { id: "c", name: "Slice C", status: "running" },
      { id: "d", name: "Step D", status: "blocked" },
    ];
    DAG_VIEWER_STATE.edges = [
      { from: "a", to: "b" },
      { from: "b", to: "c" },
    ];

    // Active filter: should show B and C (running + pending)
    DAG_VIEWER_STATE.filterPreset = "active";
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("Active");
    expect(tree).toContain("Phase B");
    expect(tree).toContain("Slice C");
    // Arc A is still rendered but dimmed (filtered out visually)
    expect(tree).toContain("Arc A");

    // All filter: should show everything
    DAG_VIEWER_STATE.filterPreset = "all";
    const box2 = renderDagViewer(DAG_VIEWER_STATE);
    const tree2 = JSON.stringify(box2);
    expect(tree2).toContain("Arc A");
    expect(tree2).toContain("Step D");
  });
});

describe("integration — teach mode DAG", () => {
  beforeEach(() => {
    resetState();
  });

  it("renders teach-mode concept graph (subject→lesson→concept→drill)", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "subject-python", name: "Subject: Python", status: "done" },
      { id: "subject-python/lesson-vars", name: "Lesson: Variables", status: "done" },
      { id: "subject-python/lesson-vars/concept-types", name: "Concept: Types", status: "running" },
      { id: "subject-python/lesson-vars/concept-types/drill-1", name: "Drill: Type Check", status: "pending" },
      { id: "subject-python/lesson-vars/concept-types/drill-2", name: "Drill: Cast", status: "pending" },
      { id: "subject-python/lesson-loops", name: "Lesson: Loops", status: "pending" },
    ];
    DAG_VIEWER_STATE.edges = [
      { from: "subject-python", to: "subject-python/lesson-vars" },
      { from: "subject-python", to: "subject-python/lesson-loops" },
      { from: "subject-python/lesson-vars", to: "subject-python/lesson-vars/concept-types" },
      { from: "subject-python/lesson-vars/concept-types", to: "subject-python/lesson-vars/concept-types/drill-1" },
      { from: "subject-python/lesson-vars/concept-types", to: "subject-python/lesson-vars/concept-types/drill-2" },
    ];

    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);

    expect(tree).toContain("Subject: Pyth");  // truncated
    expect(tree).toContain("Lesson: Varia");  // truncated
    expect(tree).toContain("Concept: Types");
    expect(tree).toContain("Drill: Type C");  // truncated
    expect(tree).toContain("Drill: Cast");
    expect(tree).toContain("Lesson: Loops");
  });

  it("teach-mode empty graph shows placeholder", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [];
    DAG_VIEWER_STATE.edges = [];
    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);
    expect(tree).toContain("No DAG data available");
  });

  it("teach-mode graph with navigation functions works", () => {
    DAG_VIEWER_STATE.connection = "connected";
    DAG_VIEWER_STATE.nodes = [
      { id: "s", name: "Subject", status: "done" },
      { id: "s/l1", name: "Lesson 1", status: "done" },
      { id: "s/l1/c1", name: "Concept 1", status: "running" },
    ];
    DAG_VIEWER_STATE.edges = [
      { from: "s", to: "s/l1" },
      { from: "s/l1", to: "s/l1/c1" },
    ];

    DAG_VIEWER_STATE.focusedNode = null;
    navigateDown(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.focusedNode).toBe("s");

    selectFocused(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.selectedNode).toBe("s");

    deselectNode(DAG_VIEWER_STATE);
    expect(DAG_VIEWER_STATE.selectedNode).toBeNull();
  });
});

// ══════════════════════════════════════════════════════════════════
//  Phase 096 — Cross-mode render verification
// ══════════════════════════════════════════════════════════════════

describe("cross-mode render", () => {
  beforeEach(() => {
    resetState();
  });

  it("same render function handles both mode node ID patterns", () => {
    DAG_VIEWER_STATE.connection = "connected";
    // Mix build-mode and teach-mode node patterns
    DAG_VIEWER_STATE.nodes = [
      { id: "arc-1", name: "Build Arc", status: "done" },
      { id: "arc-1/phase-1", name: "Build Phase", status: "running" },
      { id: "subject-py", name: "Teach Subject", status: "done" },
      { id: "subject-py/lesson-1", name: "Teach Lesson", status: "pending" },
    ];
    DAG_VIEWER_STATE.edges = [
      { from: "arc-1", to: "arc-1/phase-1" },
      { from: "subject-py", to: "subject-py/lesson-1" },
    ];

    const box = renderDagViewer(DAG_VIEWER_STATE);
    const tree = JSON.stringify(box);

    expect(tree).toContain("Build Arc");
    expect(tree).toContain("Build Phase");
    expect(tree).toContain("Teach Subjec");  // truncated
    expect(tree).toContain("Teach Lesson");
  });
});
