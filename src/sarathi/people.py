"""The people in the house, signing in to the home page.

The home page's chat speaks to Dvara as somebody, and until now that was
always you, the owner: the page's key is yours, and so is everything
behind it -- every program's page, every key on the ring. Somebody else
in the house who wanted to talk to their agents had Telegram or nothing.
This is a sign-in for them, and it gives them exactly one thing: their
own chat, as their own person in Dvara.

ONE PERSON, ONE DVARA ACTOR. A sign-in is an id from Dvara's actors file
and nothing more. Their allowance, rules, folder, memories and Setu
sign-ins are the ones that id already has on Telegram; nothing about
them is kept here. Only the chat is the page's own (Dvara's ``web:chat``
thread, its note 34). A name that isn't in the actors file can't be
invited, and one taken out of it is refused by Dvara on the next look.

THE OWNER ADDS THEM. There is no sign-up form. ``sarathi invite priya``
(or Invite on the home page) makes a link that works ONCE, within two
days: the first device to open it chooses a password, and the link is
gone. A second invite for someone already signed up is how a forgotten
password is reset; their old sessions end when the new link is used.

KEPT AS HASHES. The password is kept as scrypt with its own salt, and an
invite or a device's session only as a SHA-256 of it: this file read by
somebody else gives them no way in. It is readable by you alone, beside
the home page's own token.

A DEVICE STAYS SIGNED IN until it signs out, the owner signs that person
out (``sarathi people --sign-out priya``), or it goes unused for
``IDLE_DAYS``. Five wrong passwords for one name in a quarter of an hour
and that name waits the rest of it: a guess at a time, not a list.

THE OWNER IS NOT HERE. Your own way in is still the page's key (the
``#token=`` address ``sarathi home`` prints), which also opens the cards.
A person's sign-in never sees them: no pages, no keys, no memory switch.
And what they say is theirs, as on Telegram -- Dvara's page shows the
owner who used which agent and what it cost, never the words.

Standard library only, as the rest of Sarathi.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sarathi.config import state_dir

FILE = "people.json"
#: How long an invite may wait to be opened.
INVITE_HOURS = 48
#: A device unused this long is signed out.
IDLE_DAYS = 90
#: The shortest password a person may choose.
MIN_PASSWORD = 8
#: Wrong passwords for one name before it waits, and for how long.
TRIES, WAIT_SECONDS = 5, 15 * 60
#: A session's last use is written down at most this often.
TOUCH_SECONDS = 3600
#: An id as Dvara's actors file can have it, and short enough to type.
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}
#: What a name with no password is checked against.
_NOBODY = "scrypt$" + base64.urlsafe_b64encode(b"\0" * 16).decode() + "$x"


class PeopleError(Exception):
    """Said to the person in front of the page, or to the owner."""


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(when: datetime) -> str:
    return when.isoformat(timespec="seconds")


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    b64 = base64.urlsafe_b64encode
    return f"scrypt${b64(salt).decode()}${b64(dk).decode()}"


def password_matches(password: str, kept: str | None) -> bool:
    if not kept or not kept.startswith("scrypt$"):
        return False
    try:
        _, salt, _dk = kept.split("$")
        salt_bytes = base64.urlsafe_b64decode(salt)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt_bytes), kept)


def actor_ids(actors: Path) -> list[str]:
    """The ids in Dvara's actors file, read as TOML and nothing more."""
    try:
        data = tomllib.loads(Path(actors).expanduser().read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PeopleError(f"can't read Dvara's actors file {actors}: {exc}") from None
    table = data.get("actor", {})
    return sorted(table) if isinstance(table, dict) else []


@dataclass(frozen=True)
class Person:
    """What the owner sees about one person's sign-in."""

    name: str
    signed_up: bool
    invite_until: str | None
    devices: int
    last_used: str | None

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "signed_up": self.signed_up,
                "invite_until": self.invite_until, "devices": self.devices,
                "last_used": self.last_used}


