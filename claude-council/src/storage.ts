// JSON-file storage for conversations.

import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { DATA_DIR } from "./config.ts";
import type { MemberReply } from "./claude.ts";
import type { Stage2Result } from "./council.ts";

export type Message =
  | { role: "user"; content: string }
  | { role: "assistant"; stage1: MemberReply[]; stage2: Stage2Result; stage3: MemberReply };

export interface Conversation {
  id: string;
  createdAt: string;
  title: string;
  messages: Message[];
}

const ID_PATTERN = /^[0-9a-f-]{36}$/;

function filePath(id: string): string {
  if (!ID_PATTERN.test(id)) throw new Error("invalid conversation id");
  return path.join(DATA_DIR, `${id}.json`);
}

export async function createConversation(id: string): Promise<Conversation> {
  const conversation = { id, createdAt: new Date().toISOString(), title: "New Conversation", messages: [] };
  await saveConversation(conversation);
  return conversation;
}

export async function getConversation(id: string): Promise<Conversation | null> {
  try {
    return JSON.parse(await readFile(filePath(id), "utf8")) as Conversation;
  } catch {
    return null;
  }
}

export async function saveConversation(conversation: Conversation): Promise<void> {
  await mkdir(DATA_DIR, { recursive: true });
  await writeFile(filePath(conversation.id), JSON.stringify(conversation, null, 2));
}

export async function listConversations() {
  await mkdir(DATA_DIR, { recursive: true });
  const files = (await readdir(DATA_DIR)).filter((f) => f.endsWith(".json"));
  const conversations = await Promise.all(files.map((f) => getConversation(f.slice(0, -5))));
  return conversations
    .filter((c): c is Conversation => c !== null)
    .map(({ id, createdAt, title, messages }) => ({ id, createdAt, title, messageCount: messages.length }))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}
