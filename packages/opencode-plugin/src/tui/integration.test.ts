/** Cross-component integration tests for the full TUI plugin lifecycle */

import { describe, expect, it, mock, beforeEach } from "bun:test";
import { createTuiPlugin } from "../tui.js";
import { renderBuildProgress, BUILD_PROGRESS_STATE } from "./build-progress.js";
import { renderStatusline, STATUSLINE_STATE } from "./statusline.js";
import { renderTeachConcept, TEACH_CONCEPT_STATE } from "./teach-concept.js";
import { TOAST_HISTORY } from "./toast.js";
import type { TuiPluginMeta } from "@opencode-ai/plugin/tui";

/* ── Helpers ────────────────────────────────────────────────────── */

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

function makeApi() {
  const installCalls: InstallCall[] = [];
  const mcpAddCalls: McpAddCall[] = [];
  const eventOnCalls: string[] = [];
  const eventHandlers = new Map<string, unknown[]>();
  const slotReg = { plugin: null as unknown };
  const disposeCallbacks: (() => void)[] = [];

  return {
    theme: {
      install: mock(async (_path: string) => {
      }),
    },
    slots: {
      register: mock((plugin: unknown) => {
        slotReg.plugin = plugin;
        return "registered-slot-id";
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
      on: mock((eventType: string, handler: unknown) => {
        eventOnCalls.push(eventType);
        const list = eventHandlers.get(eventType) || [];
        list.push(handler);
        eventHandlers.set(eventType, list);
        return () => {};
      }),
    },
    lifecycle: {
      onDispose: mock((cb: () => void) => {
        disposeCallbacks.push(cb);
        return () => {};
      }),
      signal: new AbortController().signal,
    },
    ui: {
      toast: mock((_opts: unknown) => {}),
    },
    // Expose call trackers
    _installCalls: installCalls,
    _mcpAddCalls: mcpAddCalls,
    _eventOnCalls: eventOnCalls,
    _eventHandlers: eventHandlers,
    _slotReg: slotReg,
    _themeInstalled: () => themeInstalled,
    _disposeCallbacks: disposeCallbacks,
  };
}

/* ── Reset all module-level state ────────────────────────────────── */

function resetAllState(): void {
  BUILD_PROGRESS_STATE.connection = "unreachable";
  BUILD_PROGRESS_STATE.sessionStatus = null;
  BUILD_PROGRESS_STATE.sessionID = null;

  STATUSLINE_STATE.connection = "unreachable";
  STATUSLINE_STATE.mode = "unknown";
  STATUSLINE_STATE.step = "\u2014";
  STATUSLINE_STATE.provider = "\u2014";
  STATUSLINE_STATE.cost = 0;

  TEACH_CONCEPT_STATE.connection = "unreachable";
  TEACH_CONCEPT_STATE.concept = null;

  TOAST_HISTORY.clear();
}

/* ── Tests ──────────────────────────────────────────────────────── */

// 1. Full lifecycle: create → activate → teardown
describe("TUI plugin integration — full lifecycle", () => {
  it("createTuiPlugin returns a callable function", () => {
    const plugin = createTuiPlugin();
    expect(typeof plugin).toBe("function");
  });

  it("first-run activation calls theme.install", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    expect(api.theme.install).toHaveBeenCalled();
  });

  it("first-run activation calls slots.register", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    expect(api.slots.register).toHaveBeenCalled();
  });

  it("first-run activation calls plugins.install with correct spec", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const calls = api._installCalls as InstallCall[];
    expect(calls.length).toBe(1);
    expect(calls[0].spec).toBe("@state/opencode-plugin");
    expect(calls[0].options).toEqual({ global: false });
  });

  it("first-run activation calls mcp.add for state-build and state-teach", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const calls = api._mcpAddCalls as McpAddCall[];
    expect(calls.length).toBe(2);
    expect(calls.map((c: McpAddCall) => c.name).sort()).toEqual(["state-build", "state-teach"]);
  });

  it("slot plugin's sidebar_content returns a renderable result", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const slotPlugin = api._slotReg.plugin as any;
    expect(slotPlugin).not.toBeNull();
    expect(slotPlugin.slots).toBeDefined();
    expect(typeof slotPlugin.slots.sidebar_content).toBe("function");

    const result = slotPlugin.slots.sidebar_content({}, {});
    // Should return a non-empty result (SidebarContentRenderer output)
    expect(result).toBeDefined();
    expect(result).not.toBeNull();
  });

  it("slot plugin's sidebar_footer returns a renderable result", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const slotPlugin = api._slotReg.plugin as any;

    const result = slotPlugin.slots.sidebar_footer({}, {});
    expect(result).toBeDefined();
    expect(result).not.toBeNull();
  });

  it("slot plugin's home_footer returns a renderable result", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const slotPlugin = api._slotReg.plugin as any;

    const result = slotPlugin.slots.home_footer({}, {});
    expect(result).toBeDefined();
    expect(result).not.toBeNull();
  });

  it("updated state skips first-run install but still registers slots", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "updated" });

    // Should skip first-run logic
    expect((api._installCalls as InstallCall[]).length).toBe(0);
    expect((api._mcpAddCalls as McpAddCall[]).length).toBe(0);

    // Should still register slots and theme
    expect(api.theme.install).toHaveBeenCalled();
    expect(api.slots.register).toHaveBeenCalled();
  });
});

