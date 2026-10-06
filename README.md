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
| **Smritikosh** (स्मृतिकोश, "store of memories") | a memory store an agent can use instead of Yantra's own |

Each is useful alone. Together they are a helper that knows your
accounts, remembers you and keeps time — but only if you know five
names, five installs, and how they find each other. **Sarathi is the
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
`sarathi init --provider ollama --model gemma4:12b --web-port 8400
--no-clock`.

The file it writes is short and meant to be edited:

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

A table or key Sarathi doesn't know (`[clok]`) stops `up` with its
name. Nothing is ignored quietly.

### Every day: `sarathi up` and `sarathi down`

```
$ sarathi up
clock  up at http://127.0.0.1:8780/#token=…  (pid 3324159)
page   up at http://127.0.0.1:8321/  (pid 3324163)
```

That starts two things: **Samay's clock** and **Yantra's page**, in
that order. The page asks once, at start-up, whether the clock runs, so
the clock has to be there first. Setu isn't started: it runs only when
the agent uses an account. Both get the same model, so a scheduled run
is answered by the same model as the page. Each piece's output goes to
`~/.local/share/sarathi/logs/`.

A second `sarathi up` starts nothing new. A clock you already run some
other way (`samay unit`, a terminal) is left alone, because a second
clock would run every schedule twice. A port something else holds is
reported, not fought over. A piece that crashes on start is reported
with the last lines of its log, not as "started".

`sarathi down` stops what `up` started and nothing else.

That's the process road, plain programs. The same commands run
everything as containers instead, after `sarathi road podman` (below).

### For other people, and your phone: `sarathi door`

```bash
sarathi door                  # which agent a Telegram bot answers as; the bot's token
sarathi door --telegram greeter --telegram-id 8675309
sarathi door --off
```

turns on **dvara** as a third piece. `up` then starts clock, door, page,
in that order:

```
door   dvara --root ~/dvara/agents --actors ~/dvara/actors.toml --state ~/dvara/state
             --ask --provider <model.provider> --model <model.model> --samay <samay>
             serve --port <door.port> [--telegram <door.telegram>]
```

What a person would otherwise wire by hand in two places:

* **The clock and the door know each other.** Both get the same
  `SAMAY_DVARA_URL` (the door's address) and `SAMAY_DVARA_TOKEN` (the
  door's own token), so a schedule made in a chat is checked by the clock
  against the door that made it.
* **Tokens.** `DVARA_TOKEN` is made for you; `TELEGRAM_TOKEN` (from
  @BotFather) is typed at a hidden prompt. Both go to `secrets.env`, and
  from there **to the door alone**: the page never holds the bot's token,
  and the clock gets only the door's.
* **dvara's files, only when missing.** A starter `actors.toml` (you, as
  the owner) and dvara's own example agents. dvara's formats; Sarathi
  never touches them again, and ships no agent of its own.
* **The same model** as the page and the clock (`--provider`, `--model`).
* **Who may talk to it** is the actors file. Someone not in it gets
  silence, and `sarathi status` names their Telegram id, which is how
  you find your own:

  ```
    door   running at http://127.0.0.1:8770/  (pid 3426486)
           messaged the bot but not in the actors file (telegram id): 8675309
  ```

