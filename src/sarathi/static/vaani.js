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
  const quiet = text(p.fresh_after ?? 30, { inputmode: "numeric", size: "5" });
  // the puck's own wake words, as it told Vaani; none known while it's away
  const offers = p.wake_words?.offers || [];
  const on = (p.wake_words?.on || [])[0] || "";
  const wake = offers.length ? pick(offers.map((w) => [w, w]),
    offers.find((w) => [w.toLowerCase(), w.toLowerCase().replace(/ /g, "_")]
      .includes((p.wake_word || "").toLowerCase())) || on) : null;
  const boxes = people.map((x) => {
    const c = check((p.people || []).includes(x));
    c.value = x;
    const no = (p.people || []).includes(x) && !voiced.has(x);
    return h("label.inline", {}, c, ` ${x}`, no ? h("span.meta", {}, " (voice not learned yet)") : null);
  });
  const go = button("Save", () => vaaniSave({
    do: "puck", puck: p.name, person: unsure.value, agent: agent.value,
    fresh_after: quiet.value.trim(),
    ...(wake ? { wake_word: wake.value } : {}),
    people: boxes.map((b) => b.querySelector("input")).filter((c) => c.checked).map((c) => c.value),
  }));
  return h("div.card.form", {}, h("h3", {}, `The ${p.name} puck`),
    field("It may tell apart (by voice, or “this is NAME, …”)", h("div.boxes", {}, ...boxes),
          "Nobody ticked: it always answers as the person below. Each person ticked needs " +
          "their voice learned (on Vaani's page) and must be allowed the agent."),
    field("When it isn't sure who's asking", unsure,
          "Best: a person with only the house's accounts, so one person's mail is never " +
          "read to another. The puck says it wasn't sure."),
    field("Agent", agent),
    wake ? field("Wake word", wake, `What you say to wake it. Now: ${on || "not known"}. ` +
                 "A change reaches the puck within a minute.")
         : h("p.meta", {}, "Wake word: the puck hasn't told Vaani its wake words yet " +
                           "(is it listening? See Vaani's page)."),
    field("Start a new conversation after this many minutes quiet", quiet,
          "Until then, everything someone asks at this puck is one conversation, so " +
          "“and the one before?” works. After it, the next question starts afresh (the " +
          "old one is kept: /chats). 0: never by itself, only when someone says " +
          "“new conversation”."),
    row(go));
}

async function vaaniSave(body) {
  said("Asking Vaani…");
  try {
    const got = await api("/api/vaani", body);
    said(got.said || "Saved.");
  } catch (err) { said(err.message, true); return; }
  if (sets.tab === "vaani") drawTabs();
}
