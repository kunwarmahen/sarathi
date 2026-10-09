# sarathi — the one you install

[Yantra](https://github.com/kunwarmahen/yantra) is an agent you can name,
hand to someone, meter and gate. Around it sit projects that each do one
job and stand on their own:

| | What it does |
|---|---|
| **Yantra** (यन्त्र, "machine") | the agent itself |
| **Setu** (सेतु, "bridge") | your accounts — Gmail, Home Assistant, X — signed in once, the key never shown to the model |
| **Samay** (समय, "time") | work done later, on a schedule, with a record of every run |
| **Dvara** (द्वार, "door") | many people and many agents behind one always-on service, e.g. on Telegram |
| **Sparsh** (स्पर्श, "touch") | your phone, worked by the agent from a numbered list of what's on its screen, with a yes before Send |
| **Smritikosh** (स्मृतिकोश, "store of memories") | a memory store an agent can use instead of Yantra's own |

Each is useful alone. Together they are a helper that knows your
accounts, remembers you, keeps time and works your phone — but only if
you know six names, six installs, and how they find each other. **Sarathi is the
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
wrote ~/.config/sarathi/sarathi.toml
  answering: ollama, qwen3.8:latest
next: `sarathi up`
```

On the local road, Ollama is asked which models are already pulled, so
the suggestion is one that answers today. Embedding models are never
offered. On a cloud road the key is typed at a hidden prompt and saved
to `secrets.env`, readable only by you. A key already in your
environment is used where it is and never copied.

Every question has a flag, so a script can answer them all:
`sarathi init --provider ollama --model gemma4:12b --yantra-port 8400
--no-samay`.

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
yantra     up at http://127.0.0.1:8321/  (pid 3324163)
setu       up at http://127.0.0.1:8775/#token=…  (pid 3324170)
sarathi    up at http://127.0.0.1:8760/#token=…  (pid 3324178)
```

Each line names the project it started. Open the `sarathi` one: it
links to all the others. With Dvara on, its line is the one without an
address to open, `dvara      up on 8770 (no page here; yours is
dvara-page, below)`, because Dvara's port answers Samay and its own
page, not a browser ([notes/09](notes/09-each-by-its-own-name.md)).

That starts **Samay's clock** and **Yantra's page**, in
that order, and then the pages you look at: **Setu's page** (your
accounts), **Dvara's owner page** when Dvara is on, and **the home
page** that links them all. Bookmark the `sarathi` address. The page asks once, at start-up, whether Samay runs, so
Samay has to be there first. Setu isn't started: it runs only when
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

### Your phone: `sarathi phone`

```bash
sarathi phone                                  # a phone on a USB cable (process road)
sarathi phone pair 192.168.1.23:37000 123456   # once: trust this computer over Wi-Fi
sarathi phone 192.168.1.23:41234               # then: reach it over Wi-Fi
sarathi phone --off
```