**Amazon or X from someone's phone.** Those sites are signed in to in a
browser window on this computer. Give the door a window address and Setu
streams that window to their phone when they send `/connect amazon`
(dvara's note 22):

```bash
sarathi door --window-host 100.101.102.103      # your Tailscale address, say
sarathi door --window-host 127.0.0.1 --window-url https://door.example.net   # behind your HTTPS
```

They become `[door] window_host / window_port / window_url`, passed to dvara
as Setu's `SETU_WINDOW_*`. A home network address works for people at home
but is plain HTTP; Tailscale or your own HTTPS is the safe choice beyond it.
On the Podman road the window runs in the door's container: it listens
on a fixed port there (`window_port`, else 8790), published on
`window_host` alone, and the link says `window_url` or
`http://window_host:port`.

A door that can't start (no actors file, a bot with no token) says why,
and the clock and page start anyway. On the Podman road it's a third
unit, `sarathi-door`, on a network shared with the others
(`sarathi.network`), where the clock reaches it as `sarathi-door`.
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
| after `git pull` in a checkout | nothing: it runs the checkout | `sarathi image` again |
| Amazon and X | your own Chrome | Chrome in the image |
| connectors walled off | your bubblewrap (`sudo apt install bubblewrap`) | bubblewrap in the image |
| the door's streamed window | listens on `window_host` itself | published from the door's container |
| a cloud key | from `secrets.env`, or your shell | from `secrets.env` only |
| Ollama | as it is | must listen beyond 127.0.0.1 (`OLLAMA_HOST=0.0.0.0`) |

Your accounts, schedules and memories are the same files either way, so
switching loses nothing. A port something else already uses stops that
piece on either road, with the setting that moves it.

#### On the Podman road

```bash
sarathi road podman            # or  sarathi init --podman
sarathi image                  # build the image (a few minutes, once per update; ~1.3 GB)
sarathi up
```

On this road `up` writes Quadlet units (`sarathi-clock`, `sarathi-page`,
and `sarathi-door` when the door is on) into
`~/.config/containers/systemd/`, and systemd starts them. When
`sarathi.toml` changes a unit, `up` restarts it with the new settings. They come back on their own after a crash, and they start again
when you log in. `sarathi down` stops them; `sarathi down --remove` also
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
  has got ahead of the image's (`sarathi image` catches up). Google ships
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
setu        ~/.local/bin/setu  (path)
            the bridge: your accounts, signed in once
            2 accounts connected: gmail:mine, homeassistant:home
samay       ~/agent/samay/.venv/bin/samay  (beside)
            the clock: work done later, with receipts
            clock not running (start it: samay serve); schedules: 0 active, 0 paused
dvara       ~/agent/dvara/.venv/bin/dvara  (beside)
            the door: many people and agents behind one service
            door serving at http://127.0.0.1:8770 (dvara serve); 3 agents, 2 people
smritikosh  not found (optional) -- install it, or set SARATHI_SMRITIKOSH=/path/to/smritikosh-mcp
            a memory store (Yantra keeps its own without it)
```

Each line says **where** a piece was found and **which rule** found it.
The line under it is that piece's own account of itself: Setu's
connections, Samay's clock, and whether the door is serving (asked about
the folders `[door]` names; with the door off, dvara isn't asked).
Sarathi repeats it and adds nothing. Yantra and Smritikosh have no
status command, so for them "found, here" is the whole answer.

After `sarathi up`, `status` also lists what it started, and whether
each one is still running. If one has exited, it shows the end of its
log.

`sarathi status --json` prints the same as `sarathi.status.v1`, with each
sibling's own status object inside. The exit status is 0 when Yantra,
Setu and Samay are all found and readable, and 1 otherwise. Dvara and
Smritikosh are optional: a missing one is reported and never fails the
check.

### Where it looks

In this order; the first hit wins:

| Rule | Where |
|---|---|
| `env` | a path you set: `SARATHI_YANTRA`, `SARATHI_SETU`, `SARATHI_SAMAY`, `SARATHI_DVARA`, `SARATHI_SMRITIKOSH` |
| `path` | what your shell would run |
| `beside` | `<dir>/<name>/.venv/bin/<program>`, for checkouts kept side by side. `<dir>` is `SARATHI_SIBLINGS`, or the folder this checkout of Sarathi sits in |

### Where its files live

| | |
|---|---|
| `~/.config/sarathi/sarathi.toml` | the settings (`$SARATHI_CONFIG` for another folder) |
| `~/.config/sarathi/secrets.env` | a cloud key, if you typed one, and the door's two tokens; readable only by you |
| `~/.config/sarathi/units/` | the Podman road: each unit's own share of secrets.env, copied by `up`; yours alone |
| `~/.config/containers/systemd/sarathi-*` | the Podman road's units and network, written by `up` (edit `sarathi.toml`, not these) |
| `~/dvara/` | the door's own files: `actors.toml`, `agents/`, `state/` (dvara's defaults; `[door]` can name others) |
| `~/.local/share/sarathi/` | `work/` where the page starts, `run/` what `up` started, `logs/` what each printed (`$SARATHI_STATE`); `run/` and `logs/` are yours alone, since Samay's page token appears in them |

Each sibling keeps its own data where it always has. Samay's schedules
are still in `~/.samay`, and Setu's sign-ins are still where Setu put
them. Sarathi starts the pieces; it doesn't move their files.

## The source

```
src/sarathi/
  siblings.py   which pieces exist, where each is found, and what its
                status --json says, read by format  (notes/01)
  config.py     sarathi.toml and secrets.env: read, checked, written  (notes/02)
  first_run.py  sarathi init: which model answers, asked once  (notes/02)
  services.py   sarathi up / down: start the clock and the page, know
                which are ours  (notes/02)
  podman.py     the same on the podman road: the image, the Quadlet
                units, systemd  (notes/03); the door's unit  (notes/04);
                its streamed window, and the image's browser  (notes/05)
  door.py       sarathi door: dvara turned on, its tokens, starter files,
                and who messaged unlisted  (notes/04)
  Containerfile one image, every program, a browser and bubblewrap  (notes/05)
  cli.py        sarathi init | door | road | image | up | down | status [--json]
tests/
  test_status.py  test_config.py  test_up.py  test_podman.py  test_door.py
```

## Status

Finding the pieces, the settings, starting them as plain processes or
as Podman containers, and the household road (dvara on Telegram, wired
to the clock) are all built, with a browser and bubblewrap inside the
containers.

## Tests

```bash
uv run pytest -q
```

## License

Apache-2.0
