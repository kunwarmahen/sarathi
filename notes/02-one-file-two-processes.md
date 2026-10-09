# 02 — One file, two processes

[Note 01](01-five-names-one-answer.md) found the pieces. This one starts
them. Of the five, two need to keep running: **Samay's clock**, so that
work happens on time, and **Yantra's page**, so that someone can talk to
the agent. Setu runs only when the agent uses an account. Dvara is the
household road and comes later. Smritikosh is optional.

Starting two programs is easy. The hard part is everything that has to
be true for them to work together, which until now lived in whoever set
up the machine: the page has to know where Setu and Samay are; the clock
has to know which Yantra to run; both have to use the same model; and
the clock has to exist before the page asks about it.

## Asked once

The first thing Sarathi needs is the answer to the question that splits
its readers in two: **which model answers?** About half of them run a
model on their own machine with Ollama, and the rest use a cloud key.
`sarathi init` asks it as a plain question, with the local road first:

```
Which model should answer?
  1) one on this machine, through Ollama -- free, private, needs a GPU or patience
  2) Anthropic's, with an API key
  3) OpenAI's, with an API key
```

**THE LOCAL ROAD LOOKS BEFORE IT SUGGESTS.** Ollama is asked which
models are already pulled, so the suggestion is one that will answer
today, not a name copied from a README. On the machine this was written
on, Ollama listed eight models. Two were not offered: `nomic-embed-text`
turns text into numbers and cannot hold a conversation, and offering it
would cost someone an evening. Yantra's own default came first because
it was pulled:

```
$ sarathi init --provider ollama --web-port 8410 --clock-port 8790
wrote .../config/sarathi.toml
  answering: ollama, qwen3.8:latest
next: `sarathi up`
```

Ollama not running is not an error here. Setup and start are different
moments, so the file is written and the line says `ollama serve`.

**A KEY NEVER GOES ON THE COMMAND LINE OR INTO THE SETTINGS FILE.** On a
cloud road, the key is typed at a hidden prompt and written to
`secrets.env`, created readable by its owner only (not tightened after
the fact). That keeps `sarathi.toml` safe to paste into a question. A
key already in the environment is used where it is and never copied, so
someone who manages keys their own way doesn't end up with a second copy
they didn't ask for.

## A file that refuses what it doesn't know

```toml
[model]
provider = "ollama"
model = "qwen3.8:latest"

[web]
port = 8321

[clock]
on = true
port = 8780
```

**UNKNOWN KEYS ARE ERRORS.** A misspelt `[clok]` with `on = false`
under it would otherwise be skipped, and the clock would run every
schedule while its owner believed it was off. Every table and key is
listed, and anything else stops `up` with its name.

**THE SIBLINGS NEVER READ IT.** Sarathi turns it into what each one
already understands. Nothing new is invented for them:

| sarathi.toml | becomes |
|---|---|
| `model.provider` | `YANTRA_PROVIDER`, which Yantra reads before guessing from keys. It's the only way to choose a local model, since "no key" can't be seen by a ladder of keys |
| `model.model` | `OLLAMA_MODEL` / `ANTHROPIC_MODEL` / `OPENAI_MODEL` |
| `model.context_window` | `OLLAMA_CONTEXT_WINDOW` (and so on): when Yantra shortens a long chat. On the Podman road it is the only way in, since Yantra's `.env` is never in the image |
| `yantra.port` | `yantra --web --port` |
| `samay.port` | `samay serve --port` |
| the yantra Sarathi found | `SAMAY_YANTRA`, so the clock runs the same Yantra as the page |
| the setu and samay it found | `yantra --setu PATH --samay PATH`, so the page talks to the same ones `status` showed |

Both processes get the same model settings, and Samay passes its
environment on to every run it starts. So **a scheduled run is answered
by the same model as the page**, which was a promise nobody could make
when the two were configured in two places.

A real environment variable outranks `secrets.env`, the same rule
Yantra applies to its own `.env`: whatever someone typed in this shell
is what they meant this time.

## Starting, without doubling anything

**ONE OF EACH, AND NEVER SOMEONE ELSE'S.** Before starting anything,
`up` checks whether it is already there:

* a piece Sarathi started that is still alive is left alone:

  ```
  $ sarathi up
  clock  already running at http://127.0.0.1:8790/#token=…  (pid 3324159)
  page   already running at http://127.0.0.1:8410/  (pid 3324163)
  ```

