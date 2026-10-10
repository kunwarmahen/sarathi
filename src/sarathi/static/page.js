// Sarathi's home page: one card per program's page, drawn from /api/pieces,
// and a chat with your agents that passes through to Dvara (/api/chat).
// Every value goes in as text, never as markup. The key arrives after "#",
// is kept in this browser, and leaves the address bar at once. The links
// it draws carry each page's own key, so they open with no referrer.
"use strict";

const KEY = "sarathi.home.token";
const EVERY = 20000;

function keep(token) {
  try { localStorage.setItem(KEY, token); } catch (_) { /* private window */ }
}
function kept() {
  try { return localStorage.getItem(KEY) || ""; } catch (_) { return ""; }
}

function takeToken() {
  const fresh = new URLSearchParams(location.hash.slice(1)).get("token");
  if (fresh) {
    keep(fresh);
    history.replaceState(null, "", location.pathname + location.search);
    return fresh;
  }
  return kept();
}

const token = takeToken();

function h(spec, attrs, ...kids) {
  const [tag, ...classes] = spec.split(".");
  const el = document.createElement(tag || "div");
  if (classes.length) el.className = classes.join(" ");
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v !== undefined && v !== null && v !== false) el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

function card(p) {
  return h("article.card", {},
    h("div.card-head", {}, h("h3", {}, p.title),
      h("span.badge." + (p.up ? "up" : "down"), {}, p.up ? "running" : "not running")),
    h("div.who", {}, p.purpose),
    p.said ? h("div.said", {}, p.said) : null,
    p.up
      ? [h("a.open", { href: p.open, target: "_blank", rel: "noopener noreferrer" },
           `Open ${p.title}`),
         p.keyed ? null : h("div.warn", {}, "Its key wasn't found here: open it from " +
                            "the address its program printed.")]
      : [h("div.meta", {}, "Start it with:"), h("div.cmd", {}, p.start)],
    h("span.ref", {}, p.url));
}

async function refresh() {
  const gate = document.getElementById("gate");
  if (!token) { gate.hidden = false; return; }
  let res;
  try {
    res = await fetch("/api/pieces", { headers: { Authorization: `Bearer ${token}` },
                                       cache: "no-store" });
  } catch (_) {
    document.getElementById("updated").textContent =
      "Couldn't reach Sarathi. Is sarathi home still running?";
    return;
  }
  if (res.status === 401) { gate.hidden = false; return; }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    document.getElementById("updated").textContent = `Couldn't read it: ${body.detail}`;
    return;
  }
  gate.hidden = true;
  const up = body.pieces.filter((p) => p.up).length;
  document.getElementById("facts").replaceChildren(
    h("span", {}, `${up} of ${body.pieces.length} running`));
  document.getElementById("pieces").replaceChildren(...body.pieces.map(card));
  if (body.chat && !chat.on) startChat();
  document.getElementById("updated").textContent =
    `Updated ${new Date().toLocaleTimeString()}`;
}

// ---- the chat -----------------------------------------------------------------
// Lines come from Dvara oldest first, each with an id; the page asks for what
// came after the last one it has. A turn runs in Dvara behind the request, so
// the answer is simply a later line. Questions and held turns are redrawn
// whole on every look: an answer given on Telegram makes them go away here.

const CHAT_EVERY = 3000;
const chat = { on: false, last: 0, timer: null, agents: [], sending: false };

function api(path, body) {
  const init = { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" };
  if (body !== undefined) {
    init.method = "POST";
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  return fetch(path, init).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `status ${res.status}`);
    return data;
  });
}

function problem(text) {
  const el = document.getElementById("chat-problem");
  el.hidden = !text;
  el.textContent = text || "";
}

function when(iso) {
  const d = new Date(iso);
  const today = new Date().toDateString() === d.toDateString();
  return today ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
               : d.toLocaleString([], { month: "short", day: "numeric",
                                         hour: "2-digit", minute: "2-digit" });
}

