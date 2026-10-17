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
panel. `sarathi phone` turns it on for Dvara too, and on the
containers' road it reaches the phone over Wi-Fi. Smritikosh, a memory
that finds things by meaning, is optional too: Step 7, when the helper
starts forgetting things you told it.)

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
            work done later, with receipts
            not running (start it: samay serve); schedules: 0 active, 0 paused
dvara       not found (optional) -- install it, or set SARATHI_DVARA=/path/to/dvara
            many people and agents behind one service
smritikosh  not found (optional) -- install it, or set SARATHI_SMRITIKOSH=/path/to/smritikosh-mcp
            a memory store (Yantra keeps its own without it)

memory: the built-in file (local); `sarathi smritikosh` switches to Smritikosh
```

Each line says **where** it found a program and **how** (`beside` means
"in the folder next to Sarathi"). The line under it is that program
describing itself. "not found (optional)" is fine. The last line says
where the helper keeps what it remembers about you (Step 7).

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

**One week later, Gmail may stop.** Google expires the sign-in of an app
still in *Testing* every seven days. You'll see it in `sarathi status`
(`SIGN-IN EXPIRED, sign in again: setu connect gmail --as personal`), in
`setu list`, and from the helper itself when you ask about mail. Run that
command, and the helper has Gmail again on your next message; nothing
needs restarting, containers included. To stop it happening, publish your
Google app once (Setu's README, *Testing mode signs you out weekly*).

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
Where should what you tell it be remembered?
  1) Yantra's own file on this computer -- nothing to install
  2) Smritikosh, which finds a memory by meaning, not only its words --
     a database in a container, set up now (about a minute)
Choose 1 or 2 [1]:
wrote ~/.config/sarathi/sarathi.toml
  answering: ollama, qwen3.8:latest
  memory: Yantra's own file (`sarathi smritikosh` switches to Smritikosh)
next: `sarathi up`
```

The last question can wait: press Enter. Yantra's own file is all you
need to start, and Step 7 switches whenever you like.

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

[yantra]
port = 8321

[samay]
on = true
port = 8780

[run]
road = "process"

[memory]
via = "local"
```

(There are a few more tables, each with a comment saying what it does.)
Your key is **not** in it. It's in `secrets.env` beside it, so this file
is safe to show someone if you need help.

---

## Step 4 · Start it

```bash
sarathi up
```

```
samay      up at http://127.0.0.1:8780/#token=…  (pid 3324159)
yantra     up at http://127.0.0.1:8321/  (pid 3324163)
setu       up at http://127.0.0.1:8775/#token=…  (pid 3324170)
sarathi    up at http://127.0.0.1:8760/#token=…  (pid 3324178)
```

Open **http://127.0.0.1:8321/** in your browser. That's the helper. Try:

* *"Anything from my accountant this week?"*
* *"Every weekday at 8, tell me if anything in my mail needs me."*

The second one is a schedule. The helper will say back *when* it will
run and *what* it will do, and wait for your yes before saving it. After
that, Samay's clock does it every weekday at 8, whether or not the page
is open. If a run needs your yes for something you didn't allow up
front (a schedule to turn a light off, say), it asks you on Telegram and
on the home page's chat, rather than giving up. Its own page (the `clock` address above, token included) lists
every schedule and every run.

When you're done:

```bash
sarathi down
```

```
samay      stopped  (pid 3324159)
yantra     stopped  (pid 3324163)
```

`sarathi status` shows, at the end, what `up` started and whether each
one is still running.

**One bookmark for all of it.** The `home` line above is a page that
links every other page: Yantra's, Samay's, Setu's (your accounts, who in
your household has their own page open, the catalog and Setu's
settings) and, once you turn Dvara on in Step 6,
Dvara's (your door: who's on it, every turn your agents took and how
each came in — Telegram, the web, a Samay schedule or the terminal —
their files and schedules, and the questions your agents are asking
you). Open that address and bookmark
it. It shows whether each page is running and opens any of them already
signed in. Its **Memory** card says where the helper keeps what it
remembers about you, and once you've done Step 7 it switches between the
two.

Once Dvara is on (Step 6), the same page also has **Talk to your
agents** at the top: a chat with the agents behind Dvara, with no
Telegram needed. What a schedule sends you waits there as a line marked
*Sent to you*, including the answers of schedules you make on Yantra's
page. When an agent wants a yes, a card with **Yes** and **No** appears
under the chat.

Give it a job of a few steps and watch: each step shows as a line while
it runs, then the answer appears as it's written. The buttons under the
chat ask without typing: **Skills** (what your agent has learned, and
anything it offers to keep), **Tools** (what it could use on your last
message), **Schedules**, **Memory**, **Phone** (if the phone is yours:
its screen now, and what was last done on it), **New chat**, **Past chats** (what
New chat ended, kept; write `/chats 2` to go back into the second, and
its messages show again under the answer). After a job of four
steps or more, an agent whose package has skills may offer to keep how
it was done. Press **Keep** and next time it's one step, for you only.
For a shorter job, press **Learn this** after it to ask for the same
offer.
On a phone, **Full screen** gives the chat the whole window.

To show it something, press the paperclip beside **Send** and pick a
photo or a file (a receipt, a letter from school), then ask about it.
It's kept in your folder with that agent, under `from-you/`, and the
agent can read it again later. A picture is looked at only by a model
that can see (most new local ones can; `ollama show MODEL` lists
"vision"). Otherwise the agent says it can't look. On Telegram, just send
the photo or file to the bot, with your question as its caption.

Voice notes work too: on Telegram, hold the microphone and talk; on the
home page, press 🎤, talk, press it again, then **Send**. A local model
that can hear turns it into words first (Dvara picks the smallest one in
Ollama that lists "audio", such as `gemma4:e4b`; `ollama pull gemma4:e4b`
if you have none). The answer starts with *I heard: "…"*, so you can see
if a name was misheard. Your phone's browser can't record from the home
page over plain `http://` (browsers allow the microphone only on this
computer or over https); Telegram has no such limit.

