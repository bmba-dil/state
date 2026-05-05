/** Tool execute before hook — mode gate, scope gate, path rewrite */

import type { Hooks } from "@opencode-ai/plugin";
import { getCurrentMode } from "../mode-reader.js";

const STATE_MCP_PREFIX = "mcp__state-";
const STATE_BUILD_PREFIX = "mcp__state-build__";
const STATE_TEACH_PREFIX = "mcp__state-teach__";

function isStateTool(tool: string): boolean {
  return tool.startsWith(STATE_MCP_PREFIX);
}

function rewriteStatePaths(args: Record<string, unknown>): Record<string, unknown> {
  const rewritten = { ...args };
  for (const key of Object.keys(rewritten)) {
    const val = rewritten[key];
    if (typeof val === "string" && val.startsWith(".state/")) {
      rewritten[key] = val.replace(/^\.state\//, "$STATE_HOME/");
    }
  }
  return rewritten;
}

export const toolExecuteBefore: NonNullable<
  Hooks["tool.execute.before"]
> = async (input, output) => {
  const mode = await getCurrentMode(process.cwd());
  // Both mode and absent mode.json are permissive — allow all tools
  if (mode === "both" || mode === null) return;

  const tool = input.tool;

  if (mode === "build" && tool.startsWith(STATE_TEACH_PREFIX)) {
    throw new Error(
      `[state] Cross-mode tool blocked: ${tool} is forbidden in build mode`
    );
  }

  if (mode === "teach" && tool.startsWith(STATE_BUILD_PREFIX)) {
    throw new Error(
      `[state] Cross-mode tool blocked: ${tool} is forbidden in teach mode`
    );
  }

  if (isStateTool(tool) && output.args && typeof output.args === "object") {
    output.args = rewriteStatePaths(
      output.args as Record<string, unknown>
    );
  }
};
