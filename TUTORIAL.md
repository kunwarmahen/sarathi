# Tutorial — your own helper, set up in an afternoon

This is for someone who wants a helper on their own computer: one that
can read their email, look at their home, do things later on a schedule,
and remember what they told it. You don't need to know how any of it
works inside. You need a terminal, and about an hour.

If you'd rather understand the parts and wire them yourself, Yantra's
tutorial does that by hand (its §24). This one uses Sarathi to do it for
you.

---

## What you're setting up

Five small programs, each with one job. You'll use three of them today:

```
   you, in a browser
          │
          ▼
   ┌──────────────┐   reads your mail,     ┌──────────────┐
   │  Yantra's    │   your home ────────▶  │    Setu      │──▶ Gmail,
   │  page        │                        │ (your keys)  │    Home Assistant
   │ (the helper) │                        └──────────────┘
   └──────┬───────┘
          │ "do this every morning"
          ▼
   ┌──────────────┐   at 8:00, asks Yantra to do it,
   │ Samay's      │   and writes down what came back
   │ clock        │
   └──────────────┘

   Sarathi: finds all of these, starts them in the right order,
            and stops them again.
```

| Name | What it is |
|---|---|
| **Yantra** | the helper itself, and the page you talk to it on |
| **Setu** | keeps your sign-ins (Gmail, Home Assistant, …). The helper can *use* an account, but never *sees* its key |
| **Samay** | a clock: "every morning at 8, check my mail" keeps happening while you're away |
| **Sarathi** | the one you install and run: it starts the others for you |

(Dvara, for sharing your helper with family over Telegram, and
Smritikosh, a bigger memory store, are optional. Sarathi will mention
them; you can ignore both today.)

---

## Step 0 · The first choice: whose model answers?

Everything the helper says comes from a **language model**. You have
two choices, and both are fine:

| | **A model on your own computer** | **A model in the cloud** |
|---|---|---|
| Through | Ollama, a free program | Anthropic or OpenAI, with an account |
| Costs | nothing per question | a little per question |
| Your words go | nowhere: they stay on your machine | to the company running the model |
| Needs | a decent graphics card, or patience | an API key (a long password from their website) |
| Quality | good for everyday tasks | the best available |

