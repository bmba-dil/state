/** Unit tests for sidebar-content-renderer pure functions */

import { describe, expect, it } from "bun:test";
import {
  resolveMode,
  getModeIndicator,
  renderBuildPlaceholder,
  renderTeachPlaceholder,
} from "./sidebar-content-renderer.js";
import type { ModeInfo } from "./sidebar-content-renderer.js";

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
