"""`sarathi backup drill`: open last night's backup somewhere harmless, and count what came back.

A nightly backup proves a file was written. It doesn't prove the file
opens, that every program's places are in it, or that Smritikosh's dump
restores. The only way to know is to put it back, and the one place it
must never be put back is over the house. So a drill unpacks the newest
backup (or the one named) into a throwaway folder and restores the
database into a throwaway container, counts what it finds, and removes
both.

NOTHING LIVE IS TOUCHED. The files go to a fresh folder under Sarathi's
state, extracted with tarfile's "data" filter (nothing lands outside it,
no link points out). Each SQLite file is opened read-only there, checked
with ``PRAGMA quick_check``, and its rows counted. Smritikosh's dump is
restored into a NEW Postgres container from the same image as the live
one, with no network and no volume, named ``sarathi-drill-<stamp>``. Its
``events`` (the memories) are counted, and then the container is removed.
The live database is never connected to. This is the rule a test once
broke, when it wiped the live store, and it's the reason the drill exists.

A PERSON OPENS IT. A backup is sealed to a key only your passphrase
opens, so the drill asks for it (or reads ``$SARATHI_BACKUP_PASSPHRASE``,
like restore). It can't run alone at night, so the doctor reminds you
instead. The last drill is kept (``drill.json``), and Check says when it
was, amber after 35 days or if it found something wrong.

WHAT IT COUNTS, AND AGAINST WHAT. Every place the manifest lists (missing
is a finding). The rows of each program's own tables, by the names they
hold: schedules, watches, readings, runs, conversations. The memories in
the dump, beside how many the live store has now. Fewer memories in a
backup than now is fine (it's last night's). Far fewer is the finding.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import tarfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sarathi import backup

RECORD = "drill.json"
#: After this many days without a drill, Check says so.
DUE_DAYS = 35
#: The tables a person recognises, by the name each program gives them.
TABLES = {"schedules": "schedules", "runs": "runs", "watches": "watches",
          "indriyas": "readings", "sessions": "conversations", "events": "memories"}
#: A backup holding less than this share of the memories the live store
#: has now is a finding (last night's may hold a few less).
MEMORY_SHARE = 0.7
PG_WAIT = 60


@dataclass
class Drilled:
    file: str
    made: str = ""
    ok: bool = True
    places: int = 0
    missing: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    sqlite_bad: list[str] = field(default_factory=list)
    memories: int | None = None
    memories_now: int | None = None
    problems: list[str] = field(default_factory=list)
    at: float = 0.0

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


def _is_sqlite(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def count_sqlite(path: Path) -> tuple[bool, dict[str, int]]:
    """(it checks out, rows per recognised table) for one SQLite file,
    opened read-only where the drill put it."""
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return False, {}
    try:
        ok = db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        names = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        counts = {}
        for name in names:
            if name in TABLES:
                counts[TABLES[name]] = db.execute(
                    f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        return ok, counts
    except sqlite3.Error:
        return False, {}
    finally:
        db.close()


def restore_dump(dump: Path, image: str, user: str, stamp: str,
                 run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                 sleep: Callable[[float], None] = time.sleep) -> tuple[int | None, str]:
    """(memories in it, why not) -- the dump restored into a container of
    its own, counted, and removed. Never the live database."""
    name = f"sarathi-drill-{stamp}"
    started = run(["podman", "run", "-d", "--rm", "--name", name, "--network", "none",
                   "-e", f"POSTGRES_USER={user}", "-e", "POSTGRES_PASSWORD=drill",
                   "-e", f"POSTGRES_DB={user}", image],
                  capture_output=True, text=True, check=False)
    if started.returncode != 0:
        return None, f"a throwaway database couldn't start: {started.stderr.strip()[-200:]}"
    try:
        for _ in range(PG_WAIT):
            ready = run(["podman", "exec", name, "pg_isready", "-U", user],
                        capture_output=True, text=True, check=False)
            if ready.returncode == 0:
                break
            sleep(1)
        else:
            return None, f"the throwaway database didn't come up within {PG_WAIT}s"
        sleep(2)                     # pg_isready answers before init's restart
        with dump.open("rb") as handle:
            done = run(["podman", "exec", "-i", name, "pg_restore", "--no-owner", "-U", user,
                        "-d", user], stdin=handle, capture_output=True, check=False)
        if done.returncode not in (0, 1):     # 1: warnings (an extension's comment)
            err = done.stderr.decode("utf-8", "replace") if isinstance(done.stderr, bytes) \
                else str(done.stderr)
            return None, f"the dump didn't restore: {err.strip()[-200:]}"
        counted = run(["podman", "exec", name, "psql", "-U", user, "-d", user, "-Atc",
                       "SELECT COUNT(*) FROM events"], capture_output=True, text=True,
                      check=False)
        if counted.returncode != 0 or not counted.stdout.strip().isdigit():
            return None, "the restored database has no memories table"
        return int(counted.stdout.strip()), ""
    finally:
        run(["podman", "rm", "-f", name], capture_output=True, check=False)


def live_database(config: Any, run=subprocess.run) -> tuple[str, str] | None:
    """(image, user) of Smritikosh's live database, to start a twin of;
    None when there isn't one. Only ``inspect``: nothing connects to it."""
    from sarathi import podman
    name = podman.UNITS["smritikosh-db"] if config.road == "podman" \
        else config.smritikosh.database
    seen = run(["podman", "inspect", name, "--format",
                "{{.ImageName}}\t{{range .Config.Env}}{{.}} {{end}}"],
               capture_output=True, text=True, check=False)
    if seen.returncode != 0 or "\t" not in seen.stdout:
        return None
    image, env = seen.stdout.strip().split("\t", 1)
    user = next((e.split("=", 1)[1] for e in env.split() if e.startswith("POSTGRES_USER=")),
                "postgres")
    return image, user


