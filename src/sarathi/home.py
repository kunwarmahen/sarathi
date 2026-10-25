"""`sarathi home`: one page that links to every program's own page,
and a chat with your agents through Dvara.

Each program Sarathi starts has a page of its own: Yantra's, where you
talk to the agent; Samay's, for what runs later; Setu's, for your
accounts; Dvara's, for the door and the people behind it. Sparsh, when
it's here, gets a card too: your phone, watched from the phone panel on
Yantra's page. Each sits on
its own port, and the token-protected ones (Samay, Setu, Dvara) want the
address their program printed, token and all. Four addresses and three
keys is a lot to keep. ``sarathi home`` is one bookmark:

    GET /api/pieces     each page: what it is for, up or down, its link;
                        and where your memories are kept
    POST /api/memory    {"via": "local"|"smritikosh"}: the one switch here

LINKING, AND A CHAT THAT ONLY PASSES THROUGH. Sarathi holds no logic of
its own, and this page doesn't change that. Up or down is whether the
page's port answers; the line under it is the program's own ``status``
(the same one ``sarathi status`` prints); and **Open** is that program's
page. A page that isn't running says the command that starts it.

ONE SWITCH: WHERE YOUR MEMORIES ARE KEPT. The memory card says which store
Yantra uses -- its own file, or Smritikosh -- and, for Smritikosh, whether
it answers and how many memories are yours. Its button is the same as
``sarathi smritikosh`` / ``--off`` once Smritikosh is set up: it writes
``[memory] via`` and runs ``sarathi up``, which starts Yantra (and Dvara)
again with it. Setting Smritikosh up the first time stays in a terminal:
it may need a password typed, and it can take a minute. Apart from Settings (editing.py), where each
program checks and writes its own file, nothing else on the page
starts, stops or changes anything. The card also links to
Smritikosh's own dashboard, when its checkout has one: open when it
answers as Smritikosh, else the command that starts it. Its sign-in is
Smritikosh's own (a username and password), never a key from here.

With Dvara on, the page also has a chat: Dvara's web channel (its
``web.py``), as you, the owner. Every word goes to Dvara and comes back
from it -- rules, allowance and questions are Dvara's, exactly as on
Telegram -- and what a schedule sends you waits there as a line until
you open the page. The chat keeps its own conversation; one on Telegram
doesn't continue here. Dvara's token stays in this process and never
reaches the browser, the way Dvara's own page keeps it:

    GET  /api/chat?after=N        your lines since N, agents, questions
    POST /api/chat                {"agent", "text", "files"?: [{"name", "data"}]}
    POST /api/chat/asks/ID        {"approve": true|false}
    POST /api/chat/holds/ID       {"answers": {call id: true|false|reason}}
    GET  /api/chat/file?line=&n=  a file an answer carried
    GET  /api/chat/spoken?line=   an answer read aloud (WAV)
    GET  /api/chat/steps?line=    what an answer's turn did, step by step
    GET  /api/chat/steps/export?line=   the same, as a file for a bug report
    POST /api/chat/accounts-page  {}: a one-time link to your own Setu page
    GET  /api/chat/push           your ntfy server and topic, for notices on a phone

EVERYONE IN THE HOUSE, EACH THEIR OWN CHAT. The other people in
Dvara's actors file sign in here too (people.py: an invite from the
owner, a password chosen once), and the same chat speaks to Dvara as
them. A person signed in gets their chat and nothing else: the cards,
the keys, the memory switch and the people list answer 403, whatever
the script in their browser draws. The owner sees and invites them:

    GET  /api/me                   who this is: the owner, or a person
    GET  /api/people               everyone in the actors file, signed in or not
    POST /api/people/NAME/invite   a one-time link to send them
    POST /api/people/NAME/sign-out every device of theirs signed out
    POST /api/claim                {"link", "password"}: an invite used
    POST /api/sign-in              {"name", "password"}: a session for this device
    POST /api/sign-out             this device signed out

EVERY SETTINGS FILE, THE OWNER'S ALONE (editing.py). Each program checks
and writes its own file; a person signed in gets 403:

    GET  /api/settings                     every file's settings and text
    GET  /api/version                      `sarathi version --json`: which commit of each
                                           project runs (the image's, on the podman road)
    GET  /api/doctor[?news=1]              `sarathi doctor --json`: what's wrong, and its
                                           fix; with news, what's new since the last
                                           such ask (Samay's doctor road, by the
                                           doctor key, which opens this and nothing else)
    POST /api/doctor/morning               Samay asked once to run the doctor each morning
    GET  /api/backup                       the backups: the folder, the newest, the key
    POST /api/backup                       `sarathi backup`, now (and Samay's backup road,
                                           by the backup key, which opens this alone)
    POST /api/backup/nightly               Samay asked once to back up every night
    POST /api/settings/image               `sarathi image && sarathi up`, behind the answer
    POST /api/settings/sarathi             {table: {key: value}}: sarathi.toml
    POST /api/settings/key/NAME            {"value"}: a key into secrets.env
    POST /api/settings/person/NAME         {fields} | {"remove": true}: actors.toml
    POST /api/settings/rules               [rules]: policy.toml
    POST /api/settings/household           {"add"|"forget"|"yes"|"no"}: what everyone's
                                           agents know (dvara household.json)
    POST /api/settings/agent/NAME          {"tables", "prompt"} | {"remove": true}
                                           | {"from_example": NAME}
    POST /api/settings/setu/NAME           {"value"}: `setu config NAME`
    POST /api/settings/text/KIND           {"text", "name"}: a whole file as text
    POST /api/settings/tool/AGENT          {"person", "skill", "remove"?}: a learned skill
                                           made a tool, or the tool taken back
                                           (sarathi, actors, policy, agent, prompt, site)
    POST /api/settings/phone               {"do": "tcpip"|"connect"|"pair"|"iphone"
                                           |"cable"|"remove", "address", "code",
                                           "name"}: the phone, reached from this
                                           computer, its address saved; with a
                                           name, one of several ([phone.NAME])
    POST /api/settings/apply               `sarathi up`, for what needs a restart

With ``--also-host`` (the door's window address, when it is one) the page
listens there too, so a phone at home can open a person's link.

THE LINK CARRIES THE KEY. Samay's, Setu's and Dvara's pages each keep
their token in their own folder (``serve.token``, ``page.token``), which
the containers mount at the same path as this machine, so one click
opens each page already signed in. That makes this page a key ring, so
IT HAS A TOKEN TOO: ``$SARATHI_HOME_TOKEN``, or one made once in
Sarathi's state folder (readable by you alone), printed after a ``#`` in
the address. Without it, any program on the machine could read every
key from ``/api/pieces``.

A page whose token can't be found (not started yet, or started with a
token from the environment that this process doesn't have) gets a link
without one, and its own page says how to open it.

The program statuses are asked at most every 30 seconds: each one is a
subprocess, and a page left open shouldn't run four programs every few
seconds.

Standard library, as every page in this family is.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from sarathi.config import (
    DOOR_TOKEN,
    YANTRA_TOKEN,
    Config,
    read_secrets,
    render,
    settings_path,
    state_dir,
)
from sarathi.people import INVITE_HOURS, People, PeopleError, actor_ids
from sarathi.services import HOST, answers
from sarathi.siblings import SIBLINGS, locate

DEFAULT_PORT = 8760
ENV_TOKEN = "SARATHI_HOME_TOKEN"
TOKEN_FILE = "home.token"
#: The key Samay's doctor road asks with: it opens GET /api/doctor only.
DOCTOR_TOKEN_FILE = "doctor.token"
#: The doctor's last answer to that road, to say what's new against.
DOCTOR_TOLD = "doctor-told.json"
#: The key Samay's backup road asks with: it opens POST /api/backup only.
BACKUP_TOKEN_FILE = "backup.token"
STATUS_EVERY = 30.0
#: The longest chat message passed on, in bytes.
MAX_BODY = 256 * 1024     # a whole settings file, or an agent's prompt
#: A chat message with files in it (base64: a third bigger than the files;
#: Dvara keeps up to 20 MB of them, its attached.py).
CHAT_BODY = 28 * 1024 * 1024

STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/page.js": ("page.js", "text/javascript; charset=utf-8"),
          "/settings.js": ("settings.js", "text/javascript; charset=utf-8"),
          "/md.js": ("md.js", "text/javascript; charset=utf-8"),
          "/page.css": ("page.css", "text/css; charset=utf-8"),
          "/favicon.svg": ("favicon.svg", "image/svg+xml")}

POLICY = ("default-src 'none'; script-src 'self'; style-src 'self'; "
          "connect-src 'self'; img-src 'self' data: blob:; media-src blob:; "
          "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


@dataclass(frozen=True)
class Page:
    """One program's page: where it is, and where its key is kept."""

    name: str              # the sibling's name, as `sarathi status` has it
    title: str
    purpose: str
    port: int
    token_env: str | None = None
    token_file: Path | None = None
    start: str = "sarathi up"
    #: How the link carries the token: after ``#`` (the page reads it), or
    #: as ``?token=`` (Yantra's: the server sets a cookie from it).
    token_in: str = "/#token="
    #: The token is Sarathi's own, kept in secrets.env under token_env.
    in_secrets: bool = False

    def token(self) -> str | None:
        if self.token_env and os.environ.get(self.token_env, "").strip():
            return os.environ[self.token_env].strip()
        if self.in_secrets and self.token_env:
            return read_secrets().get(self.token_env) or None
        if self.token_file is None:
            return None
        try:
            kept = self.token_file.read_text().strip()
        except OSError:
            return None
        return kept or None


