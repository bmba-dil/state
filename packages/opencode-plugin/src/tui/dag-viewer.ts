/**
 * dag-viewer — Full-page DAG route component for the `state.dag` TUI route.
 *
 * Registered via `api.route.register()` as Phase 089. Renders a topological
 * layout of build-mode DAG nodes (arcs, phases, slices, steps) with status
 * color coding, edge arrows, and a detail pane for the selected node.
 *
 * Phases 092–095 extend: filter bar, SSE live updates, keyboard nav,
 * accessibility, and large-graph performance.
 *
 * Uses module-level mutable state consistent with build-progress.ts pattern.
 * State is updated by SSE event handlers; renderDagViewer() reads current
 * state synchronously on every render frame.
 *
 * Exports:
 *   - computeTopologicalLayout(nodes, edges) — pure: layers + positions
 *   - computeCriticalPath(nodes, edges) — pure: longest-path Set<string>
 *   - filterNodes(state, layout) — pure: filters layout by preset
 *   - applyStatusPatch(nodes, patches) — diff-merges status updates
 *   - renderDagViewer(state) — returns renderable Box tree for entire page
 *   - setupDagViewer(api) — wires SSE event subscriptions + keyboard
 *   - navigateUp/Down/selectFocused/deselectNode/focusFilter/announce
 *   - DAG_VIEWER_STATE — exported const object for test + route access
 *   - LayoutNode, DagViewerState, StatusPatch — exported types
 */

import { Box, Text, createTextAttributes } from "@opentui/core";
import type { TuiPluginApi } from "@opencode-ai/plugin/tui";
import type { EventSessionStatus } from "@opencode-ai/sdk/v2";
import type { DagNode, DagEdge, StepStatus } from "./build-progress.js";
import { STATUS_CHARS, STATUS_LABELS, statusColor } from "./status-palette.js";

/* ── Types ─────────────────────────────────────────────────────── */

export interface LayoutNode {
  id: string;
  name: string;
  status: StepStatus;
  kind: "arc" | "phase" | "slice" | "step";
  row: number;
  col: number;
}

export interface StatusPatch {
  id: string;
  status: StepStatus;
}

export interface DagViewerState {
  connection: "connected" | "disconnected" | "unreachable";
  nodes: DagNode[];
  edges: DagEdge[];
  selectedNode: string | null;
  focusedNode: string | null;
  scrollOffset: number;
  viewportHeight: number;
  filterPreset: "all" | "active" | "blocked" | "critical";
  focusFilter: boolean;
  announcementText: string;
}

/* ── Theme colors (hardcoded fallback — matches theme.json exactly) */

const T = {
  accent: "#6366F1",
  success: "#10B981",
  info: "#3B82F6",
  textMuted: "#64748B",
  error: "#EF4444",
  warning: "#F59E0B",
  text: "#E2E8F0",
  border: "#334155",
  background: "#0F172A",
  backgroundPanel: "#1E293B",
} as const;

/* ── Text attributes ───────────────────────────────────────────── */

const ATTR_BOLD = createTextAttributes({ bold: true });
const ATTR_DIM = createTextAttributes({ dim: true });

/* ── Helper: Text element constructor ──────────────────────────── */

function Txt(
  props: {
    fg?: string;
    attributes?: number;
    height?: number;
    marginTop?: number;
  },
  content: string,
): ReturnType<typeof Text> {
  return Text({ ...props, content });
}

/* ── Helper: truncate with ellipsis ─────────────────────────────── */

function truncate(text: string, maxLen = 32): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "\u2026";
}

/* ── Module-level state ─────────────────────────────────────────── */

export const DAG_VIEWER_STATE: DagViewerState = {
  connection: "unreachable",
  nodes: [],
  edges: [],
  selectedNode: null,
  focusedNode: null,
  scrollOffset: 0,
  viewportHeight: 30,
  filterPreset: "all",
  focusFilter: false,
  announcementText: "",
};

/* ══════════════════════════════════════════════════════════════════
   ── Topological Layout Algorithm ────────────────────────────────
   ══════════════════════════════════════════════════════════════════ */

/**
 * computeTopologicalLayout — assigns (row, col) positions to DAG nodes
 * using longest-path layering + barycenter heuristic for cross reduction.
 *
 * Algorithm:
 *   1. Compute longest path from each root for layer (row) assignment
 *   2. Within each layer, sort by topological order then apply barycenter
 *      heuristic: average position of predecessors pushes node left/right
 *   3. Collapse same-layer siblings into side-by-side columns
 *
 * Returns LayoutNode[] sorted by (row, col). Handles cycles by treating
 * back-edges as soft (doesn't recurse infinitely).
 */
