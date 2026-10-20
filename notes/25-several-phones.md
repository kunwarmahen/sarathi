# Several phones, written down once

`[phone]` used to hold one phone: an Android's Wi-Fi `address`, an
iPhone's `wda`, or both, with whichever answered being the phone
([note 20](20-whichever-phone-is-plugged-in.md)). Two that answered at
once were refused. Sparsh can now serve several phones by name
([its note 18](https://github.com/kunwarmahen/sparsh/blob/main/notes/18-several-phones.md)),
and Dvara gives each person their own
([its note 54](https://github.com/kunwarmahen/dvara/blob/main/notes/54-each-phone-ones.md)).
What's left for Sarathi is the house's list of phones: what each is
called and how it's reached.

## A table per phone

```toml
[phone]
on = true

[phone.nexus]
serial = "84B7N16128001616"
awake = "always"

[phone.pixel]
serial = "emulator-5554"
```

Each `[phone.NAME]` has exactly one of `serial` (an Android adb sees on
a cable, or the emulator), `address` (one over Wi-Fi) or `wda` (an
iPhone), plus its own `awake`. The `serial` is new. One unnamed phone on
the cable never needed writing down, because it was the phone. Two
phones on cables do need telling apart, and a name has to point at
something. Both roads hand them to Sparsh as `SPARSH_PHONES`:

```
SPARSH_PHONES=nexus=84B7N16128001616,pixel=emulator-5554
SPARSH_AWAKE=nexus=always
```

Inside a container an iPhone's `127.0.0.1` becomes
`host.containers.internal`, as `SPARSH_WDA` already did. A phone on
this computer's cable reaches the containers through `sarathi-adb`, the
same way the single cable phone did.

**WHAT PHONES EXIST IS SAID HERE; WHOSE THEY ARE, IN DVARA.** Ownership
lives in Dvara's actors file (`phones = ["nexus"]`) and nowhere else.
**Settings → People** shows a box per phone under each person, and a
person with `phone = true` (every phone) shows every box ticked, so a
Save keeps what they had. Until a phone has a name there are no boxes
to draw, so People keeps the single *work the phone* box.

**A NAME TAKES EFFECT AT THE NEXT START.** `phone add` writes the file
and nothing else; it doesn't restart anything behind your back. The
containers get `SPARSH_PHONES` from `sarathi up`, and a container's
environment is fixed when it starts, so every `add` and `remove` ends
with *next: `sarathi down && sarathi up`*. The home page reads the file
on each request, so its boxes show the names at once, before the
agents can use them.

## Nothing written down is dropped quietly

There are three ways a list like this can lose a phone without anyone
noticing, and each one is refused:

* **An unnamed phone beside named ones.** Your `[phone]` already held an
  iPhone (`wda`). `sarathi phone add nexus` would have written a table
  beside it, and the iPhone would have been left unreachable. Instead it
  says *"[phone] has a phone with no name yet (http://127.0.0.1:8100):
  name it first -- sarathi phone add NAME iphone http://127.0.0.1:8100"*.
  Naming it takes its place.
* **A phone in a drawer blocking the rest.** Naming the iPhone already
  saved (`add iphone iphone http://127.0.0.1:8100`) used to ask it to
  answer first, so with only the Android plugged in, nothing could be
  named. **NAMING WHAT IS SAVED ASKS NOTHING OF THE PHONE.** On a copy of
  a real settings file, iPhone in a drawer:

  ```
  $ sarathi phone add iphone iphone http://127.0.0.1:8100
  the iPhone already saved, named (not asked: it needn't be plugged in)
  $ sarathi phone add nexus
  $ sarathi phone list
  iphone: iPhone at http://127.0.0.1:8100 -- not answering
  nexus: Android at 84B7N16128001616 -- answers
  ```
* **One phone under two names.** Found in the live run below: *"the
  phone on the cable"* skips the emulator, so `add pixel` named the
  Nexus a second time. Two names for one phone means two owners in Dvara
  for one set of messages. Refused: *"84B7N16128001616 is already named
  nexus: one phone, one name"*. The emulator is named by its serial
  (`add pixel emulator-5554`), checked against what Sparsh sees.
* **A Save from the page that forgot the names.** The Settings form's
  Save rebuilt `[phone]` from its three old fields, which would have
  wiped every named table. It now keeps them, and each named phone
  changes only through its own Remove and Add.

## LIVE RECEIPT

The Nexus 6P on the cable and the Android 15 emulator, on a copy of the
settings (`SARATHI_CONFIG` pointed at a scratch folder):

```
$ sarathi phone add nexus --awake always
84B7N16128001616 (Nexus_6P), on the cable
nexus is in .../sarathi.toml: Android at 84B7N16128001616
  give it to someone in Dvara's actors file: phones = ["nexus"] under their [actor.…]
  the containers reach it through this computer's adb (sarathi-adb)
next: `sarathi down && sarathi up`
$ sarathi phone add nexus2
error: 84B7N16128001616 is already named nexus: one phone, one name (sarathi phone remove nexus first, to rename it)
$ sarathi phone add pixel emulator-5554
emulator-5554 (sdk_gphone64_x86_64)
pixel is in .../sarathi.toml: Android at emulator-5554
$ sarathi phone list
nexus: Android at 84B7N16128001616 -- answers, awake always
pixel: Android at emulator-5554 -- answers
```

The home page on a spare port, in headless Chrome. **Settings → Sarathi**
shows a *Your phones* card listing nexus and pixel, each with Remove,
and an *Add a phone* form (a name, then the phone on the cable, Wi-Fi
from the cable, an address, or an iPhone). **Settings → People** shows
*Their phones* with a box for each. `SPARSH_PHONES` as Sarathi wrote it
is exactly what Sparsh, Yantra and Dvara were run with in their own
live receipts.

## What is not here yet

* A real iPhone named beside a real Android. The iPhone's table is
  `wda`, the same address `[phone] wda` has always held.
* ~~One card per phone on the home page itself.~~ The card is *Your
  phones* and names each (*"nexus (Android), iphone (iPhone), and what
  the agent did on each"*). It opens Yantra's phone panel, where each
  phone has its own row, and where one can be picked by name.
