/**
 * Unit tests for toast notification handler — pure functions, de-dup logic,
 * message generation, variant/duration mapping, and truncation.
 *
 * Phase 085 — Toast notifications for Slice completion, drill availability,
 * gray-area decisions, and auth refresh.
 */

import { describe, expect, it, beforeEach } from "bun:test";
import {
  shouldSuppressToast,
  recordToast,
  toastMessageForStepEnded,
  toastMessageForStepFailed,
  toastMessageForServerConnected,
  toastMessageForSessionError,
  toastVariantForEvent,
  toastDurationForEvent,
  truncateToastMessage,
  TOAST_HISTORY,
} from "./toast.js";

/* ── Helpers ──────────────────────────────────────────────────── */

function freshHistory(): Map<string, number> {
  return new Map<string, number>();
}

/* ── shouldSuppressToast tests ─────────────────────────────────── */

describe("shouldSuppressToast", () => {
  it("returns false for first occurrence (empty history)", () => {
    const history = freshHistory();
    expect(shouldSuppressToast("Slice complete ✓", history)).toBe(false);
  });

  it("returns true when same message exists within 10s window", () => {
    const history = new Map<string, number>();
    history.set("Slice complete ✓", 5000);
    // now=10000, diff=5000 < 10000 → suppress
    expect(shouldSuppressToast("Slice complete ✓", history, 10000)).toBe(true);
  });

  it("returns false when same message exists but older than 10s", () => {
    const history = new Map<string, number>();
    history.set("Slice complete ✓", 0);
    // now=11000, diff=11000 >= 10000 → allow
    expect(shouldSuppressToast("Slice complete ✓", history, 11000)).toBe(false);
  });

  it("returns false for different message (no collision)", () => {
    const history = new Map<string, number>();
    history.set("Slice complete ✓", 5000);
    expect(shouldSuppressToast("Step failed: oops", history, 6000)).toBe(false);
  });

  it("uses Date.now() when now parameter is omitted", () => {
    const history = freshHistory();
    // Should not throw — uses Date.now() internally
    const result = shouldSuppressToast("some message", history);
    expect(result).toBe(false);
  });
});

/* ── recordToast tests ─────────────────────────────────────────── */

describe("recordToast", () => {
  it("records a message with the given timestamp", () => {
    const history = freshHistory();
    recordToast("Slice complete ✓", history, 1000);
    expect(history.get("Slice complete ✓")).toBe(1000);
  });

  it("prunes entries older than DEBOUNCE_MS (10s)", () => {
    const history = new Map<string, number>();
    history.set("old message", 0); // 0ms
    history.set("recent message", 9500); // within window relative to now=10000
    // now=11000: old diff=11000 (>= 10s, prune), recent diff=1500 (keep)
    recordToast("new message", history, 11000);
    expect(history.has("old message")).toBe(false); // pruned
    expect(history.has("recent message")).toBe(true); // kept
    expect(history.has("new message")).toBe(true); // added
    expect(history.get("new message")).toBe(11000);
  });

  it("uses Date.now() when now parameter is omitted", () => {
    const history = freshHistory();
    recordToast("msg", history);
    const ts = history.get("msg") as number;
    const now = Date.now();
    // Should be within a few ms of now
    expect(Math.abs(now - ts)).toBeLessThan(100);
  });
});

/* ── toastMessageForStepEnded tests ─────────────────────────────── */

describe("toastMessageForStepEnded", () => {
  it('returns "Slice abcdef12 complete ✓" for event with sessionID', () => {
    const event = {
      id: "ev1",
      type: "session.next.step.ended" as const,
      properties: {
        timestamp: 1234567890,
        sessionID: "abcdef12-3456-7890-abcd-ef1234567890",
        finish: "stop",
        cost: 0.05,
        tokens: {
          input: 100,
          output: 50,
          reasoning: 0,
          cache: { read: 0, write: 0 },
        },
      },
    };
    const msg = toastMessageForStepEnded(event);
    expect(msg).toContain("Slice");
    expect(msg).toContain("complete");
    expect(msg).toContain("✓");
    expect(msg).toContain("abcdef12");
  });

  it('returns "Slice complete ✓" for event without sessionID', () => {
    const event = {
      id: "ev2",
      type: "session.next.step.ended" as const,
      properties: {
        timestamp: 1234567890,
        sessionID: "",
        finish: "stop",
        cost: 0,
        tokens: {
          input: 0,
          output: 0,
          reasoning: 0,
          cache: { read: 0, write: 0 },
        },
      },
    };
    const msg = toastMessageForStepEnded(event);
    expect(msg).toBe("Slice complete ✓");
  });
});

