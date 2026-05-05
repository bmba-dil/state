/**
 * teach-concept — TeachConcept sub-component for the `sidebar_content` TUI slot.
 *
 * Subscribes to daemon SSE events via opencode's `api.event` bus for connectivity
 * heartbeat, renders the current concept card with name, Kolb learning stage,
 * truncated description, and block-character mastery bar.
 *
 * Uses module-level mutable state (consistent with build-progress.ts pattern).
 * State is updated by event handlers; renderTeachConcept() reads current state
 * synchronously on every render frame.
 *
 * Exports:
 *   - setupTeachConcept(api) — wires event subscriptions, registers cleanup
 *   - renderTeachConcept() — returns renderable Box tree for current state
 *   - kolbStageLabel(stage) — pure function: KolbStage → display label
 *   - masteryBar(score) — pure function: 28-char block-character bar + percentage
 *   - TEACH_CONCEPT_STATE — exported const object for test inspection
 */

import { Box, Text, createTextAttributes } from "@opentui/core";
import type { TuiPluginApi } from "@opencode-ai/plugin/tui";
import type { EventSessionStatus } from "@opencode-ai/sdk/v2";

/* ── Types ─────────────────────────────────────────────────────── */

export type ConnectionStatus = "connected" | "disconnected" | "unreachable";
export type KolbStage = "concrete_experience" | "reflective_observation" | "abstract_conceptualization" | "active_experimentation";

export interface ConceptData {
  name: string;
  description: string;
  stage: KolbStage;
  mastery: number; // 0-100 integer
}

export interface TeachConceptState {
  connection: ConnectionStatus;
  concept: ConceptData | null;
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

/* ── Placeholder concept data ──────────────────────────────────── */

const PLACEHOLDER_CONCEPT: ConceptData = {
  name: "Python Type Hints",
  description:
    "Type hints declare expected types for variables and function parameters in Python 3.12+.",
  stage: "reflective_observation",
  mastery: 42,
};

/* ── Module-level state ─────────────────────────────────────────── */

export const TEACH_CONCEPT_STATE: TeachConceptState = {
  connection: "unreachable",
  concept: null,
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

/* ── Helper: split description into lines fitting maxLen ───────── */

/**
 * Split a description string into lines that each fit within maxLen characters.
 * Splits at word boundaries where possible; truncates individual words
 * with U+2026 ellipsis if they exceed maxLen. Returns at most maxLines lines.
 */
export function splitDescription(text: string, maxLen = 28, maxLines = 3): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    // If adding this word exceeds maxLen, push current line and start a new one
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > maxLen) {
      if (current) {
        lines.push(truncate(current, maxLen));
        if (lines.length >= maxLines) return lines;
        current = word;
      } else {
        // Single word longer than maxLen — truncate it
        lines.push(truncate(word, maxLen));
        if (lines.length >= maxLines) return lines;
        current = "";
      }
    } else {
      current = candidate;
    }
  }

  if (current && lines.length < maxLines) {
    lines.push(truncate(current, maxLen));
  }

  return lines;
}

/* ── Exported pure functions ────────────────────────────────────── */

/**
 * Maps a KolbStage enum value to its human-readable display label.
 *
 * Mapping:
 *   "concrete_experience"      → "Concrete Experience"
 *   "reflective_observation"   → "Reflective Observation"
 *   "abstract_conceptualization" → "Abstract Conceptualization"
 *   "active_experimentation"   → "Active Experimentation"
 */
export function kolbStageLabel(stage: KolbStage): string {
  switch (stage) {
    case "concrete_experience":
      return "Concrete Experience";
    case "reflective_observation":
      return "Reflective Observation";
    case "abstract_conceptualization":
      return "Abstract Conceptualization";
    case "active_experimentation":
      return "Active Experimentation";
  }
}

/**
 * Returns a 28-character-wide mastery bar string using block characters.
 *
 * Bar width: 20 cells for blocks, 8 cells for the percentage label.
 * Fill character: U+2593 (▓) dark shade
 * Empty character: U+2591 (░) light shade
 * Format: fill blocks + empty blocks + space + percentage
 *
 * Fill count = Math.round(score / 100 * 20), clamped to [0, 20].
 * The returned string is always exactly 28 characters wide (right-padded with spaces).
 */
export function masteryBar(score: number): string {
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));
  const fillCount = Math.round((clampedScore / 100) * 20);
  const emptyCount = 20 - fillCount;

  const fill = "\u2593".repeat(fillCount); // ▓ dark shade
  const empty = "\u2591".repeat(emptyCount); // ░ light shade

  // Fixed-width 4-char label: right-aligned score + "%"
  // "  0%", " 42%", "100%"
  const label = String(clampedScore).padStart(3, " ") + "%";

  // Bar = 20 cells for blocks; label = 4 chars; pad = 4 spaces
  // Total: 20 + 4 (padding) + 4 (label) = 28
  const bar = fill + empty + " ".repeat(4) + label;
  return bar;
}

/* ── Main render function ──────────────────────────────────────── */

