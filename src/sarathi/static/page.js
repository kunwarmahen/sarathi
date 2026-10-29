// Sarathi's home page: one card per program's page, drawn from /api/pieces,
// and a chat with your agents that passes through to Dvara (/api/chat).
// Every value goes in as text, never as markup. The owner's key arrives
// after "#token=", is kept in this browser, and leaves the address bar at
// once. The links it draws carry each page's own key, so they open with no
// referrer. Someone else in the house signs in instead (an invite link,
// "#invite=", once; then their name and password) and gets their own chat,
// nothing else: the server holds that line, this script only draws it.
// The page is a chat app: your conversations listed at the left (every
// road's: this page, Telegram, a puck), the one you're in beside them.
// Notices, Your pages and Settings are views of the same pane, each at
// its own address (#notices, #pages, #settings) so a reload stays put;
// Your pages and Settings open from your name at the foot of the list.
"use strict";

const KEY = "sarathi.home.token";
const SESSION = "sarathi.home.session";
const EVERY = 20000;
const VIEWS = ["chat", "notices", "pages", "settings"];
const SIDE = "sarathi.side";

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

// ---- the views ------------------------------------------------------------------
// Each section keeps its own `hidden` (whether there is anything to show);
// which view is on is body[data-view], read by the stylesheet. Someone in
// the house has the chat and their notices; the owner with Dvara off has
// no chat, so their page opens on Your pages instead.

function wantedView() {
  const asked = location.hash.slice(1);
  return VIEWS.includes(asked) ? asked : "chat";
}

const TITLES = { notices: "Notices", pages: "Your pages", settings: "Settings" };

function drawView() {
  if (!me) {
    document.body.dataset.view = "signin";
    show("side", false);
    show("bar", false);
    return;
  }
  show("side", true);
  show("bar", true);
  let view = wantedView();
  if (!me.owner && (view === "pages" || view === "settings")) view = "chat";
  if (view === "chat" && !chat.on && me.owner) view = "pages";
  const was = document.body.dataset.view;
  document.body.dataset.view = view;
  const bell = document.getElementById("bell");
  if (view === "notices") bell.setAttribute("aria-current", "page");
  else bell.removeAttribute("aria-current");
  bell.hidden = !chat.on;
  document.getElementById("bar-title").textContent =
    view === "chat" ? chatTitle() : TITLES[view];
  if (view === "notices" && was !== "notices") drawNotices(true);
  if (view === "chat" && was !== "chat") {
    const box = document.getElementById(chat.reading ? "past" : "lines");
    box.scrollTop = box.scrollHeight;
    if (chat.on) fitText();
  }
  if (view !== was && was) document.querySelector(".pane > main").scrollTop = 0;
  drawConvsMark();
}

/* -- the list at the left: shown, hidden, and on a phone slid over --------- */

const phone = window.matchMedia("(max-width: 760px)");

function openSide() {
  if (phone.matches) {
    document.body.classList.add("side-shown");
    show("scrim", true);
  } else {
    document.body.classList.remove("side-closed");
    keep(SIDE, "");
  }
}

function closeSide() {
  if (phone.matches) {
    document.body.classList.remove("side-shown");
    show("scrim", false);
  } else {
    document.body.classList.add("side-closed");
    keep(SIDE, "closed");
  }
}

// on a phone the list goes once something in it is picked
function sideDone() { if (phone.matches) closeSide(); }

/* -- your name at the foot of the list: the rest of the page, and out ------ */

const account = { setu: null };

function menuItem(label, hint, onClick, cls = "") {
  const b = h(`button${cls ? "." + cls : ""}`, { type: "button", role: "menuitem" },
    h("span", {}, label), hint ? h("span.hint", {}, hint) : null);
  b.addEventListener("click", (e) => { e.stopPropagation(); closeMenus(); onClick(b); });
  return b;
}

function go(view) { location.hash = view; sideDone(); }

function drawAccount() {
  document.getElementById("account-name").textContent = me.owner ? `${me.name} (runs this house)` : me.name;
  document.getElementById("account-avatar").textContent = (me.name || "?").slice(0, 1).toUpperCase();
  const items = [];
  if (me.owner) {
    items.push(menuItem("Your pages", "Each program's own page, already signed in", () => go("pages")));
    items.push(menuItem("Settings", "Every settings file, and the people in the house", () => go("settings")));
  }
  if (chat.on) {
    items.push(menuItem("Notices", "What was sent to you, and on your phone", () => go("notices")));
    items.push(menuItem("Turned down", "What you said no to remembering", openDeclined));
  }
  if (me.owner && account.setu) {
    items.push(menuItem("My accounts", "Your sign-ins, on Setu's page", () => window.open(account.setu, "_blank", "noopener,noreferrer")));
  } else if (!me.owner && me.chat) {
    items.push(menuItem("My accounts", "A link to your own sign-ins page", askAccounts));
  }
  if (!me.owner) {
    items.push(h("hr"));
    items.push(menuItem("Sign out", null, async () => {
      try { await api("/api/sign-out", {}); } catch (_) { /* gone already */ }
      keep(SESSION, "");
      location.reload();
    }));
  }
  document.getElementById("account-menu").replaceChildren(...items);
}

function closeMenus(except) {
  for (const m of document.querySelectorAll(".menu:not([hidden])")) {
    if (m !== except) m.hidden = true;
  }
  for (const b of document.querySelectorAll('[aria-expanded="true"]')) {
    if (!except || !except.parentElement.contains(b)) b.setAttribute("aria-expanded", "false");
  }
}

