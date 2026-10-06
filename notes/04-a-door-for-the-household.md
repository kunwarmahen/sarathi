# 04 — A door for the household

[Note 03](03-two-containers-one-clock.md) left one person with a page
and a clock, kept running by systemd. The next road is the household's:
the helper on Telegram, for you on your phone and for the people you
choose, each as themselves. That's dvara, the door. Every piece of it
already existed in dvara. What didn't exist was anyone wiring it up
except by hand, from a list in Yantra's tutorial (§24, step 3) that
named four environment variables, two of which had to match in two
different programs.

## What a person would get wrong

To run the door beside the clock, by hand:

1. start `dvara serve` with `--ask` (so questions reach people) and
   `--samay` (so a person can ask for a schedule in the chat);
2. give it a `DVARA_TOKEN`, made up, at least 16 characters;
3. give it a `TELEGRAM_TOKEN`, from @BotFather;
4. set `SAMAY_DVARA_URL` and `SAMAY_DVARA_TOKEN` **for dvara**, so the
   `samay mcp` it starts per turn knows which door made a schedule;
5. set the same two **for the clock**, so it checks every such schedule
   against that door;
6. start the clock before the door, because the door asks once whether
   the clock is running;
7. write an actors file, with the right Telegram id in it.

Steps 4 and 5 are the trap. Get the token right in one and wrong in the
other and nothing fails at start: schedules made in the chat are refused
later, one by one, with a message about a token nobody remembers
setting.

## `sarathi door`

```bash
sarathi door
```

asks one question (which agent a Telegram bot answers as), takes the
bot's token at a hidden prompt, and does the rest:

* **makes `DVARA_TOKEN`** (48 hex digits) and saves both tokens to
  `secrets.env`, readable only by you;
* **writes dvara's files only where there are none**: an actors file
  with you as the owner, and dvara's own example agents copied into
  `~/dvara/agents`. They're dvara's formats, explained in dvara's
  tutorial, and Sarathi never edits them again. The agents are dvara's
  examples, not Sarathi's: Sarathi has no agent of its own (the plan's
  "not doing", kept);
* **turns `[door]` on** in `sarathi.toml`, on port 8770 unless told
  otherwise (`--port`). Not dvara's own 8765: that's the port a person
  running dvara by hand, or some other program, is likeliest to have
  taken already, and on this machine something had. Inside a container
  the door still listens on 8765; only the published port moved.

Then `sarathi up` starts clock, door, page, in that order. Steps 4 and 5
are done once, in one place: both programs get `SAMAY_DVARA_URL` (the
door's address) and `SAMAY_DVARA_TOKEN` (the door's own token), read
from the same line of `secrets.env`. The door gets the same model as the
page and the clock (`--provider`, `--model`), so the person on Telegram
and the person on the page get the same helper.

## The door's secrets go to the door

Before this, `up` handed every line of `secrets.env` to every piece. With
one cloud key in it, that was right. With the bot's token in it, the
page would hold a token that lets anyone who has it answer as your bot.
So now **the door's two tokens go to the door alone**; the clock gets
only the door's token, as `SAMAY_DVARA_TOKEN`; the page gets neither.
Checked live, by reading each process's environment:

```
clock: SAMAY_DVARA_URL=http://127.0.0.1:8766 SAMAY_DVARA_TOKEN=…
door:  DVARA_TOKEN=… SAMAY_DVARA_URL=http://127.0.0.1:8766 SAMAY_DVARA_TOKEN=…
page:  (none of them)
```

On the Podman road the same rule needed a change of shape. Every unit
used to say `EnvironmentFile=secrets.env`. Now `up` copies from it into
one file per unit (`~/.config/sarathi/units/<unit>.env`, folder 0700,
files 0600), each holding only that unit's share, and each unit names
its own. The unit files still hold no secret and can still be pasted
into a question.

## Finding the clock from the door, in containers

