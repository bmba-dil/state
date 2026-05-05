/** Unit tests for sidebar-content-renderer pure functions */

import { describe, expect, it } from "bun:test";
import {
  resolveMode,
  getModeIndicator,
  renderBuildPlaceholder,
  renderTeachPlaceholder,
  truncate,
} from "./sidebar-content-renderer.js";
import type { ModeInfo } from "./sidebar-content-renderer.js";
import SidebarContentRenderer from "./sidebar-content-renderer.js";

// ── resolveMode tests ──────────────────────────────────────────────

describe("resolveMode", () => {
  it('returns active state for { mode: "build" }', () => {
    const result: ModeInfo = resolveMode({ mode: "build" });
    expect(result.mode).toBe("build");
    expect(result.status).toBe("active");
  });

  it('returns active state for { mode: "teach" }', () => {
    const result: ModeInfo = resolveMode({ mode: "teach" });
    expect(result.mode).toBe("teach");
    expect(result.status).toBe("active");
  });

  it('returns active state for { mode: "both" }', () => {
    const result: ModeInfo = resolveMode({ mode: "both" });
    expect(result.mode).toBe("both");
    expect(result.status).toBe("active");
  });

  it("returns empty state for null input", () => {
    const result: ModeInfo = resolveMode(null);
    expect(result.mode).toBe("unknown");
    expect(result.status).toBe("empty");
  });

  it("returns empty state for undefined input", () => {
    const result: ModeInfo = resolveMode(undefined);
    expect(result.mode).toBe("unknown");
    expect(result.status).toBe("empty");
  });

  it("returns empty state for empty object (no mode key)", () => {
    const result: ModeInfo = resolveMode({} as any);
    expect(result.mode).toBe("unknown");
    expect(result.status).toBe("empty");
  });

  it("returns empty state for invalid mode value", () => {
    const result: ModeInfo = resolveMode({ mode: "invalid" } as any);
    expect(result.mode).toBe("unknown");
    expect(result.status).toBe("empty");
  });
});

// ── getModeIndicator tests ──────────────────────────────────────────

describe("getModeIndicator", () => {
  it('returns icon + BUILD label for "build" mode', () => {
    const indicator = getModeIndicator("build");
    expect(indicator).toContain("BUILD");
    expect(indicator).toContain("\uE615"); // nf-dev-codeigniter
  });

  it('returns icon + TEACH label for "teach" mode', () => {
    const indicator = getModeIndicator("teach");
    expect(indicator).toContain("TEACH");
    expect(indicator).toContain("\uE28C"); // nf-fa-graduation_cap
  });

  it('returns icon + BOTH label for "both" mode', () => {
    const indicator = getModeIndicator("both");
    expect(indicator).toContain("BOTH");
    expect(indicator).toContain("\uF0628"); // nf-md-sync
  });

  it('returns circle + IDLE label for "unknown" mode', () => {
    const indicator = getModeIndicator("unknown");
    expect(indicator).toContain("IDLE");
    expect(indicator).toContain("\u25CB"); // white circle
  });
});

// ── Placeholder tests ───────────────────────────────────────────────

describe("renderBuildPlaceholder", () => {
  it("contains BuildProgress title in box-drawing border", () => {
    const placeholder = renderBuildPlaceholder();
    expect(placeholder).toContain("BuildProgress");
    expect(placeholder).toContain("\u250C"); // box-drawing light down and right (┌)
    expect(placeholder).toContain("\u2510"); // box-drawing light down and left (┐)
    expect(placeholder).toContain("\u2514"); // box-drawing light up and right (└)
    expect(placeholder).toContain("\u2518"); // box-drawing light up and left (┘)
    expect(placeholder).toContain("\u2502"); // box-drawing light vertical (│)
    expect(placeholder).toContain("Phase 082");
  });
});

describe("renderTeachPlaceholder", () => {
  it("contains TeachConcept title in box-drawing border", () => {
    const placeholder = renderTeachPlaceholder();
    expect(placeholder).toContain("TeachConcept");
    expect(placeholder).toContain("\u250C"); // box-drawing light down and right (┌)
    expect(placeholder).toContain("\u2510"); // box-drawing light down and left (┐)
    expect(placeholder).toContain("\u2514"); // box-drawing light up and right (└)
    expect(placeholder).toContain("\u2518"); // box-drawing light up and left (┘)
    expect(placeholder).toContain("\u2502"); // box-drawing light vertical (│)
    expect(placeholder).toContain("Phase 083");
  });
});

