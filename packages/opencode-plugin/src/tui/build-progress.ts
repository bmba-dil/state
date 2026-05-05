/**
 * build-progress — BuildProgress sub-component for the `sidebar_content` TUI slot.
 *
 * Subscribes to daemon SSE events via opencode's `api.event` bus, renders the
 * current Step status with color coding, and draws a Slice DAG thumbnail using
 * box-drawing characters with per-node status colors.
 *
 * Uses module-level mutable state (consistent with sidebar-content-renderer.ts
 * pattern). State is updated by event handlers; renderBuildProgress() reads
 * current state synchronously on every render frame.
 *
 * Exports:
 *   - setupBuildProgress(api) — wires event subscriptions, registers cleanup
 *   - renderBuildProgress() — returns renderable Box tree for current state
 *   - stepStatusColor(status) — pure function: maps StepStatus to hex color
 *   - renderDagBox(nodes, edges) — pure function: box-drawing DAG thumbnail
 *   - BUILD_PROGRESS_STATE — exported const object for test inspection
 */

import { Box, Text, createTextAttributes } from "@opentui/core";
import type { TuiPluginApi } from "@opencode-ai/plugin/tui";
import type { SessionStatus } from "@opencode-ai/sdk/v2";
import type { EventSessionStatus } from "@opencode-ai/sdk/v2";
import { STATUS_CHARS, STATUS_LABELS, statusColor, stepStatusColor } from "./status-palette.js";
import type { StepStatus } from "./status-palette.js";

export { statusColor, stepStatusColor };
export type { StepStatus };

/* ── Types ─────────────────────────────────────────────────────── */

export type ConnectionStatus = "connected" | "disconnected" | "unreachable";

export interface BuildProgressState {
  connection: ConnectionStatus;
  sessionStatus: SessionStatus | null;
  sessionID: string | null;
}

export interface DagNode {
  id: string;
  name: string;
  status: StepStatus;
}

export interface DagEdge {
  from: string;
  to: string;
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
} as const;

/* ── Text attributes (pre-computed for performance) ─────────────── */

const ATTR_BOLD = createTextAttributes({ bold: true });
const ATTR_DIM = createTextAttributes({ dim: true });

/* ── Module-level state ─────────────────────────────────────────── */

export const BUILD_PROGRESS_STATE: BuildProgressState = {
  connection: "unreachable",
  sessionStatus: null,
  sessionID: null,
};

/* ── Helper: Text element constructor ──────────────────────────── */

interface TextElProps {
  fg?: string;
  attributes?: number;
  height?: number;
  marginTop?: number;
  marginBottom?: number;
}

function Txt(props: TextElProps, content: string): ReturnType<typeof Text> {
  return Text({ ...props, content });
}

/* ── Helper: truncate with ellipsis ─────────────────────────────── */

function truncate(text: string, maxLen = 28): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "\u2026";
}

/* ── Exported pure functions ────────────────────────────────────── */

/**
 * Returns the status indicator text for the connection state.
 * Used at the top of the DAG area within renderBuildProgress().
 */
function connectionStatusLine(): string {
  switch (BUILD_PROGRESS_STATE.connection) {
    case "disconnected":
      return "Connection lost. Retrying\u2026";
    case "unreachable":
      return "state-daemon not running";
    default:
      return "";
  }
}

/**
 * Derives a StepStatus from the current SessionStatus.
 */
function deriveStepStatus(): StepStatus {
  const status = BUILD_PROGRESS_STATE.sessionStatus;
  if (status === null) return "unknown";
  switch (status.type) {
    case "idle":
      return "done";
    case "busy":
      return "running";
    case "retry":
      return "retry";
    default:
      return "unknown";
  }
}

/**
 * Renders a multi-line box-drawing DAG thumbnail as a single string.
 *
 * Width: 28 cells. Uses Unicode box-drawing characters (U+2500 family).
 * Status dots: ● (done/idle), ◉ (running/retry), ○ (pending/unknown), ✗ (blocked).
 * Edge rendering: horizontal nodes connected by ──→ on a single line.
 *
 * Empty state: centered "No Slices defined" within a 28-wide box.
 */
