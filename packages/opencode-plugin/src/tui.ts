/** @state/opencode-plugin/tui — TUI plugin for opencode sidebar, statusline, toast, prompt-hint slots */

import type { TuiPlugin, TuiSlotPlugin } from "@opencode-ai/plugin/tui";
import type { TuiPluginModule as TuiPluginModuleType } from "@opencode-ai/plugin/tui";

/**
 * Creates the TuiPlugin function that opencode calls when loading the TUI module.
 *
 * On load, this plugin:
 * 1. Installs the custom theme.json (dark mode, 12 semantic color tokens)
 * 2. Registers placeholder slot renderers for all four TUI slots
 *    (phases 081–088 replace these with real components)
 * 3. Subscribes to session status events from the daemon's SSE stream
 *
 * All side effects are cleaned up via api.lifecycle.onDispose.
 */
function createTuiPlugin(): TuiPlugin {
  return async (api) => {
    // ── 1. Install custom theme ──────────────────────────────────────────
    const themeURL = new URL("./theme.json", import.meta.url);
    await api.theme.install(themeURL.pathname);

    // ── 2. Register slot plugins ─────────────────────────────────────────
    // Each slot returns an empty-string placeholder (zero cells rendered).
    // Phases 081–088 replace these with functional components
    // (sidebar_content→081/082/083, sidebar_footer→084,
    // home_footer→084, session_prompt_right→087).
    const slotPlugin: TuiSlotPlugin = {
      order: 100,
      setup() {
        console.log(
          `[@state/opencode-plugin/tui] TUI slot plugins initialized (order=100)`
        );
      },
      dispose() {
        console.log(
          `[@state/opencode-plugin/tui] TUI slot plugins disposed`
        );
      },
      slots: {
        sidebar_content(_ctx, _props) {
          // Phase 081: Mode-aware renderer (build-tree vs concept-state)
          return "";
        },
        sidebar_footer(_ctx, _props) {
          // Phase 084: Statusline (mode · scope · provider · cost)
          return "";
        },
        home_footer(_ctx, _props) {
          // Phase 084: Statusline (home view variant)
          return "";
        },
        session_prompt_right(_ctx, _props) {
          // Phase 087: PromptHint (model · cost · Step N.m)
          return "";
        },
      },
    };

    api.slots.register(slotPlugin);

    // ── 3. Subscribe to daemon SSE ───────────────────────────────────────
    // opencode's event bus relays daemon SSE as typed events.
    // Phases 082–085 subscribe to specific event types here.
    const unsubStatus = api.event.on("session.status", (event) => {
      console.log(
        JSON.stringify({
          source: "@state/opencode-plugin/tui",
          type: "event.session.status",
          sessionID: (event as Record<string, unknown>).sessionID,
          status: (event as Record<string, unknown>).status,
        })
      );
    });

    // Cleanup all subscriptions on plugin dispose
    api.lifecycle.onDispose(() => {
      unsubStatus();
    });
  };
}

export const TuiPluginModule: TuiPluginModuleType = {
  id: "@state/opencode-plugin/tui",
  tui: createTuiPlugin(),
};
