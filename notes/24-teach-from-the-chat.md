# Teach from the chat

A lesson teaches an agent a job one step at a time: you tell it each
step, or you do each step on the phone yourself and send `next`
(Yantra's notes/129, Dvara's notes/49). On the home page, the only way
to start one was to write `/learn start …` or `/learn watch …` in the
box, and nothing on the page said a lesson was open. After a few steps
it was easy to forget whether you were still teaching, and to which
agent.

## A button and a bar

**Teach** sits in the row of words, after **Learn this**. It opens a
small dialog with two choices, *Tell it* or *Show it*, and a box for
what the job is for. **Start** sends the same words a person would
write (`/learn watch check my battery level`) to the agent picked
below. So the chat shows the line as yours, and Telegram, the terminal
and this page all go through the same road. Escape or **Cancel** sends
nothing.

While a lesson is open, a bar sits above the row of words: *"Showing
minder: check my battery level. 2 step(s) so far; do the next step on
the phone, then send next."* **Done** sends `/learn done`, **Stop**
sends `/learn stop`, and the bar goes when Dvara's next look has no
lesson.

**THE BAR COMES FROM DVARA, NOT FROM THE BUTTON.** Dvara's look (`GET
/web`) now lists each open lesson for the person. Sarathi passes it
through and draws the one for the agent picked. A lesson started by
typing, or on Telegram, shows the same way, and one finished on
Telegram goes from here at the next look. The page keeps nothing of
its own about it. Picking another agent shows that agent's lesson, or
none. **Teach** with a lesson already open says to finish it first,
rather than starting a second.

`/learn clear` is another word for **Stop**, for people who reach for
it. The skill a phone lesson leaves opens its app by name, so a job
taught on the iPhone is written for the Android phone too (Yantra's
notes/133).

## Live receipt

Headless Chrome at 1280 px and 390 px, signed in as a person, with
Dvara's answers stood in for. Teach → *Show it* → "check my battery
level" → Enter sent `/learn watch check my battery level`, and the bar
read *"Showing minder: check my battery level. 0 step(s) so far; do the
next step on the phone, then send next."* Stop sent `/learn stop` and
the bar went. Teach again, a word typed, then Escape: nothing sent. On
a phone's width the bar wraps its words above **Done** and **Stop**,
which stay together.

Dvara's side has its own tests (its `tests/test_lessons.py`: the look
lists a person's open lesson and not another's). Sarathi's 304 tests
pass unchanged: the page passes Dvara's answer through as it is.

Teach now sits behind the + beside the box, as **Teach…**, with the
other words ([note 33](33-a-list-beside-the-chat.md)); the bar sits
above the box.

## Not done, on purpose

* **No lesson state in Sarathi.** The bar is drawn from Dvara's answer
  every look. A second copy here would go stale when a lesson is
  finished on Telegram.
* **Not a different road.** Teach writes the words a person would, so a
  lesson started here is the same lesson everywhere else.
