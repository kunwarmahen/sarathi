"""`sarathi backup` and `sarathi restore`: the house in one locked file.

Everything that makes this computer yours is spread across seven
programs' folders: Setu's accounts, keys and browser profiles, each
person's conversations and their own Setu folder in Dvara's, the
schedules and their logbook in Samay's, the watches in Prahari's, the
phone rules and adb's key in Sparsh's, History and the learned skills in
Yantra's, the memories in Smritikosh's database, and every settings file.
A disk that dies, or a move to a Raspberry Pi, loses each one separately.
This is one command for all of them, and one to bring them back.

EACH PROGRAM SAYS WHAT IT KEEPS. Sarathi knows nothing of what is inside
another program's folder: each answers ``keeps --json``
(``<name>.keeps.v1``, asked the way ``status --json`` is, Dvara with its
folders as sarathi.toml names them) with its places -- a stable ``id``,
the ``path``, ``what`` in plain words, and ``leave_out``: names never
worth carrying (a browser's caches: 2.6 GB of profiles are 0.5 GB
without them). Sarathi adds only what is its own: its settings and
state, Smritikosh's ``.env`` and database (it set them up), and
``[backup] also``, the places that are yours and no program's (a
catalog signing key). A program that can't say is named in the answer,
and the backup exits 1, so a nightly run that missed one is heard about.

A COPY THAT IS NEVER HALF A WRITE. A SQLite file (found by its first
bytes, not its name) is copied with SQLite's own backup, so a run that
finishes mid-copy is in it whole or not at all; its ``-wal`` file is
folded in, not carried. Every other file is read whole before it is
written into the pack, so a file that grows while it is read cannot
break the pack. Smritikosh's database is ``pg_dump``'s, from the
container running it.

LOCKED LIKE SETU'S FOLDER, SO A NIGHT NEEDS NO PASSPHRASE. The first
backup asks for a passphrase twice and makes a key pair: the public half
in the clear, the private half sealed with a key from the passphrase
(scrypt), both in ``backup-key.json`` beside sarathi.toml. Every backup
is sealed to the public half -- by a person, or by Samay at 03:00 with
nobody there -- and opened only by the passphrase. Each file carries the
sealed private half in its own header, so a new computer with nothing on
it opens it with the file and the passphrase alone. Forgetting the
passphrase loses every backup: there is no other way in, by design.

Format, after the 16-byte magic: a 4-byte length and a JSON header (the
key's public half and sealed private half, an ephemeral X25519 key, the
content key sealed to the public half, a nonce prefix); then chunks, each
a flag byte (1 on the last), a 4-byte length and AES-256-GCM ciphertext,
its nonce the prefix and a counter, the header's hash, the counter and
the flag its associated data -- so a chunk can't be moved, dropped or
swapped, and a file cut short says so instead of restoring half a house.
Inside is a tar: ``keeps/<owner>/<id>/...``, ``memory/smritikosh.dump``,
and ``manifest.json`` last.

RESTORE PUTS THINGS WHERE THEY WERE, AND MOVES NOTHING AWAY UNSAID. Each
place goes back to its path, with this computer's home in place of the
old one's (the settings that name those paths come back with them). A
place already there is moved aside to ``<name>.before-restore-<time>``,
never deleted. Restore refuses while anything `up` started is running:
programs writing into folders being replaced would ruin both.
"""

from __future__ import annotations

import base64
import fnmatch
import getpass
import hashlib
import io
import json
import os
import secrets
import shutil
import socket
import sqlite3
import stat
import struct
import subprocess
import tarfile
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from sarathi.config import Config, config_dir, state_dir
from sarathi.siblings import Found

FORMAT = "sarathi.backup.v1"
KEY_FORMAT = "sarathi.backup-key.v1"
KEY_FILE = "backup-key.json"
MAGIC = b"SARATHI-BACKUP\x00\x01"
SUFFIX = ".sarathi-backup"
#: Plaintext per chunk.
CHUNK = 1 << 20
#: scrypt's cost: about half a second and 128 MB -- a file on a USB disk
#: can be guessed at for as long as someone has it.
SCRYPT = {"n": 2 ** 17, "r": 8, "p": 1}
MIN_PASSPHRASE = 8
#: The variable a script gives the passphrase in, to restore unattended.
ENV_PASSPHRASE = "SARATHI_BACKUP_PASSPHRASE"
SQLITE_HEADER = b"SQLite format 3\x00"
SQLITE_SIDES = ("-wal", "-shm", "-journal")
#: Read into memory whole below this; copied to a temporary file above.
IN_MEMORY = 64 << 20
#: Sarathi's own: what is made again by `up`, and what is only a record.
OWN_LEAVE_OUT = {"config": ["units", "*.bak*"],
                 "state": ["logs", "run", "*.lock", "*.sock"]}
