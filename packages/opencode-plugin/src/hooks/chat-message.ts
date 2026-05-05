/** Chat message hook — command parsing, mode gating, context injection */

import type { Hooks } from "@opencode-ai/plugin";
import type { Part, UserMessage } from "@opencode-ai/sdk";
import { log } from "../logger.js";

type StateMode = "build" | "teach" | "kernel";

interface ParsedCommand {
  mode: StateMode;
  namespace: string;
  command: string;
}

const STATE_COMMAND_RE = /^\/state:(build|teach)(?::(\w[\w-]*))?(?::(\w[\w-]*))?/;

function parseStateCommand(text: string): ParsedCommand | null {
  const match = text.match(STATE_COMMAND_RE);
  if (!match) return null;
  const [, mode, namespace, command] = match;
  if (mode !== "build" && mode !== "teach") return null;
  return {
    mode: mode as StateMode,
    namespace: namespace || "",
    command: command || "",
  };
}

function detectCurrentMode(): StateMode {
  const envMode = process.env.STATE_MODE;
  if (envMode === "build" || envMode === "teach" || envMode === "kernel") {
    return envMode;
  }
  return "kernel";
}

function createTextPart(text: string, message: UserMessage): Part {
  return {
    id: `state-hint-${Date.now()}`,
    sessionID: message.sessionID,
    messageID: message.id,
    type: "text",
    text,
    time: { start: Date.now() },
    metadata: { source: "@state/opencode-plugin" },
  } as Part;
}

function injectBuildHint(parts: Part[], message: UserMessage): void {
  const hint = createTextPart(
    "[state:build] Active Step hint — mode is build, state context will be injected when daemon is available.",
    message
  );
  parts.push(hint);
}

function recordTeachObservation(text: string): void {
  log({
    source: "@state/opencode-plugin",
    hook: "chat.message",
    type: "observation",
    mode: "teach",
    text: text.slice(0, 200),
    timestamp: Date.now(),
  });
}

export const chatMessage: NonNullable<Hooks["chat.message"]> = async (
  input,
  output
) => {
  const text = output.message.summary?.body || "";
  if (!text) return;

  const parsed = parseStateCommand(text);
  if (!parsed) return;

  const currentMode = detectCurrentMode();

  if (currentMode !== "kernel" && parsed.mode !== currentMode) {
    const rejection = createTextPart(
      `[state] Cross-mode command rejected: /state:${parsed.mode}:${parsed.namespace}${parsed.command ? `:${parsed.command}` : ""} is not allowed in ${currentMode} mode.`,
      output.message
    );
    output.parts.push(rejection);
    return;
  }

  if (parsed.mode === "build") {
    injectBuildHint(output.parts, output.message);
  } else if (parsed.mode === "teach") {
    recordTeachObservation(text);
  }
};
