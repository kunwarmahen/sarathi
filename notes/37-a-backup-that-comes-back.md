# 37 — A backup that comes back

Every night at 02:30 a backup is written, and the morning check says
whether it was (notes/36). That proves a file exists. It doesn't prove the
file opens, that each program's places are inside it, or that
Smritikosh's dump restores. The only way to know is to put the backup
back. The one place it must never be put back is over the house, because
a test that once touched the live database wiped it.

Continues [36 — the bad days the doctor sees](36-the-bad-days-the-doctor-sees.md).

## The drill

```
sarathi backup drill          the newest backup
sarathi backup drill 2        the second newest (sarathi backup list numbers them)
sarathi backup drill FILE     one by its name
sarathi backup drill --json   sarathi.backup.drill.v1
```

**NOTHING LIVE IS TOUCHED.** The pack is unpacked into a fresh folder
under Sarathi's state, with tarfile's *data* filter, so nothing lands
outside it and no link points out. Each SQLite file is opened read-only
there, checked with `PRAGMA quick_check`, and the tables a person would
recognise are counted (schedules, runs, watches, readings,
conversations). Smritikosh's dump is restored into a **new** container,
`sarathi-drill-<time>`. It's started from the same image as the live
database (`podman inspect` reads the image, and nothing connects to the
live one), with `--network none` and no volume. Its `events` (the
memories) are counted, and then it's removed. When the drill ends, the
folder is removed too.

**A PERSON OPENS IT.** A backup is sealed to a key that only your
passphrase opens. That's what lets a night need no passphrase, and it's
also why a drill can't run alone. So the drill asks (or reads
`$SARATHI_BACKUP_PASSPHRASE`, as `restore` does), and the doctor reminds
you: Check shows the last drill, amber after 35 days, red if it failed.

**WHAT FAILS IT.** A pack that doesn't open (a wrong passphrase, a
truncated file). A SQLite file that fails its check. A dump that won't
restore. A backup holding fewer than 70% of the memories the house has
now (last night's may hold a few less; far fewer is a loss that the
backup captured). A place that was missing when the backup was made is
listed, but doesn't fail the drill: it was said when the backup was
made, and it's not a backup failing to come back.

## Live receipt

The house's passphrase is the owner's, so the receipt below is a scratch
backup, made with a throwaway key, of one small folder plus a real
`pg_dump` of the live memory database (read-only, the same dump the
nightly backup takes). It was then drilled with the real Podman:

```
made sarathi-linux-al-ml-beast-20261113-062452.sarathi-backup memory: True [] 0.2s
✓ it opens: sarathi-linux-al-ml-beast-20261113-062452.sarathi-backup (made 2026-11-13T06:24:52-0500)
  1 places came back
  9 schedules
  84 memories restored into a throwaway database (the house has 84 now)
  nothing here was changed; the drill's copy is gone
drill 4.9s
```

Afterwards, `podman ps -a` showed no `sarathi-drill-*` container.

## What is deliberately not here

* **No drill at night.** It needs the passphrase, and a passphrase kept
  where a schedule could read it would make the seal decoration.
* **Neo4j's and MongoDB's folders aren't started.** Under `[smritikosh]
  full` they're in the pack, and the drill counts them as places that
  came back. Starting a graph database from a copied folder is a
  restore's job. The memories that answer questions are Postgres's, and
  those are restored.
* **No comparison with every table now.** Only the memories are counted
  against the house, because that's the number that fell on the bad day.

## Tests

`tests/test_drill.py`: a good backup comes back counted. The database is
a throwaway twin (from the live image, no network, removed), and the live
one is never exec'd into. Its copy is gone and the house is unchanged.
Far fewer memories than now, a dump that won't restore, a wrong
passphrase and a damaged SQLite file each make it fail. The answer is
kept and read back for Check. `tests/test_doctor.py`,
`TestABackupNobodyOpened`: never drilled is amber, failed is red, long
ago is amber, lately is green, and with no backup at all the drill line
says nothing.
