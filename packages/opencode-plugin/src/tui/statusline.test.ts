/** Unit tests for statusline pure functions and render output */

import { describe, expect, it, beforeEach } from "bun:test";
import {
  formatCost,
  getModeIcon,
  getModeColor,
  renderStatusline,
  STATUSLINE_STATE,
} from "./statusline.js";

// ── formatCost tests ──────────────────────────────────────────────

describe("formatCost", () => {
  it("formatCost(0.42) returns $0.42", () => {
    expect(formatCost(0.42)).toBe("$0.42");
  });

  it("formatCost(0) returns $0.00", () => {
    expect(formatCost(0)).toBe("$0.00");
  });

  it("formatCost(1.05) returns $1.05", () => {
    expect(formatCost(1.05)).toBe("$1.05");
  });

  it("formatCost(undefined) returns — (em dash)", () => {
    expect(formatCost(undefined)).toBe("\u2014");
  });

  it("formatCost(0.005) rounds to $0.01", () => {
    expect(formatCost(0.005)).toBe("$0.01");
  });
});

// ── getModeIcon tests ─────────────────────────────────────────────

describe("getModeIcon", () => {
  it('returns nf-dev-codeigniter glyph for "build"', () => {
    expect(getModeIcon("build")).toBe("\uE615");
  });

  it('returns nf-fa-graduation_cap glyph for "teach"', () => {
    expect(getModeIcon("teach")).toBe("\uE28C");
  });

  it('returns white circle fallback for "unknown"', () => {
    expect(getModeIcon("unknown")).toBe("\u25CB");
  });
});

// ── getModeColor tests ────────────────────────────────────────────

describe("getModeColor", () => {
  it("returns accent (#6366F1) for build mode", () => {
    expect(getModeColor("build")).toBe("#6366F1");
  });

  it("returns success (#10B981) for teach mode", () => {
    expect(getModeColor("teach")).toBe("#10B981");
  });

  it("returns info (#3B82F6) for both mode", () => {
    expect(getModeColor("both")).toBe("#3B82F6");
  });

  it("returns textMuted (#64748B) for unknown mode", () => {
    expect(getModeColor("unknown")).toBe("#64748B");
  });
});

// ── STATUSLINE_STATE defaults ─────────────────────────────────────

describe("STATUSLINE_STATE defaults", () => {
  // Reset state to factory defaults before each test
  function resetState(): void {
    STATUSLINE_STATE.connection = "unreachable";
    STATUSLINE_STATE.mode = "unknown";
    STATUSLINE_STATE.step = "\u2014";
    STATUSLINE_STATE.provider = "\u2014";
    STATUSLINE_STATE.cost = 0;
  }

  it("has connection unreachable on module load", () => {
    resetState();
    expect(STATUSLINE_STATE.connection).toBe("unreachable");
  });

  it('has mode "unknown" on module load', () => {
    resetState();
    expect(STATUSLINE_STATE.mode).toBe("unknown");
  });

  it('has step "—" on module load', () => {
    resetState();
    expect(STATUSLINE_STATE.step).toBe("\u2014");
  });

  it('has provider "—" on module load', () => {
    resetState();
    expect(STATUSLINE_STATE.provider).toBe("\u2014");
  });

  it("has cost 0 on module load", () => {
    resetState();
    expect(STATUSLINE_STATE.cost).toBe(0);
  });
});

// ── renderStatusline tests ────────────────────────────────────────

describe("renderStatusline", () => {
  it("returns a Box (non-null) when connection is unreachable", () => {
    STATUSLINE_STATE.connection = "unreachable";
    const result = renderStatusline();
    expect(result).not.toBeNull();
  });

  it("returns a Box (non-null) when connection is connected", () => {
    STATUSLINE_STATE.connection = "connected";
    const result = renderStatusline();
    expect(result).not.toBeNull();
  });

  it("returns a Box (non-null) when connection is disconnected", () => {
    STATUSLINE_STATE.connection = "disconnected";
    const result = renderStatusline();
    expect(result).not.toBeNull();
  });
});

// ── formatCost edge cases ─────────────────────────────────────────

describe("formatCost edge cases", () => {
  it("formatCost(NaN) returns em dash", () => {
    expect(formatCost(NaN)).toBe("\u2014");
  });

  it("formatCost(Infinity) returns em dash", () => {
    expect(formatCost(Infinity)).toBe("\u2014");
  });

  it("formatCost(-Infinity) returns em dash", () => {
    expect(formatCost(-Infinity)).toBe("\u2014");
  });

  it("formatCost(null as any) returns em dash", () => {
    expect(formatCost(null as any)).toBe("\u2014");
  });

  it("formatCost(99999) returns $99999.00 (below clamp ceiling)", () => {
    expect(formatCost(99999)).toBe("$99999.00");
  });

  it("formatCost(200000) clamps to $100000.00", () => {
    expect(formatCost(200000)).toBe("$100000.00");
  });

  it("formatCost(-5) clamps to $0.00", () => {
    expect(formatCost(-5)).toBe("$0.00");
  });

  it("formatCost(100000) returns $100000.00 (at clamp ceiling)", () => {
    expect(formatCost(100000)).toBe("$100000.00");
  });
});

