/**
 * toast — Toast notification handler for opencode TUI.
 *
 * Subscribes to daemon SSE events via opencode's `api.event` bus:
 *   - session.next.step.ended → Slice completion (success toast)
 *   - session.next.step.failed → Gray-area / error (warning toast)
 *   - session.error → Auth failures / runtime errors (error toast)
 *   - server.connected → Connection/auth restored (info toast)
 *
 * Applies de-duplication (same message within 10 seconds suppressed),
 * enforces 40-character message truncation (per 080-UI-SPEC copywriting
 * contract), and dispatches via `api.ui.toast()` with correct variant
 * and duration per event type.
 *
 * Uses module-level mutable state for de-duplication history
 * (consistent with statusline.ts and build-progress.ts pattern).
 *
 * Exports:
 *   - setupToast(api) — wires event subscriptions, registers cleanup
 *   - TOAST_HISTORY — exported Map for test inspection
 *   - shouldSuppressToast(msg, history, now?) — de-dup check (pure)
 *   - recordToast(msg, history, now?) — records + prunes stale entries
 *   - truncateToastMessage(msg, maxLen?) — enforces 40-char max
 *   - toastMessageForStepEnded(event) — Slice complete message
 *   - toastMessageForStepFailed(event) — error message with context
 *   - toastMessageForServerConnected(event) — auth refresh message
 *   - toastVariantForEvent(eventType) — maps event to toast variant
 *   - toastDurationForEvent(eventType) — maps event to toast duration
 */

import type { TuiPluginApi } from "@opencode-ai/plugin/tui";
import type { TuiToast } from "@opencode-ai/plugin/tui";
import type {
  EventSessionNextStepEnded,
  EventSessionNextStepFailed,
  EventSessionError,
  EventServerConnected,
} from "@opencode-ai/sdk/v2";
import { log } from "../logger.js";

/* ── Types ─────────────────────────────────────────────────────── */

interface ToastEntry {
  message: string;
  timestamp: number; // Date.now() ms
  variant: "info" | "success" | "warning" | "error";
}

/* ── Constants ──────────────────────────────────────────────────── */

/** Debounce window: identical messages within this interval are suppressed. */
const DEBOUNCE_MS = 10_000; // 10 seconds — per 080-UI-SPEC de-duplication rule

/** Maximum toast message length — per 080-UI-SPEC copywriting contract. */
const MAX_MESSAGE_LENGTH = 40;

/* ── Module-level state ─────────────────────────────────────────── */

/**
 * TOAST_HISTORY — Map of message string → timestamp (Date.now() ms).
 * Entries older than DEBOUNCE_MS are pruned on each dispatch.
 * Exported for test inspection.
 */
export const TOAST_HISTORY = new Map<string, number>();

/* ── De-duplication pure functions ──────────────────────────────── */

/**
 * Checks whether a toast message should be suppressed based on the
 * de-duplication history.
 *
 * Returns `true` if the message exists in history AND the elapsed time
 * since it was recorded is less than DEBOUNCE_MS (10 seconds).
 *
 * Pure function — does not mutate history.
 */
export function shouldSuppressToast(
  message: string,
  history: Map<string, number>,
  now?: number,
): boolean {
  const currentTime = now ?? Date.now();
  const lastTimestamp = history.get(message);
  if (lastTimestamp === undefined) return false;
  return (currentTime - lastTimestamp) < DEBOUNCE_MS;
}

/**
 * Records a toast message in the de-duplication history and prunes
 * stale entries (older than DEBOUNCE_MS).
 *
 * Mutates the passed-in Map. The `now` parameter is exposed for
 * deterministic testing — defaults to Date.now().
 */
export function recordToast(
  message: string,
  history: Map<string, number>,
  now?: number,
): void {
  const currentTime = now ?? Date.now();
  history.set(message, currentTime);

  // Prune stale entries
  for (const [key, timestamp] of history) {
    if ((currentTime - timestamp) >= DEBOUNCE_MS) {
      history.delete(key);
    }
  }
}