**If you choose your own computer**, install Ollama
([ollama.com](https://ollama.com)) and pull a model before going on:

```bash
ollama pull qwen3.8:latest
```

**If you choose the cloud**, make an API key on the company's website
and keep it to hand. You'll paste it once, into a hidden prompt.

---

## Step 1 · Get the programs

Sarathi expects the projects to sit side by side in one folder:

```bash
mkdir -p ~/agent && cd ~/agent
for p in yantra setu samay sarathi; do
    git clone https://github.com/kunwarmahen/$p
done

(cd yantra  && uv sync --extra web)     # the page needs its web extra
(cd setu    && uv sync --all-packages)
(cd samay   && uv sync)
(cd sarathi && uv sync)
```

(`uv` is a tool that installs Python programs; if you don't have it:
`curl -LsSf https://astral.sh/uv/install.sh | sh`.)

From here on, `sarathi` means `~/agent/sarathi/.venv/bin/sarathi`. Add an
alias so you can type it short:

```bash
alias sarathi=~/agent/sarathi/.venv/bin/sarathi
```

Check what it can see:

```bash
sarathi status
```

```
yantra      ~/agent/yantra/.venv/bin/yantra  (beside)
            the machine: the agent itself
setu        ~/agent/setu/.venv/bin/setu  (beside)
            the bridge: your accounts, signed in once
            no accounts connected (connect one: setu connect gmail)
samay       ~/agent/samay/.venv/bin/samay  (beside)
            the clock: work done later, with receipts
            clock not running (start it: samay serve); schedules: 0 active, 0 paused
dvara       not found (optional) -- install it, or set SARATHI_DVARA=/path/to/dvara
            the door: many people and agents behind one service
smritikosh  not found (optional) -- install it, or set SARATHI_SMRITIKOSH=/path/to/smritikosh-mcp
            a memory store (Yantra keeps its own without it)
```

Each line says **where** it found a program and **how** (`beside` means
"in the folder next to Sarathi"). The line under it is that program
describing itself. "not found (optional)" is fine.

> **Something says "not found" that isn't optional?** The line tells you
> the fix: install it beside the others, or point Sarathi at it with the
> variable it names.

---

## Step 2 · Connect an account

The helper is more useful when it can see something of yours. Gmail is
the usual first one.

Google asks every program that reads Gmail to have its own "sign-in
client", so the first time there's a one-off step of about ten minutes:
making yours in Google's console. Setu's README walks through it
([*Make your own Google sign-in client*](https://github.com/kunwarmahen/setu#2-make-your-own-google-sign-in-client)).
It ends with a file, `client_secret.json`. Tell Setu where it is, once,
then connect:

```bash
setu=~/agent/setu/.venv/bin/setu
$setu config client-file ~/.config/setu/client_secret.json
$setu connect gmail
```

A browser opens on Google's sign-in page. Sign in and allow it. Setu
asks for **Read only** unless you say otherwise, so the helper can search
and read your mail but not send or delete anything, and Google itself
enforces that. Setu keeps the sign-in in a file only you can read. The
helper only ever sees the email text, never the key.

Setu's README lists the other accounts (Home Assistant, and sites like
Amazon through a browser) and what each level allows.

`sarathi status` now says `1 account connected: gmail:…`.

---

## Step 3 · Tell Sarathi which model answers

```bash
sarathi init
```

**On your own computer** (choose 1). Sarathi asks Ollama which models
you've pulled and suggests one that can hold a conversation:

```
Which model should answer?
  1) one on this machine, through Ollama -- free, private, needs a GPU or patience
  2) Anthropic's, with an API key
  3) OpenAI's, with an API key
Choose 1, 2 or 3 [1]: 1
Pulled models that can talk:
  1) qwen3.8:latest
  2) gemma4:12b
Choose one [1 = qwen3.8:latest]:
wrote ~/.config/sarathi/sarathi.toml
  answering: ollama, qwen3.8:latest
next: `sarathi up`
```

**In the cloud** (choose 2 or 3). Paste your key when asked. Nothing
shows as you paste, which is on purpose:

```
Choose 1, 2 or 3 [1]: 2
ANTHROPIC_API_KEY (hidden as you type; Enter to skip):
wrote ~/.config/sarathi/sarathi.toml
  answering: anthropic, its default model
  ANTHROPIC_API_KEY saved to ~/.config/sarathi/secrets.env (readable only by you)
next: `sarathi up`
```

To choose a particular cloud model, run it as
`sarathi init --force --provider anthropic --model claude-sonnet-5-5`
instead, or edit the file afterwards.

What it wrote is a short file you can read and change at any time:

```toml
[model]
provider = "ollama"
model = "qwen3.8:latest"

[web]
port = 8321

[clock]
on = true
port = 8780

[run]
road = "process"
```

Your key is **not** in it. It's in `secrets.env` beside it, so this file
is safe to show someone if you need help.

---

## Step 4 · Start it

```bash
sarathi up
```

```
clock  up at http://127.0.0.1:8780/#token=…  (pid 3324159)
page   up at http://127.0.0.1:8321/  (pid 3324163)
```

Open **http://127.0.0.1:8321/** in your browser. That's the helper. Try:

* *"Anything from my accountant this week?"*
* *"Every weekday at 8, tell me if anything in my mail needs me."*

The second one is a schedule. The helper will say back *when* it will
run and *what* it will do, and wait for your yes before saving it. After
that, Samay's clock does it every weekday at 8, whether or not the page
is open. Its own page (the `clock` address above, token included) lists
every schedule and every run.

When you're done:

```bash
sarathi down
```

```
clock  stopped  (pid 3324159)
page   stopped  (pid 3324163)
```

`sarathi status` shows, at the end, what `up` started and whether each
one is still running.

---

## Step 5 (optional) · Keep it running, even after a restart

`sarathi up` starts the programs from your terminal session. When the
computer restarts, they're gone until you run it again, and that
includes the clock, so a schedule set for 8:00 won't run if the machine
rebooted at 7:00.

If you have **Podman** (a program for containers), Sarathi can instead
run them as containers that your computer keeps running: restarted if
they crash, started again when you log in.

```bash
sarathi init --force --podman     # same questions, plus: use containers
sarathi image                     # builds the container image (a few minutes)
sarathi up
```

```
units rewritten from sarathi.toml
clock  up at http://127.0.0.1:8780/#token=…  (unit sarathi-clock)
page   up at http://127.0.0.1:8321/  (unit sarathi-page)
```

Same page, same accounts, same schedules, same memories: the containers
use your files where they already are.

Three things to know on this road:

* **On your own computer's model:** Ollama has to accept connections
  from the containers. Start it with `OLLAMA_HOST=0.0.0.0 ollama serve`
  (or set that in its service settings).
* **In the cloud:** the key has to be in `secrets.env` (Step 3 puts it
  there). A key you typed into your terminal another way won't reach
  the containers, so Sarathi refuses to start without it rather than
  start a helper that can't answer.
* **Accounts that need a browser** (Amazon, X) don't work in containers
  yet. Gmail and Home Assistant do.

`sarathi down` stops them, and they come back at your next login. To stop
that too: `sarathi down --remove`.

When the projects get an update (`git pull` in their folders), run
`sarathi image` again and then `sarathi down && sarathi up`.

---

## When something goes wrong

Sarathi tries to say what happened and what fixes it. The messages
you're most likely to meet:

| You see | What it means | Do this |
|---|---|---|
| `Ollama is not answering at http://localhost:11434` | Ollama isn't running | `ollama serve`, or start the Ollama app |
| `qwen3.8:latest is not pulled yet` | the model isn't downloaded | `ollama pull qwen3.8:latest` |
| `no key for anthropic: run sarathi init or set ANTHROPIC_API_KEY` | no key saved | `sarathi init --force` and paste it |
| `page not started: something else is listening on port 8321` | another program uses that port | change `port` under `[web]` in sarathi.toml |
| `page exited at once (code 2)`, then a few lines | the page stopped as it started | read the lines; `--web needs the web extra` means Step 1's `uv sync --extra web` was missed |
| `clock already running at …, not started by Sarathi: left alone` | you already run Samay's clock another way | nothing: a second clock would run every schedule twice |
| `unknown key clock.onn` | a typo in sarathi.toml | fix the spelling; Sarathi never guesses |
| `no image yet (localhost/sarathi:latest): run sarathi image first` | Podman road, image not built | `sarathi image` |
| a schedule never runs | the clock isn't running | `sarathi status`; on the process road, the clock stops with your session (Step 5 fixes that) |

Each program also writes down what it printed:
`~/.local/share/sarathi/logs/page.log` and `clock.log` on the process
road; `journalctl --user -u sarathi-page` on the Podman road.

---

## Where your things are

| What | Where |
|---|---|
| Sarathi's settings | `~/.config/sarathi/sarathi.toml` |
| A cloud key | `~/.config/sarathi/secrets.env` (only you can read it) |
| Your sign-ins | Setu's folder, `~/.local/state/setu/` |
| Your schedules and their history | Samay's folder, `~/.samay/` |
| What the helper remembers about you | `~/.local/state/yantra/` |
| What Sarathi started, and what each printed | `~/.local/share/sarathi/` |

Sarathi doesn't move anything: each program keeps its files where it
always has. To start over with Sarathi, delete its two folders; your
accounts, schedules and memories stay.

---

## Words used here

* **Model** — the part that reads your message and writes the answer.
* **Ollama** — a free program that runs models on your own computer.
* **API key** — a long password a cloud company gives you so your
  computer can use its model. Treat it like a password.
* **Account / connection** — one sign-in Setu keeps, like `gmail:mine`.
* **Schedule** — something Samay asks the helper to do later, or on a
  repeat.
* **Port** — a number that tells your browser which program on your
  computer to talk to (8321 for the page, 8780 for the clock).
* **Container** — a program running in its own sealed box, which your
  computer can restart on its own. Podman is the program that runs them.