DUMP = "memory/smritikosh.dump"
#: How long one sibling may take to say what it keeps.
KEEPS_TIMEOUT = 20.0


class BackupError(Exception):
    """A backup or restore that can't go on, in words."""


# ---- the key ----------------------------------------------------------------------


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _kdf(passphrase: str, salt: bytes, params: dict[str, int]) -> bytes:
    return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, dklen=32,
                          n=params["n"], r=params["r"], p=params["p"],
                          maxmem=256 * 1024 * 1024)


def _shared_key(shared: bytes, ephemeral: bytes, public: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=ephemeral + public,
                info=b"sarathi-backup").derive(shared)


def key_path() -> Path:
    return config_dir() / KEY_FILE


def make_key(passphrase: str) -> dict[str, Any]:
    """A new key pair, its private half sealed with ``passphrase``."""
    if len(passphrase) < MIN_PASSPHRASE:
        raise BackupError(f"a passphrase needs at least {MIN_PASSPHRASE} characters -- "
                          "a few words are easier to remember than symbols")
    private = X25519PrivateKey.generate()
    raw = private.private_bytes(serialization.Encoding.Raw,
                                serialization.PrivateFormat.Raw,
                                serialization.NoEncryption())
    public = private.public_key().public_bytes(serialization.Encoding.Raw,
                                               serialization.PublicFormat.Raw)
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    sealed = AESGCM(_kdf(passphrase, salt, SCRYPT)).encrypt(nonce, raw, public)
    return {"format": KEY_FORMAT, "public": _b64(public), "kdf": "scrypt", **SCRYPT,
            "salt": _b64(salt), "nonce": _b64(nonce), "sealed": _b64(sealed)}


def open_key(key: dict[str, Any], passphrase: str) -> bytes:
    """The private half, or BackupError when the passphrase isn't its."""
    public = _unb64(key["public"])
    try:
        return AESGCM(_kdf(passphrase, _unb64(key["salt"]), key)).decrypt(
            _unb64(key["nonce"]), _unb64(key["sealed"]), public)
    except (InvalidTag, KeyError, ValueError):
        raise BackupError("that passphrase doesn't open this backup") from None


def read_key(path: Path | None = None) -> dict[str, Any] | None:
    path = path or key_path()
    try:
        key = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return key if isinstance(key, dict) and key.get("format") == KEY_FORMAT else None


def save_key(key: dict[str, Any], path: Path | None = None) -> Path:
    path = path or key_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    staged = path.with_suffix(".tmp")
    staged.write_text(json.dumps(key, indent=1) + "\n")
    staged.chmod(0o600)
    os.replace(staged, path)
    return path


def ask_passphrase(twice: bool) -> str:
    """At a terminal; $SARATHI_BACKUP_PASSPHRASE for a script."""
    given = os.environ.get(ENV_PASSPHRASE)
    if given:
        return given
    try:
        first = getpass.getpass("the backup's passphrase: ")
        if twice and getpass.getpass("again, to be sure: ") != first:
            raise BackupError("the two didn't match; nothing was made")
    except EOFError:
        raise BackupError(f"no terminal to ask at: set {ENV_PASSPHRASE}") from None
    return first


# ---- the locked file --------------------------------------------------------------


def _nonce(prefix: bytes, counter: int) -> bytes:
    return prefix + struct.pack(">I", counter)


def _aad(header_hash: bytes, counter: int, last: bool) -> bytes:
    return header_hash + struct.pack(">IB", counter, int(last))


