# 03 — Two containers, one clock

[Note 02](02-one-file-two-processes.md) started the clock and the page
as plain processes. They stop when the machine does, and nobody restarts
them after a crash. On this machine, everything long-running already
lives in Podman containers under systemd. This note puts the clock and
the page there too: `run.road = "podman"`, `sarathi image`, and the same
`sarathi up`.

## One image, every program

The obvious layout is one image per project. It doesn't survive the
first look at how they talk. The page doesn't call Setu over a network;
it runs `setu run gmail:mine` as a child process and speaks MCP over its
pipes. It runs `samay mcp` the same way. The clock runs `yantra --json`
for every scheduled job. Each link is a program, so **EVERY CONTAINER
HOLDS EVERY PROGRAM**: one image with Yantra, Setu and Samay, each in its
own environment under `/opt` as on a desktop, so their dependencies
never have to agree. Then two containers from that image, one per
long-running process.

**BUILT FROM WHAT IS COMMITTED.** `sarathi image` doesn't send the
working trees to the build. It takes `git archive HEAD` of each
checkout, so the same commits always give the same image and a
half-finished edit never ships by accident. What it leaves out is named:

```
building from:
  yantra  0706360
  setu    96a6b4a
  samay   707562e
```

A checkout with uncommitted changes gets `(3 uncommitted change(s) left
out: commit to include them)` next to its commit. The question "why
isn't my fix in there?" gets answered before anyone has to ask it.

## The same files at the same paths

**THE DATA STAYS WHERE IT IS, AT THE SAME PATH.** Samay's `~/.samay`,
Setu's `~/.local/state/setu` and Yantra's `~/.local/state/yantra` and
`~/.yantra` are mounted into both containers at the paths they have on
the host, `HOME` is set to match, and `UserNS=keep-id` runs the
containers as you. Mounting them at, say, `/data/setu` would have been
tidier. But Setu's records hold absolute paths (a browser profile's
folder), and a schedule names its agent's folder. At the same paths,
the same files give the same answers, and switching between the process
road and the Podman road changes nothing about what the agent knows. On
this machine, the page in its container came up with everything the
desktop page had:

```
setu: gmail-mine (7 tool(s)), gmail-personal (7 tool(s)), homeassistant-home (6
tool(s)), amazon (7 tool(s)), ... -- via /usr/local/bin/setu
samay: 7 tool(s), 0 active schedule(s); its clock is running -- via
/usr/local/bin/samay
memory: local for mahen -- 25 remembered (/memory; --memory off)
```

**OLLAMA STAYS ON THE HOST.** Inside a container, `localhost` is the
container. The local road's address becomes `host.containers.internal`,
which Podman points at the host. Ollama has to listen on more than
127.0.0.1 for that to reach it. On this machine it already listens on
`*:11434`.

**A KEY ONLY FROM SECRETS.ENV.** On the process road a key exported in
the shell reaches the pieces, because `up` started them from that shell.
A systemd unit never sees that shell, so the key would silently not
arrive, and the first sign would be a failed turn hours later. So on
this road `up` refuses up front if the key isn't in `secrets.env`, and
hands that file to the units with `EnvironmentFile=`. The unit files
hold no key, and can be read and pasted like `sarathi.toml`.

## What the first crash found

The units were written, the containers came up, a turn was answered.
Then the clock was killed, to see whether systemd would bring it back.

**THE FIRST DESIGN SHARED A PID NAMESPACE, AND IT BROKE.** Samay used to
decide "is the clock running?" by checking whether the pid in its
`serve.json` was alive, and a pid means nothing in another container.
So the page had been put in the clock's namespace (`--pid=container:`),
and bound to it. After `kill -9` on the clock, the page died with it,
since its namespace was gone, and nothing restarted it. Adding
`Upholds=` to bring it back made it worse:

```
Error: container 842f7ab… has dependent containers which must be removed before it
error: samay serve is already running for /home/mahen/.samay
sarathi-clock.service: Start request repeated too quickly.
```

Podman wouldn't replace the clock while the page depended on it. And
once it could, the new clock refused to start. The dead clock's
`serve.json` named pid 2, and in a fresh container pid 2 was the new
`samay serve` itself, so it found "itself" running.

