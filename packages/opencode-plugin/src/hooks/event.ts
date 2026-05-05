/** Event hook — listens for state.mode.activated for hot-reload of MCP registration */

import type { Hooks } from "@opencode-ai/plugin";
import { log } from "../logger.js";
import { readModeConfig, getMcpServersForMode } from "./config.js";
import { resetModeCache } from "../mode-reader.js";

/**
 * state.mode.activated handler: re-reads mode.json and computes
 * the MCP server list. Actual dynamic re-registration at runtime
 * will be handled by the daemon client API (Phase 061).
 */
export const event: NonNullable<Hooks["event"]> = async (input) => {
  // Cast: "state.mode.activated" is not yet in the opencode SDK Event.type
  // union. The daemon emits this event over SSE, and the type assertion
  // preserves TS2367 compatibility (index access on constrained union).
  const eventType = input.event?.type as string | undefined;
  if (eventType !== "state.mode.activated") return;

  log({ msg: "event hook: state.mode.activated received", event: eventType });

  const cwd = process.cwd();
  const mode = await readModeConfig(cwd);
  resetModeCache();
  const servers = getMcpServersForMode(mode);

  log({
    msg: "event hook: state.mode.activated — hot-reload complete",
    new_mode: mode,
    mcp_servers: servers,
    action:
      servers.length > 0
        ? `MCP servers to activate: ${servers.join(", ")}`
        : "No MCP servers for this mode",
  });
};