---

**Changing a setting later.** Everything you chose here, and everything
in the steps below, can be changed on the home page, under **Settings**:

* **People**: who may use your agents, which ones, their daily
  allowance, their accounts, their Telegram id.
* **Agents**: each agent's model, tools, memory, accounts and
  instructions. Add one from an example, or remove one. Tools are
  checkboxes: each says what it does and whether it *asks you first* or
  *runs unasked* (open a page in its own browser, remember things about
  you, your schedules, your phone...). Names no box stands for, like
  `amazon_*`, wait under **Advanced**. Under each agent, *Skills its
  people kept* lists what each person's agent learned and how often it
  worked. One with a script has **Make it a tool**: its script runs once
  as a test, and it's kept (for that person only) if the test passes.
  Then the agent does that job in one step. **Stop using as a tool**
  takes it back: the skill stays, as steps the agent reads.
* **Rules**: standing answers for a tool (always allow, always ask,
  never), so you're not asked the same thing twice.
* **Accounts**: Setu's settings, and the rules of each site you added.
* **Sarathi**: the model, Dvara and its bot, notices on phones, your
  phone, ports.
* **Keys**: a cloud key or the bot's token, typed in once and never
  shown back.

Each program checks a change before it's saved and keeps the file
before as a backup, so a mistake is refused, not saved. People, agents
and rules take effect from the next message. A change under Sarathi or
Keys shows **Apply**, which starts everything again with it (about a
minute). Each tab also has **Edit as text**, for the file itself.

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
includes Samay, so a schedule set for 8:00 won't run if the machine
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
samay      up at http://127.0.0.1:8780/#token=…  (unit sarathi-samay)
yantra     up at http://127.0.0.1:8321/  (unit sarathi-yantra)
```

Same page, same accounts, same schedules, same memories: the containers
use your files where they already are.

Four things to know on this road:

* **On your own computer's model:** Ollama has to accept connections
  from the containers. Start it with `OLLAMA_HOST=0.0.0.0 ollama serve`
  (or set that in its service settings).
* **Your Yantra `.env` stays behind.** The containers are built from
  what's committed, and `.env` never is. A setting you put there, like
  `OLLAMA_CONTEXT_WINDOW=64000` for a 64k model, goes in `sarathi.toml`
  instead, as `context_window = 64000` under `[model]`.
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
sarathi dvara
```

```
Which agent should a Telegram bot answer as? greeter
Your bot's token from BotFather (TELEGRAM_TOKEN; hidden as you type): ••••
Dvara is on in ~/.config/sarathi/sarathi.toml: port 8770, a Telegram bot answering as greeter
  made Dvara's own token (DVARA_TOKEN, in secrets.env)
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
samay      up at http://127.0.0.1:8780/#token=…
dvara      up on 8770 (no page here; yours is dvara-page, below)
yantra     up at http://127.0.0.1:8321/
```

`sarathi status` asks Dvara itself whether it's serving, so the
dvara line says `door serving …` once it's open, and `door not serving`
if it stopped.

**Let yourself in.** Message your bot. It won't answer yet: it doesn't
know who you are. Then:

```bash
sarathi status
```

```
  dvara      running on 8770 (no page here; yours is dvara-page, below)
         messaged the bot but not in the actors file (telegram id): 8675309
```

That number is you. Open the home page, go to **Settings → People**: the
number is listed under *Messaged your Telegram bot, but not on the
list*. Press **Change** on yourself (`owner`), put the number in
*Telegram ids*, and **Save**. Message the bot again: it answers. (No
restart needed; Dvara rereads its list. If you'd rather edit the file,
it's `~/dvara/actors.toml`, and **Edit as text** at the bottom of the
same tab shows it.)

