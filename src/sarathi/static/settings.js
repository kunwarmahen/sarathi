"use strict";
// The owner's Settings: every settings file as forms, and each as text.
// Uses page.js's h(), api() and show(). Every value goes in as text.
// Nothing is decided here: each change goes to the program whose file it
// is (editing.py on the server), which checks it before writing.

const sets = { data: null, tab: "people", editing: null };

const TABS = [["people", "People"], ["agents", "Agents"], ["rules", "Rules"],
              ["accounts", "Accounts"], ["sarathi", "Sarathi"], ["keys", "Keys"]];

const RUNGS = { "": "Dvara's default (read only)", read_only: "Read only: never asked",
                ask: "Asked before anything changes", yolo: "Never asked: anything" };

function said(text, bad) {
  const el = document.getElementById("settings-said");
  el.textContent = text || "";
  el.classList.toggle("warn", !!bad);
}

async function drawSettings() {
  show("settings", true);
  try {
    sets.data = await api("/api/settings");
    document.getElementById("settings-state").textContent = "";
  } catch (err) {
    document.getElementById("settings-state").textContent = `Couldn't read them: ${err.message}`;
    return;
  }
  drawTabs();
}

function drawTabs() {
  const bar = document.getElementById("settings-tabs");
  bar.replaceChildren(...TABS.map(([id, label]) => {
    const b = h("button.tab", { type: "button", role: "tab",
                                "aria-selected": sets.tab === id ? "true" : "false" }, label);
    b.addEventListener("click", () => { sets.tab = id; sets.editing = null; said(""); drawTabs(); });
    return b;
  }));
  const draw = { people: drawPeopleTab, agents: drawAgentsTab, rules: drawRulesTab,
                 accounts: drawAccountsTab, sarathi: drawSarathiTab, keys: drawKeysTab };
  document.getElementById("settings-body").replaceChildren(
    ...[draw[sets.tab]()].flat().filter((kid) => kid != null));
}

// A change, sent; the result said; everything read again.
async function save(path, body, after) {
  said("Saving…");
  try {
    const got = await api(path, body);
    sets.editing = null;
    if (got.restart) needsApply();
    await drawSettings();
    said(got.said || "Saved.");
    if (after) after(got);
  } catch (err) {
    said(err.message, true);
  }
}

function needsApply() {
  const box = document.getElementById("settings-apply");
  const go = h("button.open", { type: "button" }, "Apply: start everything again");
  go.addEventListener("click", async () => {
    go.disabled = true;
    try {
      const got = await api("/api/settings/apply", {});
      box.replaceChildren(got.said);
    } catch (err) { box.replaceChildren(`That didn't work: ${err.message}`); }
  });
  box.replaceChildren(h("span", {}, "Some of this takes effect when everything starts again. "), go);
  box.hidden = false;
}

// ---- small pieces ------------------------------------------------------------------

function field(label, input, hint) {
  const id = `f-${Math.random().toString(36).slice(2, 9)}`;
  input.id = id;
  return h("div.field", {}, h("label", { for: id }, label), input,
           hint ? h("div.hint", {}, hint) : null);
}

function text(value, attrs) {
  const el = h("input", { type: "text", ...(attrs || {}) });
  el.value = value == null ? "" : String(value);
  return el;
}

function check(on) {
  const el = h("input", { type: "checkbox" });
  el.checked = !!on;
  return el;
}

function pick(options, value) {
  const el = h("select", {});
  for (const [v, label] of options) {
    const o = h("option", { value: v }, label);
    if (String(value ?? "") === v) o.selected = true;
    el.append(o);
  }
  return el;
}

function lines(list) {
  const el = h("textarea", { rows: "3" });
  el.value = (list || []).join("\n");
  return el;
}

const listOf = (el) => el.value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean);
const numOr = (el) => (el.value.trim() === "" ? null : Number(el.value));

function row(...kids) { return h("div.buttons", {}, ...kids); }

function button(label, onClick, kind = "open") {
  const b = h(`button.${kind}`, { type: "button" }, label);
  b.addEventListener("click", onClick);
  return b;
}

// "Edit as text": the whole file, checked by its program before it's saved.
function asText(kind, name, body, path) {
  const area = h("textarea.file", { rows: "16", spellcheck: "false" });
  area.value = body || "";
  const go = button("Save the file", () => save(`/api/settings/text/${kind}`,
                                                 { text: area.value, name }));
  return h("details.astext", {}, h("summary", {}, "Edit as text"),
           path ? h("div.hint", {}, path) : null, area, row(go));
}

function warnBox(textValue) {
  return textValue ? h("div.warn", {}, textValue) : null;
}