/* ── Truncation utility ─────────────────────────────────────────── */

/**
 * Truncates a toast message to `maxLen` characters, appending a single
 * ellipsis character (U+2026) if the message exceeds the limit.
 *
 * Per 080-UI-SPEC copywriting contract.
 */
export function truncateToastMessage(message: string, maxLen = MAX_MESSAGE_LENGTH): string {
  if (message.length <= maxLen) return message;
  return message.slice(0, maxLen - 1) + "\u2026";
}

/* ── Message generation pure functions ──────────────────────────── */

/**
 * Generates a toast message for a completed Step (Slice completion).
 *
 * Format: "Slice {shortID} complete ✓" when sessionID is available,
 * or "Slice complete ✓" as fallback.
 *
 * The ✓ character is U+2713 (check mark), per copywriting contract.
 */
export function toastMessageForStepEnded(
  event: EventSessionNextStepEnded,
): string {
  const sessionID = event.properties.sessionID;
  if (sessionID && sessionID.length > 0) {
    const shortID = sessionID.slice(0, 8);
    return truncateToastMessage(`Slice ${shortID} complete \u2713`);
  }
  return "Slice complete \u2713";
}

/**
 * Generates a toast message for a failed Step.
 *
 * Format: "Step failed: {error.message}" when error is available,
 * or "Step failed" as fallback.
 *
 * Final message is truncated to 40 chars.
 */
export function toastMessageForStepFailed(
  event: EventSessionNextStepFailed,
): string {
  const errorObj = event.properties.error;
  if (errorObj && typeof errorObj.message === "string" && errorObj.message.length > 0) {
    return truncateToastMessage(`Step failed: ${errorObj.message}`);
  }
  return "Step failed";
}

/**
 * Generates a toast message for the server.connected event.
 *
 * Returns the exact copywriting contract string: "Auth token refreshed".
 */
export function toastMessageForServerConnected(
  _event: EventServerConnected,
): string {
  return "Auth token refreshed";
}

/**
 * Generates a toast message for session.error events.
 *
 * Format: "{errorType}: {shortMessage}" — extracts from event.properties.error.
 * Falls back to "Session error" when error details are unavailable.
 */
export function toastMessageForSessionError(
  event: EventSessionError,
): string {
  const errorObj = event.properties.error as Record<string, unknown> | undefined;
  if (errorObj && typeof errorObj === "object") {
    const errorType = String(errorObj.name || errorObj.type || "Error");
    const shortMsg = String(errorObj.message || "").split("\n")[0].trim();
    if (shortMsg.length > 0) {
      return truncateToastMessage(`${errorType}: ${shortMsg}`);
    }
    return truncateToastMessage(`${errorType}`);
  }
  return "Session error";
}

/* ── Variant and duration selection ─────────────────────────────── */

/**
 * Maps an event type string to the corresponding toast variant.
 *
 * Mapping:
 *   session.next.step.ended  → success (Slice complete)
 *   session.next.step.failed → warning (gray-area, may retry)
 *   session.next.retried     → warning (gray-area, actively retrying)
 *   session.error            → error   (auth failure / runtime error)
 *   server.connected         → info    (auth refreshed)
 *   default                  → info
 */
export function toastVariantForEvent(
  eventType: string,
): "info" | "success" | "warning" | "error" {
  switch (eventType) {
    case "session.next.step.ended":
      return "success";
    case "session.next.step.failed":
      return "warning";
    case "session.next.retried":
      return "warning";
    case "session.error":
      return "error";
    case "server.connected":
      return "info";
    default:
      return "info";
  }
}

/**
 * Maps an event type string to the corresponding toast duration in
 * milliseconds.
 *
 * Mapping:
 *   session.next.step.ended  → 4000 (success — brief)
 *   session.next.step.failed → 6000 (warning — longer)
 *   session.next.retried     → 6000 (warning — longer)
 *   session.error            → 0    (error — persistent)
 *   server.connected         → 4000 (info — brief)
 *   default                  → 4000
 */
