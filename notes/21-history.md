# History

The home page's **Past chats** button sent `/chats`. The answer was a
numbered list of what **New chat** had ended, as a chat message, and
the way back was typing `/chats 2`. To find the conversation about the
boiler you read the list, guessed a number, and tried again.

Dvara now keeps every conversation as it goes, in a file of each
person's own, searchable by its words (Dvara's notes/50, on Yantra's
conversation log, its notes/130). The page draws that instead of a
message.

## The button

**History**, in the row under the chat where **Past chats** was, opens a
dialog:

* a search box. Every word typed must be in the conversation, matched
  by Dvara's full-text index across all of them, not only the rows on
  screen. Each row shows the words around a match, marked.
* the list, newest first: title (its first words), when, which agent,
  which channel (*on the page*, *on Telegram*), how many messages. The
  one open in a chat now says so, and its **Delete** is greyed out.
* a conversation to read, the way it looked: your words, the agent's
  answers as formatted text, each tool folded on one grey line. The
  searched words are marked here too, and the first one is scrolled into
  view.
* **Carry on in the chat** sends `/chats open ID` to that conversation's
  agent, so the answer arrives as the usual *"Back in: …"* line with the
  conversation unfolded under it, and the agent picker moves to that
  agent.
* **Delete** asks once, then deletes for good through Dvara.

## Passing it through

Three routes, all for the person signed in and never anyone the browser
names:

```
GET  /api/chat/chats?q=WORDS        -> Dvara GET    /web/chats
GET  /api/chat/chats/ID             -> Dvara GET    /web/chats/ID
POST /api/chat/chats/ID/delete      -> Dvara DELETE /web/chats/ID
```

The id goes on as one quoted path segment: `..%2Fweb` reaches Dvara as
`..%252Fweb`, never as a step up to `/web`. Dvara's refusal (409, *open
in a chat now*) comes back in its own words. This page decides nothing
about conversations. It only links, signs people in, and passes words
to Dvara.

## Live receipt

A scratch Dvara on `qwen3.8:latest` with two conversations (a boiler's
pressure, then `/new`, then Lisbon), and this page in front of it, in a
browser at 1280 px and at 390 px. **History** listed both, the Lisbon one
*open in a chat*. Typing *boiler* left one row, with *boiler* marked
twice in its snippet. Opening it showed the question and answer, the
word marked in both. **Carry on in the chat** sent `/chats open
ea51cd053863`, and the chat answered *"Back in: In one sentence: what
pressure should a home boiler show when cold?"* with the two messages
under it. **Delete** on Lisbon, no longer open, removed it. Dvara's
`owner.sqlite` then held no "Lisbon" at all.

The first run caught two layout bugs. The reading view drew under the
list, because a `display: grid` beat the `hidden` attribute. On a phone,
**Delete** filled the row's width, so a tap in the middle of a row hit
it. Both are fixed: `[hidden]` wins inside the dialog, and the button
sits at the row's start.

## What is not here yet

* ~~**Its own view.**~~ The chat is now the page, with Your pages and
  Settings behind icons ([note 22](22-the-chat-is-the-page.md)). History
  stayed a button under the chat, since it is about the chat.
* **The chat scroll above, by choice.** Deleting a conversation clears
  the person's history; the lines it left in this page's chat window
  stay until they age out, and the run ledger keeps its own. Blanking
  them too was offered and turned down: the owner's record of each run
  stays whole.
