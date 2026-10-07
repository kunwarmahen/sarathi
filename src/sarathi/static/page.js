// Sarathi's home page: one card per program's page, drawn from /api/pieces.
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
  document.getElementById("updated").textContent =
    `Updated ${new Date().toLocaleTimeString()}`;
}

document.addEventListener("DOMContentLoaded", () => {
  refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, EVERY);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
});
