/** Shell env hook — STATE_* env var injection */

import type { Hooks } from "@opencode-ai/plugin";

const STATE_ENV_VARS = [
  "STATE_ARC",
  "STATE_PHASE",
  "STATE_SLICE",
  "STATE_STEP",
  "STATE_WORKTREE",
  "STATE_DAEMON_URL",
  "STATE_AUTH_JSON",
];

export const shellEnv: NonNullable<Hooks["shell.env"]> = async (
  input,
  output
) => {
  for (const key of STATE_ENV_VARS) {
    const val = process.env[key];
    if (val !== undefined) {
      output.env[key] = val;
    }
  }

  if (!output.env.STATE_DAEMON_URL) {
    output.env.STATE_DAEMON_URL =
      process.env.STATE_DAEMON_URL || "http://localhost:9337";
  }

  if (!output.env.STATE_AUTH_JSON) {
    output.env.STATE_AUTH_JSON =
      process.env.STATE_AUTH_JSON || ".state/auth.json";
  }
};