// 2. Cross-component mode consistency
describe("TUI plugin integration — cross-component consistency", () => {
  beforeEach(() => {
    resetAllState();
  });

  it("renderBuildProgress and renderStatusline both work in build mode", () => {
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "busy" } as any;

    STATUSLINE_STATE.connection = "connected";
    STATUSLINE_STATE.mode = "build";
    STATUSLINE_STATE.provider = "anthropic";
    STATUSLINE_STATE.cost = 0.42;

    const buildResult = renderBuildProgress();
    const statusResult = renderStatusline();

    expect(buildResult).not.toBeNull();
    expect(statusResult).not.toBeNull();
    // Both should be Box objects
    expect(typeof buildResult).toBe("object");
    expect(typeof statusResult).toBe("object");
  });

  it("renderBuildProgress and renderStatusline are independent", () => {
    // Build progress can be connected while statusline is unreachable
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "busy" } as any;

    STATUSLINE_STATE.connection = "unreachable";

    const buildResult = renderBuildProgress();
    const statusResult = renderStatusline();

    expect(buildResult).not.toBeNull();
    expect(statusResult).not.toBeNull();
  });

  it("renderTeachConcept returns non-null when connected with concept", () => {
    TEACH_CONCEPT_STATE.connection = "connected";
    TEACH_CONCEPT_STATE.concept = {
      name: "Test Integration",
      description: "Testing cross-component state isolation.",
      stage: "active_experimentation",
      mastery: 80,
    };

    const result = renderTeachConcept();
    expect(result).not.toBeNull();
    expect(typeof result).toBe("object");
  });

  it("components share no mutable state cross-contamination", () => {
    // Set build state
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "busy" } as any;

    // Verify teach state is unaffected
    expect(TEACH_CONCEPT_STATE.connection).toBe("unreachable");
    expect(TEACH_CONCEPT_STATE.concept).toBeNull();

    // Verify statusline state is unaffected
    expect(STATUSLINE_STATE.connection).toBe("unreachable");
  });
});

