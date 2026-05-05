/** Session compacting hook — phase-aware compaction */

import type { Hooks } from "@opencode-ai/plugin";

export const sessionCompacting: NonNullable<
  Hooks["experimental.session.compacting"]
> = async (input, output) => {
  const activeStepID = process.env.STATE_STEP || "";
  const activeSliceID = process.env.STATE_SLICE || "";
  const activePhase = process.env.STATE_PHASE || "";

  const preserve: string[] = [];

  if (activeStepID) {
    preserve.push(
      `ACTIVE_STEP: ${activeStepID} — preserve all context related to this Step.`
    );
  }
  if (activeSliceID) {
    preserve.push(
      `ACTIVE_SLICE: ${activeSliceID} — preserve Slice boundary context.`
    );
  }
  if (activePhase) {
    preserve.push(
      `ACTIVE_PHASE: ${activePhase} — preserve open gray-area decisions.`
    );
  }

  preserve.push(
    "PRESERVE: last 3 verify results, open gray-area items, pending drills."
  );

  output.context = [...preserve, ...output.context];
};