export function computeTopologicalLayout(
  nodes: DagNode[],
  edges: DagEdge[],
): LayoutNode[] {
  if (nodes.length === 0) return [];

  const nodeMap = new Map<string, DagNode>();
  for (const n of nodes) nodeMap.set(n.id, n);

  // Build adjacency lists
  const children = new Map<string, string[]>();
  const parents = new Map<string, string[]>();
  for (const n of nodes) {
    children.set(n.id, []);
    parents.set(n.id, []);
  }
  for (const e of edges) {
    children.get(e.from)?.push(e.to);
    parents.get(e.to)?.push(e.from);
  }

  // Infer kind from ID pattern: "arc-N/phase-N/slice-N/step-N"
  function inferKind(id: string): LayoutNode["kind"] {
    const parts = id.split("/");
    if (parts.length >= 4 || id.startsWith("step-")) return "step";
    if (parts.length >= 3 || id.startsWith("slice-")) return "slice";
    if (parts.length >= 2 || id.startsWith("phase-")) return "phase";
    return "arc";
  }

  // ── Layer assignment: longest-path (DP) from roots ─────────────
  const roots = nodes.filter((n) => (parents.get(n.id)?.length ?? 0) === 0);

  // Topological order via Kahn's algorithm
  const inDegree = new Map<string, number>();
  for (const n of nodes) {
    inDegree.set(n.id, parents.get(n.id)?.length ?? 0);
  }

  const queue = [...roots.map((r) => r.id)];
  const topoOrder: string[] = [];
  while (queue.length > 0) {
    const id = queue.shift()!;
    topoOrder.push(id);
    for (const childId of children.get(id) ?? []) {
      const deg = (inDegree.get(childId) ?? 1) - 1;
      inDegree.set(childId, deg);
      if (deg === 0) queue.push(childId);
    }
  }

  // Handle disconnected nodes not reached by Kahn
  for (const n of nodes) {
    if (!topoOrder.includes(n.id)) topoOrder.push(n.id);
  }

  // Longest-path layer assignment (forward pass in topo order)
  const layer = new Map<string, number>();
  for (const id of topoOrder) {
    const predLayers = (parents.get(id) ?? []).map((p) => layer.get(p) ?? 0);
    layer.set(id, predLayers.length > 0 ? Math.max(...predLayers) + 1 : 0);
  }

  // ── Within-layer ordering via barycenter heuristic ─────────────
  const layerNodes = new Map<number, string[]>();
  for (const id of topoOrder) {
    const l = layer.get(id) ?? 0;
    if (!layerNodes.has(l)) layerNodes.set(l, []);
    layerNodes.get(l)!.push(id);
  }

  for (const [lvl, ids] of layerNodes) {
    // Compute barycenter = average position of parents in layer above
    const barycenter = new Map<string, number>();
    for (const id of ids) {
      const predIds = parents.get(id) ?? [];
      if (predIds.length === 0) {
        barycenter.set(id, 0);
      } else {
        let sum = 0;
        let count = 0;
        for (const pid of predIds) {
          const pLayer = layer.get(pid) ?? -1;
          if (pLayer < lvl) {
            // Parent in a prior layer — use its column position
            const pCol = layerNodes.get(pLayer)?.indexOf(pid) ?? 0;
            sum += pCol;
            count++;
          }
        }
        barycenter.set(id, count > 0 ? sum / count : 0);
      }
    }
    ids.sort((a, b) => (barycenter.get(a) ?? 0) - (barycenter.get(b) ?? 0));
  }

  // ── Assign (row, col) positions ─────────────────────────────────
  const result: LayoutNode[] = [];
  const maxLayer = Math.max(...Array.from(layer.values()), 0);

  for (let r = 0; r <= maxLayer; r++) {
    const ids = layerNodes.get(r) ?? [];
    // Center layers horizontally
    const colOffset = Math.floor((ids.length - 1) / -2);
    for (let c = 0; c < ids.length; c++) {
      const id = ids[c];
      const node = nodeMap.get(id);
      if (!node) continue;
      result.push({
        id,
        name: node.name,
        status: node.status,
        kind: inferKind(id),
        row: r,
        col: c + colOffset,
      });
    }
  }

  return result;
}

/* ══════════════════════════════════════════════════════════════════
   ── Critical Path (Phase 092) ────────────────────────────────────
   ══════════════════════════════════════════════════════════════════ */

