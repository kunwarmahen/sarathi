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
             "window_port", "window_url", "owner"},
    "pages": {"on", "sarathi_port", "setu_port", "dvara_port"},
    "phone": {"on", "address"},
}

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
    ``address``, since a container can't reach a cable."""

    #: ``192.168.1.23:41234``: the phone's wireless debugging address.
    #: None: a phone on a USB cable (the process road only).
    address: str | None = None


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
    door = Door(port=_port(door_table, "port", DEFAULT_DOOR_PORT, "dvara"),
                telegram=door_table.get("telegram") or None,
                root=door_table.get("root") or DOOR_ROOT,
                actors=door_table.get("actors") or DOOR_ACTORS,
                state=door_table.get("state") or DOOR_STATE,
                window_host=door_table.get("window_host") or None,
                window_port=_port(door_table, "window_port", 0, "dvara") or None
                if "window_port" in door_table else None,
                window_url=door_table.get("window_url") or None,
                owner=door_table.get("owner") or "owner") \
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
    phone = Phone(address=address) if phone_table.get("on", False) else None
    return Config(provider=provider, road=road, door=door, pages=pages, phone=phone,
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
{_render_phone(config.phone)}"""


def _render_phone(phone: Phone | None) -> str:
    head = """# Your phone, through Sparsh: Dvara's agents may work it for the one
# person marked `phone = true` in its actors file. On the podman road the
# containers reach it over Wi-Fi at `address` (a container can't reach a
# cable): `sarathi phone pair ADDRESS CODE` once, then `sarathi phone ADDRESS`.
[phone]
"""
    if phone is None:
        return head + "on = false\n"
    address = f'address = "{phone.address}"' if phone.address else \
        '# address = "192.168.1.23:41234"   # its Wireless debugging address'
    return head + f"on = true\n{address}\n"


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
{window}"""


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