/**
 * renderTeachConcept — returns a Box tree for the current TeachConcept state.
 *
 * Sections (mutually exclusive based on state):
 *   A. Concept header (2 rows: status dot + name, stage indicator + label)
 *   B. Divider (28 ─ chars, border color)
 *   C. Description (2-3 truncated lines, concept non-null + connected only)
 *   D. Mastery bar (block-character bar, concept non-null + connected only)
 *   E. Connection error states (disconnected / unreachable)
 *
 * State logic:
 *   - concept === null && connection === "connected" → A (empty) + B + empty C
 *   - concept !== null && connection === "connected" → A (full) + B + C + divider + D
 *   - connection === "disconnected" → A (empty) + B + E (disconnected)
 *   - connection === "unreachable" → A (empty) + B + E (unreachable)
 */
export function renderTeachConcept(): ReturnType<typeof Box> {
  const st = TEACH_CONCEPT_STATE;
  const children: (ReturnType<typeof Box> | ReturnType<typeof Text>)[] = [];

  // ── A. Concept header ──────────────────────────────────────────
  // Row 1: ● Concept: {name} (accent, bold) or ● No active concept (textMuted, dim)
  if (st.concept !== null) {
    const headerText = `\u25CF Concept: ${st.concept.name}`; // ● dot
    children.push(
      Txt(
        { fg: T.accent, attributes: ATTR_BOLD, height: 1 },
        truncate(headerText),
      ),
    );

    // Row 2: ◈ {stage_label} (info, dim, 2-space indent)
    const stageLabel = kolbStageLabel(st.concept.stage);
    children.push(
      Txt(
        { fg: T.info, attributes: ATTR_DIM, height: 1 },
        truncate(`\u25C8 ${stageLabel}`), // ◈ dot
      ),
    );
  } else {
    children.push(
      Txt(
        { fg: T.textMuted, attributes: ATTR_DIM, height: 1 },
        truncate("\u25CF No active concept"), // ● dot
      ),
    );
  }

  // ── B. Divider ─────────────────────────────────────────────────
  children.push(
    Txt({ fg: T.border, height: 1 }, "\u2500".repeat(28)),
  );

  // ── C/D/E. Content area (mutually exclusive) ───────────────────
  if (st.connection === "connected") {
    if (st.concept !== null) {
      // ── C. Description ────────────────────────────────────────
      const descLines = splitDescription(st.concept.description, 28, 3);
      // First line gets marginTop: 1, subsequent lines get marginTop: 1
      for (const line of descLines) {
        children.push(
          Txt(
            { fg: T.text, attributes: ATTR_DIM, height: 1, marginTop: 1 },
            line,
          ),
        );
      }

      // ── D. Mastery bar ─────────────────────────────────────────
      // Divider above mastery bar
      children.push(
        Txt(
          { fg: T.border, height: 1, marginTop: 1 },
          "\u2500".repeat(28),
        ),
      );
      children.push(
        Txt(
          { fg: T.accent, height: 1, marginTop: 1 },
          masteryBar(st.concept.mastery),
        ),
      );
    } else {
      // ── Empty state when connected but no concept ──────────────
      children.push(
        Txt(
          { fg: T.textMuted, height: 1, marginTop: 4 },
          truncate("No active concept."),
        ),
      );
      children.push(
        Txt(
          { fg: T.textMuted, attributes: ATTR_DIM, height: 1, marginTop: 1 },
          truncate("Select a subject to begin learning."),
        ),
      );
    }
  } else if (st.connection === "disconnected") {
    // ── E. Disconnected state ────────────────────────────────────
    children.push(
      Txt(
        { fg: T.warning, attributes: ATTR_DIM, height: 1, marginTop: 4 },
        truncate("Connection lost. Retrying\u2026"),
      ),
    );
  } else {
    // ── E. Unreachable state ─────────────────────────────────────
    children.push(
      Txt(
        { fg: T.error, attributes: ATTR_BOLD, height: 1, marginTop: 4 },
        truncate("state-daemon not running"),
      ),
    );
    children.push(
      Txt(
        { fg: T.text, attributes: ATTR_DIM, height: 1, marginTop: 1 },
        truncate("Run state-daemon start to"),
      ),
    );
    children.push(
      Txt(
        { fg: T.text, attributes: ATTR_DIM, height: 1, marginTop: 1 },
        truncate("resume."),
      ),
    );
  }

  return Box({ flexDirection: "column" }, ...children);
}

/* ── Event wiring ──────────────────────────────────────────────── */

/**
 * setupTeachConcept — wires event subscriptions for daemon SSE events.
 *
 * Subscribes to `api.event.on("session.status")` and updates
 * TEACH_CONCEPT_STATE on each event. On first event received, sets
 * connection to "connected" and concept to PLACEHOLDER_CONCEPT.
 * Cleanup is registered via api.lifecycle.onDispose.
 */
export function setupTeachConcept(api: TuiPluginApi): void {
  const unsubStatus = api.event.on("session.status", (_event: EventSessionStatus) => {
    TEACH_CONCEPT_STATE.connection = "connected";
    TEACH_CONCEPT_STATE.concept = PLACEHOLDER_CONCEPT;
  });

  api.lifecycle.onDispose(() => {
    unsubStatus();
    // Reset state to factory defaults on dispose
    TEACH_CONCEPT_STATE.connection = "unreachable";
    TEACH_CONCEPT_STATE.concept = null;
  });
}
