/** Command execute before hook — mode gate for slash commands */

import type { Hooks } from "@opencode-ai/plugin";
import type { Part } from "@opencode-ai/sdk";
import { log } from "../logger.js";

type StateMode = "build" | "teach" | "kernel";

const STATE_COMMAND_RE = /^\/state:(build|teach):/;

function currentMode(): StateMode {
  const m = process.env.STATE_MODE;
  if (m === "build" || m === "teach" || m === "kernel") return m;
  return "kernel";
}

function createTextPart(text: string): Part {
  return {
    id: `state-command-${Date.now()}`,
    sessionID: "state",
    messageID: "state",
    type: "text",
    text,
    time: { start: Date.now() },
    metadata: { source: "@state/opencode-plugin" },
  } as Part;
}

export const commandExecuteBefore: NonNullable<
  Hooks["command.execute.before"]
> = async (input, output) => {
  const mode = currentMode();
  if (mode === "kernel") return;

  const match = input.command.match(STATE_COMMAND_RE);
  if (!match) return;

  const [, commandMode] = match;

  if (commandMode !== mode) {
    output.parts.push(
      createTextPart(
        `[state] Cross-mode command blocked: ${input.command} is not allowed in ${mode} mode.`
      )
    );
    return;
  }

  log({
    source: "@state/opencode-plugin",
    hook: "command.execute.before",
    type: "command.gated",
    command: input.command,
    mode,
    timestamp: Date.now(),
  });
};