`127.0.0.1` inside a container is the container. The page never had to
reach the clock over the network (it runs `samay` as a program and
reads the clock's lock file, note 03). The clock *does* have to reach
the door: it checks schedules against it. So all three containers now
join one network, `sarathi.network` (a Quadlet network unit), where each
answers to its own name: the clock's `SAMAY_DVARA_URL` is
`http://sarathi-door:8765`, and the door's, for its own `samay mcp`, is
its own `127.0.0.1`. `host.containers.internal` still reaches the host
on that network, so a local Ollama works as before. `sarathi down
--remove` removes the network with the units.

The image grew dvara, built against the Yantra already in it. A
checkout of dvara beside the others is optional: without it, the image
is built without dvara (and says so), and a door asked for on the
Podman road says the image has no dvara and how to put it in.

## Letting yourself in

An actors file needs your Telegram id, and nobody knows their Telegram
id. dvara already answers strangers with silence and writes their id in
its log, for the owner. So `sarathi status` reads the door's log (or its
journal) and names them:

```
  door   running at http://127.0.0.1:8770/  (pid 3426486)
         messaged the bot but not in the actors file (telegram id): 8675309
```

Message your bot, run `sarathi status`, paste the number. The door
rereads the actors file, so no restart. Adding a person is the same
three steps, and with `setu = true` they connect their own accounts from
the chat (dvara's note 20).

## A door that can't start costs nobody the page

No actors file, no agents, no `DVARA_TOKEN`, a bot with no token: each
is a reason, said in one line, and the clock and page start anyway:

```
door   not started: no actors file at ~/dvara/actors.toml: `sarathi door` writes a starter one
clock  up at http://127.0.0.1:8780/#token=…
page   up at http://127.0.0.1:8321/
```

On the Podman road the same checks run before anything is written, and
stop `up` with the reason, since the units would otherwise be installed
to fail at every login.

## Receipt

Real Yantra, Samay, dvara and Setu, `qwen3.8:latest` on Ollama, scratch
settings and scratch dvara files, `sarathi door --telegram ""` (no bot:
the HTTP surface only).

**Process road:**

```
clock  up at http://127.0.0.1:8781/#token=…  (pid 3426483)
door   up at http://127.0.0.1:8766/  (pid 3426486)
page   up at http://127.0.0.1:8421/  (pid 3426493)

dvara: schedules through samay 0.1.0 (…/samay); its clock is running
POST /message {"actor": "owner", "agent": "greeter", "text": "who are you?"}
  end_turn | I'm the greeter here, ready to help with whatever you need.
```

No warning about `SAMAY_DVARA_URL`: dvara prints one when it's missing.

**Podman road**, after `sarathi image` (dvara 3bf6565, yantra bccf58e,
setu 3d5b929, samay d6f669d):

```
units rewritten from sarathi.toml
clock  up at http://127.0.0.1:8781/#token=…  (unit sarathi-clock)
door   up at http://127.0.0.1:8766/  (unit sarathi-door)
page   up at http://127.0.0.1:8421/  (unit sarathi-page)

dvara: schedules through samay 0.1.0 (/usr/local/bin/samay); its clock is running
clock -> http://sarathi-door:8765/health: 401 (it answers, and wants the token)
page container: no TOKEN in its environment
  end_turn | Hello, how are you today?
```

`sarathi down --remove` left no units, containers or network behind.

**Not tested live** when this was written: a real Telegram bot, and a
schedule made in the chat end to end. ~~A real bot~~ has since run on
the Podman road from a real phone: letting yourself in from `sarathi
status`, Gmail connected from the chat, and Amazon through the window
([note 05](05-a-browser-in-the-image.md)). ~~dvara's example agents can't
make one: their tool lists don't include Samay's.~~ dvara now ships
`minder`, which can, and `sarathi door` copies it with the others; its
end-to-end receipt is in dvara's note 18.

**Found on the way:** the image has no bubblewrap, so Setu's
connectors there run without their sandbox. They still hold no key,
since Setu makes their requests, and Setu's card says they aren't
walled off. ~~Putting bubblewrap into the image is its own small
change.~~ Done: [notes/05](05-a-browser-in-the-image.md).