// ---- People ------------------------------------------------------------------------

function dvaraOff() {
  return [h("p.meta", {}, sets.data.dvara_problem ||
    "Dvara is off. Turn it on under Sarathi to give other people your agents.")];
}

function drawPeopleTab() {
  const d = sets.data.dvara;
  if (!d) return dvaraOff();
  const owner = sets.data.sarathi.dvara?.owner;
  const out = [warnBox(d.actors_problem)];
  if (sets.data.strangers.length) {
    out.push(h("div.card", {}, h("div.meta", {}, "Messaged your Telegram bot, but not on the list:"),
      ...sets.data.strangers.map((id) => row(h("span.mono", {}, id),
        button("Add as a new person", () => { sets.editing = { new: true, telegram: [id] };
                                              drawTabs(); })))));
  }
  if (sets.editing && sets.editing.new) out.push(personForm(sets.editing, true));
  else out.push(row(button("Add a person", () => { sets.editing = { new: true }; drawTabs(); })));
  for (const p of d.people) {
    if (sets.editing && sets.editing.id === p.id) { out.push(personForm(p, false)); continue; }
    const agents = p.agents ? p.agents.join(", ") : "every agent";
    const accounts = p.setu === "none" ? "no accounts" : p.setu === "own" ? "their own accounts"
      : `accounts in ${p.setu}${p.setu_manage ? " (may change them)" : ""}`;
    const bits = [agents, accounts,
                  p.max_usd_per_day != null ? `$${p.max_usd_per_day} a day` : "no daily limit",
                  p.telegram.length ? `Telegram ${p.telegram.join(", ")}` : "no Telegram",
                  p.phones ? `phones: ${p.phones.join(", ")}`
                    : p.phone ? "the phone" : null].filter(Boolean);
    out.push(h("article.card", {},
      h("div.card-head", {}, h("h3", {}, p.id + (p.id === owner ? " (you)" : ""))),
      h("div.meta", {}, bits.join(" · ")),
      row(button("Change", () => { sets.editing = p; drawTabs(); }),
              p.id === owner ? null : button("Remove", () => {
                if (confirm(`Remove ${p.id}? They lose their chat and sign-in here. ` +
                            "Their folder and history are kept.")) {
                  save(`/api/settings/person/${encodeURIComponent(p.id)}`, { remove: true });
                }
              }, "no"))));
  }
  out.push(asText("actors", "", d.actors.text, d.actors.path));
  return out;
}

function personForm(p, isNew) {
  const d = sets.data.dvara;
  const ownerSetu = (d.people.find((x) => x.id === sets.data.sarathi.dvara?.owner) || {}).setu;
  const shared = ownerSetu && !["own", "none"].includes(ownerSetu) ? ownerSetu
    : "~/.local/state/setu";
  const name = text(p.id || "", { autocapitalize: "none", placeholder: "priya" });
  const allAgents = check(!p.agents);
  const agentBoxes = d.agents.map((a) => {
    const c = check(p.agents ? p.agents.includes(a.name) : false);
    c.dataset.agent = a.name;
    return h("label.inline", {}, c, ` ${a.name}`);
  });
  const setu = pick([["none", "None"], ["own", "Their own (they connect them from the chat)"],
                     [shared, "This computer's accounts (yours)"]],
                    p.setu && !["own", "none"].includes(p.setu) ? shared : (p.setu || "none"));
  const manage = check(p.setu_manage);
  const rung = pick(Object.entries(RUNGS), p.permissions || "");
  const day = text(p.max_usd_per_day ?? "", { inputmode: "decimal", placeholder: "no limit" });
  const turn = text(p.max_usd_per_turn ?? "", { inputmode: "decimal", placeholder: "the agent's own" });
  const receipt = pick([["", "Nothing"], ["cost", "What it cost"], ["remaining", "What's left today"]],
                       p.receipt || "");
  const phone = check(p.phone);
  // With several phones named (Settings → Sarathi → Your phone), a box
  // for each: whose each is, said here (Dvara's phones = [...]).
  const named = sets.data.sarathi?.phone?.named || [];
  const phoneBoxes = named.map((n) => {
    // phone = true is every phone: each ticked, so a Save keeps them all
    const c = check(p.phone || (p.phones || []).includes(n.name));
    c.dataset.phone = n.name;
    return h("label.inline", {}, c, ` ${n.name} (${n.kind})`);
  });
  const telegram = text((p.telegram || []).join(", "), { inputmode: "numeric",
                                                          placeholder: "8675309" });
  const go = button(isNew ? "Add" : "Save", () => {
    const who = isNew ? name.value.trim() : p.id;
    if (!who) return said("Give them a name (letters and numbers).", true);
    const agents = allAgents.checked ? null
      : agentBoxes.map((l) => l.querySelector("input")).filter((c) => c.checked)
          .map((c) => c.dataset.agent);
    save(`/api/settings/person/${encodeURIComponent(who)}`, {
      agents, setu: setu.value, setu_manage: setu.value !== "own" && setu.value !== "none"
        && manage.checked, permissions: rung.value || null, max_usd_per_day: numOr(day),
      max_usd_per_turn: numOr(turn), receipt: receipt.value || null,
      phone: named.length ? false : phone.checked,
      phones: named.length ? phoneBoxes.map((l) => l.querySelector("input"))
        .filter((c) => c.checked).map((c) => c.dataset.phone) : null,
      telegram: listOf(telegram) });
  });
  return h("article.card.form", {},
    isNew ? field("Name", name, "The name they sign in with. Letters, numbers, - and _.")
          : h("h3", {}, p.id),
    h("div.field", {}, h("span.label", {}, "Agents they may use"),
      h("label.inline", {}, allAgents, " Every agent"), h("div.checks", {}, ...agentBoxes)),
    field("Accounts their agents use", setu),
    h("label.inline", {}, manage, " They may connect and disconnect those from the chat"),
    field("Asking before changes", rung),
    field("Daily allowance (US dollars)", day),
    field("Most per message (US dollars)", turn),
    field("Under each answer", receipt),
    field("Telegram ids", telegram, "Their numbers, comma-separated. Someone who messages the " +
          "bot and isn't on the list shows above, to add."),
    named.length
      ? h("div.field", {}, h("span.label", {}, "Their phones (each is one person's)"),
          h("div.checks", {}, ...phoneBoxes))
      : h("label.inline", {}, phone, " Their agents may work the phone on this computer"),
    row(go, button("Cancel", () => { sets.editing = null; drawTabs(); }, "linkish")));
}

