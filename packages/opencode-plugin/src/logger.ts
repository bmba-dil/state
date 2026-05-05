/** Shared logger — gated behind STATE_DEBUG for production suppression */
const DEBUG = process.env.STATE_DEBUG === "1";

export interface LogData {
  [key: string]: unknown;
}

export function log(data: LogData): void {
  if (!DEBUG) return;
  console.log(JSON.stringify(data));
}
