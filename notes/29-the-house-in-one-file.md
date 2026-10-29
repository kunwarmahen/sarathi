# 29 — The house in one file

What makes this computer yours is spread across seven programs' folders.
Setu holds your accounts, their keys and the browser profiles Amazon and
X are signed in on. Dvara holds everyone's conversations, their past
chats and their own Setu folders. Samay holds the schedules and the
logbook of every run, and Prahari the watches and what each last saw.
Sparsh holds your phone rules and adb's key, the one the phone trusts.
Yantra holds History and the skills it learned, Smritikosh's database
holds the memories, and every program has its settings file. A disk
that dies loses each of them separately, and so does a move to a
Raspberry Pi.

```
$ sarathi backup
Choose the passphrase that opens your backups. Without it nothing can open them -- not even you -- so write it down somewhere safe.
the backup's passphrase:
again, to be sure:
its key: ~/.config/sarathi/backup-key.json
yantra     state          ~/.local/state/yantra
...
  setu home                2 files, 58 bytes
  samay state              1 files, 8.0 KB
  ...
  smritikosh database      its memories (pg_dump)

written: ~/sarathi-backups/sarathi-beast-20261023-165107.sarathi-backup (50.6 KB, 0s), locked with your backup passphrase

$ sarathi restore ~/sarathi-backups/sarathi-beast-20261023-165107.sarathi-backup
the backup's passphrase:
...
put back, from beast (2026-10-23T16:51:08-0400):
  setu home                ~/.local/state/setu
  ...
next: `sarathi up` (each program must be installed here first: a backup holds what is yours, not the programs)
```

## Each program says what it keeps

Sarathi could guess where the files are. `~/.local/state/setu` is right
today, but it would be wrong the day `SETU_HOME` moves it, or the day a
new file appears beside the others. So each program answers one more
question about itself, asked the way `status --json` is:

```
$ setu keeps --json
{"format": "setu.keeps.v1", "keeps": [
  {"id": "home", "path": "/home/mahen/.local/state/setu",
   "what": "your accounts and their keys, settings, own servers' sign-ins, sites and their browser profiles",
   "leave_out": ["BrowserMetrics", "Cache", "CacheStorage", "Code Cache", ..., "Singleton*", "logs", "vault.lock"],
   "exists": true},
  {"id": "google-client", "path": "/home/mahen/Desktop/client_secret_….json", ...}]}
```