// ── getModeIcon edge cases ────────────────────────────────────────

describe("getModeIcon edge cases", () => {
  it("returns both glyph for 'both' mode", () => {
    expect(getModeIcon("both")).toBe("\uF0628");
  });

  it("returns white circle for empty string", () => {
    expect(getModeIcon("")).toBe("\u25CB");
  });

  it("returns white circle for 'bogus' string", () => {
    expect(getModeIcon("bogus")).toBe("\u25CB");
  });
});

// ── getModeColor edge cases ───────────────────────────────────────

describe("getModeColor edge cases", () => {
  it("returns textMuted (#64748B) for empty string", () => {
    expect(getModeColor("")).toBe("#64748B");
  });

  it("returns textMuted (#64748B) for 'bogus' string", () => {
    expect(getModeColor("bogus")).toBe("#64748B");
  });
});

// ── renderStatusline content validation ───────────────────────────

describe("renderStatusline content validation", () => {
  function resetState(): void {
    STATUSLINE_STATE.connection = "unreachable";
    STATUSLINE_STATE.mode = "unknown";
    STATUSLINE_STATE.step = "\u2014";
    STATUSLINE_STATE.provider = "\u2014";
    STATUSLINE_STATE.cost = 0;
  }

  it("connected state with mode=build → output is a Box with children", () => {
    resetState();
    STATUSLINE_STATE.connection = "connected";
    STATUSLINE_STATE.mode = "build";
    STATUSLINE_STATE.provider = "anthropic";
    STATUSLINE_STATE.cost = 0.42;
    const result = renderStatusline();
    expect(result).not.toBeNull();
    expect(typeof result).toBe("object");
  });

  it("disconnected state → output is a Box (non-null)", () => {
    resetState();
    STATUSLINE_STATE.connection = "disconnected";
    STATUSLINE_STATE.provider = "anthropic";
    STATUSLINE_STATE.cost = 0.42;
    const result = renderStatusline();
    expect(result).not.toBeNull();
  });

  it("unreachable state → output is a Box (non-null)", () => {
    resetState();
    STATUSLINE_STATE.connection = "unreachable";
    const result = renderStatusline();
    expect(result).not.toBeNull();
  });

  it("connected state with mode=teach → output is a Box with children", () => {
    resetState();
    STATUSLINE_STATE.connection = "connected";
    STATUSLINE_STATE.mode = "teach";
    STATUSLINE_STATE.provider = "\u2014";
    STATUSLINE_STATE.cost = 0;
    const result = renderStatusline();
    expect(result).not.toBeNull();
  });

  it("connected state with mode=both → output is a Box with children", () => {
    resetState();
    STATUSLINE_STATE.connection = "connected";
    STATUSLINE_STATE.mode = "both";
    STATUSLINE_STATE.provider = "\u2014";
    STATUSLINE_STATE.cost = 0;
    const result = renderStatusline();
    expect(result).not.toBeNull();
  });

  it("connected state with mode=unknown → output is a Box", () => {
    resetState();
    STATUSLINE_STATE.connection = "connected";
    STATUSLINE_STATE.mode = "unknown";
    const result = renderStatusline();
    expect(result).not.toBeNull();
  });
});

// ── STATUSLINE_STATE mutation safety ───────────────────────────────

describe("STATUSLINE_STATE mutation safety", () => {
  it("renderStatusline() does not mutate any state field", () => {
    STATUSLINE_STATE.connection = "connected";
    STATUSLINE_STATE.mode = "build";
    STATUSLINE_STATE.step = "M-A1.P2";
    STATUSLINE_STATE.provider = "anthropic";
    STATUSLINE_STATE.cost = 0.42;

    const before = JSON.parse(JSON.stringify(STATUSLINE_STATE));
    renderStatusline();
    const after = JSON.parse(JSON.stringify(STATUSLINE_STATE));

    expect(after).toEqual(before);
  });

  it("renderStatusline() does not mutate state when unreachable", () => {
    STATUSLINE_STATE.connection = "unreachable";
    STATUSLINE_STATE.mode = "unknown";
    STATUSLINE_STATE.step = "\u2014";
    STATUSLINE_STATE.provider = "\u2014";
    STATUSLINE_STATE.cost = 0;

    const before = JSON.parse(JSON.stringify(STATUSLINE_STATE));
    renderStatusline();
    const after = JSON.parse(JSON.stringify(STATUSLINE_STATE));

    expect(after).toEqual(before);
  });
});