// ---- Agents ------------------------------------------------------------------------

function drawAgentsTab() {
  const d = sets.data.dvara;
  if (!d) return dvaraOff();
  const out = [];
  const newName = text("", { autocapitalize: "none", placeholder: "helper" });
  const example = pick(d.examples.map((e) => [e, e]), d.examples[0]);
  if (d.examples.length) {
    out.push(h("div.card", {}, h("h3", {}, "Add an agent"),
      field("Name", newName), field("Start from", example, "One of Dvara's examples, " +
            "copied; change it after."),
      row(button("Add", () => save(`/api/settings/agent/${encodeURIComponent(
        newName.value.trim())}`, { from_example: example.value })))));
  }
  for (const a of d.agents) {
    if (sets.editing && sets.editing.name === a.name) { out.push(agentForm(a)); continue; }
    const t = a.tables || {};
    const bits = [t.agent?.description, t.model?.model ? `model ${t.model.model}` : "Sarathi's model",
                  t.memory?.via && t.memory.via !== "off" ? "remembers people" : null,
                  (t.connections?.needs || []).length ? `accounts: ${t.connections.needs.join(", ")}` : null,
                  (t.tools?.allow || []).length ? `tools: ${t.tools.allow.join(", ")}` : null]
      .filter(Boolean);
    out.push(h("article.card", {}, h("div.card-head", {}, h("h3", {}, a.name)),
      warnBox(a.problem), h("div.meta", {}, bits.join(" · ")),
      learnedList(a),
      row(button("Change", () => { sets.editing = a; drawTabs(); }),
              button("Remove", () => {
                if (confirm(`Remove ${a.name}? Its folder is moved aside, not deleted.`)) {
                  save(`/api/settings/agent/${encodeURIComponent(a.name)}`, { remove: true });
                }
              }, "no"))));
  }
  return out;
}