def pages(config: Config, env: dict[str, str] | None = None) -> list[Page]:
    """The pages this machine's settings say there are, in the order a
    person reaches for them."""
    env = os.environ if env is None else env
    home = Path.home()
    xdg_state = Path(env.get("XDG_STATE_HOME") or home / ".local" / "state")
    setu_home = Path(env.get("SETU_HOME") or xdg_state / "setu").expanduser()
    samay_state = Path(env.get("SAMAY_STATE", "").strip() or home / ".samay").expanduser()
    # Yantra's page wants the token Sarathi made for it (Yantra's gate.py)
    yantra = {"token_env": YANTRA_TOKEN, "token_in": "/?token=", "in_secrets": True}
    found = [Page("yantra", "Yantra", "Talk to your agent.", config.web_port, **yantra)]
    if config.clock_on:
        found.append(Page("samay", "Samay", "What runs later, and what each run said.",
                          config.clock_port, "SAMAY_TOKEN", samay_state / "serve.token"))
    from sarathi.services import watching

    if watching(config, dict(env)):
        prahari_state = Path(env.get("PRAHARI_STATE", "").strip()
                             or home / ".prahari").expanduser()
        found.append(Page("prahari", "Prahari", "What you're waiting for, what each "
                          "watch saw, and the inlet a phone app knocks on.",
                          config.watch_port, "PRAHARI_TOKEN", prahari_state / "serve.token"))
    # started by `sarathi up` when [pages] is on; by hand otherwise
    by_up = config.pages.on
    found.append(Page("setu", "Setu", "Your accounts: what's connected, at what level, "
                      "and what each one was used for; who has their own page "
                      "open; the catalog and Setu's settings.", config.pages.setu_port,
                      "SETU_PAGE_TOKEN", setu_home / "page.token",
                      start="sarathi up" if by_up else
                      f"setu serve --port {config.pages.setu_port}"))
    door = config.door
    sparsh = next(s for s in SIBLINGS if s.name == "sparsh")
    on_cable = config.road != "podman" and locate(sparsh, dict(env)) is not None
    over_wifi = config.road == "podman" and config.phone is not None \
        and bool(config.phone.addresses or config.phone.wdas or config.phone.named)
    if on_cable or over_wifi:
        # Sparsh has no page of its own: the phone is watched from the
        # panel on Yantra's page, so the card opens that page. On the
        # podman road only with a Wi-Fi address or an iPhone's
        # WebDriverAgent: a container can't reach a phone on a USB cable.
        named = config.phone.named if config.phone is not None else ()
        if named:
            # several, each by a name: the card says which (Yantra's panel
            # shows each one's screen and steps)
            which = ", ".join(f"{p.name} ({p.kind})" for p in named)
            found.append(Page(
                "sparsh", "Your phones", f"{which}, and what the agent did on each: the "
                "phone panel on Yantra's page.", config.web_port, **yantra))
        else:
            found.append(Page(
                "sparsh", "Your phone", "Your phone and what the agent did on it: the phone "
                "panel on Yantra's page.", config.web_port, **yantra))
    if door is not None:
        found.append(Page(
            "dvara", "Dvara", "Your door: the people on it, what they've spent, what "
            "their agents have been doing, their files and schedules, and your "
            "questions.", config.pages.door_port, "DVARA_PAGE_TOKEN",
            door.path("state") / "page.token",
            start="sarathi up" if by_up else
            (f"DVARA_TOKEN=... dvara --root {door.root} --actors {door.actors} "
             f"--state {door.state} page --as {door.owner} --port {config.pages.door_port}")))
    return found


