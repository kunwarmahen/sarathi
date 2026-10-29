"""`sarathi backup` and `sarathi restore`: the house in one locked file.

The bias these tests encode: A BACKUP YOU FIND OUT ABOUT ON THE DAY YOU
NEED IT. Every failure here is one that is silent until a disk has died:
a file that opens for a wrong passphrase or not for the right one, a
file cut short that restores half a house, a SQLite file copied mid-write
(its last hour only in the -wal beside it), caches that make the file
too big to keep, a program that couldn't say what it keeps and was
quietly left out, a restore that deleted what was there, and a restore
onto a new computer that put things under the old one's home. And the
backups' own upkeep: a delete that takes a file that isn't a backup, and
a USB disk left unplugged that quietly gets its backup on this computer.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
from pathlib import Path

import pytest

from sarathi import backup, cli
from sarathi.config import parse
from sarathi.siblings import Found, Sibling

from conftest import program

WORDS = "a few plain words"


@pytest.fixture(autouse=True)
def quick_scrypt(monkeypatch):
    """The real cost is half a second a key; a key's own params say what
    opened it, so a cheap one here proves the same thing."""
    monkeypatch.setattr(backup, "SCRYPT", {"n": 2 ** 10, "r": 8, "p": 1})


@pytest.fixture
def key():
    return backup.make_key(WORDS)


def house(home: Path) -> list[backup.Place]:
    """A small house: a profile with caches, a SQLite logbook mid-write, a file."""
    setu = home / ".local/state/setu"
    (setu / "profiles/amazon/Default/Cache").mkdir(parents=True)
    (setu / "profiles/amazon/Default/Cache/data_0").write_bytes(b"x" * 5000)
    (setu / "profiles/amazon/Default/Cookies").write_bytes(b"signed in")
    (setu / "profiles/amazon/SingletonLock").symlink_to("beast-1234")
    (setu / "vault.json").write_text('{"gmail:personal": {"secret": "refresh"}}')
    samay = home / ".samay"
    samay.mkdir()
    db = sqlite3.connect(samay / "samay.sqlite3")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE runs (said TEXT)")
    db.execute("INSERT INTO runs VALUES ('the 08:00 run')")
    db.commit()                       # in the -wal only: not checkpointed, still open
    (samay / "serve.json").write_text('{"pid": 4242}')
    actors = home / "dvara/actors.toml"
    actors.parent.mkdir()
    actors.write_text('[mahen]\ntelegram = "1"\n')
    places = [backup.Place("setu", "home", str(setu), "accounts",
                           ["Cache", "Singleton*", "logs"]),
              backup.Place("samay", "state", str(samay), "schedules", ["serve.json"]),
              backup.Place("dvara", "actors", str(actors), "everyone"),
              backup.Place("prahari", "state", str(home / ".prahari"), "watches")]
    house.db = db                     # kept open, as a running Samay keeps it
    return places


def made(tmp_path, key, **kw):
    home = tmp_path / "old-home"
    places = house(home)
    return home, backup.make(places, key, tmp_path / "backups", home=home, **kw)


# ---- the lock -----------------------------------------------------------------------


class TestTheLock:
    def test_it_opens_with_its_passphrase_and_names_what_is_in_it(self, tmp_path, key):
        home, out = made(tmp_path, key)
        manifest = backup.peek(out.file, WORDS)
        rows = {(r["owner"], r["id"]): r for r in manifest["places"]}
        assert rows[("dvara", "actors")]["kind"] == "file"
        assert rows[("prahari", "state")]["kind"] == "missing"
        assert manifest["home"] == str(home)
        assert out.file.stat().st_mode & 0o777 == 0o600

    def test_a_wrong_passphrase_opens_nothing(self, tmp_path, key):
        _, out = made(tmp_path, key)
        with pytest.raises(backup.BackupError, match="doesn't open"):
            backup.peek(out.file, "the wrong words")

    def test_nothing_readable_is_in_the_file(self, tmp_path, key):
        _, out = made(tmp_path, key)
        raw = out.file.read_bytes()
        assert b"refresh" not in raw and b"signed in" not in raw and b"vault" not in raw

    def test_a_file_cut_short_says_so_instead_of_restoring_half(self, tmp_path, key):
        _, out = made(tmp_path, key)
        raw = out.file.read_bytes()
        out.file.write_bytes(raw[: len(raw) - 40])
        with pytest.raises(backup.BackupError, match="cut short|damaged"):
            backup.peek(out.file, WORDS)

    def test_a_changed_byte_is_refused(self, tmp_path, key):
        _, out = made(tmp_path, key)
        raw = bytearray(out.file.read_bytes())
        raw[-100] ^= 1
        out.file.write_bytes(bytes(raw))
        with pytest.raises(backup.BackupError, match="damaged"):
            backup.peek(out.file, WORDS)

    def test_a_short_passphrase_is_refused_before_a_key_is_made(self):
        with pytest.raises(backup.BackupError, match="8 characters"):
            backup.make_key("short")

    def test_sealing_needs_only_the_public_half(self, tmp_path, key):
        """Samay at 03:00 has the key file and no passphrase: enough to make one."""
        backup.save_key(key, tmp_path / "backup-key.json")
        read = backup.read_key(tmp_path / "backup-key.json")
        _, out = made(tmp_path, read)
        assert backup.peek(out.file, WORDS)["format"] == backup.FORMAT

    def test_every_file_opens_alone_on_a_computer_with_no_key(self, tmp_path, key):
        """A new computer has the file and the passphrase, nothing else."""
        _, out = made(tmp_path, key)
        assert backup.read_key(tmp_path / "nowhere.json") is None
        assert backup.peek(out.file, WORDS)["places"]


# ---- what goes in -------------------------------------------------------------------


class TestWhatGoesIn:
    def test_caches_and_chromes_locks_stay_out_and_the_sign_in_goes_in(self, tmp_path, key):
        _, out = made(tmp_path, key)
        setu = next(t for t in out.taken if t.place.owner == "setu")
        assert setu.files == 2                  # Cookies and vault.json
        assert setu.bytes < 5000

    def test_a_sqlite_files_wal_is_folded_in_not_carried(self, tmp_path, key):
        """What is only in the -wal comes back inside the file (TestTheRestore)."""
        _, out = made(tmp_path, key)
        samay = next(t for t in out.taken if t.place.owner == "samay")
        assert samay.files == 1                 # samay.sqlite3; no -wal, -shm, serve.json

    def test_the_backups_own_folder_is_never_packed_into_itself(self, tmp_path, key):
        home = tmp_path / "home"
        (home / "backups").mkdir(parents=True)
        (home / "backups" / "old.sarathi-backup").write_bytes(b"y" * 9000)
        (home / "notes.txt").write_text("mine")
        out = backup.make([backup.Place("you", "also-1", str(home))], key, home / "backups")
        assert out.taken[0].files == 1

    def test_a_place_inside_another_is_packed_once(self, tmp_path, key):
        home = tmp_path / "home"
        (home / "skills").mkdir(parents=True)
        (home / "skills" / "a.md").write_text("skill")
        out = backup.make([backup.Place("yantra", "all", str(home)),
                           backup.Place("yantra", "skills", str(home / "skills"))],
                          key, tmp_path / "b")
        assert [t.files for t in out.taken] == [0, 1]

    def test_a_socket_is_passed_over(self, tmp_path, key):
        home = tmp_path / "h"
        home.mkdir()
        (home / "rules.toml").write_text("never = []")
        with socket.socket(socket.AF_UNIX) as s:
            s.bind(str(home / "adb.sock"))
            out = backup.make([backup.Place("sparsh", "state", str(home))], key,
                              tmp_path / "b")
        assert out.taken[0].files == 1

    def test_the_newest_n_are_kept_and_older_removed(self, tmp_path):
        folder = tmp_path / "b"
        folder.mkdir()
        for i in range(5):
            f = folder / f"sarathi-beast-2026102{i}-030000{backup.SUFFIX}"
            f.write_bytes(b"")
            os.utime(f, (1000 + i, 1000 + i))
        (folder / "notes.txt").write_text("not a backup")
        gone = backup.prune(folder, 2)
        assert sorted(gone) == [f"sarathi-beast-2026102{i}-030000{backup.SUFFIX}"
                                for i in range(3)]
        assert {p.name for p in folder.iterdir()} == {
            "notes.txt", *(f"sarathi-beast-2026102{i}-030000{backup.SUFFIX}" for i in (3, 4))}
        assert backup.prune(folder, 0) == []


# ---- each program says -------------------------------------------------------------


class TestEachProgramSays:
    SETU = Sibling("setu", "setu", "the bridge", status_format="setu.status.v1")

    def test_what_a_program_says_it_keeps_is_what_is_taken(self, tmp_path):
        said = {"format": "setu.keeps.v1", "keeps": [
            {"id": "home", "path": "/h/.local/state/setu", "what": "accounts",
             "leave_out": ["Cache"]}]}
        setu = program(tmp_path / "bin", "setu", json.dumps(said))
        places = backup.ask_keeps(Found(self.SETU, program=str(setu)))
        assert places == [backup.Place("setu", "home", "/h/.local/state/setu", "accounts",
                                       ["Cache"])]

    def test_an_older_program_is_named_never_quietly_left_out(self, tmp_path):
        setu = program(tmp_path / "bin", "setu", "usage: setu [-h]", code=2)
        with pytest.raises(backup.BackupError, match="doesn't say what it keeps.*update"):
            backup.ask_keeps(Found(self.SETU, program=str(setu)))

    def test_another_programs_format_is_refused(self, tmp_path):
        setu = program(tmp_path / "bin", "setu", json.dumps({"format": "samay.keeps.v1"}))
        with pytest.raises(backup.BackupError):
            backup.ask_keeps(Found(self.SETU, program=str(setu)))

    def test_dvara_is_asked_with_the_folders_sarathi_toml_names(self, world):
        seen = world / "dvara-asked"
        dvara = world / "bin" / "dvara"
        dvara.write_text(f"#!/bin/sh\necho \"$@\" > {seen}\n"
                         "echo '{\"format\": \"dvara.keeps.v1\", \"keeps\": []}'\n")
        dvara.chmod(0o755)
        for name in ("yantra", "setu", "samay"):
            program(world / "bin", name, json.dumps({"format": f"{name}.keeps.v1",
                                                     "keeps": []}))
        config = parse('[model]\nprovider = "ollama"\n[dvara]\non = true\n'
                       f'root = "{world}/agents"\n')
        _, problems = cli.backup_places(config)
        assert problems == []
        assert f"--root {world}/agents" in seen.read_text()
        assert seen.read_text().rstrip().endswith("keeps --json")

    def test_a_missing_needed_program_is_a_problem_an_optional_one_is_not(self, world):
        program(world / "bin", "yantra", json.dumps({"format": "yantra.keeps.v1",
                                                     "keeps": []}))
        _, problems = cli.backup_places(parse('[model]\nprovider = "ollama"\n'))
        assert len(problems) == 2 and all("isn't on this computer" in p for p in problems)
        assert not any("sparsh" in p or "prahari" in p for p in problems)

    def test_sarathis_own_and_yours_are_after_theirs(self, world):
        config = parse('[model]\nprovider = "ollama"\n[backup]\nalso = ["~/keys"]\n')
        own = backup.own_places(config)
        assert [(p.owner, p.id) for p in own] == [("sarathi", "config"),
                                                 ("sarathi", "state"), ("you", "also-1")]
        assert own[2].path == str(Path("~/keys").expanduser())
        assert "units" in own[0].leave_out


# ---- the restore --------------------------------------------------------------------


class TestTheRestore:
    def test_everything_comes_back_under_this_computers_home(self, tmp_path, key):
        old = tmp_path / "old-home"
        places = house(old)
        out = backup.make(places, key, tmp_path / "b", home=old)
        manifest = backup.peek(out.file, WORDS)
        # as if made on a computer whose home was old-home
        new = tmp_path / "new-home"
        restored = _unpack_from(out.file, old, new)
        assert (new / ".local/state/setu/profiles/amazon/Default/Cookies").read_bytes() \
            == b"signed in"
        assert not (new / ".local/state/setu/profiles/amazon/Default/Cache").exists()
        assert not (new / ".local/state/setu/profiles/amazon/SingletonLock").is_symlink()
        assert (new / "dvara/actors.toml").read_text().startswith("[mahen]")
        assert not (new / ".samay/serve.json").exists()
        db = sqlite3.connect(new / ".samay/samay.sqlite3")
        assert db.execute("SELECT said FROM runs").fetchall() == [("the 08:00 run",)]
        assert restored.moved_aside == [] and manifest["places"]

    def test_what_was_there_is_moved_aside_never_deleted(self, tmp_path, key):
        old = tmp_path / "old-home"
        out = backup.make(house(old), key, tmp_path / "b", home=old)
        new = tmp_path / "new-home"
        (new / "dvara").mkdir(parents=True)
        (new / "dvara/actors.toml").write_text("the one that was here")
        restored = _unpack_from(out.file, old, new, stamp="20261023-0300")
        aside = new / "dvara/actors.toml.before-restore-20261023-0300"
        assert aside.read_text() == "the one that was here"
        assert str(aside) in restored.moved_aside

    def test_only_puts_back_the_programs_named(self, tmp_path, key):
        old = tmp_path / "old-home"
        out = backup.make(house(old), key, tmp_path / "b", home=old)
        new = tmp_path / "new-home"
        _unpack_from(out.file, old, new, only={"dvara"})
        assert (new / "dvara/actors.toml").exists()
        assert not (new / ".samay").exists() and not (new / ".local").exists()

    def test_smritikoshs_settings_wait_for_its_checkout(self, tmp_path, key):
        old = tmp_path / "old-home"
        (old / "smritikosh").mkdir(parents=True)
        (old / "smritikosh/.env").write_text("POSTGRES_URL=postgresql://u:p@h/db\n")
        out = backup.make([backup.Place("smritikosh", "env", str(old / "smritikosh/.env"))],
                          key, tmp_path / "b", home=old)
        new = tmp_path / "new-home"
        restored = _unpack_from(out.file, old, new)
        assert not (new / "smritikosh").exists()     # a git clone can still go there
        assert "kept back" in restored.lines[0]

    def test_restore_refuses_while_the_house_runs(self, world, monkeypatch, capsys):
        f = world / "x.sarathi-backup"
        f.write_bytes(b"")
        monkeypatch.setattr(cli.services, "running", lambda: [{"name": "samay",
                                                               "alive": True}])
        assert cli.main(["restore", str(f)]) == 2
        assert "sarathi down" in capsys.readouterr().err


def _unpack_from(file: Path, old: Path, new: Path, **kw) -> backup.Restored:
    restored = backup.unpack(file, WORDS, home=new, **kw)
    backup.finish(restored)
    return restored


# ---- the memories -------------------------------------------------------------------


class TestTheMemories:
    CONFIG = '[model]\nprovider = "ollama"\n[smritikosh]\ncheckout = "{checkout}"\n'

    def _config(self, tmp_path):
        checkout = tmp_path / "smritikosh"
        checkout.mkdir()
        (checkout / ".env").write_text(
            "POSTGRES_URL=postgresql+asyncpg://smritikosh:pw@localhost:5432/smritikosh\n")
        return parse(self.CONFIG.format(checkout=checkout))

    def test_the_dump_is_of_the_container_the_road_runs(self, tmp_path, key):
        config = self._config(tmp_path)
        asked = []

        def run(argv, **kw):
            asked.append(argv)
            if argv[:3] == ["podman", "container", "inspect"]:
                return subprocess.CompletedProcess(argv, 0, "true\n" if
                                                   argv[-1] == "sarathi-smritikosh-db"
                                                   else "false\n", "")
            kw["stdout"].write(b"PGDMP the memories")
            return subprocess.CompletedProcess(argv, 0, None, b"")

        out = backup.make([], key, tmp_path / "b", config=config,
                          dump=lambda c, into: backup.dump_memory(c, into, run=run))
        assert not out.memory                  # the process road's container isn't running
        config = parse(self.CONFIG.format(checkout=config.smritikosh.checkout)
                       + '[run]\nroad = "podman"\n')
        out = backup.make([], key, tmp_path / "b", config=config,
                          dump=lambda c, into: backup.dump_memory(c, into, run=run))
        assert out.memory and out.problems == []
        assert asked[-1][:3] == ["podman", "exec", "sarathi-smritikosh-db"]
        assert "pg_dump" in asked[-1] and "smritikosh" in asked[-1]

    def test_a_stopped_database_is_said_never_skipped_quietly(self, tmp_path, key):
        config = self._config(tmp_path)
        out = backup.make([], key, tmp_path / "b", config=config,
                          dump=lambda c, into: backup.dump_memory(
                              c, into, run=lambda argv, **kw: subprocess.CompletedProcess(
                                  argv, 1, "", "no such container")))
        assert not out.memory
        assert out.problems == ["Smritikosh's database isn't running, so its memories "
                                "aren't in this backup (`sarathi up` starts it)"]
        assert out.as_json()["ok"] is False

    def test_the_dump_goes_back_with_clean_and_the_podman_road_gets_its_volume_back(
            self, tmp_path, monkeypatch):
        from sarathi import smritikosh

        config = parse(self.CONFIG.format(checkout=self._config(tmp_path).smritikosh.checkout)
                       + '[run]\nroad = "podman"\n')
        dump = tmp_path / "m.dump"
        dump.write_bytes(b"PGDMP")
        stopped = []
        monkeypatch.setattr(smritikosh, "start_database", lambda kosh, db, say: kosh)
        monkeypatch.setattr(smritikosh, "stop_database", lambda kosh: stopped.append(kosh))
        given = {}

        def run(argv, **kw):
            given["argv"], given["stdin"] = argv, kw["stdin"].read()
            return subprocess.CompletedProcess(argv, 0, b"", b"")

        said = backup.restore_memory(config, dump, run=run)
        assert "--clean" in given["argv"] and given["stdin"] == b"PGDMP"
        assert stopped and "smritikosh-pgdata" in said

    def test_no_checkout_here_says_how_to_bring_them_back(self, tmp_path):
        config = parse(self.CONFIG.format(checkout=tmp_path / "not-here"))
        with pytest.raises(backup.BackupError, match="--only smritikosh"):
            backup.restore_memory(config, tmp_path / "m.dump")


# ---- the command --------------------------------------------------------------------


class TestTheCommand:
    def test_a_night_with_no_key_yet_asks_for_a_person(self, world, monkeypatch):
        monkeypatch.delenv(backup.ENV_PASSPHRASE, raising=False)
        with pytest.raises(backup.BackupError, match="at a terminal"):
            cli.run_backup(ask=False)

    def test_the_first_backup_makes_the_key_then_nights_need_no_passphrase(
            self, world, monkeypatch, capsys):
        for name in ("yantra", "setu", "samay"):
            program(world / "bin", name, json.dumps({"format": f"{name}.keeps.v1",
                                                     "keeps": []}))
        (world / "config").mkdir()
        (world / "config/sarathi.toml").write_text(
            f'[model]\nprovider = "ollama"\n[backup]\nfolder = "{world}/b"\nkeep = 1\n')
        monkeypatch.setenv(backup.ENV_PASSPHRASE, WORDS)
        assert cli.main(["backup"]) == 0
        assert backup.read_key() is not None
        monkeypatch.delenv(backup.ENV_PASSPHRASE)
        assert cli.main(["backup", "--json"]) == 0
        said = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert said["ok"] and len(list((world / "b").glob("*.sarathi-backup"))) == 1
        monkeypatch.setenv(backup.ENV_PASSPHRASE, WORDS)
        assert cli.main(["restore", said["file"], "--list"]) == 0
        assert "sarathi config" in capsys.readouterr().out


class TestTheBackupsThere:
    def _made(self, folder: Path, n: int) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            f = folder / f"sarathi-host-2026102{i}-000000{backup.SUFFIX}"
            f.write_bytes(b"x" * (i + 1))
            os.utime(f, (1_800_000_000 - i * 3600,) * 2)    # 0 is the newest
        (folder / "notes.txt").write_text("mine")

    def test_listed_newest_first_and_deleted_by_number_or_name_only(self, tmp_path):
        self._made(tmp_path, 3)
        rows = backup.listing(tmp_path)
        assert [r["n"] for r in rows] == [1, 2, 3] and rows[0]["name"].endswith("0-000000"
                                                                                + backup.SUFFIX)
        assert backup.delete(tmp_path, ["3"]) == [rows[2]["name"]]
        for wrong in ("notes.txt", "../notes.txt", "9"):
            with pytest.raises(backup.BackupError, match="sarathi backup list"):
                backup.delete(tmp_path, [wrong])
        assert backup.delete(tmp_path, [], all_but=1) == [rows[1]["name"]]
        assert sorted(p.name for p in tmp_path.iterdir()) == ["notes.txt", rows[0]["name"]]

    def test_the_command_asks_first_and_a_no_deletes_nothing(self, world, monkeypatch, capsys):
        (world / "config").mkdir()
        (world / "config/sarathi.toml").write_text(
            f'[model]\nprovider = "ollama"\n[backup]\nfolder = "{world}/b"\n')
        self._made(world / "b", 2)
        monkeypatch.setattr("builtins.input", lambda _q: "n")
        assert cli.main(["backup", "delete", "1"]) == 1
        assert len(backup.listing(world / "b")) == 2
        monkeypatch.setattr("builtins.input", lambda _q: "y")
        assert cli.main(["backup", "delete", "1"]) == 0
        assert cli.main(["backup", "list", "--json"]) == 0
        listed = json.loads(capsys.readouterr().out.split("deleted 1:")[-1].split("\n", 1)[1])
        assert [r["n"] for r in listed["backups"]] == [1]

    def test_set_writes_backup_and_keeps_the_rest_of_the_file(self, world, capsys):
        (world / "config").mkdir()
        toml = world / "config/sarathi.toml"
        toml.write_text('[model]\nprovider = "ollama"\nmodel = "qwen3.8"\n')
        assert cli.main(["backup", "set", "--folder", f"{world}/usb", "--keep", "3",
                         "--also", "~/keys", "--also", "~/notes"]) == 0
        assert cli.main(["backup", "set", "--no-also", "~/notes"]) == 0
        got = parse(toml.read_text())
        assert (got.backup.folder, got.backup.keep, got.backup.also) == (
            f"{world}/usb", 3, ("~/keys",))
        assert got.model == "qwen3.8" and toml.with_suffix(".toml.bak").exists()
        assert cli.main(["backup", "set", "--keep", "-1"]) == 2

    def test_an_unplugged_disk_makes_no_backup_on_this_computer(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backup, "DISKS", (str(tmp_path) + "/",))
        gone = tmp_path / "USB" / "sarathi-backups"
        assert "plugged in" in backup.missing_disk(gone)
        with pytest.raises(backup.BackupError, match="plugged in"):
            backup.make([], {}, gone)
        assert not (tmp_path / "USB").exists()
        assert backup.missing_disk(tmp_path / "home-folder") is not None  # same rule
        monkeypatch.setattr(backup, "DISKS", ("/media/",))
        assert backup.missing_disk(tmp_path / "anywhere-else") is None


class TestANewHome:
    def test_sarathis_own_paths_follow_the_new_home_and_nothing_else_is_rewritten(
            self, tmp_path, key):
        old = tmp_path / "old-home"
        (old / ".config/sarathi").mkdir(parents=True)
        (old / ".config/sarathi/sarathi.toml").write_text(
            f'[smritikosh]\ncheckout = "{old}/smritikosh"\n[dvara]\nroot = "{old}"\n'
            f'# "{old}-elsewhere/x" is not under it\n')
        (old / "dvara").mkdir()
        (old / "dvara/actors.toml").write_text(f'note = "{old}/x"\n')
        out = backup.make([backup.Place("sarathi", "config", str(old / ".config/sarathi")),
                           backup.Place("dvara", "actors", str(old / "dvara/actors.toml"))],
                          key, tmp_path / "b", home=old)
        new = tmp_path / "new-home"
        restored = _unpack_from(out.file, old, new)
        text = (new / ".config/sarathi/sarathi.toml").read_text()
        assert f'checkout = "{new}/smritikosh"' in text and f'root = "{new}"' in text
        assert f'"{old}-elsewhere/x"' in text
        assert (new / "dvara/actors.toml").read_text() == f'note = "{old}/x"\n'
        assert any("now under" in line for line in restored.lines)


# ---- from the home page, and Samay's road --------------------------------------------


class TestFromTheHomePage:
    KEY = "the-backup-key-long-enough"

    def served(self, tmp_path, made):
        from sarathi.home import Home, HomeServer
        from test_home import GOOD, config
        server = HomeServer(Home(config(tmp_path), lambda: {}, backup=made), GOOD, port=0,
                            backup_key=self.KEY)
        server.start()
        return server

    def test_the_backup_key_makes_one_and_opens_nothing_else(self, tmp_path):
        from test_home import ask
        server = self.served(tmp_path, lambda: {"format": "sarathi.backup.made.v1",
                                                "ok": True})
        try:
            assert ask(server, "/api/backup", self.KEY, "POST").json()["ok"] is True
            for path in ("/api/backup", "/api/pieces", "/api/settings", "/api/doctor"):
                assert ask(server, path, self.KEY).status_code == 401
            assert ask(server, "/api/backup/nightly", self.KEY, "POST").status_code == 401
            assert ask(server, "/api/backup", "wrong-key-of-a-good-length",
                       "POST").status_code == 401
        finally:
            server.stop()

    def test_no_passphrase_yet_is_said_with_what_to_do(self, tmp_path):
        from test_home import ask

        def made():
            raise backup.BackupError("there is no backup passphrase yet: run `sarathi "
                                     "backup` once at a terminal to choose it")
        server = self.served(tmp_path, made)
        try:
            got = ask(server, "/api/backup", self.KEY, "POST")
            assert got.status_code == 409 and "at a terminal" in got.json()["detail"]
        finally:
            server.stop()

    def test_the_owner_sees_the_folder_the_newest_and_whether_there_is_a_key(
            self, world, monkeypatch):
        from dataclasses import replace

        from sarathi.config import Backup
        from sarathi.home import Home
        from test_home import config
        folder = world / "b"
        folder.mkdir()
        (folder / f"sarathi-beast-20261023-023000{backup.SUFFIX}").write_bytes(b"x" * 10)
        home = Home(replace(config(world), backup=Backup(folder=str(folder), keep=3)),
                    lambda: {})
        seen = home.backups()
        assert seen["key"] is False and seen["count"] == 1 and seen["keep"] == 3
        assert seen["newest"]["bytes"] == 10

    def test_one_at_a_time(self, tmp_path):
        import threading

        from sarathi.home import Home
        from test_home import config
        gate = threading.Event()
        home = Home(config(tmp_path), lambda: {}, backup=lambda: gate.wait(5) and {})
        first = threading.Thread(target=home.backup_now)
        first.start()
        while not home._backing_up.locked():
            pass
        assert home.backup_now()[0] == 409
        gate.set()
        first.join()

    def test_samay_is_asked_once_for_a_night_before_the_tests(self, tmp_path):
        from sarathi.home import BACKUP_NIGHTLY, NIGHTLY, Home
        from test_home import config
        asked = []

        def samay(cfg, method, path, body=None):
            asked.append((method, body))
            return {"schedules": [{"runner": "backup"}] if len(asked) > 2 else []}
        home = Home(config(tmp_path), lambda: {}, ask_samay=samay)
        assert home.backup_nightly()[0] == 200 and asked[1] == ("POST", BACKUP_NIGHTLY)
        assert "already" in home.backup_nightly()[1]
        assert BACKUP_NIGHTLY["when"] < NIGHTLY["when"]

    def test_samay_is_told_where_and_with_which_key(self, tmp_path, monkeypatch):
        from sarathi import services
        monkeypatch.setenv("SARATHI_STATE", str(tmp_path))
        env = services.doctor_env(parse('[model]\nprovider = "ollama"\n'
                                        '[pages]\non = true\n'))
        assert env["SAMAY_BACKUP_URL"].endswith("/api/backup")
        assert len(env["SAMAY_BACKUP_TOKEN"]) >= 16
        assert env["SAMAY_BACKUP_TOKEN"] != env["SAMAY_DOCTOR_TOKEN"]
