// Configuration for the Claude Council.

export type Effort = "low" | "medium" | "high" | "xhigh" | "max";

export interface CouncilMember {
  /** Display name shown in the UI and given to the chairman. */
  name: string;
  /** Claude model ID. */
  model: string;
  effort: Effort;
  /**
   * Opt into server-side refusal fallbacks (`fallbacks: "default"`). Supported
   * on Opus 5.5 / Sonnet 5.5 on the Claude API; Haiku 5.5 has no fallback.
   */
  fallbacks: boolean;
}

// The council: three Claude tiers answer the question independently and then
// review each other. Different tiers think differently, which is the point.
export const COUNCIL_MEMBERS: CouncilMember[] = [
  { name: "Opus", model: "claude-opus-5-5", effort: "high", fallbacks: true },
  { name: "Sonnet", model: "claude-sonnet-5-5", effort: "high", fallbacks: true },
  { name: "Haiku", model: "claude-haiku-5-5", effort: "high", fallbacks: false },
];

// The chairman reads every answer and every review, then writes the final one.
export const CHAIRMAN: CouncilMember = {
  name: "Chairman (Opus)",
  model: "claude-opus-5-5",
  effort: "high",
  fallbacks: true,
};

// Cheap, fast model for conversation titles.
export const TITLE_MODEL: CouncilMember = {
  name: "Titler",
  model: "claude-haiku-5-5",
  effort: "low",
  fallbacks: false,
};

export const PORT = Number(process.env.PORT ?? 8001);

// Conversations are stored as JSON files here.
export const DATA_DIR = process.env.DATA_DIR ?? "data/conversations";