/* ── toastMessageForStepFailed tests ────────────────────────────── */

describe("toastMessageForStepFailed", () => {
  it('returns "Step failed: permission denied" for event with error message', () => {
    const event = {
      id: "ev3",
      type: "session.next.step.failed" as const,
      properties: {
        timestamp: 1234567890,
        sessionID: "abc123",
        error: { type: "ToolError", message: "permission denied" },
      },
    };
    const msg = toastMessageForStepFailed(event);
    expect(msg).toBe("Step failed: permission denied");
  });

  it('returns "Step failed" for event without error (fallback)', () => {
    const event = {
      id: "ev4",
      type: "session.next.step.failed" as const,
      properties: {
        timestamp: 1234567890,
        sessionID: "abc123",
        error: undefined as unknown as { type: string; message: string },
      },
    };
    const msg = toastMessageForStepFailed(event);
    expect(msg).toBe("Step failed");
  });

  it("truncates long error messages to 40 chars", () => {
    const event = {
      id: "ev5",
      type: "session.next.step.failed" as const,
      properties: {
        timestamp: 1234567890,
        sessionID: "abc123",
        error: {
          type: "ToolError",
          message: "this is a very long error message that should be truncated at forty characters",
        },
      },
    };
    const msg = toastMessageForStepFailed(event);
    expect(msg.length).toBeLessThanOrEqual(40);
    expect(msg.startsWith("Step failed: ")).toBe(true);
  });
});

/* ── toastMessageForServerConnected tests ───────────────────────── */

describe("toastMessageForServerConnected", () => {
  it('returns "Auth token refreshed" exactly', () => {
    const event = {
      id: "ev6",
      type: "server.connected" as const,
      properties: {},
    };
    const msg = toastMessageForServerConnected(event);
    expect(msg).toBe("Auth token refreshed");
  });
});

/* ── toastVariantForEvent tests ─────────────────────────────────── */

describe("toastVariantForEvent", () => {
  it('returns "success" for session.next.step.ended', () => {
    expect(toastVariantForEvent("session.next.step.ended")).toBe("success");
  });

  it('returns "warning" for session.next.step.failed', () => {
    expect(toastVariantForEvent("session.next.step.failed")).toBe("warning");
  });

  it('returns "warning" for session.next.retried', () => {
    expect(toastVariantForEvent("session.next.retried")).toBe("warning");
  });

  it('returns "error" for session.error', () => {
    expect(toastVariantForEvent("session.error")).toBe("error");
  });

  it('returns "info" for server.connected', () => {
    expect(toastVariantForEvent("server.connected")).toBe("info");
  });

  it('returns "info" for unknown event types (fallback)', () => {
    expect(toastVariantForEvent("unknown.event")).toBe("info");
  });
});

/* ── toastDurationForEvent tests ────────────────────────────────── */

describe("toastDurationForEvent", () => {
  it("returns 4000 for session.next.step.ended", () => {
    expect(toastDurationForEvent("session.next.step.ended")).toBe(4000);
  });

  it("returns 6000 for session.next.step.failed", () => {
    expect(toastDurationForEvent("session.next.step.failed")).toBe(6000);
  });

  it("returns 6000 for session.next.retried", () => {
    expect(toastDurationForEvent("session.next.retried")).toBe(6000);
  });

  it("returns 0 for session.error (persistent)", () => {
    expect(toastDurationForEvent("session.error")).toBe(0);
  });

  it("returns 4000 for server.connected", () => {
    expect(toastDurationForEvent("server.connected")).toBe(4000);
  });

  it("returns 4000 for unknown event types (fallback)", () => {
    expect(toastDurationForEvent("unknown.event")).toBe(4000);
  });
});

