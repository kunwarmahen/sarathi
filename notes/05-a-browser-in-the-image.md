# 05 — a browser in the image

*[Note 03](03-two-containers-one-clock.md) put the pieces in containers
and left out a browser. [Note 04](04-a-door-for-the-household.md) found
the image had no bubblewrap either. This note puts both in, and says
what it took for each to actually work in there.*

## The problem, as you would meet it

On the Podman road, three things didn't work:

* **Amazon and X.** Setu signs in to them in a browser, and their tools
  drive one. The page listed their tools; every call failed.
* **The streamed window.** dvara's people sign in to Amazon from their
  phone through a browser on this computer (dvara's note 22). On this
  road `up` could only say the window needed a browser the image didn't
  have.
* **The wall around a connector.** Without bubblewrap, Setu's connectors
  ran unwalled. They still held no key, since Setu makes every request,
  but they had the network and could read your files, and the card said
  so.

## Chrome, at the path your desktop has it

The question was Chrome or Chromium, and it had one deciding fact. Setu
records which browser wrote a profile and opens it with that browser,
and Chrome refuses a profile written by a newer version of itself. On
this machine every browser-road connection records
`/usr/bin/google-chrome`. So **THE IMAGE HAS GOOGLE CHROME AT
`/usr/bin/google-chrome`**: the path in the record resolves inside the
container unchanged, to the same browser.

Debian's Chromium would open a Chrome profile only if it happened to be
the same version or newer, and the path in the record wouldn't exist.
Google ships Chrome for amd64 only, so elsewhere the image gets Debian's
Chromium, and a profile from a desktop's Chrome may need signing in to
again. That road has been built but not run on a real arm64 machine
(below).

**AN ARM64 BUILD, UNDER EMULATION.** On an amd64 machine with
`qemu-user-static`, the same staged sources built for arm64
(`podman build --arch arm64`, 20 minutes, 1.35 GB) with no errors. Inside
it, `samay`, `sparsh`, `yantra status --json` and `setu serve` all ran;
the page answered after 34 seconds, which is the emulator's slowness.
The browser is Debian's Chromium 154, and adb is Debian's 34.0.5 with
`pair`. Two things can't be judged under emulation, and both need a
real Raspberry Pi:
bubblewrap ("Creating new namespace failed": qemu's user mode doesn't
make namespaces, and the same call walls a connector off in the amd64
image) and Chromium itself (qemu stops it with "uncaught target signal
5" before it draws a page).

That build left something behind. Pulling arm64 bases put them under
the usual names, `python:3.12-slim` and `debian:trixie-slim`, in place
of the amd64 ones, and the next plain `sarathi image` built on them: an
arm64 Sarathi on an amd64 machine, every service run through qemu.
`sarathi up` said the door and the page "did not come up"; they had,
three minutes later, and the page fell over once when `setu status
--json` took longer than its 15 seconds. So **`sarathi image` names
this machine's platform on every build** (`--platform linux/amd64`
here), and podman pulls the matching base when the tag holds the wrong
one:

```
Trying to pull docker.io/library/python:3.12-slim...
...
$ podman image inspect localhost/sarathi:latest --format '{{.Architecture}}'
amd64
```

**NEWER HERE, REFUSED THERE.** Your desktop's Chrome updates itself; the
image's is whatever was current when it was built. When the desktop's
gets ahead, a profile signed in to here won't open in there, so `up`
compares the two and says so:

```
browser: this machine has Chrome 155.0.1.2, the image 154.0.8037.97; a profile
signed in to here won't open in there until `sarathi image` builds it again
```

`sarathi image` ends by saying which browser it put in.

**THE BUILD IS TOLD WHICH CHROME IS HERE.** The first time that note
appeared, `sarathi image` didn't make it go away: the Chrome step's text
hadn't changed, so the build took it from the cache and put 154 back in.
The step now starts from `ARG HOST_BROWSER`, which `sarathi image` sets
to this machine's Chrome version. A new version here re-runs the step
and fetches the current Chrome. Otherwise the cached step is kept, so
a rebuild with nothing new still takes seconds.

The rest of what a browser needs:

* **Xvfb.** X's site rules ask for a real window, because headless is
  what such sites look for. Yantra starts an invisible screen when there
  is no display, and the image now has one to start.
* **Fonts**, so a page has its letters and a screenshot can be read.
* **Playwright's Python side** (Yantra's `browse` extra), pointed at the
  image's Chrome with `YANTRA_BROWSER_EXECUTABLE`. Playwright's own
  browser isn't downloaded: a real browser is an ordinary client to a
  site, and Playwright's build announces itself.
