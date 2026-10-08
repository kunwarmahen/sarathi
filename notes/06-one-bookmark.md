# 06 — one bookmark

*[Note 01](01-five-names-one-answer.md) made `sarathi status` the one
place that says what is here. This note puts that answer on a page, with
a link to each program's own page beside it.*

## The problem, as you would meet it

Each program has its own page now. Yantra's is where you talk to the
agent. Samay's lists what runs later. Setu's shows your accounts (`setu
serve`), and Dvara's shows the door and the people on it (`dvara page`).
They're on four ports, and three of them want a token after the `#`,
printed once by the program that started them. To open Setu's page next
week you need that line from the terminal it scrolled off of.

## A page of links, and nothing else

```
$ sarathi home
your home page:
  http://127.0.0.1:8760/#token=…
```

The page has one card per page: what it's for, **running** or **not
running**, the program's own status line under it (the same line
`sarathi status` prints), and **Open**. A page that isn't running shows
the command that starts it instead.

**LINKING ONLY.** Sarathi has no logic of its own ([the README](../README.md#what-sarathi-does-not-do)),
and this page doesn't add any. *Running* means the page's port answers.
The line under it is the program's own `status`. **Open** is the
program's own page. Nothing on the home page starts, stops or changes
anything, and a POST to it is refused.

**THE LINK CARRIES THE KEY.** Samay keeps its page's token in
`~/.samay/serve.token`, Setu in its folder's `page.token`, and Dvara in
the door's state folder. On the Podman road those folders are mounted at
the same paths ([note 03](03-two-containers-one-clock.md)), so one read
works on both roads. The home page puts each token after the `#` of its
link, and the page opens already signed in.

**SO IT HAS A KEY OF ITS OWN.** A page whose answer contains every other
page's token is a key ring, and anything on this machine can reach
127.0.0.1. `/api/pieces` answers only with the home page's own token
(`$SARATHI_HOME_TOKEN`, or one kept in `~/.local/share/sarathi/home.token`
at 0600), which arrives after the `#` like the others. Its links open
with no referrer, and no site may frame it.

A token Sarathi can't find (the page started with one from its own
environment, or never started) gets a plain link and a line saying to
open that page from the address its program printed.

**ASKED AT MOST EVERY 30 SECONDS.** Each status line is a program run as
a subprocess. A page left open in a tab shouldn't start four programs
every 20 seconds, so the lines are kept for 30.

## Live receipt

On this machine, with `setu serve` and `dvara page` started by hand and
the Podman units stopped:

```
$ curl -s -o /dev/null -w "%{http_code}\n" localhost:8760/api/pieces
401

$ curl -s -H "Authorization: Bearer $T" localhost:8760/api/pieces
yantra down keyed | yantra 0.1.0; would ask ollama for qwen3.8-64k:latest | http://127.0.0.1:8321/
samay  down keyed | clock not running (start it: samay serve); schedules: 0 active, 0 paus… | http://127.0.0.1:8780/#token=…
setu   up   keyed | 9 accounts connected: amazon:personal, gmail:mine, gmail:personal, hom… | http://127.0.0.1:8775/#token=…
dvara  up   keyed | door not serving; 3 agents, 1 people | http://127.0.0.1:8785/#token=…
```

In a browser, **Open Setu** and **Open Dvara** each opened their page
signed in (no "this page needs its key"), with `document.referrer`
empty.

## What was deliberately not built

* **Start buttons.** A down page shows the command that starts it. A
  button would make this page a second `sarathi up`, with its own idea of
  what started what.
* **Frames.** The home page could show each page inside itself. But Setu
  and Dvara allow framing only by name, and a page of frames would also
  need every token in its own HTML.
* **Reaching it from your phone.** Like every page here, it listens on
  127.0.0.1. Its links point to 127.0.0.1 too, so opening it from another
  device needs each page reachable there first (Tailscale, later).

## Started with the rest

`sarathi up` now starts the pages too, unless `[pages] on = false`:

```
$ sarathi up
clock  off in sarathi.toml
page   up at http://127.0.0.1:8331/  (pid 571501)
setu   up at http://127.0.0.1:8876/#token=…  (pid 571627)
home   up at http://127.0.0.1:8861/#token=…  (pid 571637)
```

(A scratch config: the clock and the door off, the pages on two free
ports.) The home page it started answered with Yantra's page and Setu's,
both running, and **sarathi up** as the way to start them. `sarathi down`
stopped all three.

**DVARA'S PAGE GETS THE DOOR'S TOKEN, AND NOTHING ELSE DOES.** Dvara's
page passes your answers to the running door, so `up` hands it
`DVARA_TOKEN` and the door's address (`DVARA_URL`). On the Podman road
the token is in its own env file, and the address is the door's name on
the network. Yantra's page, Setu's page, the clock and the home page
never hold it. `[door] owner` names whose page it is; an id the actors
file doesn't have stops it at start, with the reason in its log.

**ON THE PODMAN ROAD, THE HOME PAGE IS NOT A CONTAINER.** Setu's and
Dvara's pages are two more containers from the image, published on
127.0.0.1. The home page isn't: Sarathi is not in the image, and inside
a container 127.0.0.1 is the container, so it couldn't tell whether the
other pages' ports answer. It is a plain user service running this
machine's `sarathi home`, enabled so it starts at login with the units.

Each page's port is a `[pages]` setting (`home_port`, `setu_port`,
`door_port`), and a taken one says which to change, like the others.

## The Podman road, run

On the owner's own machine and `sarathi.toml` (the door on, its window on
the home network's address), after `sarathi image`:

```
$ sarathi up
clock  up at http://127.0.0.1:8780/#token=…  (unit sarathi-clock)
door   up at http://127.0.0.1:8770/  (unit sarathi-door)
page   up at http://127.0.0.1:8321/  (unit sarathi-page)
setu   up at http://127.0.0.1:8775/#token=…  (unit sarathi-setu)
owner  up at http://127.0.0.1:8785/#token=…  (unit sarathi-owner)
home   up at http://127.0.0.1:8760/#token=…  (unit sarathi-home)
```

Each page was then asked through its own API, with its key, the way the
browser asks:

* **Home**: four cards, each up, each saying something real (*"would ask
  ollama for qwen3.8-64k:latest"*, *"schedules: 0 active, 0 paused"*,
  the accounts connected, *"door serving; 3 agents, 1 people"*).
* **Dvara's page**, from its container, reached the door's by name:
  `{"door": {"reachable": true}}`, with the people, recent runs, files,
  and Samay found for the schedules. Its unit names no `--samay` (the
  process road's does); it finds the image's `samay` on its path.
* **Setu's page** answered on 127.0.0.1 and on the home network's
  address, and refused its API there without a key. A link made in the
  door's container for a person (`setu page-link`, `SETU_HOME` at that
  person's folder) opened from the network address once; the second
  try got *"that link has been used, or replaced by a newer one"*. The
  session it gave saw that person's folder and no other, and adding a
  site got *"that part of the page is your owner's"*.

Two things only the real run found, both fixed: the pages' units read
**failed** after every `sarathi down` ([note 03](03-two-containers-one-clock.md),
a stop is a stop), and a fresh `sarathi image` kept an older Chrome
than this machine's ([note 05](05-a-browser-in-the-image.md), the build
is told which Chrome is here).

## What is not here yet

* ~~**`setu serve` and `dvara page` as units**~~ Above.
* ~~**The Podman road, tried for real.**~~ Run, above.
