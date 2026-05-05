/** @state/opencode-plugin/tui — TUI plugin for opencode sidebar, statusline, toast, prompt-hint slots */

import type { TuiPlugin, TuiSlotPlugin } from "@opencode-ai/plugin/tui";
import type { TuiPluginModule as TuiPluginModuleType } from "@opencode-ai/plugin/tui";
import { log } from "./logger.js";
import SidebarContentRenderer from "./tui/sidebar-content-renderer.js";
import { setupBuildProgress } from "./tui/build-progress.js";
import { setupTeachConcept } from "./tui/teach-concept.js";
import { setupStatusline, renderStatusline } from "./tui/statusline.js";
import { setupPromptHint, renderPromptHint } from "./tui/prompt-hint.js";
import { setupToast } from "./tui/toast.js";
import { setupDagViewer, renderDagViewer, DAG_VIEWER_STATE } from "./tui/dag-viewer.js";

/**
 * Creates the TuiPlugin function that opencode calls when loading the TUI module.
 *
 * On load, this plugin:
 * 1. Installs the custom theme.json (dark mode, 12 semantic color tokens)
 * 2. Registers placeholder slot renderers for all four TUI slots
 *    (phases 081–088 replace these with real components)
 * 3. Wires BuildProgress event subscriptions (Phase 082)
 * 4. Wires TeachConcept event subscriptions (Phase 083)
 * 5. Wires Statusline event subscriptions for footer slots (Phase 084)
 * 6. Wires Toast notification handler (Phase 085)
 *
 * All side effects are cleaned up via api.lifecycle.onDispose.
 */
function createTuiPlugin(): TuiPlugin {
  return async (api, _options, meta) => {
    // ── 0. First-run auto-install ──────────────────────────────────────────
    if (meta.state === "first") {
      // Auto-register the plugin itself using TuiPluginInstallOptions API
      api.plugins.install("@state/opencode-plugin", { global: false })
        .then((result) => {
          log({
            source: "@state/opencode-plugin/tui",
            event: "tui.install.plugin",
            state: meta.state,
            result,
          });
        })
        .catch((err) => {
          log({
            source: "@state/opencode-plugin/tui",
            event: "tui.install.plugin.error",
            error: String(err),
          });
        });

      // Auto-register MCP servers
      for (const name of ["state-build", "state-teach"] as const) {
        api.client.mcp.add({
          name,
          config: {
            type: "local",
            command: [name],
            enabled: true,
          },
        })
          .then((response) => {
            log({
              source: "@state/opencode-plugin/tui",
              event: "tui.install.mcp",
              mcp: name,
              response: response.data,
            });
          })
          .catch((err) => {
            log({
              source: "@state/opencode-plugin/tui",
              event: "tui.install.mcp.error",
              mcp: name,
              error: String(err),
            });
          });
      }
    }

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
        log({
          source: "@state/opencode-plugin/tui",
          event: "tui.slots.setup",
          order: 100,
        });
      },
      dispose() {
        log({
          source: "@state/opencode-plugin/tui",
          event: "tui.slots.dispose",
        });
      },
      slots: {
        sidebar_content(_ctx, _props) {
          // Phase 081: SidebarContentRenderer — mode-aware renderer (build-tree vs concept-state)
          return SidebarContentRenderer(_ctx, _props) as unknown as string;
        },
        sidebar_footer(_ctx, _props) {
          // Phase 084: Statusline (mode · scope · provider · cost)
          return renderStatusline() as unknown as string;
        },
        home_footer(_ctx, _props) {
          // Phase 084: Statusline (home view variant)
          return renderStatusline() as unknown as string;
        },
        session_prompt_right(_ctx, _props) {
          // Phase 087: PromptHint (model · cost · Step N)
          return renderPromptHint() as unknown as string;
        },
      },
    };

    api.slots.register(slotPlugin);

    // ── 2.5. Register state.dag route (Phase 089) ──────────────────────
    const unregisterDag = api.route.register([
      {
        name: "state.dag",
        render: (_input) => renderDagViewer(DAG_VIEWER_STATE) as any,
      },
    ]);
    api.lifecycle.onDispose(() => unregisterDag());

    // ── 3. Subscribe to daemon SSE ───────────────────────────────────────
    // Phase 082: BuildProgress — subscribes to daemon SSE via api.event bus.
    // State is updated by event handlers; renderBuildProgress() reads it each frame.
    setupBuildProgress(api);

    // Phase 083: TeachConcept — subscribes to daemon SSE for connectivity heartbeat.
    // State is updated by event handlers; renderTeachConcept() reads it each frame.
    setupTeachConcept(api);

    // Phase 089: DagViewer — subscribes to daemon SSE for DAG route state
    setupDagViewer(api);

    // Phase 084: Statusline — subscribes to daemon SSE cost/status events
    // for sidebar_footer and home_footer rendering.
    setupStatusline(api);

    // Phase 087: PromptHint — subscribes to model/cost events for session_prompt_right
    setupPromptHint(api);

    // Phase 085: Toast — subscribes to daemon SSE events (step ended, step failed,
    // server connected, session error), maps to toast notifications with de-dup.
    setupToast(api);
  };
}

export { createTuiPlugin };

export const TuiPluginModule: TuiPluginModuleType = {
  id: "@state/opencode-plugin/tui",
  tui: createTuiPlugin(),
};
