// HTTP server: serves the UI from public/ and a small JSON + SSE API.

import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { readFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { CHAIRMAN, COUNCIL_MEMBERS, PORT } from "./config.ts";
import { generateTitle, stage1CollectResponses, stage2CollectRankings, stage3Synthesize } from "./council.ts";
import { createConversation, getConversation, listConversations, saveConversation } from "./storage.ts";

const PUBLIC_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "public");
const ROOT_DIR = path.join(PUBLIC_DIR, "..");
// URL path -> [file on disk, content type]. Markdown libraries come from node_modules.
const STATIC_FILES: Record<string, [string, string]> = {
  "/": [path.join(PUBLIC_DIR, "index.html"), "text/html"],
  "/app.js": [path.join(PUBLIC_DIR, "app.js"), "text/javascript"],
  "/style.css": [path.join(PUBLIC_DIR, "style.css"), "text/css"],
  "/vendor/marked.js": [path.join(ROOT_DIR, "node_modules/marked/lib/marked.umd.js"), "text/javascript"],
  "/vendor/purify.js": [path.join(ROOT_DIR, "node_modules/dompurify/dist/purify.min.js"), "text/javascript"],
};

function sendJson(res: ServerResponse, status: number, body: unknown) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

async function readBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {};
}

async function streamCouncil(res: ServerResponse, conversationId: string, content: string) {
  const conversation = await getConversation(conversationId);
  if (!conversation) return sendJson(res, 404, { error: "Conversation not found" });

  res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
  const send = (event: Record<string, unknown>) => res.write(`data: ${JSON.stringify(event)}\n\n`);

  try {
    const titlePromise = conversation.messages.length === 0 ? generateTitle(content) : null;
    conversation.messages.push({ role: "user", content });
    await saveConversation(conversation);

    send({ type: "stage1_start" });
    const stage1 = await stage1CollectResponses(content);
    if (stage1.length === 0) throw new Error("Every council member failed to respond. Check the server log.");
    send({ type: "stage1_complete", data: stage1 });

    send({ type: "stage2_start" });
    const stage2 = await stage2CollectRankings(content, stage1);
    send({ type: "stage2_complete", data: stage2 });

    send({ type: "stage3_start" });
    const stage3 = await stage3Synthesize(content, stage1, stage2);
    send({ type: "stage3_complete", data: stage3 });

    if (titlePromise) {
      conversation.title = await titlePromise;
      send({ type: "title_complete", data: { title: conversation.title } });
    }
    conversation.messages.push({ role: "assistant", stage1, stage2, stage3 });
    await saveConversation(conversation);
    send({ type: "complete" });
  } catch (error) {
    send({ type: "error", message: error instanceof Error ? error.message : String(error) });
  }
  res.end();
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", "http://localhost");
  const parts = url.pathname.split("/").filter(Boolean);

  try {
    if (req.method === "GET" && Object.hasOwn(STATIC_FILES, url.pathname)) {
      const [file, contentType] = STATIC_FILES[url.pathname];
      res.writeHead(200, { "Content-Type": `${contentType}; charset=utf-8` });
      return res.end(await readFile(file));
    }
    if (req.method === "GET" && url.pathname === "/api/council") {
      return sendJson(res, 200, { members: COUNCIL_MEMBERS, chairman: CHAIRMAN });
    }
    if (url.pathname === "/api/conversations") {
      if (req.method === "GET") return sendJson(res, 200, await listConversations());
      if (req.method === "POST") return sendJson(res, 200, await createConversation(randomUUID()));
    }
    if (parts[0] === "api" && parts[1] === "conversations" && parts[2]) {
      const id = parts[2];
      if (req.method === "GET" && parts.length === 3) {
        const conversation = await getConversation(id);
        return conversation ? sendJson(res, 200, conversation) : sendJson(res, 404, { error: "Conversation not found" });
      }
      if (req.method === "POST" && parts[3] === "message" && parts[4] === "stream") {
        const { content } = await readBody(req);
        if (typeof content !== "string" || !content.trim()) return sendJson(res, 400, { error: "content is required" });
        return await streamCouncil(res, id, content);
      }
    }
    sendJson(res, 404, { error: "Not found" });
  } catch (error) {
    console.error(error);
    if (!res.headersSent) sendJson(res, 500, { error: "Internal server error" });
    else res.end();
  }
});

server.listen(PORT, () => {
  console.log(`Claude Council running at http://localhost:${PORT}`);
  console.log(`Members: ${COUNCIL_MEMBERS.map((m) => `${m.name} (${m.model})`).join(", ")}; chairman: ${CHAIRMAN.model}`);
});
