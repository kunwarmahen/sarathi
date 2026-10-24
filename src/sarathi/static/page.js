// Sarathi's home page: one card per program's page, drawn from /api/pieces,
// and a chat with your agents that passes through to Dvara (/api/chat).
// Every value goes in as text, never as markup. The owner's key arrives
// after "#token=", is kept in this browser, and leaves the address bar at
// once. The links it draws carry each page's own key, so they open with no
// referrer. Someone else in the house signs in instead (an invite link,
// "#invite=", once; then their name and password) and gets their own chat,
// nothing else: the server holds that line, this script only draws it.
// The chat is the page; Your pages and Settings are views of their own,
// behind the icons at the top, each at its own address (#pages, #settings)
// so a reload stays put.
"use strict";

const KEY = "sarathi.home.token";
const SESSION = "sarathi.home.session";
const EVERY = 20000;
const VIEWS = ["chat", "pages", "settings"];

function keep(name, value) {
  try {
    if (value) localStorage.setItem(name, value); else localStorage.removeItem(name);
  } catch (_) { /* private window */ }
}
function kept(name) {
  try { return localStorage.getItem(name) || ""; } catch (_) { return ""; }
}

// "#token=" (the owner) or "#invite=" (a person's one-time link), taken
// from the address bar at once either way.
function takeHash() {
  const hash = new URLSearchParams(location.hash.slice(1));
  const fresh = hash.get("token");
  const invite = hash.get("invite") || "";
  if (fresh || invite) {
    // a view asked for alongside the key ("#settings&token=…") is kept
    const view = VIEWS.find((v) => hash.has(v));
    history.replaceState(null, "", location.pathname + location.search + (view ? `#${view}` : ""));
  }
  if (fresh) keep(KEY, fresh);
  return invite;
}

const invite = takeHash();
// the owner's key first: on the owner's own browser it opens everything
let token = kept(KEY) || kept(SESSION);
let me = null;
let invited = false;     // the invite on this address has been used, here

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

// Where your memories are kept: Yantra's own file, or Smritikosh. Its one
// button is `sarathi smritikosh` (or --off) once Smritikosh is set up.
const memory = { busy: false, said: "" };

function memoryCard(m) {
  const kosh = m.via === "smritikosh";
  const badge = kosh ? (m.up ? ["up", "Smritikosh"] : ["down", "Smritikosh, not answering"])
                     : ["up", "built-in file"];
  const count = h("div.meta", {}, "The list itself is on Yantra's page, under the bookmark.");
  let action;
  if (kosh || m.set_up) {
    const to = kosh ? "local" : "smritikosh";
    action = h("button.open", { type: "button", disabled: memory.busy },
               kosh ? "Back to the built-in file" : "Switch to Smritikosh");
    action.addEventListener("click", () => switchMemory(to));
  } else {
    action = [h("div.meta", {}, "Set up Smritikosh, which finds a memory by meaning, " +
                "once, in a terminal:"), h("div.cmd", {}, "sarathi smritikosh")];
  }
  const dash = m.dashboard;
  const portal = !dash ? null : dash.up
    ? [h("a.open", { href: dash.url, target: "_blank", rel: "noopener noreferrer" },
         "Open Smritikosh's dashboard"),
       h("div.meta", {}, "Sign in with your Smritikosh username and password.")]
    : h("div.meta", {}, `Smritikosh's dashboard isn't running: ${dash.start.replace(/`/g, "")}.`);
  return h("article.card", {},
    h("div.card-head", {}, h("h3", {}, "Memory"),
      h("span.badge." + badge[0], {}, badge[1])),
    h("div.who", {}, "What your agents remember about you, and where it is kept."),
    m.said ? h("div.said", {}, m.said) : null,
    count, action,
    memory.said ? h("div.meta", { role: "status" }, memory.said) : null,
    portal,
    m.server ? h("span.ref", {}, m.server) : null,
    dash ? h("span.ref", {}, dash.url) : null);
}

// Your kept tests: conversations kept as tests (Yantra's note 141),
// replayed by Samay's tests road each night. The card says the last
// night (Yantra's last.json) and offers the night run once.
const tests = { busy: false, said: "" };

function testsCard(t, yantra) {
  const night = t.summary;
  let badge = ["down", "none kept yet"];
  if (night && night.suites.length) {
    badge = night.errors ? ["down", "couldn't run"]
      : night.broke ? ["down", `${night.broke} broke`]
      : [night.green ? "up" : "down", `${night.passed} of ${night.cases} passed`];
  } else if (t.suites) badge = ["down", "not run yet"];
  const lines = [];
  if (night && night.suites.length) {
    lines.push(h("div.said", {}, `Last run ${new Date(night.at).toLocaleString()}: `
      + `${night.passed} of ${night.cases} passed`
      + (night.broke ? `, ${night.broke} broke since the run before` : "")
      + (night.fixed ? `, ${night.fixed} fixed` : "") + "."));
    for (const row of night.suites) {
      const whose = row.person ? `${row.person}'s ${row.agent}` : row.agent;
      if (row.error) lines.push(h("div.warn", {}, `${whose}: couldn't run — ${row.error}`));
      else if (row.broke.length) lines.push(h("div.warn", {}, `${whose}: broke ${row.broke.join(", ")}`));
      else if (row.red.length) lines.push(h("div.meta", {}, `${whose}: still red ${row.red.join(", ")}`));
    }
  }
  let action = null;
  if (t.nightly) {
    action = h("div.meta", {}, "Samay replays them every night; you hear only when one breaks.");
  } else if (t.clock_on && t.samay) {
    action = h("button.open", { type: "button", disabled: tests.busy }, "Run them every night");
    action.addEventListener("click", askNightly);
  } else if (t.clock_on) {
    action = h("div.meta", {}, "Samay isn't answering, so the night run can't be set yet.");
  } else {
    action = h("div.meta", {}, "Turn Samay on in Settings to run them every night.");
  }
  return h("article.card", {},
    h("div.card-head", {}, h("h3", {}, "Kept tests"),
      h("span.badge." + badge[0], {}, badge[1])),
    h("div.who", {}, "Conversations that went well, asked again with the tools answering "
      + "from what they said then — so a new model or prompt can't quietly break them."),
    ...lines,
    t.suites ? null : h("div.meta", {}, "Keep one from History on Yantra's page, or send "
      + "/keep test in a chat."),
    action,
    // the list itself, with delete, is Yantra's: its tests, its page
    t.suites && yantra && yantra.up
      ? h("a.open", { href: yantra.open + "#tests", target: "_blank",
                      rel: "noopener noreferrer" }, "See and delete them on Yantra's page")
      : null,
    tests.said ? h("div.meta", { role: "status" }, tests.said) : null);
}

