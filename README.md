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
part you install.** It finds the others, says what each is doing, and
(soon) sets them up and starts them together.

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
.venv/bin/sarathi status
```

## Using it

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

## The source

```
src/sarathi/
  siblings.py   which pieces exist, where each is found, and what its
                status --json says, read by format  (notes/01)
  cli.py        sarathi status [--json]
tests/
  test_status.py
```

## Status

Finding the pieces is built. Next: one settings file turned into each
piece's own settings and a `sarathi up` that starts them, first as plain
processes, then as Podman containers with Quadlet units. After that come
the pages Yantra currently wires for Setu and Samay, and the road for a
household on Telegram through Dvara.

## Tests

```bash
uv run pytest -q
```

## License

Apache-2.0
