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
  hands it to Yantra alone; Samay and the pages never see it.
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

**Found on the way: a fresh clone didn't run.** Smritikosh doesn't commit
its `uv.lock`, so a clone resolves its dependencies anew. That gave `mcp`
2.3, which renamed the `FastMCP` that `smritikosh-mcp` is built on, and
no numpy, which its server imports. Smritikosh's `pyproject.toml` now
pins `mcp<2` and names numpy. With that, Smritikosh installed in a
throwaway image the way Sarathi's Containerfile installs it, and its
programs imported (`mcp 1.30.0`, numpy 2.5.4).

## What is not here yet

* **The Podman road, run.** The units are written and tested, and
  Smritikosh installs in an image, but the receipt above is plain
  programs. On this machine it needs `sarathi smritikosh`, then
  `sarathi image`, then `sarathi up`.
* **Neo4j, MongoDB, Redis.** Left out; Smritikosh runs "degraded",
  which is everything Yantra asks of it. Maybe a later `--full`.
* **Samay's runs.** A scheduled run is Yantra started by Samay, and it
  still remembers in Yantra's own file.
* **A person removed from the actors file** keeps their account and
  memories in Smritikosh; nothing is deleted on Sarathi's say-so.