class Sealed(io.RawIOBase):
    """A file written through this is sealed to ``key``'s public half."""

    def __init__(self, out: BinaryIO, key: dict[str, Any], about: dict[str, Any]) -> None:
        self.out = out
        content = AESGCM.generate_key(bit_length=256)
        ephemeral = X25519PrivateKey.generate()
        eph_raw = ephemeral.public_key().public_bytes(serialization.Encoding.Raw,
                                                      serialization.PublicFormat.Raw)
        public = _unb64(key["public"])
        wrap = _shared_key(ephemeral.exchange(X25519PublicKey.from_public_bytes(public)),
                           eph_raw, public)
        wrap_nonce = secrets.token_bytes(12)
        self.prefix = secrets.token_bytes(8)
        header = json.dumps({
            **about, "format": FORMAT, "key": key, "ephemeral": _b64(eph_raw),
            "wrap_nonce": _b64(wrap_nonce),
            "content": _b64(AESGCM(wrap).encrypt(wrap_nonce, content, b"content-key")),
            "prefix": _b64(self.prefix), "chunk": CHUNK}).encode("utf-8")
        out.write(MAGIC + struct.pack(">I", len(header)) + header)
        self.hash = hashlib.sha256(header).digest()
        self.aead = AESGCM(content)
        self.buffer = bytearray()
        self.counter = 0
        self.written = 0

    def writable(self) -> bool:
        return True

    def write(self, data) -> int:
        self.buffer += data
        while len(self.buffer) > CHUNK:
            self._chunk(bytes(self.buffer[:CHUNK]), last=False)
            del self.buffer[:CHUNK]
        return len(data)

    def _chunk(self, plain: bytes, last: bool) -> None:
        sealed = self.aead.encrypt(_nonce(self.prefix, self.counter), plain,
                                   _aad(self.hash, self.counter, last))
        self.out.write(struct.pack(">BI", int(last), len(sealed)) + sealed)
        self.counter += 1
        self.written += len(plain)

    def finish(self) -> None:
        self._chunk(bytes(self.buffer), last=True)
        self.buffer.clear()


def read_header(stream: BinaryIO) -> tuple[dict[str, Any], bytes]:
    head = stream.read(len(MAGIC))
    if head != MAGIC:
        raise BackupError("this isn't a Sarathi backup (or it is from a newer Sarathi)")
    (size,) = struct.unpack(">I", stream.read(4))
    raw = stream.read(size)
    try:
        header = json.loads(raw)
    except ValueError:
        raise BackupError("this backup's header is damaged") from None
    if header.get("format") != FORMAT:
        raise BackupError(f"this backup speaks {header.get('format')!r}, not {FORMAT!r}")
    return header, raw


class Opened(io.RawIOBase):
    """A sealed file, read back as what was written into it."""

    def __init__(self, stream: BinaryIO, passphrase: str) -> None:
        header, raw = read_header(stream)
        self.header = header
        private = X25519PrivateKey.from_private_bytes(open_key(header["key"], passphrase))
        eph = _unb64(header["ephemeral"])
        wrap = _shared_key(private.exchange(X25519PublicKey.from_public_bytes(eph)), eph,
                           _unb64(header["key"]["public"]))
        try:
            content = AESGCM(wrap).decrypt(_unb64(header["wrap_nonce"]),
                                           _unb64(header["content"]), b"content-key")
        except InvalidTag:
            raise BackupError("this backup's header is damaged") from None
        self.aead = AESGCM(content)
        self.prefix = _unb64(header["prefix"])
        self.hash = hashlib.sha256(raw).digest()
        self.stream = stream
        self.counter = 0
        self.done = False
        self.buffer = b""

    def readable(self) -> bool:
        return True

    def readinto(self, into) -> int:
        while not self.buffer and not self.done:
            self._next()
        n = min(len(into), len(self.buffer))
        into[:n] = self.buffer[:n]
        self.buffer = self.buffer[n:]
        return n

    def _next(self) -> None:
        head = self.stream.read(5)
        if len(head) < 5:
            raise BackupError("this backup ends early: it was cut short (a full disk, "
                              "a copy that didn't finish)")
        last, size = struct.unpack(">BI", head)
        sealed = self.stream.read(size)
        try:
            self.buffer = self.aead.decrypt(_nonce(self.prefix, self.counter), sealed,
                                            _aad(self.hash, self.counter, bool(last)))
        except InvalidTag:
            raise BackupError("this backup is damaged: a part of it doesn't open") from None
        self.counter += 1
        if last:
            self.done = True
            if self.stream.read(1):
                raise BackupError("this backup has something after its end")


# ---- what is kept, and by whom ----------------------------------------------------


@dataclass
class Place:
    owner: str          # "setu", "sarathi", "smritikosh", "you"
    id: str
    path: str
    what: str = ""
    leave_out: list[str] = field(default_factory=list)


@dataclass
class Taken:
    place: Place
    kind: str = "missing"       # "folder" | "file" | "missing"
    files: int = 0
    bytes: int = 0
    skipped: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        return {**asdict(self.place), "kind": self.kind, "files": self.files,
                "bytes": self.bytes, "skipped": self.skipped[:20]}