function toggleMenu(button, menu) {
  const opening = menu.hidden;
  closeMenus(opening ? menu : undefined);
  menu.hidden = !opening;
  button.setAttribute("aria-expanded", String(opening));
}

function signedOut(said) {
  // a session that stopped working is forgotten; the owner's key is kept
  if (token && token === kept(SESSION)) keep(SESSION, "");
  if (token && token === kept(KEY) && said) keep(KEY, "");
  token = kept(KEY) || kept(SESSION);
  me = null;
  for (const id of ["chat", "pages", "people"]) show(id, false);
  drawView();
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
  // your own accounts: Setu's page for your own folder, already signed in
  const setu = body.pieces.find((p) => p.name === "setu" && p.up);
  account.setu = setu ? setu.open : null;
  document.getElementById("facts").textContent = `${up} of ${body.pieces.length} running`;
  const cards = body.pieces.map(card);
  if (body.memory) cards.push(memoryCard(body.memory));
  if (body.tests) cards.push(testsCard(body.tests, body.pieces.find((p) => p.name === "yantra")));
  document.getElementById("pieces").replaceChildren(...cards);
  if (body.people) drawPeople();
  if (body.chat && !chat.on) { startChat(); drawPush(); }
  drawAccount();
  if (chat.on) lookNotices();
  if (!sets.data && !document.getElementById("settings").dataset.asked) {
    document.getElementById("settings").dataset.asked = "1";
    drawSettings();
    drawVersionLine();
  }
  drawView();
  document.getElementById("updated").textContent =
    `Updated ${new Date().toLocaleTimeString()}`;
}

// ---- someone in the house: their chat, and a way out ---------------------------

function drawPerson() {
  document.getElementById("foot-said").textContent =
    "Your chat goes to Dvara as you, with your own allowance and rules. " +
    "The person running this house sees which agent you used and what it cost, " +
    "never what you said.";
  if (me.chat && !chat.on) { startChat(); drawPush(); }
  drawAccount();
  drawView();
  if (!me.chat) {
    problem("Dvara isn't running right now, so there's no chat. Try again later.");
    show("chat", true);
    return;
  }
  lookNotices();
  document.getElementById("updated").textContent =
    `Updated ${new Date().toLocaleTimeString()}`;
}

// Their own Setu page, by the one-time link Dvara makes for /accounts page.
// Fetched on the press and shown in the menu as a link to tap, since a
// phone blocks a window opened after a wait.
async function askAccounts() {
  const menu = document.getElementById("account-menu");
  const said = h("div.said", { role: "status" }, "Asking for your link…");
  menu.append(said);
  menu.hidden = false;
  try {
    const got = await api("/api/chat/accounts-page", {});
    if (got.url) {
      said.replaceChildren(
        h("a", { href: got.url, target: "_blank", rel: "noopener" }, "Open my accounts page"),
        h("span.hint", {}, "Works once, on this device, for 10 minutes"));
    } else {
      said.textContent = got.said;
    }
  } catch (err) {
    said.textContent = `That didn't work: ${err.message}`;
  }
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
// THE WINDOW IS THE CONVERSATION YOU'RE IN. /new's answer empties it (and
// draws nothing: the greeting shows instead), and a conversation opened
// again starts it over with that conversation's own words. What was sent
// to you unasked goes to the bell (Notices), not between your words.

const CHAT_EVERY = 3000;
const CHAT_BUSY_EVERY = 700;
const chat = { on: false, last: 0, timer: null, agents: [], sending: false, busy: false,
               lessons: [], voice: false, reading: null, title: "", waiting: 0 };

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
//
// ONE VOICE, EVER. An answer that plays by itself waits for the one being
// read to finish (``queued``), and is played once however many looks bring
// it (``played``). A press of ▶ is the person's: it stops what's reading and
// plays now. Another tab of this page that starts reading stops this one
// (``voices``), so two open copies never talk over each other.
const playing = { audio: null, button: null, url: null };
const queued = [];
const played = new Set();
const voices = "BroadcastChannel" in window ? new BroadcastChannel("sarathi-voice") : null;
if (voices) voices.onmessage = () => { queued.length = 0; stopVoice(); };

function stopVoice() {
  if (playing.audio) playing.audio.pause();
  if (playing.button) playing.button.textContent = "▶ Listen";
  if (playing.url) URL.revokeObjectURL(playing.url);
  playing.audio = playing.button = playing.url = null;
}

// An answer the person asked to hear, as it arrives: now, or after this one.
function playByItself(line, button) {
  if (played.has(line)) return;
  played.add(line);
  if (playing.button) queued.push([line, button]);
  else playVoice(line, button);
}

function playNext() {
  const next = queued.shift();
  if (next && next[1].isConnected) playVoice(...next);
  else if (next) playNext();
}

async function playVoice(line, button) {
  const again = playing.button === button;
  stopVoice();
  if (again) { queued.length = 0; return; }
  if (voices) voices.postMessage(line);
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
    playing.audio.addEventListener("ended", () => {
      if (playing.button === button) { stopVoice(); playNext(); }
    });
    button.textContent = "■ Stop";
    await playing.audio.play();
  } catch (err) {
    if (playing.button === button) { stopVoice(); playNext(); }
    // a browser that won't play before a tap says NotAllowedError: the button stays
    if (err.name !== "NotAllowedError") problem(`Couldn't read it aloud: ${err.message}`);
  }
}

