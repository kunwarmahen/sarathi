"""One settings file, read the same way every time.

``sarathi.toml`` says the few things a person decides once: which model
answers, and where the pages listen. ``sarathi init`` writes it,
``sarathi up`` reads it on every start, and a person may edit it by hand
in between. The siblings never read it: ``up`` turns it into each one's
own flags and environment (services.py).

UNKNOWN KEYS ARE ERRORS. A misspelt ``[clok]`` that was quietly ignored
would leave the clock in a state nobody chose. Every table and key is
listed here, and anything else stops ``up`` with the name of what it did
not know.

NO KEY IN THE SETTINGS FILE. A cloud key goes in ``secrets.env`` beside
it, written readable by its owner only, so ``sarathi.toml`` can be shown
to someone or pasted into a question without leaking anything. A key
already in the environment is used as it is and never copied.

MEMORY IS YANTRA'S OWN FILE UNLESS YOU SAY OTHERWISE. ``[memory] via``
is ``local`` (the built-in file) or ``smritikosh`` (a memory server that
searches by meaning); ``sarathi smritikosh`` sets that server up and
switches to it, ``sarathi smritikosh --off`` switches back, and nothing
is deleted either way. Its key, and each Dvara person's, are Sarathi's
to hand out, never written here.

EVERY PAGE ON THE HOME NETWORK, BY ONE NAME: ``[house]``. Unset, each
piece listens on this computer alone (127.0.0.1), and only the few a
phone must reach -- the home page, Setu's page, the sign-in windows,
ntfy -- also on Dvara's ``window_host``. With ``[house] name`` (the name
the house knows this computer by: ``beast.local`` from Avahi, a router's
DNS name, a Tailscale name -- not ``.local`` for a phone on a VPN, which
only the Wi-Fi itself answers), every page you open in a browser is ALSO
published on the house address (``address``, or what the name finds);
what only the pieces talk to (Dvara's own port, Smritikosh's server and
databases) stays here. Every link a piece
hands out says the name: the home page's cards, a person's Setu link,
a sign-in window's link, ntfy's. Yantra's page then wants its token
(``YANTRA_WEB_TOKEN``, made once into secrets.env), and the home page's
link to it carries it.

With ``[dvara] on = true``, ``up`` also starts Dvara, the door your
agents live behind for other people and for you on your phone. Its two
tokens (dvara's own, and the Telegram bot's) are in secrets.env too.

Where things live:

    $SARATHI_CONFIG, else ~/.config/sarathi/   sarathi.toml, secrets.env
    $SARATHI_STATE,  else ~/.local/share/sarathi/
        work/                    where the pages start (Yantra's --cwd)
        run/<service>.json       what `up` started: pid, command, address
        logs/<service>.log       what it printed
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROVIDERS = ("ollama", "anthropic", "openai")

#: The key each cloud road reads (Yantra's own names).
KEY_NAMES = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}

DEFAULT_WEB_PORT = 8321
DEFAULT_CLOCK_PORT = 8780
#: Prahari: its page, its API and its inlet (what a phone app knocks on).
DEFAULT_WATCH_PORT = 8782
DEFAULT_DOOR_PORT = 8770
#: ntfy, the push server Dvara's notices reach phones through (`dvara.ntfy`).
DEFAULT_NTFY_PORT = 8793
#: The voices answers are read aloud in (Dvara's spoken.py): Piper's names,
#: from https://huggingface.co/rhasspy/piper-voices.
DEFAULT_VOICES = ("en_US-lessac-medium",)
VOICE_NAME = re.compile(r"^[a-z]{2,3}_[A-Z]{2}-[A-Za-z0-9_]+-(x_low|low|medium|high)$")
#: Each program's own page, and the home page linking them (`[pages]`).
DEFAULT_HOME_PORT, DEFAULT_SETU_PAGE_PORT, DEFAULT_DOOR_PAGE_PORT = 8760, 8775, 8785
#: Window addresses that are not one address a phone can be sent to.
NOT_ONE_ADDRESS = ("0.0.0.0", "::", "127.0.0.1", "localhost", "::1")
#: Dvara's own defaults, used when [dvara] names no folder.
DOOR_ROOT, DOOR_ACTORS, DOOR_STATE = "~/dvara/agents", "~/dvara/actors.toml", "~/dvara/state"
#: The two secrets the door needs: dvara's own bearer token (Sarathi
#: makes one), and the bot's, from BotFather (the person pastes it).
DOOR_TOKEN, BOT_TOKEN = "DVARA_TOKEN", "TELEGRAM_TOKEN"

KNOWN: dict[str, set[str]] = {
    "model": {"provider", "model", "base_url", "context_window"},
    "yantra": {"port"},
    "samay": {"on", "port"},
    "prahari": {"on", "port", "inlet_port", "public_url", "people"},
    "run": {"road"},
    "dvara": {"on", "port", "telegram", "root", "actors", "state", "window_host",
             "window_port", "window_url", "owner", "ntfy", "ntfy_port", "voices"},
    "pages": {"on", "sarathi_port", "setu_port", "dvara_port"},
    "phone": {"on", "address", "wda", "awake"},
    "memory": {"via"},
    "house": {"name", "address"},
    "backup": {"folder", "keep", "also"},
    "smritikosh": {"checkout", "port", "database", "volume", "db_port", "full", "neo4j",
                   "mongodb", "redis", "dashboard", "dashboard_port"},
}
#: Yantra's page's token (its gate.py), made once by `up` into secrets.env:
#: the page wants it, and the home page's link carries it.
YANTRA_TOKEN = "YANTRA_WEB_TOKEN"
#: Where Yantra (and Dvara's people) keep what they remember.
MEMORY_ROADS = ("local", "smritikosh")
DEFAULT_SMRITIKOSH_PORT, DEFAULT_DB_PORT = 8080, 5432
#: Smritikosh's own dashboard (its ui/, a Next.js app): built by `sarathi
#: smritikosh`, started by `up` after Smritikosh, linked from the home page.
DEFAULT_DASHBOARD_PORT = 3000
#: The database container `sarathi smritikosh` starts, or finds, and the
#: volume its data is in.
SMRITIKOSH_DB, SMRITIKOSH_VOLUME = "smritikosh-postgres", "smritikosh-pgdata"
#: Sparsh's words for the phone's screen while an agent works it
#: (``SPARSH_AWAKE``): kept on while working, never asleep, left alone.
AWAKE = ("working", "always", "off")

#: The names these had before each piece went by its project's name. A
#: file written then still reads; the next one Sarathi writes uses the new.
OLD_TABLES = {"web": "yantra", "clock": "samay", "door": "dvara"}
OLD_PAGE_KEYS = {"home_port": "sarathi_port", "door_port": "dvara_port"}

#: How `up` starts things: plain processes, or Podman containers under
#: systemd (podman.py).
ROADS = ("process", "podman")


class ConfigError(ValueError):
    """The settings file is missing or says something Sarathi cannot use."""


@dataclass(frozen=True)
class Pages:
    """The pages `up` starts besides Yantra's and Samay's: Setu's, Dvara's
    owner page (with the door on), and the home page linking them all."""

    on: bool = True
    home_port: int = DEFAULT_HOME_PORT
    setu_port: int = DEFAULT_SETU_PAGE_PORT
    door_port: int = DEFAULT_DOOR_PAGE_PORT


@dataclass(frozen=True)
class Phone:
    """Your phone, through Sparsh: ``[phone]``. On, the door's agents may
    work it for the person marked ``phone = true`` in its actors file
    (with named phones, each person's own ``phones = [...]``),
    and on the podman road the containers reach it: an Android on this
    computer's cable through this computer's adb (``sarathi-adb``,
    podman.py), or over Wi-Fi at ``address``.

    WHICHEVER IS PLUGGED IN. An Android phone is its cable or ``address``;
    an iPhone is ``wda``, the address WebDriverAgent answers at. Both may
    be written down: Sparsh uses the one that answers (its device.pick),
    so an iPhone swapped for an Android on the same cable, or back, needs
    no setting changed. Two that answer at once are said, not guessed."""

    #: ``192.168.1.23:41234``: the phone's wireless debugging address.
    #: None: a phone on a USB cable (the process road only).
    address: str | None = None
    #: ``http://127.0.0.1:8100``: an iPhone's WebDriverAgent, as Sparsh's
    #: ``SPARSH_WDA`` (started by ``sparsh iphone``: phone.py).
    wda: str | None = None
    #: The screen while an agent works it, as Sparsh's ``SPARSH_AWAKE``
    #: (one of AWAKE). None: Sparsh's own default, kept on while working.
    awake: str | None = None
    #: Several phones, each by a name (``[phone.nexus]``): then the three
    #: above are unset, and each named phone says its own.
    named: tuple[NamedPhone, ...] = ()

    @property
    def wdas(self) -> list[str]:
        """Every iPhone's WebDriverAgent address written down."""
        return [w for w in [self.wda, *(p.wda for p in self.named)] if w]

    @property
    def addresses(self) -> list[str]:
        """Every Android's Wi-Fi address written down."""
        return [a for a in [self.address, *(p.address for p in self.named)] if a]


@dataclass(frozen=True)
class NamedPhone:
    """One of several phones: ``[phone.NAME]``, as Sparsh's ``SPARSH_PHONES``
    names it. Exactly one of ``serial`` (an Android on this computer's
    cable), ``address`` (one over Wi-Fi) and ``wda`` (an iPhone). Whose
    it is, Dvara's actors file says (``phones = ["NAME"]``): this says
    what phones there are."""

    name: str
    serial: str | None = None
    address: str | None = None
    wda: str | None = None
    awake: str | None = None

    @property
    def where(self) -> str:
        return self.wda or self.address or self.serial or ""

    @property
    def kind(self) -> str:
        return "iPhone" if self.wda else "Android"


@dataclass(frozen=True)
class House:
    """Every server on the home network, by one name: ``[house]``."""

    #: The name links say: ``beast.local``, a router's DNS name.
    name: str
    #: The address everything is published on; None: what ``name`` finds.
    address: str | None = None

    def published_on(self) -> str | None:
        """The address, or the first IPv4 address the name finds here; None
        when it finds none (Avahi down, a name the router has forgotten)."""
        if self.address:
            return self.address
        import socket

        try:
            found = socket.getaddrinfo(self.name, None, socket.AF_INET)
        except OSError:
            return None
        return str(found[0][4][0]) if found else None


@dataclass(frozen=True)
class Backup:
    """``sarathi backup``: where its files go, how many are kept, and any
    place of yours beyond what the programs keep: ``[backup]``."""

    folder: str = "~/sarathi-backups"
    #: The newest this many are kept in ``folder``; 0 keeps every one.
    keep: int = 7
    #: Files or folders that are yours, not a program's (a signing key).
    also: tuple[str, ...] = ()

    def path(self) -> Path:
        return Path(self.folder).expanduser()


@dataclass(frozen=True)
class Smritikosh:
    """The memory server, as ``sarathi smritikosh`` set it up: ``[smritikosh]``."""

    #: Its checkout (the API, its .env, ``smritikosh-mcp``). None: not set
    #: up yet -- ``sarathi smritikosh`` finds or clones one.
    checkout: str | None = None
    port: int = DEFAULT_SMRITIKOSH_PORT
    #: Its PostgreSQL container, the volume that container keeps its data
    #: in, and the port it is published on here.
    database: str = SMRITIKOSH_DB
    volume: str = SMRITIKOSH_VOLUME
    db_port: int = DEFAULT_DB_PORT
    #: ``--full``: Neo4j, MongoDB and Redis too, each in the container
    #: named here (found by its address, or made, by ``sarathi smritikosh``).
    full: bool = False
    neo4j: str = "smritikosh-neo4j"
    mongodb: str = "smritikosh-mongo"
    redis: str = "smritikosh-redis"
    #: Start Smritikosh's own dashboard with it (`up`), and its port.
    dashboard: bool = True
    dashboard_port: int = DEFAULT_DASHBOARD_PORT

    def extras(self) -> dict[str, str]:
        """Store -> its container, with ``full`` on; empty without."""
        return {"neo4j": self.neo4j, "mongodb": self.mongodb, "redis": self.redis} \
            if self.full else {}

    def path(self) -> Path | None:
        return Path(self.checkout).expanduser() if self.checkout else None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


@dataclass(frozen=True)
class Config:
    provider: str
    model: str | None = None
    base_url: str | None = None
    web_port: int = DEFAULT_WEB_PORT
    clock_on: bool = True
    clock_port: int = DEFAULT_CLOCK_PORT
    road: str = "process"
    door: Door | None = None
    pages: Pages = Pages()
    phone: Phone | None = None
    #: How many tokens the model holds, as Yantra's <PROVIDER>_CONTEXT_WINDOW:
    #: when to shorten a long conversation. None: Yantra's default.
    context_window: int | None = None
    #: ``local`` (Yantra's built-in file) or ``smritikosh``.
    memory: str = "local"
    smritikosh: Smritikosh = Smritikosh()
    #: ``[house]``: every server on the home network too, links by name.
    house: House | None = None
    #: Prahari, the watch: on unless sarathi.toml says ``[prahari] on = false``.
    watch_on: bool = True
    watch_port: int = DEFAULT_WATCH_PORT
    #: Prahari's inlet ALONE (no page, no API) on its own port, for the
    #: public road; 0 for none.
    watch_inlet_port: int = 0
    #: Where the internet reaches that inlet (its Tailscale Funnel name).
    watch_public: str = ""
    #: Only these people get watches through Dvara; () for everyone.
    watch_people: tuple[str, ...] = ()
    backup: Backup = Backup()

    @property
    def remembers_in_smritikosh(self) -> bool:
        return self.memory == "smritikosh"

    def people_host(self) -> str | None:
        """Where people's phones reach Setu's page, for the link ``/accounts
        page`` sends them: the house's address (``[house]``), else the
        door's window address, when it is ONE address (Tailscale, the home
        network) -- never every address (0.0.0.0) and never this computer
        alone. None: the page stays on 127.0.0.1, and a person's link
        opens only here."""
        if self.house is not None:
            return self.house.published_on()
        door = self.door
        if door is None or not self.pages.on:
            return None
        host = (door.window_host or "").strip()
        return host if host and host not in NOT_ONE_ADDRESS else None

    def link_host(self) -> str | None:
        """The name or address a link says: the house's name, else the
        address phones reach (people_host)."""
        return self.house.name if self.house is not None else self.people_host()

    def link(self, port: int, path: str = "/") -> str:
        """``http://<link_host>:<port><path>``; this computer's 127.0.0.1
        when there is no house address."""
        host = self.link_host() or "127.0.0.1"
        return f"http://{f'[{host}]' if ':' in host else host}:{port}{path}"

    def setu_window_env(self) -> dict[str, str]:
        """Setu's page's own streamed window, on the plain-programs road: a
        person who connects Amazon from their page on a phone gets a
        window link on the address their phone reaches (any free port, as
        the door's). Nothing when that is not one address, or when the
        door's window is behind ``window_url`` -- a public address that
        isn't Sarathi's to split."""
        host = self.people_host()
        if host is None or self.door is None or self.door.window_url:
            return {}
        name = self.house.name if self.house is not None else None
        return {"SETU_WINDOW_HOST": host, **({"SETU_WINDOW_NAME": name} if name else {})}

    def ntfy_host(self) -> str:
        """Where ntfy listens: the house address when there is one (a
        phone has to reach it), else this computer alone."""
        return self.people_host() or "127.0.0.1"

    def ntfy_url(self) -> str | None:
        """ntfy as a phone subscribes to it, or None with no ntfy."""
        if self.door is None or self.door.ntfy_port is None:
            return None
        return self.link(self.door.ntfy_port, "")

    def people_env(self) -> dict[str, str]:
        """The door's word for that page (``setu page-link`` reads it)."""
        if self.people_host() is None:
            return {}
        return {"SETU_PAGE_URL": self.link(self.pages.setu_port)}


@dataclass(frozen=True)
class Door:
    """Dvara, for other people and for your phone: ``[dvara]``."""

    port: int = DEFAULT_DOOR_PORT
    #: The agent a Telegram bot answers as; None: no bot, HTTP only.
    telegram: str | None = None
    root: str = DOOR_ROOT
    actors: str = DOOR_ACTORS
    state: str = DOOR_STATE
    #: Where Setu's streamed sign-in window listens, for a site signed in
    #: to in a browser (Amazon) from someone's phone; None: at the machine.
    window_host: str | None = None
    window_port: int | None = None
    window_url: str | None = None
    #: Your id in the actors file: Dvara's page shows your words and your
    #: questions, and nobody else's.
    owner: str = "owner"
    #: ntfy's port, when the house runs one for notices on phones (dvara's
    #: push.py); None: no ntfy, notices wait on the page and go to Telegram.
    ntfy_port: int | None = None
    #: Piper's voices for answers read aloud: in the image, and fetched to
    #: this computer by `sarathi dvara --voices` (Dvara's spoken.py).
    voices: tuple[str, ...] = DEFAULT_VOICES

    def window_env(self) -> dict[str, str]:
        """Setu's own names for the window settings."""
        pairs = (("SETU_WINDOW_HOST", self.window_host),
                 ("SETU_WINDOW_PORT", str(self.window_port) if self.window_port else None),
                 ("SETU_WINDOW_URL", self.window_url))
        return {k: v for k, v in pairs if v}

    def path(self, which: str) -> Path:
        return Path(getattr(self, which)).expanduser()


def config_dir() -> Path:
    raw = os.environ.get("SARATHI_CONFIG", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / ".config" / "sarathi"


def state_dir() -> Path:
    raw = os.environ.get("SARATHI_STATE", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / ".local" / "share" / "sarathi"


def settings_path() -> Path:
    return config_dir() / "sarathi.toml"


def secrets_path() -> Path:
    return config_dir() / "secrets.env"


def _port(table: dict, key: str, default: int, where: str) -> int:
    value = table.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
        raise ConfigError(f"{where}.{key} must be a port number, not {value!r}")
    return value


def _rename_old(data: dict, where: str) -> None:
    """[clock] read as [samay], and so on (OLD_TABLES): both at once is
    refused, since one would be ignored."""
    for old, new in OLD_TABLES.items():
        if old in data:
            if new in data:
                raise ConfigError(f"{where}: both [{old}] and [{new}]; [{old}] is the old "
                                  f"name, so keep [{new}] alone")
            data[new] = data.pop(old)
    pages = data.get("pages")
    if isinstance(pages, dict):
        for old, new in OLD_PAGE_KEYS.items():
            if old in pages:
                if new in pages:
                    raise ConfigError(f"{where}: both pages.{old} and pages.{new}; keep "
                                      f"pages.{new} alone")
                pages[new] = pages.pop(old)


def parse(text: str, where: str = "sarathi.toml") -> Config:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{where} is not valid TOML: {exc}") from None
    _rename_old(data, where)
    for table, value in data.items():
        if table not in KNOWN or not isinstance(value, dict):
            raise ConfigError(f"{where}: unknown table [{table}] "
                              f"(known: {', '.join(f'[{k}]' for k in KNOWN)})")
        unknown = sorted(k for k in set(value) - KNOWN[table]
                         if not (table == "phone" and isinstance(value[k], dict)))
        if unknown:
            raise ConfigError(f"{where}: unknown key {table}.{unknown[0]} "
                              f"(known: {', '.join(sorted(KNOWN[table]))})")
    model = data.get("model", {})
    provider = model.get("provider")
    if provider not in PROVIDERS:
        raise ConfigError(f"{where}: model.provider must be one of "
                          f"{', '.join(PROVIDERS)}, not {provider!r}")
    window = model.get("context_window")
    if window is not None and (not isinstance(window, int) or isinstance(window, bool)
                               or window < 1024):
        raise ConfigError(f"{where}: model.context_window must be a number of tokens "
                          f"(1024 or more), not {window!r}")
    clock = data.get("samay", {})
    if not isinstance(clock.get("on", True), bool):
        raise ConfigError(f"{where}: samay.on must be true or false")
    watch = data.get("prahari", {})
    if not isinstance(watch.get("on", True), bool):
        raise ConfigError(f"{where}: prahari.on must be true or false")
    watch_inlet = watch.get("inlet_port", 0)
    if watch_inlet != 0:
        watch_inlet = _port(watch, "inlet_port", 0, "prahari")
    watch_public = watch.get("public_url", "")
    if not isinstance(watch_public, str) or (
            watch_public and not watch_public.startswith(("https://", "http://"))):
        raise ConfigError(f"{where}: prahari.public_url is the inlet's public address, "
                          f"like https://<computer>.<tailnet>.ts.net:8443 -- not "
                          f"{watch_public!r}")
    if watch_public and not watch_inlet:
        raise ConfigError(f"{where}: prahari.public_url needs prahari.inlet_port: the "
                          "public road reaches the inlet alone, on a port of its own")
    watch_people = watch.get("people", [])
    if not isinstance(watch_people, list) or not all(
            isinstance(n, str) and n.strip() for n in watch_people):
        raise ConfigError(f"{where}: prahari.people is a list of names from Dvara's "
                          "actors file (leave it out for everyone)")
    road = data.get("run", {}).get("road", "process")
    if road not in ROADS:
        raise ConfigError(f"{where}: run.road must be one of {', '.join(ROADS)}, not {road!r}")
    door_table = data.get("dvara", {})
    if not isinstance(door_table.get("on", False), bool):
        raise ConfigError(f"{where}: dvara.on must be true or false")
    for key in ("telegram", "root", "actors", "state", "window_host", "window_url", "owner"):
        if not isinstance(door_table.get(key, ""), str):
            raise ConfigError(f"{where}: dvara.{key} must be text")
    if not isinstance(door_table.get("ntfy", False), bool):
        raise ConfigError(f"{where}: dvara.ntfy must be true or false")
    voices = door_table.get("voices", list(DEFAULT_VOICES))
    if not isinstance(voices, list) or not all(isinstance(v, str) and VOICE_NAME.match(v)
                                               for v in voices):
        raise ConfigError(f'{where}: dvara.voices must be a list of Piper voice names, like '
                          f'["en_US-lessac-medium", "hi_IN-pratham-medium"]')
    door = Door(port=_port(door_table, "port", DEFAULT_DOOR_PORT, "dvara"),
                telegram=door_table.get("telegram") or None,
                root=door_table.get("root") or DOOR_ROOT,
                actors=door_table.get("actors") or DOOR_ACTORS,
                state=door_table.get("state") or DOOR_STATE,
                window_host=door_table.get("window_host") or None,
                window_port=_port(door_table, "window_port", 0, "dvara") or None
                if "window_port" in door_table else None,
                window_url=door_table.get("window_url") or None,
                owner=door_table.get("owner") or "owner",
                ntfy_port=_port(door_table, "ntfy_port", DEFAULT_NTFY_PORT, "dvara")
                if door_table.get("ntfy", False) else None,
                voices=tuple(dict.fromkeys(voices))) \
        if door_table.get("on", False) else None
    pages_table = data.get("pages", {})
    if not isinstance(pages_table.get("on", True), bool):
        raise ConfigError(f"{where}: pages.on must be true or false")
    pages = Pages(on=pages_table.get("on", True),
                  home_port=_port(pages_table, "sarathi_port", DEFAULT_HOME_PORT, "pages"),
                  setu_port=_port(pages_table, "setu_port", DEFAULT_SETU_PAGE_PORT, "pages"),
                  door_port=_port(pages_table, "dvara_port", DEFAULT_DOOR_PAGE_PORT, "pages"))
    phone_table = data.get("phone", {})
    if not isinstance(phone_table.get("on", False), bool):
        raise ConfigError(f"{where}: phone.on must be true or false")
    address = phone_table.get("address") or None
    if address is not None and (not isinstance(address, str)
                                or not re.fullmatch(r"[A-Za-z0-9.\-\[\]:]{1,80}:\d{1,5}",
                                                    address)):
        raise ConfigError(f"{where}: phone.address must be an address and port, like "
                          f"\"192.168.1.23:41234\", not {address!r}")
    wda = phone_table.get("wda") or None
    if wda is not None and (not isinstance(wda, str)
                            or not re.fullmatch(r"https?://[A-Za-z0-9.\-\[\]:]{1,80}:\d{1,5}/?",
                                                wda)):
        raise ConfigError(f"{where}: phone.wda must be WebDriverAgent's address, like "
                          f"\"http://127.0.0.1:8100\", not {wda!r}")
    awake = phone_table.get("awake") or None
    if awake is not None and awake not in AWAKE:
        raise ConfigError(f"{where}: phone.awake is one of {', '.join(AWAKE)}, "
                          f"not {awake!r}")
    named = tuple(_named_phone(n, body, where)
                  for n, body in phone_table.items() if isinstance(body, dict))
    if named and (address or wda or awake):
        raise ConfigError(f"{where}: [phone] has address, wda or awake beside named "
                          f"phones ([phone.{named[0].name}]); with names, each phone "
                          f"says its own")
    phone = Phone(address=address, wda=wda, awake=awake, named=named) \
        if phone_table.get("on", False) else None
    via = data.get("memory", {}).get("via", "local")
    if via not in MEMORY_ROADS:
        raise ConfigError(f"{where}: memory.via is one of {', '.join(MEMORY_ROADS)}, "
                          f"not {via!r}")
    kosh = data.get("smritikosh", {})
    for key in ("checkout", "database", "volume", "neo4j", "mongodb", "redis"):
        if not isinstance(kosh.get(key, ""), str):
            raise ConfigError(f"{where}: smritikosh.{key} must be text")
    if not isinstance(kosh.get("dashboard", True), bool):
        raise ConfigError(f"{where}: smritikosh.dashboard must be true or false")
    if not isinstance(kosh.get("full", False), bool):
        raise ConfigError(f"{where}: smritikosh.full must be true or false")
    smritikosh = Smritikosh(checkout=kosh.get("checkout") or None,
                            port=_port(kosh, "port", DEFAULT_SMRITIKOSH_PORT, "smritikosh"),
                            database=kosh.get("database") or SMRITIKOSH_DB,
                            volume=kosh.get("volume") or SMRITIKOSH_VOLUME,
                            db_port=_port(kosh, "db_port", DEFAULT_DB_PORT, "smritikosh"),
                            full=kosh.get("full", False),
                            dashboard=kosh.get("dashboard", True),
                            dashboard_port=_port(kosh, "dashboard_port",
                                                 DEFAULT_DASHBOARD_PORT, "smritikosh"),
                            **{k: kosh[k] for k in ("neo4j", "mongodb", "redis")
                               if kosh.get(k)})
    house_table = data.get("house")
    house = None
    if house_table is not None:
        name, at = house_table.get("name"), house_table.get("address") or None
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9.\-]{1,253}", name):
            raise ConfigError(f"{where}: house.name must be this computer's name on your "
                              f"network, like \"beast.local\", not {name!r}")
        if at is not None and (not isinstance(at, str) or at in NOT_ONE_ADDRESS
                               or not re.fullmatch(r"[0-9A-Fa-f.:]{2,45}", at)):
            raise ConfigError(f"{where}: house.address must be this computer's one address "
                              f"on your network, like \"192.168.1.44\", not {at!r}")
        house = House(name=name, address=at)
    kept = data.get("backup", {})
    if not isinstance(kept.get("folder", ""), str):
        raise ConfigError(f"{where}: backup.folder must be text, a folder's path")
    keep = kept.get("keep", Backup.keep)
    if isinstance(keep, bool) or not isinstance(keep, int) or keep < 0:
        raise ConfigError(f"{where}: backup.keep must be how many to keep (0: all), "
                          f"not {keep!r}")
    also = kept.get("also", [])
    if not isinstance(also, list) or not all(isinstance(a, str) and a.strip() for a in also):
        raise ConfigError(f"{where}: backup.also must be a list of paths, like "
                          "[\"~/keys\"]")
    backup = Backup(folder=kept.get("folder") or Backup.folder, keep=keep,
                    also=tuple(a.strip() for a in also))
    if via == "smritikosh" and smritikosh.checkout is None:
        raise ConfigError(f"{where}: memory.via = \"smritikosh\" but it isn't set up "
                          "yet: run `sarathi smritikosh`")
    return Config(provider=provider, road=road, door=door, pages=pages, phone=phone,
                  memory=via, smritikosh=smritikosh, house=house, backup=backup,
                  model=model.get("model") or None,
                  base_url=model.get("base_url") or None,
                  context_window=window,
                  web_port=_port(data.get("yantra", {}), "port", DEFAULT_WEB_PORT, "yantra"),
                  clock_on=clock.get("on", True),
                  clock_port=_port(clock, "port", DEFAULT_CLOCK_PORT, "samay"),
                  watch_on=watch.get("on", True),
                  watch_port=_port(watch, "port", DEFAULT_WATCH_PORT, "prahari"),
                  watch_inlet_port=watch_inlet, watch_public=watch_public.rstrip("/"),
                  watch_people=tuple(n.strip() for n in watch_people))


def _render_watch_extra(config: Config) -> str:
    lines = []
    if config.watch_inlet_port:
        lines.append(f"inlet_port = {config.watch_inlet_port}")
    if config.watch_public:
        lines.append(f'public_url = "{config.watch_public}"')
    if config.watch_people:
        lines.append("people = [" + ", ".join(f'"{n}"' for n in config.watch_people) + "]")
    return "\n".join(lines) + ("\n" if lines else "")


def load() -> Config:
    path = settings_path()
    try:
        text = path.read_text()
    except FileNotFoundError:
        raise ConfigError(f"no settings yet ({path}): run `sarathi init` first") from None
    return parse(text, str(path))


def render(config: Config) -> str:
    """The file `init` writes: every setting shown, with what it does."""
    model = f'model = "{config.model}"' if config.model else '# model = "..."'
    base = f'base_url = "{config.base_url}"' if config.base_url else '# base_url = "..."'
    window = (f"context_window = {config.context_window}" if config.context_window
              else "# context_window = 8192")
    return f"""\
# Sarathi's settings. `sarathi up` reads this every time it starts things;
# edit it and run `sarathi down && sarathi up`. Keys never go here: a cloud
# key lives in secrets.env beside this file, readable only by you.

# What answers, on the page and in scheduled runs.
# provider: ollama (a model on this machine) | anthropic | openai
# model: unset means Yantra's default for that provider
# base_url: unset means the provider's usual address
# context_window: the tokens your model holds (a 64k Ollama model: 64000);
#   unset means Yantra's default, which shortens a long chat early
[model]
provider = "{config.provider}"
{model}
{base}
{window}

# Yantra's page.
[yantra]
port = {config.web_port}

# Samay: things done later, on a schedule.
[samay]
on = {"true" if config.clock_on else "false"}
port = {config.clock_port}

# Prahari: tells your agent when something happens (a price, a mail, a
# phone's notification), looking with no model. Its page also has the
# inlet, where a phone app or a webhook knocks. Everyone in Dvara's
# actors file may make watches, each looking with their own accounts;
# people = ["you", "asha"] narrows that. inlet_port opens the inlet ALONE
# (no page, no API) for the public road, and public_url is where the
# internet reaches it (deploy/public-inlet-tailscale.sh in Prahari).
[prahari]
on = {"true" if config.watch_on else "false"}
port = {config.watch_port}
{_render_watch_extra(config)}
# How `sarathi up` starts them: process (plain programs on this machine)
# | podman (containers kept running by systemd; build with `sarathi image`).
[run]
road = "{config.road}"

# Each program's own page, started by `sarathi up`: Setu's (your accounts),
# Dvara's (when Dvara is on), and Sarathi's own, which links them all
# with Yantra's, Samay's and Prahari's -- bookmark that one.
[pages]
on = {"true" if config.pages.on else "false"}
sarathi_port = {config.pages.home_port}
setu_port = {config.pages.setu_port}
dvara_port = {config.pages.door_port}

{_render_house(config.house)}
{_render_backup(config.backup)}
{_render_door(config.door)}
{_render_phone(config.phone)}
{_render_memory(config)}"""


def _render_house(house: House | None) -> str:
    head = """# Every page on your home network too, by one name: Yantra's, Samay's,
# Prahari's (and its inlet, for a phone app), Dvara's, Setu's, this home
# page and Smritikosh's dashboard (what only
# the programs talk to stays here). name: what your other devices call this computer (Avahi's
# "<hostname>.local", or your router's name for it); every link says it.
# address: the address they are published on; unset, what the name finds.
# Yantra's page then wants its token; the home page's link carries it.
"""
    if house is None:
        return head + '# [house]\n# name = "beast.local"\n'
    address = f'address = "{house.address}"' if house.address else \
        '# address = "192.168.1.44"'
    return head + f'[house]\nname = "{house.name}"\n{address}\n'



def _render_backup(backup: Backup) -> str:
    also = "also = [" + ", ".join(f'"{a}"' for a in backup.also) + "]" if backup.also \
        else '# also = ["~/keys"]'
    return f"""# `sarathi backup`: one locked file of everything here. folder: where it
# is written (a USB disk's folder, too); keep: the newest this many are
# kept there, 0 for all; also: places of yours no program keeps.
[backup]
folder = "{backup.folder}"
keep = {backup.keep}
{also}
"""


def _render_memory(config: Config) -> str:
    kosh = config.smritikosh
    head = f"""# What your agents remember about you: local (Yantra's own file on this
# computer) or smritikosh (a memory server that finds a memory by meaning,
# not only by its words). `sarathi smritikosh` sets it up and switches;
# `sarathi smritikosh --off` switches back. Nothing is deleted either way.
[memory]
via = "{config.memory}"
"""
    if kosh.checkout is None:
        return head
    lines = [f'checkout = "{kosh.checkout}"']
    for key, value, default in (("port", kosh.port, DEFAULT_SMRITIKOSH_PORT),
                                ("database", kosh.database, SMRITIKOSH_DB),
                                ("volume", kosh.volume, SMRITIKOSH_VOLUME),
                                ("db_port", kosh.db_port, DEFAULT_DB_PORT),
                                ("dashboard_port", kosh.dashboard_port,
                                 DEFAULT_DASHBOARD_PORT)):
        shown = json.dumps(value)
        lines.append(f"{key} = {shown}" if value != default else f"# {key} = {shown}")
    lines.append(f"full = {'true' if kosh.full else 'false'}")
    lines.append(f"dashboard = {'true' if kosh.dashboard else 'false'}")
    if kosh.full:
        lines += [f"{key} = {json.dumps(getattr(kosh, key))}"
                  for key in ("neo4j", "mongodb", "redis")]
    return head + ("""
# Smritikosh, as `sarathi smritikosh` set it up: its checkout, the port its
# server listens on, and its database (a PostgreSQL container, the volume
# that holds its data, and the port it is published on here). full: Neo4j,
# MongoDB and Redis too (`sarathi smritikosh --full`), each in the container
# named below; without it, PostgreSQL alone, which is all Yantra uses.
# dashboard: start Smritikosh's own dashboard (its ui/) with it, on
# dashboard_port, 127.0.0.1 only; the home page links to it.
[smritikosh]
""" + "\n".join(lines) + "\n")


def with_phone(phone: Phone | None, named: NamedPhone) -> Phone:
    """``[phone]`` with ``named`` added, or put in place of the one by its
    name. An old unnamed phone can't stay beside it: naming it (the same
    address or wda) takes its place; another phone is refused until it is
    named, so nothing written down is dropped quietly."""
    if phone is not None and (phone.address or phone.wda):
        if named.where not in (phone.address, phone.wda):
            old = phone.wda or phone.address
            how = f"iphone {phone.wda}" if phone.wda else phone.address
            raise ConfigError(f"[phone] has a phone with no name yet ({old}): name it "
                              f"first -- sarathi phone add NAME {how}")
        phone = None
    kept = [p for p in (phone.named if phone else ()) if p.name != named.name]
    twin = next((p for p in kept if p.where == named.where), None)
    if twin is not None:
        # one phone, two names: two owners in Dvara for one set of messages
        raise ConfigError(f"{named.where} is already named {twin.name}: one phone, one "
                          f"name (sarathi phone remove {twin.name} first, to rename it)")
    return Phone(named=(*kept, named))


def without_phone(phone: Phone | None, name: str) -> Phone | None:
    """``[phone]`` without the one called ``name``; None when it was the last."""
    kept = tuple(p for p in (phone.named if phone else ()) if p.name != name)
    if phone is None or len(kept) == len(phone.named):
        raise ConfigError(f"no phone is called {name!r}"
                          + (f" ({', '.join(p.name for p in phone.named)})"
                             if phone and phone.named else ""))
    return Phone(named=kept) if kept else None


#: A phone's name, as Sparsh takes it (its phones.py).
PHONE_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
PHONE_KEYS = {"serial", "address", "wda", "awake"}


def _named_phone(name: str, body: dict, where: str) -> NamedPhone:
    if not PHONE_NAME.fullmatch(name):
        raise ConfigError(f"{where}: [phone.{name}] -- a phone's name is lower case "
                          f"letters, digits and dashes (nexus, asha-iphone)")
    unknown = sorted(set(body) - PHONE_KEYS)
    if unknown:
        raise ConfigError(f"{where}: unknown key phone.{name}.{unknown[0]} "
                          f"(known: {', '.join(sorted(PHONE_KEYS))})")
    given = [k for k in ("serial", "address", "wda") if body.get(k)]
    if len(given) != 1:
        raise ConfigError(f"{where}: [phone.{name}] needs exactly one of serial (a "
                          f"phone on this computer's cable), address (over Wi-Fi) or "
                          f"wda (an iPhone)")
    value = body[given[0]]
    checks = {"serial": r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}",
              "address": r"[A-Za-z0-9.\-\[\]:]{1,80}:\d{1,5}",
              "wda": r"https?://[A-Za-z0-9.\-\[\]:]{1,80}:\d{1,5}/?"}
    if not isinstance(value, str) or not re.fullmatch(checks[given[0]], value):
        raise ConfigError(f"{where}: phone.{name}.{given[0]} can't be {value!r}")
    awake = body.get("awake") or None
    if awake is not None and awake not in AWAKE:
        raise ConfigError(f"{where}: phone.{name}.awake is one of {', '.join(AWAKE)}, "
                          f"not {awake!r}")
    return NamedPhone(name=name, awake=awake, **{given[0]: value})


def _render_phone(phone: Phone | None) -> str:
    head = """# Your phone, through Sparsh: Dvara's agents may work it for the one
# person marked `phone = true` in its actors file. An Android on this
# computer's cable just works (the containers get this computer's adb);
# over Wi-Fi, `address` (`sarathi phone ADDRESS`). An iPhone: `wda`,
# WebDriverAgent's address (`sarathi phone iphone`). Both may be set: the
# one plugged in, the one that answers, is used. Several at once, each by
# a name (`sarathi phone add NAME ...`): a [phone.NAME] table for each,
# and Dvara's actors file says whose (phones = ["NAME"]).
[phone]
"""
    if phone is None:
        return head + "on = false\n"
    if phone.named:
        out = head + "on = true\n"
        for each in phone.named:
            key = "wda" if each.wda else "address" if each.address else "serial"
            out += f"\n[phone.{each.name}]\n{key} = \"{each.where}\"\n"
            if each.awake:
                out += f'awake = "{each.awake}"\n'
        return out
    address = f'address = "{phone.address}"' if phone.address else \
        '# address = "192.168.1.23:41234"   # its Wireless debugging address'
    wda = f'wda = "{phone.wda}"' if phone.wda else \
        '# wda = "http://127.0.0.1:8100"   # an iPhone: its WebDriverAgent'
    awake = f'awake = "{phone.awake}"' if phone.awake else \
        '# awake = "working"   # its screen while an agent works it: working, always, off'
    return head + f"on = true\n{address}\n{wda}\n{awake}\n"


def _render_door(door: Door | None) -> str:
    if door is None:
        return """# dvara: your agents for other people, and for you on your phone.
# Off; `sarathi dvara` turns it on.
[dvara]
on = false
"""
    bot = (f'telegram = "{door.telegram}"' if door.telegram
           else '# telegram = "AGENT"   # the agent a Telegram bot answers as')
    folders = "".join(
        f'{key} = "{getattr(door, key)}"\n' if getattr(door, key) != default
        else f'# {key} = "{default}"\n'
        for key, default in (("root", DOOR_ROOT), ("actors", DOOR_ACTORS),
                             ("state", DOOR_STATE)))
    owner = f'owner = "{door.owner}"' if door.owner != "owner" else '# owner = "owner"'
    window = "".join(
        f"{key} = {json.dumps(value)}\n" if value else f"# {key} = ...\n"
        for key, value in (("window_host", door.window_host), ("window_port", door.window_port),
                           ("window_url", door.window_url)))
    ntfy = (f"ntfy = true\nntfy_port = {door.ntfy_port}\n" if door.ntfy_port
            else "ntfy = false\n")
    return f"""# dvara: your agents for other people, and for you on your phone.
# Its tokens are in secrets.env; who it serves is in the actors file.
[dvara]
on = true
port = {door.port}
{bot}
{folders}{owner}   # your id in the actors file, for Dvara's page

# Signing in to Amazon or X from someone's phone: a browser window here,
# streamed to them. Where it listens (your home network's address, a
# Tailscale address, or 127.0.0.1 behind your own HTTPS with window_url).
# Unset: those sites are signed in to at this computer.
{window}
# ntfy: a push server here, so a schedule's answer (or a sign-in that ran
# out) shows on a phone with the ntfy app, while it can reach this house.
# `sarathi dvara --ntfy` turns it on.
{ntfy}
# Voices for answers read aloud, from https://huggingface.co/rhasspy/piper-voices:
# the image has these; `sarathi dvara --voices a,b` fetches them here too.
# An answer is read in a voice for its language when one is in this list.
voices = {json.dumps(list(door.voices))}
"""


def write_private(path: Path, text: str) -> None:
    """Write ``text`` so that only its owner can read it -- from the first byte."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(text)
    os.chmod(path, 0o600)


def read_secrets() -> dict[str, str]:
    """KEY=VALUE lines from secrets.env; '#' lines and blanks skipped."""
    try:
        lines = secrets_path().read_text().splitlines()
    except FileNotFoundError:
        return {}
    found = {}
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            found[key.strip()] = value.strip().strip("'\"")
    return found


def yantra_token() -> str:
    """Yantra's page's token: kept in secrets.env, made the first time. The
    page wants it (Yantra's gate.py) and the home page's link carries it."""
    import secrets as random

    held = read_secrets().get(YANTRA_TOKEN)
    if held:
        return held
    token = random.token_urlsafe(24)
    save_secret(YANTRA_TOKEN, token)
    return token


def save_secret(name: str, value: str) -> Path:
    secrets = read_secrets()
    secrets[name] = value
    body = "".join(f"{k}={v}\n" for k, v in secrets.items())
    write_private(secrets_path(), "# Read by `sarathi up`; readable only by you.\n" + body)
    return secrets_path()
