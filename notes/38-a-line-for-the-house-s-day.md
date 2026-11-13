# 38 — A line for the house's day

`sarathi usage` says what the house's models did today: every program's
turns, from the one usage file they all write. It only tells you after
the fact. Nothing stopped the house as a whole. A turn's budget stops one
turn, and Dvara's allowances stop one person. But a watch asking every
few minutes on a cloud key, a schedule in a loop, and a busy Telegram
evening could all spend at once, with nobody looking.

Continues [36 — the bad days the doctor sees](36-the-bad-days-the-doctor-sees.md).

## The setting

```toml
[usage]
day_usd = 2.50       # billed models' dollars a day, every program together; 0: no limit
day_minutes = 120    # minutes of answering a day, local models too; 0: no line
```

Settings → Sarathi → *Which model answers* has both: **Most a day for
billed models** and **Minutes of answering a day**.

## The rules

**ONE NUMBER, HELD WHERE THE TURNS RUN.** `up` puts `day_usd` into every
container and every plain program as `YANTRA_HOUSE_DAY_USD`. Yantra holds
each one to it from the same usage file `sarathi usage` reads (Yantra's
notes/161), so the number on the page and the number that stops a turn
can't disagree. Once the day reaches it, a billed model isn't asked again
until midnight. A local model standing by (`[model] fallback`) answers
instead, and the answer says so. With none, the answer is *Nothing was
done: the house's $2.50 for today is spent…*.

**MINUTES ARE TOLD, NEVER STOPPED.** A house on Ollama bills nothing, so a
dollar line means nothing to it. Its cost is a GPU busy all afternoon.
`day_minutes` is that line. The doctor says when a day goes past it, and
nothing is stopped: a local house that went quiet because of a number
would be worse than one that ran long.

**THE MORNING AFTER IS TOLD ONCE.** Check has a `usage` line. It's amber
near the dollar line (80%), amber at it (*billed turns wait for
midnight*), and amber when a day went past its minutes. It also says
**yesterday's** dollar line was reached. The morning check runs at 07:30,
when today has barely started, so yesterday's line is the one with news,
and it's sent only when it's new.

**A CARD, NOT ANOTHER COMMAND TO REMEMBER.** Settings → Check → **Model use
today** shows what `sarathi usage` shows: turns and minutes, billed
dollars against the line, each program's turns (local or billed, minutes,
models), and Smritikosh's own calls. It's read from `GET /api/usage`,
for the owner only.

## Live receipt

The ceiling itself, on the real Ollama (Yantra's notes/161): with $2.10 of
$2.00 already billed today, a cloud turn wasn't sent, and
`qwen3.8-64k:latest` answered with *claude-sonnet-5-5 (anthropic) wasn't
asked: the house's $2.00 for today is spent ($2.10 so far)*.

## What is deliberately not here

* **No push the moment 80% is passed.** The doctor's line and the morning
  check carry it. A notice for every crossing would need a program
  watching the file all day.
* **Smritikosh isn't held.** It calls its own model without Yantra, on
  your local model. The card shows its calls beside the rest.
* **No share of the day per program.** Deciding that Samay's schedules
  matter more than a person's question is the owner's call. Per person,
  Dvara's allowances already do it.

## Tests

`tests/test_house_day.py`: `[usage]` round-trips through sarathi.toml and
the Settings form, and a bad number is refused in words. The ceiling
reaches every container and every plain program. Yesterday counts as its
own day. The doctor's lines are green on a quiet day, amber when today's
line is reached, amber the morning after, and minutes are said, never
stopped.
