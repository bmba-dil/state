/**
 * statusline — one-line statusline component for `sidebar_footer` and `home_footer` TUI slots.
 *
 * Shows: mode icon · scope · provider name · session cost on one line.
 * Subscribes to daemon SSE events via opencode's `api.event` bus for cost, provider,
 * and session status updates. Updates module-level state on each event and renders
 * synchronously on every frame using @opentui/core constructs API (Box, Text).
 *
 * Uses module-level mutable state (consistent with build-progress.ts pattern).
 * State is updated by event handlers; renderStatusline() reads current state
 * synchronously on every render frame.
 *
 * Note: The opencode SDK does not have a standalone `session.cost` event.
 * Cost data arrives via `session.next.step.ended` (properties.cost).
 * Provider data arrives via `session.next.model.switched` (properties.providerID).
 *
 * Exports:
 *   - setupStatusline(api) — wires event subscriptions, registers cleanup
 *   - renderStatusline() — returns renderable Box tree for current state
 *   - STATUSLINE_STATE — exported const object for test inspection
 *   - formatCost(amount) — pure function: formats USD cost
 *   - getModeIcon(mode) — pure function: maps mode string to Nerd Font glyph
 *   - getModeColor(mode) — pure function: maps mode to hex color
 */

import { Box, Text, createTextAttributes } from "@opentui/core";
import { readFileSync } from "node:fs";
import type { TuiPluginApi } from "@opencode-ai/plugin/tui";
import type {
  EventSessionStatus,
  EventSessionNextStepEnded,
  EventSessionNextModelSwitched,
} from "@opencode-ai/sdk/v2";
import { log } from "../logger.js";

/* ── Types ─────────────────────────────────────────────────────── */

export type ConnectionStatus = "connected" | "disconnected" | "unreachable";

