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

Six small programs, each with one job. You'll use three of them today:

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

(Dvara, for your helper on your phone and for your family over
Telegram, is Step 6, when you want it. Sparsh, which lets the helper
work an Android phone plugged into this computer, is optional: install
it (its SETUP.md) and Sarathi finds it, and Yantra's page gets a phone
panel. `sarathi phone` turns it on for the door too, and on the
containers' road it reaches the phone over Wi-Fi. Smritikosh, a bigger memory store, is optional too; Sarathi will
mention it, and you can ignore it.)

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
setu   up at http://127.0.0.1:8775/#token=…  (pid 3324170)
home   up at http://127.0.0.1:8760/#token=…  (pid 3324178)
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

**One bookmark for all of it.** The `home` line above is a page that
links every other page: Yantra's, Samay's, Setu's (your accounts, who in
your household has their own page open, the catalog and Setu's
settings) and, once you turn the door on in Step 6,
Dvara's (your door: who's on it, their files and schedules, and the
questions your agents are asking you). Open that address and bookmark
it. It shows whether each page is running and opens any of them already
signed in.

---

## Step 5 (optional) · Plain programs, or containers

Sarathi runs everything two ways, and you can switch back and forth.
Everything in this tutorial works either way, with the same accounts,
schedules and memories.