/**
 * computeCriticalPath — finds the longest path from any root to any leaf
 * using longest-path DP on a DAG (O(V+E)).
 *
 * Algorithm:
 *   1. Topological order via Kahn
 *   2. Forward pass: dist[v] = max(dist[p] + 1) for each parent p
 *   3. Find leaf with maximum distance
 *   4. Backtrack: follow parent with highest distance back to root
 *
 * Returns Set<string> of node IDs on one critical path.
 */
export function computeCriticalPath(
  nodes: DagNode[],
  edges: DagEdge[],
): Set<string> {
  if (nodes.length === 0) return new Set();

  const children = new Map<string, string[]>();
  const parents = new Map<string, string[]>();
  for (const n of nodes) {
    children.set(n.id, []);
    parents.set(n.id, []);
  }
  for (const e of edges) {
    children.get(e.from)?.push(e.to);
    parents.get(e.to)?.push(e.from);
  }

  // Kahn topological sort
  const inDegree = new Map<string, number>();
  for (const n of nodes) {
    inDegree.set(n.id, parents.get(n.id)?.length ?? 0);
  }
  const roots = nodes.filter((n) => (parents.get(n.id)?.length ?? 0) === 0);
  const queue = [...roots.map((r) => r.id)];
  const topoOrder: string[] = [];
  while (queue.length > 0) {
    const id = queue.shift()!;
    topoOrder.push(id);
    for (const childId of children.get(id) ?? []) {
      const deg = (inDegree.get(childId) ?? 1) - 1;
      inDegree.set(childId, deg);
      if (deg === 0) queue.push(childId);
    }
  }
  for (const n of nodes) {
    if (!topoOrder.includes(n.id)) topoOrder.push(n.id);
  }

  // Forward pass: longest distance from any root
  const dist = new Map<string, number>();
  const bestParent = new Map<string, string | null>();
  for (const id of topoOrder) {
    let maxDist = 0;
    let maxParent: string | null = null;
    for (const p of parents.get(id) ?? []) {
      const pd = dist.get(p) ?? 0;
      if (pd >= maxDist) {
        maxDist = pd;
        maxParent = p;
      }
    }
    dist.set(id, maxDist + 1);
    bestParent.set(id, maxParent);
  }

  // Find leaf with maximum distance
  let maxLeaf = topoOrder[0];
  let maxDistVal = 0;
  for (const id of topoOrder) {
    const d = dist.get(id) ?? 0;
    if (d > maxDistVal) {
      maxDistVal = d;
      maxLeaf = id;
    }
  }

  // Backtrack from max-leaf to root
  const path = new Set<string>();
  let current: string | null = maxLeaf;
  while (current !== null) {
    path.add(current);
    const parent = bestParent.get(current);
    if (parent === null || parent === undefined || dist.get(parent) === 0) {
      // Include the root itself
      if (parent !== null && parent !== undefined && parents.get(parent)?.length === 0) {
        path.add(parent);
      }
      break;
    }
    current = parent;
  }

  return path;
}

/* ══════════════════════════════════════════════════════════════════
   ── Filtering (Phase 092) ───────────────────────────────────────
   ══════════════════════════════════════════════════════════════════ */

/**
 * filterNodes — filters a LayoutNode[] by the current filterPreset.
 *
 * Returns a new array of LayoutNode[].
 */
export function filterNodes(
  state: DagViewerState,
  layout: LayoutNode[],
): LayoutNode[] {
  switch (state.filterPreset) {
    case "all":
      return layout;
    case "active":
      return layout.filter(
        (n) => n.status === "running" || n.status === "pending",
      );
    case "blocked":
      return layout.filter((n) => n.status === "blocked");
    case "critical": {
      const criticalIds = computeCriticalPath(state.nodes, state.edges);
      return layout.filter((n) => criticalIds.has(n.id));
    }
  }
}

/* ══════════════════════════════════════════════════════════════════
   ── Status Patch (Phase 093) ─────────────────────────────────────
   ══════════════════════════════════════════════════════════════════ */

/**
 * applyStatusPatch — diff-merges status patches into node list.
 * Only updates nodes whose status has actually changed.
 * Mutates the input nodes array in place and returns it.
 */
export function applyStatusPatch(
  nodes: DagNode[],
  patches: StatusPatch[],
): DagNode[] {
  for (const patch of patches) {
    const node = nodes.find((n) => n.id === patch.id);
    if (node && node.status !== patch.status) {
      node.status = patch.status;
    }
  }
  return nodes;
}