async function askNightly() {
  tests.busy = true;
  refresh();
  try {
    tests.said = (await api("/api/tests/nightly", {})).said;
  } catch (err) {
    tests.said = err.message;
  }
  tests.busy = false;
  refresh();
}

async function switchMemory(via) {
  memory.busy = true;
  memory.said = "Switching…";
  refresh();
  try {
    const done = await api("/api/memory", { via });
    memory.said = done.said;
  } catch (err) {
    memory.said = err.message;
  }
  memory.busy = false;
  refresh();
}

function show(id, on) { document.getElementById(id).hidden = !on; }

// ---- the three views -----------------------------------------------------------
// Each section keeps its own `hidden` (whether there is anything to show);
// which view is on is body[data-view], read by the stylesheet. Someone in
// the house has only the chat; the owner with Dvara off has no chat, so
// their page opens on Your pages instead.

function wantedView() {
  const asked = location.hash.slice(1);
  return VIEWS.includes(asked) ? asked : "chat";
}

function drawView() {
  if (!me) {
    document.body.dataset.view = "signin";
    show("views", false);
    return;
  }
  let view = me.owner ? wantedView() : "chat";
  if (view === "chat" && me.owner && !chat.on) view = "pages";
  const was = document.body.dataset.view;
  document.body.dataset.view = view;
  show("views", me.owner);
  for (const a of document.querySelectorAll(".view-icon")) {
    if (a.dataset.view === view) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
    a.hidden = a.dataset.view === "chat" && !chat.on;
  }
  // with no chat there is nothing to go back to
  show("back-row", view !== "chat" && chat.on);
  if (view === "chat" && was !== "chat") {
    const box = document.getElementById("lines");
    box.scrollTop = box.scrollHeight;
  }
  if (view !== was && was) window.scrollTo(0, 0);
}

function signedOut(said) {
  // a session that stopped working is forgotten; the owner's key is kept
  if (token && token === kept(SESSION)) keep(SESSION, "");
  if (token && token === kept(KEY) && said) keep(KEY, "");
  token = kept(KEY) || kept(SESSION);
  me = null;
  for (const id of ["chat", "pages", "people"]) show(id, false);
  drawView();
  document.getElementById("facts").replaceChildren();
  signInForm(invite && !said ? "invite" : "sign-in", said);
}

async function whoAmI() {
  if (!token) return null;
  const res = await fetch("/api/me", { headers: { Authorization: `Bearer ${token}` },
                                       cache: "no-store" });
  if (res.status === 401) return null;
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.status);
  return res.json();
}

async function refresh() {
  // an invite link opens its own form first, even in a browser already signed in
  if (invite && !invited) return signInForm("invite");
  if (!me && !document.getElementById("signin").hidden && !token) return;
  let found;
  try {
    found = await whoAmI();
  } catch (_) {
    document.getElementById("updated").textContent =
      "Couldn't reach Sarathi. Is sarathi home still running?";
    return;
  }
  if (!found) {
    if (!me) return signedOut(token ? "That device was signed out. Sign in again." : "");
    return signedOut("You were signed out. Sign in again.");
  }
  me = found;
  show("signin", false);
  if (!me.owner) return drawPerson();
  let res;
  try {
    res = await fetch("/api/pieces", { headers: { Authorization: `Bearer ${token}` },
                                       cache: "no-store" });
  } catch (_) {
    document.getElementById("updated").textContent =
      "Couldn't reach Sarathi. Is sarathi home still running?";
    return;
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    document.getElementById("updated").textContent = `Couldn't read it: ${body.detail}`;
    return;
  }
  show("pages", true);
  const up = body.pieces.filter((p) => p.up).length;
  const setu = body.pieces.find((p) => p.name === "setu" && p.up);
  document.getElementById("facts").replaceChildren(
    h("span", {}, `${up} of ${body.pieces.length} running`),
    // your own accounts: Setu's page for your own folder, already signed in
    setu ? h("a", { href: setu.open, target: "_blank", rel: "noopener noreferrer" },
             "My accounts") : null);
  const cards = body.pieces.map(card);
  if (body.memory) cards.push(memoryCard(body.memory));
  if (body.tests) cards.push(testsCard(body.tests, body.pieces.find((p) => p.name === "yantra")));
  document.getElementById("pieces").replaceChildren(...cards);
  if (body.people) drawPeople();
  if (body.chat && !chat.on) { startChat(); drawPush(); }
  if (!sets.data && !document.getElementById("settings").dataset.asked) {
    document.getElementById("settings").dataset.asked = "1";
    drawSettings();
  }
  drawView();
  document.getElementById("updated").textContent =
    `Updated ${new Date().toLocaleTimeString()}`;
}

