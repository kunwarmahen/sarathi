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

Where things live:

    $SARATHI_CONFIG, else ~/.config/sarathi/   sarathi.toml, secrets.env
    $SARATHI_STATE,  else ~/.local/share/sarathi/
        work/                    where the pages start (Yantra's --cwd)
        run/<service>.json       what `up` started: pid, command, address
        logs/<service>.log       what it printed
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROVIDERS = ("ollama", "anthropic", "openai")

#: The key each cloud road reads (Yantra's own names).
KEY_NAMES = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}

DEFAULT_WEB_PORT = 8321
DEFAULT_CLOCK_PORT = 8780

KNOWN: dict[str, set[str]] = {
    "model": {"provider", "model", "base_url"},
    "web": {"port"},
    "clock": {"on", "port"},
}


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
    return Config(provider=provider, model=model.get("model") or None,
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


def save_secret(name: str, value: str) -> Path:
    secrets = read_secrets()
    secrets[name] = value
    body = "".join(f"{k}={v}\n" for k, v in secrets.items())
    write_private(secrets_path(), "# Read by `sarathi up`; readable only by you.\n" + body)
    return secrets_path()
