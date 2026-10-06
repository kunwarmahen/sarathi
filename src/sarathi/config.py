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

With ``[door] on = true``, ``up`` also starts dvara, the door your
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
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROVIDERS = ("ollama", "anthropic", "openai")

#: The key each cloud road reads (Yantra's own names).
KEY_NAMES = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}

DEFAULT_WEB_PORT = 8321
DEFAULT_CLOCK_PORT = 8780
DEFAULT_DOOR_PORT = 8770
#: Dvara's own defaults, used when [door] names no folder.
DOOR_ROOT, DOOR_ACTORS, DOOR_STATE = "~/dvara/agents", "~/dvara/actors.toml", "~/dvara/state"
#: The two secrets the door needs: dvara's own bearer token (Sarathi
#: makes one), and the bot's, from BotFather (the person pastes it).
DOOR_TOKEN, BOT_TOKEN = "DVARA_TOKEN", "TELEGRAM_TOKEN"

KNOWN: dict[str, set[str]] = {
    "model": {"provider", "model", "base_url"},
    "web": {"port"},
    "clock": {"on", "port"},
    "run": {"road"},
    "door": {"on", "port", "telegram", "root", "actors", "state", "window_host",
             "window_port", "window_url"},
}

#: How `up` starts things: plain processes, or Podman containers under
#: systemd (podman.py).
ROADS = ("process", "podman")


class ConfigError(ValueError):
    """The settings file is missing or says something Sarathi cannot use."""


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


@dataclass(frozen=True)
class Door:
    """Dvara, for other people and for your phone: ``[door]``."""

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


def parse(text: str, where: str = "sarathi.toml") -> Config:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{where} is not valid TOML: {exc}") from None
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
    clock = data.get("clock", {})
    if not isinstance(clock.get("on", True), bool):
        raise ConfigError(f"{where}: clock.on must be true or false")
    road = data.get("run", {}).get("road", "process")
    if road not in ROADS:
        raise ConfigError(f"{where}: run.road must be one of {', '.join(ROADS)}, not {road!r}")
    door_table = data.get("door", {})
    if not isinstance(door_table.get("on", False), bool):
        raise ConfigError(f"{where}: door.on must be true or false")
    for key in ("telegram", "root", "actors", "state", "window_host", "window_url"):
        if not isinstance(door_table.get(key, ""), str):
            raise ConfigError(f"{where}: door.{key} must be text")
    door = Door(port=_port(door_table, "port", DEFAULT_DOOR_PORT, "door"),
                telegram=door_table.get("telegram") or None,
                root=door_table.get("root") or DOOR_ROOT,
                actors=door_table.get("actors") or DOOR_ACTORS,
                state=door_table.get("state") or DOOR_STATE,
                window_host=door_table.get("window_host") or None,
                window_port=_port(door_table, "window_port", 0, "door") or None
                if "window_port" in door_table else None,
                window_url=door_table.get("window_url") or None) \
        if door_table.get("on", False) else None
    return Config(provider=provider, road=road, door=door, model=model.get("model") or None,
                  base_url=model.get("base_url") or None,
                  web_port=_port(data.get("web", {}), "port", DEFAULT_WEB_PORT, "web"),
                  clock_on=clock.get("on", True),
                  clock_port=_port(clock, "port", DEFAULT_CLOCK_PORT, "clock"))


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
    return f"""\
# Sarathi's settings. `sarathi up` reads this every time it starts things;
# edit it and run `sarathi down && sarathi up`. Keys never go here: a cloud
# key lives in secrets.env beside this file, readable only by you.

# What answers, on the page and in scheduled runs.
# provider: ollama (a model on this machine) | anthropic | openai
# model: unset means Yantra's default for that provider
# base_url: unset means the provider's usual address
[model]
provider = "{config.provider}"
{model}
{base}

# Yantra's page.
[web]
port = {config.web_port}

# Samay: things done later, on a schedule.
[clock]
on = {"true" if config.clock_on else "false"}
port = {config.clock_port}

# How `sarathi up` starts them: process (plain programs on this machine)
# | podman (containers kept running by systemd; build with `sarathi image`).
[run]
road = "{config.road}"

{_render_door(config.door)}"""


def _render_door(door: Door | None) -> str:
    if door is None:
        return """# dvara: your agents for other people, and for you on your phone.
# Off; `sarathi door` turns it on.
[door]
on = false
"""
    bot = (f'telegram = "{door.telegram}"' if door.telegram
           else '# telegram = "AGENT"   # the agent a Telegram bot answers as')
    folders = "".join(
        f'{key} = "{getattr(door, key)}"\n' if getattr(door, key) != default
        else f'# {key} = "{default}"\n'
        for key, default in (("root", DOOR_ROOT), ("actors", DOOR_ACTORS),
                             ("state", DOOR_STATE)))
    window = "".join(
        f"{key} = {json.dumps(value)}\n" if value else f"# {key} = ...\n"
        for key, value in (("window_host", door.window_host), ("window_port", door.window_port),
                           ("window_url", door.window_url)))
    return f"""# dvara: your agents for other people, and for you on your phone.
# Its tokens are in secrets.env; who it serves is in the actors file.
[door]
on = true
port = {door.port}
{bot}
{folders}
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