class People:
    """The sign-ins, kept in one file, safe to share with ``sarathi invite``
    run while the home page is serving."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else state_dir() / FILE
        self._misses: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    # ---- the file -------------------------------------------------------------

    @contextmanager
    def _held(self) -> Iterator[dict[str, Any]]:
        """The whole file, read under a lock and written back on the way out."""
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock = os.open(self.path.with_suffix(".lock"), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._read()
            before = json.dumps(data, sort_keys=True)
            yield data
            if json.dumps(data, sort_keys=True) != before:
                self._write(data)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            os.close(lock)

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text())
        except FileNotFoundError:
            return {"people": {}}
        except (OSError, ValueError) as exc:
            raise PeopleError(f"{self.path} can't be read: {exc}") from None
        if not isinstance(data, dict) or not isinstance(data.get("people"), dict):
            raise PeopleError(f"{self.path} isn't a people file")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        spare = self.path.with_suffix(".tmp")
        fd = os.open(spare, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as out:
            json.dump(data, out, indent=1, sort_keys=True)
            out.write("\n")
        os.replace(spare, self.path)

    @staticmethod
    def _fresh(entry: dict[str, Any], now: datetime) -> None:
        """Drop the sessions gone unused too long, and an invite run out."""
        idle = now - timedelta(days=IDLE_DAYS)
        sessions = entry.get("sessions") or {}
        entry["sessions"] = {k: s for k, s in sessions.items()
                             if datetime.fromisoformat(s["used"]) > idle}
        invite = entry.get("invite")
        if invite and datetime.fromisoformat(invite["until"]) <= now:
            entry["invite"] = None

    # ---- the owner's side -----------------------------------------------------

    def invite(self, name: str, known: list[str], owner: str) -> str:
        """A one-time link's secret for ``name``: ``name.secret``. Replaces an
        invite not yet used."""
        if not NAME.match(name):
            raise PeopleError(f"{name!r} isn't an id Dvara's actors file can have")
        if name == owner:
            raise PeopleError(f"{name} is you: your way in is the home page's own "
                              "address, the one `sarathi home` prints")
        if name not in known:
            raise PeopleError(f"{name} isn't in Dvara's actors file. Add "
                              f"[actor.{name}] there first (who they are, which agents, "
                              "their allowance), then invite them")
        secret = secrets.token_urlsafe(24)
        now = _now()
        with self._held() as data:
            entry = data["people"].setdefault(name, {"added": _iso(now), "password": None,
                                                     "sessions": {}})
            entry["invite"] = {"hash": _hash(secret),
                               "until": _iso(now + timedelta(hours=INVITE_HOURS))}
        return f"{name}.{secret}"

    def sign_out(self, name: str) -> int:
        """Every device of ``name`` signed out; how many there were."""
        with self._held() as data:
            entry = data["people"].get(name)
            if entry is None:
                raise PeopleError(f"{name} has no sign-in here")
            gone = len(entry.get("sessions") or {})
            entry["sessions"] = {}
        return gone

    def remove(self, name: str) -> None:
        """``name``'s sign-in, password, invite and devices, all gone."""
        with self._held() as data:
            if data["people"].pop(name, None) is None:
                raise PeopleError(f"{name} has no sign-in here")

    def listing(self) -> list[Person]:
        now = _now()
        with self._held() as data:
            out = []
            for name, entry in sorted(data["people"].items()):
                self._fresh(entry, now)
                sessions = entry["sessions"].values()
                out.append(Person(
                    name, bool(entry.get("password")),
                    (entry.get("invite") or {}).get("until"), len(sessions),
                    max((s["used"] for s in sessions), default=None)))
        return out

    # ---- the person's side ----------------------------------------------------

    def claim(self, link: str, password: str, device: str = "") -> tuple[str, str]:
        """(name, session): the invite used, the password set, this device in."""
        name, _, secret = (link or "").partition(".")
        if len(password or "") < MIN_PASSWORD:
            raise PeopleError(f"choose a password of at least {MIN_PASSWORD} characters")
        now = _now()
        with self._held() as data:
            entry = data["people"].get(name)
            if entry is not None:
                self._fresh(entry, now)
            invite = (entry or {}).get("invite")
            if not invite or not secret or \
                    not hmac.compare_digest(invite["hash"], _hash(secret)):
                raise PeopleError("that link has been used, has run out, or was replaced "
                                  "by a newer one: ask for a new one")
            assert entry is not None
            entry["password"] = hash_password(password)
            entry["invite"] = None
            entry["sessions"] = {}          # a reset ends every old device
            session = self._open(entry, now, device)
        with self._lock:
            self._misses.pop(name, None)
        return name, session

    def sign_in(self, name: str, password: str, device: str = "") -> str:
        """A session for this device, or PeopleError -- the same words for a
        wrong name and a wrong password."""
        wrong = PeopleError("that name and password don't match")
        with self._lock:
            now_s = time.monotonic()
            misses = [t for t in self._misses.get(name, []) if now_s - t < WAIT_SECONDS]
            self._misses[name] = misses
            if len(misses) >= TRIES:
                wait = int((WAIT_SECONDS - (now_s - misses[0])) // 60) + 1
                raise PeopleError(f"too many wrong passwords: try again in {wait} min")
        now = _now()
        with self._held() as data:
            entry = data["people"].get(name)
            # a name nobody has costs the same scrypt: the time says nothing
            kept = (entry or {}).get("password") or _NOBODY
            if not password_matches(password or "", kept) or entry is None:
                with self._lock:
                    self._misses.setdefault(name, []).append(time.monotonic())
                raise wrong
            self._fresh(entry, now)
            session = self._open(entry, now, device)
        with self._lock:
            self._misses.pop(name, None)
        return session

    @staticmethod
    def _open(entry: dict[str, Any], now: datetime, device: str) -> str:
        session = "s." + secrets.token_urlsafe(32)
        entry["sessions"][_hash(session)] = {"since": _iso(now), "used": _iso(now),
                                             "device": device[:80]}
        return session

    def who(self, session: str) -> str | None:
        """The person a session belongs to, or None. Its last use is noted."""
        if not session.startswith("s."):
            return None
        key, now = _hash(session), _now()
        try:
            data = self._read()
        except PeopleError:
            return None
        idle = now - timedelta(days=IDLE_DAYS)
        for name, entry in data["people"].items():
            kept = (entry.get("sessions") or {}).get(key)
            if kept is None:
                continue
            used = datetime.fromisoformat(kept["used"])
            if used <= idle:
                return None
            if (now - used).total_seconds() > TOUCH_SECONDS:
                with self._held() as held:
                    s = held["people"].get(name, {}).get("sessions", {}).get(key)
                    if s is not None:
                        s["used"] = _iso(now)
            return name
        return None

    def leave(self, session: str) -> None:
        """This one device signed out."""
        key = _hash(session)
        with self._held() as data:
            for entry in data["people"].values():
                (entry.get("sessions") or {}).pop(key, None)