/* ── truncateToastMessage tests ─────────────────────────────────── */

describe("truncateToastMessage", () => {
  it("returns short message (< 40 chars) as-is", () => {
    const msg = "Short message";
    expect(truncateToastMessage(msg)).toBe("Short message");
  });

  it("truncates long message (> 40 chars) with … (U+2026)", () => {
    const msg = "This is a very long toast message that exceeds forty characters in length";
    const result = truncateToastMessage(msg);
    expect(result.length).toBe(40);
    expect(result.endsWith("\u2026")).toBe(true);
  });

  it("returns exact 40-char message as-is", () => {
    const msg = "a".repeat(40);
    expect(truncateToastMessage(msg)).toBe(msg);
    expect(truncateToastMessage(msg).length).toBe(40);
  });
});

/* ── TOAST_HISTORY defaults ─────────────────────────────────────── */

describe("TOAST_HISTORY defaults", () => {
  it("starts empty (size 0) on module load", () => {
    // Clear any existing entries from other tests
    TOAST_HISTORY.clear();
    expect(TOAST_HISTORY.size).toBe(0);
    expect(TOAST_HISTORY).toBeInstanceOf(Map);
  });
});

/* ── De-dup integration test ────────────────────────────────────── */

describe("de-dup integration", () => {
  it("first call allows, record, second call suppresses", () => {
    const history = freshHistory();
    const msg = "Slice abc123 complete ✓";

    // First occurrence — should NOT be suppressed
    const first = shouldSuppressToast(msg, history, 1000);
    expect(first).toBe(false);

    // Record it
    recordToast(msg, history, 1000);

    // Second occurrence within 10s — SHOULD be suppressed
    const second = shouldSuppressToast(msg, history, 2000);
    expect(second).toBe(true);
  });
});

// ── toastMessageForSessionError tests ──────────────────────────────

describe("toastMessageForSessionError", () => {
  it('returns "AuthError: token expired" when error has name and message', () => {
    const event = {
      id: "ev7",
      type: "session.error" as const,
      properties: {
        timestamp: 1234567890,
        error: { name: "AuthError", message: "token expired" },
      },
    };
    const msg = toastMessageForSessionError(event);
    expect(msg).toBe("AuthError: token expired");
  });

  it('returns "AuthError" when error has name only (no message)', () => {
    const event = {
      id: "ev8",
      type: "session.error" as const,
      properties: {
        timestamp: 1234567890,
        error: { name: "AuthError", message: "" },
      },
    };
    const msg = toastMessageForSessionError(event);
    expect(msg).toBe("AuthError");
  });

  it('returns "Session error" when event has no error object', () => {
    const event = {
      id: "ev9",
      type: "session.error" as const,
      properties: {
        timestamp: 1234567890,
      } as any,
    };
    const msg = toastMessageForSessionError(event);
    expect(msg).toBe("Session error");
  });

  it("uses only first line of multi-line error.message", () => {
    const event = {
      id: "ev10",
      type: "session.error" as const,
      properties: {
        timestamp: 1234567890,
        error: {
          name: "RuntimeError",
          message: "first line\nsecond line\nthird line",
        },
      },
    };
    const msg = toastMessageForSessionError(event);
    // Only first line used, truncated to 40 chars
    expect(msg).toContain("RuntimeError");
    expect(msg).not.toContain("second line");
    expect(msg).not.toContain("third line");
  });

  it("uses error.name over error.type when both present", () => {
    const event = {
      id: "ev11",
      type: "session.error" as const,
      properties: {
        timestamp: 1234567890,
        error: { name: "AuthError", type: "SomeType", message: "token expired" },
      },
    };
    const msg = toastMessageForSessionError(event);
    expect(msg).toContain("AuthError");
    expect(msg).not.toContain("SomeType");
  });

  it("uses error.type when error.name is absent", () => {
    const event = {
      id: "ev12",
      type: "session.error" as const,
      properties: {
        timestamp: 1234567890,
        error: { type: "FallbackType", message: "something happened" },
      },
    };
    const msg = toastMessageForSessionError(event);
    expect(msg).toContain("FallbackType");
    expect(msg).toContain("something happened");
  });
});

