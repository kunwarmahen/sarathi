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
DEFAULT_DOOR_PORT = 8770
#: ntfy, the push server Dvara's notices reach phones through (`dvara.ntfy`).
DEFAULT_NTFY_PORT = 8793
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
    "run": {"road"},
    "dvara": {"on", "port", "telegram", "root", "actors", "state", "window_host",
             "window_port", "window_url", "owner", "ntfy", "ntfy_port"},
    "pages": {"on", "sarathi_port", "setu_port", "dvara_port"},
    "phone": {"on", "address", "wda", "awake"},
    "memory": {"via"},
    "smritikosh": {"checkout", "port", "database", "volume", "db_port", "full", "neo4j",
                   "mongodb", "redis", "dashboard", "dashboard_port"},
}
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
    work it for the person marked ``phone = true`` in its actors file,
    and on the podman road the containers reach it -- over Wi-Fi, at
    ``address``, since a container can't reach a cable.

    ONE PHONE. An Android phone is ``address`` (or its cable); an iPhone
    is ``wda``, the address WebDriverAgent answers at. Sparsh takes an
    iPhone it is told about ahead of any Android it finds, so both at
    once would quietly mean the iPhone; the file holds one or the other."""

    #: ``192.168.1.23:41234``: the phone's wireless debugging address.
    #: None: a phone on a USB cable (the process road only).
    address: str | None = None
    #: ``http://127.0.0.1:8100``: an iPhone's WebDriverAgent, as Sparsh's
    #: ``SPARSH_WDA`` (started by Sparsh's scripts/start-wda-from-linux.sh).
    wda: str | None = None
    #: The screen while an agent works it, as Sparsh's ``SPARSH_AWAKE``
    #: (one of AWAKE). None: Sparsh's own default, kept on while working.
    awake: str | None = None


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

    @property
    def remembers_in_smritikosh(self) -> bool:
        return self.memory == "smritikosh"

    def people_host(self) -> str | None:
        """Where people's phones reach Setu's page, for the link ``/accounts
        page`` sends them: the door's window address, when it is ONE
        address (Tailscale, the home network) -- never every address
        (0.0.0.0) and never this computer alone. None: the page stays on
        127.0.0.1, and a person's link opens only here."""
        door = self.door
        if door is None or not self.pages.on:
            return None
        host = (door.window_host or "").strip()
        return host if host and host not in NOT_ONE_ADDRESS else None

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
        return {"SETU_WINDOW_HOST": host}

    def ntfy_host(self) -> str:
        """Where ntfy listens: the house address when there is one (a
        phone has to reach it), else this computer alone."""
        return self.people_host() or "127.0.0.1"

    def ntfy_url(self) -> str | None:
        """ntfy as a phone subscribes to it, or None with no ntfy."""
        if self.door is None or self.door.ntfy_port is None:
            return None
        host = self.ntfy_host()
        return f"http://{f'[{host}]' if ':' in host else host}:{self.door.ntfy_port}"

    def people_env(self) -> dict[str, str]:
        """The door's word for that page (``setu page-link`` reads it)."""
        host = self.people_host()
        if host is None:
            return {}
        shown = f"[{host}]" if ":" in host else host
        return {"SETU_PAGE_URL": f"http://{shown}:{self.pages.setu_port}/"}


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
        unknown = sorted(set(value) - KNOWN[table])
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
                if door_table.get("ntfy", False) else None) \
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
    if wda and address:
        raise ConfigError(f"{where}: phone.address (an Android) and phone.wda (an iPhone) "
                          "are two phones; Sarathi gives its agents one -- keep one of them")
    awake = phone_table.get("awake") or None
    if awake is not None and awake not in AWAKE:
        raise ConfigError(f"{where}: phone.awake is one of {', '.join(AWAKE)}, "
                          f"not {awake!r}")
    phone = Phone(address=address, wda=wda, awake=awake) \
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
    if via == "smritikosh" and smritikosh.checkout is None:
        raise ConfigError(f"{where}: memory.via = \"smritikosh\" but it isn't set up "
                          "yet: run `sarathi smritikosh`")
    return Config(provider=provider, road=road, door=door, pages=pages, phone=phone,
                  memory=via, smritikosh=smritikosh,
                  model=model.get("model") or None,
                  base_url=model.get("base_url") or None,
                  context_window=window,
                  web_port=_port(data.get("yantra", {}), "port", DEFAULT_WEB_PORT, "yantra"),
                  clock_on=clock.get("on", True),
                  clock_port=_port(clock, "port", DEFAULT_CLOCK_PORT, "samay"))


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

# How `sarathi up` starts them: process (plain programs on this machine)
# | podman (containers kept running by systemd; build with `sarathi image`).
[run]
road = "{config.road}"

# Each program's own page, started by `sarathi up`: Setu's (your accounts),
# Dvara's (when Dvara is on), and Sarathi's own, which links them all
# with Yantra's and Samay's -- bookmark that one.
[pages]
on = {"true" if config.pages.on else "false"}
sarathi_port = {config.pages.home_port}
setu_port = {config.pages.setu_port}
dvara_port = {config.pages.door_port}

{_render_door(config.door)}
{_render_phone(config.phone)}
{_render_memory(config)}"""


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


def _render_phone(phone: Phone | None) -> str:
    head = """# Your phone, through Sparsh: Dvara's agents may work it for the one
# person marked `phone = true` in its actors file. On the podman road the
# containers reach it over Wi-Fi at `address` (a container can't reach a
# cable): `sarathi phone pair ADDRESS CODE` once, then `sarathi phone ADDRESS`.
# An iPhone instead: `wda`, WebDriverAgent's address (`sarathi phone iphone`).
[phone]
"""
    if phone is None:
        return head + "on = false\n"
    address = f'address = "{phone.address}"' if phone.address else \
        '# address = "192.168.1.23:41234"   # its Wireless debugging address'
    wda = f'wda = "{phone.wda}"' if phone.wda else \
        '# wda = "http://127.0.0.1:8100"   # an iPhone instead: its WebDriverAgent'
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
{ntfy}"""


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


def save_secret(name: str, value: str) -> Path:
    secrets = read_secrets()
    secrets[name] = value
    body = "".join(f"{k}={v}\n" for k, v in secrets.items())
    write_private(secrets_path(), "# Read by `sarathi up`; readable only by you.\n" + body)
    return secrets_path()
