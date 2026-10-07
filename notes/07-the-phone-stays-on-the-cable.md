# 07 — the phone stays on the cable

*[Note 06](06-one-bookmark.md) put every program's page on one bookmark.
This note adds a sixth program, Sparsh, which has no page of its own and
can't follow the others into the containers yet.*

## What Sparsh is, to Sarathi

[Sparsh](https://github.com/kunwarmahen/sparsh) lets an agent work a
phone: an Android phone on a USB cable, or the emulator. It reads the
screen as a numbered list, taps by number, and holds a step that can't
be taken back (Send, Pay, Delete) for a person's yes. Yantra finds it at
start-up and gives the agent its tools.

To Sarathi it is one more sibling, found the same three ways (a path you
set, `PATH`, a checkout beside), asked the same question (`sparsh status
--json`, format `sparsh.status.v1`), and repeated in its own words:

```
sparsh      ~/Documents/ai/agent/sparsh/.venv/bin/sparsh  (beside)
            the hands: your phone, worked by number, with a yes before Send
            phone emulator-5554 (sdk_gphone64_x86_64), emulator-5556 (sdk_gphone64_x86_64) ready
```

That's this machine, with two emulators running. With none it says
*no phone attached (plug one in with USB debugging on, or start the
emulator)*; with a phone waiting for its yes, *attached but not ready:
R58M unauthorized*. It also names the apps your rules keep the agent
out of, and an iPhone's signature running out. It's **optional**, like
Dvara and Smritikosh: missing, it's reported and never fails `status`.

## Handed to the page, but not turned on

`sarathi up` starts Yantra's page with the Setu and Samay it found. For
Sparsh, `--sparsh PATH` would be wrong. In Yantra a path means **on**:
the phone tools even with no phone attached. Yantra's own rule (its
note 119) is the opposite: no phone at the start means no tools and no
prompt, until a phone is attached and the person presses **use this
phone**. NOTHING HAPPENS BY ITSELF, and Sarathi starting the page is not
the person saying to use a phone.

So Yantra learned one more form, `auto:PATH`: auto, with this program
instead of the one on `PATH`. Sarathi passes `--sparsh
auto:<the sparsh it found>`, and `sarathi status` asks Yantra with
`YANTRA_SPARSH=auto:<…>`, so Yantra's answer is about the Yantra `up`
starts.

## A card on the home page, pointing elsewhere

Sparsh has no page. The phone is watched from the **phone panel** on
Yantra's page: the phones, a picture of the screen beside the lines the
agent reads, and every step the agent took. So the home page's **Your
phone** card opens Yantra's page. It's only there when Sparsh was found.

## Not in the containers

On the Podman road there's no phone card, and the containers aren't
told about Sparsh. A container can't reach a phone on a USB cable
without passing the host's USB bus through, which hands the container
every device on it. The way in is wireless debugging: `adb pair` over
the network, with no cable and no USB passthrough. That is [note 08](08-the-phone-over-wifi.md).

## What the tests hold

* Sparsh's line in its own terms: ready, none attached, not ready; the
  apps kept out (`test_status.py`).
* Missing is optional, never a failure.
* `status` asks Yantra with `YANTRA_SPARSH=auto:<path>`; `up` starts
  the page with `--sparsh auto:<path>` (`test_up.py`).
* The phone card appears when Sparsh is found, opens Yantra's page, and
  is absent on the Podman road (`test_home.py`).

125 tests before, 133 after.
