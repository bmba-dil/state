/** Chat system transform hook — mode-specific system injection */

import type { Hooks } from "@opencode-ai/plugin";

type StateMode = "build" | "teach" | "kernel";

function currentMode(): StateMode {
  const m = process.env.STATE_MODE;
  if (m === "build" || m === "teach" || m === "kernel") return m;
  return "kernel";
}

const BUILD_BANNER = `[state:build] You are operating in BUILD mode.
Your primary host is the state engine running on opencode.
Follow the project conventions defined in STEP.md and CLAUDE.md.
Every artifact you create must pass the verify contract for the active Step.`;

const TEACH_BANNER = `[state:teach] You are operating in TEACH mode.
Your role is to guide the learner using the active teaching paradigm (PRIMM, Scaffolded, Socratic, or Constructivist).
Never write code for the learner — offer graduated hints and teach prerequisites proactively.`;

export const chatSystemTransform: NonNullable<
  Hooks["experimental.chat.system.transform"]
> = async (input, output) => {
  const mode = currentMode();

  if (mode === "build") {
    output.system.unshift(BUILD_BANNER);
  } else if (mode === "teach") {
    output.system.unshift(TEACH_BANNER);
  }
};