export function renderDagBox(nodes: DagNode[], edges: DagEdge[]): string {
  const W = 28;
  const innerW = W - 2;

  // ── Empty state ───────────────────────────────────────────────
  if (nodes.length === 0) {
    const msg = "No Slices defined";
    const padLeft = Math.floor((innerW - 2 - msg.length) / 2);
    const padRight = innerW - 2 - msg.length - padLeft;
    return [
      `\u250C${"\u2500".repeat(innerW)}\u2510`,
      `\u2502 ${" ".repeat(Math.max(0, padLeft))}${msg}${" ".repeat(Math.max(0, padRight))} \u2502`,
      `\u2514${"\u2500".repeat(innerW)}\u2518`,
    ].join("\n");
  }

  const lines: string[] = [];

  // ── Top border with title ──────────────────────────────────────
  const title = "Slice DAG";
  const topFill = innerW - 3 - title.length;
  lines.push(
    `\u250C\u2500 ${title} ${"\u2500".repeat(Math.max(0, topFill))}\u2510`,
  );

  // ── Node rows (horizontal chain layout) ─────────────────────────
  // Nodes connected by edges render on the same line with ──→ between them.
  // Disconnected/unconnected nodes render on separate lines below.
  // Simple approach: follow forward edges from each root, chain connected
  // nodes horizontally on one line; remaining nodes get their own lines.

  const nodeMap = new Map<string, DagNode>();
  for (const node of nodes) nodeMap.set(node.id, node);

  // Build adjacency map: parentId → [childId, ...]
  const outgoingEdges = new Map<string, string[]>();
  for (const edge of edges) {
    const list = outgoingEdges.get(edge.from) || [];
    list.push(edge.to);
    outgoingEdges.set(edge.from, list);
  }

  // Find roots: nodes that are NOT the target of any edge
  const hasEdgeTo = new Set(edges.map((e) => e.to));
  const rootIds = nodes.filter((n) => !hasEdgeTo.has(n.id)).map((n) => n.id);

  const rendered = new Set<string>();

  // Process each root: follow edge chain and render on one line
  for (const rootId of rootIds) {
    if (rendered.has(rootId)) continue;

    const chainParts: string[] = [];
    let current: string | undefined = rootId;

    while (current !== undefined && !rendered.has(current)) {
      rendered.add(current);
      const node = nodeMap.get(current);
      if (!node) break;
      const dot = STATUS_CHARS[node.status] || STATUS_CHARS.unknown;
      chainParts.push(`${dot} ${node.name}`);
      // Follow first edge from this node
      const childIds: string[] = outgoingEdges.get(current) || [];
      current = childIds.length > 0 ? childIds[0] : undefined;
    }

    // Build the row: join nodes with ──→ between them
    const connector = ` \u2500\u2500\u2192 `;
    let rowContent = chainParts.join(connector);
    if (rowContent.length > innerW - 2) {
      rowContent = rowContent.slice(0, innerW - 5) + "\u2026";
    }
    const rightPad = innerW - 2 - rowContent.length;
    lines.push(
      `\u2502 ${rowContent}${" ".repeat(Math.max(0, rightPad))} \u2502`,
    );
  }

  // Render any remaining unrendered nodes (disconnected)
  for (const node of nodes) {
    if (!rendered.has(node.id)) {
      rendered.add(node.id);
      const dot = STATUS_CHARS[node.status] || STATUS_CHARS.unknown;
      const lineContent = `${dot} ${node.name}`;
      const rightPad = innerW - 2 - lineContent.length;
      lines.push(
        `\u2502 ${lineContent}${" ".repeat(Math.max(0, rightPad))} \u2502`,
      );
    }
  }

  // ── Bottom border ──────────────────────────────────────────────
  lines.push(`\u2514${"\u2500".repeat(innerW)}\u2518`);

  return lines.join("\n");
}

/* ── Main render function ──────────────────────────────────────── */

/**
 * renderBuildProgress — returns a Box tree for the current BuildProgress state.
 *
 * Sections:
 *   A. Step status row (derived from sessionStatus)
 *   B. Divider (28 ─ chars)
 *   C. DAG area (placeholder DAG / error states based on connection)
 */
