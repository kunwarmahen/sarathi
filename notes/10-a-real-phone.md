# 10 — a real phone

*[Note 08](08-the-phone-over-wifi.md) reached the emulator over its
network port and left the case it was built for untried: a real phone
on the house Wi-Fi, the containers on their own network. This note is
that case, on a Nexus 6P running Android 8.1.*

## Old Android, no pairing page

`sarathi phone pair` follows Android 11's *Wireless debugging* page,
which an Android 8 phone doesn't have. The older road needs the cable
once: `adb tcpip 5555` makes the phone listen on its Wi-Fi address, and
the key allowed over the cable is the one it trusts (Sparsh's SETUP.md,
B4). Then the same command as for any phone:

```
$ sarathi phone 192.168.1.161:5555
already connected to 192.168.1.161:5555
the phone is on in /home/mahen/.config/sarathi/sarathi.toml, over Wi-Fi at 192.168.1.161:5555
  nobody in ~/dvara/actors.toml is marked `phone = true` yet: add it under your own [actor.…] so Dvara's agents may work the phone for you
next: `sarathi down && sarathi up` (or just `sarathi up`)
```

**THE CONTAINERS MUST START AGAIN, AND IT MATTERS WHICH KEY THEY HOLD.**
Tried before the restart, a container's adb reached the phone but made
a key of its own, since `~/.android` is mounted only once `[phone]` is
on. The phone answered `unauthorized` and put up *"Allow USB
debugging?"* for a key nobody meant to trust. Saying no to it was
right. After `sarathi down && sarathi up`, both the Yantra and Dvara
containers had this computer's key and were trusted at once:

```
== sarathi-yantra
SPARSH_CONNECT=192.168.1.161:5555
192.168.1.161:5555  Nexus_6P  device
```

## What it did from there

From inside Yantra's container, on `qwen3.8-64k:latest`, with no cable
in the picture:

```
sparsh: 10 tool(s); phone 192.168.1.161:5555 (Nexus_6P); ...
The Battery row in Settings says: "Battery — 98% - charging".
```

And a schedule through Samay and Dvara, the phone locked with a PIN,
its person on Telegram (Dvara's note 33 has the four runs): asked in the
chat, unlocked in time, and answered *"Battery — 99% · charging"*.
Along the way it found two things, both fixed where they belong:

* Locked, the phone's Wi-Fi dozes and adb's link goes stale; the first
  command said `error: closed` and the run was skipped as unreachable.
  Sparsh now reconnects once (its note 08).
* `minder`'s tool list left the phone out, so the run that had just
  been let in had no phone tool. Dvara now refuses such a run before
  asking anyone to unlock anything (its note 33).

## Not here yet

* ~~**`sarathi phone` doesn't look at the packages.**~~ It now says
  when the agent on Telegram can't use the phone, as well as when
  nobody is marked:

  ```
    minder, the agent on Telegram, can't use the phone: its [tools] in
    ~/dvara/agents/minder/agent.toml leaves out "mcp__sparsh__*" -- add it
    there (Sparsh still holds Send, Pay and Delete for your yes)
  ```
* ~~**The phone's screen in the containers.**~~ `[phone] awake` (and
  `sarathi phone --awake`) becomes Sparsh's `SPARSH_AWAKE` in both
  containers and on the plain-programs road, because Yantra's `.env`
  never reaches a container. Sparsh keeps the screen on while an agent
  works (its note 09); a rename from Telegram had stopped at the lock
  screen.
* **The image carries the Sparsh and Dvara it was built with.** Both
  fixes above reach the containers at the next `sarathi image`.
