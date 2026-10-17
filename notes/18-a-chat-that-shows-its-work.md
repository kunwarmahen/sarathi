# 18 — a chat that shows its work

*[Note 12](12-a-chat-on-the-home-page.md) put a chat on the home page,
through Dvara. It worked like Telegram: you wrote, and some time later
the whole answer appeared. This note makes it feel like Yantra's own
page while still going through Dvara.*

## The problem, as you would meet it

Yantra's page is the one you test on. Each step shows as it happens, the
answer appears word by word, and after a job of several steps it offers
to keep how it was done. But it talks straight to the agent, so it never
goes through Dvara: not your rules, not your allowance, not the people
in the house. The home page's chat does go through Dvara, and for a
minute it showed only *helper is working…*.

## What the page shows now

All of it comes from Dvara (its notes/42); the page only draws it.

* **The turn as it runs.** Under the agent's name, each step is a line,
  `✓ bash: $ wc -l people.csv`, or `✗ … — refused`. The answer then
  appears as it is written. While a turn runs the page looks every
  0.7 seconds, and every 3 seconds otherwise.
* **Answers as formatted text.** Lists, code, tables and links are drawn
  with the same small renderer Yantra's page uses (`md.js`). It escapes
  everything first, so nothing the model writes becomes markup. Your own
  words stay as you typed them.
* **A skill to keep.** After a job of four steps or more, a notice can
  offer to keep how it was done, with **Keep** and **Not now**. A kept
  skill is yours: saved in your own folder for that agent, so nobody
  else's agent changes.
* **A row of words.** **Skills**, **Learn this**, **Tools**,
  **Schedules**, **Memory**, **Phone**, **New chat**, **Past chats**.
  Each sends the word to Dvara (`/skills`, `/learn`, `/tools`,
  `/schedules`, `/memory`, `/phone`, `/new`, `/chats`), exactly as typing it would, so it
  answers the same here, on Telegram and over HTTP.
* **A sign-in you tap.** When an answer tells you to send
  `/connect gmail` or `/unlock`, the word is a button under it
  (**Connect gmail**); pressing it sends the word, as typing it would.
  Only those words, and only where the answer says them (Dvara, its
  notes/20).
* **A picture in an answer is shown.** `/phone`'s screen appears in the
  chat (tap it to save it); other files stay a button to download.
* **Pictures and files.** The paperclip beside **Send** adds them to
  your next message, shown as chips you can take off. They go to Dvara
  with your words (in base64; this page passes them on, up to 20 MB
  together, and checks nothing about them).
* **Full screen.** A button above the chat gives it the whole window,
  which is what a phone wants; Escape or the button closes it.

**IT STILL HOLDS NO LOGIC.** No new route on this page's server: the
look it already passed through (`GET /api/chat`) now carries `live`, and
every button posts a message. The only new file served is `md.js`.

## Receipt

A scratch Dvara on 8798 (`serve --web`, `qwen3.8:latest` through Ollama)
with this page in front of it on 8797, driven by a headless Chrome at
1100 pixels and at 390. Asked to *"make the same kind of report for
people.csv again, into report2.md"* after keeping the skill an earlier
job offered, the page showed *helper · working* and then:

> Done. Used the project's csv-people-report skill script to regenerate
> the report from `people.csv` into `report2.md`:
>
> ```
> # Report
> - Number of people: 3
> - Average age: 34.7
> - Youngest person: Chen (29)
> ```

That was drawn as formatted text, with the code block boxed. At 390
pixels, **Full screen** filled the window: the lines, the row of words,
the agent picker, and the box to write in.

## What is not here yet

* ~~**Past conversations.**~~ **Past chats** lists what **New chat**
  ended, and one can be opened again (Dvara, its notes/45).
* ~~**Sending a file from the page.**~~ The paperclip beside **Send**:
  pictures and files go with your next message, kept in your folder,
  a picture shown to a model that can see (Dvara, its notes/44).
