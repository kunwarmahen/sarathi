# 01 — Five names, one answer

Yantra grew siblings one job at a time. Setu holds the sign-ins, so the
model never sees a key. Samay keeps the clock, so work happens while
nobody watches. Dvara is the door many people knock on. Smritikosh is a
memory store. Each one refused to be part of another, and each refusal
was right: a scheduler inside the agent framework would have been a
second framework that only runs at 08:00.

The cost of being right five times is five names. Someone who wants a
helper that reads their mail every morning has to install three of them,
know which environment each lives in, and know that Yantra finds Setu by
running `setu status --json`. That knowledge lived in nobody's code. It
lived in the head of whoever set the machine up.

Sarathi is where it lives now.

## Wiring, and nothing else

**SARATHI HOLDS NO LOGIC OF ITS OWN.** Not an agent, not a tool, not a
prompt layer, not a memory. The test for any line of code proposed here
is: *would someone using that sibling alone want this too?* If yes, it
belongs in the sibling. What is left is the part that only exists
because the pieces are together: which ones, where, started how, set up
with which settings.

The reverse holds too: **NOTHING DEPENDS ON SARATHI.** Every sibling
must keep working without it. Sarathi reads what they publish and never
asks them to know it exists.

## A program, not an import

The obvious package is one that depends on all five and imports them.
It doesn't survive the first look at a real machine:

```
yantra      ~/Documents/ai/agent/yantra/.venv/bin/yantra  (beside)
setu        ~/.local/bin/setu  (path)
samay       ~/Documents/ai/agent/samay/.venv/bin/samay  (beside)
dvara       ~/Documents/ai/agent/dvara/.venv/bin/dvara  (beside)
```

Four programs, four environments. Setu is installed as a tool on its own
so that its sign-in files are read by one small program and nothing
else. Pulling it into one Python with Playwright, FastAPI and a model
client would undo the reason it was split off. So Sarathi does what Yantra
already does with Setu and Samay: **find the program, run `status --json`,
read the `format`.** Sarathi has no dependencies at all.

**AN UNKNOWN FORMAT IS REFUSED.** `setu.status.v1` is a promise about
which fields mean what. A `v2` might have renamed `connections`, and a
Sarathi that guessed would print "no accounts connected" to someone with
nine. It says instead:

```
setu        ~/.local/bin/setu  (path)
            found, but: `status --json` speaks 'setu.status.v2', not 'setu.status.v1': a version this Sarathi does not know
```

## Where it looks, and saying so

Three rules, in order: a path you set (`SARATHI_SAMAY=...`), then your
shell's `PATH`, then checkouts kept side by side (`<dir>/samay/.venv/bin/
samay`). **EVERY ANSWER NAMES ITS RULE** (`(env)`, `(path)`, `(beside)`),
because the question after "is it there?" is always "why is it running
*that* one?", and the answer should be on the screen, not in a debugger.

The side-by-side rule exists because that's how the projects are
developed: one folder, a checkout of each. Smritikosh happens to live
elsewhere on this machine, which is what the first rule is for:

```
$ SARATHI_SMRITIKOSH=~/Documents/ai/smritikosh/.venv/bin/smritikosh-mcp sarathi status
...
smritikosh  ~/Documents/ai/smritikosh/.venv/bin/smritikosh-mcp  (env)
            a memory store (Yantra keeps its own without it)
```

## Only what the sibling says

**SARATHI REPEATS; IT DOES NOT INFER.** Setu knows its connections and
Samay knows whether its clock is running, so their lines are their own
words, shortened:

```
setu        9 accounts connected: amazon:personal, gmail:mine, ...
samay       clock not running (start it: samay serve); schedules: 0 active, 0 paused
```

Smritikosh has no status command. Sarathi could probe a port and guess
that a listener there is it, but a guess printed in the same font as a
fact is worse than no line. For it, "found, here" is the whole answer
until it can say more for itself.

Yantra can now. `yantra status --json` gives its release and the model
a turn would ask (Yantra's note 117). Sarathi asks it with the model
settings `up` gives Yantra, so the answer is about the Yantra Sarathi
starts, and a model Ollama hasn't pulled shows up here rather than as
the first message that fails:

```
yantra      ~/Documents/ai/agent/yantra/.venv/bin/yantra  (beside)
            the machine: the agent itself
            yantra 0.1.0; would ask ollama for qwen3.8-64k:latest
```

Dvara can now. `dvara status --json` answers from the lock a serving
dvara holds on its state folder (dvara's note 23), so it's right after
a crash and from another container. Sarathi asks it about the folders
`[door]` names in sarathi.toml, not dvara's defaults, so the answer is
about the door `up` starts:

```
dvara       ~/Documents/ai/agent/dvara/.venv/bin/dvara  (beside)
            the door: many people and agents behind one service
            door serving at http://127.0.0.1:8798 (dvara serve); 3 agents, 2 people
```

With the door off, dvara isn't asked at all. Its answer about folders
nobody set up would only be a list of problems nobody has:

```
            door off in sarathi.toml (`sarathi door` turns it on)
```

**A MISSING PIECE COMES WITH ITS FIX.** "not found" alone sends the
reader to the docs. The line names the variable that would fix it:

```
smritikosh  not found (optional) -- install it, or set SARATHI_SMRITIKOSH=/path/to/smritikosh-mcp
```

Dvara and Smritikosh are optional. A helper for one person on one
machine needs Yantra, Setu and Samay, and the exit status checks only
those, so `sarathi status && sarathi up` will never stop on a door
nobody asked for.

## Live receipt

On the machine it was written on, with the siblings checked out side by
side and Setu installed as a tool:

```
$ sarathi status
yantra      ~/Documents/ai/agent/yantra/.venv/bin/yantra  (beside)
            the machine: the agent itself
setu        ~/.local/bin/setu  (path)
            the bridge: your accounts, signed in once
            9 accounts connected: amazon:personal, gmail:mine, gmail:personal, homeassistant:home, linkedin:personal, slack:work, whatsapp:personal, x:personal, yahoo:personal
samay       ~/Documents/ai/agent/samay/.venv/bin/samay  (beside)
            the clock: work done later, with receipts
            clock not running (start it: samay serve); schedules: 0 active, 0 paused
dvara       ~/Documents/ai/agent/dvara/.venv/bin/dvara  (beside)
            the door: many people and agents behind one service
smritikosh  not found (optional) -- install it, or set SARATHI_SMRITIKOSH=/path/to/smritikosh-mcp
            a memory store (Yantra keeps its own without it)
$ echo $?
0
```

## What is not here yet

* ~~One settings file (`sarathi.toml`) turned into each sibling's own
  settings.~~ Built: [notes/02](02-one-file-two-processes.md).
* ~~`sarathi up` / `down` as plain processes.~~ Built:
  [notes/02](02-one-file-two-processes.md). As Podman containers with
  Quadlet units: not yet.
* A way for Yantra's web page to take tabs from outside, so the Setu and
  Samay wiring Yantra carries today can move here.
* ~~The household road: Dvara's agents reaching each person's Setu and
  Samay, with Telegram set up from here.~~ Built:
  [notes/04](04-a-door-for-the-household.md).
* ~~Whether the door is serving, not just that dvara was found.~~ Built:
  above, from `dvara status --json`.
* ~~Yantra's version.~~ Built: above, from `yantra status --json`. A
  Yantra older than that reads `status` as a prompt for its model, and
  Sarathi refuses the answer for having no `format`.