def home_token() -> str:
    """``$SARATHI_HOME_TOKEN``, or the one kept in Sarathi's state folder."""
    configured = os.environ.get(ENV_TOKEN, "").strip()
    if configured:
        if len(configured) < 16:
            raise ValueError(f"{ENV_TOKEN} must be at least 16 characters")
        return configured
    path = state_dir() / TOKEN_FILE
    try:
        kept = path.read_text().strip()
        if len(kept) >= 16:
            return kept
    except OSError:
        pass
    token = secrets.token_urlsafe(24)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(token + "\n")
    return token


def memory_status(config: Config) -> dict[str, Any]:
    """The memory card: which store, and for Smritikosh how it is doing."""
    from sarathi import smritikosh

    seen = smritikosh.health(config) if config.remembers_in_smritikosh else {}
    return {"via": config.memory, "set_up": config.smritikosh.checkout is not None,
            "up": seen.get("up"), "memories": seen.get("memories"),
            "said": smritikosh.health_line(config, seen or None),
            "server": config.smritikosh.url if config.remembers_in_smritikosh else None,
            "dashboard": smritikosh.dashboard(config)}


#: The night run Sarathi asks Samay for: Samay's own tests road, which
#: replays every conversation kept as a test (Yantra's note 141).
NIGHTLY = {"prompt": "the night's kept tests", "when": "at 03:00",
           "runner": "tests", "time_limit": 3600, "notify": "when_new"}
MORNING = {"prompt": "the house, checked by Sarathi's doctor", "when": "at 07:30",
           "runner": "doctor", "time_limit": 300, "notify": "when_new"}
#: Before the kept tests, so a night's backup never waits behind them.
BACKUP_NIGHTLY = {"prompt": "the house, backed up", "when": "at 02:30",
                  "runner": "backup", "time_limit": 3600, "notify": "when_new"}


def doctor_token() -> str:
    """The doctor key, made once in Sarathi's state folder (yours alone).
    Not the home token: Samay holds this one, and it opens the doctor's
    answer and nothing else -- no page keys, no chat, no settings."""
    return _key_file(DOCTOR_TOKEN_FILE)


def backup_token() -> str:
    """The backup key: Samay's too, and it opens POST /api/backup alone. A
    backup is sealed to a public key, so this key can make one and open
    none."""
    return _key_file(BACKUP_TOKEN_FILE)


def _key_file(name: str) -> str:
    path = state_dir() / name
    try:
        kept = path.read_text().strip()
        if len(kept) >= 16:
            return kept
    except OSError:
        pass
    token = secrets.token_urlsafe(24)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(token + "\n")
    return token


def run_image() -> None:
    """``sarathi image && sarathi up``, behind the answer: minutes long,
    and it restarts this page at the end."""
    from sarathi.services import sarathi_program

    log = state_dir() / "logs" / "rebuild.log"
    log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    program = sarathi_program()
    with open(log, "ab") as out:
        subprocess.Popen(["sh", "-c", '"$0" image && "$0" up', program],
                         stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                         start_new_session=True)


