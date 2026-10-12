# 17 — the phone, from the page

*[Note 08](08-the-phone-over-wifi.md) gave the containers your phone
over Wi-Fi, and [note 10](10-a-real-phone.md) reached a real Nexus 6P
that way: plug it in once, `adb tcpip 5555`, `sarathi phone ADDRESS`.
[Note 16](16-every-setting-from-the-page.md) put every setting on the
home page, the phone's address among them. Neither survived the phone
being switched off and on.*

## The problem, as you would meet it

You switch the phone off at night and on in the morning. Yantra's phone
panel says *"No phone yet"*. The phone is on your desk, and
`sparsh devices` on the computer lists it. The panel isn't wrong about
what it sees. Yantra runs in a container, which has no USB cable, and
it was trying the Wi-Fi address you saved. Two things had changed:

* the phone stopped listening over Wi-Fi when it restarted (`adb tcpip`
  doesn't last), and
* its address moved, `.161` to `.160`.

The fix was three adb commands, typed in a terminal, and nothing on
the page could run them. **Settings → Sarathi** had a box for the
address, but typing in the new one wouldn't turn the listening back on,
and nothing told you the address had moved.

## The cable, as one step

Sparsh does the three steps itself now: `sparsh tcpip` reads the
phone's Wi-Fi address over the cable, tells it to listen, and connects
(Sparsh's note 11). Sarathi only passes it on:

```
$ sarathi phone tcpip
the phone listens over Wi-Fi at 192.168.1.160:5555
already connected to 192.168.1.160:5555
the phone is on in /home/mahen/.config/sarathi/sarathi.toml, over Wi-Fi at 192.168.1.160:5555
  the same address as before: nothing to restart, Sparsh reconnects by itself
```

That is the real Nexus 6P on Android 8.1, on a USB cable. When the
address does move, the line is `next: sarathi down && sarathi up`
instead. The containers get the address when they start, so only a new
address needs a restart. For the same address, each container's Sparsh
connects again the next time it looks for phones.

* **WIRING, NOT A PHONE.** Sarathi keeps no adb logic. It runs
  `sparsh tcpip --json`, reads `address` and `connected`, and saves the
  address only if the phone answered there, the same rule
  `sarathi phone ADDRESS` already followed. A phone that was told to
  listen but didn't answer is reported, and nothing is saved.
* **ANY ANDROID.** Pairing over *Wireless debugging* (Android 11 and
  later) needs the phone's screen, a code and two addresses. The cable
  needs none of that, so it's offered first, for every phone.

## On the page

**Settings → Sarathi** has its own card for the phone, **Your phone**:

* *Your phone, through Sparsh*, its Wi-Fi address and its screen while
  an agent works it, saved with the rest of the tab;
* **Turn on Wi-Fi from the cable**: `sparsh tcpip`, and the address it
  found saved;
* **Connect**: the address typed in, tried, then saved only if it
  answers;
* *No cable? Android 11 and newer: pair once*: the pairing address and
  the six digits, then **Pair**.

A step that saved a new address shows **Apply**, which runs
`sarathi up`. The same address says there's nothing to restart.

* **THE PAGE RUNS WHERE THE CABLE IS.** The home page is a user service
  on this computer, not a container (podman.py), so it can see the USB
  cable and the containers can't. That's why the buttons are on this
  page and not on Yantra's. Yantra's panel only watches.
* **THE OWNER'S ALONE.** `POST /api/settings/phone` is under Settings,
  so a person signed in gets 403, the same as every other setting.

The receipt, from the page running on this computer:

```
POST /api/settings/phone {"do": "tcpip"}
{"said": "the phone listens over Wi-Fi at 192.168.1.160:5555. Same address as before:
 nothing to restart. Yantra's phone panel finds it on its next look.", "restart": false}

POST /api/settings/phone {"do": "connect", "address": "192.168.1.161:5555"}
{"detail": "failed to connect to '192.168.1.161:5555': No route to host -- not saved.
 Is the phone listening? Turn it on from the cable, or check its Wireless debugging page"}
```

## Yantra's panel says why

The panel's *"No phone yet"* came from an empty list. Sparsh now lists
a named address that doesn't answer as offline, with the fix (Sparsh's
note 11), and Yantra's panel shows that sentence under the phone:
*"not answering over Wi-Fi -- a phone that restarted stops listening:
plug it in and run `sparsh tcpip` (its address may have changed too)"*.
The containers get it with the next `sarathi image`.

## What the tests hold

* `test_phone.py`: `sarathi phone tcpip` saves the address the phone on
  the cable now has; with no phone on a cable it saves nothing and says
  why; a phone told to listen that didn't answer saves nothing; the same
  address again asks for no restart.
* `test_settings_page.py`: the cable's address is saved and **Apply** is
  asked; the same address again needs none; an address that doesn't
  answer is said and not saved; pairing saves nothing and wants both
  numbers; a person signed in can't press any of it, and Sparsh is never
  run for them.

## What is not here yet

* The address moving is up to your router. Give the phone a fixed
  address there (a DHCP reservation, by its MAC), and after a restart
  only **Turn on Wi-Fi from the cable** is left to do.
* The cable step can't be done without the cable. A phone that
  restarted in another room stays offline until it's plugged in, or, on
  Android 11 and later, until Wireless debugging is turned back on.