* a clock started some other way (`samay unit`, a terminal) is found
  through `samay status` and also left alone. Its schedules live in the
  same file, so a second clock would run every job twice;
* a port something else already listens on is reported with the
  setting that moves it, and nothing is fought over.

**WHAT WAS STARTED IS WRITTEN DOWN.** `run/<name>.json` holds the pid,
the command and the address. `down` stops only what is written there,
and the whole process group, so a page's browser goes with it. `status`
reads the same records, so nothing is inferred from a list of processes.
A record whose process has died is shown, not quietly removed:

```
started by `sarathi up`:
  clock  STOPPED -- it exited; the end of ~/.local/share/sarathi/logs/clock.log:
         | ...
```

**A START IS NOT A SUCCESS UNTIL THE PORT ANSWERS.** A page that dies on
a missing web extra would otherwise read as "started". `up` waits for
the address to accept a connection, and if the process exits first, it
says so with the process's own last words.

## What the first live run found

Two things, both invisible in a test that only checks the processes ran.

**THE ORDER MATTERED.** The first version started the page, then the
clock. Both came up. The page's log said:

```
samay: 7 tool(s), 0 active schedule(s); its clock is NOT running -- nothing runs
on time until `samay serve` is
```

Yantra asks Samay about its clock once, at start-up, and tells the model
what it heard for the whole session. The page started first, so for
that session the agent would have warned on every schedule it offered
that nothing would run, while the clock four seconds behind it was
running fine. The clock now starts first, and a test checks the order:

```
samay: 7 tool(s), 0 active schedule(s); its clock is running
```

**THE CLOCK'S ADDRESS WAS UNUSABLE.** Samay's page only opens with its
token after `#`, and `samay status` deliberately leaves the token out.
So `clock up at http://127.0.0.1:8790/` pointed to a page that refused
to open. Samay does print the full address in its own first lines, so
Sarathi now reads that line from this start's log and shows it. The log
holds a token, so the folders for logs and records are created readable
by their owner only. Before this fix, every user on the machine could
read them.

## Live receipt

`qwen3.8:latest` through Ollama, the real Yantra, Setu (nine accounts)
and Samay, with scratch settings and ports because 8321 was already in
use on this machine:

```
$ sarathi up
clock  up at http://127.0.0.1:8790/#token=…  (pid 3324159)
page   up at http://127.0.0.1:8410/  (pid 3324163)
```

The page's own account of itself:

```
setu: gmail-mine (7 tool(s)), gmail-personal (7 tool(s)), homeassistant-home (6
tool(s)), amazon (7 tool(s)), linkedin (5 tool(s)), slack (5 tool(s)), whatsapp
(7 tool(s)), x (7 tool(s)), yahoo (5 tool(s)) -- via /home/mahen/.local/bin/setu
samay: 7 tool(s), 0 active schedule(s); its clock is running -- via
/home/mahen/Documents/ai/agent/samay/.venv/bin/samay
```

One turn through the page's HTTP endpoint, answered by the model
`sarathi.toml` named:

```
$ curl -s http://127.0.0.1:8410/api/state      → provider "ollama", model "qwen3.8:latest"
user:      In one short sentence: what is 17 times 3?
assistant: 17 times 3 is 51.
```

And back down, with both ports free afterwards:

```
$ sarathi down
clock  stopped  (pid 3324159)
page   stopped  (pid 3324163)
$ sarathi down
nothing started by `sarathi up` is running
```

## What is not here yet

* ~~The same two processes as Podman containers with Quadlet units.~~
  Built: [notes/03](03-two-containers-one-clock.md).
* ~~Keeping them running after a reboot or a crash.~~ The Podman road
  does: [notes/03](03-two-containers-one-clock.md). On the process road
  it's still `samay unit` for the clock.
* Each sibling's data in one place. Sarathi deliberately leaves Samay's
  schedules in `~/.samay` and Setu's sign-ins where Setu put them, so
  installing Sarathi on a machine that already uses them changes
  nothing. The containers mount those same folders at the same paths
  ([notes/03](03-two-containers-one-clock.md)).

*The tables were `[web]` and `[clock]` when this note was written; they are `[yantra]` and `[samay]` now, and the old names still read ([note 09](09-each-by-its-own-name.md)).*
