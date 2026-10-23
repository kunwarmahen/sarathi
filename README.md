# sarathi — the one you install

[Yantra](https://github.com/kunwarmahen/yantra) is an agent you can name,
hand to someone, meter and gate. Around it sit projects that each do one
job and stand on their own:

| | What it does |
|---|---|
| **Yantra** (यन्त्र, "machine") | the agent itself |
| **Setu** (सेतु, "bridge") | your accounts — Gmail, Home Assistant, X — signed in once, the key never shown to the model |
| **Samay** (समय, "time") | work done later, on a schedule, with a record of every run |
| **Prahari** (प्रहरी, "the sentinel") | tells your agent when something happens — a price, a mail, a phone's notification — looking with no model |
| **Dvara** (द्वार, "door") | many people and many agents behind one always-on service, e.g. on Telegram |
| **Sparsh** (स्पर्श, "touch") | your phone, worked by the agent from a numbered list of what's on its screen, with a yes before Send |
| **Smritikosh** (स्मृतिकोश, "store of memories") | a memory store an agent can use instead of Yantra's own |

Each is useful alone. Together they are a helper that knows your
accounts, remembers you, keeps time, keeps watch and works your phone —
but only if you know seven names, seven installs, and how they find each
other. **Sarathi is the
part you install.** It finds the others, asks you once which model
should answer, and starts them together.

## The name

**sarathi** — सारथी (Sanskrit *sārathi*; said roughly *saa-ruh-thee*):
the charioteer, the one who drives. Krishna was Arjuna's. Sarathi drives
the machine for you.

## What Sarathi does not do

Sarathi has **no agent, tool, prompt or memory logic of its own**. It
holds only the wiring. If something wants to be written here, it belongs
in one of the projects above, where people who use that project alone
get it too. And it never becomes something those projects need: every
one of them works without Sarathi.

The one thing it keeps of its own is who may open its home page: your
key, and the sign-ins of the people in the house, each of them an id in
Dvara's actors file. Who they are, what they may use and what they may
spend stay Dvara's ([notes/14](notes/14-everyone-in-the-house.md)).

It also imports none of them. Each lives in its own environment, with
its own dependencies, so Sarathi runs each as a program and reads the
JSON it prints. Sarathi itself has no dependencies.
([notes/01](notes/01-five-names-one-answer.md))

## Setup

**New to all of this? Start with [the tutorial](TUTORIAL.md):** from
choosing a model to a helper that reads your mail and keeps a schedule,
in plain English.

```bash
git clone https://github.com/kunwarmahen/sarathi
cd sarathi
uv sync
.venv/bin/sarathi status      # which pieces are here
.venv/bin/sarathi init        # which model answers (asked once)
.venv/bin/sarathi up          # start them
```

Yantra needs its web extra for the page: `uv sync --extra web` in
Yantra's checkout.

## Using it

### Once: `sarathi init`

The one question that matters is which model answers: one on your own
machine, or a cloud one. Both roads are treated the same:

```
$ sarathi init
Which model should answer?
  1) one on this machine, through Ollama -- free, private, needs a GPU or patience
  2) Anthropic's, with an API key
  3) OpenAI's, with an API key
Choose 1, 2 or 3 [1]: 1
Pulled models that can talk:
  1) qwen3.8:latest
  2) gemma4:12b
  ...
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

On the local road, Ollama is asked which models are already pulled, so
the suggestion is one that answers today. Embedding models are never
offered. On a cloud road the key is typed at a hidden prompt and saved
to `secrets.env`, readable only by you. A key already in your
environment is used where it is and never copied.

The last question is where memories are kept. Enter keeps Yantra's own
file; **2** sets Smritikosh up there and then (`sarathi smritikosh`,
below), and leaves the file in place if it can't finish.

Every question has a flag, so a script can answer them all:
`sarathi init --provider ollama --model gemma4:12b --yantra-port 8400
--no-samay --memory local`.

The file it writes is short and meant to be edited:

```toml
[model]
provider = "ollama"
model = "qwen3.8:latest"

[yantra]
port = 8321

[samay]
on = true
port = 8780

[prahari]
on = true              # started when Prahari is on this computer; optional
port = 8782

[memory]
via = "local"          # or "smritikosh", once `sarathi smritikosh` set it up
```

A table or key Sarathi doesn't know (`[clok]`) stops `up` with its
name. Nothing is ignored quietly.

A model that holds more than Yantra's default 8192 tokens (a 64k Ollama
model, say) gets one more line under `[model]`:

```toml
context_window = 64000
```

Sarathi hands it to every piece as `OLLAMA_CONTEXT_WINDOW` (or the
cloud provider's own name). Without it, the model still answers, but
Yantra shortens a long chat much earlier than it needs to.

### Every day: `sarathi up` and `sarathi down`

```
$ sarathi up
samay      up at http://127.0.0.1:8780/#token=…  (pid 3324159)
prahari    up at http://127.0.0.1:8782/#token=…  (pid 3324161)
yantra     up at http://127.0.0.1:8321/  (pid 3324163)
setu       up at http://127.0.0.1:8775/#token=…  (pid 3324170)
sarathi    up at http://127.0.0.1:8760/#token=…  (pid 3324178)
```

Each line names the project it started. Open the `sarathi` one: it
links to all the others. With Dvara on, its line is the one without an
address to open, `dvara      up on 8770 (no page here; yours is
dvara-page, below)`, because Dvara's port answers Samay and its own
page, not a browser ([notes/09](notes/09-each-by-its-own-name.md)).

That starts **Samay's clock**, **Prahari's watch** (when Prahari is on
this computer) and **Yantra's page**, in that order, and then the pages
you look at: **Setu's page** (your
accounts), **Dvara's owner page** when Dvara is on, and **the home
page** that links them all. Bookmark the `sarathi` address. The page asks once, at start-up, whether Samay runs, so
Samay has to be there first. With `[memory] via = "smritikosh"`,
Smritikosh's database and server start before all of them
(`smritikosh  up at http://127.0.0.1:8080/`), since Yantra and Dvara
connect to it as they start, and its dashboard just after
(`smritikosh-ui up at http://127.0.0.1:3000/`). Setu isn't started: it runs only when
the agent uses an account. Both get the same model, so a scheduled run
is answered by the same model as the page. Each piece's output goes to
`~/.local/share/sarathi/logs/`.

Sarathi finds **Sparsh** the way it finds the others, a checkout beside
its own included, so it needs no link on your `PATH`; Yantra started on
its own does (Sparsh's README, "Letting an agent use it"). With Sparsh
found, the page is started with `--sparsh auto:<that sparsh>`: Yantra uses that program, but only once a phone is
attached and you say to use it (the phone panel's **use this phone**).
No phone at the start means no phone tools, the same as a Yantra you
start by hand ([notes/07](notes/07-the-phone-stays-on-the-cable.md)).

### Tell me when: Prahari

With [Prahari](https://github.com/kunwarmahen/prahari) beside the other
checkouts (or on your `PATH`), `up` starts it too, between the clock and
the page, and your agent can offer a watch: *"tell me when ALAB drops
under $50"*, *"tell me when a mail from the bank comes"*. Prahari looks
with no model, one tool call every so often, and the news comes to your
chat through Dvara like a schedule's answer. It's optional: without it,
nothing about it is started, and `[prahari] on = false` turns it off
when it is here.

**Samay or Prahari?** Samay does things *at a time* ("every morning at
8", "on Friday"); Prahari waits for something *to happen* ("when the
price drops", "as soon as the bank writes"). Ask your agent in plain
words, and it picks; the tutorial's Step 8 has a table.

**Mail the moment it lands**: add the mail account on Setu's page (its
**Mail (IMAP)** card, with an app password), then `prahari mailbox add
work-mail --account mail:work`. The password stays in Setu; Prahari keeps
the folder open and asks Setu for the login each time it connects.

What `up` wires for you:

* **Yantra's page** gets `--prahari`, so the agent there can offer
  watches, and Prahari's own page is on the home page under **Your pages**.
* **Prahari** gets the door's address, token and owner (`PRAHARI_DVARA_URL`,
  `PRAHARI_DVARA_TOKEN`, `PRAHARI_DVARA_ACTOR`), the same three Samay
  gets, so what a watch sees reaches you.
* **Dvara** gets `--prahari <it>`, so everyone in your house can ask
  for a watch in their chat, and each watch looks as its person, with
  their own accounts (Dvara's notes/56). `people = ["you", "asha"]` under
  `[prahari]` narrows that (`--prahari-for`).
* **The inlet.** Prahari's page shows an address and a key that can only
  knock: an Android phone's MacroDroid (a WhatsApp notification, say), a
  Home Assistant automation or a webhook sends there, and a watch that
  listens decides. With `[house]`, the inlet is on the house address too,
  and the firewall line names its port (8782). Each person has their own
  key, so their phone reaches only their watches
  ([notes/26](notes/26-the-watch-started-with-the-rest.md)).
* **The inlet from outside**, for Gmail's push or a webhook on the
  internet: `inlet_port = 8783` under `[prahari]` opens the inlet ALONE
  (no page, no API) on 127.0.0.1, Prahari's
  `deploy/public-inlet-tailscale.sh` gives it a public HTTPS name through
  Tailscale Funnel, and `public_url = "https://…:8443"` tells Prahari
  that name, so its page and your agent show it.

### Every page on your home network: `[house]`

Each piece listens on this computer alone unless you say otherwise. To
open them all from your phone or another computer at home, name this
computer in sarathi.toml (or under **Settings** on the home page):

```toml
[house]
name = "linux-al-ml-beast.local"   # what your other devices call it
address = "192.168.1.44"           # optional: what the name finds
```

`sarathi up` then publishes every page on that address too: Yantra's,
Samay's, Prahari's (with its inlet, where a phone app knocks), Dvara's,
Setu's and its sign-in windows, the home page, and
Smritikosh's dashboard (and ntfy, as before). What isn't a page stays on
this computer: Dvara's own port, Smritikosh's server and its databases,
which only the pieces talk to.
Every link the pieces hand out says the name: a person's `/accounts
page` link, a sign-in window, an invite, ntfy, Samay's address.
`<hostname>.local` works on most home networks (Avahi answers it), and so
does your router's name for the computer. On the plain-programs road the
pages listen on every address, and the firewall line below narrows
that. **Yantra's page then wants its token** (it runs a shell): Sarathi
keeps one in secrets.env (`YANTRA_WEB_TOKEN`), and the home page's
Yantra card carries it. Open the card once on each device, and that
device stays in. The home page's cards link by whatever name you opened
it at, so on your phone they say `linux-al-ml-beast.local` and here they
say `127.0.0.1`. With Dvara on, `[house]` also opens the sign-in window
on that address, and `/connect gmail` from Telegram streams Google's
page to your phone, so nothing has to be copied back. Yantra's page
gets a sign-in window of its own too (8792 on the Podman road, after
Dvara's 8790 and Setu's page's 8791): **connect** and **Another site?**
on its Connections panel, opened on your phone, show the sign-in there
instead of a command to type at the computer. `sarathi up` names every
port and the `ufw` line that opens them to your network
([notes/23](notes/23-every-server-by-one-name.md)).

### A memory by meaning: `sarathi smritikosh`

Yantra remembers you in a file of its own, which matches words: *"find
me flights"* never finds *"lives near RDU"*. Smritikosh finds it by
meaning. One command sets it up and switches to it:

```
$ sarathi smritikosh
checkout   ~/agent/smritikosh  (beside)
settings   wrote ~/agent/smritikosh/.env: ollama, nomic-embed-text, 768 dimensions
           (the tables are built for 768 now; another embedding model later means an empty database)
database   started smritikosh-postgres (docker.io/pgvector/pgvector:pg17, volume smritikosh-pgdata)
tables     30 step(s) run
dashboard  built; `sarathi up` starts it on 127.0.0.1:3000
server     started for these steps at http://127.0.0.1:8080 (able to make its first admin)
admin      made 'sarathi'; its password is in secrets.env
you        account 'asha' and its key (in secrets.env)
dvara      2 in the actors file: you as 'asha', 1 with an account of their own (priya new); keys in ~/dvara/state/memory.json
memory: smritikosh (in ~/.config/sarathi/sarathi.toml)
  what the built-in file holds stays there: type `/memory copy local` on Yantra's page once to bring it across
next: `sarathi up`
```

It does every step of Yantra's SMRITIKOSH.md, each skipped when already
done: Smritikosh's checkout (`SARATHI_SMRITIKOSH`, beside the others, or
cloned there), its programs, its `.env` (the local road with Ollama, or
the cloud road with OpenAI's embeddings, by `[model]`; `--local` for the
local one on a cloud model), a PostgreSQL container with pgvector (and,
with `--full`, Neo4j, MongoDB and Redis, below), its
tables, your account (named as Yantra knows you) with its own key, and
an account and key for each person in Dvara's actors file. Then
`sarathi up` starts Smritikosh before Yantra and Dvara and hands each the
way to reach it, on either road.

**A Smritikosh you already have is used, not replaced.** With its
database container already here, Sarathi looks for the checkout whose
`.env` opens it (beside the others, the folder above them, `~/src`,
`~/Documents`, home), so a setup made by hand is found without being
named. It never clones around an existing database or writes a new `.env`
for it: a new one would hold another password and another `JWT_SECRET`.
Its `.env` is read, and only a missing secret is added. Its database container is
started as it is. A key in secrets.env or in Yantra's `.env` is checked
and kept, so no new account is made.

**Each person's memories are their own.** A Smritikosh key opens only
its own account's memories. Yours reaches only what runs as you:
Yantra's page, and Samay for a schedule made at this computer, so a
morning check knows what the page knows. Dvara starts the
server for each person's turn with that person's key, so one person's
facts can't reach another's agent. A person added to the actors file
later gets an account the next time you run `sarathi smritikosh`. Dvara
gives memory only to an agent whose package asks for it (`[memory] via`
in its agent.toml).

**Going back is one command:** `sarathi smritikosh --off`, or the
**Memory** card on the home page. Nothing is deleted either way.

**Neo4j, MongoDB and Redis only with `--full`.** Yantra's remember,
recall, list and forget need PostgreSQL alone, and Smritikosh says
"degraded" without the others, which is fine. `sarathi smritikosh --full`
adds Neo4j (linked facts), MongoDB (its audit trail) and Redis (its job
queue) the way it adds the database: the container already serving the
address your `.env` names is used, found by its published port, and one
is made (on 127.0.0.1) only when none is. Your `.env` gains only the lines
it lacks. `up` starts them first on both roads; on Podman each becomes a
unit copied from its container, with the same image (by id, never a
`latest` tag), the same data and the same ports. `--no-full` leaves them
out again, and nothing is deleted.

**Smritikosh's own dashboard** (its `ui/`, a Next.js app) is built by
`sarathi smritikosh` (`npm install`, `next build`, again whenever its
`ui/` has a newer commit than the build) and started by `sarathi up`.
A build older than `ui/`'s last commit is not served: `sarathi up` stops
the dashboard and says `its build is older than the last commit to ui/`
until `sarathi smritikosh` builds it again. It is started
after Smritikosh, at **http://localhost:3000/dashboard/memories**, on this computer only (the home page
links there: the bare address can open blank in a browser).
On the Podman road it's a user service (`sarathi-smritikosh-ui.service`)
run with your machine's Node, so no Node goes into the image. The home
page's **Memory** card links to it. `[smritikosh] dashboard = false` stops
starting it, and `dashboard_port` moves it. It needs Node.js 20 or newer;
without npm, the setup says so and everything else still works.

**Signing in to the dashboard** takes a Smritikosh username and password,
never a key:

| Account | Its password |
|---|---|
| yours (named as Yantra knows you) | the one you chose, if you set Smritikosh up by hand; if Sarathi made it, in `~/.local/share/sarathi/smritikosh-accounts.json` |
| `dvara-<id>`, each person behind Dvara | `~/.local/share/sarathi/smritikosh-accounts.json` |
| `sarathi`, the admin Sarathi made (only if it had to) | `SMRITIKOSH_ADMIN_PASSWORD` in `~/.config/sarathi/secrets.env` |

**Where the keys are.** You put none anywhere: `sarathi smritikosh` does.

| Whose | Where | Used by |
|---|---|---|
| yours | `SMRITIKOSH_API_KEY` in `~/.config/sarathi/secrets.env` | Yantra |
| yours, on Telegram | `"owner"` in `~/dvara/state/memory.json` | Dvara |
| each person behind Dvara | `"<id>"` in `~/dvara/state/memory.json` | Dvara, for that person's turns only |

To give someone an account you made yourself in the dashboard, sign in
as them, make a key under **Settings → API keys** (shown once), and add
them to `memory.json` by hand, with `user` exactly that account's name:

```json
{"people": {"owner": {"user": "asha", "key": "sk-smriti-…"},
            "priya": {"user": "priya", "key": "sk-smriti-…"}}}
```

Always the person's own key, never an admin's: a key opens only its own
account's memories, which is what keeps one person's memories away from
another's agent. ([notes/13](notes/13-a-memory-by-meaning.md))

### Your phone: `sarathi phone`

```bash
sarathi phone                                  # a phone on a USB cable (process road)
sarathi phone tcpip                            # the phone on the cable listens over Wi-Fi;
                                               #   its address found and saved (any Android)
sarathi phone pair 192.168.1.23:37000 123456   # once: trust this computer over Wi-Fi
sarathi phone 192.168.1.23:41234               # then: reach it over Wi-Fi
sarathi phone iphone                           # an iPhone too: its WebDriverAgent
                                               #   at http://127.0.0.1:8100, started first
                                               #   when it isn't answering
sarathi phone --awake always                   # its screen while an agent works it
sarathi phone --off
```

turns on `[phone]`. Dvara's agents may then work the phone for the
one person marked `phone = true` in its actors file (or, with several
phones named, for each person their own `phones = [...]`; dvara's
`--sparsh`), through a package whose `[tools] allow` names
`mcp__sparsh__*` (it says when the agent on Telegram doesn't), and Yantra's page reconnects to a Wi-Fi phone by itself.
On the Podman road an Android on this computer's cable reaches the
containers too: `up` starts `sarathi-adb`, which lends this computer's
adb to them through a file in `~/.sparsh` (Sparsh's `adb-share`), not a
port ([notes/20](notes/20-whichever-phone-is-plugged-in.md)).
On your phone: *Developer options → Wireless debugging*, then *Pair
device with pairing code* for the first two numbers, and the address on
the Wireless debugging page itself for the third. A wrong address is
said, not saved. Android 10 and older have no such page: plug the phone
in and run `sarathi phone tcpip` ([notes/10](notes/10-a-real-phone.md)).

**An iPhone too.** Sparsh drives an iPhone through WebDriverAgent,
an app on the phone that Sparsh's own scripts build (on a Mac, once a
week with a free Apple ID) and start (`sparsh iphone`, with the iPhone
on this computer's cable; Sparsh's SETUP.md, Part C). `sarathi phone
iphone` starts it when it isn't answering (`sparsh iphone --background`:
tunnel, developer image, port 8100, no `sudo`), checks that it answers,
and saves `[phone] wda`, beside any Android. `sarathi up` starts a
saved one again, after an unplug, a restart or an iOS update. `sparsh
iphone --stop` stops it, and `down` leaves it running. **Whichever
phone is plugged in is the one used**: Sparsh asks the iPhone and the
Androids alike and takes the one that answers, so swapping the iPhone
for an Android on the cable, or back, needs no setting changed. While an
Android answers, `up` starts the iPhone's unit without waiting for it.
Two unnamed phones that answer at once are said, not guessed
([notes/20](notes/20-whichever-phone-is-plugged-in.md)); to use both,
name them (*Several phones, each someone's*, below). The containers
reach the iPhone at `host.containers.internal:8100`.
Keep the iPhone unlocked while an agent works it; `--awake` can't change
an iPhone's Auto-Lock. The same step is **Use the iPhone** on the
**Your phone** card ([notes/19](notes/19-an-iphone-too.md)).

**Several phones, each someone's.** Name each phone, and Dvara's
actors file says whose it is:

```bash
sarathi phone add nexus                 # the Android on this computer's cable
sarathi phone add pixel emulator-5554   # one adb sees, by its serial
sarathi phone add asha 192.168.1.160:5555   # one over Wi-Fi (or: add NAME tcpip)
sarathi phone add iphone iphone         # an iPhone, its WebDriverAgent
sarathi phone list                      # each one, and whether it answers
sarathi phone remove pixel
```

Each is a `[phone.NAME]` table with one of `serial`, `address` or
`wda` (and its own `awake`), handed to Sparsh as `SPARSH_PHONES`, an
iPhone at `host.containers.internal` inside the containers. In Dvara's
actors file `phones = ["nexus"]` gives a person theirs, and their agents
reach their phones and no others. The same is **Settings → Sarathi →
Your phones** (each phone, Remove, Add a phone) and a box per phone
under each person in **Settings → People** (those boxes appear once
phones have names; before, People has the single *work the phone* box).
A phone already written down without a name is named first (`sarathi
phone add iphone iphone http://127.0.0.1:8100`; it needn't be plugged
in, and `list` says *not answering* until its WebDriverAgent runs;
`list` asks Sparsh with the names, as Yantra and Dvara do), and
one phone under two names is refused
([notes/25](notes/25-several-phones.md)). Names take effect at the next
`sarathi down && sarathi up` (or **Apply**): the containers are handed
`SPARSH_PHONES` when they start, and a running one keeps what it
started with.

**After the phone restarts.** A phone switched off and on stops
listening over Wi-Fi, and its address can change, so Yantra's phone
panel lists it as *not answering over Wi-Fi* with what to do. Plug it in
and run `sarathi phone tcpip` again, or press **Turn on Wi-Fi from the
cable** in **Settings → Sarathi → Your phone** on the home page. It
finds the new address and saves it. A new address shows **Apply**
(`sarathi up`); the same address needs nothing more. The same card has
**Connect** for an address you type, and **Pair** for Android 11 and
later ([notes/17](notes/17-the-phone-from-the-page.md)). A fixed address
for the phone in your router saves the restart.

**Its screen while an agent works it.** A local model can think for
longer than the phone's screen timeout between steps, and a dark screen
locks. Sparsh keeps it on while an agent works and puts your own timeout
back after (`working`, the default). `--awake always` keeps it on for
good, for a phone set aside for the agent; `--awake off` leaves it
alone. It becomes `[phone] awake` in sarathi.toml and Sparsh's
`SPARSH_AWAKE` in the containers and the plain programs, since Yantra's
`.env` never reaches a container (Sparsh's note 09).

**In the containers**, the phone is reached over Wi-Fi only: a container
can't reach a USB cable without being handed every device on the bus.
The image has `adb` and Sparsh; the page and Dvara mount `~/.android`
(so the key this computer paired with is theirs, and nothing is paired
twice) and `~/.sparsh` (so your rules hold inside), and Sparsh
reconnects to `[phone] address` whenever it looks for phones. The home
page's **Your phone** card appears there once an address is set.
Rebuild the image (`sarathi image`) to get adb and Sparsh into it
([notes/08](notes/08-the-phone-over-wifi.md)).

A second `sarathi up` starts nothing new. A clock you already run some
other way (`samay unit`, a terminal) is left alone, because a second
clock would run every schedule twice. A port something else holds is
reported, not fought over. A piece that crashes on start is reported
with the last lines of its log, not as "started".

`sarathi down` stops what `up` started and nothing else.

That's the process road, plain programs. The same commands run
everything as containers instead, after `sarathi road podman` (below).

### For other people, and your phone: `sarathi dvara`

```bash
sarathi dvara                  # which agent a Telegram bot answers as; the bot's token
sarathi dvara --telegram greeter --telegram-id 8675309
sarathi dvara --ntfy           # notices on phones, through ntfy in the house (--no-ntfy)
sarathi dvara --off
```

turns on **dvara** as a third piece. `up` then starts clock, door, page,
in that order:

```
dvara  dvara --root ~/dvara/agents --actors ~/dvara/actors.toml --state ~/dvara/state
             --ask --provider <model.provider> --model <model.model> --samay <samay>
             [--prahari <prahari> [--prahari-for <prahari.people>]]
             serve --port <dvara.port> --web [--telegram <dvara.telegram>]
```

What a person would otherwise wire by hand in two places:

* **Samay and Dvara know each other.** Both get the same
  `SAMAY_DVARA_URL` (Dvara's address) and `SAMAY_DVARA_TOKEN` (Dvara's
  own token), so a schedule made in a chat is checked by Samay
  against the Dvara that made it. Samay also gets `SAMAY_DVARA_ACTOR`,
  your `[dvara] owner`: a schedule you make on Yantra's page still runs
  straight from Samay, but its answer reaches you through Dvara (on
  Telegram, and in the home page's chat), and so does any question it
  has: a write nobody allowed ahead of time is put to you there as a
  Yes/No (Dvara's `POST /ask`), waiting the schedule's wait, instead of
  being refused (Samay's notes/07).
* **A chat on the home page.** Dvara starts with `--web`, its web
  channel, and the home page shows it (below).
* **Tokens.** `DVARA_TOKEN` is made for you; `TELEGRAM_TOKEN` (from
  @BotFather) is typed at a hidden prompt. Both go to `secrets.env`, and
  from there **to Dvara alone**: the page never holds the bot's token,
  and Samay gets only Dvara's.
* **dvara's files, only when missing.** A starter `actors.toml` (you, as
  the owner) and dvara's own example agents. dvara's formats; Sarathi
  never touches them again, and ships no agent of its own.
* **The same model** as the page and Samay (`--provider`, `--model`).
* **Who may talk to it** is the actors file. Someone not in it gets
  silence, and `sarathi status` names their Telegram id, which is how
  you find your own:

  ```
    dvara      running on 8770 (no page here; yours is dvara-page, below)  (pid 3426486)
           messaged the bot but not in the actors file (telegram id): 8675309
  ```

**An MCP server of your own.** A server nobody wrote a Setu connector for
(a notes server at home, a docs server at work) is added on Setu's page,
under **Add your own server**: its address, and its token if it needs
one. Or in a terminal, once, on this computer: `setu connect --server
URL --id docs`, plus `--ask-token` for one that wants a key (Setu asks
for it, hidden). One with its own sign-in page (Linear, Notion) opens it
in a browser instead. The containers never need the token; Setu adds it
([TUTORIAL, Step 2](TUTORIAL.md#step-2--connect-an-account)). From then on every road has it: Yantra's page, the home page's chat
and Telegram. A person adds one to their own folder from their page, or
from the chat with `/connect server URL` when it needs no token (one
with its own sign-in page opens it in the streamed window)
([Dvara's notes/48](https://github.com/kunwarmahen/dvara/blob/main/notes/48-a-server-of-their-own.md)). On
the Podman road, Setu runs inside the containers, so a server on this
computer is `http://host.containers.internal:PORT/mcp`, not `127.0.0.1`.

It won't appear among an agent's boxes under *Tools it may use*. Those
are Yantra's own tools, Samay and the phone. A Setu account, your own
server included, reaches a Telegram agent through *Accounts it needs*
(**Settings → Agents → Change**): `"*:read"` already gives it every
account's reading tools, and a line like `docs:write` adds that server's
writing ones. Which tools count as reading is in Setu's file for the
server: `setu site file docs` shows it, and `--set` replaces it.

Adding accounts never needs a change to the agent for the model's sake.
Past twenty tools, each message is sent only the ones it points at, plus
a way to list the rest, so a local model's window doesn't overflow as
servers are added. *Tools sent each message* on the same form says so
(*Automatic*), or sends every tool every time.

**Amazon or X from someone's phone.** Those sites are signed in to in a
browser window on this computer. Give Dvara a window address and Setu
streams that window to their phone when they send `/connect amazon`
(dvara's note 22):

```bash
sarathi dvara --window-host 100.101.102.103      # your Tailscale address, say
sarathi dvara --window-host 127.0.0.1 --window-url https://door.example.net   # behind your HTTPS
```

They become `[dvara] window_host / window_port / window_url`, passed to dvara
as Setu's `SETU_WINDOW_*`. A home network address works for people at home
but is plain HTTP; Tailscale or your own HTTPS is the safe choice beyond it.
On the Podman road the window runs in Dvara's container: it listens
on a fixed port there (`window_port`, else 8790), published on
`window_host` alone, and the link says `window_url` or
`http://window_host:port`.

**Their own accounts page, from their phone.** When `window_host` is one
address (your Tailscale or home-network address, not `0.0.0.0`), Setu's
page listens there too, on its usual port, and Dvara builds people's
links with it: someone sends `/accounts page` and the link opens on
their phone. This computer still reaches the page at `127.0.0.1`. With
no `window_host`, or `0.0.0.0`, the page stays on this computer and the
link opens only here. Connecting Amazon or X from that page gets its own
streamed window on the same address, so it opens on their phone too. On
the Podman road that window is published on the port after Dvara's
(`window_port + 1`, else 8791). In its container even you, at this
computer, are "another device", so without a `window_host` it is
published on `127.0.0.1` for you alone. Behind a `window_url`, Setu's
page gets no window of its own: sign those sites in from the chat.

**A firewall is named, not opened.** These ports (8790, 8775, 8791 by
default, and the home page's 8760, where the people in the house sign
in) do nothing for a phone when ufw or firewalld drops them; the
page just keeps loading. When `window_host` is one address and either is
on, `sarathi up` ends with the ports and the command that opens them to
your network alone (`sudo ufw allow from 192.168.1.0/24 to any port
8760,8775,8790,8791 proto tcp`). It never runs it: that needs root and is
your call ([notes/11](notes/11-the-firewall-says-nothing.md)).

Your own phone can use the same sign-ins as this computer's page: under
`[actor.owner]`, `setu = "~/.local/state/setu"` with `setu_manage = true`,
so `/connect amazon` from the chat signs in there (dvara's note 27). The
image installs dvara with its browse extra, so an agent behind Dvara
can read Amazon or X when its package asks for them.

**Notices on a phone.** `sarathi dvara --ntfy` writes `[dvara] ntfy =
true` (and `ntfy_port`, 8793 by default), and `up` then starts ntfy, a
small push server, before Dvara, which gets `--ntfy <its address>` and
`DVARA_NTFY_CLICK`, the home page. Every notice for every person (a
schedule's answer, a sign-in that ran out, what a look back noticed) also
goes to their own topic there, for the ntfy app on their phone. Each
person finds their server and topic under **Notices on this phone** on
the home page. ntfy listens on `window_host` when that is one address,
so a phone at home reaches it, and otherwise on this computer alone. The
words never leave the house, so a phone hears them while it can reach
your house: home Wi-Fi, or Tailscale. On plain programs, install ntfy
first (<https://docs.ntfy.sh/install/>, or set `SARATHI_NTFY`); on the
Podman road it is its own container, `sarathi-ntfy`, from ntfy's own
image (`docker.io/binwiederhier/ntfy:v2.11.0`), with its port added to
the firewall line ([notes/15](notes/15-notices-on-a-phone.md)).

Dvara also checks every Setu folder's sign-ins once a day and tells the
person when one stopped working, and looks back over a conversation
nobody has written in for 30 minutes (dvara's note 39). `/new` doesn't
wait for its look back either: "Starting fresh" comes at once, and what
the look noticed comes after as one of these notices (dvara's note 51).
Nothing to set: it comes with Dvara.

A door that can't start (no actors file, a bot with no token) says why,
and Samay and Yantra start anyway. On the Podman road it's a third
unit, `sarathi-dvara`, on a network shared with the others
(`sarathi.network`), where Samay reaches it as `sarathi-dvara`.
Each unit reads its own secrets from `~/.config/sarathi/units/<unit>.env`,
copied from `secrets.env` by `up`. The image includes dvara when its
checkout sits beside the others.

### Two ways to run it: plain programs, or containers

Everything above runs the same two ways, and you can switch whenever you
like. **The process road** (the default) starts plain programs from your
session, using what's on your computer. **The Podman road** runs them in
containers that systemd keeps running.

```bash
sarathi road                   # which one you're on
sarathi road podman            # containers (then `sarathi image` once, and `sarathi up`)
sarathi road process           # plain programs again (then `sarathi up`)
```

Switching stops what the other road started, and on leaving Podman it
removes the units, since both roads use the same ports and the units
would otherwise start again at your next login. It starts nothing new;
`sarathi up` does that.

| | process road | Podman road |
|---|---|---|
| how it starts | `sarathi up`, from your session | systemd units, also at every login |
| after a crash, a reboot, logging out | gone until the next `sarathi up` | started again on its own |
| what it needs | the checkouts (or installs) of each piece | Podman, and `sarathi image` (~1.3 GB) |
| after `git pull` in a checkout | nothing: it runs the checkout | `sarathi image` again, then `sarathi up` |
| Amazon and X | your own Chrome | Chrome in the image |
| connectors walled off | your bubblewrap (`sudo apt install bubblewrap`) | bubblewrap in the image |
| voice notes heard | your ffmpeg (`sudo apt install ffmpeg`) and an Ollama model listing "audio" | ffmpeg in the image; the model in your Ollama |
| Dvara's streamed window | listens on `window_host` itself | published from Dvara's container |
| Setu's page's streamed window | on `window_host`, any free port | published from Setu's container on the next port (8791) |
| Yantra's page's streamed window | with `[house]`, on the house address, any free port | published from Yantra's container on the port after that (8792): on the house address with `[house]`, else on `127.0.0.1` for you (in its container even your own browser is "another device") |
| Setu's page for people's phones | `setu serve --also-host <window_host>` | published on `window_host` too; only the people's folders mounted |
| the pages | plain programs | Setu's and Dvara's as containers; the home page, and Smritikosh's dashboard when it's on, as user services (`~/.config/systemd/user/sarathi-home.service`, `sarathi-smritikosh-ui.service`) |
| a cloud key | from `secrets.env`, or your shell | from `secrets.env` only |
| Ollama | as it is | must listen beyond 127.0.0.1 (`OLLAMA_HOST=0.0.0.0`) |
| Yantra's own `.env` | read, as in a terminal | not in the image: model settings come from `[model]` in sarathi.toml only |
| Smritikosh (`[memory] via = "smritikosh"`) | its database container, then its server in its checkout | two units on the same database volume (`sarathi-smritikosh-db`, `sarathi-smritikosh`); Smritikosh in the image; with `--full`, a unit each for Neo4j, MongoDB and Redis, copied from their containers; its dashboard a user service with your Node |

Your accounts, schedules and memories are the same files either way, so
switching loses nothing. A port something else already uses stops that
piece on either road, with the setting that moves it.

#### On the Podman road

```bash
sarathi road podman            # or  sarathi init --podman
sarathi image                  # build the image (a few minutes, once per update; ~1.3 GB)
sarathi up
```

On this road `up` writes Quadlet units (`sarathi-samay`, `sarathi-yantra`,
and `sarathi-dvara` when Dvara is on) into
`~/.config/containers/systemd/`, and systemd starts them. When
`sarathi.toml` changes a unit, or `sarathi image` built a newer image,
`up` restarts what's affected and leaves the rest running. They come back on their own after a crash, and they start again
when you log in. `sarathi down` stops them (each under podman's small init,
so a page that doesn't catch SIGTERM still stops at once and its unit
reads stopped, not failed; [notes/03](notes/03-two-containers-one-clock.md));
`sarathi down --remove` also
takes the units out, so nothing starts at login.

What goes into the containers:

* **One image holding Yantra, Setu and Samay** (and Dvara, Sparsh and
  Prahari when their checkouts are beside Sarathi's). They call each
  other as programs, so each container needs all of them. `sarathi image` builds
  it from the **committed** code of the checkouts beside Sarathi, and
  names any uncommitted changes it left out.
* **A browser, and the wall around a connector.** Google Chrome at
  `/usr/bin/google-chrome`, where a desktop has it, so the Amazon and X
  profiles Setu already recorded open with the browser that wrote them;
  Xvfb for a site that wants a real window; bubblewrap, so Setu's
  connectors are walled off here as on your desktop; and ffmpeg, so a
  voice note can be heard. Chrome refuses a
  profile a newer Chrome wrote, so `up` says when your computer's Chrome
  has got ahead of the image's (`sarathi image` catches up: it tells the
  build which Chrome is here, so that step isn't taken from the cache;
  [notes/05](notes/05-a-browser-in-the-image.md)). Google ships
  Chrome for amd64 only; elsewhere the image gets Debian's Chromium.
* **Your data, at the same paths.** Samay's schedules, Prahari's
  watches, Setu's sign-ins and Yantra's memory are mounted from where they are on your machine,
  at the same paths, and the containers run as you. Nothing is copied,
  and the process road and the Podman road see the same things.
* **Smritikosh, when your memories are kept there.** Its database runs
  the pgvector image on the same volume as on the plain road (`up` stops
  the plain container first: two servers on one data folder would ruin
  it), and its server runs from Sarathi's image, which carries Smritikosh
  once `sarathi smritikosh` has recorded its checkout. Run `sarathi image`
  after `sarathi smritikosh`. Neither mounts anything of the others'.
  With `--full`, Neo4j, MongoDB and Redis are a unit each
  (`sarathi-smritikosh-neo4j`, `-mongodb`, `-redis`), copied from the
  container that holds their data, which `up` stops first.
* **Ollama stays on your machine.** The containers reach it at
  `host.containers.internal`, so Ollama has to listen on more than
  127.0.0.1 (`OLLAMA_HOST=0.0.0.0`).
* **A home folder Chrome can write to.** Inside a container your home's
  path would be a folder Podman made only to hold the mounts, owned by
  root, and Chrome dies at start there. So it's a scratch folder of
  yours, emptied at each start, with your data folders mounted inside it.
* **Google's client file, alone and read-only.** Setu keeps only the
  path of the file a Gmail sign-in uses, and it usually sits on your
  Desktop or in Downloads. That one file is mounted at the same path;
  the folder around it isn't.
* **A cloud key only from `secrets.env`.** A systemd unit can't see the
  shell you ran `sarathi up` from, so on this road a key there wouldn't
  arrive. `up` refuses to start rather than start without it. The unit
  files themselves hold no key.

Everything works on both roads: Gmail and Home Assistant through their
APIs, Amazon and X through your own Chrome or the one in the image
([notes/05](notes/05-a-browser-in-the-image.md)).

### Any time: `sarathi status`

```
$ sarathi status
yantra      ~/agent/yantra/.venv/bin/yantra  (beside)
            the machine: the agent itself
            yantra 0.1.0; would ask ollama for qwen3.8:latest
setu        ~/.local/bin/setu  (path)
            the bridge: your accounts, signed in once
            2 accounts connected: gmail:mine, homeassistant:home
samay       ~/agent/samay/.venv/bin/samay  (beside)
            work done later, with receipts
            not running (start it: samay serve); schedules: 0 active, 0 paused
prahari     ~/agent/prahari/.venv/bin/prahari  (beside)
            the watch: tells your agent when something happens
            watching at http://127.0.0.1:8782/; watches: 2 active (1 at the inlet), 0 paused
dvara       ~/agent/dvara/.venv/bin/dvara  (beside)
            many people and agents behind one service
            door serving at http://127.0.0.1:8770 (dvara serve); 3 agents, 2 people
sparsh      ~/agent/sparsh/.venv/bin/sparsh  (beside)
            the hands: your phone, worked by number, with a yes before Send
            phone emulator-5554 (sdk_gphone64_x86_64) ready
smritikosh  ~/agent/smritikosh/.venv/bin/smritikosh-mcp  (sarathi.toml)
            a memory store (Yantra keeps its own without it)

memory: smritikosh at http://127.0.0.1:8080 -- postgres ok; degraded; 12 remembered for asha
  its dashboard: http://localhost:3000/dashboard/memories
```

Each line says **where** a piece was found and **which rule** found it.
The line under it is that piece's own account of itself: Yantra's
release and the model it would ask (asked with the model, Setu and
Samay `up` gives it, so a model Ollama hasn't pulled shows here with
the `ollama pull` that fixes it, and so does a sibling it can't find), Setu's connections (and any sign-in the site refused, with `setu connect …` to fix it), Samay's clock, the phones Sparsh can reach (with phones named, each
one *connected* or *not connected* and why, and a phone attached under
none of the names said to be out of the agents' reach; the home page's
phone card says the same), and
whether Dvara is serving (asked about the folders `[dvara]` names;
with Dvara off, dvara isn't asked). Sarathi repeats it and adds
nothing. Smritikosh has no status command, so its line is "found,
here", and the last line says where your memories are kept: Yantra's
own file, or Smritikosh with what its `/health` says and how many
memories are yours.

After `sarathi up`, `status` also lists what it started, and whether
each one is still running. If one has exited, it shows the end of its
log.

`sarathi status --json` prints the same as `sarathi.status.v1`, with each
sibling's own status object inside. The exit status is 0 when Yantra,
Setu and Samay are all found and readable, and 1 otherwise. Dvara,
Sparsh and Smritikosh are optional: a missing one is reported and never fails the
check.

### Every page in one place: `sarathi home`

```
$ sarathi home
your home page:
  http://127.0.0.1:8760/#token=…
```

When `sarathi up` has already started it, `sarathi home` just prints
its links, with the one for your other devices under `[house]`:

```
$ sarathi home
your home page is already running:
  http://127.0.0.1:8760/#token=…
on your other devices:
  http://linux-al-ml-beast.local:8760/#token=…
```

One page for all of it, in three views. With Dvara on, it opens on the
chat (below), which fills the window. Two icons at the top right open
the rest: **Your pages** (four squares) and **Settings** (a gear). Each
view has its own address (`#pages`, `#settings`), so a reload stays put,
and **← Back to the chat** or Escape goes back
([notes/22](notes/22-the-chat-is-the-page.md)). With Dvara off there is
no chat, and the page opens on Your pages.

**Your pages** links to each program's own page: Yantra's, Samay's,
Prahari's (when it's here), Setu's (`setu serve`) and, with Dvara on,
Dvara's (`dvara page`).
With Sparsh found (on the Podman road, once `[phone] address` or `wda` is set), a **Your phone** card
opens Yantra's page, where the phone panel shows the phone and what the
agent did on it; Sparsh has no page of its own. Each
card says whether that page is running, shows the program's own status
line (the one `sarathi status` prints), and has an **Open** link that
opens the page already signed in. A page that isn't running shows the
command that starts it.

`sarathi up` starts it, with Setu's page and (with Dvara on) Dvara's,
unless `[pages] on = false` in sarathi.toml. With Dvara on, Setu's page
also knows where each person's own folder is (`--people`), for the
one-time link `/accounts page` sends them, and Dvara's page reads each
person's schedules from the Samay Sarathi found. A person's link opens
only on an address their phone can reach: with `[dvara] window_host` set
to one address, Setu's page listens there too and the links use it
(above); without it, they work only here. `sarathi home` runs it by
hand. `[pages]` also holds their ports (`sarathi_port`, `setu_port`,
`dvara_port`), and `[dvara] owner` names your id in the actors file, which
Dvara's page shows and answers for. Dvara's page gets Dvara's token and
address from `up`, so your answers on it reach Dvara. No other page
gets that token.

The **Memory** card says where your memories are kept and, for
Smritikosh, whether it answers, with **Open Smritikosh's dashboard** when
the dashboard is running (or what starts it when it isn't). Once Smritikosh is set up, its button
switches between it and Yantra's own file: it writes `[memory] via` and
runs `sarathi up`, which starts Yantra and Dvara again with it.

Apart from that switch and Settings (below), it links, and nothing on it starts, stops or changes anything. Because
its links carry the other pages' keys, it has a key of its own (after the
`#`, kept in `~/.local/share/sarathi/home.token`, or
`$SARATHI_HOME_TOKEN`). It listens on this computer, and on `[dvara]
window_host` when that is one address, for the people in the house
(below). ([notes/06](notes/06-one-bookmark.md))

**Talk to your agents.** With Dvara on, the page opens on a chat: pick an agent, write, and the answer comes back a few seconds
later. What a schedule sends you waits there too, even with no Telegram.
A question an agent asks shows as a card with **Yes** and **No** (and
goes to Telegram as well; the first answer counts). The chat holds no
logic: every word goes to Dvara's web channel and back, as you, the
`[dvara] owner`, with the same rules and allowance as on Telegram.
Dvara's token stays in the home page's process, never in the browser.
The chat is its own conversation: one on Telegram doesn't continue
there. ([notes/12](notes/12-a-chat-on-the-home-page.md))

It shows the work as it happens, as Yantra's page does: each step as a
line under the agent's name, then the answer as it is written, drawn as
formatted text. After a job of several steps it may offer to keep how
it was done, with **Keep** and **Not now**, saved for you alone. A row
of buttons sends **Skills**, **Learn this**, **Tools**, **Schedules**, **Memory**, **Phone** (its
screen and last steps, for the phone's person),
**New chat** to Dvara as the words they are, **History** opens every
conversation the person has had, searched by its words, read again,
carried on, shared (Save as PDF, Download, or the phone's Send…) or
deleted for good (Dvara's
[notes/50](https://github.com/kunwarmahen/dvara/blob/main/notes/50-every-conversation-kept.md);
[notes/21](notes/21-history.md)). On a phone the chat takes the whole screen too. A job can also be taught one step at a time:
**Teach** in the row of words, or `/learn start <what it's for>` and each step (the agent does only what
you say), or `/learn watch` and do each step on your phone yourself,
saying `next`; while it's open a bar shows how far it got, with
**Done** (keeps it as one skill) and **Stop** (`/learn clear` does the
same) (Dvara's
[notes/49](https://github.com/kunwarmahen/dvara/blob/main/notes/49-a-job-taught-step-by-step.md);
[notes/24](notes/24-teach-from-the-chat.md)). 🎤 records a voice note (on this computer, or a
page served over https), heard into words by a local model that can
hear, and shown back as *I heard: "…"*. The paperclip beside **Send** adds pictures or
files to your next message (up to 20 MB together): Dvara keeps them in
your folder with that agent, and shows a picture to a model that can
see. When an answer tells you to send `/connect gmail`, it's a button
under the answer. ([notes/18](notes/18-a-chat-that-shows-its-work.md))

**Everyone in the house.** The other people in Dvara's actors file can
sign in to the same page and get their own chat, as themselves:

```
$ sarathi invite priya
priya's link, for one device, within 48 hours:
  http://192.168.1.44:8760/#invite=priya.…
```

They open the link (once, within two days), choose a password, and from
then on sign in with their name and that password. They see their chat
and nothing else: no cards, no keys, no memory switch. Each turn is
theirs in Dvara, with their own allowance, rules, folder, memories and
sign-ins. Dvara's page shows you who used which agent and what it cost,
never their words. **People in the house**, under the gear below the
Settings tabs, lists
everyone in the actors file with **Invite** (the link to send) and
**Sign out everywhere**. `sarathi people` lists them in a terminal;
`--sign-out NAME` ends their devices, `--remove NAME` their sign-in. A
new link for someone already signed up resets their password. The link
opens on a phone when `[dvara] window_host` is one address (your home
network, or Tailscale), the same address Setu's page uses; without it,
on this computer only, and it says so. Signed in, they also get **My
accounts**, which opens their own Setu page by the same one-time link
`/accounts page` sends in the chat, and **Notices on this phone** when
the house runs ntfy (above). Passwords are kept as scrypt,
links and sessions only as hashes, in `~/.local/share/sarathi/people.json`.
([notes/14](notes/14-everyone-in-the-house.md))

**Every setting, on the page.** Behind the gear, **Settings** changes
every file you'd otherwise edit by hand, in six tabs: **People** (Dvara's
actors file: who, which agents, accounts, allowance, Telegram ids, and
anyone who messaged the bot unlisted), **Agents** (each agent's model,
memory, tools as checkboxes in plain words, each marked *asks you first*
or *runs unasked*, accounts, budget and instructions; add from an
example; the skills its people kept, and **Make it a tool** for one with
a script; a long list of boxes or skills gets a box above it that keeps
only what matches what you type, and a ticked tool stays ticked while
hidden),
**Rules** (Dvara's standing answers), **Accounts** (Setu's settings,
each added site's rules, and which tools of each MCP server of your own
only read), **Sarathi** (this file: the model, Dvara and
its bot, the house address, ntfy, road, ports, and your phone, with
buttons that reach it from this computer's USB cable) and **Keys**
(typed in, never shown back). Each program checks a change the way it
reads its file at start-up, and refuses one it couldn't load in its own
words; the file before is kept as `.bak`. People, agents and rules take
effect from the next message; Sarathi's settings and keys show
**Apply**, which runs `sarathi up`. Every tab has **Edit as text** for the
whole file. You're in People too, and **My accounts** at the top opens
your own Setu page. Only your page has Settings; people signed in get
none of it ([notes/16](notes/16-every-setting-from-the-page.md)).

### Where it looks

In this order; the first hit wins:

| Rule | Where |
|---|---|
| `env` | a path you set: `SARATHI_YANTRA`, `SARATHI_SETU`, `SARATHI_SAMAY`, `SARATHI_PRAHARI`, `SARATHI_DVARA`, `SARATHI_SPARSH`, `SARATHI_SMRITIKOSH` |
| `path` | what your shell would run |
| `sarathi.toml` | Smritikosh, where `sarathi smritikosh` set it up (`[smritikosh] checkout`) |
| its database | Smritikosh only, while `sarathi smritikosh` sets it up: with its database container already here, the checkout whose `.env` holds that container's user and password (beside, the folder above, `~/src`, `~/Documents`, home). Nothing is cloned around an existing database |
| `beside` | `<dir>/<name>/.venv/bin/<program>`, for checkouts kept side by side. `<dir>` is `SARATHI_SIBLINGS`, or the folder this checkout of Sarathi sits in |

### Where its files live

| | |
|---|---|
| `~/.config/sarathi/sarathi.toml` | the settings (`$SARATHI_CONFIG` for another folder) |
| `~/.config/sarathi/secrets.env` | a cloud key, if you typed one, Dvara's two tokens, and Smritikosh's key and admin password; readable only by you |
| `~/.config/sarathi/units/` | the Podman road: each unit's own share of secrets.env, copied by `up`, and Smritikosh's settings as its container reads them (with `--full`, each store's settings from the container it was copied from); yours alone |
| `~/.config/containers/systemd/sarathi-*` | the Podman road's units and network, written by `up` (edit `sarathi.toml`, not these) |
| `~/.config/systemd/user/sarathi-home.service` | the Podman road's home page, a plain user service (written by `up` too) |
| `~/.config/systemd/user/sarathi-smritikosh-ui.service` | the Podman road's Smritikosh dashboard, run with your Node (written by `up`, with Smritikosh on) |
| `~/dvara/` | Dvara's own files: `actors.toml`, `agents/`, `state/` (dvara's defaults; `[dvara]` can name others) |
| `~/dvara/state/memory.json` | with Smritikosh on: each person's name and key there, for Dvara; yours alone |
| `<smritikosh>/ui/.env.local` | the dashboard's own sign-in secret, written by `sarathi smritikosh` only when there is none |
| `~/.local/share/sarathi/` | `smritikosh-accounts.json` the passwords of the Smritikosh accounts Sarathi made, and `mcp/` how Yantra, Samay's runs and Dvara start `smritikosh-mcp` (no key in it); `home.token` the home page's key (yours alone), `people.json` the people in the house's sign-ins (hashes only; yours alone), `work/` where the page starts, `run/` what `up` started, `logs/` what each printed (`$SARATHI_STATE`); `run/` and `logs/` are yours alone, since Samay's page token appears in them |

Each sibling keeps its own data where it always has. Samay's schedules
are still in `~/.samay`, Prahari's watches in `~/.prahari`, and Setu's sign-ins are still where Setu put
them. Sarathi starts the pieces; it doesn't move their files.

## The source

```
src/sarathi/
  siblings.py   which pieces exist, where each is found, and what its
                status --json says, read by format  (notes/01); Sparsh,
                the phone  (notes/07)
  config.py     sarathi.toml and secrets.env: read, checked, written  (notes/02);
                each table by its project's name, old names still read  (notes/09);
                [house], every page on the home network, links by its
                name; Yantra's page's token, made once  (notes/23)
  first_run.py  sarathi init: which model answers, asked once  (notes/02)
  services.py   sarathi up / down: start Samay and the page, know
                which are ours  (notes/02); and the pages  (notes/06);
                each line by its project's name  (notes/09); ntfy before
                Dvara, for notices on phones  (notes/15); Prahari beside
                the clock, wired to the door, the owner's alone  (notes/26)
  podman.py     the same on the podman road: the image, the Quadlet
                units, systemd  (notes/03); Dvara's unit  (notes/04);
                its streamed window, and the image's browser  (notes/05);
                the firewall named when phones are to reach it  (notes/11);
                ntfy's own container  (notes/15); sarathi-adb, this
                computer's adb lent to the containers by a file  (notes/20);
                a second PublishPort on the house address for every
                page, and the firewall line naming them  (notes/23)
  door.py       sarathi dvara: dvara turned on, its tokens, starter files,
                and who messaged unlisted  (notes/04)
  phone.py      sarathi phone: [phone] on, paired and reached over Wi-Fi
                through the Sparsh found  (notes/08); its screen while an
                agent works it, --awake  (notes/10); `tcpip`, Wi-Fi turned
                on from the cable and the address saved  (notes/17); an
                iPhone's WebDriverAgent, `iphone`, beside the Android, the
                plugged-in one used  (notes/19, notes/20); several by name,
                `add`, `remove`, `list`  (notes/25)
  home.py       sarathi home: one page linking every program's page, each
                with its status and its key; static/ is that page  (notes/06);
                the phone's card, which opens Yantra's page  (notes/07); the
                chat, passed through to Dvara's web channel as you  (notes/12),
                showing each step and the answer as it comes, md.js for
                the answers, skills to keep  (notes/18),
                or as the person signed in  (notes/14); My accounts and
                Notices on this phone, for each person  (notes/15);
                Settings, routes owner-only  (notes/16); the chat as
                the page, Your pages and Settings behind icons  (notes/22);
                each card linked by the name the page was opened at, and
                Yantra's with its token  (notes/23)
  editing.py    every settings file from the page: each program checks
                and writes its own (dvara settings, setu config / site
                file), sarathi.toml and secrets.env here  (notes/16);
                the phone card's steps, Sparsh's own, run here  (notes/17)
  people.py     the people in the house signing in to the home page: an
                invite that works once, a password, a session per device,
                each one an id in Dvara's actors file  (notes/14)
  smritikosh.py sarathi smritikosh: Smritikosh set up and switched to, an
                account and key for you and for each person behind Dvara;
                --full, Neo4j, MongoDB, Redis; its dashboard built and
                started; its line in status, its card on the home page  (notes/13)
  Containerfile one image, every program, a browser and bubblewrap  (notes/05)
  cli.py        sarathi init | dvara | phone | smritikosh | road | image | up | down |
                status [--json] | home | invite | people
tests/
  test_status.py  test_config.py  test_up.py  test_podman.py  test_door.py  test_home.py
  test_pages_up.py  test_phone.py  test_phones_named.py  test_names.py  test_smritikosh.py  test_people.py
  test_house.py  test_prahari.py
```

## Status

Finding the pieces, the settings, starting them as plain processes or
as Podman containers, and the household road (dvara on Telegram, wired
to Samay) are all built, with a browser and bubblewrap inside the
containers. `sarathi up` also starts Setu's page, Dvara's owner page and
the home page that links every program's page, with a chat to your
agents through Dvara where a schedule's answers wait for you, and a
sign-in for each person in the house to a chat of their own
([notes/14](notes/14-everyone-in-the-house.md); run as plain programs). Sparsh is found, its
phones are said, and Yantra's page and Dvara are handed it; inside
the containers the phone is reached over Wi-Fi (`sarathi phone`), tried
against the emulator and a real Nexus 6P on Android 8.1, a schedule's
locked phone asked about on Telegram and worked once unlocked
([notes/10](notes/10-a-real-phone.md)). An iPhone is given out the same
way, through its WebDriverAgent, and read from inside a container on a
real iPhone 17, where a task asked of Yantra and the same from Telegram
through Dvara both worked ([notes/19](notes/19-an-iphone-too.md)). Smritikosh is set up by one
command and switched on and off from it or the home page, with an
account of its own for each person behind Dvara, Neo4j, MongoDB and Redis
with `--full`, and its own dashboard built and started beside it; run on
plain programs, written and tested for Podman
([notes/13](notes/13-a-memory-by-meaning.md)). With `[dvara] ntfy`, notices
reach phones through ntfy in the house, and each person opens their own
Setu page from the home page ([notes/15](notes/15-notices-on-a-phone.md));
ntfy's own image was run, and the rest is written and tested, not yet
run on Sarathi's roads. Every settings file is changed from the home page,
each checked by its own program ([notes/16](notes/16-every-setting-from-the-page.md)),
and the phone is reached again from the page after it restarts, run on
a real Nexus 6P ([notes/17](notes/17-the-phone-from-the-page.md)).

## Tests

```bash
uv run pytest -q
```

## License

Apache-2.0