function listenButton(ln) {
  const b = h("button.listen", { type: "button" }, "▶ Listen");
  b.addEventListener("click", () => { played.add(ln.id); queued.length = 0; playVoice(ln.id, b); });
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

// A conversation opened again (/chats N): a mark that you're back in it,
// then its own words as the chat they were, so it reads as the
// conversation you're now in.
function transcriptView(ln) {
  const title = ln.text.split("\n")[0].replace(/^Back in:\s*/, "");
  return [h("div.line.back", {}, h("span.tag", {}, `Back in · ${when(ln.at)}`)),
          ...ln.transcript.map((t) => h(`div.line.${t.who}`, {},
            t.who === "you" ? null : h("span.tag", {}, h("span.who", {}, ln.agent || "Agent")),
            bubble(t.text, t.who))),
          title];
}

// What an answer's turn did, step by step (Dvara's runsteps): folded under
// the answer, fetched the first time it's opened. Each step is the tool,
// when, how long it waited for a yes and ran, and a line of what came back;
// the file holds the rest, and says so before anyone sends it.
function stepsView(ln) {
  const box = h("details.steps", {}, h("summary", {}, "Steps"));
  const body = h("div.steps-body", {}, h("div.meta", {}, "…"));
  box.append(body);
  box.addEventListener("toggle", async () => {
    if (!box.open || box.dataset.got) return;
    box.dataset.got = "1";
    try {
      const d = await api(`/api/chat/steps?line=${ln.id}`);
      const head = `${d.steps.length} step${d.steps.length === 1 ? "" : "s"}`
        + (d.seconds != null ? ` · ${d.seconds}s` : "") + (d.outcome ? ` · ${d.outcome}` : "");
      const rows = d.steps.map((st, i) => h("div.step", {},
        h("div.step-head", {}, d.said[i] || st.tool),
        st.short ? h("div.step-said", {}, `→ ${st.short}`) : null));
      const file = h("button.file", { type: "button" }, "⤓ File for a bug report");
      file.addEventListener("click", () => saveSteps(ln.id));
      body.replaceChildren(h("div.meta", {}, head),
        ...(rows.length ? rows : [h("div.meta", {}, "No tools: it answered from what it knew.")]),
        file);
    } catch (err) {
      body.replaceChildren(h("div.meta", {}, err.message));
      delete box.dataset.got;
    }
  });
  return box;
}

async function saveSteps(line) {
  try {
    const res = await fetch(`/api/chat/steps/export?line=${line}`,
                            { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.status);
    const url = URL.createObjectURL(await res.blob());
    const a = h("a", { href: url, download: `steps-${line}.md` });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (err) {
    problem(`Couldn't make the file: ${err.message}`);
  }
}

function lineView(ln) {
  const failed = ln.who === "agent" && ln.stop_reason
    && !["held", "skills", "seen", "memory", "new", "files", "accounts", "phone"]
      .includes(ln.stop_reason);
  const tag = ln.who === "you"
    ? (chat.agents.length > 1 ? h("span.tag", {}, `to ${ln.agent} · ${when(ln.at)}`) : null)
    : h("span.tag", {}, h("span.who", {}, ln.agent || "Agent"), ` · ${when(ln.at)}`);
  return h(`div.line.${ln.who}${failed ? ".failed" : ""}`, {},
    tag,
    ln.text ? bubble(ln.text, ln.who) : null,
    ln.sent ? h("div.sent", {}, `📎 ${ln.sent.join(", ")}`) : null,
    ln.offer ? offerView(ln.offer) : null,
    ln.heard ? h("div.heard", {}, `I heard: "${ln.heard}"`) : null,
    ln.taps ? tapsView(ln) : null,
    ln.held ? h("span.receipt", {}, "Waiting for your yes, below.") : null,
    ln.receipt ? h("span.receipt", {}, ln.receipt) : null,
    ln.steps && ln.who === "agent" ? stepsView(ln) : null,
    chat.voice && ln.who !== "you" && ln.text ? listenButton(ln) : null,
    (ln.files || []).map((name, n) => {
      if (PICTURE.test(name)) return picture(ln.id, n, name);
      const b = h("button.file", { type: "button" }, `⤓ ${name}`);
      b.addEventListener("click", () => download(ln.id, n, name));
      return b;
    }));
}

function buttons(onYes, onNo, yes = "Yes", no = "No", onAll = null) {
  const y = h("button.yes", { type: "button" }, yes);
  const n = h("button.no", { type: "button" }, no);
  const a = onAll ? h("button.yes", { type: "button" }, "Yes to all for this task") : null;
  const all = [y, n, a].filter(Boolean);
  const go = (fn) => async () => {
    all.forEach((b) => { b.disabled = true; });
    try { await fn(); problem(""); } catch (err) { problem(err.message); }
    look();
  };
  y.addEventListener("click", go(onYes));
  n.addEventListener("click", go(onNo));
  if (a) a.addEventListener("click", go(onAll));
  return h("div.buttons", {}, ...all);
}

function askView(a) {
  return h("div.ask", {},
    h("div.q", {}, `${a.agent} asks: may it do this?`),
    h("div.what", {}, `${a.tool}: ${a.summary}`),
    a.picture ? h("img", { src: `data:image/png;base64,${a.picture}`,
                           alt: "The phone's screen, what it would tap ringed" }) : null,
    // a.for_turn: asked only because the agent read something you didn't
    // write; one yes can cover the rest of this task (Dvara's gate.put)
    buttons(() => api(`/api/chat/asks/${encodeURIComponent(a.id)}`, { approve: true }),
            () => api(`/api/chat/asks/${encodeURIComponent(a.id)}`, { approve: false }),
            "Yes", "No",
            a.for_turn ? () => api(`/api/chat/asks/${encodeURIComponent(a.id)}`,
                                   { approve: true, for_turn: true }) : null));
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
  let changed = false;
  if (!chat.last) { box.replaceChildren(live); chat.title = ""; }
  if (data.lines.length) {
    const fresh = Boolean(chat.last);   // lines that came while the page was open
    for (const ln of data.lines) {
      if (ln.who === "notice") { lookNotices(); continue; }   // the bell's
      changed = true;
      // /new's answer: the window starts over, and says nothing itself
      if (ln.fresh) {
        queued.length = 0; stopVoice(); box.replaceChildren(live); chat.title = "";
        continue;
      }
      if (ln.transcript) {
        // back in an old one: its words are the window now
        box.replaceChildren(live);
        const [...views] = transcriptView(ln);
        chat.title = views.pop();
        for (const v of views) box.insertBefore(v, live);
        continue;
      }
      if (ln.who === "you" && !chat.title) chat.title = (ln.text || "").split("\n")[0].slice(0, 80);
      const view = lineView(ln);
      box.insertBefore(view, live);
      const listen = view.querySelector("button.listen");
      if (fresh && ln.speak && listen) playByItself(ln.id, listen);
    }
    chat.last = data.lines[data.lines.length - 1].id;
  }
  if (!live.isConnected) box.append(live);
  live.replaceChildren(...running.map(liveView));
  if (atEnd || data.lines.some((l) => l.who === "you")) box.scrollTop = box.scrollHeight;
  document.getElementById("waiting").replaceChildren(
    ...data.asks.map(askView), ...data.holds.map(holdView));
  chat.waiting = data.asks.length + data.holds.length;
  drawBell();
  chat.lessons = data.lessons || [];
  drawLesson();
  document.getElementById("chat-state").textContent =
    data.busy.length ? `${data.busy.join(", ")} is working…` : "";
  const wasBusy = chat.busy;
  chat.busy = data.busy.length > 0;
  drawHello();
  if (document.body.dataset.view === "chat") {
    document.getElementById("bar-title").textContent = chatTitle();
  }
  // a new conversation shows in the list once it has an answer
  if (changed && (wasBusy && !chat.busy || data.lines.some((l) => l.who === "agent"))) lookConvs();
}

function chatTitle() {
  if (chat.reading) return chat.reading.title;
  // Dvara's own title when it has one (a name you gave it, too)
  const here = chat.title ? openHere() : null;
  return (here && here.title) || chat.title || "New chat";
}

// The greeting, on a chat with nothing in it yet.
function drawHello() {
  const empty = !chat.reading && !document.querySelector("#lines > .line")
    && !document.querySelector("#live > *");
  show("hello", empty);
}

const SUGGEST = [
  ["What can you do for me?", null],
  ["Show my skills", "/skills"],
  ["What's on my schedule?", "/schedules"],
  ["What do you remember about me?", "/memory"],
];

function drawSuggest() {
  document.getElementById("suggest").replaceChildren(...SUGGEST.map(([words, word]) => {
    const b = h("button", { type: "button" }, words);
    b.addEventListener("click", () => send(word || words));
    return b;
  }));
}

// One look at a time: two at once (the timer's, and the one after a send)
// both asked "after N" and drew the same new answer twice, read aloud twice.
async function look() {
  while (chat.looking) await chat.looking;
  chat.looking = (async () => {
    try {
      const data = await api(`/api/chat?after=${chat.last}`);
      if (chat.last) data.lines = data.lines.filter((ln) => ln.id > chat.last);
      draw(data);
      if (!chat.sending) problem("");
    } catch (err) {
      problem(err.message);
    }
  })();
  try { await chat.looking; } finally { chat.looking = null; }
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
    // writing under one from the list carries it on: it's opened here
    // first (it stays open where else it was), then the words go to it
    const row = chat.reading;
    if (row && !row.here) {
      await api("/api/chat", { agent: row.agent, text: `/chats open ${row.id}` });
    }
    const to = row ? row.agent : agent;
    if (row && row.here) {
      // the window goes on from its words, which only the reading had
      const box = document.getElementById("lines");
      const live = document.getElementById("live");
      for (const ln of document.querySelectorAll("#past > .line")) box.insertBefore(ln, live);
      chat.title = row.title;
    }
    stopReading();
    const files = await Promise.all(chosen.map(async (f) => ({ name: f.name,
                                                               data: await asBase64(f) })));
    await api("/api/chat", files.length ? { agent: to, text, files } : { agent: to, text });
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

function openTeach() {
  const box = document.getElementById("teach");
  const what = document.getElementById("teach-what");
  if ((chat.lessons || []).some((l) => l.agent === document.getElementById("agent").value)) {
    problem("A lesson is open with this agent: press Done or Stop first.");
    return;
  }
  what.value = "";
  box.returnValue = "";        // Escape leaves the last open's answer otherwise
  box.showModal();
  what.focus();
}

function startTeach() {
  const box = document.getElementById("teach");
  const what = document.getElementById("teach-what");
  box.addEventListener("close", () => {
    const how = document.querySelector('input[name="teach-how"]:checked')?.value;
    const task = what.value.trim();
    if (box.returnValue !== "start" || !task) return;
    send(`/learn ${how === "watch" ? "watch" : "start"} ${task}`);
  });
  document.getElementById("lesson-done").addEventListener("click", () => send("/learn done"));
  document.getElementById("lesson-stop").addEventListener("click", () => send("/learn stop"));
  document.getElementById("agent").addEventListener("change", () => { drawLesson(); drawConvsMark(); });
}

async function say(event) {
  event.preventDefault();
  const text = document.getElementById("text");
  if (await send(text.value)) { text.value = ""; fitText(); }
}

// The box grows with what's written, up to a few lines.
function fitText() {
  const text = document.getElementById("text");
  text.style.height = "auto";
  // not drawn yet (the chat still hidden): its own one row, measured later
  text.style.height = text.scrollHeight ? `${text.scrollHeight}px` : "";
}

/* -- the words your agent answers: behind + and typed after / -----------------
   Each sends what a person would type on Telegram. Teach and Turned down
   open their own boxes. The / list narrows as you type and goes away when
   nothing matches, so a word it doesn't know is still sent as written. */

const WORDS = [
  ["/skills", "Skills", "What it has learned, and what's on offer"],
  ["/learn", "Learn this", "Keep what it just did as a skill"],
  ["teach", "Teach…", "A job one step at a time, by telling or showing"],
  ["/tools", "Tools", "What it can use"],
  ["/schedules", "Schedules", "What it does by itself, and when"],
  ["/memory", "Memory", "What it remembers about you"],
  ["declined", "Turned down…", "What you said no to remembering"],
  ["/phone", "Phone screen", "Your phone's screen now"],
  ["/doctor", "Check what's mine", "Accounts, schedules, watches, phones, limits"],
  ["/chats", "Conversations", "Every one, as a list in the chat"],
];

function useWord(word) {
  closeMenus();
  if (word === "teach") return openTeach();
  if (word === "declined") return openDeclined();
  const text = document.getElementById("text");
  text.value = "";
  fitText();
  send(word);
}

function drawPlus() {
  document.getElementById("plus-menu").replaceChildren(...WORDS.map(([word, label, hint]) =>
    menuItem(label, hint, () => useWord(word))));
}

const slash = { at: 0, shown: [] };

function drawSlash() {
  const text = document.getElementById("text");
  const menu = document.getElementById("slash");
  const typed = text.value;
  if (!/^\/\S*$/.test(typed)) { menu.hidden = true; return; }
  slash.shown = WORDS.filter(([word]) => word.startsWith("/") && word.startsWith(typed.toLowerCase()));
  if (!slash.shown.length) { menu.hidden = true; return; }
  slash.at = Math.min(slash.at, slash.shown.length - 1);
  menu.replaceChildren(...slash.shown.map(([word, label, hint], i) => {
    const b = h("button", { type: "button", role: "option",
      "aria-selected": String(i === slash.at) }, h("span", {}, `${word} — ${label}`), h("span.hint", {}, hint));
    b.addEventListener("mousedown", (e) => { e.preventDefault(); useWord(word); });
    return b;
  }));
  menu.hidden = false;
}

function slashKeys(e) {
  const menu = document.getElementById("slash");
  if (menu.hidden) return false;
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const n = slash.shown.length;
    slash.at = (slash.at + (e.key === "ArrowDown" ? 1 : n - 1)) % n;
    drawSlash();
    return true;
  }
  if ((e.key === "Enter" && !e.shiftKey) || e.key === "Tab") {
    e.preventDefault();
    useWord(slash.shown[slash.at][0]);
    return true;
  }
  if (e.key === "Escape") { e.preventDefault(); menu.hidden = true; return true; }
  return false;
}

/* -- the bell: what was sent to you unasked, and questions waiting ----------
   Dvara keeps what was sent to you (a schedule's answer, a watch, a sign-in
   that stopped) whatever New chat cleared; this browser remembers how far
   you've read. The count adds the questions waiting for your yes, which
   stay in the chat that asked. */

const notices = { rows: [], looking: false };

function readKey() { return `sarathi.notices.read.${me ? me.name : ""}`; }

async function lookNotices() {
  if (notices.looking || !chat.on) return;
  notices.looking = true;
  try {
    notices.rows = (await api("/api/chat/notices")).notices;
    drawBell();
    if (document.body.dataset.view === "notices") drawNotices(false);
  } catch (_) { /* the bell waits for the next look */ }
  notices.looking = false;
}

function unread() {
  const seen = Number(kept(readKey()) || 0);
  return notices.rows.filter((n) => n.id > seen).length;
}

function drawBell() {
  const n = unread() + chat.waiting;
  const count = document.getElementById("bell-count");
  count.hidden = !n;
  count.textContent = n > 99 ? "99+" : String(n);
  document.title = n ? `(${n}) Sarathi` : "Sarathi";
}

function drawNotices(opening) {
  const seen = Number(kept(readKey()) || 0);
  const rows = notices.rows.map((n) => h(`article.notice${n.id > seen ? ".unread" : ""}`, {},
    h("div.meta", {}, `${when(n.at)}${n.agent ? ` · ${n.agent}` : ""}`),
    (() => { const b = bubble(n.text, "notice"); b.classList.add("notice-text"); return b; })(),
    (n.files || []).map((name, i) => {
      const b = h("button.file.quiet", { type: "button" }, `⤓ ${name}`);
      b.addEventListener("click", () => download(n.id, i, name));
      return b;
    })));
  document.getElementById("notices-rows").replaceChildren(...(rows.length ? rows
    : [h("p.empty", {}, "Nothing yet. What a schedule or a watch sends you shows here.")]));
  const waiting = chat.waiting;
  const toChat = h("button.yes", { type: "button" }, "Go to the chat");
  toChat.addEventListener("click", () => go("chat"));
  document.getElementById("notices-waiting").replaceChildren(...(waiting
    ? [h("div.ask", {}, h("div.q", {}, `${waiting} question${waiting === 1 ? "" : "s"} waiting for your yes`),
         h("div.buttons", {}, toChat))] : []));
  // opened, they're read; the marks stay until you next come back
  if (opening && notices.rows.length) {
    keep(readKey(), String(notices.rows[0].id));
    drawBell();
  }
}

/* -- the list: every conversation, kept by Dvara as it goes (past.py) -------
   Every road's, newest first under Pinned / Today / Yesterday / Previous 7
   days / Older, each marked by where it went on (this page, Telegram, a
   puck). Searched by any words in it (Dvara's full-text index, every
   conversation and not only the rows drawn). Picked, one is read in the
   chat's place; writing under it carries it on. Its ⋯ renames, pins,
   shares or deletes it for good. */

const past = { q: "", timer: null, rows: [], looking: null };

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

// Where it went on, as a mark: 💬 this page, ✈ Telegram, 🔊 a puck. A
// puck's conversation kept before its puck was named says only "vaani".
function roadMark(road) {
  if (road === "the page") return "💬";
  if (road === "Telegram") return "✈";
  if (road === "vaani" || / puck$/.test(road)) return "🔊";
  return "•";
}

function roadName(road) {
  return road === "vaani" ? "puck" : road.replace(/^the /, "");
}

function roadsSaid(r) {
  const roads = r.roads && r.roads.length ? r.roads : [r.road];
  return roads.map((x) => `${roadMark(x)} ${roadName(x)}`).join(" · ");
}

function groupOf(r) {
  if (r.pinned) return "Pinned";
  const d = new Date(r.updated_at);
  const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const ago = Math.round((day(new Date()) - day(d)) / 86400000);
  return ago <= 0 ? "Today" : ago === 1 ? "Yesterday" : ago < 7 ? "Previous 7 days"
    : ago < 30 ? "Previous 30 days" : "Older";
}

// One look at a time, like the chat's.
async function lookConvs() {
  if (past.looking) return past.looking;
  past.looking = (async () => {
    try {
      past.rows = (await api(`/api/chat/chats?q=${encodeURIComponent(past.q)}`)).rows;
      drawConvs();
      if (document.body.dataset.view === "chat") {
        document.getElementById("bar-title").textContent = chatTitle();
      }
      // Dvara can be in a conversation the window no longer shows (its lines
      // aged out, or it was opened elsewhere): shown, so nothing written
      // lands in a conversation the page called new
      const here = openHere();
      if (here && !past.q && !chat.reading && !chat.sending
          && !document.querySelector("#lines > .line") && !document.querySelector("#live > *")) {
        openPast(here);
      }
    } catch (err) {
      document.getElementById("convs").replaceChildren(h("p.empty", {}, err.message));
    }
  })();
  try { await past.looking; } finally { past.looking = null; }
}

function drawConvs() {
  const box = document.getElementById("convs");
  if (!past.rows.length) {
    box.replaceChildren(h("p.empty", {}, past.q
      ? `None of your conversations say “${past.q}”.`
      : "Your conversations show here as you talk."));
    return;
  }
  const out = [];
  let group = null;
  for (const r of past.rows) {
    const g = groupOf(r);
    if (g !== group) { out.push(h("div.group", {}, g)); group = g; }
    out.push(convRow(r));
  }
  box.replaceChildren(...out);
  drawConvsMark();
}

// The one you're in (or reading) is marked in the list.
function drawConvsMark() {
  const agent = document.getElementById("agent").value;
  const onChat = document.body.dataset.view === "chat";
  for (const el of document.querySelectorAll(".conv")) {
    const r = past.rows.find((x) => x.id === el.dataset.id);
    const current = onChat && r && (chat.reading ? chat.reading.id === r.id
      : r.here && r.agent === agent && Boolean(chat.title));
    el.setAttribute("aria-current", String(Boolean(current)));
  }
}

function convRow(r) {
  const open = h("button.conv-open", { type: "button", title: r.title },
    h("span.conv-title", {}, r.title || "(no words)"),
    h("span.conv-meta", {}, roadsSaid(r) + (chat.agents.length > 1 ? ` · ${r.agent}` : "")));
  open.addEventListener("click", () => openPast(r));
  const more = h("button.conv-more", { type: "button", "aria-haspopup": "menu",
    "aria-expanded": "false", "aria-label": `More for “${r.title}”` }, "⋯");
  const menu = h("div.menu", { role: "menu", hidden: "" });
  more.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.replaceChildren(...rowMenu(r, row));
    toggleMenu(more, menu);
  });
  const row = h("div.conv", { "data-id": r.id }, open, more, menu,
    r.snippet ? snippetView(r.snippet) : null);
  return row;
}

function rowMenu(r, row) {
  const items = [
    menuItem("Rename", null, () => renameRow(r, row)),
    menuItem(r.pinned ? "Unpin" : "Pin to top", null, async () => {
      try { await api(`/api/chat/chats/${encodeURIComponent(r.id)}/pin`, { pinned: !r.pinned }); }
      catch (err) { problem(err.message); }
      lookConvs();
    }),
    menuItem("Save as PDF", "Opens the print window: pick Save as PDF", async () => {
      try { printPast(await pastRead(r.id)); } catch (err) { problem(err.message); }
    }),
    menuItem("Download", "A Markdown file: any notes app opens it", async () => {
      try {
        const made = await pastFile(r);
        const url = URL.createObjectURL(made);
        const a = h("a", { href: url, download: made.name });
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
      } catch (err) { problem(`Couldn't download it: ${err.message}`); }
    }),
  ];
  if (navigator.canShare) {
    items.push(menuItem("Send…", "WhatsApp, email, …", async () => {
      try {
        const made = await pastFile(r);
        if (navigator.canShare({ files: [made] })) await navigator.share({ files: [made], title: r.title });
        else await navigator.share({ title: r.title, text: await made.text() });
      } catch (err) { if (err.name !== "AbortError") problem(`Not sent: ${err.message}`); }
    }));
  }
  items.push(h("hr"));
  const del = menuItem("Delete", r.open ? "It's open in a chat now: start a new chat there first" : null,
    async () => {
      if (!confirm(`Delete “${r.title}” for good? It can't be brought back.`)) return;
      try {
        await api(`/api/chat/chats/${encodeURIComponent(r.id)}/delete`, {});
        if (chat.reading && chat.reading.id === r.id) stopReading();
        problem("");
      } catch (err) { problem(err.message); }
      lookConvs();
    }, "danger");
  del.disabled = r.open;
  items.push(del);
  return items;
}

// Renamed in place: Enter keeps it, Escape leaves it, empty gives its first words back.
function renameRow(r, row) {
  const input = h("input.rename", { value: r.title, "aria-label": "A name for it", maxlength: "80" });
  row.replaceChildren(input);
  input.focus();
  input.select();
  let done = false;
  const finish = async (save) => {
    if (done) return;
    done = true;
    if (save && input.value.trim() !== r.title) {
      try {
        await api(`/api/chat/chats/${encodeURIComponent(r.id)}/rename`, { title: input.value });
      } catch (err) { problem(err.message); }
    }
    lookConvs();
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); finish(true); }
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); finish(false); }
  });
  input.addEventListener("blur", () => finish(true));
}

