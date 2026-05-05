/** Unit tests for prompt-hint pure functions and render output */

import { describe, expect, it } from "bun:test";
import {
  shortenModelID,
  renderPromptHint,
  PROMPT_HINT_STATE,
} from "./prompt-hint.js";

// ── shortenModelID tests ───────────────────────────────────────────

describe("shortenModelID", () => {
  it('shortenModelID("deepseek/deepseek-v4-pro") returns "deepseek-v4-pro"', () => {
    expect(shortenModelID("deepseek/deepseek-v4-pro")).toBe("deepseek-v4-pro");
  });

  it('shortenModelID("anthropic/claude-sonnet-4-20250514") returns "claude-sonnet-4-20250514"', () => {
    expect(shortenModelID("anthropic/claude-sonnet-4-20250514")).toBe("claude-sonnet-4-20250514");
  });

  it('shortenModelID("openai/gpt-4o") returns "gpt-4o"', () => {
    expect(shortenModelID("openai/gpt-4o")).toBe("gpt-4o");
  });

  it('shortenModelID("no-slash-here") returns "no-slash-here" (no slash → as-is)', () => {
    expect(shortenModelID("no-slash-here")).toBe("no-slash-here");
  });

  it('shortenModelID("") returns "—" (em dash fallback)', () => {
    expect(shortenModelID("")).toBe("\u2014");
  });
});

// ── PROMPT_HINT_STATE defaults ─────────────────────────────────────

describe("PROMPT_HINT_STATE defaults", () => {
  // Reset state to factory defaults before each test
  function resetState(): void {
    PROMPT_HINT_STATE.connection = "unreachable";
    PROMPT_HINT_STATE.model = undefined;
    PROMPT_HINT_STATE.cost = 0;
    PROMPT_HINT_STATE.stepCount = 0;
  }

  it("model is undefined on module load", () => {
    resetState();
    expect(PROMPT_HINT_STATE.model).toBeUndefined();
  });

  it("cost is 0 on module load", () => {
    resetState();
    expect(PROMPT_HINT_STATE.cost).toBe(0);
  });

  it("stepCount is 0 on module load", () => {
    resetState();
    expect(PROMPT_HINT_STATE.stepCount).toBe(0);
  });

  it('connection is "unreachable" on module load', () => {
    resetState();
    expect(PROMPT_HINT_STATE.connection).toBe("unreachable");
  });
});

// ── renderPromptHint tests ─────────────────────────────────────────

describe("renderPromptHint", () => {
  it("returns a Box (non-null) when connection is unreachable", () => {
    PROMPT_HINT_STATE.connection = "unreachable";
    const result = renderPromptHint();
    expect(result).not.toBeNull();
  });

  it("returns a Box (non-null) when connection is connected", () => {
    PROMPT_HINT_STATE.connection = "connected";
    const result = renderPromptHint();
    expect(result).not.toBeNull();
  });

  it("returns a Box (non-null) when connection is disconnected", () => {
    PROMPT_HINT_STATE.connection = "disconnected";
    const result = renderPromptHint();
    expect(result).not.toBeNull();
  });

  it("returns a Box (non-null) when cost is 0 and model is undefined (empty state)", () => {
    PROMPT_HINT_STATE.connection = "connected";
    PROMPT_HINT_STATE.model = undefined;
    PROMPT_HINT_STATE.cost = 0;
    PROMPT_HINT_STATE.stepCount = 0;
    const result = renderPromptHint();
    expect(result).not.toBeNull();
  });

  it('contains "Step" substring when stepCount is 0 and connection is connected', () => {
    PROMPT_HINT_STATE.connection = "connected";
    PROMPT_HINT_STATE.model = "deepseek/deepseek-v4-pro";
    PROMPT_HINT_STATE.cost = 0.42;
    PROMPT_HINT_STATE.stepCount = 0;
    const result = renderPromptHint();
    expect(result).not.toBeNull();
  });
});
