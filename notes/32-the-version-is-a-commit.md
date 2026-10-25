# 32 — The version is a commit, and its day

"Is my fix in there?" is the question a version answers, and a number
somebody bumps answers it only as well as they remember to bump it. Each
project here gets eight commits on a busy day; a bump each time would be
a chore, and a skipped one a lie. So a version is worked out from the
history instead, the same way in every project:

    YEAR.MONTH.DAY.N      2026.10.25.3

the day of the last commit (in the time zone it was made in) and N the
commits made that day up to it: the third commit of 25 October. Two
versions say at once which is newer and when it was made, and the commit
beside it says exactly which. Nothing is bumped, nothing is tagged, and
`pyproject.toml` keeps its `0.1.0` for the packaging tools.

```
$ sarathi version
Sarathi 2026.10.25.7, containers from the image of Sun 25 Oct 12:09
  yantra     2026.10.25.1  d73c5b8  docs(notes): a PDF where there is no print window…
  setu       2026.10.25.1  203f861  feat(own,page): a server's tools marked read or w…
  samay      2026.10.23.8  6ca3c52  feat(backup): the house backed up every night, an…
  prahari    2026.10.23.1  fc4f36c  feat(keeps): where the watches are kept, said for…
  dvara      2026.10.25.1  a65654e  feat(remembering,telegram,printed): take back a "…
  sparsh     2026.10.23.3  485e162  feat(keeps): where your phone rules and adb's key…
  smritikosh 2026.10.23.1  540ab4f  feat(memory): a memory in use does not age; fact …
  sarathi    2026.10.25.7  …        (this page, from its checkout)
```

After a commit to Dvara, its line ends `-- 1 newer in the checkout`, and
a last line says the next `sarathi image && sarathi up` takes it in.

Every program says its own the same way:

```
$ dvara --version
dvara 2026.10.25.1 (a65654e)
$ samay status --json | jq '.version, .commit'
"2026.10.23.8"
"6ca3c52"
```

Each sibling has a small `version.py` of its own (they share no
library, note 01): git in a checkout, with `+dirty` for uncommitted
changes; in the image, which has no git, a `VERSION` file at the top of
each project (`2026.10.25.1 a65654e`) that `sarathi image` writes; with
neither, the package's own number. `--version` is worked out only when
asked, so git isn't run on every start.

The home page shows the same: the first line in its footer, for the
owner, and a **Version** card in Settings → Check, with **Rebuild and
restart** under it when the checkouts have moved on.

## The image says, not the checkout

On the containers' road, what runs is the image, and the checkouts move
on the moment you commit after building it. Reading the checkouts would
answer the question wrong in exactly the case it's asked: you committed
a fix, and wonder whether it's live. It isn't, and the checkout says it
is.

So `sarathi image` writes down what it built from, on the image itself:
a label, `sarathi.build`, holding each project's version, commit, day,
first line and how many uncommitted changes it left out (the build is from `git
archive HEAD`, note 03, so those are never in it). `podman image
inspect` reads it back without starting a container, and it stays true
however far the checkouts get ahead. Each checkout's commit now is
shown *against* it: "2 newer in the checkout" is `git rev-list --count`
from the image's commit, which the next build takes in.

The label holds no time. The image's own `Created` says when, and the
same commits make the same label.

An image built before the label is said to be one ("the image doesn't
say"), with each checkout's commit beside it, never as what runs. One
stamped before versions were has each version worked out from the
commit it names. A
container still on an older image than the newest built is named too:
`sarathi up` restarts it on the new one (the doctor's same check, note
28).

## On plain programs, the checkout says

Without containers each program runs from its checkout, so what's
checked out is what runs, uncommitted changes and all ("+3 uncommitted
change(s)"). The one gap: a program started before your last commit
still runs the code it started with, until `sarathi down && sarathi up`.
Sarathi doesn't track when each process read its code; the line is
honest about the checkout, not the memory of a running process.

Sarathi itself runs from its own checkout on both roads: the home page
is a user service, not a container. Its line is that checkout.

## Shape

`sarathi version --json` prints `sarathi.version.v1`:

```json
{"format": "sarathi.version.v1", "sarathi": "2026.10.25.7", "road": "podman",
 "image": {"exists": true, "made": 1761340200, "stamped": true, "behind": []},
 "projects": [{"name": "dvara",
               "running": {"commit": "a65654e", "version": "2026.10.25.1",
                           "date": 1761390000,
                           "subject": "feat(remembering): ...", "left_out": 0},
               "now": {"commit": "9c1e0aa", ...}, "newer": 2}, ...]}
```

`GET /api/version` on the home page answers the same with a `said`
line, the owner's alone (a person signed in gets 401), asked at most
every 30 seconds: it is a git or two per project.

## Receipt

The house here, before the first build with the label:

```
$ sarathi version
Sarathi 0.1.0, containers from the image of Sun 25 Oct 10:43
  built before images said their commits: `sarathi image` once to see them
  yantra     ?        the checkout is on d73c5b8 now
  setu       ?        the checkout is on 203f861 now
  samay      ?        the checkout is on 6ca3c52 now
  prahari    ?        the checkout is on fc4f36c now
  dvara      ?        the checkout is on a65654e now
  sparsh     ?        the checkout is on 485e162 now
  smritikosh ?        the checkout is on 540ab4f now
  sarathi    acbd84b  25 Oct  feat(chat): Turned down, what you said no to, with an Undo …  (+9 uncommitted change(s))
```

After the rebuild, the house's own home page (8760) answered `GET
/api/version` with the image stamped, every project's commit, none
newer and no container behind, and 401 without its token.

The Version card on a scratch home page (port 8797) drew the same rows,
with **Rebuild and restart** under them, and the footer said *Sarathi
0.1.0, containers from the image of Sun 25 Oct 10:43*; pressing it
opened Settings → Check.

## What is not here

* **No version per process on plain programs.** See above: the
  checkout, not what a long-running process loaded.
* **No changelog.** "2 newer" says how many; `git log` in the checkout
  says which. The page doesn't list them.
* **No release numbers.** A day and a count say when, not how big a
  change was: nothing here says "this one breaks things". Everything
  ships together in one image, so nobody installs one project against
  another's old version; a release number for strangers installing a
  single package is a different job, not done here.
* **No version for a commit's day across machines.** The day is the one
  the commit was made in, its own time zone, so the same commit has the
  same version everywhere; a commit made at 23:30 in Pune is the 25th
  even where it is already the 26th.
