# 36 — The bad days the doctor sees

The morning check (notes/28, Samay's notes/09) asks every program how it's
doing and tells the owner only what's newly wrong. Each of the house's
worst days was a problem that check could not see:

* **The memory store was wiped by a test.** 99 facts went to 0, and
  Smritikosh kept answering *up*. The doctor said *Smritikosh is
  answering*.
* **A backup didn't happen.** The backup schedule's failed run was a
  line among Samay's failures, but a backup that was never even started
  (the schedule paused, a restore that left it off) said nothing at all.
* **The ice-cream watches stopped themselves.** After five failed looks
  in a row Prahari paused them, as it should, and told the person once,
  in a notice. A week later, nobody remembered. The doctor said
  *Prahari is watching*.

Continues [28 — the doctor](28-the-doctor.md).

## Three new lines

**MEMORIES THAT FELL AWAY ARE RED.** The doctor keeps the most memories it
has seen in the last fourteen days (`doctor-counts.json` in Sarathi's
state folder). Below 70% of that is a loss, not a tidy-up, and it's red,
with the night's backup as the fix:

```
✗ needs fixing  memory: Smritikosh holds 3 memories; it held 99 on Fri 30 Oct.
                That is a loss, not a tidy-up
      fix: put them back from last night's backup: sarathi backup list, then
           sarathi restore FILE --only smritikosh
```

It stays red each morning until the memories come back, or until fourteen
days have passed and the lower number has become normal. Below 20
memories it never says anything, because a store that small moves by
whole handfuls when a few are forgotten.

**LAST NIGHT'S BACKUP, BY ITS FILE.** The newest pack in the backup
folder, by its own time. If it's more than 30 hours old, last night's
didn't happen, and that's amber. More than a week is red. No backup ever
is amber, because a disk that dies takes everything with it. This counts
the file, not the schedule, so a backup that was never started is seen
the same way as one that failed.

**A WATCH THAT STOPPED ITSELF IS AMBER.** `prahari status --json` now
lists `stopped_itself`: the watches and readings Prahari paused on its
own, each with why. A pause a person made (*paused by you*) isn't on that
list, because they know.

```
! worth a look  prahari: Prahari paused the watch "Mayfield ice cream under $6.19"
                by itself: failed 5 times in a row; last: timeout
      fix: Prahari's page: Mend or Resume it, or say so in a chat
```

The morning check tells only what's new, so each of these is said once
when it starts and again only after it has gone away and come back.

## Live receipt

`sarathi doctor` on the house, after the change:

```
✓ fine  prahari: Prahari is watching
✓ fine  memory: Smritikosh is answering, 84 memories
✓ fine  backup: the newest backup is from Thu 12 Nov 2026 02:30 (3 kept)
```

The house's one paused watch (Cary temp below 60) was paused by a person,
so it isn't listed.

## What is deliberately not here

* **No restore from the doctor.** A loss is red with the command that
  puts the memories back. Putting a database back is a step a person
  takes on purpose.
* **No count of facts and beliefs.** Smritikosh's health answers a count
  of memories, and that's the number that fell on the bad day. Its graph
  facts follow its memories.
* **No check that a backup can be opened.** That's the restore drill's
  job: it unpacks the newest pack into throwaway stores, which is far too
  slow for a morning check.

## Tests

`tests/test_doctor.py`, `TestTheBadDaysAreSeen`: last night's backup
missing is amber and a week is red. Memories that fell away are red until
they come back. A few tidied away is not a loss. A watch Prahari stopped
itself is amber, and a person's pause is not. Prahari's
`tests/test_cli.py`: `stopped_itself` names watches and readings paused on
their own, never a person's pause.
