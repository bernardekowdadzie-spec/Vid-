// 3-stage Claude Council orchestration.

import { CHAIRMAN, COUNCIL_MEMBERS, TITLE_MODEL } from "./config.ts";
import { queryMember, type MemberReply } from "./claude.ts";

export interface Review extends MemberReply {
  /** Labels in ranked order, e.g. ["Response B", "Response A"]. */
  parsedRanking: string[];
}

export interface AggregateRank {
  member: string;
  averageRank: number;
  rankingsCount: number;
}

export interface Stage2Result {
  reviews: Review[];
  /** "Response A" -> member name. Revealed to the user, never to reviewers. */
  labelToMember: Record<string, string>;
  aggregateRankings: AggregateRank[];
}

async function askAll(prompt: string): Promise<MemberReply[]> {
  const replies = await Promise.all(COUNCIL_MEMBERS.map((m) => queryMember(m, prompt)));
  return replies.filter((r): r is MemberReply => r !== null);
}

/** Stage 1: every member answers the question independently. */
export async function stage1CollectResponses(query: string): Promise<MemberReply[]> {
  return askAll(query);
}

/** Stage 2: every member reviews and ranks the anonymized answers. */
export async function stage2CollectRankings(
  query: string,
  stage1: MemberReply[],
): Promise<Stage2Result> {
  const labels = stage1.map((_, i) => `Response ${String.fromCharCode(65 + i)}`);
  const labelToMember = Object.fromEntries(labels.map((label, i) => [label, stage1[i].member]));
  const responsesText = stage1
    .map((r, i) => `<response label="${labels[i]}">\n${r.response}\n</response>`)
    .join("\n\n");

  const prompt = `You are reviewing several anonymous answers to the same question. One of them may be your own; judge them on merit alone.

<question>
${query}
</question>

${responsesText}

For each response, say briefly what it gets right and what it gets wrong or misses - accuracy first, then insight, then clarity.

End with a ranking from best to worst in exactly this format, with nothing after it:

FINAL RANKING:
1. Response X
2. Response Y
...`;

  const replies = await askAll(prompt);
  const reviews = replies.map((r) => ({ ...r, parsedRanking: parseRanking(r.response) }));
  return {
    reviews,
    labelToMember,
    aggregateRankings: aggregateRankings(reviews, labelToMember),
  };
}

/** Stage 3: the chairman synthesizes one final answer. */
export async function stage3Synthesize(
  query: string,
  stage1: MemberReply[],
  stage2: Stage2Result,
): Promise<MemberReply> {
  const answers = stage1
    .map((r) => `<answer member="${r.member}">\n${r.response}\n</answer>`)
    .join("\n\n");
  const reviews = stage2.reviews
    .map((r) => `<review reviewer="${r.member}">\n${r.response}\n</review>`)
    .join("\n\n");
  const legend = Object.entries(stage2.labelToMember)
    .map(([label, member]) => `${label} = ${member}`)
    .join(", ");

  const prompt = `You chair a council of Claude models. Each member answered the user's question, then all members reviewed the anonymized answers (${legend}).

<question>
${query}
</question>

${answers}

${reviews}

Write the single best answer to the user's question. Draw on the strongest points across the answers, resolve disagreements using the reviews and your own judgment, and drop anything the reviews showed to be wrong. Address the user directly; don't describe the council process unless the members disagreed in a way the user should know about.`;

  const reply = await queryMember(CHAIRMAN, prompt, 64000);
  return (
    reply ?? {
      member: CHAIRMAN.name,
      model: CHAIRMAN.model,
      servedBy: CHAIRMAN.model,
      response: "Error: the chairman could not produce a final answer.",
    }
  );
}

/** Extract ranked labels from the FINAL RANKING section of a review. */
export function parseRanking(text: string): string[] {
  const idx = text.lastIndexOf("FINAL RANKING:");
  const section = idx >= 0 ? text.slice(idx) : text;
  const numbered = [...section.matchAll(/\d+\.\s*(Response [A-Z])/g)].map((m) => m[1]);
  const labels = numbered.length > 0 ? numbered : [...section.matchAll(/Response [A-Z]/g)].map((m) => m[0]);
  return [...new Set(labels)];
}

/** Average each member's position across all reviews (lower is better). */
export function aggregateRankings(
  reviews: Pick<Review, "parsedRanking">[],
  labelToMember: Record<string, string>,
): AggregateRank[] {
  const positions = new Map<string, number[]>();
  for (const review of reviews) {
    review.parsedRanking.forEach((label, i) => {
      const member = labelToMember[label];
      if (!member) return;
      positions.set(member, [...(positions.get(member) ?? []), i + 1]);
    });
  }
  return [...positions.entries()]
    .map(([member, ps]) => ({
      member,
      averageRank: Math.round((ps.reduce((a, b) => a + b, 0) / ps.length) * 100) / 100,
      rankingsCount: ps.length,
    }))
    .sort((a, b) => a.averageRank - b.averageRank);
}

export async function generateTitle(query: string): Promise<string> {
  const reply = await queryMember(
    TITLE_MODEL,
    `Write a title of at most five words for a conversation that starts with the question below. Reply with the title only, no quotes or trailing punctuation.\n\n<question>\n${query}\n</question>`,
    1024,
  );
  const title = reply?.response.trim().replace(/^["']|["']$/g, "") || "New Conversation";
  return title.length > 50 ? `${title.slice(0, 47)}...` : title;
}
