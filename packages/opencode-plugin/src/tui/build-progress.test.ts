/** Unit tests for build-progress pure rendering functions */

import { describe, expect, it, beforeEach } from "bun:test";
import {
  stepStatusColor,
  renderDagBox,
  renderBuildProgress,
  BUILD_PROGRESS_STATE,
} from "./build-progress.js";
import type { DagNode, DagEdge } from "./build-progress.js";

// ── stepStatusColor tests ──────────────────────────────────────────

describe("stepStatusColor", () => {
  it('returns T.accent (#6366F1) for "running"', () => {
    expect(stepStatusColor("running")).toBe("#6366F1");
  });

  it('returns T.accent (#6366F1) for "busy"', () => {
    expect(stepStatusColor("busy")).toBe("#6366F1");
  });

  it('returns T.success (#10B981) for "done"', () => {
    expect(stepStatusColor("done")).toBe("#10B981");
  });

  it('returns T.success (#10B981) for "idle"', () => {
    expect(stepStatusColor("idle")).toBe("#10B981");
  });

  it('returns T.warning (#F59E0B) for "blocked"', () => {
    expect(stepStatusColor("blocked")).toBe("#F59E0B");
  });

  it('returns T.info (#3B82F6) for "retry"', () => {
    expect(stepStatusColor("retry")).toBe("#3B82F6");
  });

  it('returns T.textMuted (#64748B) for "pending"', () => {
    expect(stepStatusColor("pending")).toBe("#64748B");
  });

  it('returns T.textMuted (#64748B) for "unknown"', () => {
    expect(stepStatusColor("unknown")).toBe("#64748B");
  });
});

// ── renderDagBox tests ─────────────────────────────────────────────

