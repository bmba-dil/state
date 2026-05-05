/** Minimal stub — failing tests will drive implementation */
import { Box, Text, createTextAttributes } from "@opentui/core";
import type { TuiPluginApi } from "@opencode-ai/plugin/tui";
import type { EventSessionStatus } from "@opencode-ai/sdk/v2";

export type ConnectionStatus = "connected" | "disconnected" | "unreachable";
export type KolbStage = "concrete_experience" | "reflective_observation" | "abstract_conceptualization" | "active_experimentation";

export interface ConceptData {
  name: string;
  description: string;
  stage: KolbStage;
  mastery: number;
}

export interface TeachConceptState {
  connection: ConnectionStatus;
  concept: ConceptData | null;
}

export const TEACH_CONCEPT_STATE: TeachConceptState = {
  connection: "unreachable",
  concept: null,
};

export function kolbStageLabel(_stage: KolbStage): string {
  return ""; // STUB — will be replaced in GREEN phase
}

export function masteryBar(_score: number): string {
  return ""; // STUB — will be replaced in GREEN phase
}

export function renderTeachConcept(): ReturnType<typeof Box> {
  return Box({}); // STUB — will be replaced in GREEN phase
}

export function setupTeachConcept(_api: TuiPluginApi): void {
  // STUB — will be replaced in GREEN phase
}
