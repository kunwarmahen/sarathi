# 08 — the phone over Wi-Fi

*[Note 07](07-the-phone-stays-on-the-cable.md) found Sparsh and handed it
to Yantra's page, but left the containers without a phone: a container
can't reach a USB cable. This note gets the phone to them the way
another computer would reach it, over the network.*

## Why not the cable

Podman can pass a USB device into a container, but adb finds a phone by
scanning the USB bus, so in practice that means the bus, and every
device on it: keyboards, disks, security keys. That's a lot to hand a
container for one phone. And a cable ties the phone to the machine's
desk.

Android 11 and later have **wireless debugging**: adb over the network,
paired once with a six-digit code, encrypted. A container reaches the
house network already (Ollama's address proves it every day), so the
phone can be one more thing on it.

## One switch, `[phone]`

```toml
[phone]
on = true
address = "192.168.1.23:41234"   # its Wireless debugging address
```

`sarathi phone` writes it. Three forms, because three moments need the
phone in front of you:

* `sarathi phone pair ADDRESS CODE`: once per computer, the address and
  code from the phone's *Pair device with pairing code* screen.
* `sarathi phone ADDRESS`: the address on the Wireless debugging page
  itself. It's connected to first, and **a wrong address is said, not
  saved**, so `up` never starts containers pointed at nothing.
* `sarathi phone` alone: a phone on a cable (the process road). On the
  podman road it says a container can't reach that.

**WIRING, NOT A PHONE.** Pairing and connecting run the Sparsh `sarathi
status` found (`sparsh pair`, `sparsh connect`). Sarathi only writes the
setting.

## What the containers get

With `[phone]` on:

* **adb in the image.** Google's platform-tools on amd64, because
  wireless debugging needs adb 30 or newer and Debian's is 29. Elsewhere
  Debian's adb, which still reaches a phone put on the network with
  `adb tcpip`. And Sparsh beside the other programs.
* **`~/.android`, mounted at the same path.** Pairing teaches the phone
  this computer's adb key, which lives there. With the same folder, the
  containers present the same key. **ONE KEY, NOTHING PAIRED TWICE.**
* **`~/.sparsh`, mounted too.** The person's rules (`never`, `ask`) live
  there. Without it, a container would run with no rules at all: its
  home is a scratch folder emptied at every start.
* **`SPARSH_CONNECT=<address>`.** Sparsh connects to that address
  whenever it looks for phones and adb has forgotten it, so a container
  started fresh finds the phone again by itself (Sparsh's own change).
* **The page** gets `--sparsh auto:/usr/local/bin/sparsh`: no phone
  answering at the start still means no tools until the person says to
  use one. **The door** gets `--sparsh`, for the one person its actors
  file marks `phone = true`.

With `[phone]` off, no unit mentions the phone at all. The home page's
**Your phone** card shows on the podman road once there's an address.
On the process road, the page and the door get the same address, and
the door the same `--sparsh`.

## Live receipt

The rebuilt image, a container started the way the units start one
(running as you, home a scratch folder, `~/.android` and `~/.sparsh`
mounted), with `SPARSH_CONNECT` pointed at the emulator's network port.
Host networking stood in for the house network, and the container ran
its own adb server on another port so it couldn't borrow this
machine's:

```
Android Debug Bridge version 1.0.41
Version 37.0.1-15733141
127.0.0.1:5555  sdk_gphone64_x86_64  device
...
App: com.google.android.apps.nexuslauncher
1 list "workspace" [scroll]
2 item "At a glance" [long-press]
```

The container's adb connected by itself, was trusted at once (the
mounted key; no "allow USB debugging?" on the phone), and Sparsh read
the screen.

Not yet: a real phone over real Wi-Fi, with the containers on their own
network. The emulator listens on this machine's loopback, which a
container on that network can't reach. A phone on the house network
is the case this was built for.

## What the tests hold

`tests/test_phone.py`: the setting reads back as written, and an address
that isn't one stops everything; with no `[phone]`, no unit mentions it;
with it, the page reaches the address with this computer's key and the
person's rules, and never a USB device; the door gets `--sparsh`; the
image takes Sparsh; the home card needs the address on the podman road;
the process road gets the address too; `sarathi phone` saves an address
that answers, refuses one that doesn't, pairs without turning anything
on, warns about a cable on the podman road, turns off, and says when
nobody in the door's actors file is marked. 133 tests before, 147 after.
