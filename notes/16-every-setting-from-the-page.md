# 16 — every setting, from the page

*Sarathi is the one you install, and it asked an owner to edit TOML for
nearly everything after `sarathi init`: add a person to Dvara's actors
file, give an agent an account in its `agent.toml`, change a port in
`sarathi.toml`, paste a key into `secrets.env`. This note puts every one
of those on the home page.*

## The problem, as you would meet it

You want to try **My accounts** as someone else. The answer was: open
`~/dvara/actors.toml`, add `[actor.priya]` with `setu = true`, then
invite her. Adding Home Assistant to the Telegram agent meant finding
`[connections]` in `~/dvara/agents/minder/agent.toml`. A port clash
meant `sarathi.toml`. Each is a file you have to know exists, in a
syntax you have to get right.

## Settings, on your own page

Under the cards, **Settings** has six tabs:

| Tab | What | Whose file | Written by |
|---|---|---|---|
| People | add, change, remove; agents, accounts, allowance, rung, Telegram ids, the phone; strangers who messaged the bot, to add | `actors.toml` | `dvara settings person` |
| Agents | model, memory, tools, accounts it needs, budget, rung, instructions; add from an example; remove (moved aside) | `agent.toml`, `prompt.md` | `dvara settings agent` |
| Rules | standing allow / ask / deny per tool and argument | `policy.toml` | `dvara settings rules` |
| Accounts | Setu's settings; each added site's rules | Setu's `config.json`, `sites/*.toml` | `setu config`, `setu site file` |
| Sarathi | model, Dvara and its bot, the house address, ntfy, Samay, pages, phone, road, ports | `sarathi.toml` | Sarathi |
| Keys | cloud keys, the bot's token: in, never out | `secrets.env` | Sarathi |

Every tab ends in **Edit as text**: the whole file, for whatever a form
doesn't cover.

* **EACH PROGRAM WRITES ITS OWN FILE, AND CHECKS IT FIRST.** The page
  sends a change; the program whose file it is applies it, reads it back
  the way it will at its next start, and writes it only if it loads
  (Dvara's note 41, Setu's `site file`, `config.parse` for
  `sarathi.toml`). A refusal comes back in that program's own words, and
  nothing is written. The file before is kept as `.bak`.
* **THE OWNER'S COMMENTS STAY.** Dvara and Setu change only the table you
  changed. `sarathi.toml` is written whole, as `init` writes it: its
  comments are Sarathi's own.
* **WHEN IT TAKES EFFECT.** People, agents and rules: from the next
  message, since Dvara rereads them. Setu's settings: at once. Sarathi's
  settings and keys: on the next start, so the page shows **Apply**,
  which runs `sarathi up` behind the answer.
* **KEYS IN, NEVER OUT.** The Keys tab says only whether each is set.
* **THE OWNER'S ALONE.** A person signed in gets 403 on all of it: these
  files decide what everyone else may do. You can't remove yourself.

## You have accounts too

You're in the People list like everyone else, marked *(you)*, with the
same form: *This computer's accounts (yours)* with *may connect and
disconnect from the chat* is the usual choice. **My accounts**, at the
top of your page, opens Setu's page for your own folder, already signed
in. A person's **My accounts** opens theirs by a one-time link (note 15).

## Receipt

A scratch home page on copies of this machine's `sarathi.toml`, actors
file and agents, driven in Chrome through Yantra's Playwright: Priya
added (greeter, her own accounts, $0.50 a day, Telegram 1234567) and
written as one new table under the owner's untouched lines; `@ravi` as a
Telegram id refused in Dvara's words; a second person with Priya's id
refused (*"telegram id '1234567' is claimed by both [actor.priya] and
[actor.priya2]…"*); greeter given memory; a rule saved; Ollama's address
set under Sarathi, kept with `sarathi.toml.bak`, **Apply** offered. Every
tab drawn at 1100 and 390 pixels with no script errors. The run found
two things: a stray "null" drawn for an empty warning (fixed), and
Dvara's rules going to its default `~/dvara/policy.toml` rather than
beside the scratch actors file. Dvara's default is now beside the
actors file (its note 41). The file that run had written to
`~/dvara/policy.toml` was removed.

## What the tests hold

`tests/test_settings_page.py`: the owner sees every file and Dvara is
asked with its folders; a person goes to Dvara with what the form said;
Dvara's refusal is the page's answer; you can't remove yourself;
`sarathi.toml` is checked and the old one kept, a bad port and an
unknown table refused with the file unchanged; a key goes in and never
comes back out; a person signed in gets none of it.

## What is not here yet

* **Smritikosh's own settings.** Memory is switched on the Memory card;
  its server's `.env` stays `sarathi smritikosh`'s.
* **Samay's schedules** are on Samay's page, and Yantra's own page keeps
  its own settings panel.
* ~~**The phone's address is only typed.**~~ A typed address didn't turn
  a restarted phone's Wi-Fi back on. **Your phone** on the Sarathi tab
  now does that from the USB cable, and connects or pairs, each step
  Sparsh's own ([note 17](17-the-phone-from-the-page.md)).
* ~~**An agent's tools are a text box.**~~ They're checkboxes now, from
  Dvara's list of every tool an agent could have, each in plain words and
  marked *asks you first* or *runs unasked*; names no box stands for wait
  under **Advanced**, and no box ticked is refused before it's sent
  (Dvara, its notes/43).
* ~~**A learned skill made a tool only at Yantra's page.**~~ Under each
  agent, the skills its people kept, and **Make it a tool** for one with
  a script; the press is the yes for its one test run, and **Stop using
  as a tool** takes it back (Dvara, its notes/46).
* A long list of tool boxes (28 on a real setup) or kept skills has a
  box above it: only the rows holding every typed word stay, a group
  with none left goes too, and `1 of 28` says rows are hidden. Rows are
  only hidden, never redrawn, so a ticked box that's filtered out stays
  ticked and is saved. The same box as on Yantra's page.