function agentForm(a) {
  const t = a.tables || {};
  const desc = text(t.agent?.description || "");
  const provider = pick([["", "Sarathi's"], ...sets.data.sarathi.providers.map((p) => [p, p])],
                        t.model?.provider || "");
  const model = text(t.model?.model || "", { placeholder: "Sarathi's model" });
  const memory = pick([["", "Doesn't remember people"], ["local", "Remembers each person"]],
                      t.memory?.via && t.memory.via !== "off" ? "local" : "");
  const picker = toolPicker(a);
  // How many tools a message is sent: automatic sends, past twenty, only
  // the ones the message points at (a local model's window overflows
  // otherwise); 0 sends every tool, every time.
  const perTurn = t.tools?.per_turn;
  const sent = pick([["", "Automatic: past 20, the ones the message needs"],
                     ["0", "Every tool, every message"],
                     ...(perTurn > 0 ? [[String(perTurn), `${perTurn} per message`]] : [])],
                    perTurn == null ? "" : String(perTurn));
  const needs = lines(t.connections?.needs);
  const budget = text(t.budget?.max_usd_per_turn ?? "", { inputmode: "decimal",
                                                         placeholder: "no limit" });
  const mode = pick([["", "The package's default"], ["read_only", RUNGS.read_only],
                     ["ask", RUNGS.ask], ["yolo", RUNGS.yolo]], t.permissions?.mode || "");
  const prompt = h("textarea", { rows: "8" });
  prompt.value = a.prompt || "";
  const go = button("Save", () => {
    const allow = picker.allow();
    if (allow && !allow.length) {
      return said("Tick at least one tool, or \"Every tool it has\".", true);
    }
    save(`/api/settings/agent/${encodeURIComponent(a.name)}`, {
    tables: {
      agent: { description: desc.value.trim() || null },
      model: { provider: provider.value || null, model: model.value.trim() || null },
      memory: { via: memory.value || null },
      tools: { allow, per_turn: sent.value === "" ? null : Number(sent.value) },
      connections: { needs: listOf(needs).length ? listOf(needs) : null },
      budget: { max_usd_per_turn: numOr(budget) },
      permissions: { mode: mode.value || null },
    },
    prompt: prompt.value });
  });
  return h("article.card.form", {}, h("h3", {}, a.name),
    field("What it does", desc),
    field("Provider", provider), field("Model", model, "Empty: the one Sarathi uses."),
    field("Memory", memory),
    picker.el,
    field("Tools sent each message", sent, "Automatic keeps a local model's window from overflowing as accounts are added; nothing to change when you connect one."),
    field("Accounts it needs", needs, "One per line, connector:level, e.g. gmail:read; *:read is every account."),
    field("Most per message (US dollars)", budget),
    field("Asking before changes", mode),
    field("Its instructions (" + a.prompt_file + ")", prompt),
    row(go, button("Cancel", () => { sets.editing = null; drawTabs(); }, "linkish")),
    asText("agent", a.name, a.text, a.path));
}

// Type to filter a long list, the same box as on Yantra's page: only the
// rows holding every typed word stay, any case, and "3 of 51" says rows
// are hidden. Rows are only hidden, never redrawn, so a ticked box that's
// filtered out stays ticked and is saved. Short lists get no box.
const FILTER_MIN = 6;

function filterBox(list, rowSel, what, groupSel) {
  const rows = [...list.querySelectorAll(rowSel)];
  if (rows.length < FILTER_MIN) return null;
  const input = h("input", { type: "search", placeholder: `Type to filter ${what}`,
                             "aria-label": `Filter ${what}`, spellcheck: "false" });
  const count = h("span.count", { "aria-live": "polite" }, String(rows.length));
  input.addEventListener("input", () => {
    const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const r of rows) {
      const text = (r.textContent + " " + (r.title || "")).toLowerCase();
      const hit = words.every((w) => text.includes(w));
      r.classList.toggle("filtered-out", !hit);
      if (hit) shown++;
    }
    // a group whose every row is hidden goes too, heading and all
    for (const g of groupSel ? list.querySelectorAll(groupSel) : []) {
      g.classList.toggle("filtered-out",
        ![...g.querySelectorAll(rowSel)].some((r) => !r.classList.contains("filtered-out")));
    }
    count.textContent = words.length ? `${shown} of ${rows.length}` : String(rows.length);
  });
  return h("div.list-filter", {}, input, count);
}

// What this agent's people kept as skills (Dvara's promoting.py). A skill
// with one script can become a tool: its script runs once as a test, and
// it's kept, for that person only, if the test passes.
function learnedList(a) {
  const rows = a.learned || [];
  if (!rows.length) return null;
  const list = h("div.learned", {}, h("div.label", {}, "Skills its people kept"),
    ...rows.map((r) => {
      const how = `worked ${r.worked}, failed ${r.failed}` +
        (r.in_a_row ? `, ${r.in_a_row} in a row` : "");
      const can = r.script && !r.tool && !r.stale;
      const make = can ? button(r.suggest ? "Make it a tool (it's earned it)" : "Make it a tool",
        () => {
          if (!confirm(`Make ${r.name} a tool for ${r.person}? Its script runs once now as ` +
                       "a test, and it's kept only if the test passes. This takes up to a " +
                       "few minutes.")) return;
          save(`/api/settings/tool/${encodeURIComponent(a.name)}`,
               { person: r.person, skill: r.name });
        }, r.suggest ? "open" : "linkish") : null;
      const undo = r.tool ? button("Stop using as a tool", () => {
        if (!confirm(`Stop using ${r.tool} as a tool? ${r.name} stays, as written steps ` +
                     "the agent reads, and keeps its record.")) return;
        save(`/api/settings/tool/${encodeURIComponent(a.name)}`,
             { person: r.person, skill: r.name, remove: true });
      }, "linkish") : null;
      return h("div.learned-row", {},
        h("span", {}, h("b", {}, r.name), ` — ${r.person} · ${how}` +
          (r.tool ? ` · a tool: ${r.tool}` : "") + (r.stale ? " · set aside after failing" : "") +
          (!r.script && !r.tool ? " · written steps, no script" : "")),
        make, undo);
    }));
  const box = filterBox(list, ".learned-row", "skills");
  if (box) list.children[0].after(box);
  return list;
}