export function toastDurationForEvent(eventType: string): number {
  switch (eventType) {
    case "session.next.step.ended":
      return 4000;
    case "server.connected":
      return 4000;
    case "session.next.step.failed":
      return 6000;
    case "session.next.retried":
      return 6000;
    case "session.error":
      return 0;
    default:
      return 4000;
  }
}

/* ── Toast dispatch orchestration ────────────────────────────────── */

/**
 * Dispatches a toast notification after running the de-duplication gate.
 *
 * 1. Calls `shouldSuppressToast()` — if suppressed, returns early (no-op).
 * 2. Calls `recordToast()` to record this toast in the history.
 * 3. Calls `api.ui.toast()` to show the toast.
 *
 * Duration defaults per variant: info/success → 4000, warning → 6000, error → 0.
 */
function dispatchToast(
  api: TuiPluginApi,
  variant: TuiToast["variant"],
  message: string,
  duration?: number,
): void {
  // De-duplication gate
  if (shouldSuppressToast(message, TOAST_HISTORY)) {
    return;
  }

  // Record this toast
  recordToast(message, TOAST_HISTORY);

  // Determine duration if not explicitly provided
  const resolvedDuration = duration !== undefined
    ? duration
    : variant === "error"
      ? 0
      : variant === "warning"
        ? 6000
        : 4000;

  // Dispatch
  api.ui.toast({
    variant,
    message,
    duration: resolvedDuration,
  });
}

/* ── Event wiring ────────────────────────────────────────────────── */

/**
 * setupToast — wires event subscriptions for daemon SSE events.
 *
 * Subscribes to:
 *   - api.event.on("session.next.step.ended") → Slice completion toast
 *   - api.event.on("session.next.step.failed") → Gray-area / error toast
 *   - api.event.on("session.error") → Auth failure / runtime error toast
 *   - api.event.on("server.connected") → Connection restored toast
 *
 * Each handler derives variant, duration, and message, then dispatches
 * via `dispatchToast()` (which applies de-duplication).
 *
 * Cleanup is registered via api.lifecycle.onDispose.
 */
export function setupToast(api: TuiPluginApi): void {
  // 1. Slice completion → success toast
  const unsubStepEnded = api.event.on(
    "session.next.step.ended",
    (event: EventSessionNextStepEnded) => {
      const variant = toastVariantForEvent(event.type);
      const duration = toastDurationForEvent(event.type);
      const message = toastMessageForStepEnded(event);
      dispatchToast(api, variant, message, duration);
    },
  );

  // 2. Step failed → warning toast (gray-area, may retry)
  const unsubStepFailed = api.event.on(
    "session.next.step.failed",
    (event: EventSessionNextStepFailed) => {
      const variant = toastVariantForEvent(event.type);
      const duration = toastDurationForEvent(event.type);
      const message = toastMessageForStepFailed(event);
      dispatchToast(api, variant, message, duration);
    },
  );

  // 3. Session error → error toast (auth failures, runtime errors)
  const unsubSessionError = api.event.on(
    "session.error",
    (event: EventSessionError) => {
      const variant = toastVariantForEvent(event.type);
      const duration = toastDurationForEvent(event.type);
      const message = toastMessageForSessionError(event);
      dispatchToast(api, variant, message, duration);
    },
  );

  // 4. Server connected → info toast (auth restored)
  const unsubServerConnected = api.event.on(
    "server.connected",
    (event: EventServerConnected) => {
      const variant = toastVariantForEvent(event.type);
      const duration = toastDurationForEvent(event.type);
      const message = toastMessageForServerConnected(event);
      dispatchToast(api, variant, message, duration);
    },
  );

  api.lifecycle.onDispose(() => {
    unsubStepEnded();
    unsubStepFailed();
    unsubSessionError();
    unsubServerConnected();

    // Clear de-duplication history on dispose
    TOAST_HISTORY.clear();
  });

  log({
    source: "@state/opencode-plugin/tui",
    event: "toast.setup",
    subscriptions: [
      "session.next.step.ended",
      "session.next.step.failed",
      "session.error",
      "server.connected",
    ],
  });
}
