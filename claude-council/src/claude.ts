// Thin wrapper around the Anthropic SDK for querying one council member.

import Anthropic from "@anthropic-ai/sdk";
import type { CouncilMember } from "./config.ts";

// Resolves credentials from ANTHROPIC_API_KEY (or an `ant auth login` profile).
const client = new Anthropic();

const FALLBACK_BETA = "server-side-fallback-2026-07-01";

export interface MemberReply {
  member: string;
  model: string;
  /** Model that actually produced the reply (differs when a fallback ran). */
  servedBy: string;
  response: string;
}

/**
 * Ask one member a single-turn question. Streams under the hood so long,
 * high-effort answers don't hit HTTP timeouts. Returns null on failure so one
 * failing member doesn't sink the whole council.
 */
export async function queryMember(
  member: CouncilMember,
  prompt: string,
  maxTokens = 32000,
): Promise<MemberReply | null> {
  try {
    const stream = client.beta.messages.stream({
      model: member.model,
      max_tokens: maxTokens,
      thinking: { type: "adaptive" },
      output_config: { effort: member.effort },
      messages: [{ role: "user", content: prompt }],
      ...(member.fallbacks ? { betas: [FALLBACK_BETA], fallbacks: "default" as const } : {}),
    });
    const message = await stream.finalMessage();

    if (message.stop_reason === "refusal") {
      const category = message.stop_details?.category ?? "unspecified";
      console.warn(`${member.name} declined (category: ${category})`);
      return null;
    }

    const text = message.content
      .flatMap((block) => (block.type === "text" ? [block.text] : []))
      .join("");
    return { member: member.name, model: member.model, servedBy: message.model, response: text };
  } catch (error) {
    if (error instanceof Anthropic.AuthenticationError) {
      console.error(`${member.name}: authentication failed - is ANTHROPIC_API_KEY set?`);
    } else if (error instanceof Anthropic.RateLimitError) {
      console.error(`${member.name}: rate limited`);
    } else if (error instanceof Anthropic.APIError) {
      console.error(`${member.name}: API error ${error.status}: ${error.message}`);
    } else {
      console.error(`${member.name}:`, error);
    }
    return null;
  }
}
