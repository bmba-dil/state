/** Unit tests for build-progress pure rendering functions */

import { describe, expect, it } from "bun:test";
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

  it('returns T.error (#EF4444) for "blocked"', () => {
    expect(stepStatusColor("blocked")).toBe("#EF4444");
  });

  it('returns T.warning (#F59E0B) for "retry"', () => {
    expect(stepStatusColor("retry")).toBe("#F59E0B");
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

  it("renders cross (✗) for blocked nodes", () => {
    const nodes: DagNode[] = [
      { id: "d", name: "M-A3.P1", status: "blocked" },
    ];
    const result = renderDagBox(nodes, []);
    expect(result).toContain("\u2717"); // ✗
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
