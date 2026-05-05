/** Unit tests for first-run auto-install in createTuiPlugin */

import { describe, expect, it, mock } from "bun:test";
import { createTuiPlugin } from "../tui.js";
import type { TuiPluginMeta } from "@opencode-ai/plugin/tui";

// ── Helpers ───────────────────────────────────────────────────────────

interface InstallCall {
  spec: string;
  options: Record<string, unknown>;
}

interface McpAddCall {
  name: string;
  config: Record<string, unknown>;
}

function fakeEntry(): Omit<TuiPluginMeta, "state"> {
  return {
    id: "@state/opencode-plugin",
    source: "file",
    spec: "@state/opencode-plugin",
    target: "/tmp/test-plugin",
    first_time: Date.now(),
    last_time: Date.now(),
    time_changed: Date.now(),
  };
}

function makeApi(overrides: Record<string, unknown> = {}) {
  const installCalls: InstallCall[] = [];
  const mcpAddCalls: McpAddCall[] = [];
  let themeInstalled = false;
  let slotRegistered = false;

  return {
    theme: {
      install: mock(async (_path: string) => {
        themeInstalled = true;
      }),
    },
    slots: {
      register: mock((_plugin: unknown) => {
        slotRegistered = true;
        return "slot-id";
      }),
    },
    plugins: {
      install: mock((spec: string, options?: Record<string, unknown>) => {
        installCalls.push({ spec, options: options ?? {} });
        return Promise.resolve({ ok: true, dir: "/tmp/installed", tui: true });
      }),
    },
    client: {
      mcp: {
        add: mock((params: { name: string; config: Record<string, unknown> }) => {
          mcpAddCalls.push({ name: params.name, config: params.config });
          return Promise.resolve({ data: { success: true } });
        }),
      },
    },
    event: {
      on: mock(() => () => {}),
    },
    route: {
      register: mock(() => () => {}),
    },
    lifecycle: {
      onDispose: mock(() => () => {}),
      signal: new AbortController().signal,
    },
    // Expose call trackers for assertions
    _installCalls: installCalls,
    _mcpAddCalls: mcpAddCalls,
    _themeInstalled: () => themeInstalled,
    _slotRegistered: () => slotRegistered,
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────

describe("createTuiPlugin first-run install", () => {
  it("accepts TuiPlugin signature (api, options, meta)", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as ReturnType<typeof makeApi> & Record<string, unknown>;

    await expect(
      plugin(api as any, undefined, { ...fakeEntry(), state: "first" }),
    ).resolves.toBeUndefined();
  });

  it("calls api.plugins.install on first run with correct args", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as ReturnType<typeof makeApi> & Record<string, unknown>;

    await plugin(api as any, undefined, { ...fakeEntry(), state: "first" });

    const calls = api._installCalls as InstallCall[];
    expect(calls.length).toBe(1);
    expect(calls[0].spec).toBe("@state/opencode-plugin");
    expect(calls[0].options).toEqual({ global: false });
  });

  it("calls api.client.mcp.add for state-build and state-teach on first run", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as ReturnType<typeof makeApi> & Record<string, unknown>;

    await plugin(api as any, undefined, { ...fakeEntry(), state: "first" });

    const calls = api._mcpAddCalls as McpAddCall[];
    expect(calls.length).toBe(2);
    expect(calls.map((c) => c.name).sort()).toEqual(["state-build", "state-teach"]);
  });

  it("passes correct McpLocalConfig to mcp.add", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as ReturnType<typeof makeApi> & Record<string, unknown>;

    await plugin(api as any, undefined, { ...fakeEntry(), state: "first" });

    const calls = api._mcpAddCalls as McpAddCall[];
    for (const call of calls) {
      expect(call.config.type).toBe("local");
      expect(call.config.command).toEqual([call.name]);
      expect(call.config.enabled).toBe(true);
    }
  });

  it("skips install when state is 'updated'", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as ReturnType<typeof makeApi> & Record<string, unknown>;

    await plugin(api as any, undefined, { ...fakeEntry(), state: "updated" });

    expect((api._installCalls as InstallCall[]).length).toBe(0);
    expect((api._mcpAddCalls as McpAddCall[]).length).toBe(0);
  });

  it("skips install when state is 'same'", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as ReturnType<typeof makeApi> & Record<string, unknown>;

    await plugin(api as any, undefined, { ...fakeEntry(), state: "same" });

    expect((api._installCalls as InstallCall[]).length).toBe(0);
    expect((api._mcpAddCalls as McpAddCall[]).length).toBe(0);
  });

  it("resolves even when api.client.mcp.add rejects", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi({
      client: {
        mcp: {
          add: mock(() => Promise.reject(new Error("MCP registration failed"))),
        },
      },
    }) as ReturnType<typeof makeApi> & Record<string, unknown>;

    // Must not throw — plugin load always succeeds
    await expect(
      plugin(api as any, undefined, { ...fakeEntry(), state: "first" }),
    ).resolves.toBeUndefined();
  });

  it("still calls theme.install and slots.register after first-run logic", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as ReturnType<typeof makeApi> & Record<string, unknown>;

    await plugin(api as any, undefined, { ...fakeEntry(), state: "first" });

    // Verify existing setup functions were called (theme, slots, SSE setups)
    const themeMock = api.theme.install as ReturnType<typeof mock>;
    const slotsMock = api.slots.register as ReturnType<typeof mock>;
    expect(themeMock).toHaveBeenCalled();
    expect(slotsMock).toHaveBeenCalled();
  });
});