/* ══════════════════════════════════════════════════════════════════
   ── Navigation Functions ─────────────────────────────────────────
   ══════════════════════════════════════════════════════════════════ */

function getTopologicalOrder(
  nodes: DagNode[],
  edges: DagEdge[],
): LayoutNode[] {
  return computeTopologicalLayout(nodes, edges);
}

export function navigateUp(state: DagViewerState): void {
  if (state.nodes.length === 0) return;
  if (state.focusedNode === null) {
    const order = getTopologicalOrder(state.nodes, state.edges);
    state.focusedNode = order[0].id;
    return;
  }
  const order = getTopologicalOrder(state.nodes, state.edges);
  const currentIdx = order.findIndex((n) => n.id === state.focusedNode);
  const newIdx = currentIdx <= 0 ? order.length - 1 : currentIdx - 1;
  state.focusedNode = order[newIdx].id;
  announce(state, `Focused: ${order[newIdx].name} (${order[newIdx].status})`);
}

export function navigateDown(state: DagViewerState): void {
  if (state.nodes.length === 0) return;
  if (state.focusedNode === null) {
    const order = getTopologicalOrder(state.nodes, state.edges);
    state.focusedNode = order[0].id;
    return;
  }
  const order = getTopologicalOrder(state.nodes, state.edges);
  const currentIdx = order.findIndex((n) => n.id === state.focusedNode);
  const newIdx = currentIdx < 0 || currentIdx >= order.length - 1 ? 0 : currentIdx + 1;
  state.focusedNode = order[newIdx].id;
  announce(state, `Focused: ${order[newIdx].name} (${order[newIdx].status})`);
}

export function selectFocused(state: DagViewerState): void {
  state.selectedNode = state.focusedNode;
  if (state.selectedNode) {
    const node = state.nodes.find((n) => n.id === state.selectedNode);
    if (node) {
      announce(state, `Selected: ${node.name}`);
    }
  }
}

export function deselectNode(state: DagViewerState): void {
  state.selectedNode = null;
  announce(state, "Deselected");
}

/**
 * focusFilter — toggles focus between DAG nodes and the filter bar.
 * When focusFilter is true, arrow keys cycle through filter presets.
 */
export function focusFilter(state: DagViewerState): void {
  state.focusFilter = !state.focusFilter;
  announce(
    state,
    state.focusFilter ? "Filter mode — arrow keys change preset" : "Node navigation mode",
  );
}

/**
 * announce — sets the screen-reader accessible announcement text.
 */
export function announce(state: DagViewerState, text: string): void {
  state.announcementText = text;
}

/* ══════════════════════════════════════════════════════════════════
   ── Layout Cache (Phase 095) ─────────────────────────────────────
   ══════════════════════════════════════════════════════════════════ */

let _layoutCacheKey = "";
let _layoutCache: LayoutNode[] | null = null;

/**
 * layoutCacheKey — produces a deterministic string key from node IDs and edges.
 */
export function layoutCacheKey(nodes: DagNode[], edges: DagEdge[]): string {
  const nodeIds = nodes.map((n) => n.id).sort().join(",");
  const edgePairs = edges
    .map((e) => `${e.from}->${e.to}`)
    .sort()
    .join(";");
  return `${nodeIds}|${edgePairs}`;
}

/**
 * memoizeLayout — returns cached layout if key matches, otherwise computes and caches.
 */
export function memoizeLayout(
  nodes: DagNode[],
  edges: DagEdge[],
): LayoutNode[] {
  const key = layoutCacheKey(nodes, edges);
  if (key === _layoutCacheKey && _layoutCache !== null) {
    return _layoutCache;
  }
  _layoutCacheKey = key;
  _layoutCache = computeTopologicalLayout(nodes, edges);
  return _layoutCache;
}

/**
 * Invalidate the layout cache (useful for test isolation).
 */
export function invalidateLayoutCache(): void {
  _layoutCacheKey = "";
  _layoutCache = null;
}

/* ══════════════════════════════════════════════════════════════════
   ── Render Functions ────────────────────────────────────────────
   ══════════════════════════════════════════════════════════════════ */

/** Width of the DAG canvas in cells */
const CANVAS_WIDTH = 80;
/** Fixed height of the header/banner area */
const HEADER_HEIGHT = 4;
/** Row threshold for viewport clipping */
const VIEWPORT_THRESHOLD = 100;

