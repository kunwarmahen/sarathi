# A list beside the chat

The chat was the page ([note 22](22-the-chat-is-the-page.md)), but it
still looked like a box that had grown. Ten buttons sat in a row above
the place to write. Every conversation you'd had was behind **History**,
a dialog over the chat. A schedule's answer landed between your
question and the agent's reply, and **New chat** was one more button in
the row. A chat app you already know puts your conversations in a list
at the side, the one you're in beside it, and a new one at the top of
the list. This page now does too.

## The list

**EVERY CONVERSATION, EVERY ROAD.** The list at the left is every
conversation you've had with your agents, newest first, under
**Pinned**, **Today**, **Yesterday**, **Previous 7 days**, **Previous
30 days** and **Older**. Each says where it went on: 💬 this page,
✈ Telegram, 🔊 a puck (*kitchen puck*; one kept before pucks were named
says only *puck*), several when it went on several.
The box at the top searches what was said in all of them (Dvara's
full-text index), with the words marked under each match.

**PICKED, ONE IS READ IN THE CHAT'S PLACE.** Its words fill the chat,
tools folded under the answers that used them, with *Write below to
carry this conversation on here*. Writing does: the page sends
`/chats open ID` first, then your words. One begun on Telegram stays
open there too, and both carry it on (Dvara's
[notes/71](https://github.com/kunwarmahen/dvara/blob/main/notes/71-one-conversation-two-chats.md)).

**CARRIED ON, IT STAYS AS YOU READ IT.** The window goes on from the
reading as it was drawn: its name and where it went on at the top, each
tool folded where it ran, every answer with its own lists and bold. The
answer to `/chats open` brings Dvara's short transcript; the page has
the whole already, so it draws nothing from it, and `/chats open ID`
itself never shows as something you said. A voice note's line reads as
you said it, *🎤 "…"*, in the reading and in the list's names, never
Dvara's *(a voice note, heard as: "…")*.

**THE LIST LOOKS AGAIN BY ITSELF.** A conversation on Telegram or at a
puck never touches this window, so nothing here would ask for the list
again. It looks every 20 seconds while the tab is in sight and when you
come back to it, but not while you're renaming a row or have its menu
open, which a redraw would close. A conversation you're reading that
moved elsewhere is drawn again, at its end if you were there, and not
while you have one of its tools unfolded.

**⋯ ON EACH ROW**: **Rename** (in place; Enter keeps it, Escape leaves
it, empty gives its first words back), **Pin to top**, **Save as PDF**,
**Download**, **Send…** where the browser has a share sheet, and
**Delete**, asked once. A name you give is searched too. **History**
is gone: the list does all of it ([note 21](21-history.md)).

**THE LIST HIDES.** The button at its top right hides it, and the page
remembers that in this browser. ☰ at the top left brings it back. On a
phone the list is hidden until ☰, slides over the chat, and goes when
you pick something.

## The chat

**THE WINDOW IS THE CONVERSATION YOU'RE IN.** **New chat** empties it,
and nothing is drawn for `/new`'s own answer: a greeting shows instead
(*What can I do for you?*) with four things to ask. A conversation
opened again starts the window over with that conversation's words, not
a fold under *Back in*. The title at the top is the conversation's own,
or the name you gave it.

**AN EMPTY WINDOW ISN'T ALWAYS A NEW CONVERSATION.** Dvara can be in a
conversation the window no longer shows: its lines aged out, or it was
opened from somewhere else. Then the page shows that conversation, and
writing carries it on with its words still there. **New chat** sends
`/new` whenever the list says one is open here, not only when the
window has lines. The first run found this the hard way: a question
written under the greeting went into an old conversation.

**THE TEN BUTTONS ARE BEHIND +.** **Skills**, **Learn this**,
**Teach…**, **Tools**, **Schedules**, **Memory**, **Turned down…**,
**Phone screen**, **Check what's mine** (`/doctor`) and
**Conversations** (`/chats`), each with a line saying what it's for.
Typing `/` at the start of a message lists the same words, narrowing as
you type. Arrows move, Enter or Tab picks, and a word it doesn't list is
still sent as written. The writing box grows with what you write.

## The bell

**WHAT WAS SENT TO YOU UNASKED HAS ITS OWN PLACE.** A schedule's answer,
a watch, a sign-in that stopped working: these go under the 🔔 at the top
right, not between your words. The count is what you haven't read plus
the questions waiting for your yes, which stay in the chat that asked.
**Notices** lists them newest first, unread ones marked, with **Go to the
chat** when a question is waiting. **Notices on this phone** (the ntfy
steps) moved there too. Dvara keeps the notices whatever **New chat**
cleared (`GET /web/notices`), and how far you've read them: opened on
the phone, on this computer, or by another address for the same page
(`localhost` and the house name are two to a browser), the bell counts
the same. A mark this browser kept from before is handed to Dvara once.

**A SKILL OFFERED IS ANSWERED FROM THE NOTICE.** After a job on
Telegram or at the puck, the offer to keep it as a skill comes as a
notice. Telegram's has **Keep** and **Not now**; here it does too, under
the notice: they send the same `/skills keep ID` / `/skills drop ID` the
chat's buttons do, the notice then says what was sent, with *See its
answer in the chat*. Pressed once on Telegram and again here, Dvara's
answer says the offer is gone.

## Your name at the foot

Your pages, Settings, Notices, Turned down, My accounts and, for
someone else in the house, Sign out: a menu from your name at the foot
of the list, where the icons at the top used to be. Someone else in the
house gets the list, the chat and their notices, as before: the server
holds that line, the page only draws it.

## Passing it through

Three routes, each to Dvara as the person signed in, deciding nothing:

```
POST /api/chat/chats/ID/rename  {title}    -> Dvara's /web/chats/ID/rename
POST /api/chat/chats/ID/pin     {pinned}   -> Dvara's /web/chats/ID/pin
GET  /api/chat/notices                     -> Dvara's /web/notices
POST /api/chat/notices/read     {upto}     -> Dvara's /web/notices/read
```

Each row of `/api/chat/chats` now carries `roads`, `pinned` and `here`
(open in this page's own chat), from Dvara.

## Live receipt

A scratch Dvara from its `examples/` on 8798 (`qwen3.8:latest`,
`--web`), already holding a conversation begun on Telegram, and this
page on 8794, driven by headless Chrome at 1280 × 800 and at 390 × 800,
dark:

```
title: In one short sentence: a good month to visit Lisbon?
rows: ['In one short sentence: a good month to visit Lisbon?',
       'In one sentence: what pressure should a home boiler show when cold?']
carry: Write below to carry this conversation on here (it stays open on Telegram too).
title after carry: In one sentence: what pressure should a home boiler show when cold?
notify {"actor":"owner","sent":["web"],...}
bell: 1
rows after: ['Pinned', 'Lisbon trip💬 page · greeter⋯', 'Today', 'In one sentence: what pressure…']
```

New chat showed the greeting. The Lisbon question was answered (*"May,
June, or September are the sweet spot…"*) and the conversation appeared
at the top of **Today**. The Telegram one opened in place, marked
*✈ Telegram · 💬 page*. Writing under it, *"And what if it reads 2.5
bar?"* was answered in that conversation. A `POST /notify` lit the bell
with 1, and **Notices** showed it bold. Pin and Rename moved the Lisbon
one under **Pinned** as *Lisbon trip*. Then the empty-window case: New
chat, `/chats 2` sent on the page's own chat over Dvara's HTTP, a
reload. The page opened on that conversation (*You're in this
conversation*), and *"So is 1.2 bar fine?"* went on from its ten lines.
On the phone the list slid over the chat and went when a row was
picked. No page errors.

The read mark, again with a scratch pair: a notice lit the bell with 1
on `127.0.0.1`; **Notices** opened there; then the same page opened as
`localhost` (its own storage) showed no count. Before, that second
address showed every notice unread, which is what a restart seemed to do.

The first runs found three things, all fixed before the commit: the
greeting over a conversation still open, described above; **Notices**
drawn empty, because its section started hidden; and the writing box
measured while the chat was still hidden, so its one line was cut in
half on a phone.

Carrying on, and the list looking by itself, were run on a scratch
Dvara (`qwen3.8-64k:latest`, the example agents) and a scratch home page
in headless Chrome. A voice note's words to minder asking for three
fruits as a bold numbered list, then `/new`, then the row picked and
*And one more fruit, same style.* written under it. The reading had 3
list items and *🎤 "Name three fruits…"* on your line; carried on, the
window kept the title at its head, had 4 list items, no *Back in* and no
`/chats open` line. A conversation then begun on a Telegram thread came
into the open list without a reload, and, read here, grew by its next
question while Telegram went on. No page errors.

Keep on a notice: a skill offer put in a scratch Dvara's notice book
(as learning.py makes them), the page at 390 px, **Notices**: Keep and
Not now under its words; Keep, and the notice said *Keep
robinhood-portfolio-value: sent.*; the chat had minder's answer (the
example minder has skills off, so *nothing to keep here*).

## Tests

`tests/test_home.py`: rename and pin go through as the person signed
in, never as an actor the browser named; the bell asks for your own
notices, and the bell's read mark goes to Dvara as the person signed
in; and every view hides every other view's sections, with the
list, New chat and the bell in the page and the History dialog gone.

## What is not here yet

* **Suggestions from your own skills.** The greeting's four are
  questions every agent answers. Dvara's look doesn't list a person's
  skills yet; when it does, they can be the suggestions.
* ~~**Vaani's page as a chat.**~~ Its pucks' conversations are in this
  list, marked 🔊, and Vaani's own page reads them as a chat too
  (Vaani's notes/03).