def tests_root(env: dict[str, str] | None = None) -> Path:
    """Where Yantra keeps the kept tests (its kept_tests.default_root)."""
    env = os.environ if env is None else env
    chosen = env.get("YANTRA_TESTS", "").strip()
    if chosen:
        return Path(chosen).expanduser()
    state = Path(env.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return state / "yantra" / "tests"


def _samay(config: Config, method: str, path: str, body: dict | None = None,
           env: dict[str, str] | None = None) -> Any:
    """One call to Samay's own API, with its token. Samay checks and
    keeps the schedule; Sarathi only asks."""
    env = os.environ if env is None else env
    state = Path(env.get("SAMAY_STATE", "").strip() or Path.home() / ".samay").expanduser()
    token = env.get("SAMAY_TOKEN", "").strip()
    if not token:
        token = (state / "serve.token").read_text().strip()
    request = urllib.request.Request(
        f"http://{HOST}:{config.clock_port}/api/{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as answer:
        return json.loads(answer.read() or b"null")


def kept_tests_status(config: Config, env: dict[str, str] | None = None) -> dict[str, Any]:
    """The kept-tests card: the last night's summary (Yantra's last.json),
    and whether Samay has the night run. Nothing here runs a test."""
    summary = None
    try:
        raw = json.loads((tests_root(env) / "last.json").read_text())
        if raw.get("format") == "yantra.tests.v1":
            summary = raw
    except (OSError, ValueError):
        pass
    nightly, samay = None, False
    if config.clock_on:
        try:
            listed = sys.modules[__name__]._samay(config, "GET", "schedules", env=env)
            rows = listed.get("schedules", listed) if isinstance(listed, dict) else listed
            nightly = next((r for r in rows or [] if r.get("runner") == "tests"), None)
            samay = True
        except (OSError, ValueError, urllib.error.URLError):
            samay = False
    kept = sum(1 for _ in tests_root(env).glob("**/cases.toml")) if tests_root(env).is_dir() else 0
    return {"summary": summary, "nightly": nightly, "samay": samay,
            "clock_on": config.clock_on, "suites": kept}


def run_up() -> None:
    """``sarathi up``, behind the answer: it outlives this request, and
    this page, if it is ever the one restarted."""
    from sarathi.services import sarathi_program

    log = state_dir() / "logs" / "memory-switch.log"
    log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(log, "ab") as out:
        subprocess.Popen([sarathi_program(), "up"], stdin=subprocess.DEVNULL, stdout=out,
                         stderr=subprocess.STDOUT, start_new_session=True)


class Home:
    """What ``/api/pieces`` answers, apart from HTTP."""

    def __init__(self, config: Config, said: Callable[[], dict[str, str]],
                 *, up: Callable[[int], bool] = answers, every: float = STATUS_EVERY,
                 memory: Callable[[Config], dict[str, Any]] = memory_status,
                 restart: Callable[[], None] = run_up,
                 tests: Callable[[Config], dict[str, Any]] | None = None,
                 ask_samay: Callable[..., Any] | None = None,
                 doctor: Callable[[], dict[str, Any]] | None = None,
                 rebuild: Callable[[], None] = run_image,
                 backup: Callable[[], dict[str, Any]] | None = None,
                 version: Callable[[Config], dict[str, Any]] | None = None) -> None:
        self.config = config
        self._said = said
        self._up = up
        self._every = every
        self._cache: tuple[float, dict[str, str]] | None = None
        self._memory = memory
        self._memory_cache: tuple[float, dict[str, Any]] | None = None
        self._restart = restart
        self._tests = tests
        self._ask_samay = ask_samay
        self._doctor = doctor
        self._rebuild = rebuild
        self._backup = backup
        self._backing_up = threading.Lock()
        self._version = version
        self._version_cache: tuple[float, dict[str, Any]] | None = None
        self._lock = threading.Lock()

    def doctor(self, news: bool = False) -> tuple[int, dict[str, Any]]:
        """(status, answer): ``sarathi doctor``, asked now. Never cached: a
        person pressing Check has just fixed something. ``news``: what's
        new since the last ask with news (doctor.news), which only
        Samay's doctor road asks for, so pressing Check doesn't eat it."""
        if self._doctor is None:
            return 404, {"detail": "the doctor isn't wired in here"}
        try:
            answer = self._doctor()
        except Exception as exc:          # a check that broke is a line, not a 500
            return 500, {"detail": f"the check itself failed: {exc}"}
        if news:
            from sarathi import doctor

            answer = doctor.news(answer, state_dir() / DOCTOR_TOLD)
        return 200, answer

    def morning(self) -> tuple[int, str]:
        """(status, words): Samay asked once to run the doctor each morning."""
        return self._ask_once(MORNING, "doctor", "Samay already checks the house "
                              "each morning", "Every morning at 07:30 Samay asks the "
                              "doctor. You hear only when something new is wrong.")

    def backup_now(self) -> tuple[int, dict[str, Any]]:
        """(status, sarathi.backup.made.v1): one backup, now; one at a time."""
        from sarathi.backup import BackupError

        if self._backup is None:
            return 404, {"detail": "backups aren't wired in here"}
        if not self._backing_up.acquire(blocking=False):
            return 409, {"detail": "a backup is being made already"}
        try:
            return 200, self._backup()
        except BackupError as exc:
            return 409, {"detail": str(exc)}
        except Exception as exc:          # a full disk, a folder gone: said, not a 500
            return 500, {"detail": f"the backup didn't finish: {exc}"}
        finally:
            self._backing_up.release()

    def backups(self) -> dict[str, Any]:
        """Where they go, the newest there, and whether the key is chosen."""
        from sarathi import backup

        folder = self.config.backup.path()
        made = sorted(folder.glob(f"sarathi-*{backup.SUFFIX}"),
                      key=lambda p: p.stat().st_mtime) if folder.is_dir() else []
        newest = made[-1] if made else None
        return {"folder": str(folder), "keep": self.config.backup.keep,
                "key": backup.read_key() is not None, "count": len(made),
                "busy": self._backing_up.locked(),
                "newest": None if newest is None else {
                    "name": newest.name, "bytes": newest.stat().st_size,
                    "made": time.strftime("%a %d %b %H:%M",
                                          time.localtime(newest.stat().st_mtime))}}

    def backup_nightly(self) -> tuple[int, str]:
        """(status, words): Samay asked once to back up every night."""
        return self._ask_once(BACKUP_NIGHTLY, "backup", "Samay already backs up every night",
                              "Every night at 02:30 Samay makes a backup in "
                              f"{self.config.backup.folder}, keeping the newest "
                              f"{self.config.backup.keep or 'all'}. You hear only when "
                              "one fails.")

    def rebuild(self) -> str:
        self._rebuild()
        return ("Rebuilding the image, then starting everything again: several "
                "minutes, and this page restarts at the end. Its log: "
                f"{state_dir() / 'logs' / 'rebuild.log'}")

    def version(self) -> dict[str, Any]:
        """``sarathi version --json`` with the footer's line, asked at most
        every ``every`` seconds: it is a git or two per project."""
        from sarathi import version

        with self._lock:
            now = time.monotonic()
            if self._version_cache is None or now - self._version_cache[0] > self._every:
                got = (self._version or version.report)(self.config)
                self._version_cache = (now, {**got, "said": version.headline(got)})
            return self._version_cache[1]

    def tests(self) -> dict[str, Any]:
        return (self._tests or kept_tests_status)(self.config)

    def nightly(self) -> tuple[int, str]:
        """(status, words): Samay asked for the night run, once."""
        return self._ask_once(NIGHTLY, "tests", "Samay already runs them every night",
                              "Every night at 03:00 Samay replays your kept tests. "
                              "You hear about it only when one breaks.")

    def _ask_once(self, schedule: dict[str, Any], runner: str, already: str,
                  done: str) -> tuple[int, str]:
        """Samay asked for ``schedule`` -- unless one on ``runner`` is there."""
        if not self.config.clock_on:
            return 409, "Samay isn't on here: turn it on in Settings first"
        try:
            ask = self._ask_samay or _samay
            listed = ask(self.config, "GET", "schedules")
            rows = listed.get("schedules", listed) if isinstance(listed, dict) else listed
            if any(r.get("runner") == runner for r in rows or []):
                return 200, already
            ask(self.config, "POST", "schedules", schedule)
        except urllib.error.HTTPError as exc:
            try:
                why = json.loads(exc.read() or b"{}").get("detail") or str(exc)
            except ValueError:
                why = str(exc)
            return exc.code, f"Samay said no: {why}"
        except (OSError, ValueError) as exc:
            return 502, f"Samay didn't answer: {exc}"
        return 200, done

    def memory(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            if self._memory_cache is None or now - self._memory_cache[0] > self._every:
                self._memory_cache = (now, self._memory(self.config))
            return self._memory_cache[1]

    def switch(self, via: str) -> tuple[int, str]:
        """(status, words): ``[memory] via`` written, and ``sarathi up`` run."""
        from sarathi.config import MEMORY_ROADS, ConfigError, load

        if via not in MEMORY_ROADS:
            return 400, f"via is one of {', '.join(MEMORY_ROADS)}"
        try:
            config = load()          # as it is on disk now, not as it was at start
        except ConfigError as exc:
            return 409, str(exc)
        if via == "smritikosh" and config.smritikosh.checkout is None:
            return 409, ("Smritikosh isn't set up yet: run `sarathi smritikosh` in a "
                         "terminal once; this switch works after that")
        if via == config.memory:
            return 200, f"already {via}"
        config = replace(config, memory=via)
        settings_path().write_text(render(config))
        with self._lock:
            self.config, self._memory_cache = config, None
        self._restart()
        where = "Smritikosh" if via == "smritikosh" else "Yantra's own file"
        return 200, (f"Switching to {where}: Yantra and Dvara start again with it, "
                     "in about a minute. Nothing is deleted.")

    def said(self) -> dict[str, str]:
        """Each program's one line from its own status, asked at most every
        ``every`` seconds."""
        with self._lock:
            now = time.monotonic()
            if self._cache is None or now - self._cache[0] > self._every:
                self._cache = (now, self._said())
            return self._cache[1]

    def pieces(self, opened_at: str | None = None) -> list[dict[str, Any]]:
        """Each page's card. ``opened_at``: the name this page was opened
        by (its Host). With ``[house]`` every page is published on the
        house address too, so each card links by that same name -- the
        house's name on a phone, 127.0.0.1 here -- and a phone never gets
        a link to itself."""
        lines = self.said()
        out = []
        host = opened_at if self.config.house is not None and opened_at else HOST
        shown = f"[{host}]" if ":" in host else host
        for page in pages(self.config):
            token = page.token()
            url = f"http://{shown}:{page.port}/"
            out.append({"name": page.name, "title": page.title, "purpose": page.purpose,
                        "up": self._up(page.port), "url": url,
                        "open": f"{url.rstrip('/')}{page.token_in}{token}" if token
                        else url,
                        "keyed": token is not None or page.token_file is None,
                        "said": lines.get(page.name, ""), "start": page.start})
        return out


class ChatError(Exception):
    """Dvara said no, or couldn't be reached: its words, and a status."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status


#: How long a call to Dvara may take: a look, or a turn being started
#: (a turn itself runs behind the request, in Dvara).
CHAT_TIMEOUT = 15.0


class Chat:
    """Dvara's web channel, as whoever this page says is talking: the owner,
    or a person signed in (people.py). Passes through; decides nothing."""

    def __init__(self, url: str, token: str, actor: str) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.actor = actor

    @classmethod
    def for_config(cls, config: Config) -> Chat | None:
        """The door's address, its token (secrets.env) and your id in its
        actors file; None with the door off or no token yet."""
        door = config.door
        if door is None:
            return None
        token = os.environ.get(DOOR_TOKEN, "").strip() or read_secrets().get(DOOR_TOKEN, "")
        if not token:
            return None
        return cls(f"http://{HOST}:{door.port}", token, door.owner)

    def call(self, method: str, path: str, body: dict | None = None,
             query: dict | None = None, *, actor: str | None = None) -> tuple[bytes, str]:
        actor = actor or self.actor
        q = urllib.parse.urlencode({"actor": actor, **(query or {})})
        data = None
        if body is not None:
            data = json.dumps({**body, "actor": actor}).encode()
        request = urllib.request.Request(
            f"{self.url}{path}?{q}", data=data, method=method,
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=CHAT_TIMEOUT) as answer:
                return answer.read(), answer.headers.get("Content-Disposition", "")
        except urllib.error.HTTPError as exc:
            try:
                said = json.loads(exc.read() or b"{}").get("detail")
            except (ValueError, AttributeError):
                said = None
            if exc.code == 404 and path == "/web" and said and "--web" in said:
                said = ("Dvara is running without its web channel: restart it "
                        "with `sarathi down` and `sarathi up`")
            raise ChatError(exc.code, str(said or exc.reason)) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ChatError(502, f"Dvara isn't answering at {self.url}: "
                                 f"{getattr(exc, 'reason', exc)}") from None

    def json(self, method: str, path: str, body: dict | None = None,
             query: dict | None = None, *, actor: str | None = None) -> dict[str, Any]:
        raw, _ = self.call(method, path, body, query, actor=actor)
        return json.loads(raw or b"{}")


def invite_address(config: Config, link: str) -> tuple[str, bool]:
    """(the address a person opens, whether a phone can reach it): the
    house's name (``[house]``), or the address the door's window uses,
    when there is one; else this computer, and the owner is told so."""
    reachable = config.people_host() is not None
    base = config.link(config.pages.home_port) if reachable else \
        f"http://{HOST}:{config.pages.home_port}/"
    return f"{base}#invite={link}", reachable


class HomeServer:
    def __init__(self, home: Home, token: str, *, host: str = HOST,
                 port: int = DEFAULT_PORT, chat: Chat | None = None,
                 people: People | None = None, also_host: str | None = None,
                 doctor_key: str | None = None, backup_key: str | None = None) -> None:
        self.home = home
        self.chat = chat
        self.token = token
        #: Samay's key for the doctor's answer alone (doctor_token); a
        #: random one when none is given, so no empty header ever matches.
        self.doctor_key = doctor_key or secrets.token_urlsafe(24)
        #: Samay's key for making a backup alone (backup_token).
        self.backup_key = backup_key or secrets.token_urlsafe(24)
        self.people = people
        self.httpd = ThreadingHTTPServer((host, port), _handler(self))
        self.httpd.daemon_threads = True
        # the house address too (people_host), so a phone at home reaches it
        self.also: ThreadingHTTPServer | None = None
        #: Why the house address isn't served, when it was asked for and isn't.
        self.also_problem: str | None = None
        if also_host and also_host != host:
            try:
                self.also = ThreadingHTTPServer((also_host, self.httpd.server_address[1]),
                                                _handler(self))
                self.also.daemon_threads = True
            except OSError as exc:
                # Tailscale down, a moved address: your own page still opens here
                self.also_problem = f"{also_host} can't be listened on ({exc.strerror})"

        self._threads: list[threading.Thread] = []

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address[:2]
        if host in ("0.0.0.0", "::"):
            host = HOST
        return f"http://{host}:{port}/"

    @property
    def page_url(self) -> str:
        return f"{self.url}#token={self.token}"

    def serve_forever(self) -> None:
        if self.also is not None:
            threading.Thread(target=self.also.serve_forever, name="sarathi-home-house",
                             daemon=True).start()
        self.httpd.serve_forever()

    def start(self) -> None:
        for httpd in (self.httpd, self.also):
            if httpd is not None:
                thread = threading.Thread(target=httpd.serve_forever,
                                          name="sarathi-home", daemon=True)
                thread.start()
                self._threads.append(thread)

    def stop(self) -> None:
        for httpd in (self.httpd, self.also):
            if httpd is not None:
                httpd.shutdown()
                httpd.server_close()
        for thread in self._threads:
            thread.join()


@dataclass(frozen=True)
class Who:
    """Who a request is from: the owner (the page's key), or a person
    signed in, by their id in Dvara's actors file."""

    owner: bool
    actor: str | None          # None: the owner, with no door to name them in
    session: str | None = None


def _strangers(config: Config) -> list[str]:
    """Telegram ids that messaged Dvara's bot and aren't in its actors file."""
    from sarathi.door import strangers

    try:
        if config.road == "podman":
            from sarathi.podman import UNITS, journal_tail
            return strangers(journal_tail(UNITS["dvara"], 400))
        from sarathi.services import log_tail
        return strangers(log_tail("dvara", 400))
    except Exception:  # noqa: BLE001 -- a list to help, never a failure
        return []


def _handler(server: HomeServer):
    class Handler(BaseHTTPRequestHandler):
        server_version = "sarathi"

        def log_message(self, *_a: Any) -> None:
            pass

        def _send(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            # the links carry keys: an address must not leak to the page opened
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", POLICY)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data: dict[str, Any]) -> None:
            self._send(code, json.dumps(data).encode(), "application/json")

        def _who(self) -> Who | None:
            """The owner, a person, or None (and a 401 said)."""
            offered = self.headers.get("Authorization", "")
            if hmac.compare_digest(offered.encode(), f"Bearer {server.token}".encode()):
                return Who(True, server.chat.actor if server.chat else None)
            session = offered.removeprefix("Bearer ").strip()
            if server.people is not None and session.startswith("s."):
                name = server.people.who(session)
                if name is not None:
                    return Who(False, name, session)
            self._json(401, {"detail": "missing or wrong token, or signed out"})
            return None

        def _owner(self) -> Who | None:
            who = self._who()
            if who is not None and not who.owner:
                self._json(403, {"detail": "only the owner's own page has that"})
                return None
            return who

        def _body(self, limit: int = MAX_BODY) -> dict | None:
            try:
                size = int(self.headers.get("Content-Length") or 0)
                if size > limit:
                    self._json(413, {"detail": "that message is too long"
                                     if limit == MAX_BODY else
                                     "those files are too big to send at once"})
                    return None
                body = json.loads(self.rfile.read(size) or b"{}")
            except ValueError:
                self._json(400, {"detail": "the body must be JSON"})
                return None
            if not isinstance(body, dict):
                self._json(400, {"detail": "the body must be a JSON object"})
                return None
            return body

        def _chat(self, who: Who, method: str, path: str, body: dict | None = None,
                  query: dict | None = None) -> None:
            if server.chat is None:
                return self._json(404, {"detail": "no chat here: Dvara is off, or "
                                                  "has no token yet (`sarathi dvara`)"})
            try:
                return self._json(200, server.chat.json(method, path, body, query,
                                                        actor=who.actor))
            except ChatError as exc:
                return self._json(exc.status, {"detail": str(exc)})

        def _push(self, who: Who) -> None:
            """How this person subscribes to their notices in the ntfy app:
            the house's ntfy server and their own topic, which Dvara keeps."""
            server_url = server.home.config.ntfy_url()
            if server_url is None or server.chat is None:
                return self._json(200, {"on": False})
            try:
                topic = server.chat.json("GET", "/web/push", actor=who.actor).get("topic")
            except ChatError as exc:
                return self._json(exc.status, {"detail": str(exc)})
            if not topic:
                return self._json(200, {"on": False})
            hostport = urlparse(server_url).netloc
            return self._json(200, {"on": True, "server": server_url, "topic": topic,
                                    "link": f"ntfy://{hostport}/{topic}?secure=false",
                                    "house": server.home.config.people_host() is not None})

        def _past(self, url) -> None:
            """The person's own past conversations, from Dvara (its past.py):
            the list (``?q=`` searches), and one by its id to read."""
            who = self._who()
            if who is None:
                return None
            rest = url.path[len("/api/chat/chats"):].strip("/")
            if not rest:
                q = parse_qs(url.query).get("q", [""])[-1]
                return self._chat(who, "GET", "/web/chats", query={"q": q})
            if rest.endswith("/export") and rest.count("/") == 1:
                # one of theirs as a file to share: Dvara writes it, we pass it on
                return self._past_file(who, rest[:-len("/export")])
            return self._chat(who, "GET", f"/web/chats/{urllib.parse.quote(rest, safe='')}")

        def _past_file(self, who: Who, conversation_id: str) -> None:
            if server.chat is None:
                return self._json(404, {"detail": "no chat here"})
            try:
                raw, named = server.chat.call(
                    "GET", f"/web/chats/{urllib.parse.quote(conversation_id, safe='')}/export",
                    actor=who.actor)
            except ChatError as exc:
                return self._json(exc.status, {"detail": str(exc)})
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            if named:
                self.send_header("Content-Disposition", named)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(raw)
            return None

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path in STATIC:
                name, kind = STATIC[url.path]
                return self._send(200, files("sarathi").joinpath("static", name)
                                  .read_bytes(), kind)
            if url.path == "/api/settings":
                return self._settings_get()
            if url.path == "/api/doctor":
                query = {k: v[-1] for k, v in parse_qs(url.query).items()}
                offered = self.headers.get("Authorization", "")
                # the doctor key opens this one answer; anything else is the owner's
                if not hmac.compare_digest(offered.encode(),
                                           f"Bearer {server.doctor_key}".encode()) \
                        and self._owner() is None:
                    return None
                return self._json(*server.home.doctor(news=query.get("news") == "1"))
            if url.path == "/api/backup":
                if self._owner() is None:
                    return None
                return self._json(200, server.home.backups())
            if url.path == "/api/version":
                if self._owner() is None:
                    return None
                try:
                    return self._json(200, server.home.version())
                except Exception as exc:     # a bug is a 500 that says what, not a hang
                    return self._json(500, {"detail": f"{type(exc).__name__}: {exc}"})
            if url.path.startswith("/api/chat/chats"):
                return self._past(url)
            if url.path not in ("/api/pieces", "/api/chat", "/api/chat/file", "/api/me",
                                "/api/people", "/api/chat/push", "/api/chat/spoken",
                                "/api/chat/steps", "/api/chat/steps/export",
                                "/api/chat/declined"):
                return self._json(404, {"detail": "not found"})
            who = self._owner() if url.path in ("/api/pieces", "/api/people") \
                else self._who()
            if who is None:
                return None
            query = {k: v[-1] for k, v in parse_qs(url.query).items()}
            if url.path == "/api/me":
                return self._json(200, {"owner": who.owner, "name": who.actor,
                                        "chat": server.chat is not None})
            if url.path == "/api/people":
                return self._people_list()
            if url.path == "/api/chat/push":
                return self._push(who)
            if url.path == "/api/chat":
                return self._chat(who, "GET", "/web",
                                  query={"after": query.get("after", "0")})
            if url.path == "/api/chat/declined":
                # what they turned down with /remember not (Dvara's remembering.py)
                return self._chat(who, "GET", "/web/declined")
            if url.path == "/api/chat/steps":
                # what an answer's own turn did, step by step (Dvara's runsteps)
                return self._chat(who, "GET", "/web/steps",
                                  query={"line": query.get("line", "0")})
            if url.path == "/api/chat/steps/export":
                if server.chat is None:
                    return self._json(404, {"detail": "no chat here"})
                try:
                    raw, named = server.chat.call("GET", "/web/steps/export", query={
                        "line": query.get("line", "0")}, actor=who.actor)
                except ChatError as exc:
                    return self._json(exc.status, {"detail": str(exc)})
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                if named:
                    self.send_header("Content-Disposition", named)
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(raw)
                return None
            if url.path == "/api/chat/spoken":
                # an answer read aloud, as WAV (Dvara's spoken.py)
                if server.chat is None:
                    return self._json(404, {"detail": "no chat here"})
                try:
                    raw, _ = server.chat.call("GET", "/web/spoken", query={
                        "line": query.get("line", "0")}, actor=who.actor)
                except ChatError as exc:
                    return self._json(exc.status, {"detail": str(exc)})
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "private, max-age=86400")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(raw)
                return None
            if url.path == "/api/chat/file":
                if server.chat is None:
                    return self._json(404, {"detail": "no chat here"})
                try:
                    raw, named = server.chat.call("GET", "/web/file", query={
                        "line": query.get("line", "0"), "n": query.get("n", "0")},
                        actor=who.actor)
                except ChatError as exc:
                    return self._json(exc.status, {"detail": str(exc)})
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(raw)))
                if named:
                    self.send_header("Content-Disposition", named)
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(raw)
                return None
            try:
                return self._json(200, {"pieces": server.home.pieces(self._opened_at()),
                                        "memory": server.home.memory(),
                                        "tests": server.home.tests(),
                                        "chat": server.chat is not None,
                                        "people": server.people is not None
                                        and server.home.config.door is not None})
            except Exception as exc:     # a bug is a 500 that says what, not a hang
                return self._json(500, {"detail": f"{type(exc).__name__}: {exc}"})

        def _opened_at(self) -> str | None:
            """The name in this request's Host, when it is a plain name or
            address (never anything a link could not hold)."""
            raw = (self.headers.get("Host") or "").strip()
            name = raw[1:raw.index("]")] if raw.startswith("[") and "]" in raw \
                else raw.rsplit(":", 1)[0] if raw.count(":") == 1 else raw
            return name if re.fullmatch(r"[A-Za-z0-9.\-:]{1,253}", name or "") else None

        # ---- people (people.py): the owner adds them, they sign in --------------

        def _known(self) -> list[str]:
            door = server.home.config.door
            if door is None:
                raise PeopleError("Dvara is off: people sign in to talk to their agents "
                                  "through it (`sarathi dvara`)")
            return actor_ids(door.path("actors"))

        def _people_list(self) -> None:
            if server.people is None:
                return self._json(404, {"detail": "no sign-ins here"})
            door = server.home.config.door
            try:
                known = self._known()
                kept = {p.name: p for p in server.people.listing()}
            except PeopleError as exc:
                return self._json(409, {"detail": str(exc)})
            owner = door.owner if door else None
            out = []
            for name in sorted(set(known) | set(kept)):
                if name == owner:
                    continue
                p = kept.get(name)
                out.append({**(p.as_dict() if p else {"name": name, "signed_up": False,
                                                       "invite_until": None, "devices": 0,
                                                       "last_used": None}),
                            "on_roster": name in known})
            _, reachable = invite_address(server.home.config, "")
            return self._json(200, {"people": out, "reachable": reachable})

        def _device(self) -> str:
            return self.headers.get("User-Agent", "")[:80]

        def _people_post(self, parts: list[str]) -> None:
            if server.people is None:
                return self._json(404, {"detail": "no sign-ins here"})
            if parts == ["api", "sign-in"] or parts == ["api", "claim"]:
                body = self._body()
                if body is None:
                    return None
                try:
                    if parts[1] == "claim":
                        name, session = server.people.claim(
                            str(body.get("link") or ""), str(body.get("password") or ""),
                            self._device())
                    else:
                        name = str(body.get("name") or "").strip()
                        session = server.people.sign_in(
                            name, str(body.get("password") or ""), self._device())
                except PeopleError as exc:
                    return self._json(403, {"detail": str(exc)})
                return self._json(200, {"name": name, "session": session})
            if parts == ["api", "sign-out"]:
                who = self._who()
                if who is None:
                    return None
                if who.session:
                    server.people.leave(who.session)
                return self._json(200, {"said": "signed out on this device"})
            # the owner's: /api/people/NAME/invite, /api/people/NAME/sign-out
            if self._owner() is None:
                return None
            name, act = parts[2], parts[3]
            try:
                if act == "invite":
                    link = server.people.invite(name, self._known(),
                                                server.home.config.door.owner)
                    url, reachable = invite_address(server.home.config, link)
                    return self._json(200, {"url": url, "reachable": reachable,
                                            "hours": INVITE_HOURS})
                gone = server.people.sign_out(name)
            except PeopleError as exc:
                return self._json(409, {"detail": str(exc)})
            return self._json(200, {"said": f"{name} signed out on {gone} "
                                            f"device{'s' if gone != 1 else ''}"})

        def _settings_get(self) -> None:
            from sarathi import editing
            from sarathi.config import ConfigError, load

            if self._owner() is None:
                return None
            try:
                config = load()
            except ConfigError as exc:
                return self._json(409, {"detail": str(exc)})
            return self._json(200, editing.snapshot(config, _strangers(config)))

        def _settings_post(self, parts: list[str]) -> None:
            """/api/settings/WHAT[/NAME]: one change, checked by the program
            whose file it is (editing.py)."""
            from sarathi import editing
            from sarathi.config import ConfigError, load

            if self._owner() is None:
                return None
            body = self._body()
            if body is None:
                return None
            what = parts[2] if len(parts) > 2 else ""
            name = urllib.parse.unquote(parts[3]) if len(parts) > 3 else ""
            restart, said = False, "Saved."
            try:
                config = load()
                if what == "image":
                    return self._json(200, {"said": server.home.rebuild()})
                if what == "apply":
                    server.home._restart()
                    return self._json(200, {"said": "Starting everything again with the "
                                                    "new settings: about a minute."})
                if what == "sarathi":
                    config = editing.sarathi_apply(body)
                    restart = True
                elif what == "phone":
                    said, restart = editing.phone_step(config, body)
                    config = load()
                elif what == "key":
                    editing.set_key(name, str(body.get("value") or ""))
                    restart, said = True, f"{name} saved; it's never shown here again."
                elif what == "person":
                    if body.get("remove"):
                        if config.door and name == config.door.owner:
                            raise editing.EditError(400, "you can't remove yourself")
                        editing.dvara(config, ["person", name, "--remove"])
                        if server.people is not None:
                            try:
                                server.people.remove(name)
                            except PeopleError:
                                pass            # never signed in here
                        said = f"{name} removed, and signed out everywhere."
                    else:
                        fields = {k: v for k, v in body.items() if k != "remove"}
                        editing.dvara(config, ["person", name], fields)
                        said = f"{name} saved. Dvara uses it from their next message."
                elif what == "household":
                    # what everyone's agents know (dvara household.py)
                    editing.dvara(config, ["household"], {k: body[k] for k in
                                  ("add", "forget", "yes", "no") if k in body})
                    said = ("Kept for everyone's agents, from their next message."
                            if "add" in body or "yes" in body else "Done.")
                elif what == "rules":
                    rules = body.get("rules") if isinstance(body.get("rules"), list) else []
                    editing.dvara(config, ["rules"], rules)
                    said = "Rules saved. Dvara uses them from the next tool call."
                elif what == "agent":
                    if body.get("remove"):
                        out = editing.dvara(config, ["agent", name, "--remove"])
                        said = f"{name} removed (kept aside in {out.get('moved_to')})."
                    elif body.get("from_example"):
                        examples = editing.dvara_examples(config)
                        if examples is None:
                            raise editing.EditError(409, "dvara's example agents weren't "
                                                         "found")
                        editing.dvara(config, ["agent", name, "--from-example",
                                               str(body["from_example"]), "--examples",
                                               examples])
                        said = f"{name} added. Give people it under People."
                    else:
                        editing.dvara(config, ["agent", name],
                                      {"tables": body.get("tables") or {},
                                       "prompt": body.get("prompt")})
                        said = f"{name} saved. It's used from the next message."
                elif what == "tool" and body.get("remove"):
                    gone = editing.unmake_tool(config, name, str(body.get("person") or ""),
                                               str(body.get("skill") or ""))
                    said = (f"{gone} is no longer a tool; {body.get('skill')} is a recipe "
                            "again, its record kept.")
                elif what == "tool":
                    made = editing.make_tool(config, name, str(body.get("person") or ""),
                                             str(body.get("skill") or ""))
                    test = made.get("test") or {}
                    said = (f"{made.get('name')} is a tool now, for "
                            f"{body.get('person')} only. Its test passed."
                            if made.get("kept") else
                            f"Not made: its test didn't pass.\n{test.get('output', '')}")
                    return self._json(200, {"said": said, "made": made})
                elif what == "setu":
                    said = editing.setu_set(name, body.get("value"))
                elif what == "text":
                    text = body.get("text")
                    if not isinstance(text, str):
                        raise editing.EditError(400, "send the file as text")
                    if name == "sarathi":
                        config = editing.sarathi_text(text)
                        restart = True
                    elif name in ("actors", "policy"):
                        editing.dvara(config, ["text", name], text)
                    elif name in ("agent", "prompt"):
                        editing.dvara(config, ["text", name, "--agent",
                                               str(body.get("name") or "")], text)
                    elif name == "site":
                        editing.setu_site(str(body.get("name") or ""), text)
                    else:
                        raise editing.EditError(400, f"no file called {name!r} here")
                else:
                    return self._json(404, {"detail": "no such setting"})
            except editing.EditError as exc:
                return self._json(exc.status, {"detail": str(exc)})
            except (ConfigError, PeopleError) as exc:
                return self._json(400, {"detail": str(exc)})
            if what == "phone":
                with server.home._lock:
                    server.home.config = config
            if what in ("sarathi", "text") and restart:
                with server.home._lock:
                    server.home.config = config
                said = "Saved. Press Apply to start everything again with it."
            return self._json(200, {"said": said, "restart": restart})

        def do_POST(self) -> None:
            url = urlparse(self.path)
            parts = url.path.strip("/").split("/")
            if parts[:2] == ["api", "settings"]:
                return self._settings_post(parts)
            if parts in (["api", "sign-in"], ["api", "claim"], ["api", "sign-out"]) or \
                    (len(parts) == 4 and parts[:2] == ["api", "people"]
                     and parts[3] in ("invite", "sign-out")):
                return self._people_post(parts)
            if parts == ["api", "memory"]:
                if self._owner() is None:
                    return None
                body = self._body()
                if body is None:
                    return None
                code, words = server.home.switch(str(body.get("via")))
                return self._json(code, {"detail" if code >= 400 else "said": words})
            if parts == ["api", "doctor", "morning"]:
                if self._owner() is None:
                    return None
                code, words = server.home.morning()
                return self._json(code, {"detail" if code >= 400 else "said": words})
            if parts == ["api", "backup"]:
                offered = self.headers.get("Authorization", "")
                # the backup key makes one; anything else is the owner's
                if not hmac.compare_digest(offered.encode(),
                                           f"Bearer {server.backup_key}".encode()) \
                        and self._owner() is None:
                    return None
                return self._json(*server.home.backup_now())
            if parts == ["api", "backup", "nightly"]:
                if self._owner() is None:
                    return None
                code, words = server.home.backup_nightly()
                return self._json(code, {"detail" if code >= 400 else "said": words})
            if parts == ["api", "tests", "nightly"]:
                if self._owner() is None:
                    return None
                code, words = server.home.nightly()
                return self._json(code, {"detail" if code >= 400 else "said": words})
            if parts == ["api", "chat", "accounts-page"]:
                # their own Setu page, by the link /accounts page makes
                who = self._who()
                if who is None:
                    return None
                return self._chat(who, "POST", "/web/accounts-page", {})
            if parts == ["api", "chat", "declined"]:
                # one they turned down, offered again (not kept); only their own
                who = self._who()
                if who is None:
                    return None
                body = self._body(MAX_BODY)
                if body is None:
                    return None
                return self._chat(who, "POST", "/web/declined", {"undo": body.get("undo")})
            if parts[:3] == ["api", "chat", "chats"] and len(parts) == 5 \
                    and parts[4] == "delete":
                # deleted for good, by Dvara; only ever the person's own
                who = self._who()
                if who is None:
                    return None
                return self._chat(who, "DELETE",
                                  f"/web/chats/{urllib.parse.quote(parts[3], safe='')}")
            if parts[:2] != ["api", "chat"] or len(parts) not in (2, 4) or \
                    (len(parts) == 4 and parts[2] not in ("asks", "holds")):
                return self._json(405, {"detail": "this page only links, passes your "
                                                  "chat to Dvara, signs people in, and "
                                                  "switches memory"})
            who = self._who()
            if who is None:
                return None
            body = self._body(CHAT_BODY if len(parts) == 2 else MAX_BODY)
            if body is None:
                return None
            # only what Dvara's web channel takes, and never who: that's set here
            if len(parts) == 2:
                said = {"agent": body.get("agent"), "text": body.get("text")}
                if body.get("files"):
                    said["files"] = body.get("files")    # Dvara checks them
                return self._chat(who, "POST", "/web/message", said)
            if parts[2] == "asks":
                return self._chat(who, "POST",
                                  f"/web/asks/{urllib.parse.quote(parts[3])}",
                                  {"approve": body.get("approve")})
            return self._chat(who, "POST", f"/web/holds/{urllib.parse.quote(parts[3])}",
                              {"answers": body.get("answers")})

    return Handler