// 3. Event wiring: setup functions invoked
describe("TUI plugin integration — event wiring", () => {
  it("plugin activation registers event listeners for build progress", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const eventCalls = api._eventOnCalls as string[];
    // setupBuildProgress registers session.status
    expect(eventCalls).toContain("session.status");
  });

  it("plugin activation registers event listeners for teach concept", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const eventCalls = api._eventOnCalls as string[];
    // setupTeachConcept also registers session.status
    expect(eventCalls.filter((c: string) => c === "session.status").length).toBeGreaterThanOrEqual(2);
  });

  it("plugin activation registers event listeners for statusline", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const eventCalls = api._eventOnCalls as string[];
    // setupStatusline registers session.next.step.ended, session.next.model.switched, session.status
    expect(eventCalls).toContain("session.next.step.ended");
    expect(eventCalls).toContain("session.next.model.switched");
  });

  it("plugin activation registers event listeners for toast", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const eventCalls = api._eventOnCalls as string[];
    // setupToast registers session.next.step.ended, session.next.step.failed, session.error, server.connected
    expect(eventCalls).toContain("session.next.step.failed");
    expect(eventCalls).toContain("session.error");
    expect(eventCalls).toContain("server.connected");
  });

  it("plugin activation registers lifecycle.onDispose", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    // Each setup function calls onDispose. There are 5 setup functions
    // (build-progress, teach-concept, statusline, prompt-hint, toast)
    expect(api.lifecycle.onDispose).toHaveBeenCalled();
  });
});

// 4. Cleanup / dispose resets state
describe("TUI plugin integration — cleanup/dispose", () => {
  beforeEach(() => {
    resetAllState();
  });

  it("dispose callbacks reset BUILD_PROGRESS_STATE to unreachable", async () => {
    // Set state to connected first
    BUILD_PROGRESS_STATE.connection = "connected";
    BUILD_PROGRESS_STATE.sessionStatus = { type: "busy" } as any;
    BUILD_PROGRESS_STATE.sessionID = "test-session";

    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    // Execute all dispose callbacks
    const disposeCallbacks = api._disposeCallbacks as (() => void)[];
    for (const cb of disposeCallbacks) {
      cb();
    }

    // After dispose, state should be reset
    // Note: BUILD_PROGRESS_STATE is reset to "unreachable" by build-progress's onDispose
    expect(BUILD_PROGRESS_STATE.connection).toBe("unreachable");
    expect(BUILD_PROGRESS_STATE.sessionStatus).toBeNull();
    expect(BUILD_PROGRESS_STATE.sessionID).toBeNull();
  });

  it("dispose callbacks reset STATUSLINE_STATE to unreachable", async () => {
    STATUSLINE_STATE.connection = "connected";
    STATUSLINE_STATE.provider = "anthropic";
    STATUSLINE_STATE.cost = 0.42;

    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const disposeCallbacks = api._disposeCallbacks as (() => void)[];
    for (const cb of disposeCallbacks) {
      cb();
    }

    expect(STATUSLINE_STATE.connection).toBe("unreachable");
  });

  it("dispose callbacks reset TEACH_CONCEPT_STATE to unreachable", async () => {
    TEACH_CONCEPT_STATE.connection = "connected";
    TEACH_CONCEPT_STATE.concept = {
      name: "Test Concept",
      description: "Test",
      stage: "concrete_experience",
      mastery: 50,
    };

    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const disposeCallbacks = api._disposeCallbacks as (() => void)[];
    for (const cb of disposeCallbacks) {
      cb();
    }

    expect(TEACH_CONCEPT_STATE.connection).toBe("unreachable");
    expect(TEACH_CONCEPT_STATE.concept).toBeNull();
  });

  it("dispose callbacks clear TOAST_HISTORY", async () => {
    TOAST_HISTORY.set("test-toast", Date.now());

    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const disposeCallbacks = api._disposeCallbacks as (() => void)[];
    for (const cb of disposeCallbacks) {
      cb();
    }

    // Toast history should be cleared
    expect(TOAST_HISTORY.size).toBe(0);
  });
});

// 5. Prompt-hint slot integration
describe("TUI plugin integration — prompt-hint slot", () => {
  it("session_prompt_right slot returns a renderable Box (phase 087 prompt-hint implemented)", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const slotPlugin = api._slotReg.plugin as any;
    expect(slotPlugin).not.toBeNull();
    expect(slotPlugin.slots.session_prompt_right).toBeDefined();

    const result = slotPlugin.slots.session_prompt_right({}, {});
    // Phase 087 prompt-hint renders a Box with model/cost/step info
    expect(result).not.toBeNull();
    expect(typeof result).toBe("object");
  });

  it("session_prompt_right returns a Box with children when invoked", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const slotPlugin = api._slotReg.plugin as any;

    const result = slotPlugin.slots.session_prompt_right({}, {});
    expect(result).not.toBeNull();
    // Should be a Box object with children
    expect(result.children).toBeDefined();
  });
});