async function download(line, n, name) {
  try {
    const res = await fetch(`/api/chat/file?line=${line}&n=${n}`,
                            { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.status);
    const url = URL.createObjectURL(await res.blob());
    const a = h("a", { href: url, download: name });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (err) {
    problem(`Couldn't get ${name}: ${err.message}`);
  }
}

function lineView(ln) {
  const failed = ln.who === "agent" && ln.stop_reason && ln.stop_reason !== "held";
  const label = ln.who === "you" ? `You${chat.agents.length > 1 ? " → " + ln.agent : ""}`
    : ln.who === "notice" ? "Sent to you"
    : (ln.agent || "Agent");
  return h(`div.line.${ln.who}${failed ? ".failed" : ""}`, {},
    h("span.tag", {}, `${label} · ${when(ln.at)}`),
    h("div.bubble", {}, ln.text),
    ln.held ? h("span.receipt", {}, "Waiting for your yes, below.") : null,
    ln.receipt ? h("span.receipt", {}, ln.receipt) : null,
    (ln.files || []).map((name, n) => {
      const b = h("button.file", { type: "button" }, `⤓ ${name}`);
      b.addEventListener("click", () => download(ln.id, n, name));
      return b;
    }));
}

function buttons(onYes, onNo, yes = "Yes", no = "No") {
  const y = h("button.yes", { type: "button" }, yes);
  const n = h("button.no", { type: "button" }, no);
  const go = (fn) => async () => {
    y.disabled = n.disabled = true;
    try { await fn(); problem(""); } catch (err) { problem(err.message); }
    look();
  };
  y.addEventListener("click", go(onYes));
  n.addEventListener("click", go(onNo));
  return h("div.buttons", {}, y, n);
}

function askView(a) {
  return h("div.ask", {},
    h("div.q", {}, `${a.agent} asks: may it do this?`),
    h("div.what", {}, `${a.tool}: ${a.summary}`),
    a.picture ? h("img", { src: `data:image/png;base64,${a.picture}`,
                           alt: "The phone's screen, what it would tap ringed" }) : null,
    buttons(() => api(`/api/chat/asks/${encodeURIComponent(a.id)}`, { approve: true }),
            () => api(`/api/chat/asks/${encodeURIComponent(a.id)}`, { approve: false })));
}

function holdView(hd) {
  const all = (v) => Object.fromEntries(hd.calls.map((c) => [c.id, v]));
  const post = (v) => api(`/api/chat/holds/${encodeURIComponent(hd.id)}`, { answers: all(v) });
  return h("div.ask", {},
    h("div.q", {}, `${hd.agent} stopped and is waiting for your yes:`),
    hd.calls.map((c) => h("div.what", {}, `${c.tool}: ${c.summary}`)),
    buttons(() => post(true), () => post(false), "Yes, carry on", "No"));
}

function draw(data) {
  const picker = document.getElementById("agent");
  if (data.agents.join() !== chat.agents.join()) {
    const was = picker.value;
    chat.agents = data.agents;
    picker.replaceChildren(...data.agents.map((a) => h("option", { value: a }, a)));
    if (data.agents.includes(was)) picker.value = was;
    picker.hidden = data.agents.length < 2;
  }
  const box = document.getElementById("lines");
  const atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  if (!chat.last && !data.lines.length) {
    box.replaceChildren(h("div.empty", {}, "Nothing yet. Say hello."));
  } else if (data.lines.length) {
    if (!chat.last) box.replaceChildren();
    box.append(...data.lines.map(lineView));
    chat.last = data.lines[data.lines.length - 1].id;
    if (atEnd || data.lines.some((l) => l.who === "you")) box.scrollTop = box.scrollHeight;
  }
  document.getElementById("waiting").replaceChildren(
    ...data.asks.map(askView), ...data.holds.map(holdView));
  document.getElementById("chat-state").textContent =
    data.busy.length ? `${data.busy.join(", ")} is working…` : "";
}

async function look() {
  try {
    draw(await api(`/api/chat?after=${chat.last}`));
    if (!chat.sending) problem("");
  } catch (err) {
    problem(err.message);
  }
}

async function say(event) {
  event.preventDefault();
  const text = document.getElementById("text");
  const agent = document.getElementById("agent").value;
  if (!text.value.trim() || !agent || chat.sending) return;
  chat.sending = true;
  const send = document.querySelector(".send");
  send.disabled = true;
  try {
    await api("/api/chat", { agent, text: text.value });
    text.value = "";
    problem("");
  } catch (err) {
    problem(err.message);
  } finally {
    chat.sending = false;
    send.disabled = false;
    look();
  }
}

function startChat() {
  chat.on = true;
  document.getElementById("chat").hidden = false;
  document.getElementById("say").addEventListener("submit", say);
  document.getElementById("text").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) say(e);
  });
  look();
  chat.timer = setInterval(() => { if (!document.hidden) look(); }, CHAT_EVERY);
}

document.addEventListener("DOMContentLoaded", () => {
  refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, EVERY);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
});