export function renderBuildProgress(): ReturnType<typeof Box> {
  const st = BUILD_PROGRESS_STATE;
  const step = deriveStepStatus();
  const color = statusColor(step);
  const dot = STATUS_CHARS[step] || STATUS_CHARS.unknown;

  // ── A. Step status row ─────────────────────────────────────────
  let statusLabel: string;
  switch (step) {
    case "running":
      statusLabel = "Running";
      break;
    case "done":
      statusLabel = "Idle";
      break;
    case "retry": {
      const retryStatus = st.sessionStatus as { type: "retry"; attempt: number };
      statusLabel = `Retrying (attempt ${retryStatus.attempt})`;
      break;
    }
    case "blocked":
      statusLabel = "Blocked";
      break;
    default:
      statusLabel = "Waiting";
  }

  let stepLine = `${dot} Step: ${statusLabel}`;
  if (st.sessionID) {
    const shortID = st.sessionID.slice(0, 8);
    stepLine += ` \u00b7 s:${shortID}\u2026`;
  }
  stepLine = truncate(stepLine);

  const children: (ReturnType<typeof Box> | ReturnType<typeof Text>)[] = [];

  children.push(
    Box(
      { flexDirection: "row", height: 1 },
      Txt({ fg: color, height: 1 }, stepLine),
    ),
  );

  // ── B. Divider ─────────────────────────────────────────────────
  children.push(
    Txt({ fg: T.border, height: 1 }, "\u2500".repeat(28)),
  );

  // ── C. DAG area ────────────────────────────────────────────────
  switch (st.connection) {
    case "connected": {
      // Placeholder DAG: 2-node, 1-edge demo
      const placeholderNodes: DagNode[] = [
        { id: "a", name: "M-A1.P1", status: "done" },
        { id: "b", name: "M-A1.P2", status: "running" },
        { id: "c", name: "M-A2.P1", status: "pending" },
      ];
      const placeholderEdges: DagEdge[] = [
        { from: "a", to: "b" },
      ];
      const dagString = renderDagBox(placeholderNodes, placeholderEdges);
      const dagLines = dagString.split("\n");
      children.push(
        Box(
          { flexDirection: "column", marginTop: 1 },
          ...dagLines.map((line) =>
            Txt({ fg: T.text, height: 1 }, line),
          ),
        ),
      );
      break;
    }
    case "disconnected":
      children.push(
        Box(
          { flexDirection: "column", marginTop: 4 },
          Txt(
            { fg: T.warning, attributes: ATTR_DIM, height: 1 },
            truncate(connectionStatusLine()),
          ),
        ),
      );
      break;
    case "unreachable":
      children.push(
        Box(
          { flexDirection: "column", marginTop: 4 },
          Txt(
            { fg: T.error, attributes: ATTR_BOLD, height: 1 },
            truncate("state-daemon not running"),
          ),
          Txt(
            { fg: T.text, attributes: ATTR_DIM, height: 1, marginTop: 1 },
            truncate("Run state-daemon start to"),
          ),
          Txt(
            { fg: T.text, attributes: ATTR_DIM, height: 1, marginTop: 1 },
            truncate("resume."),
          ),
        ),
      );
      break;
  }

  return Box({ flexDirection: "column" }, ...children);
}

/* ── Event wiring ──────────────────────────────────────────────── */

/**
 * setupBuildProgress — wires event subscriptions for daemon SSE events.
 *
 * Subscribes to `api.event.on("session.status")` and updates
 * BUILD_PROGRESS_STATE on each event. On first event received, sets
 * connection to "connected". Cleanup is registered via api.lifecycle.onDispose.
 */
export function setupBuildProgress(api: TuiPluginApi): void {
  const unsubStatus = api.event.on("session.status", (event: EventSessionStatus) => {
    BUILD_PROGRESS_STATE.sessionStatus = event.properties.status;
    BUILD_PROGRESS_STATE.sessionID = event.properties.sessionID;
    BUILD_PROGRESS_STATE.connection = "connected";
  });

  api.lifecycle.onDispose(() => {
    unsubStatus();
    // Reset state on dispose
    BUILD_PROGRESS_STATE.connection = "unreachable";
    BUILD_PROGRESS_STATE.sessionStatus = null;
    BUILD_PROGRESS_STATE.sessionID = null;
  });
}
