/**
 * status-palette — Shared status color/dot/label mappings for TUI components.
 *
 * Canonical status palette consumed by dag-viewer, build-progress, and future TUI
 * components that need consistent status rendering. Colors are derived from the
 * opencode plugin theme (theme.json) for consistency with the host application.
 *
 * Exports:
 *   - StepStatus (type) — union of all valid status strings
 *   - statusColor(status) — maps status to hex color from theme
 *   - statusChar(status) — maps status to Unicode dot character
 *   - statusLabel(status) — maps status to human-readable label
 *   - STATUS_COLORS — Record<StepStatus, string> lookup map
 *   - STATUS_CHARS — Record<string, string> lookup map (loose key for backward compat)
 *   - STATUS_LABELS — Record<string, string> lookup map (loose key for backward compat)
 *   - statusColorFn — alias for statusColor (backward compat with build-progress)
 */

/* ── Theme colors (matches theme.json) ──────────────────────────── */

const T = {
  accent: "#6366F1",
  success: "#10B981",
  info: "#3B82F6",
  textMuted: "#64748B",
  error: "#EF4444",
  warning: "#F59E0B",
} as const;

/* ── Types ─────────────────────────────────────────────────────── */

export type StepStatus =
  | "pending"
  | "running"
  | "done"
  | "failed"
  | "blocked"
  | "retry"
  | "unknown";

/* ── Status color map ──────────────────────────────────────────── */

export const STATUS_COLORS: Record<StepStatus, string> = {
  pending: T.textMuted,
  running: T.accent,
  done: T.success,
  failed: T.error,
  blocked: T.warning,
  retry: T.info,
  unknown: T.textMuted,
};

/**
 * Backward-compat color map: includes "idle", "busy", and legacy mappings
 * from the pre-shared-palette era.
 */
export const STATUS_COLORS_COMPAT: Record<string, string> = {
  ...STATUS_COLORS,
  idle: T.success,       // idle = done
  busy: T.accent,        // busy = running
};

/* ── Status dot character map ──────────────────────────────────── */

export const STATUS_CHARS: Record<string, string> = {
  pending: "\u25CB",   // ○ white circle
  running: "\u25C9",   // ◉ fisheye
  done: "\u25CF",      // ● black circle
  failed: "\u2717",    // ✗ ballot x
  blocked: "\u25CD",   // ◍ circle with vertical fill
  retry: "\u21BB",     // ↻ clockwise open circle arrow
  unknown: "\u25CB",   // ○ white circle
  // Backward-compat aliases
  idle: "\u25CF",      // ● (idle = done)
  busy: "\u25C9",      // ◉ (busy = running)
  "in-progress": "\u25C9", // ◉
};

/* ── Status label map ──────────────────────────────────────────── */

export const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  running: "In Progress",
  done: "Done",
  failed: "Failed",
  blocked: "Blocked",
  retry: "Retrying",
  unknown: "Unknown",
  // Backward-compat aliases
  idle: "Done",
  busy: "In Progress",
  "in-progress": "In Progress",
};

/* ── Pure functions ────────────────────────────────────────────── */

/**
 * Maps a StepStatus to its corresponding hex color from the opencode theme.
 *
 * Mapping:
 *   "running" → T.accent    (#6366F1) — active/primary
 *   "done"    → T.success   (#10B981) — completed
 *   "failed"  → T.error     (#EF4444) — failure
 *   "blocked" → T.warning   (#F59E0B) — blocked/dependency
 *   "retry"   → T.info      (#3B82F6) — retry active
 *   "pending" | "unknown"   → T.textMuted (#64748B) — inactive
 */
export function statusColor(status: StepStatus | string): string {
  return STATUS_COLORS_COMPAT[status] ?? (STATUS_COLORS[status as StepStatus] ?? T.textMuted);
}

/** Backward compat alias — used by build-progress.ts public API */
export const stepStatusColor = statusColor;

/**
 * Maps a StepStatus (or compat string) to its Unicode dot character.
 */
export function statusChar(status: string): string {
  return STATUS_CHARS[status] ?? STATUS_CHARS.unknown;
}

/**
 * Maps a StepStatus (or compat string) to its human-readable label.
 */
export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? STATUS_LABELS.unknown;
}