**THE FIX WAS IN SAMAY, NOT HERE.** Both failures came from one decision
in Samay, and anyone running Samay in a container hits the second one,
with or without Sarathi. So Samay changed. The clock now holds an
`flock` on `serve.lock` for as long as it runs, and "is it running?"
asks whether the lock is held ([Samay's note 05](https://github.com/kunwarmahen/samay/blob/main/notes/05-a-lock-not-a-pid.md)).
The kernel releases a lock however its holder dies, and every container
that mounts `~/.samay` sees the same lock. The page now shares nothing
with the clock except files:

```
[Unit]
Wants=sarathi-clock.service
After=sarathi-clock.service
```

`After=` keeps note 02's ordering, since the page asks about the clock
once, at start-up. Now systemd keeps that order, not a loop in `up`.

The same crash test afterwards, `kill -9` on each container in turn:

```
--- kill -9 the clock
  after ~2s: active active
  page untouched: yes
  page sees clock serving: True
--- kill -9 the page
  after ~8s: active active
samay: 7 tool(s), 0 active schedule(s); its clock is running
```

## Up, down, and login

`sarathi up` writes the units, and rewrites them and reloads systemd
only when `sarathi.toml` changed them. Then it starts them and waits
until each one **answers HTTP**. A published port accepts connections
before the program inside is listening, so the bare connect that note
02 used would report "up" for a page that was still starting.

Quadlet units with `WantedBy=default.target` start at every login,
which is the point. So `sarathi down` stops them and says they will be
back:

```
$ sarathi down
page   stopped  (unit sarathi-page)
clock  stopped  (unit sarathi-clock)
they start again at your next login (`sarathi down --remove` to stop that too)
```

**A PORT SOMETHING ELSE HOLDS IS SAID BEFORE ANYTHING STARTS.** A
published port that another program already holds fails inside systemd:
`rootlessport listen tcp 127.0.0.1:8765: bind: address already in use`,
exit 126, restarted every few seconds, with the reason a page deep in
the journal. That's how the door first met a program of the owner's
that was already on 8765. So `up` now checks each host port (the
window's too) before it starts a unit, stops a unit that was already
looping, and says what the process road says:

```
door   not started: something else is listening on port 8765 (change door.port in sarathi.toml)
```

## Switching roads

Both roads run the same things on the same ports and read the same
files, so switching is a setting, not a migration. `sarathi road
process|podman` changes it, and first stops what the other road
started. **LEAVING PODMAN REMOVES ITS UNITS.** Stopped units start again
at the next login and take the ports back from the process road, so
`down` alone isn't enough; `road` does `down --remove`. It starts
nothing; `up` does that.

```
$ sarathi road
road: podman -- containers that systemd keeps running and starts at login
  (`sarathi road process` for plain programs on this machine, using its own browser and bubblewrap)
```

## Live receipt

`qwen3.8:latest` on the host's Ollama, the image built from yantra
`0706360`, setu `96a6b4a` and samay `707562e`, with scratch settings and
ports 8410/8790:

```
$ sarathi up
units rewritten from sarathi.toml
clock  up at http://127.0.0.1:8790/#token=…  (unit sarathi-clock)
page   up at http://127.0.0.1:8410/  (unit sarathi-page)
```

A turn on the page, answered from inside its container:

```
user:      In one short sentence: what is 17 times 3?
assistant: 17 times 3 is 51.
```

A scheduled run inside the clock's container (Samay running Yantra,
Yantra reaching Ollama on the host), made, run once and removed:

```
$ podman exec sarathi-clock samay run-now 3460ef7b
Tue 6 Oct 00:53  ok            the clock works
```

## What is not here yet

* ~~**A browser.** Setu's accounts that work through a browser (Amazon, X,
  LinkedIn) and Yantra's browser tools need one, and signing in needs a
  window.~~ Built: [notes/05](05-a-browser-in-the-image.md).
* ~~**The Schedules panel's link** said `http://0.0.0.0:8780/`.~~ Samay
  now takes the address a browser uses (`SAMAY_PUBLIC_URL`), and the
  clock's unit sets it to the published port, so the panel and `samay
  status` say `http://127.0.0.1:<clock.port>/`. The log rewrite stays
  for an image built before Samay could be told.
* **Agent folders outside the mounted ones.** A schedule that runs an
  agent package from, say, `~/agents/reader` needs that folder mounted
  too. The page's own schedules run plain Yantra and don't.
