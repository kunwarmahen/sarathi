# 09 — each by its own name

*Notes [02](02-one-file-two-processes.md) to
[06](06-one-bookmark.md) called the pieces by what they do: the clock,
the door, the page, the owner page, the home page. This note calls each
one by its project's name, everywhere a person reads it.*

## Two names for one thing

Every piece already had a name: Samay, Dvara, Yantra, Setu, Sarathi.
Sarathi then gave each a second one. `sarathi up` printed `clock` for
Samay and `door` for Dvara; sarathi.toml had `[clock]` and `[door]`;
the containers were `sarathi-clock` and `sarathi-door`. A person
looking for Dvara's page had to know that Dvara was "the door", and
that "owner" was Dvara's page and "home" was Sarathi's.

The second name also misled. `up` printed the door's line like every
other:

```
door   up at http://127.0.0.1:8770/  (unit sarathi-door)
```

It looks like a page to open. It isn't one: Dvara's port answers Samay
and Dvara's own page, and a browser sent there gets
`{"detail":"Not Found"}`.

## One name, and a line that says what it is

**EACH PIECE GOES BY ITS PROJECT'S NAME.** The same name is printed,
written in sarathi.toml, and given to the container:

| piece | printed | sarathi.toml | unit |
|---|---|---|---|
| Samay | `samay` | `[samay]` | `sarathi-samay` |
| Dvara | `dvara` | `[dvara]` | `sarathi-dvara` |
| Yantra | `yantra` | `[yantra]` | `sarathi-yantra` |
| Setu's page | `setu` | `pages.setu_port` | `sarathi-setu` |
| Dvara's page | `dvara-page` | `pages.dvara_port` | `sarathi-dvara-page` |
| Sarathi's page | `sarathi` | `pages.sarathi_port` | `sarathi-home` |

The command follows: `sarathi dvara` turns Dvara on, and
`init --yantra-port / --samay-port / --no-samay` move and switch off
the other two. Sarathi's own unit stays `sarathi-home`, since
`sarathi-sarathi` would say nothing.

**DVARA'S LINE HAS NO ADDRESS TO OPEN.** It gives the port and points
at the page that is yours:

```
dvara      up on 8770 (no page here; yours is dvara-page, below)  (unit sarathi-dvara)
```

With `[pages]` off there is no Dvara page, and it says to turn them on.

## Nothing set up under an old name is lost

**OLD NAMES STILL READ.** A sarathi.toml with `[web]`, `[clock]`,
`[door]`, `pages.home_port` or `pages.door_port` reads as the new names.
A file with both an old name and its new one is refused, since one of
them would be ignored. Sarathi writes only the new names.

**OLD CONTAINERS ARE STOPPED BEFORE THEY ARE REMOVED.** `up` and `down`
look for `sarathi-clock`, `sarathi-door`, `sarathi-page` and
`sarathi-owner`. Each one found is stopped, then its unit file and env
file are removed. A unit file removed while its container ran would
leave the container holding the port the new one needs.

**OLD RECORDS TAKE THEIR NEW NAMES.** On the process road, a record or
log that an older `up` wrote as `clock.json` is renamed to
`samay.json`, so `down` still stops what was started.

## Not changed

The names inside the code (`config.door`, `clock_port`) stay as they
are: nobody reads them but the code, and renaming them would change
every line for no one's benefit. The siblings' own descriptions still
say what each name means: Samay is time, Dvara is a door.

## Live receipt

The Podman road, with the old containers running, after the tables in
sarathi.toml were renamed by hand:

```
$ sarathi up
sarathi-clock stopped and removed: it is sarathi-samay now
sarathi-door stopped and removed: it is sarathi-dvara now
sarathi-page stopped and removed: it is sarathi-yantra now
sarathi-owner stopped and removed: it is sarathi-dvara-page now
units rewritten from sarathi.toml
samay      up at http://127.0.0.1:8780/#token=…  (unit sarathi-samay)
dvara      up on 8770 (no page here; yours is dvara-page, below)  (unit sarathi-dvara)
yantra     up at http://127.0.0.1:8321/  (unit sarathi-yantra)
setu       already running at http://127.0.0.1:8775/#token=…  (unit sarathi-setu)
dvara-page up at http://127.0.0.1:8785/#token=…  (unit sarathi-dvara-page)
sarathi    restarting with the new settings  (unit sarathi-home)
sarathi    up at http://127.0.0.1:8760/#token=…  (unit sarathi-home)
```

`podman ps` then shows only the new names. Samay still reaches Dvara on
the shared network, now as `http://sarathi-dvara:8765`, and Dvara's page
has `DVARA_URL=http://sarathi-dvara:8765`. The image did not need
rebuilding: the names are given to the containers by `up`.

Tests: `tests/test_names.py` (old names read, both at once refused, an
old record found, Dvara's line), and in `tests/test_podman.py` an old
unit stopped before it is removed. 167 pass (was 160).
