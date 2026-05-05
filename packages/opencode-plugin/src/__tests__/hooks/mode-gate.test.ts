/** Integration tests for hook mode enforcement matrix */

import { describe, expect, it, beforeEach, afterEach } from "bun:test";
import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { resetModeCache } from "../../mode-reader.js";
import { commandExecuteBefore } from "../../hooks/command-execute-before.js";
import { toolExecuteBefore } from "../../hooks/tool-execute-before.js";

const STATE_DIR = join(process.cwd(), ".state");
const MODE_JSON = join(STATE_DIR, "mode.json");

function writeModeJson(mode: string): void {
  if (!existsSync(STATE_DIR)) mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(MODE_JSON, JSON.stringify({ mode }));
}

function removeModeJson(): void {
  if (existsSync(MODE_JSON)) rmSync(MODE_JSON);
}

describe("command hook mode gate", () => {
  beforeEach(() => {
    resetModeCache();
    removeModeJson();
  });

  afterEach(() => {
    removeModeJson();
  });

  it("blocks /state:build: when mode is teach", async () => {
    writeModeJson("teach");
    const output = { parts: [] as Array<Record<string, unknown>> };
    await commandExecuteBefore(
      { command: "/state:build:plan" } as Parameters<typeof commandExecuteBefore>[0],
      output as Parameters<typeof commandExecuteBefore>[1]
    );
    expect(output.parts.length).toBeGreaterThan(0);
    const part = output.parts[0] as { text?: string };
    expect(part.text).toContain("Cross-mode command blocked");
  });

  it("blocks /state:teach: when mode is build", async () => {
    writeModeJson("build");
    const output = { parts: [] as Array<Record<string, unknown>> };
    await commandExecuteBefore(
      { command: "/state:teach:lesson" } as Parameters<typeof commandExecuteBefore>[0],
      output as Parameters<typeof commandExecuteBefore>[1]
    );
    expect(output.parts.length).toBeGreaterThan(0);
    const part = output.parts[0] as { text?: string };
    expect(part.text).toContain("Cross-mode command blocked");
  });

  it("allows /state:build: when mode is build", async () => {
    writeModeJson("build");
    const output = { parts: [] as Array<Record<string, unknown>> };
    await commandExecuteBefore(
      { command: "/state:build:plan" } as Parameters<typeof commandExecuteBefore>[0],
      output as Parameters<typeof commandExecuteBefore>[1]
    );
    // No blocking Part should be pushed
    expect(output.parts.length).toBe(0);
  });

  it("allows /state:teach: when mode is teach", async () => {
    writeModeJson("teach");
    const output = { parts: [] as Array<Record<string, unknown>> };
    await commandExecuteBefore(
      { command: "/state:teach:lesson" } as Parameters<typeof commandExecuteBefore>[0],
      output as Parameters<typeof commandExecuteBefore>[1]
    );
    expect(output.parts.length).toBe(0);
  });

  it("allows /state:build: when mode is both", async () => {
    writeModeJson("both");
    const output = { parts: [] as Array<Record<string, unknown>> };
    await commandExecuteBefore(
      { command: "/state:build:plan" } as Parameters<typeof commandExecuteBefore>[0],
      output as Parameters<typeof commandExecuteBefore>[1]
    );
    expect(output.parts.length).toBe(0);
  });

  it("allows all commands when mode is null (no mode.json)", async () => {
    // Ensure no mode.json exists
    removeModeJson();
    const output = { parts: [] as Array<Record<string, unknown>> };
    await commandExecuteBefore(
      { command: "/state:build:plan" } as Parameters<typeof commandExecuteBefore>[0],
      output as Parameters<typeof commandExecuteBefore>[1]
    );
    expect(output.parts.length).toBe(0);
  });
});

describe("tool hook mode gate", () => {
  beforeEach(() => {
    resetModeCache();
    removeModeJson();
  });

  afterEach(() => {
    removeModeJson();
  });

  it("blocks mcp__state-teach__ when mode is build", async () => {
    writeModeJson("build");
    const output = {} as Parameters<typeof toolExecuteBefore>[1];
    let threw = false;
    let errorMsg = "";
    try {
      await toolExecuteBefore(
        { tool: "mcp__state-teach__do_lesson" } as Parameters<typeof toolExecuteBefore>[0],
        output
      );
    } catch (e) {
      threw = true;
      errorMsg = (e as Error).message;
    }
    expect(threw).toBe(true);
    expect(errorMsg).toContain("forbidden in build mode");
  });

  it("blocks mcp__state-build__ when mode is teach", async () => {
    writeModeJson("teach");
    const output = {} as Parameters<typeof toolExecuteBefore>[1];
    let threw = false;
    let errorMsg = "";
    try {
      await toolExecuteBefore(
        { tool: "mcp__state-build__plan_phase" } as Parameters<typeof toolExecuteBefore>[0],
        output
      );
    } catch (e) {
      threw = true;
      errorMsg = (e as Error).message;
    }
    expect(threw).toBe(true);
    expect(errorMsg).toContain("forbidden in teach mode");
  });

  it("allows mcp__state-build__ when mode is build", async () => {
    writeModeJson("build");
    const output = {} as Parameters<typeof toolExecuteBefore>[1];
    let threw = false;
    try {
      await toolExecuteBefore(
        { tool: "mcp__state-build__plan_phase" } as Parameters<typeof toolExecuteBefore>[0],
        output
      );
    } catch {
      threw = true;
    }
    expect(threw).toBe(false);
  });

  it("allows mcp__state-teach__ when mode is teach", async () => {
    writeModeJson("teach");
    const output = {} as Parameters<typeof toolExecuteBefore>[1];
    let threw = false;
    try {
      await toolExecuteBefore(
        { tool: "mcp__state-teach__do_lesson" } as Parameters<typeof toolExecuteBefore>[0],
        output
      );
    } catch {
      threw = true;
    }
    expect(threw).toBe(false);
  });

  it("allows all state tools when mode is both", async () => {
    writeModeJson("both");
    const output = {} as Parameters<typeof toolExecuteBefore>[1];

    let threwBuild = false;
    try {
      await toolExecuteBefore(
        { tool: "mcp__state-build__plan_phase" } as Parameters<typeof toolExecuteBefore>[0],
        output
      );
    } catch {
      threwBuild = true;
    }

    let threwTeach = false;
    try {
      await toolExecuteBefore(
        { tool: "mcp__state-teach__do_lesson" } as Parameters<typeof toolExecuteBefore>[0],
        output
      );
    } catch {
      threwTeach = true;
    }

    expect(threwBuild).toBe(false);
    expect(threwTeach).toBe(false);
  });

  it("allows all tools when mode is null (no mode.json)", async () => {
    removeModeJson();
    const output = {} as Parameters<typeof toolExecuteBefore>[1];
    let threw = false;
    try {
      await toolExecuteBefore(
        { tool: "mcp__state-teach__do_lesson" } as Parameters<typeof toolExecuteBefore>[0],
        output
      );
    } catch {
      threw = true;
    }
    expect(threw).toBe(false);
  });
});