async function pastRead(id) {
  return api(`/api/chat/chats/${encodeURIComponent(id)}`);
}

// One from the list, read in the chat's place. The one open here already is
// the chat itself; any other is read, and writing under it carries it on.
async function openPast(r) {
  sideDone();
  if (location.hash.slice(1) !== "chat" && wantedView() !== "chat") location.hash = "chat";
  const agent = document.getElementById("agent").value;
  if (r.here && r.agent === agent && document.querySelector("#lines > .line")) {
    stopReading();
    return;
  }
  let d;
  try { d = await pastRead(r.id); } catch (err) { problem(err.message); return; }
  chat.reading = { ...r, title: d.title || r.title };
  const box = document.getElementById("past");
  const lines = d.entries.map((e) => {
    if (e.who === "tool") {
      return h("details.tool", {},
        h("summary", {}, `· ${e.name}${e.error ? " (failed)" : ""}`),
        h("pre", {}, e.args), e.result ? h("pre", {}, `→ ${e.result}`) : null);
    }
    return h(`div.line.${e.who}`, {},
      e.who === "you" ? null : h("span.tag", {}, h("span.who", {}, d.agent)),
      bubble(e.text, e.who));
  });
  box.replaceChildren(
    h("div.past-head", {}, h("h2", {}, chat.reading.title),
      h("div.meta", {}, `${when(d.started_at)} · ${d.agent} · ${roadsSaid(r)}`
        + (d.model ? ` · ${d.model}` : ""))),
    ...lines);
  const back = r.here ? null : h("button.quiet", { type: "button" }, "Back to the chat you're in");
  if (back) back.addEventListener("click", stopReading);
  const elsewhere = (r.roads || [r.road]).filter((x) => x !== "the page").map(roadName);
  document.getElementById("carry").replaceChildren(
    h("span", {}, r.here ? "You're in this conversation. Write below to carry it on."
      : "Write below to carry this conversation on here" +
        (elsewhere.length && r.open ? ` (it stays open on ${elsewhere.join(" and ")} too).` : ".")),
    ...(back ? [back] : []));
  show("carry", true);
  show("past", true);
  show("lines", false);
  const pick = document.getElementById("agent");
  if ([...pick.options].some((o) => o.value === r.agent)) pick.value = r.agent;
  drawLesson();
  drawHello();
  box.scrollTop = box.scrollHeight;
  document.getElementById("bar-title").textContent = chatTitle();
  drawConvsMark();
  document.getElementById("text").focus();
}

