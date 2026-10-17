# Claude Council

A council made only of Claude models, based on Karpathy's [llm-council](https://github.com/karpathy/llm-council). That project sends one question to GPT, Gemini, Claude and Grok through OpenRouter. This one calls the Anthropic API directly and seats three Claude models of different sizes:

| Seat     | Model               | Effort |
| -------- | ------------------- | ------ |
| Opus     | `claude-opus-5-5`   | high   |
| Sonnet   | `claude-sonnet-5-5` | high   |
| Haiku    | `claude-haiku-5-5`  | high   |
| Chairman | `claude-opus-5-5`   | high   |

When you ask a question:

1. **Individual answers.** Each member answers on its own, in parallel. You can read every answer in a tab.
2. **Anonymous peer review.** Each member gets all the answers labelled only "Response A/B/C", critiques them, and ranks them. The UI shows the real names and an average rank for each member.
3. **Final answer.** The chairman reads every answer and every review, then writes one final answer.

## Setup

Requires Node.js 22 or newer.

```bash
cd claude-council
npm install
export ANTHROPIC_API_KEY=sk-ant-...   # or sign in with `ant auth login`
npm start
```

Then open http://localhost:8001.

## Configuration

Edit `src/config.ts` to change who sits on the council, which model chairs it, and the effort level for each seat. You can add or remove members; the review labels adjust to fit.

Every call uses adaptive thinking and streams in the background, so long answers at high effort don't hit request timeouts. Opus and Sonnet have server-side refusal fallbacks turned on (`fallbacks: "default"`). If a safety classifier wrongly declines a question, the API reruns it on a fallback model. When that happens the UI shows which model actually answered. Haiku has no fallback, so if it declines, the council goes ahead without it.

Environment variables: `PORT` (default `8001`) and `DATA_DIR` (default `data/conversations`).

## Cost

Each question makes 8 API calls: 3 answers, 3 reviews, 1 chairman call, plus 1 Haiku call to title a new conversation. The review and chairman prompts include every answer, so they are the most expensive calls. To spend less, lower `effort` in `src/config.ts` or remove a seat.

## Notes

- As in the original, each question goes to the council fresh. Earlier turns of the conversation are saved and shown, but not sent to the models.
- Conversations are saved as JSON in `data/conversations/`, which git ignores.
- `npm test` runs the ranking-parser tests. `npm run typecheck` runs `tsc`.