def drill(file: Path, passphrase: str, scratch: Path, *, config: Any = None,
          memories_now: int | None = None, run=subprocess.run,
          sleep=time.sleep) -> Drilled:
    """Open ``file`` in ``scratch`` (made fresh, removed after), count, and
    restore its memories into a throwaway container."""
    out = Drilled(file=str(file), at=time.time(), memories_now=memories_now)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    where = scratch / f"drill-{stamp}"
    where.mkdir(mode=0o700, parents=True)
    try:
        try:
            with file.open("rb") as raw, backup.Opened(raw, passphrase) as plain, \
                    tarfile.open(fileobj=plain, mode="r|") as tar:
                for member in tar:
                    try:
                        tar.extract(member, where, filter="data")
                    except tarfile.FilterError as exc:
                        out.problems.append(f"{member.name} refused: {exc}")
        except (backup.BackupError, OSError, tarfile.TarError, ValueError) as exc:
            out.ok = False
            out.problems.append(f"it didn't open: {exc}")
            return out
        try:
            manifest = json.loads((where / "manifest.json").read_text())
        except (OSError, ValueError):
            out.ok = False
            out.problems.append("it has no manifest: it didn't finish being made")
            return out
        out.made = str(manifest.get("made") or "")
        for row in manifest.get("places") or []:
            if row.get("kind") == "missing":
                out.missing.append(f"{row.get('owner')} {row.get('id')}")
            else:
                out.places += 1
        out.problems += [f"not in it when made: {p}" for p in manifest.get("problems") or []]
        for path in sorted((where / "keeps").rglob("*")) if (where / "keeps").is_dir() else []:
            if path.is_file() and _is_sqlite(path):
                ok, counts = count_sqlite(path)
                if not ok:
                    out.sqlite_bad.append(str(path.relative_to(where / "keeps")))
                for key, n in counts.items():
                    out.counts[key] = out.counts.get(key, 0) + n
        dump = where / backup.DUMP
        if dump.is_file() and config is not None:
            twin = live_database(config, run)
            if twin is None:
                out.problems.append("the memories' dump is in it, but there's no database "
                                    "image here to restore it into")
            else:
                out.memories, why = restore_dump(dump, *twin, stamp, run=run, sleep=sleep)
                if why:
                    out.problems.append(why)
        elif manifest.get("memory") and not dump.is_file():
            out.problems.append("the manifest says the memories are in it, and they aren't")
        # a place missing when the backup was made was said then, and isn't
        # a backup that fails to come back; a damaged file is
        if out.sqlite_bad:
            out.ok = False
        if (out.memories is not None and memories_now
                and out.memories < memories_now * MEMORY_SHARE):
            out.ok = False
            out.problems.append(f"it holds {out.memories} memories, and the house has "
                                f"{memories_now} now")
        if any(p.startswith(("the dump didn't", "a throwaway", "the restored", "the manifest"))
               for p in out.problems):
            out.ok = False
        return out
    finally:
        shutil.rmtree(where, ignore_errors=True)


def keep(record: Path, drilled: Drilled) -> None:
    record.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    staged = record.with_suffix(".tmp")
    staged.write_text(json.dumps(drilled.as_json(), indent=2))
    staged.replace(record)


def last(record: Path) -> dict | None:
    try:
        data = json.loads(record.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def lines(d: Drilled) -> list[str]:
    out = [f"{'✓ it opens' if d.ok else '✗ NOT ALL THERE'}: {Path(d.file).name}"
           + (f" (made {d.made})" if d.made else "")]
    out.append(f"  {d.places} places came back" + (
        f"; not there when it was made: {', '.join(d.missing)}" if d.missing else ""))
    if d.counts:
        out.append("  " + ", ".join(f"{n} {k}" for k, n in sorted(d.counts.items())))
    if d.memories is not None:
        out.append(f"  {d.memories} memories restored into a throwaway database"
                   + (f" (the house has {d.memories_now} now)" if d.memories_now else ""))
    out += [f"  damaged: {b}" for b in d.sqlite_bad]
    out += [f"  {p}" for p in d.problems]
    out.append("  nothing here was changed; the drill's copy is gone")
    return out