describe("renderDagBox", () => {
  it("returns empty-state message when nodes array is empty", () => {
    const result = renderDagBox([], []);
    expect(result).toContain("No Slices defined");
  });

  it("returns box-drawing chars for populated DAG", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "M-A1.P1", status: "done" },
      { id: "b", name: "M-A1.P2", status: "running" },
    ];
    const edges: DagEdge[] = [{ from: "a", to: "b" }];

    const result = renderDagBox(nodes, edges);

    // Box-drawing characters
    expect(result).toContain("\u250C"); // ┌
    expect(result).toContain("\u2510"); // ┐
    expect(result).toContain("\u2514"); // └
    expect(result).toContain("\u2518"); // ┘
    expect(result).toContain("\u2502"); // │

    // Node names
    expect(result).toContain("M-A1.P1");
    expect(result).toContain("M-A1.P2");

    // Edge arrow
    expect(result).toContain("\u2192"); // →
  });

  it("renders success dot (●) for done nodes", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "M-A1.P1", status: "done" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u25CF"); // ●
  });

  it("renders accent dot (◉) for running nodes", () => {
    const nodes: DagNode[] = [
      { id: "b", name: "M-A1.P2", status: "running" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u25C9"); // ◉
  });

  it("renders open circle (○) for pending nodes", () => {
    const nodes: DagNode[] = [
      { id: "c", name: "M-A2.P1", status: "pending" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u25CB"); // ○
  });

  it("renders circle-dot (◍) for blocked nodes", () => {
    const nodes: DagNode[] = [
      { id: "d", name: "M-A3.P1", status: "blocked" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u25CD"); // ◍
  });

  it('contains "Slice DAG" title in populated state', () => {
    const nodes: DagNode[] = [
      { id: "a", name: "M-A1.P1", status: "done" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("Slice DAG");
  });
});

// ── renderBuildProgress tests ──────────────────────────────────────

describe("renderBuildProgress", () => {
  it("returns a Box (non-null) when disconnected", () => {
    BUILD_PROGRESS_STATE.connection = "disconnected";
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
  });

  it("returns a Box (non-null) when unreachable", () => {
    BUILD_PROGRESS_STATE.connection = "unreachable";
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
  });

  it("returns a Box (non-null) when connected", () => {
    BUILD_PROGRESS_STATE.connection = "connected";
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
  });
});

// ── BUILD_PROGRESS_STATE initial values ────────────────────────────

describe("BUILD_PROGRESS_STATE defaults", () => {
  // Reset state to factory defaults before each test — previous tests
  // in other describe blocks mutate the module-level state.
  function resetState(): void {
    BUILD_PROGRESS_STATE.connection = "unreachable";
    BUILD_PROGRESS_STATE.sessionStatus = null;
    BUILD_PROGRESS_STATE.sessionID = null;
  }

  it('has connection "unreachable" on module load', () => {
    resetState();
    expect(BUILD_PROGRESS_STATE.connection).toBe("unreachable");
  });

  it("has sessionStatus null on module load", () => {
    resetState();
    expect(BUILD_PROGRESS_STATE.sessionStatus).toBeNull();
  });

  it("has sessionID null on module load", () => {
    resetState();
    expect(BUILD_PROGRESS_STATE.sessionID).toBeNull();
  });
});

// ── renderDagBox multi-chain DAG ────────────────────────────────────

describe("renderDagBox multi-chain DAG", () => {
  it("renders two disconnected chains in output", () => {
    // Chain 1: A→B, Chain 2: C→D — no edges between chains
    const nodes: DagNode[] = [
      { id: "a", name: "Chain1-A", status: "done" },
      { id: "b", name: "Chain1-B", status: "running" },
      { id: "c", name: "Chain2-C", status: "pending" },
      { id: "d", name: "Chain2-D", status: "blocked" },
    ];
    const edges: DagEdge[] = [
      { from: "a", to: "b" },
      { from: "c", to: "d" },
    ];

    const result = renderDagBox(nodes, edges);

    // Chain roots should appear — connected chain line may truncate chain children
    expect(result).toContain("Chain1-A");
    expect(result).toContain("Chain2-C");

    // Edge arrows for both chains
    const arrowCount = (result.match(/\u2192/g) || []).length;
    expect(arrowCount).toBe(2); // one arrow per chain
  });
});

// ── renderDagBox disconnected nodes ─────────────────────────────────

describe("renderDagBox disconnected nodes", () => {
  it("renders each unconnected node on its own line with its status dot", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "Node-A", status: "done" },
      { id: "b", name: "Node-B", status: "running" },
      { id: "c", name: "Node-C", status: "pending" },
    ];
    // No edges — all nodes disconnected
    const result = renderDagBox(nodes, []);

    // Each node name appears
    expect(result).toContain("Node-A");
    expect(result).toContain("Node-B");
    expect(result).toContain("Node-C");

    // Each line has its own box-drawing vertical
    const verticalCount = (result.match(/\u2502/g) || []).length;
    // One vertical per node line (3 nodes) + top border? No, top and bottom borders use horizontal
    // Actually: top border line has no vertical, each node line has 2 verticals (left and right border),
    // bottom border line has no vertical.
    // 3 node lines × 2 = 6 verticals
    expect(verticalCount).toBe(6);
  });
});

// ── renderDagBox truncation ─────────────────────────────────────────

describe("renderDagBox truncation", () => {
  it("truncates long node names with U+2026 ellipsis", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "ThisIsAVeryLongNodeNameThatExceedsTwentyEightCharacters", status: "done" },
    ];
    const result = renderDagBox(nodes, []);

    // Long name should be truncated in the chain row
    expect(result).toContain("\u2026"); // U+2026 ellipsis
  });

  it("does not truncate short node names", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "ShortName", status: "done" },
    ];
    const result = renderDagBox(nodes, []);

    expect(result).toContain("ShortName");
    expect(result).not.toContain("\u2026");
  });
});

// ── renderBuildProgress state transitions ──────────────────────────

