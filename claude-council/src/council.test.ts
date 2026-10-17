import { test } from "node:test";
import assert from "node:assert/strict";
import { aggregateRankings, parseRanking } from "./council.ts";

test("parseRanking reads the FINAL RANKING section", () => {
  const text = `Response A is solid. Response C is weak.

FINAL RANKING:
1. Response B
2. Response A
3. Response C`;
  assert.deepEqual(parseRanking(text), ["Response B", "Response A", "Response C"]);
});

test("parseRanking falls back to labels in order when unnumbered", () => {
  assert.deepEqual(parseRanking("FINAL RANKING: Response C, Response A"), ["Response C", "Response A"]);
});

test("aggregateRankings averages positions and sorts best first", () => {
  const labelToMember = { "Response A": "Opus", "Response B": "Sonnet", "Response C": "Haiku" };
  const result = aggregateRankings(
    [
      { parsedRanking: ["Response A", "Response B", "Response C"] },
      { parsedRanking: ["Response B", "Response A", "Response C"] },
      { parsedRanking: ["Response A", "Response C", "Response B"] },
    ],
    labelToMember,
  );
  assert.deepEqual(result, [
    { member: "Opus", averageRank: 1.33, rankingsCount: 3 },
    { member: "Sonnet", averageRank: 2, rankingsCount: 3 },
    { member: "Haiku", averageRank: 2.67, rankingsCount: 3 },
  ]);
});