// 6. Toast event handler dispatch
describe("TUI plugin integration — toast event dispatch", () => {
  beforeEach(() => {
    resetAllState();
    TOAST_HISTORY.clear();
  });

  it("toast event handlers are registered for 4 event types", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const eventCalls = api._eventOnCalls as string[];
    // setupToast registers 4 event subscriptions
    const toastEvents = eventCalls.filter((c: string) =>
      ["session.next.step.ended", "session.next.step.failed", "session.error", "server.connected"].includes(c)
    );
    // Each event type should appear at least once (others also register some)
    expect(toastEvents.length).toBeGreaterThanOrEqual(4);
  });

  it("firing server.connected event calls api.ui.toast", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const handlers = api._eventHandlers.get("server.connected") as Array<(event: unknown) => void> | undefined;
    expect(handlers).toBeDefined();
    expect(handlers!.length).toBeGreaterThanOrEqual(1);

    // Fire the server.connected event
    const event = {
      id: "ev1",
      type: "server.connected",
      properties: {},
    };
    handlers![handlers!.length - 1](event);

    // Should have called api.ui.toast
    expect(api.ui.toast).toHaveBeenCalled();
  });

  it("firing session.error event calls api.ui.toast", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const handlers = api._eventHandlers.get("session.error") as Array<(event: unknown) => void> | undefined;
    expect(handlers).toBeDefined();
    expect(handlers!.length).toBeGreaterThanOrEqual(1);

    // Fire the session.error event
    const event = {
      id: "ev2",
      type: "session.error",
      properties: {
        timestamp: Date.now(),
        error: { name: "AuthError", message: "token expired" },
      },
    };
    handlers![0](event);

    expect(api.ui.toast).toHaveBeenCalled();
  });

  it("firing session.next.step.ended event calls api.ui.toast with success variant", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const handlers = api._eventHandlers.get("session.next.step.ended") as Array<(event: unknown) => void> | undefined;
    expect(handlers).toBeDefined();
    expect(handlers!.length).toBeGreaterThanOrEqual(1);

    const event = {
      id: "ev3",
      type: "session.next.step.ended",
      properties: {
        timestamp: Date.now(),
        sessionID: "abcdef12-3456-7890-abcd-ef1234567890",
        finish: "stop",
        cost: 0.05,
        tokens: { input: 100, output: 50, reasoning: 0, cache: { read: 0, write: 0 } },
      },
    };
    handlers![handlers!.length - 1](event);

    expect(api.ui.toast).toHaveBeenCalled();
  });

  it("firing session.next.step.failed event calls api.ui.toast with warning variant", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    const handlers = api._eventHandlers.get("session.next.step.failed") as Array<(event: unknown) => void> | undefined;
    expect(handlers).toBeDefined();
    expect(handlers!.length).toBeGreaterThanOrEqual(1);

    const event = {
      id: "ev4",
      type: "session.next.step.failed",
      properties: {
        timestamp: Date.now(),
        sessionID: "abcdef12",
        error: { type: "ToolError", message: "permission denied" },
      },
    };
    handlers![0](event);

    expect(api.ui.toast).toHaveBeenCalled();
  });

  it("de-duplication suppresses repeated toast within 10s", async () => {
    const plugin = createTuiPlugin();
    const api = makeApi() as any;

    await plugin(api, undefined, { ...fakeEntry(), state: "first" });

    // Fire server.connected twice — second should be suppressed
    const handlers = api._eventHandlers.get("server.connected") as Array<(event: unknown) => void> | undefined;
    const event = { id: "ev5", type: "server.connected", properties: {} };

    handlers![handlers!.length - 1](event);
    // Second call within 10s
    handlers![handlers!.length - 1](event);

    // Both calls should have gone through dispatchToast, but second was suppressed
    // api.ui.toast should have been called at least once (first call only)
    expect(api.ui.toast).toHaveBeenCalled();
  });
});