* **A 1 GB `/dev/shm`** (`ShmSize=1g`). Chrome keeps its pages there,
  and Podman's 64 MB isn't enough for a heavy one.

## The window, published

The door's container runs the window. Setu listens on every address
*inside* the container (`SETU_WINDOW_HOST=0.0.0.0`), and the unit
publishes that port on `window_host` alone. The port is fixed
(`window_port`, else 8790), because a port has to be known to be
published. The link says `window_url`, or `http://window_host:port`:
never the container's own address, which no phone can reach.

`window_host = "0.0.0.0"` without a `window_url` stops `up` with the
reason, since that link would point nowhere.

**SETU'S PAGE HAS A WINDOW OF ITS OWN.** Amazon connected from Setu's page,
rather than the chat, starts its own sign-in in Setu's container, and that
container had no window settings at all. Its link said `127.0.0.1`,
which inside a container is the container. A probe showed what made this
matter for everyone: a request from this computer's browser reaches a
container from `10.89.9.34`, not `127.0.0.1`, so Setu's page counts you as
another device too and always picks the streamed window. (That's the
right call, since a window "here" would open on the container's screen,
which nobody sees.) So Setu's unit now publishes a window of its own on
the port after the door's (8791), on `window_host`, or on `127.0.0.1`
when there is none. On the plain-programs road `setu serve` gets
`SETU_WINDOW_HOST` from `window_host` and takes any free port, as the
door does. A port something else holds is said before Setu starts.

Live, on the owner's machine: a throwaway person claimed their link from
`192.168.1.44:8775` and pressed Connect on Amazon. The sign-in said
`{"event": "link", "url": "http://192.168.1.44:8791/w/…"}`. Chrome opened
it (`{"event": "opened"}`), a second device got *"This sign-in is
already open on another device."*, and Cancel ended it with nothing
connected.

## The wall, and the probe that lied

bubblewrap went into the image, and Setu said its connectors were
walled off. Then a real connector in the page's container failed to
start:

```
bwrap: Can't mount proc on /proc: Operation not permitted
```

**SETU'S PROBE TRIED LESS THAN THE REAL THING.** It asked whether
bubblewrap could make a sandbox with no network, and in a rootless
container it can. The real sandbox also mounts a fresh `/proc` in a new
pid namespace, and the kernel refuses that while Podman hides parts of
the container's `/proc`. So Setu claimed a wall and every connector
failed: worse than no wall at all. Setu's probe now tries the same
mounts and namespaces every connector gets (Setu `87061a6`), so where
the wall can't be built it says so, and the connector runs as it would
without bubblewrap.

**THE UNITS UNMASK `/proc`** (`Unmask=/proc/*`), so the wall can be
built here. The container runs as you, so what that shows is what your
own account can already read on this machine. Tried three ways:

```
[default]                      bwrap: Can't mount proc on /proc: Operation not permitted
[--security-opt unmask=ALL]    ok
[--security-opt unmask=/proc/*] ok
```

Chrome's own sandbox needed nothing: it starts inside the container as
it is, with no `--no-sandbox`.

## A home Chrome can write to

The first `/connect amazon` from a real phone, through the door's unit,
failed: `the browser did not answer Target.createTarget`. Chrome had
died as it started. Every test above had run with `HOME=/tmp`. The units
run with `HOME` at your real home's path, which Setu's records need, and
inside a container that path is a folder Podman made only to hold the
mounts: owned by root, not writable. Chrome couldn't make its crash
reporter's folder under `~/.config`, and stopped:

```
mkdir: cannot create directory '/home/mahen/.local/share/applications': Permission denied
chrome_crashpad_handler: --database is required
Trace/breakpoint trap
```

**HOME IS A SCRATCH FILESYSTEM OF YOUR OWN** (`Tmpfs=<home>:rw,mode=0700,U`),
emptied at each start, with the data folders still mounted inside it at
their paths. Same paths, same files; Chrome gets somewhere to write. The
page's browser tools had the same problem and get the same fix. After it,
in the door's container:

```
drwx------ 7 mahen mahen 140 Oct  6 16:56 /home/mahen
Target.createTarget answered: True
```

## A network that didn't come back

