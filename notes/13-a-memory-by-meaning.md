# 13 — a memory by meaning, set up in one command

*Yantra remembers you in a file of its own, and Smritikosh remembers you
by meaning (Yantra's notes 100–109). Getting from one to the other was
ten steps by hand in Yantra's SMRITIKOSH.md. This note makes it one
command, keeps the file as the default, and gives every person behind
Dvara a memory of their own.*

## The problem, as you would meet it

Yantra's own file matches words: *"find me flights"* never finds
*"lives near RDU"*. Smritikosh finds it, and the guide to it is good,
but it asks for a database container, a `.env` written by hand with an
embedding size you must not get wrong, an admin made through a door
left open for one call, an account named exactly as Yantra knows you,
a key copied once, and two files in the folder Yantra starts in. Then
it has to be running before Yantra every day.

And behind Dvara it couldn't be done at all. A Dvara agent that asked
for memory filed it under the login name of the process running Dvara.
Everybody's facts went into the owner's memories.

## One command, and the file stays the default

```
sarathi smritikosh          set it up, and switch to it
sarathi smritikosh --off    back to Yantra's own file; nothing is deleted
```

`[memory] via` in sarathi.toml is `local` until you say otherwise.
`sarathi init` asks, after the model, with the file as the answer to
Enter. The home page's **Memory** card has the same switch as a button,
once Smritikosh is set up. Setting it up stays in a terminal: it may
need a password typed, and it takes a minute.

The command runs the guide's steps in order, each skipped when it is
already done: the checkout (cloned beside the others if there is none),
its programs (`uv sync --extra mcp`), its `.env` (the local road with
Ollama and `nomic-embed-text` at 768, or the cloud road with OpenAI's
embeddings at 1536, by `[model]`), the pgvector database container, the
tables, then the accounts and keys. Then `sarathi up` starts the server
before Yantra and Dvara, and hands each the way to reach it.

**WHAT IS THERE IS USED, NEVER REPLACED.** A Smritikosh you set up by
hand has a `.env`, a database and a key. The `.env` is read, and only a
*missing* `JWT_SECRET` is added. Smritikosh may encrypt stored sign-ins
with that secret, so a short one is left as it is. The embedding size is
never touched, because the tables were built for it. Your database
container is started as it is, and its volume is recorded. A key already
in secrets.env, or in Yantra's `.env`, is checked against your memories
before it is kept. One that doesn't open them is said and not used.

**THROUGH ITS DOCUMENTED API.** Accounts and keys are made the way the
guide makes them: `/auth/register`, `/auth/token`, `/keys`. The first
admin is made on a server started for that one call with
`BOOTSTRAP_ADMIN=1` in its environment, never edited into its file.
Sarathi's admin is called `sarathi`, so it never collides with an
`admin` of yours, and it is made only when an account has to be. A
Smritikosh that already holds your account and key gets no admin.

**A PASSWORD IS KEPT BEFORE ITS ACCOUNT IS MADE.** Smritikosh mints a
key only for the account that is logged in, so every person's account
needs its password once. Sarathi writes the password it chose to a file
only you can read (`smritikosh-accounts.json`) *before* it makes the
account. A run stopped between the two logs in next time instead of
finding an account nobody can open. The first live run found exactly
that: a stopped run left `dvara-priya` behind with its password gone.

## One person, one key

Smritikosh keys reach only their own account's memories, so the
separation is the store's, not Sarathi's promise:

* **you**: an account named as Yantra knows you (`$YANTRA_USER`, else
  your login), and its key in secrets.env as `SMRITIKOSH_API_KEY`. `up`
  hands it to what runs as you: Yantra's page, and Samay for the runs
  it starts (below). Dvara and the pages never see it.
* **each person in Dvara's actors file**: an account of their own
  (`dvara-<id>`) and a key of their own, in Dvara's `memory.json`,
  readable by you alone. Dvara starts the memory server for each turn
  with that person's key and name (dvara's note 37). You are you there
  too: the owner in that file gets your own account, so what you told
  Yantra's page is what Dvara's agents know about you on Telegram.