// ---- someone in the house: their chat, and a way out ---------------------------

function drawPerson() {
  const out = h("button.linkish", { type: "button" }, "Sign out");
  out.addEventListener("click", async () => {
    try { await api("/api/sign-out", {}); } catch (_) { /* gone already */ }
    keep(SESSION, "");
    location.reload();
  });
  document.getElementById("facts").replaceChildren(
    h("span", {}, `Signed in as ${me.name}`), ...(me.chat ? [accountsButton()] : []), out);
  document.getElementById("h-chat").textContent = "Talk to your agents";
  document.getElementById("foot-said").textContent =
    "Your chat goes to Dvara as you, with your own allowance and rules. " +
    "The person running this house sees which agent you used and what it cost, " +
    "never what you said.";
  drawView();
  if (!me.chat) {
    document.getElementById("updated").textContent =
      "Dvara isn't running right now, so there's no chat. Try again later.";
    return;
  }
  if (!chat.on) { startChat(); drawPush(); }
  document.getElementById("updated").textContent =
    `Updated ${new Date().toLocaleTimeString()}`;
}

// Their own Setu page, by the one-time link Dvara makes for /accounts page.
// Fetched on the press and shown as a link to tap, since a phone blocks a
// window opened after a wait.
function accountsButton() {
  const button = h("button.linkish", { type: "button" }, "My accounts");
  const said = h("span.accounts-said", { role: "status" });
  button.addEventListener("click", async () => {
    button.disabled = true;
    said.textContent = "Asking for your link…";
    try {
      const got = await api("/api/chat/accounts-page", {});
      if (got.url) {
        said.replaceChildren(
          h("a", { href: got.url, target: "_blank", rel: "noopener" }, "Open my accounts page"),
          " (works once, on this device, for 10 minutes)");
      } else {
        said.textContent = got.said;
      }
    } catch (err) {
      said.textContent = `That didn't work: ${err.message}`;
    }
    button.disabled = false;
  });
  return h("span.accounts", {}, button, said);
}

// Notices on a phone: the house's ntfy server and this person's own topic.
// Shown only when there is an ntfy server; the steps work in any ntfy app.
async function drawPush() {
  let got;
  try { got = await api("/api/chat/push"); } catch (_) { return; }
  if (!got.on) return;
  const steps = h("ol.push-steps", {},
    h("li", {}, "Install the free ntfy app (Google Play, F-Droid or the App Store)."),
    h("li", {}, h("a", { href: got.link }, "Open your notices in the ntfy app"),
      " — or in the app press +, turn on “Use another server”, and enter:"),
    h("li.push-words", {}, h("span", {}, "Server: "), h("code", {}, got.server),
      h("br"), h("span", {}, "Topic: "), h("code", {}, got.topic)));
  const where = got.house
    ? "Your phone hears them while it can reach this house (home Wi-Fi)."
    : "ntfy here listens on this computer only, so a phone can't reach it yet: " +
      "the person running the house sets the house address (dvara.window_host).";
  document.getElementById("push-body").replaceChildren(
    h("p.meta", {}, "A schedule's answer, a sign-in that stopped working, and what " +
      "your agents noticed about you show on your phone, as well as here."),
    steps, h("p.meta", {}, where),
    h("p.meta", {}, "Keep the topic to yourself: whoever has it can read your notices."));
  show("push", true);
}