function stopReading() {
  if (!chat.reading) return;
  chat.reading = null;
  show("past", false);
  show("carry", false);
  show("lines", true);
  drawHello();
  const box = document.getElementById("lines");
  box.scrollTop = box.scrollHeight;
  if (document.body.dataset.view === "chat") {
    document.getElementById("bar-title").textContent = chatTitle();
  }
  drawConvsMark();
}

// The conversation Dvara has open on this page with the agent picked.
function openHere() {
  const agent = document.getElementById("agent").value;
  return past.rows.find((r) => r.here && r.agent === agent) || null;
}

// New chat: the window empties (Dvara keeps the one before, in the list).
async function newChat() {
  sideDone();
  if (wantedView() !== "chat") location.hash = "chat";
  const wasHere = openHere();
  stopReading();
  const text = document.getElementById("text");
  if (document.querySelector("#lines > .line") || wasHere) {
    await send("/new");
    await lookConvs();
  }
  text.focus();
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

function printPast(d) {
  const area = document.getElementById("print-chat");
  const blocks = [h("header", {}, h("h1", {}, d.title),
    // the full date: a printed page outlives "today"
    h("p", {}, `${new Date(d.started_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}`
      + ` · ${d.agent} · on ${(d.roads && d.roads.length ? d.roads : [d.road]).join(" and ")}`))];
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

/* -- turned down: what /remember not said no to, kept by Dvara so it isn't
   offered again (remembering.py). Undo is by the words, not a number, so a
   list drawn a minute ago can't undo the wrong one; it puts the fact back
   on their list, and only /remember keeps it. */

function declinedSaid(text) {
  const el = document.getElementById("declined-said");
  el.hidden = !text;
  el.textContent = text || "";
}

async function openDeclined() {
  const box = document.getElementById("declined");
  if (!box.open) box.showModal();
  declinedSaid("");
  let data;
  try { data = await api("/api/chat/declined"); }
  catch (err) { drawDeclined([]); declinedSaid(err.message); return; }
  drawDeclined(data.declined);
}

function drawDeclined(declined) {
  const rows = document.getElementById("declined-rows");
  if (!declined.length) {
    rows.replaceChildren(h("p.meta", {}, "Nothing turned down. When your agent lists what it "
      + "noticed about you, /remember not 2 turns one down for good, and it shows here."));
    return;
  }
  rows.replaceChildren(...declined.map((fact) => {
    const undo = h("button.quiet", { type: "button",
      title: "Offer it again: back on your list, not kept" }, "Undo");
    undo.addEventListener("click", async () => {
      undo.disabled = true;
      try {
        const data = await api("/api/chat/declined", { undo: [fact] });
        drawDeclined(data.declined);
        declinedSaid("");
        const n = data.waiting;
        document.getElementById("declined-rows").prepend(h("p.meta", {},
          `Back on your list, not kept yet: “${fact.replace(/\.\s*$/, "")}”. ${n} waiting: `
          + "send /remember to see them, and /remember with a number to keep one."));
      } catch (err) { undo.disabled = false; declinedSaid(err.message); }
    });
    return h("div.hrow", {}, h("div", {}, h("div.title", {}, fact)), undo);
  }));
}

function startList() {
  document.getElementById("declined-close").addEventListener("click",
    () => document.getElementById("declined").close());
  document.getElementById("new-chat").addEventListener("click", newChat);
  document.getElementById("convs-q").addEventListener("input", (e) => {
    clearTimeout(past.timer);
    past.timer = setTimeout(() => { past.q = e.target.value; lookConvs(); }, 200);
  });
  document.getElementById("notices-read").addEventListener("click", () => {
    if (notices.rows.length) keep(readKey(), String(notices.rows[0].id));
    drawNotices(false);
    drawBell();
  });
  lookConvs();
}

function startChat() {
  chat.on = true;
  document.getElementById("chat").hidden = false;
  document.getElementById("notices").hidden = false;
  document.getElementById("say").addEventListener("submit", say);
  document.getElementById("record").addEventListener("click", recordToggle);
  document.getElementById("files").addEventListener("change", (event) => {
    chosen.push(...event.target.files);
    event.target.value = "";
    drawChosen();
  });
  const text = document.getElementById("text");
  text.addEventListener("keydown", (e) => {
    if (e.isComposing || slashKeys(e)) return;
    if (e.key === "Enter" && !e.shiftKey) say(e);
  });
  text.addEventListener("input", () => { fitText(); slash.at = 0; drawSlash(); });
  text.addEventListener("blur", () => { document.getElementById("slash").hidden = true; });
  const plus = document.getElementById("plus");
  plus.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleMenu(plus, document.getElementById("plus-menu"));
  });
  if (phone.matches) text.placeholder = "Message your agent";
  fitText();
  drawPlus();
  drawSuggest();
  startList();
  startTeach();
  drawView();
  look().then(lookAgain);
}

document.addEventListener("DOMContentLoaded", () => {
  if (kept(SIDE) === "closed") document.body.classList.add("side-closed");
  drawView();
  window.addEventListener("hashchange", drawView);
  document.getElementById("side-close").addEventListener("click", closeSide);
  document.getElementById("side-open").addEventListener("click", openSide);
  document.getElementById("scrim").addEventListener("click", closeSide);
  const accountOpen = document.getElementById("account-open");
  accountOpen.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleMenu(accountOpen, document.getElementById("account-menu"));
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".menu")) closeMenus(); });
  // Escape closes a menu, then leaves another view for the chat (a dialog takes it first)
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || document.querySelector("dialog[open]")) return;
    if (document.querySelector(".menu:not([hidden])")) { closeMenus(); return; }
    if (document.body.classList.contains("side-shown")) { closeSide(); return; }
    if (chat.on && document.body.dataset.view !== "chat") location.hash = "chat";
  });
  refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, EVERY);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
});
