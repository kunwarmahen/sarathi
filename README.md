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
smritikosh  not found (optional) -- install it, or set SARATHI_SMRITIKOSH=/path/to/smritikosh-mcp
            a memory store (Yantra keeps its own without it)
```

Each line says **where** a piece was found and **which rule** found it.
The line under it is that piece's own account of itself: Setu's
connections, Samay's clock. Sarathi repeats it and adds nothing. Yantra,
Dvara and Smritikosh have no status command, so for them "found, here"
is the whole answer.

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
| `~/.config/sarathi/secrets.env` | a cloud key, if you typed one; readable only by you |
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
  cli.py        sarathi init | up | down | status [--json]
tests/
  test_status.py  test_config.py  test_up.py
```

## Status

Finding the pieces, the settings and starting them as plain processes
are built. Next: the same pieces as Podman containers with Quadlet units.
After that, the Setu and Samay wiring Yantra carries today moves here,
and then the road for a household on Telegram through Dvara.

## Tests

```bash
uv run pytest -q
```

## License

Apache-2.0
