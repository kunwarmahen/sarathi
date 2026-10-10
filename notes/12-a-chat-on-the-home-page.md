# 12 — a chat on the home page

*[Note 06](06-one-bookmark.md) made the home page one bookmark for
every program's page, and nothing else. This note adds the one thing a
person does there that isn't opening another page: talking to their
agents, through Dvara.*

## The problem, as you would meet it

A schedule made on Yantra's page ran at 08:00, and its answer went
nowhere you'd look: not to Yantra's page, not to Telegram. Only Samay's
page had it. Two reasons. Samay sent answers only for schedules that
came through Dvara, and a schedule made at the computer runs straight
from Samay with nobody named to tell. And Dvara had only one channel a
person could read: Telegram. Without it, the only way to talk to an
agent behind Dvara was `curl` with its token.

## Answers find you

`sarathi up` now tells Samay who you are (`SAMAY_DVARA_ACTOR`, your
`[dvara] owner`), on both roads. A schedule made at this computer still
runs straight from Samay, but its answer goes through Dvara to you: on
Telegram if you have it, and as a line in the home page's chat
whether you do or not.

## The chat

Dvara now has a web channel (dvara's note 34), and `sarathi up` starts
Dvara with it (`serve --web`). The home page draws it: **Talk to your
agents**, above the cards. Pick an agent, write, and the answer comes
back a few seconds later. What a schedule sent you is there too, marked
*Sent to you*. A question an agent asks shows up as a card with **Yes**
and **No**, and it goes to Telegram too; whichever you answer first
counts.

**IT HOLDS NO LOGIC.** Every word goes to Dvara and comes back from it.
Rules, allowance, questions and held turns are Dvara's, exactly as on
Telegram. The page only passes things through:

```
GET  /api/chat?after=N         -> Dvara's GET /web, as you
POST /api/chat                 -> POST /web/message
POST /api/chat/asks/ID         -> POST /web/asks/ID
POST /api/chat/holds/ID        -> POST /web/holds/ID
GET  /api/chat/file?line=&n=   -> GET /web/file
```

**WHO IS TALKING IS SET HERE, NEVER BY THE BROWSER.** The home page
names you, the owner, on every call. A body that names someone else is
ignored. Dvara's token is read from `secrets.env` by the home page's
own process and never reaches the browser, the same way Dvara's own
page keeps it. The browser holds only the home page's key, as before.

**ITS OWN CONVERSATION.** The chat is a conversation of its own. One on
Telegram doesn't continue here, and the reverse. You are still one
person on both: same allowance, same rules, same folder.

## Receipt

A scratch Dvara on 8798 (`serve --web`, the example agents,
`qwen3.8:latest` through Ollama) with the home page's chat in front of
it on 8797. A notice for a person with no Telegram was kept for the
page (`"sent": ["web"]`). Through the home page, `greeter` answered
*"I greet folks at the door and chat a little — that's about it."*
eight seconds after the message. Asked to write `a.txt`, `scribe`'s
question came through as `write_file: NEW FILE a.txt (1 lines)`; a Yes
from the page let it go on, and the answer was *"Done — `a.txt` now
contains the word `hello`, verified by reading it back."* Drawn at
1100 and 390 pixels wide, the chat read the same, the agent picker
moving above the box on the narrow screen.

## What is not here yet

* **Everyone in the house signing in.** The chat speaks as the owner.
  Each person with their own sign-in and their own lines is the next
  piece of work, in front of the same Dvara channel.
* **Push to a phone.** The page asks for new lines every few seconds
  while it's open; nothing arrives with it closed.
* **The Podman road, tried.** The units are written (`--web` on Dvara's,
  `SAMAY_DVARA_ACTOR` on Samay's); the live run above was plain
  programs. The image needs rebuilding (`sarathi image`) for the Dvara
  inside it to know `--web`.
