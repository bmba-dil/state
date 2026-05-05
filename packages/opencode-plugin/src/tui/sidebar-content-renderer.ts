/**
 * sidebar-content-renderer — mode-aware renderer for the `sidebar_content` TUI slot.
 *
 * Reads `.state/mode.json` at render time and conditionally produces one of four
 * states: loading, empty, active, or error. Uses the @opentui/core constructs API
 * (Box, Text) to build renderable trees directly — no JSX required.
 *
 * Exports:
 *   - SidebarContentRenderer (default) — render function for the slot handler
 *   - resolveMode(raw) — pure function for mode resolution (testable)
 *   - ModeInfo — type for resolved mode info
 *   - getModeIndicator, renderBuildPlaceholder, renderTeachPlaceholder — test helpers
 */

import { Box, Text, createTextAttributes } from "@opentui/core";
import { readFileSync } from "node:fs";

/* ── Types ─────────────────────────────────────────────────────── */

export type ModeJson = { mode: "build" | "teach" | "both" };
export type ResolvedMode = "build" | "teach" | "both" | "unknown";
export type ModeStatus = "loading" | "empty" | "active" | "error";

export interface ModeInfo {
  mode: ResolvedMode;
  status: ModeStatus;
}

/* ── Theme colors (hardcoded fallback — matches theme.json exactly) */

const T = {
  accent: "#6366F1",
  success: "#10B981",
  info: "#3B82F6",
  textMuted: "#64748B",
  error: "#EF4444",
  text: "#E2E8F0",
  border: "#334155",
} as const;

/* ── Text attributes (pre-computed for performance) ─────────────── */

const ATTR_BOLD = createTextAttributes({ bold: true });
const ATTR_DIM = createTextAttributes({ dim: true });

/* ── Mode icons (Nerd Font glyphs) ──────────────────────────────── */

const ICONS: Record<string, string> = {
  build: "\uE615",   // nf-dev-codeigniter
  teach: "\uE28C",   // nf-fa-graduation_cap
  both: "\uF0628",   // nf-md-sync
  unknown: "\u25CB", // white circle
};

const COLORS: Record<string, string> = {
  build: T.accent,
  teach: T.success,
  both: T.info,
  unknown: T.textMuted,
};

/* ── Utilities ──────────────────────────────────────────────────── */

/** Truncate text to `maxLen` characters, appending U+2026 ellipsis if needed. */
function truncate(text: string, maxLen = 28): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "\u2026";
}

/** Build a 28-cell-wide box-drawing placeholder with a title and body. */
function buildPlaceholderBox(title: string, body: string): string {
  const W = 28;
  const innerW = W - 2;
  const topFill = innerW - 3 - title.length;
  const top = `\u250C\u2500 ${title} ${"\u2500".repeat(Math.max(0, topFill))}\u2510`;
  const bodyText = truncate(body, innerW - 2);
  const bodyPad = innerW - 2 - bodyText.length;
  const middle = `\u2502 ${bodyText}${" ".repeat(Math.max(0, bodyPad))} \u2502`;
  const bottom = `\u2514${"\u2500".repeat(innerW)}\u2518`;
  return [top, middle, bottom].join("\n");
}

/* ── Helper: create a Text element with content ──────────────────── */

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

/* ── Exported pure functions (testable) ─────────────────────────── */

/**
 * Resolve a ModeJson value to a ModeInfo with status.
 * Validates mode field strictly — unknown values map to "unknown" (T-081-01).
 */
export function resolveMode(raw: ModeJson | null | undefined): ModeInfo {
  if (raw === null || raw === undefined) {
    return { mode: "unknown", status: "empty" };
  }
  const mode = (raw as Record<string, unknown>).mode;
  if (mode === "build" || mode === "teach" || mode === "both") {
    return { mode, status: "active" };
  }
  return { mode: "unknown", status: "empty" };
}

/** Returns the mode indicator string: "{icon} {UPPERCASE_LABEL}". */
export function getModeIndicator(mode: string): string {
  const icon = ICONS[mode] || ICONS.unknown;
  const label = mode === "unknown" ? "IDLE" : mode.toUpperCase();
  return `${icon} ${label}`;
}

/** Returns a 28-cell-wide box-drawing placeholder for BuildProgress. */
export function renderBuildPlaceholder(): string {
  return buildPlaceholderBox("BuildProgress", "(Phase 082 will render here)");
}

/** Returns a 28-cell-wide box-drawing placeholder for TeachConcept. */
export function renderTeachPlaceholder(): string {
  return buildPlaceholderBox("TeachConcept", "(Phase 083 will render here)");
}

/* ── Sync mode reader ──────────────────────────────────────────── */

/**
 * Read .state/mode.json synchronously and resolve to ModeInfo.
 * File is small (<100 bytes) and always local — sync read is appropriate.
 */
function readModeSync(): ModeInfo {
  try {
    const content = readFileSync(".state/mode.json", "utf-8");
    const json = JSON.parse(content) as ModeJson;
    return resolveMode(json);
  } catch {
    return { mode: "unknown", status: "error" };
  }
}