turns on `[phone]`. Dvara's agents may then work the phone for the
one person marked `phone = true` in its actors file (dvara's
`--sparsh`), through a package whose `[tools] allow` names
`mcp__sparsh__*` (it says when the agent on Telegram doesn't), and Yantra's page reconnects to a Wi-Fi phone by itself.
On your phone: *Developer options → Wireless debugging*, then *Pair
device with pairing code* for the first two numbers, and the address on
the Wireless debugging page itself for the third. A wrong address is
said, not saved. Android 10 and older have no such page: plug the phone
in once, run `adb tcpip 5555`, and give `sarathi phone` its Wi-Fi
address with `:5555` ([notes/10](notes/10-a-real-phone.md)).

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
sarathi dvara --off
```

turns on **dvara** as a third piece. `up` then starts clock, door, page,
in that order:

```
dvara  dvara --root ~/dvara/agents --actors ~/dvara/actors.toml --state ~/dvara/state
             --ask --provider <model.provider> --model <model.model> --samay <samay>
             serve --port <dvara.port> [--telegram <dvara.telegram>]
```

What a person would otherwise wire by hand in two places:

* **Samay and Dvara know each other.** Both get the same
  `SAMAY_DVARA_URL` (Dvara's address) and `SAMAY_DVARA_TOKEN` (Dvara's
  own token), so a schedule made in a chat is checked by Samay
  against the Dvara that made it.
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
default) do nothing for a phone when ufw or firewalld drops them; the
page just keeps loading. When `window_host` is one address and either is
on, `sarathi up` ends with the ports and the command that opens them to
your network alone (`sudo ufw allow from 192.168.1.0/24 to any port
8775,8790,8791 proto tcp`). It never runs it: that needs root and is
your call ([notes/11](notes/11-the-firewall-says-nothing.md)).

Your own phone can use the same sign-ins as this computer's page: under
`[actor.owner]`, `setu = "~/.local/state/setu"` with `setu_manage = true`,
so `/connect amazon` from the chat signs in there (dvara's note 27). The
image installs dvara with its browse extra, so an agent behind Dvara
can read Amazon or X when its package asks for them.

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
| Dvara's streamed window | listens on `window_host` itself | published from Dvara's container |
| Setu's page's streamed window | on `window_host`, any free port | published from Setu's container on the next port (8791) |
| Setu's page for people's phones | `setu serve --also-host <window_host>` | published on `window_host` too; only the people's folders mounted |
| the pages | plain programs | Setu's and Dvara's as containers; the home page as a user service (`~/.config/systemd/user/sarathi-home.service`) |
| a cloud key | from `secrets.env`, or your shell | from `secrets.env` only |
| Ollama | as it is | must listen beyond 127.0.0.1 (`OLLAMA_HOST=0.0.0.0`) |
| Yantra's own `.env` | read, as in a terminal | not in the image: model settings come from `[model]` in sarathi.toml only |

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

* **One image holding Yantra, Setu and Samay.** They call each other as
  programs, so each container needs all of them. `sarathi image` builds
  it from the **committed** code of the checkouts beside Sarathi, and
  names any uncommitted changes it left out.
* **A browser, and the wall around a connector.** Google Chrome at
  `/usr/bin/google-chrome`, where a desktop has it, so the Amazon and X
  profiles Setu already recorded open with the browser that wrote them;
  Xvfb for a site that wants a real window; and bubblewrap, so Setu's
  connectors are walled off here as on your desktop. Chrome refuses a
  profile a newer Chrome wrote, so `up` says when your computer's Chrome
  has got ahead of the image's (`sarathi image` catches up: it tells the
  build which Chrome is here, so that step isn't taken from the cache;
  [notes/05](notes/05-a-browser-in-the-image.md)). Google ships
  Chrome for amd64 only; elsewhere the image gets Debian's Chromium.
* **Your data, at the same paths.** Samay's schedules, Setu's sign-ins
  and Yantra's memory are mounted from where they are on your machine,
  at the same paths, and the containers run as you. Nothing is copied,
  and the process road and the Podman road see the same things.
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
dvara       ~/agent/dvara/.venv/bin/dvara  (beside)
            many people and agents behind one service
            door serving at http://127.0.0.1:8770 (dvara serve); 3 agents, 2 people
sparsh      ~/agent/sparsh/.venv/bin/sparsh  (beside)
            the hands: your phone, worked by number, with a yes before Send
            phone emulator-5554 (sdk_gphone64_x86_64) ready
smritikosh  not found (optional) -- install it, or set SARATHI_SMRITIKOSH=/path/to/smritikosh-mcp
            a memory store (Yantra keeps its own without it)
```

Each line says **where** a piece was found and **which rule** found it.
The line under it is that piece's own account of itself: Yantra's
release and the model it would ask (asked with the model, Setu and
Samay `up` gives it, so a model Ollama hasn't pulled shows here with
the `ollama pull` that fixes it, and so does a sibling it can't find), Setu's connections, Samay's clock, the phones Sparsh can reach, and
whether Dvara is serving (asked about the folders `[dvara]` names;
with Dvara off, dvara isn't asked). Sarathi repeats it and adds
nothing. Smritikosh has no status command, so for it "found, here" is
the whole answer.

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

One page that links to each program's own page: Yantra's, Samay's,
Setu's (`setu serve`) and, with Dvara on, Dvara's (`dvara page`).
With Sparsh found (on the Podman road, once `[phone] address` is set), a **Your phone** card
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

It only links. Nothing on it starts, stops or changes anything. Because
its links carry the other pages' keys, it has a key of its own (after the
`#`, kept in `~/.local/share/sarathi/home.token`, or
`$SARATHI_HOME_TOKEN`), and it listens on this computer only.
([notes/06](notes/06-one-bookmark.md))

### Where it looks

In this order; the first hit wins:

| Rule | Where |
|---|---|
| `env` | a path you set: `SARATHI_YANTRA`, `SARATHI_SETU`, `SARATHI_SAMAY`, `SARATHI_DVARA`, `SARATHI_SPARSH`, `SARATHI_SMRITIKOSH` |
| `path` | what your shell would run |
| `beside` | `<dir>/<name>/.venv/bin/<program>`, for checkouts kept side by side. `<dir>` is `SARATHI_SIBLINGS`, or the folder this checkout of Sarathi sits in |

### Where its files live

| | |
|---|---|
| `~/.config/sarathi/sarathi.toml` | the settings (`$SARATHI_CONFIG` for another folder) |
| `~/.config/sarathi/secrets.env` | a cloud key, if you typed one, and Dvara's two tokens; readable only by you |
| `~/.config/sarathi/units/` | the Podman road: each unit's own share of secrets.env, copied by `up`; yours alone |
| `~/.config/containers/systemd/sarathi-*` | the Podman road's units and network, written by `up` (edit `sarathi.toml`, not these) |
| `~/.config/systemd/user/sarathi-home.service` | the Podman road's home page, a plain user service (written by `up` too) |
| `~/dvara/` | Dvara's own files: `actors.toml`, `agents/`, `state/` (dvara's defaults; `[dvara]` can name others) |
| `~/.local/share/sarathi/` | `home.token` the home page's key (yours alone), `work/` where the page starts, `run/` what `up` started, `logs/` what each printed (`$SARATHI_STATE`); `run/` and `logs/` are yours alone, since Samay's page token appears in them |

Each sibling keeps its own data where it always has. Samay's schedules
are still in `~/.samay`, and Setu's sign-ins are still where Setu put
them. Sarathi starts the pieces; it doesn't move their files.

## The source

```
src/sarathi/
  siblings.py   which pieces exist, where each is found, and what its
                status --json says, read by format  (notes/01); Sparsh,
                the phone  (notes/07)
  config.py     sarathi.toml and secrets.env: read, checked, written  (notes/02);
                each table by its project's name, old names still read  (notes/09)
  first_run.py  sarathi init: which model answers, asked once  (notes/02)
  services.py   sarathi up / down: start Samay and the page, know
                which are ours  (notes/02); and the pages  (notes/06);
                each line by its project's name  (notes/09)
  podman.py     the same on the podman road: the image, the Quadlet
                units, systemd  (notes/03); Dvara's unit  (notes/04);
                its streamed window, and the image's browser  (notes/05);
                the firewall named when phones are to reach it  (notes/11)
  door.py       sarathi dvara: dvara turned on, its tokens, starter files,
                and who messaged unlisted  (notes/04)
  phone.py      sarathi phone: [phone] on, paired and reached over Wi-Fi
                through the Sparsh found  (notes/08)
  home.py       sarathi home: one page linking every program's page, each
                with its status and its key; static/ is that page  (notes/06);
                the phone's card, which opens Yantra's page  (notes/07)
  Containerfile one image, every program, a browser and bubblewrap  (notes/05)
  cli.py        sarathi init | dvara | phone | road | image | up | down | status [--json] | home
tests/
  test_status.py  test_config.py  test_up.py  test_podman.py  test_door.py  test_home.py
  test_pages_up.py  test_phone.py  test_names.py
```

## Status

Finding the pieces, the settings, starting them as plain processes or
as Podman containers, and the household road (dvara on Telegram, wired
to Samay) are all built, with a browser and bubblewrap inside the
containers. `sarathi up` also starts Setu's page, Dvara's owner page and
the home page that links every program's page. Sparsh is found, its
phones are said, and Yantra's page and Dvara are handed it; inside
the containers the phone is reached over Wi-Fi (`sarathi phone`), tried
against the emulator and a real Nexus 6P on Android 8.1, a schedule's
locked phone asked about on Telegram and worked once unlocked
([notes/10](notes/10-a-real-phone.md)).

## Tests

```bash
uv run pytest -q
```

## License

Apache-2.0