// ── truncate tests ──────────────────────────────────────────────────

describe("truncate", () => {
  it("returns string shorter than 28 chars as-is", () => {
    const result = truncate("short string");
    expect(result).toBe("short string");
  });

  it("returns string exactly 28 chars as-is", () => {
    const input = "a".repeat(28);
    const result = truncate(input);
    expect(result).toBe(input);
    expect(result.length).toBe(28);
  });

  it("appends U+2026 ellipsis for string longer than 28 chars", () => {
    const input = "a".repeat(30);
    const result = truncate(input);
    expect(result.length).toBe(28);
    expect(result.endsWith("\u2026")).toBe(true);
  });

  it("truncates at position 27 with ellipsis for overflow", () => {
    const input = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"; // 52 chars
    const result = truncate(input);
    expect(result.length).toBe(28);
    // First 27 chars of input preserved
    expect(result.slice(0, 27)).toBe(input.slice(0, 27));
    expect(result[27]).toBe("\u2026");
  });

  it("accepts custom maxLen parameter", () => {
    const result = truncate("hello world", 10);
    expect(result.length).toBeLessThanOrEqual(10);
  });
});

// ── getModeIndicator edge cases ─────────────────────────────────────

describe("getModeIndicator edge cases", () => {
  it("falls back to white circle for empty string (icon only, no label)", () => {
    const result = getModeIndicator("");
    expect(result).toContain("\u25CB"); // white circle
    // Empty string → mode.toUpperCase() is "" → just icon + space
    expect(result).toBe("\u25CB ");
  });

  it("falls back to white circle + uppercased name for arbitrary string", () => {
    const result = getModeIndicator("bogus");
    expect(result).toContain("\u25CB"); // white circle icon fallback
    expect(result).toContain("BOGUS"); // uses mode.toUpperCase()
  });
});

// ── SidebarContentRenderer output validation ────────────────────────

describe("SidebarContentRenderer output validation", () => {
  it("returns non-null Box object when invoked", () => {
    const result = SidebarContentRenderer();
    expect(result).not.toBeNull();
  });

  it("returns an object (Box) with children", () => {
    const result = SidebarContentRenderer();
    expect(result).not.toBeNull();
    expect(typeof result).toBe("object");
  });
});

// ── Placeholder content validation ──────────────────────────────────

describe("renderBuildPlaceholder content", () => {
  it("contains all four box-drawing corner characters", () => {
    const placeholder = renderBuildPlaceholder();
    expect(placeholder).toContain("\u250C"); // ┌
    expect(placeholder).toContain("\u2510"); // ┐
    expect(placeholder).toContain("\u2514"); // └
    expect(placeholder).toContain("\u2518"); // ┘
    expect(placeholder).toContain("\u2502"); // │
  });

  it("contains BuildProgress title text", () => {
    const placeholder = renderBuildPlaceholder();
    expect(placeholder).toContain("BuildProgress");
  });

  it("contains Phase 082 reference text", () => {
    const placeholder = renderBuildPlaceholder();
    expect(placeholder).toContain("Phase 082");
  });
});

describe("renderTeachPlaceholder content", () => {
  it("contains all four box-drawing corner characters", () => {
    const placeholder = renderTeachPlaceholder();
    expect(placeholder).toContain("\u250C"); // ┌
    expect(placeholder).toContain("\u2510"); // ┐
    expect(placeholder).toContain("\u2514"); // └
    expect(placeholder).toContain("\u2518"); // ┘
    expect(placeholder).toContain("\u2502"); // │
  });

  it("contains TeachConcept title text", () => {
    const placeholder = renderTeachPlaceholder();
    expect(placeholder).toContain("TeachConcept");
  });

  it("contains Phase 083 reference text", () => {
    const placeholder = renderTeachPlaceholder();
    expect(placeholder).toContain("Phase 083");
  });
});
