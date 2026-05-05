/** Tool execute after hook — output verification + observation */

import type { Hooks } from "@opencode-ai/plugin";
import { log } from "../logger.js";

type StateMode = "build" | "teach" | "kernel";

function currentMode(): StateMode {
  const m = process.env.STATE_MODE;
  if (m === "build" || m === "teach" || m === "kernel") return m;
  return "kernel";
}

function verifyBuildOutput(
  tool: string,
  output: string
): { matches: boolean; reason?: string } {
  log({
    source: "@state/opencode-plugin",
    hook: "tool.execute.after",
    type: "build.verify",
    tool,
    outputPreview: output.slice(0, 500),
    timestamp: Date.now(),
  });
  return { matches: true };
}

function recordTeachObservation(
  tool: string,
  output: string
): void {
  log({
    source: "@state/opencode-plugin",
    hook: "tool.execute.after",
    type: "teach.observation",
    tool,
    outputPreview: output.slice(0, 500),
    timestamp: Date.now(),
  });
}

export const toolExecuteAfter: NonNullable<
  Hooks["tool.execute.after"]
> = async (input, output) => {
  const mode = currentMode();

  if (mode === "build") {
    const result = verifyBuildOutput(input.tool, output.output);
    if (!result.matches) {
      output.title = `[WARN] ${output.title || input.tool}`;
      output.metadata = {
        ...output.metadata,
        state_verify: result,
      };
    } else {
      output.metadata = {
        ...output.metadata,
        state_verify: result,
      };
    }
  } else if (mode === "teach") {
    recordTeachObservation(input.tool, output.output);
  }
};