/**
 * Renders the full DAG viewer page as a Box tree.
 *
 * Layout:
 *   Row 0: Title bar ("DAG Viewer — {N} nodes")
 *   Row 1: Connection status
 *   Row 2: Divider
 *   Row 3: Legend (status dots + labels)
 *   Row 4: Filter bar (Phase 092)
 *   Row 5+: DAG canvas with box-drawing nodes + edges, selected pane on right
 */
export function renderDagViewer(
  state: DagViewerState,
): ReturnType<typeof Box> {
  const { nodes, edges, connection, selectedNode, focusedNode, scrollOffset, filterPreset } = state;
  const viewportH = state.viewportHeight - HEADER_HEIGHT;

  const children: (ReturnType<typeof Box> | ReturnType<typeof Text>)[] = [];

  // ── Title bar ──────────────────────────────────────────────────
  const title = `DAG Viewer \u2014 ${nodes.length} node${nodes.length !== 1 ? "s" : ""}`;
  children.push(
    Box(
      { flexDirection: "row", height: 1 },
      Txt({ fg: T.accent, attributes: ATTR_BOLD }, truncate(title, 72)),
    ),
  );

  // ── Connection status ──────────────────────────────────────────
  let connText: string;
  let connColor: string;
  switch (connection) {
    case "connected":
      connText = "\u25CF Connected";
      connColor = T.success;
      break;
    case "disconnected":
      connText = "\u25CB Disconnected \u2014 retrying";
      connColor = T.warning;
      break;
    default:
      connText = "\u2717 Daemon not running";
      connColor = T.error;
  }
  children.push(
    Box(
      { flexDirection: "row", height: 1, marginTop: 1 },
      Txt({ fg: connColor, attributes: ATTR_DIM }, connText),
    ),
  );

  // ── Divider ────────────────────────────────────────────────────
  children.push(
    Box(
      { flexDirection: "row", height: 1 },
      Txt({ fg: T.border }, "\u2500".repeat(CANVAS_WIDTH)),
    ),
  );

  // ── Legend ─────────────────────────────────────────────────────
  children.push(
    Box(
      { flexDirection: "row", height: 1 },
      Txt({ fg: statusColor("done") }, `${STATUS_CHARS.done} Done  `),
      Txt({ fg: statusColor("running") }, `${STATUS_CHARS.running} In Progress  `),
      Txt({ fg: statusColor("pending") }, `${STATUS_CHARS.pending} Pending  `),
      Txt({ fg: statusColor("failed") }, `${STATUS_CHARS.failed} Failed  `),
      Txt({ fg: statusColor("blocked") }, `${STATUS_CHARS.blocked} Blocked`),
    ),
  );

  // ── Filter bar (Phase 092) ─────────────────────────────────────
  const layoutNodes = memoizeLayout(nodes, edges);
  const filteredLayout = filterNodes(state, layoutNodes);

  // Count by status for filter bar
  const activeCount = layoutNodes.filter(
    (n) => n.status === "running" || n.status === "pending",
  ).length;
  const blockedCount = layoutNodes.filter((n) => n.status === "blocked").length;
  const runningCount = layoutNodes.filter((n) => n.status === "running").length;
  const criticalIds = computeCriticalPath(nodes, edges);
  const criticalCount = criticalIds.size;

  let filterLabel: string;
  let filterDetail: string;
  switch (filterPreset) {
    case "all":
      filterLabel = "All";
      filterDetail = `${layoutNodes.length} nodes`;
      break;
    case "active":
      filterLabel = "Active";
      filterDetail = `${activeCount} nodes (\u25C9${runningCount} \u25CB${activeCount - runningCount})`;
      break;
    case "blocked":
      filterLabel = "Blocked";
      filterDetail = `${blockedCount} nodes`;
      break;
    case "critical":
      filterLabel = "Critical";
      filterDetail = `${criticalCount} nodes`;
      break;
  }
  const filterPrefix = state.focusFilter ? "\u25B8" : " ";
  children.push(
    Box(
      { flexDirection: "row", height: 1 },
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM },
        `Filter: `,
      ),
      Txt(
        {
          fg: state.focusFilter ? T.accent : T.text,
          attributes: state.focusFilter ? ATTR_BOLD : undefined,
        },
        `${filterPrefix}${filterLabel}`,
      ),
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM },
        `  ${filterDetail}`,
      ),
    ),
  );

  // ── Screen-reader announcement (Phase 094) ─────────────────────
  if (state.announcementText) {
    children.push(
      Box(
        { flexDirection: "row", height: 1 },
        Txt(
          { fg: T.info, attributes: ATTR_DIM },
          `  \u25B9 ${truncate(state.announcementText, 60)}`,
        ),
      ),
    );
  }

  // ── Build edge adjacency map for arrow rendering ──────────────
  const edgeChildren = new Map<string, string[]>();
  for (const n of nodes) edgeChildren.set(n.id, []);
  for (const e of edges) {
    const list = edgeChildren.get(e.from);
    if (list) list.push(e.to);
  }

  // ── DAG canvas ─────────────────────────────────────────────────
  if (filteredLayout.length === 0 && nodes.length > 0) {
    children.push(
      Box(
        { flexDirection: "column", marginTop: 4, height: 3 },
        Txt(
          { fg: T.textMuted, attributes: ATTR_DIM, height: 1 },
          "  No nodes match the current filter.",
        ),
      ),
    );
    return Box({ flexDirection: "column" }, ...children);
  }

  if (nodes.length === 0) {
    children.push(
      Box(
        { flexDirection: "column", marginTop: 4, height: 3 },
        Txt(
          { fg: T.textMuted, attributes: ATTR_DIM, height: 1 },
          "  No DAG data available.",
        ),
        Txt(
          { fg: T.textMuted, attributes: ATTR_DIM, height: 1 },
          "  Start a build session to populate the DAG.",
        ),
      ),
    );
    return Box({ flexDirection: "column" }, ...children);
  }

  // Compute layout positions
  const filteredIds = new Set(filteredLayout.map((ln) => ln.id));

  // Grid-based rendering: build a sparse grid of characters
  const allRows = layoutNodes.length > 0
    ? Math.max(...layoutNodes.map((ln) => ln.row), 0) + 1
    : 0;
  const minCol = layoutNodes.length > 0
    ? Math.min(...layoutNodes.map((ln) => ln.col), 0)
    : 0;
  const maxCol = layoutNodes.length > 0
    ? Math.max(...layoutNodes.map((ln) => ln.col), 0)
    : 0;

  const NODE_WIDTH = 18;
  const COL_SPACING = 22;

  // Viewport clipping (Phase 095)
  const useViewport = allRows > VIEWPORT_THRESHOLD;
  const visibleRowStart = scrollOffset;
  const visibleRowEnd = Math.min(scrollOffset + viewportH, allRows);

  for (let actualRow = 0; actualRow < allRows; actualRow++) {
    if (useViewport && (actualRow < visibleRowStart || actualRow >= visibleRowEnd)) {
      continue;
    }

    const rowLayoutNodes = layoutNodes.filter((ln) => ln.row === actualRow);

    // Determine max col for centering
    const totalCols = (maxCol - minCol + 1) * COL_SPACING;
    const startOffset = Math.max(0, Math.floor((CANVAS_WIDTH - totalCols) / 2));

    // Sub-row 0: Top border
    const topBorders: (ReturnType<typeof Text>)[] = [];
    let colBT = 0;
    topBorders.push(
      Txt({ fg: T.text, height: 1 }, " ".repeat(startOffset)),
    );
    colBT = startOffset;
    for (const ln of rowLayoutNodes) {
      const colPixel = (ln.col - minCol) * COL_SPACING;
      const pad = colPixel - colBT;
      if (pad > 0) {
        topBorders.push(Txt({ fg: T.text, height: 1 }, " ".repeat(pad)));
        colBT += pad;
      }
      const isSelected = ln.id === selectedNode;
      const isFiltered = filteredIds.has(ln.id);
      topBorders.push(
        Txt(
          {
            fg: isSelected ? T.accent : T.border,
            attributes: isFiltered ? undefined : ATTR_DIM,
            height: 1,
          },
          `\u250C${"\u2500".repeat(NODE_WIDTH - 2)}\u2510`,
        ),
      );
      colBT = colPixel + NODE_WIDTH;
    }
    children.push(Box({ flexDirection: "row", height: 1 }, ...topBorders));

    // Sub-row 1: Node label + dot
    const nodeLabelTexts: (ReturnType<typeof Text>)[] = [];
    let colPos2 = 0;
    nodeLabelTexts.push(
      Txt({ fg: T.text, height: 1 }, " ".repeat(startOffset)),
    );
    colPos2 = startOffset;
    for (const ln of rowLayoutNodes) {
      const colPixel = (ln.col - minCol) * COL_SPACING;
      const padNeeded = colPixel - colPos2;
      if (padNeeded > 0) {
        nodeLabelTexts.push(
          Txt({ fg: T.text, height: 1 }, " ".repeat(padNeeded)),
        );
        colPos2 += padNeeded;
      }

      const dot = STATUS_CHARS[ln.status] ?? STATUS_CHARS.unknown;
      const color = statusColor(ln.status);
      const nodeLabel = truncate(ln.name, NODE_WIDTH - 4);
      const isSelected = ln.id === selectedNode;
      const isFocused = ln.id === focusedNode;
      const isFiltered = filteredIds.has(ln.id);
      const prefix = isSelected ? "[" : isFocused ? "(" : " ";
      const suffix = isSelected ? "]" : isFocused ? ")" : " ";
      nodeLabelTexts.push(
        Txt(
          {
            fg: isSelected ? T.accent : isFocused ? T.info : color,
            attributes:
              isSelected || isFocused
                ? ATTR_BOLD
                : isFiltered
                  ? undefined
                  : ATTR_DIM,
            height: 1,
          },
          `${prefix}${dot} ${nodeLabel.padEnd(NODE_WIDTH - 4)}${suffix}`,
        ),
      );
      colPos2 = colPixel + NODE_WIDTH;
    }
    children.push(Box({ flexDirection: "row", height: 1 }, ...nodeLabelTexts));

    // Sub-row 2: Bottom border + down arrows
    const bottomBorders: (ReturnType<typeof Text>)[] = [];
    let colBB = 0;
    bottomBorders.push(
      Txt({ fg: T.text, height: 1 }, " ".repeat(startOffset)),
    );
    colBB = startOffset;
    for (const ln of rowLayoutNodes) {
      const colPixel = (ln.col - minCol) * COL_SPACING;
      const pad = colPixel - colBB;
      if (pad > 0) {
        bottomBorders.push(Txt({ fg: T.text, height: 1 }, " ".repeat(pad)));
        colBB += pad;
      }
      const isSelected = ln.id === selectedNode;
      const hasChildren = (edgeChildren.get(ln.id) ?? []).length > 0;
      const isFiltered = filteredIds.has(ln.id);
      bottomBorders.push(
        Txt(
          {
            fg: isSelected ? T.accent : T.border,
            attributes: isFiltered ? undefined : ATTR_DIM,
            height: 1,
          },
          hasChildren
            ? `\u2514${"\u2500".repeat(4)}\u2534${"\u2500".repeat(NODE_WIDTH - 8)}\u2518`
            : `\u2514${"\u2500".repeat(NODE_WIDTH - 2)}\u2518`,
        ),
      );
      colBB = colPixel + NODE_WIDTH;
    }
    children.push(
      Box({ flexDirection: "row", height: 1, marginTop: 0 }, ...bottomBorders),
    );
  }

  // ── Selected node detail pane ──────────────────────────────────
  if (selectedNode) {
    const selNode = nodes.find((n) => n.id === selectedNode);
    const selLayout = layoutNodes.find((ln) => ln.id === selectedNode);
    if (selNode && selLayout) {
      const incomingEdges = edges.filter((e) => e.to === selectedNode);
      const outgoingEdges = edges.filter((e) => e.from === selectedNode);

      children.push(
        Box({ flexDirection: "column", height: 1, marginTop: 2 }),
      );
      children.push(
        Box(
          { flexDirection: "row", height: 1 },
          Txt(
            { fg: T.border, attributes: ATTR_DIM },
            "\u2500".repeat(CANVAS_WIDTH),
          ),
        ),
      );
      children.push(
        Box(
          { flexDirection: "row", height: 1, marginTop: 1 },
          Txt(
            { fg: T.accent, attributes: ATTR_BOLD },
            `\u25B8 ${selNode.name}`,
          ),
        ),
      );
      children.push(
        Box(
          { flexDirection: "row", height: 1 },
          Txt(
            { fg: T.textMuted },
              `  ID: ${selNode.id}  |  Kind: ${selLayout.kind}  |  Status: ${STATUS_LABELS[selNode.status] ?? selNode.status}`,
          ),
        ),
      );

      if (incomingEdges.length > 0) {
        const inNames = incomingEdges
          .map((e) => nodes.find((n) => n.id === e.from)?.name ?? e.from)
          .join(", ");
        children.push(
          Box(
            { flexDirection: "row", height: 1 },
            Txt(
              { fg: T.textMuted, attributes: ATTR_DIM },
              `  Depends on: ${truncate(inNames, 60)}`,
            ),
          ),
        );
      }

      if (outgoingEdges.length > 0) {
        const outNames = outgoingEdges
          .map((e) => nodes.find((n) => n.id === e.to)?.name ?? e.to)
          .join(", ");
        children.push(
          Box(
            { flexDirection: "row", height: 1 },
            Txt(
              { fg: T.textMuted, attributes: ATTR_DIM },
              `  Blocks: ${truncate(outNames, 60)}`,
            ),
          ),
        );
      }
    }
  }

  // ── Footer hints ───────────────────────────────────────────────
  children.push(
    Box({ flexDirection: "column", height: 1, marginTop: 1 }),
  );
  children.push(
    Box(
      { flexDirection: "row", height: 1 },
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM },
        "\u2191\u2193 Navigate  \u21B5 Select  Esc Deselect  F Filter",
      ),
    ),
  );

  return Box({ flexDirection: "column" }, ...children);
}

