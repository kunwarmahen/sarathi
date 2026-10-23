# 27 — Kept tests, every night

Yantra keeps a conversation that went well as a test (its note 141).
Dvara keeps one from a chat (its note 57). Samay has a road that
replays them all and only tells you news (its note 08). What was left
for Sarathi was what it always does: put it on the home page and wire
it to the rest. It adds no logic.

## The card

**Kept tests**, under Your pages, the owner's only (`/api/pieces`):

| it shows | from |
|---|---|
| the last night: passed of all, broke since the run before, fixed | Yantra's `last.json` in its tests folder (`yantra.tests.v1`; a shape it doesn't know isn't shown) |
| each suite that couldn't run, with why, and what broke, whose agent | the same file |
| whether Samay runs them every night | Samay's own `GET /api/schedules` (a `tests` schedule) |

The badge never says green when the summary has a suite that could
not run.

## One button, asked once

**Run them every night** posts to the home page (`POST
/api/tests/nightly`, owner only), which asks Samay's own API for one
schedule:

```json
{"prompt": "the night's kept tests", "when": "at 03:00",
 "runner": "tests", "time_limit": 3600, "notify": "when_new"}
```

Samay checks it and keeps it. Sarathi keeps nothing. Asked again, it
looks first and says *already*. A Samay that says no is shown in
Samay's words (an image older than its tests road says *runner must be
one of direct, dvara*).

THE MODEL IS `[model]`'S. The tests run on what Samay's Yantra is
given, which is what every container gets from `sarathi.toml`
(`YANTRA_PROVIDER`, `<PROVIDER>_MODEL`). So the night replays on the
model you chose, and changing it there is the change the tests are
for.

## Live receipt

Against this machine's real config and its running Samay (read only,
nothing created):

```
$ uv run python -c "from sarathi.config import load; \
    from sarathi.home import kept_tests_status; print(kept_tests_status(load()))"
{"summary": null, "nightly": null, "samay": true, "clock_on": true, "suites": 0}
```

Samay answered with its token. There is no night run and no test kept
yet, so the card offers the button and says how to keep one.

## Tests

`tests/test_kept_tests_card.py` (6). Tests never reach this machine's
Samay or its tests folder (conftest). They check:

* the card shows Yantra's summary;
* an unknown shape isn't shown;
* nothing kept is an empty card;
* the button asks Samay for its tests road;
* asked twice, it is asked once;
* Samay saying no is said.