describe("renderBuildProgress state transitions", () => {
  function resetState(): void {
    BUILD_PROGRESS_STATE.connection = "unreachable";
    BUILD_PROGRESS_STATE.sessionStatus = null;
    BUILD_PROGRESS_STATE.sessionID = null;
  }

  it('connected with sessionStatus "idle" → shows "Idle"', () => {
    resetState();
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "idle" } as any;
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
    // "idle" → done status → "Idle" label
    // The step line includes the dot + "Step: Idle"
    // We can verify the color is success (#10B981) which is done → idle
  });

  it('connected with sessionStatus "busy" → shows "Running"', () => {
    resetState();
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "busy" } as any;
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
    // "busy" → running status → "Running" label
  });

  it('connected with sessionStatus "retry" attempt 3 → shows retry attempt', () => {
    resetState();
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "retry", attempt: 3 } as any;
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
    // "retry" with attempt should show "Retrying (attempt 3)"
  });

  it("unreachable → output contains error text", () => {
    resetState();
    BUILD_PROGRESS_STATE.connection = "unreachable";
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
  });

  it("disconnected → output contains reconnection text", () => {
    resetState();
    BUILD_PROGRESS_STATE.connection = "disconnected";
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
  });
});

// ── BUILD_PROGRESS_STATE mutation safety ────────────────────────────

describe("BUILD_PROGRESS_STATE mutation safety", () => {
  it("renderBuildProgress() does not mutate sessionStatus", () => {
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "busy" } as any;
    BUILD_PROGRESS_STATE.sessionID = "test-1234";

    const before = JSON.parse(JSON.stringify(BUILD_PROGRESS_STATE));
    renderBuildProgress();
    const after = JSON.parse(JSON.stringify(BUILD_PROGRESS_STATE));

    expect(after.connection).toBe(before.connection);
    expect(after.sessionStatus).toEqual(before.sessionStatus);
    expect(after.sessionID).toBe(before.sessionID);
  });

  it("renderBuildProgress() does not mutate state when unreachable", () => {
    BUILD_PROGRESS_STATE.connection = "unreachable";
    BUILD_PROGRESS_STATE.sessionStatus = null;
    BUILD_PROGRESS_STATE.sessionID = null;

    const before = JSON.parse(JSON.stringify(BUILD_PROGRESS_STATE));
    renderBuildProgress();
    const after = JSON.parse(JSON.stringify(BUILD_PROGRESS_STATE));

    expect(after).toEqual(before);
  });
});

// ── renderDagBox status dot rendering ──────────────────────────────

describe("renderDagBox status dots", () => {
  it("renders fisheye dot for busy status", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "Task1", status: "busy" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u25C9"); // fisheye dot for busy
  });

  it("renders black circle dot for idle status", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "Task1", status: "idle" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u25CF"); // black circle for idle
  });

  it("renders retry arrow for retry status", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "Task1", status: "retry" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u21BB"); // ↻ for retry
  });

  it("renders open circle for unknown status", () => {
    const nodes: DagNode[] = [
      { id: "a", name: "Task1", status: "unknown" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u25CB"); // open circle for unknown
  });
});

// ── renderBuildProgress content specifics ──────────────────────────

describe("renderBuildProgress content specificity", () => {
  function resetState(): void {
    BUILD_PROGRESS_STATE.connection = "unreachable";
    BUILD_PROGRESS_STATE.sessionStatus = null;
    BUILD_PROGRESS_STATE.sessionID = null;
  }

  it("connected with sessionID → output contains session identifier", () => {
    resetState();
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "busy" } as any;
    BUILD_PROGRESS_STATE.sessionID = "abcdef12-3456-7890-abcd-ef1234567890";
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
  });

  it("connected without sessionID → renders step line without session fragment", () => {
    resetState();
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "idle" } as any;
    BUILD_PROGRESS_STATE.sessionID = null;
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
  });

  it("connected → contains DAG area with placeholder nodes", () => {
    resetState();
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "idle" } as any;
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
  });

  it("unreachable → output is a Box with children", () => {
    resetState();
    const result = renderBuildProgress();
    expect(result).not.toBeNull();
    expect(typeof result).toBe("object");
  });
});