function signInForm(mode, said) {
  show("signin", true);
  const choosing = mode === "invite";
  const name = document.getElementById("signin-name");
  const password = document.getElementById("signin-password");
  document.getElementById("h-signin").textContent =
    choosing ? "Choose your password" : "Sign in";
  document.getElementById("signin-lede").textContent = choosing
    ? "This link works once. Choose a password of at least 8 characters; after this " +
      "you sign in with your name and that password."
    : "To talk to your agents. The person who runs this house gave you your name; " +
      "you chose the password.";
  document.getElementById("signin-password-label").textContent =
    choosing ? "New password" : "Password";
  password.autocomplete = choosing ? "new-password" : "current-password";
  if (choosing) {
    name.value = invite.split(".")[0];
    name.readOnly = true;
  }
  document.getElementById("signin-go").textContent = choosing ? "Set it and sign in"
                                                              : "Sign in";
  const problemEl = document.getElementById("signin-problem");
  problemEl.hidden = !said;
  problemEl.textContent = said || "";
  const form = document.getElementById("signin-form");
  form.onsubmit = async (event) => {
    event.preventDefault();
    const go = document.getElementById("signin-go");
    go.disabled = true;
    try {
      const path = choosing ? "/api/claim" : "/api/sign-in";
      const body = choosing ? { link: invite, password: password.value }
                            : { name: name.value.trim(), password: password.value };
      const res = await fetch(path, { method: "POST", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const got = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(got.detail || `status ${res.status}`);
      keep(SESSION, got.session);
      token = got.session;
      invited = true;
      name.readOnly = false;
      password.value = "";
      refresh();
    } catch (err) {
      problemEl.hidden = false;
      problemEl.textContent = err.message;
    } finally {
      go.disabled = false;
    }
  };
}

// ---- the owner's list of the people in the house -------------------------------

const people = { links: {} };

function personRow(p, reachable) {
  const state = !p.on_roster ? "not in Dvara's actors file any more"
    : p.signed_up ? `signed in on ${p.devices} device${p.devices === 1 ? "" : "s"}` +
                    (p.last_used ? `, last ${when(p.last_used)}` : "")
    : p.invite_until ? "invited, not opened yet" : "no sign-in yet";
  const inviteB = h("button.open", { type: "button" },
                    p.signed_up ? "New link (resets their password)"
                    : p.invite_until ? "New link" : "Invite");
  inviteB.addEventListener("click", async () => {
    try {
      const got = await api(`/api/people/${encodeURIComponent(p.name)}/invite`, {});
      people.links[p.name] = got;
      document.getElementById("people-said").textContent = "";
    } catch (err) {
      document.getElementById("people-said").textContent = err.message;
    }
    drawPeople();
  });
  let outB = null;
  if (p.devices) {
    outB = h("button.no", { type: "button" }, "Sign out everywhere");
    outB.addEventListener("click", async () => {
      try {
        const got = await api(`/api/people/${encodeURIComponent(p.name)}/sign-out`, {});
        document.getElementById("people-said").textContent = got.said;
      } catch (err) {
        document.getElementById("people-said").textContent = err.message;
      }
      drawPeople();
    });
  }
  const link = people.links[p.name];
  return h("article.card", {},
    h("div.card-head", {}, h("h3", {}, p.name),
      h("span.badge." + (p.signed_up ? "up" : "down"), {}, state)),
    link ? [h("div.meta", {}, `Send ${p.name} this link. It works once, on the first ` +
                              `device, within ${link.hours} hours:`),
            h("div.cmd", {}, link.url),
            link.reachable ? null : h("div.warn", {}, "It opens on this computer only. " +
              "For a phone at home, give Dvara a window address " +
              "(sarathi dvara --window-host ADDRESS), sarathi up, and make a new link.")]
         : null,
    !link && !reachable && !p.signed_up
      ? h("div.meta", {}, "Links open on this computer only until Dvara has a window " +
                          "address on your home network.") : null,
    h("div.buttons", {}, p.on_roster ? inviteB : null, outB));
}

async function drawPeople() {
  show("people", true);
  try {
    const got = await api("/api/people");
    const rows = got.people.map((p) => personRow(p, got.reachable));
    document.getElementById("people-list").replaceChildren(...(rows.length ? rows :
      [h("div.empty", {}, "Nobody but you in Dvara's actors file yet. Add someone " +
                          "there ([actor.name]: their agents and allowance), then " +
                          "invite them here.")]));
  } catch (err) {
    document.getElementById("people-said").textContent = err.message;
  }
}

// ---- the chat -----------------------------------------------------------------
// Lines come from Dvara oldest first, each with an id; the page asks for what
// came after the last one it has. A turn runs in Dvara behind the request, so
// the answer is simply a later line. Questions and held turns are redrawn
// whole on every look: an answer given on Telegram makes them go away here.
// While a turn runs, Dvara's look carries it live (the answer so far and each
// step as a line), and the page looks more often until it is answered.
// Answers are drawn as markdown (md.js, escaped first, the same file Yantra's
// page uses). Every button here sends words Dvara answers on every channel:
// /skills, /tools, /schedules, /memory, /new, /skills keep N.

const CHAT_EVERY = 3000;
const CHAT_BUSY_EVERY = 700;
const chat = { on: false, last: 0, timer: null, agents: [], sending: false, busy: false,
               lessons: [], voice: false };

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

// An answer read aloud (Dvara's spoken.py), made on the home computer the
// first time it's asked for: ▶ plays it, ■ stops it, one at a time. An
// answer the person asked to hear (a voice note sent, or "always") plays
// by itself when it arrives -- never one already there when the page opened.
const playing = { audio: null, button: null, url: null };

function stopVoice() {
  if (playing.audio) playing.audio.pause();
  if (playing.button) playing.button.textContent = "▶ Listen";
  if (playing.url) URL.revokeObjectURL(playing.url);
  playing.audio = playing.button = playing.url = null;
}

async function playVoice(line, button) {
  const again = playing.button === button;
  stopVoice();
  if (again) return;
  playing.button = button;
  button.textContent = "… reading it";
  try {
    const res = await fetch(`/api/chat/spoken?line=${line}`,
                            { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.status);
    const url = URL.createObjectURL(await res.blob());
    if (playing.button !== button) { URL.revokeObjectURL(url); return; }
    playing.url = url;
    playing.audio = new Audio(url);
    playing.audio.addEventListener("ended", () => { if (playing.button === button) stopVoice(); });
    button.textContent = "■ Stop";
    await playing.audio.play();
  } catch (err) {
    if (playing.button === button) stopVoice();
    // a browser that won't play before a tap says NotAllowedError: the button stays
    if (err.name !== "NotAllowedError") problem(`Couldn't read it aloud: ${err.message}`);
  }
}

function listenButton(ln) {
  const b = h("button.listen", { type: "button" }, "▶ Listen");
  b.addEventListener("click", () => playVoice(ln.id, b));
  return b;
}

// A picture an answer carries (/phone's screen) is shown, not only offered:
// fetched once per line and kept as an object URL while the page is open.
const pictures = new Map();
const PICTURE = /\.(png|jpe?g|gif|webp)$/i;

function picture(line, n, name) {
  const img = h("img.picture", { alt: name });
  const key = `${line}:${n}`;
  const show = (url) => { img.src = url; };
  if (pictures.has(key)) {
    pictures.get(key).then(show, () => img.remove());
  } else {
    const got = fetch(`/api/chat/file?line=${line}&n=${n}`,
                      { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.blob() : Promise.reject(new Error(res.status))))
      .then((blob) => URL.createObjectURL(blob));
    pictures.set(key, got);
    got.then(show, () => img.remove());
  }
  img.addEventListener("click", () => download(line, n, name));
  return img;
}

function bubble(text, who) {
  // Your own words stay as you wrote them; an agent's and a notice's are markdown.
  if (who === "you" || typeof renderMarkdown !== "function") return h("div.bubble", {}, text);
  const el = h("div.bubble.md");
  el.innerHTML = renderMarkdown(text);
  return el;
}

function offerView(offer) {
  const keep = (word) => () => api("/api/chat", { agent: offer.agent, text: `/skills ${word} ${offer.id}` });
  return h("div.offer", {},
    h("div.what", {}, `${offer.name} — test: ${offer.test}`),
    buttons(keep("keep"), keep("drop"), "Keep", "Not now"));
}

// A sign-in word the answer told you to send (Dvara's accounts.taps): the
// button sends that word as if you'd typed it, to the agent that said it.
function tapsView(ln) {
  return h("div.buttons.taps", {}, ln.taps.map((t) => {
    const b = h("button.yes", { type: "button" }, t.label);
    b.addEventListener("click", async () => {
      b.disabled = true;
      try { await api("/api/chat", { agent: ln.agent, text: t.word }); problem(""); }
      catch (err) { problem(err.message); b.disabled = false; }
      chat.busy = true;
      look();
    });
    return b;
  }));
}

// A conversation opened again (/chats N): its own words, folded under the
// answer that says you're back in it -- open by default, so it reads as
// the conversation you're now in.
function transcriptView(ln) {
  const rows = ln.transcript.map((t) => h(`div.tline.${t.who}`, {},
    h("span.tag", {}, t.who === "you" ? "You" : (ln.agent || "Agent")),
    bubble(t.text, t.who)));
  return h("details.transcript", { open: "" },
    h("summary", {}, `The conversation (${ln.transcript.length} messages)`), ...rows);
}

function lineView(ln) {
  const failed = ln.who === "agent" && ln.stop_reason
    && !["held", "skills", "seen", "memory", "new", "files", "accounts", "phone"]
      .includes(ln.stop_reason);
  const label = ln.who === "you" ? `You${chat.agents.length > 1 ? " → " + ln.agent : ""}`
    : ln.who === "notice" ? "Sent to you"
    : (ln.agent || "Agent");
  return h(`div.line.${ln.who}${failed ? ".failed" : ""}`, {},
    h("span.tag", {}, `${label} · ${when(ln.at)}`),
    // a reopened conversation shows itself below: only "Back in: …" here
    ln.text ? bubble(ln.transcript ? ln.text.split("\n")[0] : ln.text, ln.who) : null,
    ln.sent ? h("div.sent", {}, `📎 ${ln.sent.join(", ")}`) : null,
    ln.offer ? offerView(ln.offer) : null,
    ln.heard ? h("div.heard", {}, `I heard: "${ln.heard}"`) : null,
    ln.taps ? tapsView(ln) : null,
    ln.transcript ? transcriptView(ln) : null,
    ln.held ? h("span.receipt", {}, "Waiting for your yes, below.") : null,
    ln.receipt ? h("span.receipt", {}, ln.receipt) : null,
    chat.voice && ln.who !== "you" && ln.text && !ln.transcript ? listenButton(ln) : null,
    (ln.files || []).map((name, n) => {
      if (PICTURE.test(name)) return picture(ln.id, n, name);
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

function liveView(lv) {
  // A turn while it runs: each step as a line, and the answer as it is written.
  const items = lv.items.map((it) => it.step !== undefined
    ? h(`div.step${it.ok ? "" : ".bad"}`, {},
        `${it.ok ? "✓" : "✗"} ${it.step}${it.ok ? "" : it.refused ? " — refused" : " — didn't work"}`)
    : bubble(it.text, "agent"));
  if (lv.using) items.push(h("div.step.now", {}, `… ${lv.using}`));
  if (!items.length) items.push(h("div.step.now", {}, "… thinking"));
  return h("div.line.agent.live", {}, h("span.tag", {}, `${lv.agent} · working`), ...items);
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
  chat.voice = Boolean(data.voice);
  const box = document.getElementById("lines");
  const atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  const live = document.getElementById("live") || h("div", { id: "live" });
  const running = data.live || [];
  if (!chat.last && !data.lines.length && !running.length) {
    box.replaceChildren(h("div.empty", {}, "Nothing yet. Say hello."), live);
  } else if (data.lines.length) {
    const fresh = Boolean(chat.last);   // lines that came while the page was open
    if (!chat.last) box.replaceChildren(live);
    for (const ln of data.lines) {
      const view = lineView(ln);
      box.insertBefore(view, live);
      const listen = view.querySelector("button.listen");
      if (fresh && ln.speak && listen) playVoice(ln.id, listen);
    }
    chat.last = data.lines[data.lines.length - 1].id;
  }
  if (!live.isConnected) box.append(live);
  live.replaceChildren(...running.map(liveView));
  if (atEnd || data.lines.some((l) => l.who === "you")) box.scrollTop = box.scrollHeight;
  document.getElementById("waiting").replaceChildren(
    ...data.asks.map(askView), ...data.holds.map(holdView));
  chat.lessons = data.lessons || [];
  drawLesson();
  document.getElementById("chat-state").textContent =
    data.busy.length ? `${data.busy.join(", ")} is working…` : "";
  chat.busy = data.busy.length > 0;
}

async function look() {
  try {
    draw(await api(`/api/chat?after=${chat.last}`));
    if (!chat.sending) problem("");
  } catch (err) {
    problem(err.message);
  }
}

function lookAgain() {
  // Often while a turn runs, so its steps and words show as they come.
  clearTimeout(chat.timer);
  chat.timer = setTimeout(async () => {
    if (!document.hidden) await look();
    lookAgain();
  }, chat.busy ? CHAT_BUSY_EVERY : CHAT_EVERY);
}

// Files chosen with the paperclip, sent with the next message (Dvara keeps
// them in your folder with that agent, under from-you/).
const chosen = [];
const SEND_AT_MOST = 20 * 1024 * 1024;

function drawChosen() {
  const box = document.getElementById("attached");
  box.hidden = !chosen.length;
  box.replaceChildren(...chosen.map((f, i) => {
    const x = h("button", { type: "button", "aria-label": `Remove ${f.name}` }, "×");
    x.addEventListener("click", () => { chosen.splice(i, 1); drawChosen(); });
    return h("span.chip", {}, f.name, x);
  }));
}

// A voice note: tap to record, tap again to stop; it joins the files for
// the next message, and Dvara turns it into words (its heard.py).
let recorder = null;

async function recordToggle() {
  const button = document.getElementById("record");
  if (recorder) { recorder.stop(); return; }
  if (!navigator.mediaDevices || typeof MediaRecorder === "undefined") {
    problem("This browser can't record here (a page on http:// that isn't this " +
            "computer can't use the microphone).");
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    problem(`The microphone wasn't allowed: ${err.message}`);
    return;
  }
  const parts = [];
  recorder = new MediaRecorder(stream);
  recorder.addEventListener("dataavailable", (e) => parts.push(e.data));
  recorder.addEventListener("stop", () => {
    stream.getTracks().forEach((t) => t.stop());
    const type = recorder.mimeType || "audio/webm";
    const ext = type.includes("ogg") ? "ogg" : type.includes("mp4") ? "m4a" : "webm";
    chosen.push(new File(parts, `voice-note.${ext}`, { type }));
    recorder = null;
    button.setAttribute("aria-pressed", "false");
    drawChosen();
  });
  recorder.start();
  button.setAttribute("aria-pressed", "true");
  problem("");
}

function asBase64(file) {
  return new Promise((ok, fail) => {
    const reader = new FileReader();
    reader.onload = () => ok(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = () => fail(new Error(`couldn't read ${file.name}`));
    reader.readAsDataURL(file);
  });
}

async function send(text) {
  const agent = document.getElementById("agent").value;
  if ((!text.trim() && !chosen.length) || !agent || chat.sending) return false;
  const total = chosen.reduce((n, f) => n + f.size, 0);
  if (total > SEND_AT_MOST) {
    problem("Those files are over 20 MB together; send fewer at once.");
    return false;
  }
  chat.sending = true;
  const button = document.querySelector("#say .send");
  button.disabled = true;
  try {
    const files = await Promise.all(chosen.map(async (f) => ({ name: f.name,
                                                               data: await asBase64(f) })));
    await api("/api/chat", files.length ? { agent, text, files } : { agent, text });
    chosen.length = 0;
    drawChosen();
    problem("");
    chat.busy = true;
    return true;
  } catch (err) {
    problem(err.message);
    return false;
  } finally {
    chat.sending = false;
    button.disabled = false;
    await look();
    lookAgain();
  }
}

/* -- a lesson: a job taught one step at a time (Yantra's skills/lesson.py) ---
   Teach sends what a person would type -- /learn start or /learn watch and
   what it's for -- to the agent picked below; the bar shows the open
   lesson with that agent, from Dvara's look, until Done or Stop. */

function drawLesson() {
  const agent = document.getElementById("agent").value;
  const lesson = (chat.lessons || []).find((l) => l.agent === agent);
  const bar = document.getElementById("lesson");
  bar.hidden = !lesson;
  if (!lesson) return;
  const how = lesson.watching ? "Showing" : "Teaching";
  const next = lesson.watching ? "do the next step on the phone, then send next"
    : "write the next step";
  document.getElementById("lesson-words").textContent =
    `${how} ${agent}: ${lesson.task}. ${lesson.told} step(s) so far; ${next}.`;
}

function startTeach() {
  const box = document.getElementById("teach");
  const what = document.getElementById("teach-what");
  document.getElementById("teach-open").addEventListener("click", () => {
    if ((chat.lessons || []).some((l) => l.agent === document.getElementById("agent").value)) {
      problem("A lesson is open with this agent: press Done or Stop first.");
      return;
    }
    what.value = "";
    box.returnValue = "";        // Escape leaves the last open's answer otherwise
    box.showModal();
    what.focus();
  });
  box.addEventListener("close", () => {
    const how = document.querySelector('input[name="teach-how"]:checked')?.value;
    const task = what.value.trim();
    if (box.returnValue !== "start" || !task) return;
    send(`/learn ${how === "watch" ? "watch" : "start"} ${task}`);
  });
  document.getElementById("lesson-done").addEventListener("click", () => send("/learn done"));
  document.getElementById("lesson-stop").addEventListener("click", () => send("/learn stop"));
  document.getElementById("agent").addEventListener("change", drawLesson);
}

async function say(event) {
  event.preventDefault();
  const text = document.getElementById("text");
  if (await send(text.value)) text.value = "";
}

/* -- history: every conversation, kept by Dvara as it goes (past.py) ----------
   Searched by any words in it (Dvara's full-text index, every conversation
   and not only the rows drawn), read the way it looked, carried on in this
   chat, or deleted for good. */

const past = { q: "", timer: null };

function marked(text, q) {
  // the words searched for, marked in what is drawn; text nodes only
  const span = h("span", {}, text);
  const words = (q.toLowerCase().match(/[\p{L}\p{N}_]+/gu) || []);
  if (!words.length) return span;
  const re = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "giu");
  span.textContent = "";
  for (const part of text.split(re)) {
    span.append(re.test(part) ? h("mark.hit", {}, part) : document.createTextNode(part));
    re.lastIndex = 0;
  }
  return span;
}

function snippetView(snip) {
  // Dvara marks each match between \u0002 and \u0003
  const out = h("div.snip");
  snip.split(/(\u0002[^\u0003]*\u0003)/).forEach((part) => {
    out.append(part.startsWith("\u0002")
      ? h("mark.hit", {}, part.slice(1, -1)) : document.createTextNode(part));
  });
  return out;
}

function historySaid(text) {
  const el = document.getElementById("history-said");
  el.hidden = !text;
  el.textContent = text || "";
}

function historyList(on) {
  document.getElementById("history-rows").hidden = !on;
  document.getElementById("history-q").hidden = !on;
  document.getElementById("history-lede").hidden = !on;
  document.getElementById("history-read").hidden = on;
  document.getElementById("history-back").hidden = on;
}

async function openHistory() {
  const box = document.getElementById("history");
  if (!box.open) box.showModal();
  historyList(true);
  historySaid("");
  await drawHistory();
  document.getElementById("history-q").focus();
}

async function drawHistory() {
  const rows = document.getElementById("history-rows");
  let data;
  try {
    data = await api(`/api/chat/chats?q=${encodeURIComponent(past.q)}`);
  } catch (err) {
    rows.replaceChildren(h("p.meta", {}, err.message));
    return;
  }
  if (!data.rows.length) {
    rows.replaceChildren(h("p.meta", {}, past.q
      ? `None of your conversations say “${past.q}”.`
      : "Nothing yet. Each conversation is kept here as you talk."));
    return;
  }
  rows.replaceChildren(...data.rows.map((r) => {
    const row = h("div.hrow", { tabindex: "0", role: "button" },
      h("div", {},
        h("div.title", {}, r.title, r.open ? h("span.now", {}, "open in a chat") : null),
        h("div.meta", {}, `${when(r.updated_at)} · ${r.agent} · on ${r.road} · `
          + `${r.turns} message${r.turns === 1 ? "" : "s"}`)),
      deleteButton(r),
      r.snippet ? snippetView(r.snippet) : null);
    row.addEventListener("click", (e) => { if (!e.target.closest("button")) readHistory(r.id); });
    row.addEventListener("keydown", (e) => { if (e.key === "Enter") readHistory(r.id); });
    return row;
  }));
}

function deleteButton(r) {
  const b = h("button.quiet.danger", { type: "button" }, "Delete");
  if (r.open) {
    b.disabled = true;
    b.title = "It's open in a chat now. Start a new chat there first.";
  }
  b.addEventListener("click", async (e) => {
    e.stopPropagation();
    if (!confirm(`Delete “${r.title}” for good? It can't be brought back.`)) return;
    try {
      await api(`/api/chat/chats/${encodeURIComponent(r.id)}/delete`, {});
      historyList(true);
      historySaid("");
      await drawHistory();
    } catch (err) { historySaid(err.message); }
  });
  return b;
}

async function readHistory(id) {
  let d;
  try { d = await api(`/api/chat/chats/${encodeURIComponent(id)}`); }
  catch (err) { historySaid(err.message); return; }
  historyList(false);
  historySaid("");
  const carry = h("button.quiet", { type: "button" }, d.open ? "Open in a chat now" : "Carry on in the chat");
  carry.disabled = d.open;
  carry.addEventListener("click", async () => {
    const pick = document.getElementById("agent");
    if ([...pick.options].some((o) => o.value === d.agent)) pick.value = d.agent;
    document.getElementById("history").close();
    try { await api("/api/chat", { agent: d.agent, text: `/chats open ${d.id}` }); problem(""); }
    catch (err) { problem(err.message); }
    chat.busy = true;
    look();
  });
  const lines = d.entries.map((e) => {
    if (e.who === "tool") {
      return h("details.tool", {},
        h("summary", {}, `· ${e.name}${e.error ? " (failed)" : ""}`),
        h("pre", {}, e.args), e.result ? h("pre", {}, `→ ${e.result}`) : null);
    }
    const said = e.who === "you" ? h("div.bubble", {}, marked(e.text, past.q)) : bubble(e.text, "agent");
    if (e.who !== "you" && past.q) {
      // markdown drawn first, then the words marked inside it
      const walk = document.createTreeWalker(said, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walk.nextNode()) nodes.push(walk.currentNode);
      for (const n of nodes) n.replaceWith(marked(n.nodeValue, past.q));
    }
    return h(`div.tline.${e.who}`, {}, h("span.tag", {}, e.who === "you" ? "You" : d.agent), said);
  });
  document.getElementById("history-read").replaceChildren(
    h("div", {}, h("div.title", {}, h("strong", {}, d.title)),
      h("div.meta", {}, `${when(d.started_at)} · ${d.agent} · on ${d.road}`
        + (d.model ? ` · ${d.model}` : ""))),
    h("div.acts", {}, carry, ...shareButtons(d), deleteButton(d)),
    ...lines);
  document.querySelector("#history-read mark.hit")?.scrollIntoView({ block: "center" });
}

/* Sharing one. A PDF is the browser's own "Save as PDF" over a print layout
   of just this conversation (every script prints right; nothing to
   install). The file is Markdown, made by Dvara: words, answers and the
   names of the tools used, never what a tool returned. Send hands that
   file to the phone's share sheet where there is one. */

async function pastFile(d) {
  const res = await fetch(`/api/chat/chats/${encodeURIComponent(d.id)}/export`,
                          { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `status ${res.status}`);
  const named = /filename\*=UTF-8''([^;]+)/.exec(res.headers.get("content-disposition") || "");
  return new File([await res.blob()], named ? decodeURIComponent(named[1]) : "conversation.md",
                  { type: "text/markdown" });
}

function shareButtons(d) {
  const pdf = h("button.quiet", { type: "button", title: "Opens the print window: pick Save as PDF" }, "Save as PDF");
  pdf.addEventListener("click", () => printPast(d));
  const file = h("button.quiet", { type: "button", title: "A Markdown file: any notes app opens it" }, "Download");
  file.addEventListener("click", async () => {
    try {
      const made = await pastFile(d);
      const url = URL.createObjectURL(made);
      const a = h("a", { href: url, download: made.name });
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (err) { historySaid(`Couldn't download it: ${err.message}`); }
  });
  const out = [pdf, file];
  if (navigator.canShare) {
    const send = h("button.quiet", { type: "button", title: "WhatsApp, email, …" }, "Send…");
    send.addEventListener("click", async () => {
      try {
        const made = await pastFile(d);
        if (navigator.canShare({ files: [made] })) await navigator.share({ files: [made], title: d.title });
        else await navigator.share({ title: d.title, text: await made.text() });
      } catch (err) { if (err.name !== "AbortError") historySaid(`Not sent: ${err.message}`); }
    });
    out.push(send);
  }
  return out;
}

function printPast(d) {
  const area = document.getElementById("print-chat");
  const blocks = [h("header", {}, h("h1", {}, d.title),
    // the full date: a printed page outlives "today"
    h("p", {}, `${new Date(d.started_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}`
      + ` · ${d.agent} · on ${d.road}`))];
  let tools = [];
  const flush = () => {
    if (tools.length) blocks.push(h("p.print-tools", {}, `Tools used: ${[...new Set(tools)].join(", ")}`));
    tools = [];
  };
  for (const e of d.entries) {
    if (e.who === "tool") { tools.push(e.name); continue; }
    if (e.who === "you") flush();
    blocks.push(h(`section.print-line.${e.who}`, {}, h("h2", {}, e.who === "you" ? "You" : d.agent),
      e.who === "you" ? h("div.plain", {}, e.text) : bubble(e.text, "agent")));
  }
  flush();
  area.replaceChildren(...blocks);
  document.body.classList.add("printing-chat");
  const done = () => {
    document.body.classList.remove("printing-chat");
    area.replaceChildren();
    window.removeEventListener("afterprint", done);
  };
  window.addEventListener("afterprint", done);
  window.print();
}

function startHistory() {
  document.getElementById("history-open").addEventListener("click", openHistory);
  document.getElementById("history-close").addEventListener("click",
    () => document.getElementById("history").close());
  document.getElementById("history-back").addEventListener("click", () => {
    historyList(true);
    drawHistory();
  });
  document.getElementById("history-q").addEventListener("input", (e) => {
    clearTimeout(past.timer);
    past.timer = setTimeout(() => { past.q = e.target.value; drawHistory(); }, 200);
  });
}

function startChat() {
  chat.on = true;
  document.getElementById("chat").hidden = false;
  document.getElementById("say").addEventListener("submit", say);
  document.getElementById("record").addEventListener("click", recordToggle);
  document.getElementById("files").addEventListener("change", (event) => {
    chosen.push(...event.target.files);
    event.target.value = "";
    drawChosen();
  });
  document.getElementById("text").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) say(e);
  });
  for (const b of document.querySelectorAll(".words [data-word]")) {
    b.addEventListener("click", () => send(b.dataset.word));
  }
  startHistory();
  startTeach();
  drawView();
  look().then(lookAgain);
}

document.addEventListener("DOMContentLoaded", () => {
  drawView();
  window.addEventListener("hashchange", drawView);
  // Escape leaves Your pages or Settings for the chat (a dialog takes it first)
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || document.querySelector("dialog[open]")) return;
    if (chat.on && document.body.dataset.view !== "chat") location.hash = "chat";
  });
  refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, EVERY);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
});
