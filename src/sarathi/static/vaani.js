"use strict";
// Settings → Vaani: the pucks, what they were last asked, and whose voices
// they know. Uses page.js's h(), api() and settings.js's small pieces.
// Everything is Vaani's (GET/POST /api/vaani, which asks `vaani`): each
// question's steps as it recorded them, and the changes made by Vaani
// itself. Looked at again every few seconds while the tab is open, so a
// question asked at the puck shows up here as it happens.

const voice = { data: null, timer: null };
const VAANI_EVERY = 5000;

function drawVaaniTab() {
  const live = h("div.vaani", { "aria-live": "polite" }, h("p.meta", {}, "Asking Vaani…"));
  const forms = h("div.vaani");
  const intro = h("p.meta", {}, "Each question at a puck, step by step: what woke it, " +
    "what Whisper heard, whose question it was taken to be, how long your agent took, " +
    "and whether the puck came for the answer. A silent puck shows here where it went " +
    "silent.");
  lookVaani(live, forms, true);
  clearInterval(voice.timer);
  voice.timer = setInterval(() => {
    if (sets.tab !== "vaani" || !document.body.contains(live)) {
      clearInterval(voice.timer);
      return;
    }
    if (!document.hidden) lookVaani(live, forms, false);
  }, VAANI_EVERY);
  return [intro, live, forms];
}

async function lookVaani(live, forms, first) {
  let got;
  try { got = await api("/api/vaani"); }
  catch (err) { live.replaceChildren(h("p.warn", {}, `Vaani didn't answer: ${err.message}`)); return; }
  voice.data = got;
  if (!got.on) {
    live.replaceChildren(h("p.meta", {}, "Vaani is off. Turn it on under Sarathi, above."));
    forms.replaceChildren();
    return;
  }
  live.replaceChildren(...pucksNow(got), enrollingNow(got), questions(got.runs || []));
  // the forms are drawn once, so a half-made change isn't drawn over
  if (first) forms.replaceChildren(...(got.pucks || []).map(puckForm), voicesCard(got));
}

function pucksNow(got) {
  const st = got.status || {};
  if (!st.serving) {
    return [h("div.doctor-line.red", {}, h("span.doctor-mark", {}, "Not running"),
              h("span", {}, "Vaani isn't running: the pucks light up and nobody answers. ",
                "Settings → Check says what to do."))];
  }
  return (st.pucks || []).map((p) => {
    const ok = p.listening !== false;
    return h(`div.doctor-line.${ok ? "green" : "red"}`, {},
      h("span.doctor-mark", {}, p.name),
      h("span", {}, ok ? `Listening at ${p.host}, answering as ${p.person}` +
                         (p.agent ? ` with ${p.agent}` : "")
                       : `Not listening: ${p.problem || "not reached yet"}`));
  });
}

function enrollingNow(got) {
  const e = got.enrolling;
  if (!e) return null;
  return h("div.doctor-line.amber", {}, h("span.doctor-mark", {}, "Learning"),
    h("span", {}, `${e.person}'s voice at the ${e.puck} puck: ${e.left} more. They say ` +
      "the wake word, then any sentence, and the puck counts down. ",
      button("Stop", () => vaaniDo({ do: "stop" }), "quiet")));
}

const ago = (at) => {
  const s = Math.max(0, Math.round(Date.now() / 1000 - at));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  return new Date(at * 1000).toLocaleString([], { weekday: "short", hour: "2-digit",
                                                  minute: "2-digit" });
};

function questions(runs) {
  const head = h("h3", {}, "Last questions");
  if (!runs.length) {
    return h("div.card.form", {}, head, h("p.meta", {}, "None yet. Say the wake word " +
      "at a puck and ask something; it shows here as it happens."));
  }
  return h("div.card.form", {}, head, ...runs.map(question));
}

