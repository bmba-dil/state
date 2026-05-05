/** Unit tests for getCurrentMode caching and resetModeCache */

import { describe, expect, it, beforeEach, afterAll } from "bun:test";
import { mkdirSync, rmSync, existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { getCurrentMode, resetModeCache } from "../mode-reader.js";
import type { ResolvedMode } from "../mode-reader.js";

const TMP = join(import.meta.dirname, "..", "..", "node_modules", ".cache", "mode-reader-test");
const TMP_STATE = join(TMP, ".state");

function ensureTmpDir(): void {
  if (!existsSync(TMP)) mkdirSync(TMP, { recursive: true });
  if (!existsSync(TMP_STATE)) mkdirSync(TMP_STATE, { recursive: true });
}

function cleanTmpDir(): void {
  const modeFile = join(TMP_STATE, "mode.json");
  if (existsSync(modeFile)) rmSync(modeFile);
}

function writeModeJson(mode: string): void {
  ensureTmpDir();
  writeFileSync(join(TMP_STATE, "mode.json"), JSON.stringify({ mode }));
}

function removeModeJson(): void {
  const modeFile = join(TMP_STATE, "mode.json");
  if (existsSync(modeFile)) rmSync(modeFile);
}

describe("getCurrentMode", () => {
  beforeEach(() => {
    resetModeCache();
    ensureTmpDir();
    cleanTmpDir();
  });

  afterAll(() => {
    // Clean up temp directory entirely
    if (existsSync(TMP)) rmSync(TMP, { recursive: true, force: true });
  });

  it("returns null when .state/mode.json is absent", async () => {
    removeModeJson();
    const mode = await getCurrentMode(TMP);
    expect(mode).toBeNull();
  });

  it("returns 'build' when mode.json contains {'mode':'build'}", async () => {
    writeModeJson("build");
    const mode = await getCurrentMode(TMP);
    expect(mode).toBe("build");
  });

  it("returns 'teach' when mode.json contains {'mode':'teach'}", async () => {
    writeModeJson("teach");
    const mode = await getCurrentMode(TMP);
    expect(mode).toBe("teach");
  });

  it("returns 'both' when mode.json contains {'mode':'both'}", async () => {
    writeModeJson("both");
    const mode = await getCurrentMode(TMP);
    expect(mode).toBe("both");
  });

  it("returns null when mode.json contains an invalid mode", async () => {
    writeModeJson("kernel");
    const mode = await getCurrentMode(TMP);
    expect(mode).toBeNull();
  });

  it("caches the mode — second call does not re-read the file", async () => {
    writeModeJson("build");
    const first = await getCurrentMode(TMP);
    expect(first).toBe("build");

    // Remove the file between calls
    removeModeJson();

    // Second call should return cached value, not re-read from disk
    const second = await getCurrentMode(TMP);
    expect(second).toBe("build");
  });

  it("resetModeCache invalidates cached value so next call re-reads", async () => {
    writeModeJson("build");
    const first = await getCurrentMode(TMP);
    expect(first).toBe("build");

    // Change mode and invalidate cache
    writeModeJson("teach");
    resetModeCache();

    const second = await getCurrentMode(TMP);
    expect(second).toBe("teach");
  });

  it("resetModeCache then no mode.json returns null", async () => {
    writeModeJson("build");
    const first = await getCurrentMode(TMP);
    expect(first).toBe("build");

    // Delete mode.json and invalidate cache
    removeModeJson();
    resetModeCache();

    const second = await getCurrentMode(TMP);
    expect(second).toBeNull();
  });
});