// The boxes come from Dvara (its toolbox.py): Yantra's own tools, Dvara's,
// and the families Samay and Sparsh bring, each saying whether it asks.
// What no box stands for stays as written, under Advanced.
function toolPicker(a) {
  const rows = sets.data.dvara.toolbox || [];
  const has = a.tools || { every: true, ticked: [], advanced: [], seen: [] };
  const every = check(has.every);
  const boxes = [];
  const groups = new Map();
  for (const r of rows) {
    const c = check(has.every || has.ticked.includes(r.name));
    c.dataset.tool = r.name;
    boxes.push(c);
    const members = (r.members || []).map((m) => m.name.split("__").pop());
    const line = h("label.tool", { title: r.name }, c,
      h("span", {}, r.said, " ",
        h("span.asks", {}, r.asks ? "asks you first" : "runs unasked")),
      members.length ? h("div.hint", {}, members.join(", ")) : null);
    if (!groups.has(r.group)) groups.set(r.group, []);
    groups.get(r.group).push(line);
  }
  const advanced = lines(has.advanced);
  const list = h("div.tools", {}, ...[...groups].map(([g, kids]) =>
    h("div.toolgroup", {}, h("div.label", {}, g), ...kids)));
  const box = filterBox(list, "label.tool", "tools", ".toolgroup");
  if (box) list.prepend(box);
  const sync = () => { list.hidden = every.checked; };
  every.addEventListener("change", sync);
  sync();
  const el = h("div.field", {}, h("span.label", {}, "Tools it may use"),
    h("label.inline", {}, every, " Every tool it has (no list)"), list,
    h("details", {}, h("summary", {}, "Advanced: other names"),
      advanced, h("div.hint", {}, "One per line, for tools no box stands for, e.g. " +
                  "amazon_*. Accounts come with \"Accounts it needs\" below, not here.")),
    h("div.hint", {}, "\"Asks you first\" is a question on the person's chat unless a " +
      "standing answer on the Rules tab says otherwise."));
  return { el, allow: () => every.checked ? null
    : [...boxes.filter((c) => c.checked).map((c) => c.dataset.tool), ...listOf(advanced)] };
}

// ---- Rules -------------------------------------------------------------------------

function drawRulesTab() {
  const d = sets.data.dvara;
  if (!d) return dvaraOff();
  const rows = (d.rules || []).map((r) => ({ ...r }));
  const list = h("div.rules");
  const redraw = () => list.replaceChildren(...rows.map((r, i) => ruleRow(r, i, rows, redraw)));
  redraw();
  return [warnBox(d.policy_problem),
    h("p.meta", {}, "A standing answer for a tool, so nobody is asked each time. The " +
      "strictest matching rule wins. An Allow takes exact values only: a * in it is refused."),
    list,
    row(button("Add a rule", () => { rows.push({ tool: "", args: {}, verdict: "ask" }); redraw(); },
                   "linkish"),
            button("Save the rules", () => save("/api/settings/rules", { rules: rows.map((r) => ({
              tool: r.tool, verdict: r.verdict, reason: r.reason || null,
              args: Object.keys(r.args || {}).length ? r.args : null })) }))),
    asText("policy", "", d.policy.text || "", d.policy.path)];
}

function ruleRow(r, i, rows, redraw) {
  const tool = text(r.tool, { placeholder: "bash" });
  tool.addEventListener("input", () => { r.tool = tool.value.trim(); });
  const args = text(Object.entries(r.args || {}).map(([k, v]) => `${k} = ${v}`).join("; "),
                    { placeholder: "command = git status" });
  args.addEventListener("input", () => {
    r.args = {};
    for (const part of args.value.split(";")) {
      const [k, ...v] = part.split("=");
      if (k.trim() && v.length) r.args[k.trim()] = v.join("=").trim();
    }
  });
  const verdict = pick([["allow", "Allow"], ["ask", "Ask"], ["deny", "Deny"]], r.verdict);
  verdict.addEventListener("change", () => { r.verdict = verdict.value; });
  const reason = text(r.reason || "", { placeholder: "why (shown when refused)" });
  reason.addEventListener("input", () => { r.reason = reason.value; });
  return h("div.rule", {}, field("Tool", tool), field("When", args), field("Answer", verdict),
           field("Why", reason),
           button("Remove", () => { rows.splice(i, 1); redraw(); }, "linkish"));
}