A person added to the actors file later gets their account the next
time `sarathi smritikosh` runs. Until then their turns have no memory,
and Dvara says so once. They never fall back to somebody else's.

## Both roads

On plain programs, `up` starts the database container and then
`uvicorn smritikosh.api.main:app` in Smritikosh's checkout, where its
`.env` is. Yantra gets `--mcp-config` (a file naming `smritikosh-mcp`
with `${SMRITIKOSH_API_KEY}`, never the key itself), `YANTRA_MEMORY` and
`YANTRA_USER`. Dvara gets `--memory`.

On Podman, these are two more units. `sarathi-smritikosh-db` runs the
pgvector image on the same volume, so it is the same data as the plain
road. `up` stops the plain container of the same name first, since two
servers on one data folder would ruin it. `sarathi-smritikosh` runs
from Sarathi's image, which carries Smritikosh when sarathi.toml names
its checkout. It reads a copy of its `.env` with the database at
`sarathi-smritikosh-db` and Ollama on the host. Neither unit runs as you
or mounts any other piece's files.

A piece already running from an earlier `up`, but with other words on
its command line, starts again with the new ones. That is what makes
the switch take effect on the plain road, as a rewritten unit already
did on Podman.

## Receipt

Two runs, both on `gemma4:12b` through Ollama, from scratch settings so
nothing of the machine's own changed.

**Fresh.** A local clone of Smritikosh, its own database container on
5442, the server on 8098, a scratch Dvara with you and `priya`:

```
settings   wrote …/smritikosh/.env: ollama, nomic-embed-text, 768 dimensions
           (the tables are built for 768 now; another embedding model later means an empty database)
database   started scratch-kosh-pg (docker.io/pgvector/pgvector:pg17, volume scratch-kosh-pgdata)
tables     30 step(s) run
server     started for these steps at http://127.0.0.1:8098
you        the key in …/yantra/.env doesn't open 'asha-scratch''s memories: not used
server     started for these steps at http://127.0.0.1:8098 (able to make its first admin)
admin      made 'sarathi'; its password is in secrets.env
server     started for these steps at http://127.0.0.1:8098
you        account 'asha-scratch' and its key (in secrets.env)
dvara      2 in the actors file: you as 'asha-scratch', 1 with accounts of their own (priya new); keys in …/dvara/state/memory.json
memory: smritikosh (in …/config/sarathi.toml)
```

Sixteen seconds. A fact was stored for each person with their own key.
Priya's key asked for your memories got `HTTP 403: Access denied` from
Smritikosh itself. Then, through Dvara's `greeter` (a package with
`[memory] via = "local"`, which Dvara's `--memory` turned into
Smritikosh), each person asked *"What do you remember about me?"*:

```
priya: You have a cat named Biscuit and you prefer tea over coffee.
owner: You live in Pune and bank with First Federal.
```

Smritikosh's log shows priya's turn reading `/memory/dvara-priya` and
yours `/memory/asha-scratch`, and nothing else. Yantra's page started
with `memory: smritikosh for asha-scratch`. `sarathi status` ended with
`memory: smritikosh at http://127.0.0.1:8098 -- postgres ok, degraded;
1 remembered for asha-scratch` ("degraded" is Neo4j left out). The home
page's button switched to the file and back. Each time sarathi.toml was
rewritten, Dvara and Yantra restarted with the new settings, and the
home page itself stayed up.

**Yours, reused.** The same command pointed at an existing hand-made
Smritikosh: a `.env` from the guide, its database on the volume
`pgdata`, and its key in Yantra's `.env`:

```
settings   …/smritikosh/.env kept (ollama, nomic-embed-text, 768)
database   smritikosh-postgres already running (volume pgdata)
tables     up to date
server     started for these steps at http://127.0.0.1:8080
you        'mahen', with the key from …/yantra/.env
```

No admin, no new account, and the `.env`'s checksum the same before and
after. That `.env` names MongoDB, which wasn't running, and Smritikosh's
`/health` waits half a minute on it. So Sarathi checks that the server
is up from `/openapi.json`, which carries Smritikosh's name, and reads
`/health` only for the detail.

