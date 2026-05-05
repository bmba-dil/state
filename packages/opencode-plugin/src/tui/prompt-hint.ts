/**
 * prompt-hint — compact single-line prompt hint component for the `session_prompt_right` TUI slot.
 *
 * Shows: model abbreviation · token cost · step counter on one line.
 * Subscribes to daemon SSE events via opencode's `api.event` bus for model, cost,
 * and session status updates. Updates module-level state on each event and renders
 * synchronously on every frame using @opentui/core constructs API (Box, Text).
 *
 * Uses module-level mutable state (consistent with statusline.ts pattern).
 * State is updated by event handlers; renderPromptHint() reads current state
 * synchronously on every render frame.
 *
 * Exports:
 *   - setupPromptHint(api) — wires event subscriptions, registers cleanup
 *   - renderPromptHint() — returns renderable Box tree for current state
 *   - PROMPT_HINT_STATE — exported const object for test inspection
 *   - shortenModelID(id) — pure function: extracts last segment of model ID
 */

import { Box, Text, createTextAttributes } from "@opentui/core";
import type { TuiPluginApi } from "@opencode-ai/plugin/tui";
import type {
  EventSessionStatus,
  EventSessionNextStepEnded,
  EventSessionNextModelSwitched,
} from "@opencode-ai/sdk/v2";
import { formatCost } from "./statusline.js";
import { log } from "../logger.js";

/* ── Types ─────────────────────────────────────────────────────── */

export type ConnectionStatus = "connected" | "disconnected" | "unreachable";

export interface PromptHintState {
  connection: ConnectionStatus;
  model: string | undefined; // full model ID from event (e.g. "deepseek/deepseek-v4-pro")
  cost: number;               // USD amount from step.ended (e.g. 0.42)
  stepCount: number;           // incremented on each step.ended
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

/* ── Module-level state ─────────────────────────────────────────── */

export const PROMPT_HINT_STATE: PromptHintState = {
  connection: "unreachable",
  model: undefined,
  cost: 0,
  stepCount: 0,
};

/* ── Helper: Text element constructor ──────────────────────────── */

interface TextElProps {
  fg?: string;
  attributes?: number;
  height?: number;
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
 * Truncates a full model ID to the last segment after the final `/`
 * for display compactness.
 *
 * - "deepseek/deepseek-v4-pro" → "deepseek-v4-pro"
 * - "anthropic/claude-sonnet-4-20250514" → "claude-sonnet-4-20250514"
 * - "openai/gpt-4o" → "gpt-4o"
 * - If no `/` in the string, return as-is (defensive fallback).
 * - If id is empty or undefined → return "—" (em dash).
 */
export function shortenModelID(id: string | undefined): string {
  if (!id) return "\u2014";
  const lastSlash = id.lastIndexOf("/");
  if (lastSlash === -1) return id;
  return id.slice(lastSlash + 1);
}

/* ── Main render function ──────────────────────────────────────── */

/**
 * renderPromptHint — returns a Box tree for the current prompt-hint state.
 *
 * Reads cost, model, stepCount, connection from PROMPT_HINT_STATE synchronously.
 * Line format: {model} · {cost} · Step {N}
 * Maximum width: 28 cells (truncated with U+2026 ellipsis).
 *
 * States:
 *   unreachable → dimmed "—" in textMuted color
 *   connected   → model (accent bold) · cost (textMuted) · Step N (textMuted)
 *   disconnected → last-known data with ATTR_DIM applied
 */
export function renderPromptHint(): ReturnType<typeof Box> {
  const st = PROMPT_HINT_STATE;

  // ── Unreachable: show dimmed em dash ─────────────────────────
  if (st.connection === "unreachable") {
    return Box(
      { flexDirection: "row", height: 1 },
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM, height: 1 },
        "\u2014",
      ),
    );
  }

  // ── Build the prompt hint row ─────────────────────────────────
  const modelStr = shortenModelID(st.model);
  const costStr = formatCost(st.cost);

  // Step indicator: only show "Step N" when connection is "connected"
  // and stepCount >= 0; otherwise use em dash
  const stepStr = st.connection === "connected"
    ? `Step ${st.stepCount}`
    : "\u2014";

  // Format: {model} · {cost} · {stepStr}
  let line = `${modelStr} \u00b7 ${costStr} \u00b7 ${stepStr}`;

  // Truncate to 28 cells
  line = truncate(line);

  const dimAttr = st.connection === "disconnected" ? ATTR_DIM : 0;

  return Box(
    { flexDirection: "row", height: 1 },
    Txt(
      { fg: T.accent, attributes: ATTR_BOLD | dimAttr, height: 1 },
      modelStr,
    ),
    Txt(
      { fg: T.textMuted, attributes: dimAttr, height: 1 },
      ` \u00b7 ${costStr} \u00b7 ${stepStr}`,
    ),
  );
}

/* ── Event wiring ──────────────────────────────────────────────── */

/**
 * setupPromptHint — wires event subscriptions for daemon SSE events.
 *
 * Subscribes to:
 *   - api.event.on("session.next.model.switched") → updates model ID
 *   - api.event.on("session.next.step.ended") → updates cost, increments stepCount
 *   - api.event.on("session.status") → updates connection state
 *
 * On first event received, sets connection to "connected".
 * Cleanup is registered via api.lifecycle.onDispose.
 * On dispose: resets state to factory defaults.
 */
export function setupPromptHint(api: TuiPluginApi): void {
  // Model event: session.next.model.switched carries properties.id (T-087-02)
  const unsubModel = api.event.on(
    "session.next.model.switched",
    (event: EventSessionNextModelSwitched) => {
      if (event.properties.id) {
        PROMPT_HINT_STATE.model = event.properties.id;
      }
      PROMPT_HINT_STATE.connection = "connected";
    },
  );

  // Cost event: session.next.step.ended carries properties.cost (T-087-01)
  const unsubCost = api.event.on(
    "session.next.step.ended",
    (event: EventSessionNextStepEnded) => {
      const cost = event.properties.cost;
      if (typeof cost === "number" && isFinite(cost)) {
        PROMPT_HINT_STATE.cost = cost;
      }
      PROMPT_HINT_STATE.stepCount += 1;
      PROMPT_HINT_STATE.connection = "connected";
    },
  );

  // Status event: session.status (T-087-04)
  const unsubStatus = api.event.on(
    "session.status",
    (_event: EventSessionStatus) => {
      PROMPT_HINT_STATE.connection = "connected";
    },
  );

  api.lifecycle.onDispose(() => {
    unsubModel();
    unsubCost();
    unsubStatus();

    // Reset state to factory defaults on dispose
    PROMPT_HINT_STATE.connection = "unreachable";
    PROMPT_HINT_STATE.model = undefined;
    PROMPT_HINT_STATE.cost = 0;
    PROMPT_HINT_STATE.stepCount = 0;
  });

  log({
    source: "@state/opencode-plugin/tui",
    event: "prompt-hint.setup",
    subscriptions: [
      "session.next.model.switched",
      "session.next.step.ended",
      "session.status",
    ],
  });
}
