# 35 — Routines in the house

Vidhi keeps routines a person drew once (Vidhi's notes/01): steps that
fetch side by side, ask the model, ask the person yes or no, and tell
them. Started on its own, it runs on one computer for one person. In the
house it has to be started with the rest, reach everyone's chats, and be
startable from Samay's, Prahari's and Dvara's containers, each of which
runs in a box of its own.

Continues [26 — the watch, started with the rest](26-the-watch-started-with-the-rest.md).

## What `up` does with it

`[vidhi]` (`on`, `port`, default 8786) says whether. On, and Vidhi found
beside the other checkouts:

* **Its own container, `sarathi-vidhi`** (or a plain `vidhi serve` on the
  process road), told the door's address, token and owner in its own
  names (`VIDHI_DVARA_URL`, `VIDHI_DVARA_TOKEN`, `VIDHI_DVARA_ACTOR`), so
  a routine's message and its questions reach the person. It gets the
  model's key: an `ask` step is a model call.
* **ITS FOLDER IS IN EVERY CONTAINER.** `~/.vidhi` is mounted beside
  `~/.samay` and `~/.prahari` in all of them. Starting a run is adding a
  row there (`vidhi start`), so Samay's container starts a scheduled
  routine and Prahari's a watch's routine without an address or a token.
* **Dvara gets `--vidhi`**: `/routines` on every channel, a run's
  question answered with Yes and No, and each person's agent able to run
  or install a routine as them (Dvara's notes/83).
* **Yantra's page gets `--vidhi`**, and `--no-vidhi` when it's off.
* **The home page** has its card; **the doctor** says when it isn't
  running, and when a run is waiting for an answer; **Settings** switches
  it and moves its port; **`sarathi backup`** takes its folder (`vidhi
  keeps`).
* **With `[house]`**, its page is on the house address too (a question
  can be answered there from a phone), and the firewall line names 8786.
* **The image** gains Vidhi and `openssh-client`: `ssh-keygen` checks the
  reviewer's signature on a routine from a marketplace.

OPTIONAL, LIKE PRAHARI. With no Vidhi checkout and nothing on `PATH`,
nothing about it is started, published, passed or carded.

A notice's buttons on the home page (a routine's Yes and No) go to the
agent chosen in the chat, since a notice comes from no agent.

## A marketplace of the house's own

`[vidhi] market_port = 8787` runs Vidhi's marketplace ALONE: `vidhi
market serve` in its own container, `sarathi-vidhi-market`, published on
127.0.0.1 only, keeping `~/.vidhi-market` (mounted, and named by `vidhi
keeps` so a backup takes it). Only `/market/` is served there, never
Vidhi's page, so Vidhi's `deploy/public-market-tailscale.sh` can put that
port on the internet through Tailscale Funnel (10000), the way Prahari's
inlet goes out on 8443. `market_url` is the marketplace the house's Vidhi
fetches from (`VIDHI_MARKET`): its public address, and the address the
marketplace's own page tells people (`VIDHI_MARKET_PUBLIC_URL`). With a
`market_port` and no `market_url`, the house fetches from its own,
inside the container network. Both are on Settings; the plain-programs
road runs the same marketplace as a process.

## Not here

* **A run seen from the home page.** Its card opens Vidhi's own page,
  where runs are listed step by step.