**Found on your machine: a clone around your own database.** Run with
no `SARATHI_SMRITIKOSH`, Sarathi found no Smritikosh beside the others
(yours is in the folder above them). It cloned one there, wrote it a new
`.env`, and pointed it at the `smritikosh-postgres` you made in March:
`password authentication failed for user "smritikosh"`. Nothing in the
database changed, but matching the password would only have hidden it:
the new `.env` had a new `JWT_SECRET` too. Now a database already here
decides. Sarathi looks for the checkout whose `.env` holds that
container's own user and password (beside the others, the folder above,
`~/src`, `~/Documents`, home) and uses it. With none, it stops before
cloning or writing anything and says how to name one. A checkout you
named that doesn't open the database is refused, not overridden. On
this machine it now picks `~/Documents/ai/smritikosh` over the stray
`agent/smritikosh`.

**Found on the way: a fresh clone didn't run.** Smritikosh doesn't commit
its `uv.lock`, so a clone resolves its dependencies anew. That gave `mcp`
2.3, which renamed the `FastMCP` that `smritikosh-mcp` is built on, and
no numpy, which its server imports. Smritikosh's `pyproject.toml` now
pins `mcp<2` and names numpy. With that, Smritikosh installed in a
throwaway image the way Sarathi's Containerfile installs it, and its
programs imported (`mcp 1.30.0`, numpy 2.5.4).

## `--full`: the other three stores, the same way

Yantra needs PostgreSQL alone. Smritikosh can use three more: Neo4j for
facts that link (you, your city, your airport) in its own context
building, MongoDB for an audit trail, Redis for its job queue and shared
rate limits. Without them it says "degraded". A Smritikosh set up by
hand from its own guide usually names Neo4j and MongoDB in its `.env`
whether or not they run. Then its `/health` waits half a minute on
MongoDB, and its log fills with Neo4j's refusals.

`sarathi smritikosh --full` treats each like the database. **THE ADDRESS
IN THE `.env` FINDS ITS CONTAINER**: the one that publishes that port
with that store's image (or the name `[smritikosh]` records). It is
started as it is. One is made, on 127.0.0.1, only when none is found.
The `.env` gains only the lines it lacks: on this machine, `REDIS_URL`
alone. The Neo4j password is never replaced, and a container made with
another one is named in a line, not changed.

On Podman each store becomes a unit **COPIED FROM ITS CONTAINER**: its
image by id (this machine's Neo4j runs `neo4j:latest`, and a unit
naming the tag could pull a newer server onto old data), its mounts as
they are (bind folders, named and unnamed volumes alike), the settings
it was made with minus the image's own, and its ports on 127.0.0.1. The
plain container is stopped first, the same rule as the database's.
Without `--full`, a store's line is left out of the server's copy of
the `.env` there, so nothing waits on a store that isn't running.

**Receipt.** A scratch `--full` on its own ports (17687, 27018, 16379)
made all three in 30 seconds, adding only `MONGODB_DB_NAME` to a `.env`
that named the rest. A second run found all three running and left them.
`/health` then answered in 0.4 seconds with `"status": "ok"`, postgres,
neo4j and mongodb `ok`, and `sarathi status` said `postgres ok, neo4j ok,
mongodb ok; ok`. Priya's turn through Dvara still answered from her own
memories alone. Read-only against this machine's own `.env`, it picks
`neo4j_container` (7687), `mongodb` (27017) and `smritikosh-redis` (6379),
and would add only `REDIS_URL`.

That run also found **a lost admin**. The scratch database had been
deleted and made again, and secrets.env still held the old `sarathi`
admin's password. A failed admin login now makes the admin again through
the bootstrap. If an admin of that name really is there, it says the
password in secrets.env is wrong.

## Its own dashboard, started with it

Smritikosh has a page of its own: its `ui/`, a Next.js app that signs in
through Smritikosh's `/auth/token` with a username and password and shows
the memories, the facts and the audit trail. It was left out at first,
to keep Node off the list of things to run. Wanting to *see* what the
helper remembers turned out to be the first thing a person asks for.
Yantra's bookmark chip shows the list, but not the rest.

