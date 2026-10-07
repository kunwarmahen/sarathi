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

## What is not here yet

* **`setu serve` and `dvara page` as units**, started by `sarathi up`,
  and the home page with them, its address printed by `up` and `status`.
  Until then each is started by hand, and its card says how.
