// Claude Council front end: plain DOM, no build step.

const $ = (id) => document.getElementById(id);
const state = { conversationId: null, busy: false };

function md(text) {
  return DOMPurify.sanitize(marked.parse(text ?? ""));
}

function el(tag, className, html) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (html !== undefined) node.innerHTML = html;
  return node;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Reviews refer to "Response A" etc.; show the real member names in bold so the
// user can see who said what, while the reviewers themselves never knew.
function deanonymize(text, labelToMember) {
  return Object.entries(labelToMember).reduce(
    (acc, [label, member]) => acc.replaceAll(label, `**${member}** (${label})`),
    text,
  );
}

function servedByNote(reply) {
  return reply.servedBy && reply.servedBy !== reply.model
    ? ` · answered by fallback ${reply.servedBy}`
    : "";
}

function tabbed(items, render) {
  const wrap = el("div");
  const tabs = el("div", "tabs");
  const body = el("div");
  items.forEach((item, i) => {
    const button = el("button", i === 0 ? "active" : "", escapeHtml(item.member));
    button.type = "button";
    button.onclick = () => {
      tabs.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      body.replaceChildren(render(item));
    };
    tabs.append(button);
  });
  if (items.length) body.replaceChildren(render(items[0]));
  wrap.append(tabs, body);
  return wrap;
}

function stageCard(title, className = "") {
  const card = el("section", `stage ${className}`);
  card.append(el("h3", "", title));
  const content = el("div", "loading", "Thinking…");
  card.append(content);
  return { card, content };
}

function renderStage1(content, stage1) {
  content.className = "";
  content.replaceChildren(
    tabbed(stage1, (r) => {
      const div = el("div");
      div.append(el("div", "meta", escapeHtml(r.model + servedByNote(r))));
      div.append(el("div", "markdown", md(r.response)));
      return div;
    }),
  );
}

function renderStage2(content, stage2) {
  content.className = "";
  const board = el("ol", "leaderboard");
  for (const rank of stage2.aggregateRankings) {
    board.append(
      el("li", "", `<strong>${escapeHtml(rank.member)}</strong> — average rank ${rank.averageRank} (${rank.rankingsCount} votes)`),
    );
  }
  content.replaceChildren(
    el("div", "meta", "Aggregate ranking across all reviewers (lower is better)"),
    board,
    tabbed(stage2.reviews, (r) => {
      const div = el("div");
      div.append(el("div", "meta", escapeHtml(`Review by ${r.model}${servedByNote(r)}`)));
      div.append(el("div", "markdown", md(deanonymize(r.response, stage2.labelToMember))));
      return div;
    }),
  );
}

function renderStage3(content, stage3) {
  content.className = "";
  content.replaceChildren(
    el("div", "meta", escapeHtml(stage3.model + servedByNote(stage3))),
    el("div", "markdown", md(stage3.response)),
  );
}

function clearEmptyState() {
  $("messages").querySelector(".empty")?.remove();
}

function renderConversation(conversation) {
  const container = $("messages");
  container.replaceChildren();
  if (!conversation.messages.length) {
    container.append(el("div", "empty", "<h2>Ask the council</h2><p>Your question goes to every member.</p>"));
  }
  for (const msg of conversation.messages) {
    if (msg.role === "user") {
      container.append(el("div", "user-msg", escapeHtml(msg.content)));
      continue;
    }
    const s1 = stageCard("Stage 1 · Individual answers");
    const s2 = stageCard("Stage 2 · Anonymous peer review");
    const s3 = stageCard("Stage 3 · Chairman's answer", "final");
    renderStage1(s1.content, msg.stage1);
    renderStage2(s2.content, msg.stage2);
    renderStage3(s3.content, msg.stage3);
    container.append(s1.card, s2.card, s3.card);
  }
  container.scrollTop = container.scrollHeight;
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

async function refreshList() {
  const list = $("conversation-list");
  list.replaceChildren();
  for (const c of await api("/api/conversations")) {
    const li = el("li", c.id === state.conversationId ? "active" : "", escapeHtml(c.title));
    li.onclick = () => openConversation(c.id);
    list.append(li);
  }
}

async function openConversation(id) {
  if (state.busy) return;
  state.conversationId = id;
  renderConversation(await api(`/api/conversations/${id}`));
  await refreshList();
}

async function newConversation() {
  if (state.busy) return;
  const conversation = await api("/api/conversations", { method: "POST" });
  await openConversation(conversation.id);
  $("input").focus();
}

async function send(content) {
  if (!state.conversationId) {
    const conversation = await api("/api/conversations", { method: "POST" });
    state.conversationId = conversation.id;
  }
  clearEmptyState();
  const container = $("messages");
  container.append(el("div", "user-msg", escapeHtml(content)));
  const stages = {
    stage1: stageCard("Stage 1 · Individual answers"),
    stage2: stageCard("Stage 2 · Anonymous peer review"),
    stage3: stageCard("Stage 3 · Chairman's answer", "final"),
  };
  const renderers = { stage1: renderStage1, stage2: renderStage2, stage3: renderStage3 };

  const res = await fetch(`/api/conversations/${state.conversationId}/message/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop();
    for (const raw of events) {
      if (!raw.startsWith("data: ")) continue;
      const event = JSON.parse(raw.slice(6));
      const [stage, phase] = event.type.split("_");
      if (phase === "start" && stages[stage]) {
        container.append(stages[stage].card);
      } else if (phase === "complete" && stages[stage]) {
        renderers[stage](stages[stage].content, event.data);
      } else if (event.type === "title_complete") {
        await refreshList();
      } else if (event.type === "error") {
        container.append(el("div", "stage error", escapeHtml(`Error: ${event.message}`)));
      }
      container.scrollTop = container.scrollHeight;
    }
  }
  await refreshList();
}

$("composer").addEventListener("submit", async (e) => {
  e.preventDefault();
  const content = $("input").value.trim();
  if (!content || state.busy) return;
  state.busy = true;
  $("send").disabled = true;
  $("input").value = "";
  try {
    await send(content);
  } catch (error) {
    $("messages").append(el("div", "stage error", escapeHtml(String(error))));
  } finally {
    state.busy = false;
    $("send").disabled = false;
  }
});

$("input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("composer").requestSubmit();
  }
});

$("new-conversation").onclick = newConversation;

api("/api/council").then(({ members, chairman }) => {
  $("roster").textContent = `Members: ${members.map((m) => m.name).join(", ")} · Chair: ${chairman.model}`;
});
refreshList();
