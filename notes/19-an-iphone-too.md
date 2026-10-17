# 19 — An iPhone too

*Sparsh drives an iPhone through WebDriverAgent, an app on the phone
that answers HTTP, and it has now read and tapped a real one: an iPhone
17 on iOS 26 (Sparsh's notes/12). Sarathi still only knew an Android:
`[phone]` had a Wi-Fi address and nothing else, so an iPhone could be
used from a terminal with `SPARSH_WDA` set, and from nothing Sarathi
started.*

## One more address, and still one phone

```bash
sarathi phone iphone                          # WebDriverAgent at http://127.0.0.1:8100
sarathi phone iphone http://192.168.1.40:8100 # or wherever it answers
```

An iPhone is an address too: the one WebDriverAgent answers at. It is
saved as `[phone] wda`, and handed to Sparsh as `SPARSH_WDA`, on both
roads and in `sarathi status`.

ONE PHONE. Sparsh takes an iPhone it is told about ahead of any Android
it finds. A `[phone]` with both an Android address and an iPhone would
quietly mean the iPhone, and whoever wrote the Android address would
wonder why it's ignored. So the file holds one or the other, and says so
when it holds both:

```
sarathi.toml: phone.address (an Android) and phone.wda (an iPhone) are
two phones; Sarathi gives its agents one -- keep one of them
```

`sarathi phone iphone` replaces the Android; `sarathi phone ADDRESS` or
`tcpip` replaces the iPhone. The Settings page's **Your phone** card has
the same step under *An iPhone instead*: **Use the iPhone**.

ASKED BEFORE IT'S SAVED. As with an Android address, a wrong one is said
now rather than at `up`. Sarathi asks Sparsh's own status with
`SPARSH_WDA` set, and saves only when Sparsh lists the iPhone as ready:

```
$ sarathi phone iphone
the iPhone answers at http://127.0.0.1:8100
the iPhone is on in ~/.config/sarathi/sarathi.toml, in place of the Android at 192.168.1.160:5555
  the containers reach it at http://host.containers.internal:8100
  keep the iPhone unlocked while an agent works it, and WebDriverAgent running; it is signed for 7 days with a free Apple ID
next: `sarathi down && sarathi up` (or just `sarathi up`)
```

With nothing answering it names the one step that's missing:

```
error: nothing answers at http://127.0.0.1:8100: start WebDriverAgent with the iPhone on
this computer's cable (in Sparsh's folder: PREFIX=com.you.sparsh
scripts/start-wda-from-linux.sh), leave it running, and try again -- not saved
```

## The containers reach it at the host

WebDriverAgent runs on the iPhone. Sparsh's start script forwards it to
this computer's port 8100 over the cable. A container's `127.0.0.1` is
the container itself, so the units say `host.containers.internal`
instead, the name Podman gives this computer, as they already do for
Ollama. That only works if the forward listens beyond loopback. It
does: go-ios's `ios forward` listens on every address (`*:8100` in
`ss -ltn`). Run as the real image on Sarathi's network:

```
$ podman run --rm --network sarathi -e SPARSH_WDA=http://host.containers.internal:8100 \
    localhost/sarathi:latest sparsh look
App: com.apple.Preferences
1 button "Settings" [tap]
2 text "Wi-Fi"
3 button "Edit" [tap]
4 list [scroll]
...
7 switch "Wi‑Fi" [tap, on]
```

No device is handed to a container and no USB is passed through, the
same rule an Android follows (note 08).

## What stays the person's

WebDriverAgent itself. It is built and signed on a Mac once a week
(free Apple ID), and started on this computer by Sparsh's
`scripts/start-wda-from-linux.sh`, which needs the iPhone on the cable,
`sudo` for iOS 17's developer tunnel, and a terminal left open. That is
not a thing `up` can do quietly, so it isn't one: Sarathi checks that
WebDriverAgent answers, says how to start it when it doesn't, and
`sarathi status` names the signature's last days (Sparsh's `wda` note).

## What the tests hold

`tests/test_phone.py`: an iPhone reads back as written; both phones at
once, or an address that isn't one, stop everything; `SPARSH_WDA`
reaches the plain programs as written and both containers at
`host.containers.internal`, with no Android address beside it; the home
page's **Your phone** card shows for an iPhone on the Podman road;
`sarathi phone iphone` saves only what answers, in place of the
Android, and an Android address afterwards takes the iPhone's place;
`sarathi status` asks Sparsh about the iPhone it gives out.
`tests/test_settings_page.py`: **Use the iPhone** saves it once it
answers and asks for Apply, and says how to start WebDriverAgent when
it doesn't.

## What is not here yet

* An agent's task on the iPhone through Dvara on Telegram, and a
  schedule on it. An iPhone says only whether it's locked; Dvara's
  checks before a scheduled step take that as the answer (Dvara's
  notes/33).
* WebDriverAgent started by `up`. Its tunnel needs root, so it stays
  Sparsh's script, in a terminal.
* `[phone] awake` on an iPhone. Sparsh can't change an iPhone's
  Auto-Lock, so the phone has to be kept unlocked by its person.