`sarathi smritikosh` builds it (`npm install`, `next build`), and builds
it again when `ui/` has a newer commit than the build. `up` starts the
build with `next start` after Smritikosh, never the dev server, which
compiles every page on first visit. It listens on 127.0.0.1:3000. On
Podman it's a user service beside the home page's, run with the
machine's own Node, so the image stays as it was. The home page's Memory
card links to it when it answers *as Smritikosh* (its page title), not
merely when something listens on 3000. It writes `ui/.env.local` only
when there is none.

**IT SAYS LOCALHOST.** Its sign-in sends the browser to `localhost`
whatever address it is given. A cookie set for `127.0.0.1` is not sent
to `localhost`, so a person who opened it as 127.0.0.1 is signed in and
then shown the login page again. Every link Sarathi gives says
`localhost`, and `AUTH_URL` does too; it still listens on 127.0.0.1
alone. **SMRITIKOSH'S ADDRESS IS BUILT IN** (its `/api/backend` route), so
it is built with the address Sarathi runs Smritikosh on.

**Receipt.** The first `next build` on this machine failed: the dashboard
had only ever been run with `npm run dev`, which doesn't check types, and
21 type errors had gathered. The admin's user table read `user.app_id`,
which no user has (the field is `app_ids`, a list), so the cell had always
been blank. Three media hooks returned untyped answers, which broke every
use in the upload form. And a graph link read a position before the
layout had set it. Fixed in Smritikosh; `tsc` is clean, and the build
makes 21 pages. Started as Sarathi starts it, on a spare port, it served
*Smritikosh — Memory Dashboard*, `/` went to `/dashboard/memories`, and a
wrong password came back through the API as `CredentialsSignin`.

## A schedule remembers too

A schedule made at this computer runs as you: Samay starts Yantra
itself (`SAMAY_YANTRA`), with Samay's own environment. Sarathi gave
Yantra's page the Smritikosh server and your key and gave Samay
neither, so a morning check that should know you live in Pune read
Yantra's built-in file instead, a different set of facts.

**WHAT RUNS AS YOU REMEMBERS AS YOU.** With `[memory] via =
"smritikosh"`, `up` now hands Samay what it hands the page:
`SAMAY_YANTRA` carries `--mcp-config <the same server file>`, and
Samay's environment gets `YANTRA_MEMORY`, `YANTRA_USER` and your key,
which the runs it starts inherit. On the Podman road, Samay's unit gets
the same lines, its env file gets the key, the server's folder is
mounted, and it starts after Smritikosh. A schedule that goes through
Dvara is untouched: Dvara runs it as its person, with that person's key
(dvara's note 37), never yours.

The key now reaches two pieces, not one. Both run your own turns, and
a schedule's run is as much yours as a message on the page.

**Receipt.** A scheduled run started exactly as Samay starts it
(`DirectRunner`, `qwen3.8:latest` through Ollama), against a real
Smritikosh with the environment `up` builds, asked *"List up to three
things you remember about me"*, answered with the two facts that
account holds (here with the person's own details taken out):

```
- Your name is <name>.
- You use Gmail (<address>) as your "mine" account.
```

The same run without it (Samay as before) answered with three other
facts, about work, hardware and a writing habit: the ones in Yantra's
built-in file. Two stores, two different sets of facts, and the first
run read the store the page reads.

## What is not here yet

* **The Podman road, run.** The units are written and tested, and
  Smritikosh installs in an image, but the receipt above is plain
  programs. On this machine it needs `sarathi smritikosh`, then
  `sarathi image`, then `sarathi up`.
* ~~**Neo4j, MongoDB, Redis.**~~ `--full`, below.
* ~~**Samay's runs.**~~ A schedule made at this computer remembers as
  your page does (above).
* **A person removed from the actors file** keeps their account and
  memories in Smritikosh; nothing is deleted on Sarathi's say-so.
