/** Unit tests for status-palette shared module */

import { describe, expect, it } from "bun:test";
import {
  statusColor,
  statusChar,
  statusLabel,
  STATUS_COLORS,
  STATUS_CHARS,
  STATUS_LABELS,
  stepStatusColor,
  type StepStatus,
} from "./status-palette.js";

// ── statusColor tests ────────────────────────────────────────────

describe("statusColor", () => {
  it('returns T.accent (#6366F1) for "running"', () => {
    expect(statusColor("running")).toBe("#6366F1");
  });

  it('returns T.success (#10B981) for "done"', () => {
    expect(statusColor("done")).toBe("#10B981");
  });

  it('returns T.error (#EF4444) for "failed"', () => {
    expect(statusColor("failed")).toBe("#EF4444");
  });

  it('returns T.warning (#F59E0B) for "blocked"', () => {
    expect(statusColor("blocked")).toBe("#F59E0B");
  });

  it('returns T.info (#3B82F6) for "retry"', () => {
    expect(statusColor("retry")).toBe("#3B82F6");
  });

  it('returns T.textMuted (#64748B) for "pending"', () => {
    expect(statusColor("pending")).toBe("#64748B");
  });

  it('returns T.textMuted (#64748B) for "unknown"', () => {
    expect(statusColor("unknown")).toBe("#64748B");
  });

  it("stepStatusColor is alias for statusColor", () => {
    expect(stepStatusColor).toBe(statusColor);
  });
});

// ── statusChar tests ─────────────────────────────────────────────

describe("statusChar", () => {
  it('returns ○ for "pending"', () => {
    expect(statusChar("pending")).toBe("\u25CB");
  });

  it('returns ◉ for "running"', () => {
    expect(statusChar("running")).toBe("\u25C9");
  });

  it('returns ● for "done"', () => {
    expect(statusChar("done")).toBe("\u25CF");
  });

  it('returns ✗ for "failed"', () => {
    expect(statusChar("failed")).toBe("\u2717");
  });

  it('returns ◍ for "blocked"', () => {
    expect(statusChar("blocked")).toBe("\u25CD");
  });

  it('returns ↻ for "retry"', () => {
    expect(statusChar("retry")).toBe("\u21BB");
  });

  it('returns ○ for "unknown"', () => {
    expect(statusChar("unknown")).toBe("\u25CB");
  });

  it('"idle" maps to ● (same as done)', () => {
    expect(statusChar("idle")).toBe("\u25CF");
  });

  it('"busy" maps to ◉ (same as running)', () => {
    expect(statusChar("busy")).toBe("\u25C9");
  });

  it("falls back to unknown dot for unrecognized status", () => {
    expect(statusChar("nonexistent")).toBe(STATUS_CHARS.unknown);
  });
});

// ── statusLabel tests ────────────────────────────────────────────

describe("statusLabel", () => {
  it('returns "Pending" for "pending"', () => {
    expect(statusLabel("pending")).toBe("Pending");
  });

  it('returns "In Progress" for "running"', () => {
    expect(statusLabel("running")).toBe("In Progress");
  });

  it('returns "Done" for "done"', () => {
    expect(statusLabel("done")).toBe("Done");
  });

  it('returns "Failed" for "failed"', () => {
    expect(statusLabel("failed")).toBe("Failed");
  });

  it('returns "Blocked" for "blocked"', () => {
    expect(statusLabel("blocked")).toBe("Blocked");
  });

  it('returns "Retrying" for "retry"', () => {
    expect(statusLabel("retry")).toBe("Retrying");
  });

  it('returns "Unknown" for "unknown"', () => {
    expect(statusLabel("unknown")).toBe("Unknown");
  });

  it('returns "Done" for "idle"', () => {
    expect(statusLabel("idle")).toBe("Done");
  });

  it('returns "In Progress" for "busy"', () => {
    expect(statusLabel("busy")).toBe("In Progress");
  });

  it("falls back to Unknown for unrecognized status", () => {
    expect(statusLabel("nonexistent")).toBe("Unknown");
  });
});

// ── Theme color verification ─────────────────────────────────────

describe("theme color consistency", () => {
  it("all defined statuses have a color", () => {
    const all: StepStatus[] = [
      "pending",
      "running",
      "done",
      "failed",
      "blocked",
      "retry",
      "unknown",
    ];
    for (const s of all) {
      expect(STATUS_COLORS[s]).toBeDefined();
      expect(STATUS_COLORS[s]).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
  });

  it("all defined statuses have a char", () => {
    const all: StepStatus[] = [
      "pending",
      "running",
      "done",
      "failed",
      "blocked",
      "retry",
      "unknown",
    ];
    for (const s of all) {
      expect(STATUS_CHARS[s]).toBeDefined();
      expect(STATUS_CHARS[s].length).toBeGreaterThanOrEqual(1);
    }
  });

  it("all defined statuses have a label", () => {
    const all: StepStatus[] = [
      "pending",
      "running",
      "done",
      "failed",
      "blocked",
      "retry",
      "unknown",
    ];
    for (const s of all) {
      expect(STATUS_LABELS[s]).toBeDefined();
      expect(STATUS_LABELS[s].length).toBeGreaterThan(0);
    }
  });
});
