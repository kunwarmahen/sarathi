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
it may need a password typed, and it can take a minute. Nothing else on
the page starts, stops or changes anything. The card also links to
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
    POST /api/chat                {"agent", "text"}
    POST /api/chat/asks/ID        {"approve": true|false}
    POST /api/chat/holds/ID       {"answers": {call id: true|false|reason}}
    GET  /api/chat/file?line=&n=  a file an answer carried
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
import secrets
import subprocess
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

from sarathi.config import DOOR_TOKEN, Config, read_secrets, render, settings_path, state_dir
from sarathi.people import INVITE_HOURS, People, PeopleError, actor_ids
from sarathi.services import HOST, answers
from sarathi.siblings import SIBLINGS, locate

DEFAULT_PORT = 8760
ENV_TOKEN = "SARATHI_HOME_TOKEN"
TOKEN_FILE = "home.token"
STATUS_EVERY = 30.0
#: The longest chat message passed on, in bytes.
MAX_BODY = 64 * 1024

STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/page.js": ("page.js", "text/javascript; charset=utf-8"),
          "/page.css": ("page.css", "text/css; charset=utf-8"),
          "/favicon.svg": ("favicon.svg", "image/svg+xml")}

POLICY = ("default-src 'none'; script-src 'self'; style-src 'self'; "
          "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
          "form-action 'none'; frame-ancestors 'none'")


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

    def token(self) -> str | None:
        if self.token_env and os.environ.get(self.token_env, "").strip():
            return os.environ[self.token_env].strip()
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
    found = [Page("yantra", "Yantra", "Talk to your agent.", config.web_port)]
    if config.clock_on:
        found.append(Page("samay", "Samay", "What runs later, and what each run said.",
                          config.clock_port, "SAMAY_TOKEN", samay_state / "serve.token"))
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
        and config.phone.address is not None
    if on_cable or over_wifi:
        # Sparsh has no page of its own: the phone is watched from the
        # panel on Yantra's page, so the card opens that page. On the
        # podman road only with a Wi-Fi address: a container can't reach
        # a phone on a USB cable.
        found.append(Page(
            "sparsh", "Your phone", "Your phone and what the agent did on it: the phone "
            "panel on Yantra's page.", config.web_port))
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
                 restart: Callable[[], None] = run_up) -> None:
        self.config = config
        self._said = said
        self._up = up
        self._every = every
        self._cache: tuple[float, dict[str, str]] | None = None
        self._memory = memory
        self._memory_cache: tuple[float, dict[str, Any]] | None = None
        self._restart = restart
        self._lock = threading.Lock()

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

    def pieces(self) -> list[dict[str, Any]]:
        lines = self.said()
        out = []
        for page in pages(self.config):
            token = page.token()
            url = f"http://{HOST}:{page.port}/"
            out.append({"name": page.name, "title": page.title, "purpose": page.purpose,
                        "up": self._up(page.port), "url": url,
                        "open": f"{url}#token={token}" if token else url,
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
    house address the door's window uses, when it is one; else this
    computer, and the owner is told so."""
    host = config.people_host()
    shown = f"[{host}]" if host and ":" in host else host
    base = f"http://{shown or HOST}:{config.pages.home_port}/"
    return f"{base}#invite={link}", host is not None


class HomeServer:
    def __init__(self, home: Home, token: str, *, host: str = HOST,
                 port: int = DEFAULT_PORT, chat: Chat | None = None,
                 people: People | None = None, also_host: str | None = None) -> None:
        self.home = home
        self.chat = chat
        self.token = token
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

        def _body(self) -> dict | None:
            try:
                size = int(self.headers.get("Content-Length") or 0)
                if size > MAX_BODY:
                    self._json(413, {"detail": "that message is too long"})
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

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path in STATIC:
                name, kind = STATIC[url.path]
                return self._send(200, files("sarathi").joinpath("static", name)
                                  .read_bytes(), kind)
            if url.path not in ("/api/pieces", "/api/chat", "/api/chat/file", "/api/me",
                                "/api/people", "/api/chat/push"):
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
                return self._json(200, {"pieces": server.home.pieces(),
                                        "memory": server.home.memory(),
                                        "chat": server.chat is not None,
                                        "people": server.people is not None
                                        and server.home.config.door is not None})
            except Exception as exc:     # a bug is a 500 that says what, not a hang
                return self._json(500, {"detail": f"{type(exc).__name__}: {exc}"})

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

        def do_POST(self) -> None:
            url = urlparse(self.path)
            parts = url.path.strip("/").split("/")
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
            if parts == ["api", "chat", "accounts-page"]:
                # their own Setu page, by the link /accounts page makes
                who = self._who()
                if who is None:
                    return None
                return self._chat(who, "POST", "/web/accounts-page", {})
            if parts[:2] != ["api", "chat"] or len(parts) not in (2, 4) or \
                    (len(parts) == 4 and parts[2] not in ("asks", "holds")):
                return self._json(405, {"detail": "this page only links, passes your "
                                                  "chat to Dvara, signs people in, and "
                                                  "switches memory"})
            who = self._who()
            if who is None:
                return None
            body = self._body()
            if body is None:
                return None
            # only what Dvara's web channel takes, and never who: that's set here
            if len(parts) == 2:
                return self._chat(who, "POST", "/web/message", {
                    "agent": body.get("agent"), "text": body.get("text")})
            if parts[2] == "asks":
                return self._chat(who, "POST",
                                  f"/web/asks/{urllib.parse.quote(parts[3])}",
                                  {"approve": body.get("approve")})
            return self._chat(who, "POST", f"/web/holds/{urllib.parse.quote(parts[3])}",
                              {"answers": body.get("answers")})

    return Handler