**Plain programs (what you have now).** `sarathi up` starts the
programs from your terminal session, using your own Chrome and your
own bubblewrap (`sudo apt install bubblewrap` if `setu status` says
connectors aren't walled off). Nothing to build, and a `git pull` in a
project folder is picked up at the next `sarathi up`. But when the
computer restarts they're gone until you run it again, and that
includes the clock, so a schedule set for 8:00 won't run if the machine
rebooted at 7:00.

**Containers.** If you have **Podman** (a program for containers),
Sarathi can run them as containers your computer keeps running:
restarted if they crash, started again when you log in.

```bash
sarathi road podman               # use containers from now on
sarathi image                     # builds the container image (a few minutes, ~1.3 GB)
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
* **Accounts that need a browser** (Amazon, X) work here too: the image
  has its own Chrome. If `up` says your computer's Chrome is newer than
  the image's, run `sarathi image` again; Chrome won't open a sign-in a
  newer Chrome saved.

`sarathi down` stops them, and they come back at your next login. To stop
that too: `sarathi down --remove`.

When the projects get an update (`git pull` in their folders), run
`sarathi image` again and then `sarathi up`: it restarts whatever runs an
older image or older settings, and leaves the rest alone.

**Back to plain programs** any time:

```bash
sarathi road process              # stops the containers and removes their units
sarathi up
```

`sarathi road` on its own says which way you're running.

---

## Step 6 (optional) · On your phone, and for your family

So far the helper lives on one page on your computer. **Dvara** (the
door) puts it on Telegram: you can ask it from your phone, and so can
the people you choose, each as themselves. Each person gets their own
conversations, their own spending limit, and, if you give them one,
their own accounts that they connect themselves. Nobody you didn't list
gets an answer at all.

**First, a bot.** In Telegram, talk to **@BotFather**, send `/newbot`,
and pick a name. It gives you a token (a long line like
`123456:AAE…`). Keep it like a password.

**Then:**

```bash
sarathi door
```

```
Which agent should a Telegram bot answer as? greeter
Your bot's token from BotFather (TELEGRAM_TOKEN; hidden as you type): ••••
the door is on in ~/.config/sarathi/sarathi.toml: port 8770, a Telegram bot answering as greeter
  made the door's own token (DVARA_TOKEN, in secrets.env)
  TELEGRAM_TOKEN saved to secrets.env (readable only by you)
  wrote ~/dvara/actors.toml: you, as the owner (your Telegram id still to add)
  copied dvara's example agents to ~/dvara/agents (greeter, minder, scribe): replace them with your own
```

`greeter` is a small example helper that only talks. It's there to
prove everything works. `minder` checks a web page for you, and can do
it on a schedule you say yes to in the chat. Your own helpers go in
`~/dvara/agents` later (dvara's tutorial shows how).

**Start it:**

```bash
sarathi down && sarathi up
```

```
clock  up at http://127.0.0.1:8780/#token=…
door   up at http://127.0.0.1:8770/
page   up at http://127.0.0.1:8321/
```

`sarathi status` asks the door itself whether it's serving, so the
dvara line says `door serving …` once it's open, and `door not serving`
if it stopped.

**Let yourself in.** Message your bot. It won't answer yet: it doesn't
know who you are. Then:

```bash
sarathi status
```

```
  door   running at http://127.0.0.1:8770/
         messaged the bot but not in the actors file (telegram id): 8675309
```

That number is you. Open `~/dvara/actors.toml`, find the lines under
"Your Telegram id", remove the `#`s and put your number in. Message the
bot again: it answers. (No restart needed; the door rereads the file.)

**Your own accounts from your phone.** Under `[actor.owner]` in the same
file, one of:

```toml
setu = "~/.local/state/setu"   # the accounts you already connected on this computer
setu = true                    # a separate folder, starting empty: you connect from the chat
```

`setu = true` is the safe way to try things first: nothing you do from
the phone touches the accounts on your computer.

With the first, the phone and the page share one set of sign-ins, but
`/connect` from the chat answers that the owner looks after them, the
same as it would for a guest. You are the owner, so add:

```toml
setu_manage = true             # /connect, /disconnect and /accounts reach that folder
```

Then when Amazon asks for its password again (it does, for its orders
page, after a while), you send `/connect amazon` and sign in in the
window it streams to your phone. Tick *Keep me signed in* there; a
sign-in without it is asked for again sooner. `/lock` still belongs to
the computer, since a passphrase on that folder would lock the page out
too (dvara's note 27).

An agent reads Amazon only if its package asks for it. For `minder`,
add to `~/dvara/agents/minder/agent.toml`:

```toml
[tools]
allow = ["web_fetch", "read_file", "write_file", "mcp__samay__*", "amazon_*"]

[connections]
needs = ["amazon:read"]        # open, follow, scroll, search -- never a click or a purchase
```

Then ask *"What were my last three Amazon orders? Just the titles and
the dates."*

**Try each piece from your phone.** Both ways of running (plain programs
or containers, Step 5) work for all of this. Say `minder` was the agent
you gave the bot:

1. **A schedule.** Send *"check whether example.com is up once an hour,
   and only tell me if it's down"*. It says back when it will run and
   asks if that's right. Say yes. A card arrives with two buttons:
   *Save a schedule … when: every hour … without asking, it may also
   use: web_fetch*. Press approve. If a card ever comes before you've
   said yes, refuse it: the card is the real yes, and you can always
   ask again.
2. **A record.** Ask for the same with *"…and keep a record in
   uptime-log.txt"*. The card now also lists `write_file`. Later, ask
   *"what does my uptime log say?"*. Every run, and every chat you have
   with that agent, uses the same folder, so it finds the lines the
   schedule wrote. To see a run happen now instead of in an hour:
   `~/agent/samay/.venv/bin/samay run-now <id>` (the id is in the bot's
   answer, or in `samay list`; on containers,
   `podman exec sarathi-clock samay run-now <id>`).
3. **Gmail, connected from the chat.** Send `/connect gmail`. Open the
   link on your phone, sign in to Google and allow it. Your phone then
   tries to open a page at `http://127.0.0.1:…` and **fails to load it.
   That's expected**: copy that page's whole address (it contains
   `code=…`) and send it to the bot. It answers *connected*, and
   `/accounts` lists Gmail. `/disconnect gmail` takes it away again.
4. **Amazon, through a window** (set up below). Send `/connect amazon`.
   The link shows Amazon's real sign-in page, live, at your phone's
   size. Type your email in the box at the bottom and press **Send**: it
   goes into the page's empty box by itself (tap a box on the picture
   first to type somewhere else). Then **Enter**, or just your
   keyboard's Go, which sends and presses Enter in one. The same for
   your password and any code Amazon texts you. Tapping a button on the
   picture (Continue, Sign in) always works too.
   When you're in, the page says so and the bot says *connected*.

If something doesn't answer, `sarathi status` says which piece stopped,
and the end of its log: `~/.local/share/sarathi/logs/door.log` for plain
programs, `journalctl --user -u sarathi-door -n 60` for containers.

**Adding someone else** is the same: they message the bot, you read
their number in `sarathi status`, and you add them to `actors.toml`
(the file has a commented example). Give them `setu = true` and they can
connect their own Gmail from their phone by sending `/connect gmail` to
the bot. Their sign-ins are kept on your computer, in a folder of their
own, so you could read them. Tell them that.

**Amazon or X for them, too.** Those sites can't send a sign-in link;
they're signed in to in a browser on your computer. If you tell the door
where its pages can be reached, it sends the person a link that shows
that browser live on their phone, and they sign in by tapping and typing:

```bash
sarathi door --window-host <your computer's address>
sarathi up
```

Which address: if everyone is on your home Wi-Fi, your computer's
address there works (`hostname -I` shows it, often `192.168.…`), but
what they type travels as plain web traffic across your Wi-Fi. If you
use **Tailscale**, its address is the safe choice, encrypted and
reachable wherever they are.

The window uses port **8790** (`--window-port` changes it). If your
computer has a firewall (`sudo ufw status` says *active*), let your home
network reach that port, and close it again when you no longer need it:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8790 proto tcp     # your network's numbers
sudo ufw delete allow from 192.168.1.0/24 to any port 8790 proto tcp
``` Your computer runs
that browser, so it handles what they type, their password included:
offer it to people who already trust you with their agent.

To turn the door off again: `sarathi door --off`, then
`sarathi down && sarathi up`.

If another program on your computer already uses the door's port
(8770), `sarathi up` says so and names the setting:
`sarathi door --port 8771` (any free number), then `sarathi up`.

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
| `door not started: door.telegram is set but there is no TELEGRAM_TOKEN` | the bot's token wasn't saved | `sarathi door` again, and paste it |
| `door not started: no actors file at ~/dvara/actors.toml` | dvara's list of people is missing | `sarathi door` writes a starter one |
| the bot never answers you | you're not in the actors file yet | Step 6, "Let yourself in" |
| `browser: this machine has Chrome …, the image …` | your Chrome updated itself after the image was built | `sarathi image`, then `sarathi up` |
| `door not started: something else is listening on port 8770 (change door.port in sarathi.toml)` | another program on your computer uses that port | `sarathi door --port 8771` (any free number), then `sarathi up` |
| `I couldn't start that sign-in: the browser did not answer Target.createTarget` | containers from an older Sarathi: the browser had nowhere to write | update Sarathi, then `sarathi up` (it restarts what changed) |
| `I couldn't start that sign-in: no client file at …client_secret….json` | containers from an older Sarathi: Google's client file wasn't mounted | the same: update, then `sarathi up` |
| `the door cannot start: the image has no dvara` | Podman road, image built without dvara | put dvara's folder beside the others, then `sarathi image` |
| `door did not come up` or `page did not come up`, and its journal says `image platform (linux/arm64/v8) does not match` | the image was built for another machine (an older `sarathi image` after an arm64 build) | `sarathi image`, then `sarathi up` |

Each program also writes down what it printed:
`~/.local/share/sarathi/logs/page.log`, `clock.log` and `door.log` on
the process road; `journalctl --user -u sarathi-page` (or `-door`,
`-clock`) on the Podman road.

---

## Where your things are

| What | Where |
|---|---|
| Sarathi's settings | `~/.config/sarathi/sarathi.toml` |
| A cloud key, and the door's and bot's tokens | `~/.config/sarathi/secrets.env` (only you can read it) |
| Who may use the bot, and the helpers it offers | `~/dvara/actors.toml`, `~/dvara/agents/` |
| Their conversations, and their own sign-ins | `~/dvara/state/` |
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
* **Bot** — a Telegram account that a program answers instead of a
  person. @BotFather makes one and gives you its token.
* **Actors file** — dvara's list of the people it answers, and what
  each may use.
