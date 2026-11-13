"""`sarathi backup drill`: a backup opened somewhere harmless, and counted.

The bias: the one place a drill must never write is the live house. Every
test hands the drill a fake `podman` and checks what it was asked to do:
a NEW container from the live one's image, no network, removed after.
Nothing outside the drill's own throwaway folder may change. The second
bias is a backup that looks fine and isn't: a place missing, a damaged
SQLite file, fewer memories than the house has, a dump that won't
restore. Each of those makes the drill say NOT ALL THERE.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from test_backup import WORDS, house

from sarathi import backup, drill
from sarathi.config import Config, Smritikosh


@pytest.fixture(autouse=True)
def quick_scrypt(monkeypatch):
    monkeypatch.setattr(backup, "SCRYPT", {"n": 2 ** 10, "r": 8, "p": 1})


class Podman:
    """A fake podman: answers each command, and remembers every one."""

    def __init__(self, memories: int = 84, restore_code: int = 0) -> None:
        self.memories, self.restore_code = memories, restore_code
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        out, code = "", 0
        if argv[:2] == ["podman", "inspect"]:
            out = ("docker.io/pgvector/pgvector:pg17\tPOSTGRES_USER=smritikosh "
                   "POSTGRES_DB=smritikosh POSTGRES_PASSWORD=x")
        elif "pg_restore" in argv:
            code = self.restore_code
        elif "psql" in argv:
            out = str(self.memories)
        text = kw.get("text")
        return subprocess.CompletedProcess(argv, code, out if text else out.encode(),
                                           "" if text else b"restore failed")


def made(tmp_path, *, dump=True):
    home = tmp_path / "home"
    places = house(home)
    key = backup.make_key(WORDS)

    def fake_dump(config, into: Path):
        if dump:
            into.write_bytes(b"PGDMP fake")
        return None
    config = Config("ollama", smritikosh=Smritikosh(checkout=str(tmp_path)))
    out = backup.make(places, key, tmp_path / "backups", home=home, config=config,
                      dump=fake_dump, stores=lambda c, s: ([], []))
    return home, out.file if hasattr(out, "file") else sorted(
        (tmp_path / "backups").glob("*.sarathi-backup"))[-1]


def run_drill(tmp_path, podman, **kw):
    _, file = made(tmp_path, dump=kw.pop("dump", True))
    return drill.drill(Path(file), WORDS, tmp_path / "drills", config=Config("ollama"),
                       run=podman, sleep=lambda s: None, **kw)


class TestItOpensAndCounts:
    def test_a_good_backup_comes_back_counted(self, tmp_path):
        podman = Podman(memories=84)
        done = run_drill(tmp_path, podman, memories_now=90)
        assert done.ok, done.problems
        assert done.places == 3 and done.missing == ["prahari state"]
        assert done.counts.get("runs") == 1        # samay's logbook, read in the copy
        assert done.memories == 84

    def test_the_database_is_a_throwaway_twin_and_is_removed(self, tmp_path):
        podman = Podman()
        run_drill(tmp_path, podman)
        started = next(c for c in podman.calls if c[:2] == ["podman", "run"])
        assert "--network" in started and started[started.index("--network") + 1] == "none"
        assert started[-1] == "docker.io/pgvector/pgvector:pg17"
        name = started[started.index("--name") + 1]
        assert name.startswith("sarathi-drill-")
        assert ["podman", "rm", "-f", name] in podman.calls
        # never the live database: only inspected, never exec'd into
        live = "sarathi-smritikosh-db"
        assert not any(c[:3] == ["podman", "exec", live] or
                       (c[:2] == ["podman", "exec"] and live in c) for c in podman.calls)

    def test_its_copy_is_gone_and_the_house_unchanged(self, tmp_path):
        home, file = made(tmp_path)
        before = sorted(str(p) for p in home.rglob("*"))
        drill.drill(Path(file), WORDS, tmp_path / "drills", config=Config("ollama"),
                    run=Podman(), sleep=lambda s: None)
        assert sorted(str(p) for p in home.rglob("*")) == before
        assert list((tmp_path / "drills").iterdir()) == []


class TestABackupThatDoesntAllComeBack:
    def test_far_fewer_memories_than_now(self, tmp_path):
        done = run_drill(tmp_path, Podman(memories=3), memories_now=84)
        assert not done.ok and "holds 3 memories" in " ".join(done.problems)

    def test_a_dump_that_wont_restore(self, tmp_path):
        done = run_drill(tmp_path, Podman(restore_code=2))
        assert not done.ok and "didn't restore" in " ".join(done.problems)

    def test_the_wrong_passphrase_opens_nothing(self, tmp_path):
        _, file = made(tmp_path)
        done = drill.drill(Path(file), "not the words", tmp_path / "drills",
                           config=Config("ollama"), run=Podman(), sleep=lambda s: None)
        assert not done.ok and "didn't open" in done.problems[0]

    def test_a_damaged_sqlite_file_is_named(self, tmp_path):
        bad = tmp_path / "bad.sqlite3"
        bad.write_bytes(b"SQLite format 3\x00" + b"\x00" * 200)
        ok, _ = drill.count_sqlite(bad)
        assert ok is False


class TestTheAnswerIsKept:
    def test_kept_and_read_back_for_check(self, tmp_path):
        done = drill.Drilled(file="x.sarathi-backup", ok=True, memories=84, places=9, at=1.0)
        drill.keep(tmp_path / "drill.json", done)
        assert drill.last(tmp_path / "drill.json")["memories"] == 84
        assert drill.last(tmp_path / "nothing.json") is None
        assert "nothing here was changed" in drill.lines(done)[-1]