// ---- Accounts (Setu) ---------------------------------------------------------------

const SETU_WORDS = {
  "client-file": ["Google client file", "The Desktop-app client file you made once in " +
                  "Google Cloud (its path on this computer)."],
  "homeassistant-url": ["Home Assistant address", "e.g. http://homeassistant.local:8123"],
  browser: ["Browser for sites without an API", "Empty: Chrome on this computer."],
  "share-installs": ["Count my installs in the catalog", "on or off"],
  "people-page": ["People's own accounts pages", "on or off: the My accounts link for " +
                  "each person"],
};

function drawAccountsTab() {
  const s = sets.data.setu;
  if (!s.found) return [h("p.meta", {}, "Setu wasn't found on this computer.")];
  const out = [h("p.meta", {}, "Your accounts themselves are on Setu's own page (Your pages, " +
                 "above). These are Setu's settings.")];
  for (const [name, [label, hint]] of Object.entries(SETU_WORDS)) {
    const value = s.settings[name];
    const input = ["share-installs", "people-page"].includes(name)
      ? pick([["", "(not set)"], ["on", "on"], ["off", "off"]], value || "")
      : text(value || "");
    out.push(h("div.card", {}, field(label, input, hint),
      row(button("Save", () => save(`/api/settings/setu/${name}`, { value: input.value })))));
  }
  if (s.sites.length) {
    out.push(h("h3.sub", {}, "Sites you added"));
    for (const site of s.sites) {
      out.push(h("div.card", {}, h("div.card-head", {}, h("h3", {}, site.id)),
        h("div.meta", {}, "Its rules: which pages spend money, how fast to go, its guide."),
        asText("site", site.id, site.text, "")));
    }
  }
  return out;
}

// ---- Sarathi -----------------------------------------------------------------------