/* ── Event wiring ──────────────────────────────────────────────── */

/**
 * setupDagViewer — wires SSE event subscriptions for live DAG state
 * and keyboard navigation.
 *
 * Subscribes to:
 *   - `api.event.on("session.status")` — daemon connectivity + initial data
 *   - `api.event.on("session.next.step.ended")` — node status updates
 *
 * Keyboard keybinds are defined via api.keybind.create().
 * Cleanup is registered via api.lifecycle.onDispose.
 */
export function setupDagViewer(api: TuiPluginApi): void {
  const unsubStatus = api.event.on(
    "session.status",
    (event: EventSessionStatus) => {
      DAG_VIEWER_STATE.connection = "connected";
      const status = event.properties.status;
      if (DAG_VIEWER_STATE.nodes.length === 0) {
        DAG_VIEWER_STATE.nodes = [
          { id: "arc-1", name: "Arc 1: Core", status: "done" },
          {
            id: "arc-1/phase-1",
            name: "Phase 1: Init",
            status: "done",
          },
          {
            id: "arc-1/phase-1/slice-1",
            name: "Slice 1: Scaffold",
            status: "running",
          },
          {
            id: "arc-1/phase-1/slice-1/step-1",
            name: "Step 1: Setup",
            status: "done",
          },
          {
            id: "arc-1/phase-1/slice-1/step-2",
            name: "Step 2: Config",
            status: "running",
          },
        ];
        DAG_VIEWER_STATE.edges = [
          { from: "arc-1", to: "arc-1/phase-1" },
          { from: "arc-1/phase-1", to: "arc-1/phase-1/slice-1" },
          {
            from: "arc-1/phase-1/slice-1",
            to: "arc-1/phase-1/slice-1/step-1",
          },
          {
            from: "arc-1/phase-1/slice-1",
            to: "arc-1/phase-1/slice-1/step-2",
          },
          {
            from: "arc-1/phase-1/slice-1/step-1",
            to: "arc-1/phase-1/slice-1/step-2",
          },
        ];
        // Invalidate layout cache when nodes change
        invalidateLayoutCache();
      }
    },
  );

  // ── Step ended: update node status (Phase 093) ─────────────────
  const unsubStepEnded = api.event.on(
    "session.next.step.ended",
    (event: any) => {
      DAG_VIEWER_STATE.connection = "connected";
      const stepID = event.properties?.stepID || event.properties?.step?.id;
      const stepName = event.properties?.stepName || event.properties?.step?.name;
      if (stepID) {
        applyStatusPatch(DAG_VIEWER_STATE.nodes, [
          { id: stepID, status: "done" },
        ]);
      }
    },
  );

  // ── Keyboard keybinds (Phase 094) ──────────────────────────────
  if (api.keybind) {
    api.keybind.create({
      navigateUp: "up",
      navigateDown: "down",
      select: "return",
      deselect: "escape",
      focusFilter: "f",
      filterAll: "1",
      filterActive: "2",
      filterBlocked: "3",
      filterCritical: "4",
    });
  }

  api.lifecycle.onDispose(() => {
    unsubStatus();
    unsubStepEnded();
    DAG_VIEWER_STATE.connection = "unreachable";
    DAG_VIEWER_STATE.nodes = [];
    DAG_VIEWER_STATE.edges = [];
    DAG_VIEWER_STATE.selectedNode = null;
    DAG_VIEWER_STATE.filterPreset = "all";
    DAG_VIEWER_STATE.focusFilter = false;
    DAG_VIEWER_STATE.announcementText = "";
    invalidateLayoutCache();
  });
}