/* ── Component ──────────────────────────────────────────────────── */

/**
 * SidebarContentRenderer — mode-aware sidebar_content slot renderer.
 *
 * Reads `.state/mode.json` and produces a renderable tree with:
 *   1. Mode indicator row (icon + uppercase label)
 *   2. Divider (28 ─ characters)
 *   3. Content area (loading / empty / active / error)
 *
 * Uses @opentui/core constructs API for Text/Box renderables.
 */
export default function SidebarContentRenderer(
  _ctx?: unknown,
  _props?: unknown,
): ReturnType<typeof Box> {
  const info = readModeSync();
  const color = COLORS[info.mode] || COLORS.unknown;

  return Box(
    { flexDirection: "column" },
    // ── Mode indicator row ──────────────────────────────────
    Box(
      { flexDirection: "row", height: 1 },
      Txt({ fg: color, height: 1 }, ICONS[info.mode] || ICONS.unknown),
      Txt({ height: 1 }, " "),
      Txt(
        { fg: color, height: 1, attributes: ATTR_BOLD },
        info.mode === "unknown" ? "IDLE" : info.mode.toUpperCase(),
      ),
    ),
    // ── Divider ─────────────────────────────────────────────
    Txt({ fg: T.border, height: 1 }, "\u2500".repeat(28)),
    // ── Content area ────────────────────────────────────────
    renderContent(info),
  );
}

/* ── Content renderers ──────────────────────────────────────────── */

/** Render the appropriate content sub-tree based on mode status. */
function renderContent(
  info: ModeInfo,
): ReturnType<typeof Text> | ReturnType<typeof Box> {
  const { status, mode } = info;

  if (status === "loading") {
    return Box(
      { flexDirection: "column", marginTop: 4 },
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM, height: 1 },
        truncate("Reading mode\u2026"),
      ),
    );
  }

  if (status === "error") {
    return Box(
      { flexDirection: "column", marginTop: 4 },
      Txt(
        { fg: T.error, attributes: ATTR_BOLD, height: 1 },
        truncate("Cannot read mode configuration"),
      ),
      Txt(
        { fg: T.text, height: 1, marginTop: 1 },
        truncate("state-daemon may not be running."),
      ),
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM, height: 1, marginTop: 1 },
        truncate("Run state-daemon start to resume."),
      ),
    );
  }

  if (status === "empty") {
    return renderEmptyState(mode);
  }

  // active
  return renderActiveState(mode);
}

/** Render the empty state: mode-appropriate messaging. */
function renderEmptyState(mode: ResolvedMode): ReturnType<typeof Box> {
  const items: ReturnType<typeof Text>[] = [];

  if (mode === "build") {
    items.push(
      Txt({ fg: T.textMuted, height: 1 }, truncate("No active build session.")),
    );
    items.push(
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM, height: 1, marginTop: 1 },
        truncate("Run /gsd:execute-phase to begin."),
      ),
    );
  } else if (mode === "teach") {
    items.push(
      Txt({ fg: T.textMuted, height: 1 }, truncate("No active concept.")),
    );
    items.push(
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM, height: 1, marginTop: 1 },
        truncate("Select a subject to begin learning."),
      ),
    );
  } else if (mode === "both") {
    items.push(
      Txt({ fg: T.textMuted, height: 1 }, truncate("No active build session.")),
    );
    items.push(
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM, height: 1, marginTop: 1 },
        truncate("Run /gsd:execute-phase to begin."),
      ),
    );
    items.push(
      Txt(
        { fg: T.textMuted, height: 1, marginTop: 2 },
        truncate("No active concept."),
      ),
    );
    items.push(
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM, height: 1, marginTop: 1 },
        truncate("Select a subject to begin learning."),
      ),
    );
  } else {
    items.push(
      Txt({ fg: T.textMuted, height: 1 }, truncate("Mode not configured.")),
    );
  }

  return Box({ flexDirection: "column", marginTop: 4 }, ...items);
}

/** Render the active state: placeholder boxes for downstream phases. */
function renderActiveState(mode: ResolvedMode): ReturnType<typeof Box> {
  if (mode === "build") {
    return placeholderBox(renderBuildPlaceholder());
  }
  if (mode === "teach") {
    return placeholderBox(renderTeachPlaceholder());
  }
  // both: both placeholders stacked
  return Box(
    { flexDirection: "column", marginTop: 4 },
    placeholderBox(renderBuildPlaceholder()),
    Box({ marginTop: 1 }, placeholderBox(renderTeachPlaceholder())),
  );
}

/** Convert a multi-line placeholder string into a vertical Box of Text elements. */
function placeholderBox(text: string): ReturnType<typeof Box> {
  const lines = text.split("\n");
  return Box(
    { flexDirection: "column", marginTop: 4 },
    ...lines.map((line) =>
      Txt({ fg: T.textMuted, attributes: ATTR_DIM, height: 1 }, line),
    ),
  );
}
