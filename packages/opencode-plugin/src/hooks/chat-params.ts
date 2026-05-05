/** Chat params + headers hook — profile + cache-control injection */

import type { Hooks } from "@opencode-ai/plugin";

type ProfileName = "quality" | "balanced" | "budget";

interface ProfileConfig {
  temperature: number;
  topP: number;
  topK: number;
  maxOutputTokens: number;
  thinkingBudget: number;
}

const PROFILES: Record<ProfileName, ProfileConfig> = {
  quality: {
    temperature: 0.3,
    topP: 1.0,
    topK: 40,
    maxOutputTokens: 64000,
    thinkingBudget: 32000,
  },
  balanced: {
    temperature: 0.7,
    topP: 0.95,
    topK: 50,
    maxOutputTokens: 32000,
    thinkingBudget: 16000,
  },
  budget: {
    temperature: 0.9,
    topP: 0.9,
    topK: 60,
    maxOutputTokens: 16000,
    thinkingBudget: 0,
  },
};

function resolveProfile(): ProfileName {
  const profile = process.env.STATE_MODEL_PROFILE;
  if (profile === "quality" || profile === "balanced" || profile === "budget") {
    return profile;
  }
  return "balanced";
}

export const chatParams: NonNullable<Hooks["chat.params"]> = async (
  input,
  output
) => {
  const profile = resolveProfile();
  const config = PROFILES[profile];

  output.temperature = config.temperature;
  output.topP = config.topP;
  output.topK = config.topK;
  output.maxOutputTokens = config.maxOutputTokens;

  output.options = {
    ...output.options,
    state_profile: profile,
    state_thinking_budget: config.thinkingBudget,
  };
};

export const chatHeaders: NonNullable<Hooks["chat.headers"]> = async (
  input,
  output
) => {
  const profile = resolveProfile();
  const config = PROFILES[profile];

  output.headers = {
    ...output.headers,
    "X-State-Profile": profile,
    "X-State-Thinking-Budget": String(config.thinkingBudget),
    "X-State-Version": "v8",
  };
};