function drawSarathiTab() {
  const s = sets.data.sarathi;
  const agents = (sets.data.dvara?.agents || []).map((a) => [a.name, a.name]);
  const people = (sets.data.dvara?.people || []).map((p) => [p.id, p.id]);
  const provider = pick(s.providers.map((p) => [p, p]), s.model.provider);
  const model = text(s.model.model || "", { placeholder: "the provider's default" });
  const base = text(s.model.base_url || "", { placeholder: "the usual address" });
  const ctx = text(s.model.context_window || "", { inputmode: "numeric", placeholder: "8192" });
  const samayOn = check(s.samay.on);
  const prahariOn = check(s.prahari ? s.prahari.on : true);
  const road = pick([["process", "Plain programs"], ["podman", "Containers (Podman)"]], s.run.road);
  const pagesOn = check(s.pages.on);
  const dv = s.dvara || {};
  const dvaraOn = check(!!s.dvara);
  const bot = pick([["", "No Telegram bot"], ...agents], dv.telegram || "");
  const owner = pick(people.length ? people : [[dv.owner || "owner", dv.owner || "owner"]],
                     dv.owner || "owner");
  const house = text(dv.window_host || "", { placeholder: "192.168.1.44" });
  const ntfy = check(dv.ntfy);
  const lanName = text(s.house?.name || "", { placeholder: "beast.local" });
  const lanAt = text(s.house?.address || "", { placeholder: "what the name finds" });
  const phoneOn = check(!!s.phone);
  const phoneAt = text(s.phone?.address || "", { placeholder: "192.168.1.23:41234" });
  const wdaAt = text(s.phone?.wda || "", { placeholder: "http://127.0.0.1:8100" });
  const awake = pick([["", "Kept on while working"], ...s.awake.map((a) => [a, a])],
                     s.phone?.awake || "");
  const ports = {
    yantra: text(s.yantra.port), samay: text(s.samay.port),
    prahari: text(s.prahari ? s.prahari.port : 8782), home: text(s.pages.sarathi_port),
    setu: text(s.pages.setu_port), dvaraPage: text(s.pages.dvara_port),
    dvara: text(dv.port || 8770), ntfy: text(dv.ntfy_port || 8793),
  };
  const go = button("Save", () => save("/api/settings/sarathi", {
    model: { provider: provider.value, model: model.value.trim(), base_url: base.value.trim(),
             context_window: ctx.value.trim() || null },
    yantra: { port: ports.yantra.value },
    samay: { on: samayOn.checked, port: ports.samay.value },
    prahari: { on: prahariOn.checked, port: ports.prahari.value },
    run: { road: road.value },
    pages: { on: pagesOn.checked, sarathi_port: ports.home.value, setu_port: ports.setu.value,
             dvara_port: ports.dvaraPage.value },
    dvara: dvaraOn.checked ? { on: true, telegram: bot.value, owner: owner.value,
                               window_host: house.value.trim(), ntfy: ntfy.checked,
                               port: ports.dvara.value, ntfy_port: ports.ntfy.value }
                           : { on: false },
    phone: phoneOn.checked ? { on: true, address: phoneAt.value.trim(),
                               wda: wdaAt.value.trim(), awake: awake.value }
                           : { on: false },
    house: { name: lanName.value.trim(), address: lanAt.value.trim() },
  }));
  return [
    h("div.card.form", {}, h("h3", {}, "Which model answers"),
      field("Provider", provider, "ollama: a model on this computer. anthropic, openai: a cloud " +
            "key, under Keys."),
      field("Model", model), field("Address", base),
      field("Tokens your model holds", ctx, "A 64k Ollama model: 64000.")),
    h("div.card.form", {}, h("h3", {}, "Dvara: your agents for other people, and your phone"),
      h("label.inline", {}, dvaraOn, " On"),
      field("A Telegram bot answers as", bot, "The bot's token goes under Keys."),
      field("You, in the people list", owner),
      field("This computer's address at home", house, "Phones at home reach the home page, " +
            "Setu's page and ntfy here. Your home network's address, or Tailscale's."),
      h("label.inline", {}, ntfy, " Notices on phones, through ntfy in the house")),
    h("div.card.form", {}, h("h3", {}, "Every page on your home network"),
      field("This computer's name at home", lanName, "Every page opens from your other " +
            "devices too, and every link says this name: <hostname>.local, or your " +
            "router's name for this computer. Empty: this computer alone."),
      field("Its address", lanAt, "Where they are published. Empty: what the name finds."),
      h("p.meta", {}, "Yantra's page then wants its token; the Yantra card here carries it.")),
    h("div.card.form", {}, h("h3", {}, "The rest"),
      h("label.inline", {}, samayOn, " Samay: things done later, on a schedule"),
      h("label.inline", {}, prahariOn, " Prahari: tells you when something happens"),
      h("label.inline", {}, pagesOn, " The pages (Setu's, Dvara's, this one)"),
      field("How it runs", road)),
    phoneCard(phoneOn, phoneAt, wdaAt, awake, s.run.road, s.phone?.named || []),
    h("details.card", {}, h("summary", {}, "Ports"),
      field("Yantra", ports.yantra), field("Samay", ports.samay),
      field("Prahari (its page and its inlet)", ports.prahari),
      field("This home page", ports.home), field("Setu's page", ports.setu),
      field("Dvara's page", ports.dvaraPage), field("Dvara", ports.dvara),
      field("ntfy", ports.ntfy)),
    h("p.meta", {}, "Memory is switched on the Memory card above."),
    row(go),
    asText("sarathi", "", s.text, "~/.config/sarathi/sarathi.toml"),
  ];
}

// The phone: its settings (saved with the rest), and the steps that reach it
// from this computer, where its USB cable is. Each step is Sparsh's own,
// run here; the address that answered is saved (editing.py, phone_step).
function phoneCard(phoneOn, phoneAt, wdaAt, awake, road, named) {
  const step = (label, body) => button(label, () => save("/api/settings/phone", body()));
  if (named.length) return namedPhonesCard(phoneOn, named, step);
  const fromCable = step("Turn on Wi-Fi from the cable", () => ({ do: "tcpip" }));
  const connect = step("Connect", () => ({ do: "connect", address: phoneAt.value.trim() }));
  const pairAt = text("", { placeholder: "192.168.1.23:37000" });
  const code = text("", { inputmode: "numeric", placeholder: "123456" });
  const pair = step("Pair", () => ({ do: "pair", address: pairAt.value.trim(),
                                     code: code.value.trim() }));
  return h("div.card.form", {}, h("h3", {}, "Your phone"),
    h("label.inline", {}, phoneOn, " Your phone, through Sparsh"),
    field("The phone's Wi-Fi address", phoneAt,
          road === "podman" ? "The containers reach the phone only over Wi-Fi."
                            : "Empty: a phone on a USB cable."),
    field("Its screen while an agent works it", awake),
    h("p.meta", {}, "Plug the phone into this computer with USB debugging on, then turn on " +
      "Wi-Fi: it finds the phone's address and saves it. Do it again whenever the phone " +
      "restarts: a phone stops listening over Wi-Fi when it's switched off, and its " +
      "address can change. Any Android works this way."),
    row(fromCable, connect),
    h("details", {}, h("summary", {}, "No cable? Android 11 and newer: pair once"),
      h("p.meta", {}, "On the phone: Developer options → Wireless debugging → Pair device " +
        "with pairing code. Type the address and six digits it shows, then Pair. Then put " +
        "the address on the Wireless debugging page itself above, and Connect."),
      field("Pairing address", pairAt), field("Pairing code", code), row(pair)),
    iphoneSteps(wdaAt, step), addPhone(step, true));
}

