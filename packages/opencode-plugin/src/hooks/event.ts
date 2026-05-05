/** Event hook — listens for state.mode.activated for hot-reload of MCP registration */

import type { Hooks } from "@opencode-ai/plugin";
import { log } from "../logger.js";
import { readModeConfig } from "./config.js";

/**
 * The event hook listens for state.mode.activated events.
 * When received, re-reads mode.json and logs the transition.
 *
 * Note: Full MCP re-registration via daemon client API will be
 * implemented when Phase 104 (mode activation event) ships with
 * the daemon SSE event bus. This scaffold establishes the event
 * listener pattern and validates the mode.json re-read.
 */
export const event: NonNullable<Hooks["event"]> = async (input) => {
  // Cast: "state.mode.activated" is not yet in the opencode SDK Event.type
  // union. Phase 104 will add it to the daemon SSE event bus.
  const eventType = input.event?.type as string | undefined;
  if (eventType !== "state.mode.activated") return;

  log({ msg: "event hook: state.mode.activated received", event: eventType });

  const cwd = process.cwd();
  const mode = await readModeConfig(cwd);
  log({
    msg: "event hook: mode.json re-read for hot-reload",
    mode,
    note:
      "Full MCP re-registration via daemon client API will be implemented when Phase 104 ships. " +
      "This scaffold validates the event listener pattern and mode re-read.",
  });
};