export interface StatuslineState {
  connection: ConnectionStatus;
  mode: string; // "build" | "teach" | "both" | "unknown"
  step: string; // e.g. "M-A1.P2" or "—"
  provider: string; // e.g. "anthropic" or "—"
  cost: number; // USD amount (e.g. 0.42)
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

/* ── Mode icons (Nerd Font glyphs — same as sidebar-content-renderer) */

const ICONS: Record<string, string> = {
  build: "\uE615",   // nf-dev-codeigniter
  teach: "\uE28C",   // nf-fa-graduation_cap
  both: "\uF0628",   // nf-md-sync
  unknown: "\u25CB", // white circle
};

/* ── Module-level state ─────────────────────────────────────────── */

export const STATUSLINE_STATE: StatuslineState = {
  connection: "unreachable",
  mode: "unknown",
  step: "\u2014",   // em dash
  provider: "\u2014", // em dash
  cost: 0,
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
 * Formats a USD cost amount (in dollars) as a string with "$" prefix.
 * Returns "—" (em dash) for undefined/null amounts.
 *
 * T-084-01: Validates amount is a finite number, clamps to 0–100000 range.
 */
export function formatCost(amount: number | undefined): string {
  if (amount === undefined || amount === null) return "\u2014";
  // Defensive: only accept finite numbers
  if (typeof amount !== "number" || !isFinite(amount)) return "\u2014";
  // Clamp to reasonable range (T-084-01 mitigation)
  const clamped = Math.max(0, Math.min(amount, 100000));
  return `$${clamped.toFixed(2)}`;
}

/**
 * Maps a mode string to its Nerd Font glyph (same glyphs as sidebar-content-renderer.ts ICONS).
 * Unknown modes fall back to white circle (U+25CB).
 */
export function getModeIcon(mode: string): string {
  return ICONS[mode] || ICONS.unknown;
}

/**
 * Maps a mode string to its theme hex color.
 * build → accent (#6366F1), teach → success (#10B981),
 * both → info (#3B82F6), unknown → textMuted (#64748B).
 */
export function getModeColor(mode: string): string {
  switch (mode) {
    case "build":
      return T.accent;
    case "teach":
      return T.success;
    case "both":
      return T.info;
    default:
      return T.textMuted;
  }
}

/* ── Sync mode reader ──────────────────────────────────────────── */

/**
 * Read .state/mode.json synchronously and return mode string.
 * File is <100 bytes and always local — sync read is appropriate.
 * Returns "unknown" on any error (T-084-03: try/catch prevents crash).
 */
function readModeSync(): { mode: string; status: string } {
  try {
    const content = readFileSync(".state/mode.json", "utf-8");
    const json = JSON.parse(content);
    const mode = json.mode;
    if (mode === "build" || mode === "teach" || mode === "both") {
      return { mode, status: "active" };
    }
    return { mode: "unknown", status: "empty" };
  } catch {
    return { mode: "unknown", status: "error" };
  }
}

/* ── Main render function ──────────────────────────────────────── */

/**
 * renderStatusline — returns a Box tree for the current statusline state.
 *
 * Line format: {modeIcon} {MODE_LABEL} · {step} · {provider} · {cost}
 * Maximum width: 28 cells (truncated with U+2026 ellipsis).
 *
 * States:
 *   unreachable → error-colored "state-daemon not running"
 *   connected   → full statusline with live cost/provider/step
 *   disconnected → dimmed statusline with last-known data
 */
export function renderStatusline(): ReturnType<typeof Box> {
  const st = STATUSLINE_STATE;
  const modeInfo = readModeSync();
  const mode = modeInfo.mode;
  const icon = getModeIcon(mode);
  const color = getModeColor(mode);
  const modeLabel = mode === "unknown" ? "IDLE" : mode.toUpperCase();

  // ── Unreachable: show error message ─────────────────────────
  if (st.connection === "unreachable") {
    return Box(
      { flexDirection: "row", height: 1 },
      Txt(
        { fg: T.error, attributes: ATTR_BOLD, height: 1 },
        truncate("state-daemon not running"),
      ),
    );
  }

  // ── Build the statusline row ─────────────────────────────────
  const costStr = st.connection === "disconnected" && st.cost === 0
    ? "\u2014"
    : formatCost(st.cost);

  const providerStr = st.connection === "disconnected" && st.provider === "\u2014"
    ? "\u2014"
    : st.provider;

  // Format: {icon} {MODE} · {step} · {provider} · {cost}
  let line = `${icon} ${modeLabel} \u00b7 ${st.step} \u00b7 ${providerStr} \u00b7 ${costStr}`;

  // Truncate to 28 cells
  line = truncate(line);

  const dimAttr = st.connection === "disconnected" ? ATTR_DIM : 0;

  return Box(
    { flexDirection: "row", height: 1 },
    Txt({ fg: color, height: 1 }, icon),
    Txt({ height: 1 }, " "),
    Txt({ fg: color, attributes: ATTR_BOLD | dimAttr, height: 1 }, modeLabel),
    Txt(
      { fg: T.textMuted, attributes: dimAttr, height: 1 },
      ` \u00b7 ${st.step} \u00b7 ${providerStr} \u00b7 ${costStr}`,
    ),
  );
}

/* ── Event wiring ──────────────────────────────────────────────── */

/**
 * setupStatusline — wires event subscriptions for daemon SSE events.
 *
 * Subscribes to:
 *   - api.event.on("session.next.step.ended") → updates cost
 *   - api.event.on("session.next.model.switched") → updates provider
 *   - api.event.on("session.status") → updates connection state
 *
 * On first event received, sets connection to "connected".
 * Cleanup is registered via api.lifecycle.onDispose.
 */
export function setupStatusline(api: TuiPluginApi): void {
  // Cost event: session.next.step.ended carries properties.cost (T-084-01)
  const unsubCost = api.event.on(
    "session.next.step.ended",
    (event: EventSessionNextStepEnded) => {
      const cost = event.properties.cost;
      if (typeof cost === "number" && isFinite(cost)) {
        STATUSLINE_STATE.cost = cost;
      }
      STATUSLINE_STATE.connection = "connected";
    },
  );

  // Provider event: session.next.model.switched carries properties.providerID
  const unsubProvider = api.event.on(
    "session.next.model.switched",
    (event: EventSessionNextModelSwitched) => {
      if (event.properties.providerID) {
        STATUSLINE_STATE.provider = event.properties.providerID;
      }
      STATUSLINE_STATE.connection = "connected";
    },
  );

  // Status event: session.status (same as build-progress)
  const unsubStatus = api.event.on(
    "session.status",
    (event: EventSessionStatus) => {
      STATUSLINE_STATE.connection = "connected";
      // Derive step identifier from sessionID if available
      if (event.properties.sessionID) {
        const shortID = event.properties.sessionID.slice(0, 8);
        STATUSLINE_STATE.step = `s:${shortID}`;
      }
    },
  );

  api.lifecycle.onDispose(() => {
    unsubCost();
    unsubProvider();
    unsubStatus();

    // Reset state to factory defaults on dispose
    STATUSLINE_STATE.connection = "unreachable";
    STATUSLINE_STATE.step = "\u2014";
    STATUSLINE_STATE.provider = "\u2014";
    STATUSLINE_STATE.cost = 0;
  });

  log({
    source: "@state/opencode-plugin/tui",
    event: "statusline.setup",
    subscriptions: [
      "session.next.step.ended",
      "session.next.model.switched",
      "session.status",
    ],
  });
}