// Several phones, each by a name ([phone.NAME]): the list, each one's Remove,
// and Add -- the same steps as one phone, with a name. Whose each is, People
// says (editing.py, _named_step).
function namedPhonesCard(phoneOn, named, step) {
  const rows = named.map((n) => h("div.row", { style: "gap: .75rem; align-items: center" },
    h("span", {}, h("b", {}, n.name), ` — ${n.kind} at `, h("code", {}, n.where),
      n.awake ? ` · awake ${n.awake}` : ""),
    step("Remove", () => ({ do: "remove", name: n.name }))));
  return h("div.card.form", {}, h("h3", {}, "Your phones"),
    h("label.inline", {}, phoneOn, " Your phones, through Sparsh"),
    ...rows, addPhone(step, false));
}

function addPhone(step, first) {
  const name = text("", { autocapitalize: "none", placeholder: "nexus" });
  const at = text("", { placeholder: "192.168.1.23:5555" });
  const wda = text("", { placeholder: "http://127.0.0.1:8100" });
  const named = (body) => () => ({ ...body(), name: name.value.trim() });
  return h("details", first ? {} : { open: true },
    h("summary", {}, first ? "Several phones? Name each" : "Add a phone"),
    h("p.meta", {}, "A name is your word for it: lower case, digits and dashes. Then, in " +
      "People, tick whose it is: each phone is one person's, and their agents reach their " +
      "phones only."),
    field("Its name", name),
    row(step("The phone on the cable", named(() => ({ do: "cable" }))),
        step("Wi-Fi, from the cable", named(() => ({ do: "tcpip" })))),
    field("Or its Wi-Fi address", at), row(step("Connect", named(() => ({
      do: "connect", address: at.value.trim() })))),
    field("Or an iPhone's WebDriverAgent", wda), row(step("Use the iPhone", named(() => ({
      do: "iphone", wda: wda.value.trim() })))));
}

// An iPhone too: WebDriverAgent's address, checked by Sparsh before it's
// saved, beside any Android. The one plugged in is the one used.
function iphoneSteps(wdaAt, step) {
  const useIt = step("Use the iPhone", () => ({ do: "iphone", wda: wdaAt.value.trim() }));
  return h("details", {}, h("summary", {}, "An iPhone"),
    h("p.meta", {}, "Plug the iPhone into this computer and unlock it, then Use the " +
      "iPhone: Sparsh starts WebDriverAgent on it (a minute; longer the first time after " +
      "an iOS update), checks it answers, and it's saved beside any Android: whichever " +
      "phone is plugged in is the one used, so swapping them needs nothing here. Apply " +
      "hands it to Yantra and Dvara. Unplugged, restarted or updated, press it again: it " +
      "comes back by itself when plugged in while it runs. WebDriverAgent is built on a " +
      "Mac once a week (Sparsh's SETUP.md, Part C). Keep the iPhone unlocked while an " +
      "agent works it."),
    field("WebDriverAgent's address", wdaAt, "Empty: http://127.0.0.1:8100."),
    row(useIt));
}

// ---- Keys --------------------------------------------------------------------------

const KEY_WORDS = {
  ANTHROPIC_API_KEY: "Anthropic (Claude) key", OPENAI_API_KEY: "OpenAI key",
  TELEGRAM_TOKEN: "Telegram bot's token (from @BotFather)",
};

function drawKeysTab() {
  const keys = sets.data.sarathi.keys;
  return [h("p.meta", {}, "Typed in once and kept in secrets.env, readable only by you. " +
                          "This page never shows a key back."),
    ...Object.entries(keys).map(([name, isSet]) => {
      const input = h("input", { type: "password", autocomplete: "off",
                                 placeholder: isSet ? "set: type a new one to replace it"
                                                    : "not set" });
      return h("div.card", {}, field(KEY_WORDS[name] || name, input),
        row(button("Save", () => save(`/api/settings/key/${name}`, { value: input.value }))));
    })];
}
