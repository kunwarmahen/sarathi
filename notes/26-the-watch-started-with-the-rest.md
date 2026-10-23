# 26 — The watch, started with the rest

Prahari is the newest sibling. It watches for what you're waiting for (a
price under a line, a mail from someone, a phone's notification) with no
model, and wakes your agent only when it happens. Like every sibling it
stands alone (`prahari serve`), and like every sibling, wiring it to the
others by hand means the same settings copied into several places and
wrong in one. Sarathi does the wiring.

## Where it sits in `up`

Between the clock and the page, the same place Samay has, and for the
same reason ([note 02](02-one-file-two-processes.md)): Yantra's page
and Dvara each ask *is it running?* once, when they start, and tell the
model what they heard for the whole session. Started after them,
Prahari would be "not running" all day.

```
samay      up at http://127.0.0.1:8780/#token=…
prahari    up at http://127.0.0.1:8782/#token=…
yantra     up at http://127.0.0.1:8321/
```

What each piece is given:

* **Prahari**: `PRAHARI_YANTRA`, the same Yantra command Samay's runs
  get (with your Smritikosh server when your memories are there), and
  the door's address, token and owner under Prahari's own names. Those
  are the three Samay already gets, renamed, so they can't drift apart.
  What a watch sees reaches you the way a schedule's answer does: in your
  chat.
* **Yantra's page**: `--prahari <it>`, so the agent there can offer a
  watch.
* **Dvara**: `--prahari <it>`, and `--prahari-for` only when
  `[prahari] people` names some.

## Yours alone

(Since Dvara's notes/56 and Prahari's notes/02 this is no longer so: a
watch's look goes to Dvara as its person, with their own accounts, so
`up` gives watches to everyone, and `[prahari] people` narrows it. The
section below is why it once was.)

That last flag was the one decision in this note. A schedule run through
Dvara is a Dvara turn, with the person's own Setu folder. A watch's look
is not: it is `yantra --call` with this computer's accounts. If anybody
in the house could make a watch, they could have Prahari read your mail
on their behalf. So Dvara gives Prahari's tools to one person, named,
and Sarathi names you (Dvara's notes/55). The people in your house keep
their schedules; watches are yours until a look can run as them.

## The inlet, on the house's network

Prahari's page carries its **inlet**: an address and a key that can only
knock, for things that can tell Prahari themselves. An Android phone's
MacroDroid sends a notification there the moment it arrives. So with
`[house]`, Prahari's port is published on the house address like every
page, and the firewall line `up` prints includes 8782. Its address says
the house's name (`PRAHARI_PUBLIC_URL`), so the address the page shows
for MacroDroid is one the phone can open.

## The inlet from outside

Gmail's push, and any webhook on the internet, need the inlet reachable
from outside the house. `[prahari]` takes two keys for that:

```toml
[prahari]
inlet_port = 8783
public_url = "https://beast.tail1234.ts.net:8443"
```

`inlet_port` makes `up` start Prahari with `--inlet-port`: a second
listener with the inlet ALONE, no page and no API. On the program road
it's on 127.0.0.1. On the Podman road the container publishes it on
`127.0.0.1:8783` only, never on the house address and never in the
firewall line, because Tailscale Funnel reaches it on this computer.
Prahari's `deploy/public-inlet-tailscale.sh` makes the public name.
You run it yourself, because it signs in to your Tailscale account.
`public_url` passes that name as `PRAHARI_INLET_PUBLIC_URL`, so
Prahari's page and your agent's `inlet_address` show it. A `public_url`
without an `inlet_port` is refused: the public road reaches the inlet
alone, or nothing. All three keys are on the settings page too.

## Optional, all the way down

Prahari is new, and a reader who cloned Sarathi last month hasn't got
it. So everything above happens only when Prahari is on this computer:
found the way `sarathi status` finds every sibling (`SARATHI_PRAHARI`,
`PATH`, or a checkout beside Sarathi's). One function, `watching()`,
answers that for both roads. Without Prahari there's no piece, no unit,
no flag to Yantra or Dvara, no firewall port and no card on the home
page. `sarathi status` lists it as optional, and the image is built
without it, the way it is built without Dvara or Sparsh.
`[prahari] on = false` turns it off when it is there; then the page is
told `--no-prahari`, so a Yantra that would otherwise find it on `PATH`
doesn't offer it.

One more Podman detail: `~/.prahari` is mounted into every container,
like `~/.samay`. Prahari holds a lock there while it watches, and
Yantra's page and Dvara, each in their own container, see that lock
when they ask whether it's running. `up` creates every data folder
first, so an empty one is fine.

## What this was checked against

Offline: `tests/test_prahari.py`. It covers the order and the wiring on
the plain-programs road, the unit and the door's flags on Podman, the
inlet on the house address, and "not installed is nothing at all" on
both roads. Live, read-only, against this computer's own `sarathi.toml`:
`sarathi status` found Prahari beside the others, and the units `up`
would write gave Prahari a container on 8782 (and on 192.168.1.44:8782),
the same Yantra command and memory server as Samay, and Dvara
`--prahari /usr/local/bin/prahari --prahari-for owner`. `up` itself
wasn't run. It restarts the containers you use every day, and the image
needs rebuilding first (`sarathi image`), so that step is yours.