// ── truncateToastMessage custom maxLen tests ───────────────────────

describe("truncateToastMessage custom maxLen", () => {
  it("truncates to custom maxLen=20 with U+2026 ellipsis", () => {
    const msg = "This is a long toast message";
    const result = truncateToastMessage(msg, 20);
    expect(result.length).toBe(20);
    expect(result.endsWith("\u2026")).toBe(true);
  });

  it("returns as-is when message equals custom maxLen=10", () => {
    const msg = "1234567890"; // exactly 10 chars
    const result = truncateToastMessage(msg, 10);
    expect(result).toBe(msg);
    expect(result.length).toBe(10);
  });

  it("returns short message as-is with custom maxLen=100", () => {
    const msg = "short";
    const result = truncateToastMessage(msg, 100);
    expect(result).toBe("short");
  });

  it("uses default 40 when maxLen not specified", () => {
    const msg = "a".repeat(50);
    const result = truncateToastMessage(msg);
    expect(result.length).toBe(40);
  });
});

// ── recordToast race-condition de-dup tests ────────────────────────

describe("recordToast race condition", () => {
  it("records two messages at near-simultaneous times as distinct entries", () => {
    const history = freshHistory();
    recordToast("message A", history, 1000);
    recordToast("message B", history, 1001);
    expect(history.has("message A")).toBe(true);
    expect(history.has("message B")).toBe(true);
    expect(history.get("message A")).toBe(1000);
    expect(history.get("message B")).toBe(1001);
  });

  it("prunes entries older than 10s from the timestamp", () => {
    const history = new Map<string, number>();
    history.set("old1", 0);
    history.set("old2", 500);
    history.set("recent", 9500);

    // now=12000: old1 diff=12000 (prune), old2 diff=11500 (prune), recent diff=2500 (keep)
    recordToast("new", history, 12000);

    expect(history.has("old1")).toBe(false);
    expect(history.has("old2")).toBe(false);
    expect(history.has("recent")).toBe(true);
    expect(history.has("new")).toBe(true);
  });

  it("does not prune entries younger than 10s", () => {
    const history = new Map<string, number>();
    history.set("msg1", 5000);
    history.set("msg2", 9000);

    // now=10000: msg1 diff=5000 (keep), msg2 diff=1000 (keep)
    recordToast("msg3", history, 10000);

    expect(history.has("msg1")).toBe(true);
    expect(history.has("msg2")).toBe(true);
    expect(history.has("msg3")).toBe(true);
  });
});

// ── shouldSuppressToast boundary tests ─────────────────────────────

describe("shouldSuppressToast boundary", () => {
  it("suppresses at t=9999 within 10s window", () => {
    const history = new Map<string, number>();
    history.set("test msg", 0);
    // diff = 9999 < 10000 → suppress
    expect(shouldSuppressToast("test msg", history, 9999)).toBe(true);
  });

  it("does not suppress at t=10000 (at boundary, outside window)", () => {
    const history = new Map<string, number>();
    history.set("test msg", 0);
    // diff = 10000 >= 10000 → allow
    expect(shouldSuppressToast("test msg", history, 10000)).toBe(false);
  });

  it("does not suppress at t=10001 (past boundary)", () => {
    const history = new Map<string, number>();
    history.set("test msg", 0);
    // diff = 10001 >= 10000 → allow
    expect(shouldSuppressToast("test msg", history, 10001)).toBe(false);
  });
});

// ── TOAST_HISTORY clears correctly ─────────────────────────────────

describe("TOAST_HISTORY persistence tests", () => {
  it("TOAST_HISTORY is a Map instance", () => {
    TOAST_HISTORY.clear();
    expect(TOAST_HISTORY).toBeInstanceOf(Map);
  });

  it("clearing TOAST_HISTORY results in size 0", () => {
    TOAST_HISTORY.set("test1", 1000);
    TOAST_HISTORY.set("test2", 2000);
    TOAST_HISTORY.clear();
    expect(TOAST_HISTORY.size).toBe(0);
  });
});