function question(r) {
  const took = r.took || {};
  const steps = [];
  const step = (label, okay, detail) => steps.push(
    h(`span.vstep${okay ? "" : ".bad"}`, {}, label, detail ? h("span.meta", {}, ` ${detail}`) : null));
  step("woken", true, r.woke_by ? `by ${r.woke_by}` : "");
  if (r.ended === "silence" || r.ended === "stopped") step("nothing said", false);
  if (r.heard || took.hear != null) step("heard", !!r.heard, took.hear != null ? `${took.hear}s` : "");
  if (r.person) step(`as ${r.person}`, true, r.how ? `(${r.how})` : "");
  if (took.agent != null) step("agent", !!r.answer && !r.error, `${took.agent}s`);
  if (took.speak != null) step("spoken", true, `${took.speak}s`);
  if (r.url) step(r.fetched ? "played" : "never fetched", !!r.fetched,
                  r.fetched ? "" : "(the puck didn't come for it)");
  const said = r.error && !r.answer ? r.error : r.answer;
  return h("div.vrun", {},
    h("div.vrun-head", {}, h("strong", {}, r.puck), h("span.meta", {}, ago(r.at))),
    r.heard ? h("div", {}, "“", r.heard, "”") : null,
    said ? h(`div.${r.error ? "warn" : "meta"}`, {}, "→ ", said) : null,
    h("div.vsteps", {}, ...steps.flatMap((s, i) => (i ? [h("span.meta", {}, " → "), s] : [s]))));
}

function puckForm(p) {
  const people = (sets.data.dvara?.people || []).map((x) => x.id);
  const agents = (sets.data.dvara?.agents || []).map((a) => [a.name, a.name]);
  const unsure = pick(people.map((x) => [x, x]), p.person);
  const agent = pick([["", "Vaani's default"], ...agents], p.agent || "");
  const boxes = people.map((x) => {
    const c = check((p.people || []).includes(x));
    c.value = x;
    return h("label.inline", {}, c, ` ${x}`);
  });
  const go = button("Save", () => vaaniDo({
    do: "puck", puck: p.name, person: unsure.value, agent: agent.value,
    people: boxes.map((b) => b.querySelector("input")).filter((c) => c.checked).map((c) => c.value),
  }));
  return h("div.card.form", {}, h("h3", {}, `The ${p.name} puck`),
    field("It may tell apart (by voice, or “this is NAME, …”)", h("div.boxes", {}, ...boxes),
          "Nobody ticked: it always answers as the person below. Each person ticked needs " +
          "their voice learned, below, and must be allowed the agent."),
    field("When it isn't sure who's asking", unsure,
          "Best: a person with only the house's accounts, so one person's mail is never " +
          "read to another. The puck says it wasn't sure."),
    field("Agent", agent), row(go));
}

function voicesCard(got) {
  const known = got.voices || [];
  const people = (sets.data.dvara?.people || []).map((x) => [x.id, x.id]);
  const pucks = (got.pucks || []).map((p) => [p.name, p.name]);
  const who = pick(people, "");
  const at = pick(pucks, pucks[0] ? pucks[0][0] : "");
  const learn = button("Learn their voice", () => vaaniDo({ do: "enroll", person: who.value,
                                                            puck: at.value }));
  const list = known.length
    ? known.map((v) => h("div.buttons", {}, h("span", {}, `${v.person}`),
        h("span.meta", {}, `from ${v.samples} sample${v.samples === 1 ? "" : "s"}`),
        button("Forget", () => {
          if (confirm(`Forget ${v.person}'s voice? They can be learned again.`)) {
            vaaniDo({ do: "forget", person: v.person });
          }
        }, "quiet")))
    : [h("p.meta", {}, "No voices learned yet.")];
  return h("div.card.form", {}, h("h3", {}, "Voices"),
    h("p.meta", {}, "A voice is learned at the puck itself: press the button, then that " +
      "person says the wake word and any sentence there, three times. Only a few numbers " +
      "about the voice are kept, never the sound."),
    ...list, row(field("Whose", who), field("At", at), learn));
}

async function vaaniDo(body) {
  said("Asking Vaani…");
  try {
    const got = await api("/api/vaani", body);
    said(got.said || "Done.");
  } catch (err) { said(err.message, true); return; }
  // draw it all again: a saved puck, a voice forgotten, a learning started
  if (sets.tab === "vaani") drawTabs();
}
