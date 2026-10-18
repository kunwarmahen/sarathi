# The chat is the page

The home page grew one section at a time: the cards, then a chat above
them ([notes/12](12-a-chat-on-the-home-page.md)), then the people in
the house ([notes/14](14-everyone-in-the-house.md)), then Settings
([notes/16](16-every-setting-from-the-page.md)). Each was right on its
own, and together they made one long page. The chat sat in a box of
fixed height between a paragraph and the cards, and a phone got the
whole window only after pressing **Full screen**. Settings came after
the cards and People, so changing an agent's tools meant scrolling past
everything else to find it.

What you open the page for, nearly every time, is to talk to an agent.
Everything else you open now and then.

## Three views

**THE CHAT IS THE PAGE.** Signed in, the chat fills the window under a
slim header: the messages, the row of words (**Skills**, **Learn
this**, … **History**), the agent picker, the box to write in. Nothing
sits under it, so there is nothing to scroll past. **Full screen** is
gone, because the page already gives the chat the whole window.

Two icons at the top right open the rest, each in its own view:

* **Your pages** (four squares): the cards for Yantra, Samay, Setu,
  Dvara, your phone and your memory, the same as before.
* **Settings** (a gear): the six tabs, then **People in the house**
  under them.

A third icon, the speech bubble, brings you back to the chat. So do
**← Back to the chat** at the top of each view and the Escape key.

**EACH VIEW HAS ITS OWN ADDRESS.** `#pages` and `#settings`, so a reload
stays where you were, the browser's back button goes back, and a
bookmark can open on Settings. The owner's key link keeps a view asked
for beside it (`#settings&token=…` opens on Settings once the key is
taken out of the address bar).

**WHO SEES WHAT DIDN'T MOVE.** Someone else in the house still gets the
chat and nothing else: no icons, because they have nothing behind them.
The server holds that line, as before; the page only draws it. The owner
with Dvara off has no chat, so the page opens on Your pages, with no
chat icon and no back link.

## How it's drawn

Each section still has its own `hidden`, which says whether it has
anything to show (no Dvara, no chat). Which view is on is one attribute,
`body[data-view]`, and the stylesheet hides the sections that belong to
the other views. A section reports what it has, the view decides where it
goes, and neither needs to know about the other. The chat's height is
the window's (`100dvh`, so a phone's address bar doesn't push the box
off the screen). The messages scroll, the page doesn't.

**IT STILL HOLDS NO LOGIC.** No route was added or changed. The three
views are three ways of showing what the page already fetched.

## Live receipt

The page from this tree on a scratch port (8762), in front of the
running Sarathi (5 of 5 running, Dvara up), driven by headless Chrome at
1280 × 820 and at 390 × 760:

```
desk url http://127.0.0.1:8762/ view chat
desk url http://127.0.0.1:8762/#pages view pages
desk view settings
desk after reload http://127.0.0.1:8762/#settings settings
desk after Esc http://127.0.0.1:8762/#chat chat
scrollW 1280 errors []
phone url http://127.0.0.1:8762/ view chat
phone url http://127.0.0.1:8762/#pages view pages
phone view settings
phone after reload http://127.0.0.1:8762/#settings settings
phone after Esc http://127.0.0.1:8762/#chat chat
scrollW 390 errors []
signed out view signin False False
```

On the phone, the chat filled the screen from the header to the box to
write in, with the row of words wrapping to two lines. The page never
scrolled sideways (`scrollW` equals the width). Signed out, neither the
icons nor the back link showed.

The first run caught two bugs. Signed out, the icons still showed,
because `.views { display: flex }` beat the `hidden` attribute (the same
trap History's dialog fell into, [notes/21](21-history.md)). In the chat
view on a wide screen, the header shrank to its contents, because the
page body had become a column of flex items. Both are fixed:
`[hidden]` wins for the icons, and the header and footer take the full
width.

## Not done, on purpose

* **Dvara's page is left as it is.** It has no chat and no settings. It
  is one page of what your agents are waiting on, who used them, what
  they ran, their schedules and files, and you read it from top to
  bottom. Splitting it would hide the questions waiting for you behind a
  click.
* **History stays a button in the chat**, not an icon at the top. It is
  about the chat (search what you said, carry one on), so it sits with
  the other words under the messages.