The first `up` of this work failed with all three units saying
`unable to find network with name or ID sarathi`. An earlier `down
--remove` had removed the network, but the unit that makes it is a
one-shot systemd keeps as "active (exited)", so systemd never ran it
again. `down --remove` now stops that service before removing the
network, and `up` restarts it if the network is missing. That second
half is what fixed this machine.

## Live receipt

`sarathi image` from dvara `435c053`, yantra `2ebdf87`, setu `87061a6`,
samay `d6f669d`:

```
browser in the image: Google Chrome 154.0.8037.97
```

The same version as this desktop's. The image is 1.28 GB, most of it
the browser. Then, piece by piece.

**A profile your desktop wrote opens signed in.** A copy of the Amazon
profile this desktop's Chrome signed in to, opened by the container's
Chrome, against an empty profile (only whether Amazon's greeting asks
you to sign in is printed):

```
amazon  says "Hello, sign in": False   (page 1749906 bytes)
empty   says "Hello, sign in": True    (page 1113476 bytes)
```

And through Yantra's own browser path, Playwright driving the image's
Chrome:

```
browser: 154.0.8037.97 | "Hello, sign in" shown: False
```

**The streamed window.** `setu connect amazon --remote` in a container
with the door's settings, played from the host as the phone: the page,
its size, a frame of Amazon's real sign-in page at phone size, a second
device refused, then "done" without signing in:

```
page: 200
size: 200
frame: 16023 bytes
a second device: HTTP Error 403: Forbidden
done: 200
{"event": "error", "message": "the window closed, but Amazon has not signed you in there
(none of at-* is set). Nothing was saved; …"}
```

**The whole road.** `sarathi up` with the door on and
`window_host = "127.0.0.1"`, on scratch settings:

```
clock  up at http://127.0.0.1:8781/#token=…  (unit sarathi-clock)
door   up at http://127.0.0.1:8766/  (unit sarathi-door)
page   up at http://127.0.0.1:8421/  (unit sarathi-page)
```

Inside the door's container:

```
shm             1.0G     0  1.0G   0% /dev/shm
SETU_WINDOW_HOST=0.0.0.0
SETU_WINDOW_URL=http://127.0.0.1:8790
SETU_WINDOW_PORT=8790
sandbox: True
Google Chrome 154.0.8037.97
8765/tcp -> 127.0.0.1:8766
8790/tcp -> 127.0.0.1:8790
```

A real Gmail connector, started in the page's container the way the
page starts it:

```
initialize: {'name': 'setu-gmail', 'version': '0.1.0'}
tools: 7 ['search_threads', 'get_thread', 'get_message', 'list_labels']
under bubblewrap: True | no network: True
a real call through Setu: ok
```

`sarathi down --remove` left no units, containers or network, and the
network's service `inactive`.

## What was deliberately not built

* **Chromium everywhere**, for one image on every architecture. It
  would have made every profile this desktop already has unopenable in
  the container. The architecture that can't have Chrome gets Chromium,
  and only that one pays.
* **Pinning a Chrome version.** The image takes Chrome stable as of the
  build, like the desktop does. What matters is the order of the two,
  and `up` says when it's wrong.
* **`--no-sandbox` for Chrome**, or a looser seccomp. Neither was needed.

## What is not here yet

* ~~**A person signing in to Amazon from a phone through the door's
  window, in the containers.**~~ Done from a real phone on home Wi-Fi:
  `/connect amazon` to the bot, the window, email, password, connected.
  It took four fixes no scripted phone had found: the Google client file
  mounted (Gmail, the step before), a writable home for Chrome (above),
  typed text focusing the page's empty box, and an Enter that presses
  the form's own button when Amazon's page ignores the key (Setu).
* **X through the window** is turned away by X itself (*"we have
  temporarily limited your access"*). Signing in to X at the computer
  instead, in an ordinary window, may get round it; not tried.
* **Yantra's site tools reading Amazon's orders** in the containers,
  with the sign-in from the phone. Not tried yet: ask the page *"what
  were my last three Amazon orders?"*.
* **One place to find every page**: [note 06](06-one-bookmark.md),
  `sarathi home`.
* **Later:** a phone over Tailscale, and the Chromium road on arm64 run
  on a real Raspberry Pi. It builds and its programs start (above);
  Chromium and the wall are what's left to see.

*The pieces here are called by their old names (clock, door, page, owner, home); they go by their projects' names now ([note 09](09-each-by-its-own-name.md)).*