def ask_keeps(found: Found, before: list[str] | None = None,
              run: Callable[..., subprocess.CompletedProcess] = subprocess.run
              ) -> list[Place]:
    """``<program> [before...] keeps --json``'s places, or BackupError."""
    name = found.sibling.name
    try:
        done = run([found.program, *(before or []), "keeps", "--json"], capture_output=True,
                   text=True, timeout=KEEPS_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackupError(f"{name} couldn't be asked what it keeps: {exc}") from None
    try:
        data = json.loads(done.stdout) if done.returncode == 0 else None
    except ValueError:
        data = None
    if not isinstance(data, dict) or data.get("format") != f"{name}.keeps.v1":
        raise BackupError(f"{name} doesn't say what it keeps (an older {name}: update "
                          f"it), so none of its files are in this backup")
    return [Place(name, str(p["id"]), str(p["path"]), str(p.get("what") or ""),
                  [str(x) for x in p.get("leave_out") or []])
            for p in data.get("keeps") or [] if isinstance(p, dict) and p.get("path")]


def own_places(config: Config | None) -> list[Place]:
    """Sarathi's own places, Smritikosh's ``.env``, and ``[backup] also``."""
    places = [Place("sarathi", "config", str(config_dir()),
                    "sarathi.toml, its keys (secrets.env) and this backup's key",
                    OWN_LEAVE_OUT["config"]),
              Place("sarathi", "state", str(state_dir()),
                    "the home page's keys, the people's sign-ins, Yantra's work folder",
                    OWN_LEAVE_OUT["state"])]
    if config is None:
        return places
    checkout = config.smritikosh.path()
    if checkout is not None:
        places.append(Place("smritikosh", "env", str(checkout / ".env"),
                            "Smritikosh's settings: its database's password, its secret"))
    for i, also in enumerate(config.backup.also):
        places.append(Place("you", f"also-{i + 1}", str(Path(also).expanduser()),
                            "yours ([backup] also)"))
    return places


def _left_out(parts: tuple[str, ...], patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(part, pat) for part in parts for pat in patterns)


def _is_sqlite(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(16) == SQLITE_HEADER
    except OSError:
        return False


def _sqlite_copy(path: Path, into: Path) -> None:
    source = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    try:
        target = sqlite3.connect(into)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def _side_of_sqlite(path: Path) -> bool:
    """A ``-wal``/``-shm``/``-journal`` beside a SQLite file: folded in."""
    for side in SQLITE_SIDES:
        if path.name.endswith(side):
            return _is_sqlite(path.with_name(path.name[: -len(side)]))
    return False


def _info(arcname: str, st: os.stat_result, size: int = 0) -> tarfile.TarInfo:
    info = tarfile.TarInfo(arcname)
    info.mode = stat.S_IMODE(st.st_mode)
    info.mtime = int(st.st_mtime)
    info.size = size
    return info


def _add_file(tar: tarfile.TarFile, path: Path, arcname: str, scratch: Path) -> int:
    """One file into the pack, consistent; its size, or -1 when it went."""
    try:
        st = path.lstat()
        if stat.S_ISLNK(st.st_mode):
            info = _info(arcname, st)
            info.type, info.linkname = tarfile.SYMTYPE, os.readlink(path)
            tar.addfile(info)
            return 0
        if not stat.S_ISREG(st.st_mode):
            return -1                           # a socket, a pipe: nothing to carry
        if _is_sqlite(path):
            copy = scratch / "copy.sqlite"
            copy.unlink(missing_ok=True)
            _sqlite_copy(path, copy)
            with copy.open("rb") as f:
                size = copy.stat().st_size
                tar.addfile(_info(arcname, st, size), f)
            copy.unlink()
            return size
        if st.st_size <= IN_MEMORY:
            data = path.read_bytes()
            tar.addfile(_info(arcname, st, len(data)), io.BytesIO(data))
            return len(data)
        copy = scratch / "copy.bin"
        shutil.copyfile(path, copy)
        with copy.open("rb") as f:
            size = copy.stat().st_size
            tar.addfile(_info(arcname, st, size), f)
        copy.unlink()
        return size
    except (FileNotFoundError, sqlite3.Error):
        return -1                               # gone while the walk went by


def _walk(root: Path, leave_out: list[str],
          never: frozenset[Path] = frozenset()) -> Iterator[tuple[Path, bool]]:
    """(path, is_folder) under ``root``, folders first, left-out names and
    the ``never`` folders (the backups' own, places packed on their own)
    pruned."""
    for here, dirs, files in os.walk(root):
        base = Path(here)
        rel = base.relative_to(root).parts
        keep_dirs = []
        for d in sorted(dirs):
            if _left_out((*rel, d), leave_out) or base / d in never:
                continue
            if (base / d).is_symlink():
                yield base / d, False           # a link, carried as one
                continue
            keep_dirs.append(d)
            yield base / d, True
        dirs[:] = keep_dirs
        for f in sorted(files):
            if not _left_out((*rel, f), leave_out):
                yield base / f, False


def take(tar: tarfile.TarFile, place: Place, scratch: Path,
         never: frozenset[Path] = frozenset()) -> Taken:
    """One place into the pack under ``keeps/<owner>/<id>``."""
    taken = Taken(place)
    root = Path(place.path)
    arc = f"keeps/{place.owner}/{place.id}"
    if root.is_file() or root.is_symlink():
        size = _add_file(tar, root, f"{arc}/{root.name}", scratch)
        if size >= 0:
            taken.kind, taken.files, taken.bytes = "file", 1, size
        return taken
    if not root.is_dir():
        return taken
    taken.kind = "folder"
    tar.addfile(_folder_info(arc, root))
    for path, is_folder in _walk(root, place.leave_out, never):
        name = f"{arc}/{path.relative_to(root).as_posix()}"
        if is_folder:
            try:
                tar.addfile(_folder_info(name, path))
            except FileNotFoundError:
                pass
            continue
        if _side_of_sqlite(path) or path in never:
            continue
        size = _add_file(tar, path, name, scratch)
        if size < 0:
            taken.skipped.append(str(path.relative_to(root)))
        else:
            taken.files += 1
            taken.bytes += size
    return taken


def _folder_info(arcname: str, path: Path) -> tarfile.TarInfo:
    info = _info(arcname, path.stat())
    info.type = tarfile.DIRTYPE
    return info


# ---- Smritikosh's database --------------------------------------------------------


def dump_memory(config: Config, into: Path,
                run: Callable[..., subprocess.CompletedProcess] = subprocess.run
                ) -> str | None:
    """``pg_dump`` of Smritikosh's database into ``into``; None when done,
    else what kept it out (said in the answer, never silently)."""
    from sarathi import podman
    from sarathi.smritikosh import Database, read_dotenv

    checkout = config.smritikosh.path()
    if checkout is None:
        return None
    url = read_dotenv(checkout / ".env").get("POSTGRES_URL")
    if not url:
        return "Smritikosh's .env names no database, so its memories aren't in it"
    db = Database.parse(url)
    # the road says which container holds it: the unit's, or the plain one
    name = podman.UNITS["smritikosh-db"] if config.road == "podman" \
        else config.smritikosh.database
    state = run(["podman", "container", "inspect", "--format", "{{.State.Running}}", name],
                capture_output=True, text=True, check=False)
    if state.returncode == 0 and state.stdout.strip() == "true":
        with into.open("wb") as out:
            done = run(["podman", "exec", name, "pg_dump", "--format=custom", "-U",
                        db.user, "-d", db.name], stdout=out, stderr=subprocess.PIPE,
                       check=False)
        if done.returncode != 0:
            err = done.stderr.decode("utf-8", "replace") if isinstance(done.stderr, bytes) \
                else str(done.stderr or "")
            return f"pg_dump of Smritikosh's database failed: {err.strip()[-300:]}"
        return None
    return ("Smritikosh's database isn't running, so its memories aren't in this "
            "backup (`sarathi up` starts it)")


# ---- the backup -------------------------------------------------------------------


@dataclass
class Made:
    file: Path | None
    taken: list[Taken]
    problems: list[str]
    memory: bool = False
    removed: list[str] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def bytes(self) -> int:
        return self.file.stat().st_size if self.file and self.file.exists() else 0

    def as_json(self) -> dict[str, Any]:
        return {"format": "sarathi.backup.made.v1", "ok": not self.problems,
                "file": str(self.file) if self.file else None, "bytes": self.bytes,
                "memory": self.memory, "places": [t.as_json() for t in self.taken],
                "problems": self.problems, "removed": self.removed,
                "seconds": round(self.seconds, 1)}


def tilde(path: str | Path) -> str:
    """``~/...`` for a path in this home, as a person reads it."""
    home, path = str(Path.home()), str(path)
    return "~" + path[len(home):] if path.startswith(home + os.sep) else path


def file_name(when: float | None = None) -> str:
    host = socket.gethostname().split(".")[0].lower() or "house"
    return f"sarathi-{host}-{time.strftime('%Y%m%d-%H%M%S', time.localtime(when))}{SUFFIX}"


def make(places: list[Place], key: dict[str, Any], folder: Path, *,
         config: Config | None = None, problems: list[str] | None = None,
         dump: Callable[[Config, Path], str | None] = dump_memory,
         say: Callable[[str], None] = lambda _line: None,
         home: Path | None = None) -> Made:
    """Every place, sealed, into a new file in ``folder``. ``home``: this
    computer's, recorded so a restore elsewhere knows what to replace."""
    start = time.monotonic()
    problems = list(problems or [])
    gone = missing_disk(folder)
    if gone:
        raise BackupError(gone)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = folder / file_name()
    partial = target.with_name(target.name + ".part")
    taken: list[Taken] = []
    memory = False
    with tempfile.TemporaryDirectory(prefix="sarathi-backup-", dir=folder) as scratch_dir:
        scratch = Path(scratch_dir)
        fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "wb") as out:
                sealed = Sealed(out, key, {"made": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                           "host": socket.gethostname()})
                with tarfile.open(fileobj=sealed, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                    # inside another place: packed once, as its own
                    never = frozenset({folder, *(Path(p.path) for p in places)})
                    for place in places:
                        say(f"{place.owner:<10} {place.id:<14} {tilde(place.path)}")
                        taken.append(take(tar, place, scratch, never - {Path(place.path)}))
                    if config is not None and config.smritikosh.path() is not None:
                        dumped = scratch / "smritikosh.dump"
                        said = dump(config, dumped)
                        if said is None and dumped.exists():
                            say(f"{'smritikosh':<10} {'database':<14} pg_dump")
                            with dumped.open("rb") as f:
                                tar.addfile(_info(DUMP, dumped.stat(), dumped.stat().st_size),
                                            f)
                            memory = True
                        elif said:
                            problems.append(said)
                    manifest = json.dumps({
                        "format": FORMAT, "made": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "host": socket.gethostname(), "home": str(home or Path.home()),
                        "places": [t.as_json() for t in taken], "memory": memory,
                        "memory_db": _db_name(config) if memory else None,
                        "problems": problems}, indent=1).encode("utf-8")
                    info = tarfile.TarInfo("manifest.json")
                    info.size, info.mtime, info.mode = len(manifest), int(time.time()), 0o600
                    tar.addfile(info, io.BytesIO(manifest))
                sealed.finish()
                out.flush()
                os.fsync(out.fileno())
            os.replace(partial, target)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
    return Made(target, taken, problems, memory=memory, seconds=time.monotonic() - start)


def _db_name(config: Config | None) -> dict[str, str] | None:
    return None if config is None else {"volume": config.smritikosh.volume,
                                        "container": config.smritikosh.database}


#: Where removable disks are mounted: a folder under one of these whose
#: disk isn't mounted is a disk unplugged, not a folder to make.
DISKS = ("/media/", "/mnt/", "/run/media/", "/Volumes/")


def missing_disk(folder: Path) -> str | None:
    """Why ``folder`` can't take a backup now, or None. A folder on a disk
    that isn't plugged in is a sentence, never a folder made where the
    disk would be -- that would put the backup on this computer's own
    disk, under a name that says it's on the other one."""
    folder = folder.expanduser()
    if folder.is_dir():
        return None if os.access(folder, os.W_OK) else f"{folder} can't be written to"
    if not str(folder).startswith(DISKS):
        return None
    there = next(p for p in folder.parents if p.is_dir())
    if there.is_mount() and there != Path(there.anchor):
        return None                      # the disk is in; the folder is made on it
    return f"{folder} isn't there: is its disk plugged in?"


def listing(folder: Path) -> list[dict[str, Any]]:
    """Every backup ``sarathi backup`` made in ``folder``, newest first and
    numbered from 1, as ``sarathi backup list`` and ``delete N`` count."""
    made = sorted((p for p in folder.expanduser().glob(f"sarathi-*{SUFFIX}") if p.is_file()),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"n": n, "name": p.name, "path": str(p), "bytes": p.stat().st_size,
             "made": time.strftime("%a %d %b %Y %H:%M", time.localtime(p.stat().st_mtime))}
            for n, p in enumerate(made, 1)]


def delete(folder: Path, picks: list[str], *, all_but: int | None = None) -> list[str]:
    """Backups in ``folder`` deleted: by number (``listing``'s) or file name,
    or every one but the newest ``all_but``. Only ``sarathi backup``'s own
    files, and only in that folder: a name with a slash, or one that isn't
    a backup, is refused before anything goes."""
    rows = listing(folder)
    if all_but is not None:
        if all_but < 1:
            raise BackupError("--all-but keeps at least the newest one (1 or more)")
        chosen = rows[all_but:]
    else:
        chosen = []
        for pick in picks:
            row = (next((r for r in rows if str(r["n"]) == pick), None) if pick.isdigit()
                   else next((r for r in rows if r["name"] == pick), None))
            if row is None:
                raise BackupError(f"no backup {pick!r} in {folder}: `sarathi backup list` "
                                  "shows their numbers")
            if row not in chosen:
                chosen.append(row)
    for row in chosen:
        Path(row["path"]).unlink()
    return [r["name"] for r in chosen]


def prune(folder: Path, keep: int) -> list[str]:
    """The newest ``keep`` backups in ``folder`` kept; older ones removed."""
    if keep <= 0:
        return []
    made = sorted((p for p in folder.glob(f"sarathi-*{SUFFIX}") if p.is_file()),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    gone = []
    for old in made[keep:]:
        old.unlink()
        gone.append(old.name)
    return gone


def size(n: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def made_lines(made: Made) -> list[str]:
    out = []
    for t in made.taken:
        where = {"folder": f"{t.files} files, {size(t.bytes)}",
                 "file": size(t.bytes), "missing": "not there, nothing taken"}[t.kind]
        out.append(f"  {t.place.owner + ' ' + t.place.id:<24} {where}")
    if made.memory:
        out.append(f"  {'smritikosh database':<24} its memories (pg_dump)")
    out.append("")
    out.append(f"written: {tilde(made.file)} ({size(made.bytes)}, {made.seconds:.0f}s), "
               "locked with your backup passphrase")
    if made.removed:
        out.append(f"older ones removed (keeping the newest): {', '.join(made.removed)}")
    for p in made.problems:
        out.append(f"NOT IN IT: {p}")
    return out


# ---- the restore ------------------------------------------------------------------


def rebase(path: str, old_home: str, home: Path | None = None) -> Path:
    """``path`` with this computer's home in place of the old one's."""
    home = home or Path.home()
    old = Path(old_home)
    p = Path(path)
    try:
        return home / p.relative_to(old)
    except ValueError:
        return p


def peek(file: Path, passphrase: str) -> dict[str, Any]:
    """The manifest of a backup, read through to its end."""
    with file.open("rb") as raw, Opened(raw, passphrase) as plain, \
            tarfile.open(fileobj=plain, mode="r|") as tar:
        manifest = None
        for member in tar:
            if member.name == "manifest.json":
                manifest = json.loads(tar.extractfile(member).read())
    if manifest is None:
        raise BackupError("this backup has no manifest: it didn't finish being made")
    return manifest


@dataclass
class Restored:
    lines: list[str]
    moved_aside: list[str]
    staging: Path
    memory_dump: Path | None = None
    manifest: dict[str, Any] = field(default_factory=dict)
    refused: list[str] = field(default_factory=list)


def unpack(file: Path, passphrase: str, *, only: set[str] | None = None,
           home: Path | None = None, stamp: str | None = None,
           say: Callable[[str], None] = lambda _line: None) -> Restored:
    """Every place back where it was (on this home); the database's dump
    left in a staging folder for :func:`restore_memory`."""
    home = home or Path.home()
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S")
    staging = home / f".sarathi-restoring-{stamp}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(mode=0o700, parents=True)
    refused = []
    with file.open("rb") as raw, Opened(raw, passphrase) as plain, \
            tarfile.open(fileobj=plain, mode="r|") as tar:
        for member in tar:
            owner = member.name.split("/")[1] if member.name.startswith("keeps/") else None
            if only is not None and owner is not None and owner not in only:
                continue
            if member.name == DUMP and only is not None and "smritikosh" not in only:
                continue
            try:
                # "data": nothing lands outside the staging folder, no link
                # points out of it, no file comes back setuid
                tar.extract(member, staging, filter="data")
            except tarfile.FilterError as exc:
                refused.append(f"{member.name}: {exc}")
    manifest = json.loads((staging / "manifest.json").read_text())
    lines, aside = [], []
    for row in manifest.get("places") or []:
        owner, ident, kind = row["owner"], row["id"], row.get("kind")
        if only is not None and owner not in only:
            continue
        if kind == "missing":
            continue
        source = staging / "keeps" / owner / ident
        if kind == "file":
            source = source / Path(row["path"]).name
        target = rebase(row["path"], manifest.get("home", ""), home)
        if owner == "smritikosh" and ident == "env" and not target.parent.is_dir():
            lines.append(f"  {owner} {ident}: kept back -- {target.parent} isn't here yet "
                         "(Smritikosh's checkout)")
            continue
        if target.exists() or target.is_symlink():
            moved = target.with_name(f"{target.name}.before-restore-{stamp}")
            target.rename(moved)
            aside.append(str(moved))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        say(f"{owner:<10} {ident:<14} {tilde(target)}")
        lines.append(f"  {owner + ' ' + ident:<24} {tilde(target)}")
    old_home = manifest.get("home", "")
    kept = manifest_path(manifest, "sarathi", "config")
    settings = rebase(kept, old_home, home) / "sarathi.toml" if kept else None
    if old_home and Path(old_home) != home and settings and settings.is_file() and (
            only is None or "sarathi" in only):
        if rehome(settings, old_home, str(home)):
            lines.append(f"  {'sarathi.toml':<24} its paths under {old_home} now under "
                         f"{tilde(home)}")
    dump = staging / DUMP
    return Restored(lines, aside, staging, dump if dump.exists() else None, manifest,
                    refused)


def manifest_path(manifest: dict[str, Any], owner: str, ident: str) -> str | None:
    for row in manifest.get("places") or []:
        if row.get("owner") == owner and row.get("id") == ident and row.get("kind") != "missing":
            return row.get("path")
    return None


def rehome(settings: Path, old: str, new: str) -> bool:
    """Sarathi's own settings, their paths moved from the old computer's
    home to this one's (Smritikosh's checkout, Dvara's folders). Only
    Sarathi's file: another program's files are its own to say."""
    text = settings.read_text()
    moved = text.replace(f'"{old}/', f'"{new}/').replace(f'"{old}"', f'"{new}"')
    if moved == text:
        return False
    settings.write_text(moved)
    return True


def restore_memory(config: Config, dump: Path,
                   run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                   say: Callable[[str], None] = lambda _line: None) -> str:
    """The database's dump into Smritikosh's database: its container
    started on its volume (made when there is none), ``pg_restore
    --clean``, and stopped again on the podman road, whose unit takes the
    volume at `up`. Returns what happened, in words."""
    from sarathi import smritikosh

    checkout = config.smritikosh.path()
    if checkout is None or not (checkout / ".env").is_file():
        raise BackupError("the memories are in this backup, but Smritikosh isn't set up "
                          f"here ({checkout or 'no checkout in sarathi.toml'}): clone it "
                          f"({smritikosh.REPO}) where sarathi.toml says, then `sarathi "
                          "restore FILE --only smritikosh`")
    url = smritikosh.read_dotenv(checkout / ".env").get("POSTGRES_URL")
    if not url:
        raise BackupError("Smritikosh's .env names no database to restore into")
    db = smritikosh.Database.parse(url)
    try:
        kosh = smritikosh.start_database(config.smritikosh, db, say)
    except smritikosh.SetupError as exc:
        raise BackupError(str(exc)) from None
    with dump.open("rb") as f:
        done = run(["podman", "exec", "-i", kosh.database, "pg_restore", "--clean",
                    "--if-exists", "--no-owner", "-U", db.user, "-d", db.name],
                   stdin=f, capture_output=True, check=False)
    if config.road == "podman":
        smritikosh.stop_database(kosh)
    err = done.stderr.decode("utf-8", "replace") if isinstance(done.stderr, bytes) \
        else str(done.stderr or "")
    # pg_restore exits 1 for warnings it went past (an extension that is
    # already there); a real failure leaves its "error:" lines
    errors = [line for line in err.splitlines() if "error:" in line.lower()
              and "already exists" not in line]
    if done.returncode != 0 and errors:
        raise BackupError("pg_restore failed: " + "; ".join(errors[-3:]))
    return f"its memories, into {kosh.database} (volume {kosh.volume})"


def finish(restored: Restored) -> None:
    """The staging folder gone: what is left in it was put back already,
    or was asked not to be (``--only``)."""
    shutil.rmtree(restored.staging, ignore_errors=True)
