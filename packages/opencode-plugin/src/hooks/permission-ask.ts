/** Permission ask hook — gray-area routing */

import type { Hooks } from "@opencode-ai/plugin";
import { log } from "../logger.js";

export const permissionAsk: NonNullable<
  Hooks["permission.ask"]
> = async (input, output) => {
  const mode = process.env.STATE_MODE || "kernel";

  const isStateInternal =
    input.title?.includes("state") ||
    input.type?.startsWith("mcp__state-") ||
    input.pattern?.includes(".state/");

  if (isStateInternal) {
    output.status = "allow";
    log({
      source: "@state/opencode-plugin",
      hook: "permission.ask",
      type: "permission.decided",
      permissionID: input.id,
      permissionType: input.type,
      decision: "allow",
      reason: "state internal",
      mode,
      timestamp: Date.now(),
    });
    return;
  }

  const metadata = input.metadata as Record<string, unknown> | undefined;
  const isStatePath =
    typeof metadata?.path === "string"
      ? (metadata.path as string).startsWith(".state/")
      : false;

  if (isStatePath) {
    output.status = "allow";
    log({
      source: "@state/opencode-plugin",
      hook: "permission.ask",
      type: "permission.decided",
      permissionID: input.id,
      permissionType: input.type,
      decision: "allow",
      reason: ".state/ path write within scope",
      mode,
      timestamp: Date.now(),
    });
    return;
  }

  log({
    source: "@state/opencode-plugin",
    hook: "permission.ask",
    type: "permission.decided",
    permissionID: input.id,
    permissionType: input.type,
    decision: "ask",
    reason: "default opencode permission flow",
    mode,
    timestamp: Date.now(),
  });
};
