# 34 — "Never asked" means it

Sarathi started Dvara with `--ask`, and never with `--yolo`. Dvara runs
a turn under the strictest of three: the house (its command line), the
person (`actors.toml`) and the agent (`agent.toml`). With `--ask` alone,
the house is "ask". So *Asking before changes: Never asked* on the
People form, written into `actors.toml` as `permissions = "yolo"`, did
nothing at all. Every `web_fetch`, every `bash`, every schedule made was
a question on Telegram, in the chat and at the puck.

That's Dvara working as designed: `--yolo` is the owner's half of yolo,
and a ceiling a file can lift isn't a ceiling. But nothing on the page
said so.

## The switch

`[dvara] yolo`, on the home page as **Settings → Sarathi → Dvara → Let
"Never asked" work**:

```toml
[dvara]
on = true
yolo = true
```

With it on, both roads start Dvara with `--ask --yolo`. Someone set to
*Never asked* isn't asked, and an agent's own `mode = "ask"` still asks.
A spend, and a change after the agent read something you didn't write,
are asked about either way (Dvara's notes/58). Off is the default. A new
house still asks about everything until its owner says otherwise.

## Nobody is lifted by it quietly

Dvara reads a person with no `permissions` as "no ceiling of their
own". Under `--ask` that's harmless, because the house is the ceiling.
Under `--yolo` it means whatever their agent says, and minder says yolo.

So while the switch is on, a person saved from the People form with
*Asking before changes* left at *Not set* is written as `"ask"`. The
blank choice is now labelled *Not set: asked before anything changes*,
which is what it means either way. Anyone already in `actors.toml`
without a setting keeps the file's reading until they're saved again.
With one person in the house that's nobody, but the switch's own words
say so.

## And two more ways to be asked less

Both are Dvara's (its notes/72), and both show up here:

* **Yes to all for this task**, a third button on a chat card that was
  asked only because the agent read something. One yes covers the rest
  of that task until it reads something new. A purchase is never
  covered.
* **Sources they trust** on the People form: servers whose answers are
  that person's own words (`samay`, `homeassistant-home`), so reading
  them asks nothing new.

## Tests

`tests/test_dvara_yolo.py` (6): off unless the file says so; on, and
kept when written back; a word isn't a yes; the Podman road starts Dvara
with `--yolo` only when on; a person saved with no setting is written as
asked, and one set to yolo stays yolo; with the switch off a person is
sent as the form said. `tests/test_door.py`: the process road's start
line has `--yolo` right after `--ask`. `tests/test_home.py`: *yes to all*
reaches Dvara, and a `for_turn` that isn't `true` doesn't.
