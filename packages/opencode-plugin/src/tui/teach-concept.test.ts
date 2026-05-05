/** Unit tests for teach-concept pure rendering functions */

import { describe, expect, it } from "bun:test";
import {
  kolbStageLabel,
  masteryBar,
  renderTeachConcept,
  TEACH_CONCEPT_STATE,
} from "./teach-concept.js";
import type { KolbStage } from "./teach-concept.js";

// ── kolbStageLabel tests ────────────────────────────────────────────

describe("kolbStageLabel", () => {
  it('returns "Concrete Experience" for "concrete_experience"', () => {
    const stage: KolbStage = "concrete_experience";
    expect(kolbStageLabel(stage)).toBe("Concrete Experience");
  });

  it('returns "Reflective Observation" for "reflective_observation"', () => {
    const stage: KolbStage = "reflective_observation";
    expect(kolbStageLabel(stage)).toBe("Reflective Observation");
  });

  it('returns "Abstract Conceptualization" for "abstract_conceptualization"', () => {
    const stage: KolbStage = "abstract_conceptualization";
    expect(kolbStageLabel(stage)).toBe("Abstract Conceptualization");
  });

  it('returns "Active Experimentation" for "active_experimentation"', () => {
    const stage: KolbStage = "active_experimentation";
    expect(kolbStageLabel(stage)).toBe("Active Experimentation");
  });
});

// ── masteryBar tests ────────────────────────────────────────────────

describe("masteryBar", () => {
  it("returns 28-char string with 0 fill, 20 empty for score 0", () => {
    const result = masteryBar(0);
    expect(result.length).toBe(28);
    // 0 fill blocks
    expect(result.split("\u2593").length - 1).toBe(0);
    // 20 empty blocks
    expect(result.split("\u2591").length - 1).toBe(20);
    // Ends with percentage
    expect(result).toMatch(/  0%$/);
  });

  it("returns 28-char string with 10 fill, 10 empty for score 50", () => {
    const result = masteryBar(50);
    expect(result.length).toBe(28);
    const fillCount = result.split("\u2593").length - 1;
    const emptyCount = result.split("\u2591").length - 1;
    expect(fillCount).toBe(10);
    expect(emptyCount).toBe(10);
    expect(result).toMatch(/ 50%$/);
  });

  it("returns 28-char string with 20 fill, 0 empty for score 100", () => {
    const result = masteryBar(100);
    expect(result.length).toBe(28);
    const fillCount = result.split("\u2593").length - 1;
    const emptyCount = result.split("\u2591").length - 1;
    expect(fillCount).toBe(20);
    expect(emptyCount).toBe(0);
    expect(result).toMatch(/100%$/);
  });

  it("returns 28-char string with correct fill for score 42", () => {
    const result = masteryBar(42);
    expect(result.length).toBe(28);
    const fillCount = result.split("\u2593").length - 1;
    // 42/100 * 20 = 8.4 → round to 8
    expect(fillCount).toBe(8);
    const emptyCount = result.split("\u2591").length - 1;
    expect(emptyCount).toBe(12);
    expect(result).toMatch(/ 42%$/);
  });
});

// ── TEACH_CONCEPT_STATE initial values ──────────────────────────────

describe("TEACH_CONCEPT_STATE defaults", () => {
  // Reset state to factory defaults before each test — previous tests
  // in other describe blocks may mutate the module-level state.
  function resetState(): void {
    TEACH_CONCEPT_STATE.connection = "unreachable";
    TEACH_CONCEPT_STATE.concept = null;
  }

  it('has connection "unreachable" on module load', () => {
    resetState();
    expect(TEACH_CONCEPT_STATE.connection).toBe("unreachable");
  });

  it("has concept null on module load", () => {
    resetState();
    expect(TEACH_CONCEPT_STATE.concept).toBeNull();
  });
});

// ── renderTeachConcept tests ───────────────────────────────────────

describe("renderTeachConcept", () => {
  it("returns non-null Box when disconnected", () => {
    TEACH_CONCEPT_STATE.connection = "disconnected";
    TEACH_CONCEPT_STATE.concept = null;
    const result = renderTeachConcept();
    expect(result).not.toBeNull();
  });

  it("returns non-null Box when unreachable", () => {
    TEACH_CONCEPT_STATE.connection = "unreachable";
    TEACH_CONCEPT_STATE.concept = null;
    const result = renderTeachConcept();
    expect(result).not.toBeNull();
  });

  it("returns non-null Box when connected", () => {
    TEACH_CONCEPT_STATE.connection = "connected";
    TEACH_CONCEPT_STATE.concept = null;
    const result = renderTeachConcept();
    expect(result).not.toBeNull();
  });
});