| program | its places |
|---|---|
| `yantra keeps` | the state home (History, the built-in memory, MCP sign-ins, the page's browser profile), the user skills, and History when `YANTRA_HISTORY` moves it |
| `setu keeps` | its folder, and the Google client file when it lives elsewhere |
| `samay keeps` | its state folder, without the running clock's record |
| `prahari keeps` | its state folder (the inlet's key with it, so senders keep working) |
| `dvara keeps` | the agents, the actors file, the rules, the state, asked with sarathi.toml's folders |
| `sparsh keeps` | its state folder, and adb's key, both halves |

Each place has an `id` that stays put, its `path`, `what` it holds in
plain words, and `leave_out`: names never worth carrying, matched
against each part of a path. **A browser's caches are the bytes:** your
2.6 GB of profiles are 0.5 GB without them, and no sign-in lives in a
cache. Chrome's `Singleton*` locks are left out too. Restored, they make
a profile read as "in use".

Sarathi adds only what is its own: its settings and state, Smritikosh's
`.env` and database (`sarathi smritikosh` set them up), and
`[backup] also`, the places that are yours and no program's. A signing
key in `~/keys` is one of those. **A program that can't say what it
keeps is named, never quietly skipped.** The backup is still written,
with *NOT IN IT: setu doesn't say what it keeps (an older setu: update
it)*, and the command exits 1.

## A copy that is never half a write

The house keeps running while a backup is made: Samay may finish a run
in the middle of it. Three rules keep each copy whole:

* **SQLite files** are found by their first sixteen bytes, not by name.
  Each is copied with SQLite's own backup. What sat only in the `-wal`
  file beside it (a run committed but not yet checkpointed) comes back
  inside the file, and the `-wal` is not carried.
* **Every other file** is read whole before it goes into the pack, so a
  file that grows while it's read can't break the tar. A file that
  vanishes mid-walk is passed over and named.
* **Smritikosh's database** goes in as `pg_dump`'s custom format. The
  dump comes from the container that runs it, chosen by the road: the
  unit's on Podman, the plain one on plain programs.

A place inside another is packed once, as its own. The backups' own
folder is never packed into itself.

## Locked like Setu's folder, so a night needs no passphrase

The first backup asks for a passphrase twice and makes a key pair. Both
halves go in `backup-key.json` beside sarathi.toml: the public half in
the clear, the private half sealed with a key from the passphrase
(scrypt, about half a second and 128 MB per guess). Every backup is
sealed to the **public** half. So Samay can make one at 02:30 with
nobody there and no passphrase anywhere in it, and only the passphrase
opens one.

Each file carries the sealed private half in its own header. A new
computer with nothing on it opens the file with the file and the
passphrase alone. `--new-passphrase` makes a new key, and older files
still open with the passphrase they were made with. **Forgetting the
passphrase loses every backup.** There is no other way in, and that's
deliberate.

The file is a 16-byte magic, a JSON header, then chunks of up to 1 MB.
Each chunk is AES-256-GCM. Its nonce is a prefix and a counter, and its
associated data is the header's hash, the counter and a last-chunk
flag. A chunk can't be moved, dropped or swapped, and a file cut short
says *"it was cut short"* instead of restoring half a house. Inside is a
tar: `keeps/<owner>/<id>/…`, `memory/smritikosh.dump`, and
`manifest.json` last.

## Restore puts things where they were, and moves nothing away unsaid

* **It refuses while anything `up` started is running.** A program
  writing into a folder that is being replaced would ruin both:
  *"Stop them first: `sarathi down`"*.
* **Each place goes back to its path, with this computer's home in
  place of the old one's.** Sarathi's own `sarathi.toml` is rewritten
  the same way (Smritikosh's checkout, Dvara's folders), because a Pi's
  user is often `pi`. Another program's files are that program's to
  say, so they are left as they came.
* **What is already there is moved aside** to
  `<name>.before-restore-<time>`, and listed. It is never deleted.
* **The memories go back with `pg_restore --clean`** into Smritikosh's
  container, made on its volume when there is none. On the Podman road
  that container is stopped again, so the unit gets the volume at `up`.
  If Smritikosh's checkout isn't on this computer yet, its `.env` waits
  (a `git clone` can still go there) and the restore says what to type:
  clone it, then `sarathi restore FILE --only smritikosh`.
* `--list` says what's in a file and changes nothing. `--only
  dvara,setu` puts back only those.

## Every night

Settings → **Check** has a **Backups** card. It shows the folder, the
newest file and its size, and **Back up now** / **Back up every night**.
The night button asks Samay, once, for a 02:30 schedule on its new
`backup` road (Samay's notes/12), before the 03:00 kept tests. Samay
asks with `POST /api/backup` and a key of its own (`backup.token`). That
key makes a backup and opens nothing else: not the page, not the
settings, not the doctor. And since a backup is sealed to a public key,
Samay holds nothing that opens one. A good night is NOTHING NEW. A night
that missed something is a failed run that says what, in Samay's
logbook and your morning messages. `[backup] keep = 7` keeps the newest
seven and removes the rest.

```toml
[backup]
folder = "~/sarathi-backups"       # a USB disk's folder works too
keep = 7                           # 0 keeps every one
also = ["~/keys"]                  # yours, no program's
```

`sarathi backup set` writes this table from a terminal, through the
same read-back check as the home page's Settings. **A DISK THAT ISN'T
THERE IS SAID, NOT MADE.** A folder under `/media`, `/mnt`, `/run/media`
or `/Volumes` whose disk isn't mounted would otherwise be made by the
backup, on this computer's own disk, under a name that says it's on the
USB one: the backup stops and says *"is its disk plugged in?"*, and the
night's run reports a failure. `sarathi backup list` and `sarathi backup
delete N|FILE` (or `--all-but N`) look after what's there by hand, after
a yes, and touch nothing in the folder but backups.

## Live receipt

A small house made by hand in a scratch home, backed up by the real
programs (each asked `keeps --json`). Its Smritikosh database was a
throwaway pgvector container holding two memories:

```
  yantra skills            1 files, 7 bytes
  setu home                2 files, 58 bytes          (a 3 MB Cache folder left out)
  samay state              1 files, 8.0 KB
  ...
  smritikosh database      its memories (pg_dump)
written: ~/backups/sarathi-…-165107.sarathi-backup (50.6 KB, 0s)
```

* **A wrong passphrase:** *error: that passphrase doesn't open this
  backup*, exit 2, nothing written.
* **Restore into a second, empty home:** every place came back under
  the new home. Samay's logbook row, committed only to the `-wal`, was
  in the restored file (`08:00 ran`). The cache and `serve.json` stayed
  out.
* **The database container and its volume deleted, then `restore
  --only smritikosh`:** the container was made again on a new volume,
  and `select said, v from memories` gave back `lives near RDU [1,2,3]`
  and `prefers aisle seats [0,1,0]`. The `.env` that was there sat
  beside it as `.env.before-restore-…`.
* **Samay's real `BackupRunner` against that home's page:** *NOTHING
  NEW / Backed up: …-165523.sarathi-backup (60.6 KB); 1 older removed*.
  With a wrong key: *the backup wasn't made: missing or wrong token*.

A lesson from the trial. A scratch `HOME` gives rootless Podman its own
storage but **not** its own runtime folder (`/run/user/<uid>`).
`podman system reset` under a scratch HOME reset the live house's
containers too, and they had to be restarted. Trials use a uniquely
named container in the real Podman, and never `system reset`.

## What is not here

* **Neo4j, MongoDB and Redis** (`sarathi smritikosh --full`) aren't in
  a backup. Yantra uses PostgreSQL alone, and the others' contents are
  Smritikosh's extras.
* **The programs themselves.** A backup holds what is yours. A new
  computer installs them first (the tutorial's Step 1), then restores.
* **Paths inside other programs' files** are not rewritten on a new
  home. Dvara's and Setu's settings name few, and they are theirs to
  say.
* **A browser profile in use** is copied as it is. A Chrome writing at
  that moment may leave its last cookie out. It signs in again on the
  next use if so.
* **Off-computer copies.** `[backup] folder` can be a USB disk's
  folder. Copying to another machine or a cloud is yours to choose:
  the file is safe to put anywhere, since only the passphrase opens it.
