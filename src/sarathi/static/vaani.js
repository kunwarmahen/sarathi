"use strict";
// Settings → Vaani: who each puck answers, and which people it tells
// apart -- vaani.toml, changed by Vaani itself (POST /api/vaani, which
// runs `vaani puck`). What the pucks did, and learning voices, are on
// Vaani's own page (its card under Your pages). Uses page.js's h(), api()
// and settings.js's small pieces.

function drawVaaniTab() {
  const out = h("div.vaani", {}, h("p.meta", {}, "Asking Vaani…"));
  const intro = h("p.meta", {}, "Who each puck answers, and which people it tells apart. " +
    "What a puck was asked, step by step, and learning someone's voice are on Vaani's " +
    "own page: its card is under Your pages.");
  fillVaani(out);
  return [intro, out];
}

async function fillVaani(out) {
  let got;
  try { got = await api("/api/vaani"); }
  catch (err) { out.replaceChildren(h("p.warn", {}, `Vaani didn't answer: ${err.message}`)); return; }
  if (!got.on) {
    out.replaceChildren(h("p.meta", {}, "Vaani is off. Turn it on under Sarathi, above."));
    return;
  }
  const voiced = new Set((got.voices || []).map((v) => v.person));
  out.replaceChildren(...(got.pucks || []).map((p) => puckForm(p, voiced)));
}

function puckForm(p, voiced) {
  const people = (sets.data.dvara?.people || []).map((x) => x.id);
  const agents = (sets.data.dvara?.agents || []).map((a) => [a.name, a.name]);
  const unsure = pick(people.map((x) => [x, x]), p.person);
  const agent = pick([["", "Vaani's default"], ...agents], p.agent || "");
  const boxes = people.map((x) => {
    const c = check((p.people || []).includes(x));
    c.value = x;
    const no = (p.people || []).includes(x) && !voiced.has(x);
    return h("label.inline", {}, c, ` ${x}`, no ? h("span.meta", {}, " (voice not learned yet)") : null);
  });
  const go = button("Save", () => vaaniSave({
    do: "puck", puck: p.name, person: unsure.value, agent: agent.value,
    people: boxes.map((b) => b.querySelector("input")).filter((c) => c.checked).map((c) => c.value),
  }));
  return h("div.card.form", {}, h("h3", {}, `The ${p.name} puck`),
    field("It may tell apart (by voice, or “this is NAME, …”)", h("div.boxes", {}, ...boxes),
          "Nobody ticked: it always answers as the person below. Each person ticked needs " +
          "their voice learned (on Vaani's page) and must be allowed the agent."),
    field("When it isn't sure who's asking", unsure,
          "Best: a person with only the house's accounts, so one person's mail is never " +
          "read to another. The puck says it wasn't sure."),
    field("Agent", agent), row(go));
}

async function vaaniSave(body) {
  said("Asking Vaani…");
  try {
    const got = await api("/api/vaani", body);
    said(got.said || "Saved.");
  } catch (err) { said(err.message, true); return; }
  if (sets.tab === "vaani") drawTabs();
}