**No phone handy?** Open the home page (the `sarathi` line `up`
printed). With Dvara on, it has a chat at the top: pick `greeter`, say
hello, and the answer appears a few seconds later. It's the same Dvara
with the same rules, but its own conversation: what you said on
Telegram doesn't carry over. If it says Dvara is running without its
web channel, run `sarathi down` and `sarathi up` (on the Podman road,
`sarathi image` first).

**Your own accounts from your phone.** In **Settings → People**, press
**Change** on yourself and pick *Accounts their agents use*:

* *This computer's accounts (yours)*: the phone and the page share one
  set of sign-ins. Also tick *They may connect and disconnect those from
  the chat*, or `/connect` from the chat answers that the owner looks
  after them, the same as it would for a guest.
* *Their own*: a separate folder, starting empty, that you connect from
  the chat. The safe way to try things first: nothing you do from the
  phone touches the accounts on your computer.

(In the file these are `setu = "~/.local/state/setu"` with `setu_manage =
true`, or `setu = true`.) **My accounts**, at the top of the home page,
opens Setu's page for your own accounts.

Then when Amazon asks for its password again (it does, for its orders
page, after a while), you send `/connect amazon` and sign in in the
window it streams to your phone. Tick *Keep me signed in* there; a
sign-in without it is asked for again sooner. `/lock` still belongs to
the computer, since a passphrase on that folder would lock the page out
too (dvara's note 27).

An agent reads Amazon only if its package asks for it. In **Settings →
Agents**, press **Change** on `minder` and add a line to *Accounts it
needs*:

```
amazon:read                    open, follow, scroll, search -- never a click or a purchase
```

(In its file, `~/dvara/agents/minder/agent.toml`, that's `needs =
["amazon:read"]` under `[connections]`.)

The need brings Amazon's tools with it; `[tools] allow` doesn't have to
name them. Your home works the same way: `needs = ["amazon:read",
"homeassistant:write"]` lets minder see your lights and switch one, and
switching asks you on Telegram first.

To let minder read **every** account you connect, now and later, put
`*:read` there instead of naming each one: `needs = ["*:read",
"homeassistant:write"]` reads Amazon, X, Gmail, Yahoo and whatever you
add next, and still switches lights. Without it, an account you didn't
name isn't minder's. minder is told so, and says so, rather than trying
your phone instead.

A webmail inbox like Yahoo's opens each message with a script, so
reading it takes one more line, in Setu's file for the site
(`~/.local/state/setu/sites/yahoo.toml`): `script_links = true` under
`[browser]`. With it, minder opens a message the way you would, and
still never presses a button that deletes, sends or moves one (Yantra's
note 128).

Then ask *"What were my last three Amazon orders? Just the titles and
the dates."*

**Try each piece from your phone.** Both ways of running (plain programs
or containers, Step 5) work for all of this. Say `minder` was the agent
you gave the bot:

1. **A schedule.** Send *"check whether example.com is up once an hour,
   and only tell me if it's down"*. It says back when it will run and
   asks if that's right. Say yes. A card arrives with two buttons:
   *New schedule … When: every hour … May use without asking:
   web_fetch*. Press approve. If a card ever comes before you've
   said yes, refuse it: the card is the real yes, and you can always
   ask again.
2. **A record.** Ask for the same with *"…and keep a record in
   uptime-log.txt"*. The card now also lists `write_file`. Later, ask
   *"what does my uptime log say?"*. Every run, and every chat you have
   with that agent, uses the same folder, so it finds the lines the
   schedule wrote. To see a run happen now instead of in an hour:
   `~/agent/samay/.venv/bin/samay run-now <id>` (the id is in the bot's
   answer, or in `samay list`; on containers,
   `podman exec sarathi-samay samay run-now <id>`).
   **A schedule that changes something** works the same way. Say *"turn
   off the stairs light in 5 minutes"* (with Home Assistant connected).
   The card should name the one switch it may use (*call_service — only
   with domain=switch, service=turn_off, entity_id=…*). If instead it says
   in capitals *NOTHING ALLOWED HERE CAN CHANGE ANYTHING*, approve anyway
   or refuse and ask again. Either way, at its time anything nobody
   allowed comes to you here as a Yes/No and waits 30 minutes; it never
   just fails quietly. A run that was refused something says so, with
   how to allow it next time.
3. **Gmail, connected from the chat.** Send `/connect gmail` (or, if
   you asked about mail first, press the **Connect gmail** button under
   the answer: it sends the same word). Open the
   link on your phone, sign in to Google and allow it. Your phone then
   tries to open a page at `http://127.0.0.1:…` and **fails to load it.
   That's expected**: copy that page's whole address (it contains
   `code=…`) and send it to the bot. It answers *connected*, and
   `/accounts` lists Gmail. `/disconnect gmail` takes it away again. If
   Gmail stops a week later (Google's limit while your app is in
   Testing), the bot says so when you ask about mail: send `/connect
   gmail` again, and your next message has it back.
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
programs, `journalctl --user -u sarathi-dvara -n 60` for containers.

**Adding someone else** is the same: they message the bot, their number
shows in **Settings → People**, and you press **Add as a new person**
(or **Add a person** for someone who'll only use the home page). Choose
their agents and a daily allowance. Pick *Their own* accounts and they can
connect their own Gmail from their phone by sending `/connect gmail` to
the bot. Their sign-ins are kept on your computer, in a folder of their
own, so you could read them. Tell them that.

**Amazon or X for them, too.** Those sites can't send a sign-in link;
they're signed in to in a browser on your computer. If you tell Dvara
where its pages can be reached, it sends the person a link that shows
that browser live on their phone, and they sign in by tapping and typing:

```bash
sarathi dvara --window-host <your computer's address>
sarathi up
```

Which address: if everyone is on your home Wi-Fi, your computer's
address there works (`hostname -I` shows it, often `192.168.…`), but
what they type travels as plain web traffic across your Wi-Fi. If you
use **Tailscale**, its address is the safe choice, encrypted and
reachable wherever they are.

The window uses port **8790** (`--window-port` changes it). With the
pages on, more ports open on that address: **8760**, the home page,
where the people in the house sign in (below); **8775**, Setu's page,
which a person reaches with `/accounts page`; and, on the Podman road,
**8791**, the window that page streams when they connect Amazon or X
from it. If your computer has a firewall, a phone gets nothing from
those ports, just a page that keeps loading. `sarathi up` notices ufw or
firewalld and prints the line that opens exactly those ports to your
network:

```text
firewall: ufw is on; if a phone can't open 192.168.1.44 on 8760, 8775, 8790, 8791, open them to your network (once is enough):
  sudo ufw allow from 192.168.1.0/24 to any port 8760,8775,8790,8791 proto tcp
```

Run that line yourself; Sarathi never changes your firewall. To close
them again: `sudo ufw delete allow from 192.168.1.0/24 to any port
8760,8775,8790,8791 proto tcp`.

Your computer runs
that browser, so it handles what they type, their password included:
offer it to people who already trust you with their agent.

**A chat of their own, without Telegram.** Someone in the actors file
who doesn't use Telegram can talk to their agents on the home page, as
themselves. With the window address set (above), invite them:

```bash
sarathi invite priya
```

```
priya's link, for one device, within 48 hours:
  http://192.168.1.44:8760/#invite=priya.…
They open it and choose a password; after that they sign in with 'priya' and that password, and see their own chat only.
```

Send them that link however you like (a text message, say). It works
once: the phone that opens it first chooses a password, and from then
on they sign in with their name and that password. They see their own
chat and nothing else on the page. It runs with their allowance and
their agents, and you see on Dvara's page what they spent, not what they
said. The home page has a **People in the house** list that does the
same with buttons: **Invite** shows the link, **Sign out everywhere**
signs them out on every device. Forgot their password? Invite them
again: the new link lets them choose a new one. `sarathi people` lists
who has signed in.

Signed in, they also see **My accounts**: press it and tap *Open my
accounts page* to see and connect their own accounts (Gmail, say). It
works once, on that phone, for ten minutes, the same as `/accounts page`
in a Telegram chat.

**Notices on a phone, without Telegram.** What a schedule sends waits on
the home page until they open it. To have it show on their phone as
well, turn on ntfy, a small push server that runs in your house:

```bash
sarathi dvara --ntfy
sarathi down && sarathi up
```

On plain programs, install ntfy first (<https://docs.ntfy.sh/install/>);
the containers bring their own. Then, on each phone:

1. Install the free **ntfy** app.
2. Open the home page, signed in, and open **Notices on this phone**.
   Tap *Open your notices in the ntfy app*. If that doesn't open it,
   press + in the app, turn on *Use another server*, and type the
   server and topic the page shows.
3. Ask for something on a schedule (*"in two minutes, tell me a joke"*),
   lock the phone, and wait. The notice arrives as *Your agents*, and
   tapping it opens the home page.

They hear notices while the phone can reach your house (home Wi-Fi).
Keep the topic private: whoever has it can read their notices. If
`sarathi up` prints a firewall line, it now includes ntfy's port, 8793.

**Two things that now happen by themselves.** Once a day Dvara checks
every sign-in, and if Google stopped one, the person whose account it is
gets a message saying so, with what to send to fix it. And when a
conversation goes quiet for half an hour, an agent that remembers sends
what it noticed about you (*"Lives in Raleigh"*), and keeps it only if
you answer `/remember 1`.

To turn Dvara off again: `sarathi dvara --off`, then
`sarathi down && sarathi up`.

If another program on your computer already uses Dvara's port
(8770), `sarathi up` says so and names the setting:
`sarathi dvara --port 8771` (any free number), then `sarathi up`.

**Your helper on your phone itself.** With Sparsh installed (its
SETUP.md), the helper can work your Android phone: read a screen, tap,
type, and ask you before Send, Pay or Delete. The containers can't reach
a USB cable, so they reach the phone over your Wi-Fi.

1. Plug the phone into this computer with USB debugging on (allow it
   on the phone), and let it listen on Wi-Fi. One command finds its
   Wi-Fi address and saves it, on any Android:

   ```bash
   sarathi phone tcpip
   #   the phone listens over Wi-Fi at 192.168.1.160:5555
   #   the phone is on in ~/.config/sarathi/sarathi.toml, over Wi-Fi at 192.168.1.160:5555
   #   next: `sarathi down && sarathi up` (or just `sarathi up`)
   ```

   Or on the home page: **Settings → Sarathi → Your phone → Turn on
   Wi-Fi from the cable**, then **Apply**. The cable can come out
   afterwards. (No cable? Android 11 and later can pair instead:
   *Developer options → Wireless debugging → Pair device with pairing
   code*, then **Pair** on the same card, or `sarathi phone pair ADDRESS
   CODE` and `sarathi phone ADDRESS`.)

2. Restart, so the containers get the address:

   ```bash
   sarathi down && sarathi up
   ```

   It says what's still missing: *"nobody in ~/dvara/actors.toml is
   marked `phone = true` yet"* (in **Settings → People**, **Change** on
   yourself, tick *Their agents may work the phone*), or *"minder, the
   agent on Telegram, can't use the phone: its [tools] … leaves out
   "mcp__sparsh__*""* (in **Settings → Agents**, **Change** on
   minder, tick *Your phone (Sparsh)* under *Tools it may use*). The restart matters: before it, the containers
   don't have this computer's key, and the phone asks *"Allow USB
   debugging?"* for a key you don't know. Say no to that one.

3. Try it from the computer, then from Telegram:

   ```bash
   podman exec sarathi-yantra yantra --prompt "On my phone, open Settings and tell me what the Battery row says."
   #   The Battery row in Settings says: "Battery — 98% - charging".
   ```

   Then send your bot the same question.

   Then one that stops for your yes: *"Call 555-0123 from my phone."*
   The bot sends a photo of your phone's screen with the Call button
   ringed in red, then one line (*"tap button "Call (dial)" … On the
   screen: field "555-0123""*) with **approve** and **refuse** under it.
   Press refuse. Nothing is dialled. For a tap only a picture can show,
   like a pin on a map, see Dvara's tutorial §18.

4. A schedule on your phone: ask your bot *"every morning at 8, tell me
   my phone's battery"* and accept the card. If the phone is locked with
   a PIN at 8, the bot asks you to unlock it and waits; with only a swipe
   lock, it just goes. Dvara's tutorial, §18, shows how to test this now
   instead of waiting for 8 o'clock.

5. Leave the phone's screen to Sparsh while the helper works it: it's
   kept on, and your own screen timeout comes back two minutes after the
   last step. For an old phone kept just for the helper, keep it on for
   good:

   ```bash
   sarathi phone --awake always      # or working (the default), or off
   sarathi up
   ```

   And answer on the card, not in words: when the helper is about to
   send something, the question comes with **Yes** and **No** buttons.
   If it asks *"shall I send it?"* in plain words instead, say yes and
   it does the step again and asks with the buttons.

**An iPhone instead of an Android.** The helper can work an iPhone
too. It needs a Mac once a week, to sign a small helper app that runs
on the iPhone (WebDriverAgent); Sparsh's SETUP.md, Part C, goes through
it step by step. Sarathi gives its agents one phone, so this replaces
an Android if you had one.

1. Start WebDriverAgent with the iPhone plugged into this computer,
   unlocked, and leave the terminal open:

   ```bash
   cd ~/sparsh
   PREFIX=com.you.sparsh scripts/start-wda-from-linux.sh
   ```

2. Tell Sarathi, and restart:

   ```bash
   sarathi phone iphone
   #   the iPhone answers at http://127.0.0.1:8100
   #   the iPhone is on in ~/.config/sarathi/sarathi.toml, in place of the Android at 192.168.1.160:5555
   #     the containers reach it at http://host.containers.internal:8100
   sarathi down && sarathi up
   ```

   Or on the home page: **Settings → Sarathi → Your phone → An iPhone
   instead → Use the iPhone**, then **Apply**. If it says *"nothing
   answers"*, step 1 isn't running.

3. Try it the same way as step 3 above: the **Your phone** card's
   phone panel shows the iPhone's screen, and
   `podman exec sarathi-yantra yantra --prompt "On my iPhone, open
   Settings and tell me what the Battery row says."` asks the helper.

   Keep the iPhone unlocked while the helper works: Sarathi can't change
   an iPhone's Auto-Lock the way it can an Android's screen timeout. A
   locked iPhone is said as locked. To go back to the Android:
   `sarathi phone tcpip` (or its address), then `sarathi up`.

---

## Step 7 (optional) · A memory that finds things by meaning

The helper remembers things about you: where you live, how you like
answers. Out of the box it keeps them in a small file that matches
**words**. Ask *"find me flights to Austin"* and it won't think of
*"lives near RDU"*, because the two share no word. Smritikosh is a memory
that searches by **meaning**, so it finds it.

You need Podman (Smritikosh keeps its memories in a database that runs
in a container) and, on your own computer's road, Ollama's small model
for meanings:

```bash
ollama pull nomic-embed-text
sarathi smritikosh
```

It takes about a minute and says each thing it does. The lines to look
for:

```
settings   wrote ~/agent/smritikosh/.env: ollama, nomic-embed-text, 768 dimensions
           (the tables are built for 768 now; another embedding model later means an empty database)
database   started smritikosh-postgres (docker.io/pgvector/pgvector:pg17, volume smritikosh-pgdata)
dashboard  built; `sarathi up` starts it on 127.0.0.1:3000
you        account 'asha' and its key (in secrets.env)
memory: smritikosh (in ~/.config/sarathi/sarathi.toml)
```

Then start things again, so the helper uses it:

```bash
sarathi up                  # on the containers' road: sarathi image first, then sarathi up
```

`sarathi status` now ends with a line like `memory: smritikosh at
http://127.0.0.1:8080 -- postgres ok; degraded; 0 remembered for asha`.
**Degraded is fine.** It means Smritikosh's optional extras are left
out, and the helper doesn't use them. To run them anyway (Neo4j, MongoDB
and Redis, about 1 GB more memory), add `--full`: `sarathi smritikosh
--full`, then `sarathi up`. If you already run them for Smritikosh,
they're found and used as they are. `--no-full` leaves them out again.

**Bring across what it already knew.** The old file isn't emptied or
moved. On Yantra's page, type `/memory copy local` once.

Schedules you make at this computer use it too: a morning check that
asks *"what's the weather where I live?"* knows where that is, the same
as the page.

**Try it.** On Yantra's page: `/memory add Prefers a window seat on
flights`, then `/memory find aeroplane seating`. It finds the window
seat, though the two share no word.

**See everything it remembers.** Smritikosh has a page of its own, its
dashboard, and `sarathi up` starts it: open **http://localhost:3000/dashboard/memories**
(the bare `localhost:3000` can open blank),
or **Open Smritikosh's dashboard** on the home page's Memory card. Sign
in with your Smritikosh username and password. That's not a key: if you
set Smritikosh up by hand, it's the password you chose then; if Sarathi
made your account, the password is in
`~/.local/share/sarathi/smritikosh-accounts.json`. **Memories** lists what
the helper remembers about you. (The dashboard needs Node.js; without it,
everything else still works.)

**With Dvara on,** everyone in your actors file gets a memory of their
own: their own account and key, so one person's facts never reach
another's helper. You are you there too, so what you told Yantra's page,
your helper on Telegram knows. Someone you add later gets theirs the next
time you run `sarathi smritikosh`. A helper remembers people only if its
package asks for it (`[memory] via = "local"` in its `agent.toml`; with
Smritikosh on, that means Smritikosh).
Each person can sign in to the dashboard as themselves too: their
account is `dvara-<their id>`, and its password is in
`~/.local/share/sarathi/smritikosh-accounts.json`. To give someone an
account you made in the dashboard instead, see the README, "Where the
keys are".

**Changed your mind?** `sarathi smritikosh --off`, then `sarathi up`, or
the **Memory** card on the home page, which does both. Nothing is
deleted either way, and the same card switches back.

**Already set Smritikosh up by hand** (Yantra's SMRITIKOSH.md)? Just run
`sarathi smritikosh`. It finds your setup by its database, and uses your
database, settings and key as they are, making no new account for you.
If you keep it somewhere unusual, say where:
`SARATHI_SMRITIKOSH=/your/path/smritikosh/.venv/bin/smritikosh-mcp sarathi smritikosh`.

---

## When something goes wrong

Sarathi tries to say what happened and what fixes it. The messages
you're most likely to meet:

| You see | What it means | Do this |
|---|---|---|
| `Ollama is not answering at http://localhost:11434` | Ollama isn't running | `ollama serve`, or start the Ollama app |
| `qwen3.8:latest is not pulled yet` | the model isn't downloaded | `ollama pull qwen3.8:latest` |
| `no key for anthropic: run sarathi init or set ANTHROPIC_API_KEY` | no key saved | `sarathi init --force` and paste it |
| `yantra not started: something else is listening on port 8321` | another program uses that port | **Settings → Sarathi → Ports**, change Yantra's, **Save**, **Apply** (or `port` under `[yantra]` in sarathi.toml) |
| `page exited at once (code 2)`, then a few lines | the page stopped as it started | read the lines; `--web needs the web extra` means Step 1's `uv sync --extra web` was missed |
| `clock already running at …, not started by Sarathi: left alone` | you already run Samay's clock another way | nothing: a second clock would run every schedule twice |
| `unknown key clock.onn` | a typo in sarathi.toml | fix the spelling; Sarathi never guesses |
| On Telegram the agent says it has no Home Assistant (or Gmail…) and tells you to connect it, though Yantra's page uses it fine | the Telegram agent's package doesn't ask for that account | **Settings → Agents**, **Change** on that agent, add `homeassistant:write` to *Accounts it needs*; there's nothing to reconnect |
| `/memory` answers that the agent doesn't keep memories, and Telegram's `/` menu has no `memory` | its package doesn't remember people | **Settings → Agents**, **Change**, *Memory*: *Remembers each person*; restart Dvara for the menu (**Apply**, or `sarathi down && sarathi up`) |
| On Telegram the agent reads an email but says it can't open a link in it (a hotel's "View reservation") | the link goes to another site, and the account's tools keep to their own site | ask it what the email itself says (dates, number); to open such links, **Settings → Agents**, **Change**, tick *Open a page in its own browser* (no sign-in there), or tap the address it gives you |
| A sign-in from the chat: after your password the page never loads | that's the expected `http://127.0.0.1…` page, and Telegram's own browser may not show its address | open the link in Chrome instead, then copy the failing page's whole address back into the chat |
| `no image yet (localhost/sarathi:latest): run sarathi image first` | Podman road, image not built | `sarathi image` |
| a schedule never runs | Samay isn't running | `sarathi status`; on the process road, Samay stops with your session (Step 5 fixes that) |
| `dvara not started: dvara.telegram is set but there is no TELEGRAM_TOKEN` | the bot's token wasn't saved | `sarathi dvara` again, and paste it |
| `dvara not started: no actors file at ~/dvara/actors.toml` | dvara's list of people is missing | `sarathi dvara` writes a starter one |
| the bot never answers you | you're not in the actors file yet | Step 6, "Let yourself in" |
| a link from Dvara (`/accounts page`, a sign-in window) keeps loading on a phone | your firewall drops that port | run the `sudo ufw allow …` line `sarathi up` printed |
| `browser: this machine has Chrome …, the image …` | your Chrome updated itself after the image was built | `sarathi image`, then `sarathi up` |
| *"Your phone locked mid-task"* in the middle of a job | the screen went dark between two steps (a Sarathi from before `[phone] awake`) | `sarathi image`, then `sarathi up`; or `sarathi phone --awake always` |
| a phone question comes as a long numbered list with no photo, or the bot opens Maps' rows one by one | containers from before the picture on every question | `sarathi image`, then `sarathi up` |
| the bot says the phone tools "aren't connected" | the agent's `[tools] allow` leaves the phone out | add `"mcp__sparsh__*"` to it; `sarathi phone ADDRESS` says which file |
| a scheduled phone run is `skipped: the phone couldn't be reached` | the phone's address changed, or it restarted (it stopped listening over Wi-Fi) | plug it in, then `sarathi phone tcpip` (or **Settings → Sarathi → Your phone → Turn on Wi-Fi from the cable**); **Apply** if it says so |
| Yantra's phone panel says *No phone yet*, or *not answering over Wi-Fi*, after the phone was switched off and on | the same: a restarted phone stops listening, and its address may move | the same: plug in, **Turn on Wi-Fi from the cable**; then **use this phone** on Yantra's panel |
| `dvara not started: something else is listening on port 8770 (change dvara.port in sarathi.toml)` | another program on your computer uses that port | `sarathi dvara --port 8771` (any free number), then `sarathi up` |
| `I couldn't start that sign-in: the browser did not answer Target.createTarget` | containers from an older Sarathi: the browser had nowhere to write | update Sarathi, then `sarathi up` (it restarts what changed) |
| `I couldn't start that sign-in: no client file at …client_secret….json` | containers from an older Sarathi: Google's client file wasn't mounted | the same: update, then `sarathi up` |
| `dvara cannot start: the image has no dvara` | Podman road, image built without dvara | put dvara's folder beside the others, then `sarathi image` |
| `a Smritikosh database is already here … made with another setup's .env` | your own Smritikosh is somewhere Sarathi didn't look | `SARATHI_SMRITIKOSH=/path/to/smritikosh/.venv/bin/smritikosh-mcp sarathi smritikosh` |
| `SIGN-IN EXPIRED, sign in again: setu connect gmail --as …` | Google expired the sign-in (apps in Testing: every 7 days) | that command; publish your Google app to stop it (Step 2) |
| `mcp server 'gmail-…' exited unexpectedly (code 2)` | an older Yantra hiding the reason (usually the line above) | `setu list` shows the reason; `sarathi image`, then `sarathi up`, for the newer Yantra |
| `dashboard  not built: no npm here` | Node.js isn't installed | install Node.js 20 or newer, then `sarathi smritikosh` again |
| the dashboard signs you in, then shows the login page again | it was opened as `127.0.0.1:3000` | open `http://localhost:3000/dashboard/memories` instead |
| `smritikosh-ui not started: not built yet` | the dashboard was never built | `sarathi smritikosh`, then `sarathi up` |
| `smritikosh-ui not started: its build is older than the last commit to ui/` | a commit or pull changed Smritikosh's dashboard after it was built; `sarathi up` won't serve the old build, so the dashboard stops and the home page says it isn't running | `sarathi smritikosh` (or `npm run build` in Smritikosh's `ui/`), then `sarathi up` |
| `memory.via = "smritikosh" but it isn't set up yet` | sarathi.toml was edited by hand | `sarathi smritikosh` |
| `the cloud road turns memories into numbers with OpenAI, and there is no OPENAI_API_KEY` | a cloud model, and no OpenAI key for Smritikosh's meanings | paste one when asked, or `sarathi smritikosh --local` (Ollama's `nomic-embed-text`) |
| `Smritikosh already has an account 'NAME' and Sarathi doesn't know its password` | an account made by hand, without its key in Sarathi | run `sarathi smritikosh` in a terminal and type its password once |
| `memory: smritikosh, NOT ANSWERING` in `sarathi status` | Smritikosh's server is stopped | `sarathi up` |
| `memory.via is smritikosh, but the image has no Smritikosh` | containers' road, image built before `sarathi smritikosh` | `sarathi image`, then `sarathi up` |
| `ntfy not started: ntfy isn't installed here` | `[dvara] ntfy` on plain programs, with no ntfy | install it (<https://docs.ntfy.sh/install/>), or use the containers' road |
| The phone gets no notices | it can't reach your house's address, the firewall drops 8793, or the topic was typed wrong | home Wi-Fi; run the firewall line `sarathi up` prints; copy the topic from **Notices on this phone** |
| `door did not come up` or `page did not come up`, and its journal says `image platform (linux/arm64/v8) does not match` | the image was built for another machine (an older `sarathi image` after an arm64 build) | `sarathi image`, then `sarathi up` |

Each program also writes down what it printed:
`~/.local/share/sarathi/logs/page.log`, `clock.log` and `door.log` on
the process road; `journalctl --user -u sarathi-yantra` (or `-door`,
`-clock`) on the Podman road.

---

## Where your things are

| What | Where |
|---|---|
| Sarathi's settings | `~/.config/sarathi/sarathi.toml` |
| A cloud key, and Dvara's and bot's tokens | `~/.config/sarathi/secrets.env` (only you can read it) |
| Who may use the bot, and the helpers it offers | `~/dvara/actors.toml`, `~/dvara/agents/` |
| Their conversations, and their own sign-ins | `~/dvara/state/` |
| Your sign-ins | Setu's folder, `~/.local/state/setu/` |
| Your schedules and their history | Samay's folder, `~/.samay/` |
| What the helper remembers about you | `~/.local/state/yantra/`, or with Smritikosh on, its database (the `smritikosh-pgdata` volume) |
| Your Smritikosh key, for the helper | `~/.config/sarathi/secrets.env`, as `SMRITIKOSH_API_KEY` |
| Each person's Smritikosh key, for Dvara | `~/dvara/state/memory.json` (only you can read it) |
| Passwords of the Smritikosh accounts Sarathi made | `~/.local/share/sarathi/smritikosh-accounts.json` (only you) |
| Who in the house can sign in to the home page | `~/.local/share/sarathi/people.json` (only you; passwords kept as hashes) |
| What an agent noticed about someone, waiting for their `/remember` | `~/dvara/state/offered.json` (only you) |
| The key each person's ntfy topic is made from | `~/dvara/state/ntfy.key` (only you) |
| Which stopped sign-ins people were already told about | `~/dvara/state/signins.json` (only you) |
| What Sarathi started, and what each printed | `~/.local/share/sarathi/` |

Sarathi doesn't move anything: each program keeps its files where it
always has. To start over with Sarathi, delete its two folders; your
accounts, schedules and memories stay (the people in the house would
need inviting again).

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
  computer to talk to (8321 for the page, 8780 for Samay).
* **Container** — a program running in its own sealed box, which your
  computer can restart on its own. Podman is the program that runs them.
* **Bot** — a Telegram account that a program answers instead of a
  person. @BotFather makes one and gives you its token.
* **Actors file** — dvara's list of the people it answers, and what
  each may use.
* **Memory key** — a long password (`sk-smriti-…`) that opens one
  person's memories in Smritikosh, and nobody else's. Sarathi keeps them;
  you sign in to the dashboard with a username and password instead.
