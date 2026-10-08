"""`sarathi home`: one page that links to every program's own page.

Each program Sarathi starts has a page of its own: Yantra's, where you
talk to the agent; Samay's, for what runs later; Setu's, for your
accounts; Dvara's, for the door and the people behind it. Sparsh, when
it's here, gets a card too: your phone, watched from the phone panel on
Yantra's page. Each sits on
its own port, and the token-protected ones (Samay, Setu, Dvara) want the
address their program printed, token and all. Four addresses and three
keys is a lot to keep. ``sarathi home`` is one bookmark:

    GET /api/pieces     each page: what it is for, up or down, its link

LINKING ONLY. Sarathi holds no logic of its own, and this page doesn't
change that. Up or down is whether the page's port answers; the line
under it is the program's own ``status`` (the same one ``sarathi
status`` prints); and **Open** is that program's page. Nothing on it
starts, stops or changes anything. A page that isn't running says the
command that starts it.

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
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sarathi.config import Config, state_dir
from sarathi.services import HOST, answers
from sarathi.siblings import SIBLINGS, locate

DEFAULT_PORT = 8760
ENV_TOKEN = "SARATHI_HOME_TOKEN"
TOKEN_FILE = "home.token"
STATUS_EVERY = 30.0

STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/page.js": ("page.js", "text/javascript; charset=utf-8"),
          "/page.css": ("page.css", "text/css; charset=utf-8")}

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


class Home:
    """What ``/api/pieces`` answers, apart from HTTP."""

    def __init__(self, config: Config, said: Callable[[], dict[str, str]],
                 *, up: Callable[[int], bool] = answers, every: float = STATUS_EVERY) -> None:
        self.config = config
        self._said = said
        self._up = up
        self._every = every
        self._cache: tuple[float, dict[str, str]] | None = None
        self._lock = threading.Lock()

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


class HomeServer:
    def __init__(self, home: Home, token: str, *, host: str = HOST,
                 port: int = DEFAULT_PORT) -> None:
        self.home = home
        self.token = token
        self.httpd = ThreadingHTTPServer((host, port), _handler(self))
        self.httpd.daemon_threads = True
        self._thread: threading.Thread | None = None

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
        self.httpd.serve_forever()

    def start(self) -> None:
        self._thread = threading.Thread(target=self.httpd.serve_forever,
                                        name="sarathi-home", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread is not None:
            self._thread.join()


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

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path in STATIC:
                name, kind = STATIC[url.path]
                return self._send(200, files("sarathi").joinpath("static", name)
                                  .read_bytes(), kind)
            if url.path != "/api/pieces":
                return self._json(404, {"detail": "not found"})
            offered = self.headers.get("Authorization", "")
            if not hmac.compare_digest(offered.encode(), f"Bearer {server.token}".encode()):
                return self._json(401, {"detail": "missing or wrong token"})
            try:
                return self._json(200, {"pieces": server.home.pieces()})
            except Exception as exc:     # a bug is a 500 that says what, not a hang
                return self._json(500, {"detail": f"{type(exc).__name__}: {exc}"})

        def do_POST(self) -> None:
            self._json(405, {"detail": "this page only links"})

    return Handler
