"""Start the pieces, stop them, and know which ones are ours.

``sarathi up`` starts two long-running things: Yantra's page and Samay's
clock, and a third with ``[dvara] on``: Dvara. Setu itself is not one of
them: it runs only when an agent asks it to. With ``[pages] on`` (the
default) it also starts the pages people look at: Setu's own page,
Dvara's owner page when the door is on, and the home page that links
them all.
Each piece is started with the flags and environment that
``sarathi.toml`` implies, and nothing is written into any sibling's own
files:

    yantra  yantra --web --host 127.0.0.1 --port <yantra.port>
                   --setu <the setu Sarathi found> --samay <the samay it found>
                   --sparsh auto:<the sparsh it found>  (no phone tools until
                   a phone is attached and you say to use it); with
                   [phone] address, SPARSH_CONNECT=<address> to both
    samay   samay serve --port <samay.port>
                   with SAMAY_YANTRA=<the yantra Sarathi found>
    dvara   dvara --root/--actors/--state <dvara.*> --ask --samay <samay>
                  [--sparsh <sparsh>, with [phone] on]
                  serve --port <dvara.port> --web [--telegram <dvara.telegram>]
    setu    setu serve --port <pages.setu_port>
                  [--people <dvara.state>/setu, with Dvara on: each person's
                  own folder, for the link /accounts page sends them;
                  --also-host <dvara.window_host>, when that is one
                  address, so the link opens on their phone -- and the
                  door gets SETU_PAGE_URL to build it]
    dvara-page  dvara --root/--actors/--state <dvara.*> [--samay <samay>] page
                  --as <dvara.owner> --port <pages.dvara_port>, with
                  DVARA_TOKEN and DVARA_URL: the door's own token and
                  address, so your answers reach it; Samay, for schedules
    home    sarathi home --port <pages.home_port>

THE DOOR AND THE CLOCK ARE TOLD ABOUT EACH OTHER. A schedule made in a
chat runs through the door as its person, and Samay checks every such
schedule against the door that made it. So both get the same
``SAMAY_DVARA_URL`` (the door's address) and ``SAMAY_DVARA_TOKEN`` (the
door's own token, from secrets.env): the wiring a person would
otherwise copy by hand into two places and get wrong in one. And
``SAMAY_DVARA_ACTOR``, the owner: a schedule made at this computer, on
Yantra's page, runs here but its answer still reaches you through the
door -- on Telegram, and on the home page's chat (``--web``). The order
is clock, door, page -- the door, like the page, asks once at start-up
whether the clock is running.

Both get the same model settings (``YANTRA_PROVIDER``, ``<PROVIDER>_MODEL``,
``<PROVIDER>_CONTEXT_WINDOW`` and so on, plus secrets.env), so a scheduled
run is answered by the same model as the page. A real environment variable outranks secrets.env, the
same rule Yantra applies to its own ``.env``.

ONE OF EACH, AND NEVER SOMEONE ELSE'S. Before starting anything, ``up``
asks whether it is already there. A piece Sarathi started and that is
still alive is left as it is. A clock started some other way (``samay
unit``, a terminal) is found through ``samay status`` and left alone.
Its schedules are the same file, so a second clock would only run every
job twice. A port something else already listens on is reported and not
fought over.

WHAT WAS STARTED IS WRITTEN DOWN. ``run/<name>.json`` holds the pid, the
command and the address. ``down`` stops only what is written there, and
``status`` reads it, so nothing is inferred from a process list. A
record whose process has gone is reported as stopped, with the last
lines of its log, rather than quietly removed.

A START IS NOT A SUCCESS UNTIL THE PORT ANSWERS. A page that crashed on
a missing extra or a taken port would otherwise read as "started".
``up`` waits for the address to accept a connection; if the process
exits first, it says so with the last lines of its log.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sarathi.config import (
    BOT_TOKEN,
    DOOR_TOKEN,
    KEY_NAMES,
    Config,
    ConfigError,
    read_secrets,
    state_dir,
)
from sarathi.siblings import Found, read_status

HOST = "127.0.0.1"
#: How long `up` waits for a started piece to answer on its port.
READY_TIMEOUT = 45.0
#: How long `down` waits after asking a piece to stop, before insisting.
STOP_TIMEOUT = 10.0
LOG_TAIL = 5

#: What this process started. Kept so the objects outlive the call: a
#: Popen dropped while its process still runs is reported by Python as a
#: leak, and here it runs on purpose (``down``, later, is what stops it).
_started: list[subprocess.Popen] = []


@dataclass
class Service:
    name: str                       # "yantra" | "samay" | "dvara" | ...
    sibling: str
    argv: list[str]
    port: int
    env: dict[str, str] = field(default_factory=dict)
    #: The start of the line in which the piece prints its own address --
    #: Samay's carries the page's token after '#', without which the page
    #: cannot be used. None: the plain address is the whole answer.
    says_address: str | None = None

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.port}/"


def model_env(config: Config, environ: dict[str, str] | None = None) -> dict[str, str]:
    """What tells Yantra which model answers -- in Yantra's own names."""
    environ = os.environ if environ is None else environ
    prefix = config.provider.upper()
    env = {"YANTRA_PROVIDER": config.provider}
    if config.model:
        env[f"{prefix}_MODEL"] = config.model
    if config.base_url:
        env[f"{prefix}_BASE_URL"] = config.base_url
    if config.context_window:
        env[f"{prefix}_CONTEXT_WINDOW"] = str(config.context_window)
    # the door's two tokens go to the door alone (and the clock its token,
    # as SAMAY_DVARA_TOKEN): never to every piece that reads secrets.env
    secrets = {k: v for k, v in read_secrets().items()
               if k not in environ and k not in (DOOR_TOKEN, BOT_TOKEN)}
    env.update(secrets)
    key = KEY_NAMES.get(config.provider)
    if key and key not in environ and key not in env:
        raise ConfigError(f"no key for {config.provider}: run `sarathi init` "
                          f"or set {key} in your environment")
    return env


def plan(config: Config, found: dict[str, Found]) -> tuple[list[Service], list[str]]:
    """What `up` would start, and lines about what it will not."""
    yantra, setu, samay = found["yantra"], found["setu"], found["samay"]
    if yantra.program is None:
        raise ConfigError("yantra was not found, so there is nothing to start "
                          "(see `sarathi status`)")
    env = model_env(config)
    notes: list[str] = []
    clock_on = config.clock_on and samay.program is not None
    if config.clock_on and samay.program is None:
        notes.append(f"{'samay':<{WIDTH}} not started: samay was not found "
                     "(see `sarathi status`)")
    elif not config.clock_on:
        notes.append(f"{'samay':<{WIDTH}} off in sarathi.toml")

    # The clock starts first: the page asks Samay whether its clock runs
    # once, at start-up, and tells the model what it heard for the whole
    # session -- so a page started first would say "not running" forever.
    services = []
    door = door_service(config, found, env, clock_on, notes)
    meet = door_env(config) if door is not None else {}
    if clock_on:
        services.append(Service(
            "samay", "samay", [samay.program, "serve", "--port", str(config.clock_port)],
            config.clock_port,
            {**env, "SAMAY_YANTRA": yantra.program, "SAMAY_YANTRA_HOME": str(work_dir()),
             **meet},
            says_address="page: "))
    if door is not None:
        services.append(door)
    page_argv = [yantra.program, "--web", "--host", HOST, "--port", str(config.web_port)]
    if setu.program is not None:
        page_argv += ["--setu", setu.program]
    page_argv += ["--samay", samay.program] if clock_on else ["--no-samay"]
    if found.get("sparsh") is not None and found["sparsh"].program is not None:
        # auto, not on: no phone at the start still means no phone tools
        # until the person says to use one (Yantra's phone panel).
        page_argv += ["--sparsh", f"auto:{found['sparsh'].program}"]
    services.append(Service("yantra", "yantra", page_argv, config.web_port,
                            {**env, **phone_env(config)}))
    if config.pages.on:
        services += page_services(config, found, door is not None, notes)
    return services, notes


#: Width of a piece's name in the lines `up`, `down` and `status` print.
WIDTH = 10
#: What each piece was called before it went by its project's name.
OLD_NAMES = {"clock": "samay", "door": "dvara", "page": "yantra", "owner": "dvara-page",
             "home": "sarathi"}

#: The sarathi.toml key that moves each piece's port, for "change it" lines.
PORT_SETTINGS = {"yantra": "yantra.port", "samay": "samay.port", "dvara": "dvara.port",
                 "setu": "pages.setu_port", "dvara-page": "pages.dvara_port",
                 "sarathi": "pages.sarathi_port"}


def sarathi_program() -> str:
    """This Sarathi, as a program the home page can be started with."""
    beside = Path(sys.executable).parent / "sarathi"
    return str(beside) if beside.exists() else (shutil.which("sarathi") or "sarathi")


def page_services(config: Config, found: dict[str, Found], door_on: bool,
                  notes: list[str]) -> list[Service]:
    """Setu's page, Dvara's owner page and the home page. Each prints its
    address with its token on the line after the first, two spaces in."""
    pages, out = config.pages, []
    setu = found["setu"].program
    door = config.door
    if setu is not None:
        argv = [setu, "serve", "--port", str(pages.setu_port)]
        if door is not None and door_on:
            argv += ["--people", str(door.path("state") / "setu")]
            if config.people_host():
                # people's links open on their phones (config.people_host)
                argv += ["--also-host", config.people_host()]
        out.append(Service("setu", "setu", argv, pages.setu_port,
                           config.setu_window_env() if door_on else {},
                           says_address="  "))
    else:
        notes.append(f"{'setu':<{WIDTH}} page not started: setu was not found "
                     "(see `sarathi status`)")
    if door is not None and door_on:
        token = read_secrets().get(DOOR_TOKEN) or os.environ.get(DOOR_TOKEN, "")
        samay = found["samay"].program if "samay" in found else None
        out.append(Service(
            "dvara-page", "dvara",
            [str(found["dvara"].program), "--root", str(door.path("root")), "--actors",
             str(door.path("actors")), "--state", str(door.path("state")),
             *(["--samay", str(samay)] if samay else []),
             "page", "--as", door.owner, "--port", str(pages.door_port)],
            pages.door_port,
            # the door's token stays server-side in the page, never in a browser
            {DOOR_TOKEN: token, "DVARA_URL": f"http://{HOST}:{door.port}"},
            says_address="  "))
    out.append(Service("sarathi", "sarathi", [sarathi_program(), "home", "--port",
                                              str(pages.home_port)],
                       pages.home_port, says_address="  "))
    return out


def door_env(config: Config, at: str | None = None) -> dict[str, str]:
    """How the clock and the door find each other: the door's address and
    its token, the same in both."""
    token = read_secrets().get(DOOR_TOKEN) or os.environ.get(DOOR_TOKEN, "")
    if not token:
        raise ConfigError(f"dvara is on but has no {DOOR_TOKEN}: run `sarathi dvara`")
    assert config.door is not None
    # a schedule made at this computer (Yantra's page) is told to the owner
    return {"SAMAY_DVARA_URL": at or f"http://{HOST}:{config.door.port}",
            "SAMAY_DVARA_TOKEN": token, "SAMAY_DVARA_ACTOR": config.door.owner}


def door_problems(config: Config, found: dict[str, Found] | None) -> list[str]:
    """Why the door cannot start, in words -- before anything is started.
    ``found`` None: dvara is not looked for on this machine (it is in the
    image, on the podman road)."""
    door = config.door
    assert door is not None
    secrets = {**read_secrets(), **{k: v for k, v in os.environ.items()
                                    if k in (DOOR_TOKEN, BOT_TOKEN)}}
    problems = []
    if found is not None and found["dvara"].program is None:
        problems.append("dvara was not found (see `sarathi status`)")
    if not door.path("actors").is_file():
        problems.append(f"no actors file at {door.actors}: `sarathi dvara` writes a "
                        "starter one")
    if not door.path("root").is_dir():
        problems.append(f"no agents folder at {door.root}: `sarathi dvara` copies "
                        "dvara's examples there")
    if DOOR_TOKEN not in secrets:
        problems.append(f"no {DOOR_TOKEN} in secrets.env: run `sarathi dvara`")
    if door.telegram and BOT_TOKEN not in secrets:
        problems.append(f"dvara.telegram is set but there is no {BOT_TOKEN}: "
                        "run `sarathi dvara` to paste the bot's token")
    return problems


def door_service(config: Config, found: dict[str, Found], env: dict[str, str],
                 clock_on: bool, notes: list[str]) -> Service | None:
    door = config.door
    if door is None:
        return None
    problems = door_problems(config, found)
    if problems:
        notes.append(f"{'dvara':<{WIDTH}} not started: " + "; ".join(problems))
        return None
    dvara, samay = found["dvara"].program, found["samay"].program
    assert dvara is not None
    argv = [dvara, "--root", str(door.path("root")), "--actors", str(door.path("actors")),
            "--state", str(door.path("state")), "--ask"]
    # the same model as the page, overruling a package that names another
    argv += ["--provider", config.provider] + (["--model", config.model] if config.model
                                               else [])
    argv += ["--samay", samay] if clock_on and samay else ["--samay", "off"]
    sparsh = found["sparsh"].program if "sparsh" in found else None
    if config.phone is not None:
        if sparsh is not None:
            # for the one person marked `phone = true` in the actors file
            argv += ["--sparsh", sparsh]
        else:
            notes.append(f"{'dvara':<{WIDTH}} no phone: sparsh was not found "
                         "(see `sarathi status`)")
    # --web: the home page's chat, and every notice kept for it (dvara web.py)
    argv += ["serve", "--host", HOST, "--port", str(door.port), "--web"]
    if door.telegram:
        argv += ["--telegram", door.telegram]
    secrets = read_secrets()
    tokens = {k: secrets[k] for k in (DOOR_TOKEN, BOT_TOKEN) if k in secrets}
    return Service("dvara", "dvara", argv, door.port,
                   {**env, **tokens, **door_env(config), **door.window_env(),
                    **config.people_env(), **phone_env(config)})


def phone_env(config: Config) -> dict[str, str]:
    """Sparsh's name for the phone's Wi-Fi address: it reconnects to it
    whenever it looks for phones, so a restart finds the phone again. And
    ``[phone] awake``, its screen while an agent works it."""
    phone = config.phone
    if phone is None:
        return {}
    pairs = (("SPARSH_CONNECT", phone.address), ("SPARSH_AWAKE", phone.awake))
    return {k: v for k, v in pairs if v}


def work_dir() -> Path:
    return state_dir() / "work"


def _record_path(name: str) -> Path:
    return state_dir() / "run" / f"{name}.json"


def log_path(name: str) -> Path:
    return state_dir() / "logs" / f"{name}.log"


def records() -> dict[str, dict[str, Any]]:
    folder = state_dir() / "run"
    _rename_old(folder)
    found = {}
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            found[path.stem] = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
    return found


def _rename_old(folder: Path) -> None:
    """A record and log written under a piece's old name (OLD_NAMES) take
    its new one, so `down` still stops what an older `up` started."""
    for old, new in OLD_NAMES.items():
        for path, renamed in ((folder / f"{old}.json", folder / f"{new}.json"),
                              (log_path(old), log_path(new))):
            if path.exists() and not renamed.exists():
                path.rename(renamed)


def alive(pid: int) -> bool:
    try:
        done, _ = os.waitpid(pid, os.WNOHANG)   # our own child: reap it if it ended
        if done == pid:
            return False
    except ChildProcessError:
        pass                                    # someone else's child: just look
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def answers(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=timeout):
            return True
    except OSError:
        return False


def log_tail(name: str, lines: int = LOG_TAIL) -> list[str]:
    try:
        text = log_path(name).read_text(errors="replace")
    except FileNotFoundError:
        return []
    return [line for line in text.splitlines() if line.strip()][-lines:]


def _clock_elsewhere(samay: Found) -> str | None:
    """The address of a clock Sarathi did not start, if one is running."""
    if samay.program is None:
        return None
    try:
        status = read_status(samay.program, "samay.status.v1")
    except ValueError:
        return None
    return (status.get("url") or "(no page)") if status.get("serving") else None


def start(service: Service, owner: bool = False) -> str:
    """Start one piece and wait for it to answer; one line saying how it went."""
    work_dir().mkdir(parents=True, exist_ok=True)
    for private in (log_path(service.name).parent, _record_path("x").parent):
        # Logs and records can hold a page's token: readable by their owner only.
        private.mkdir(parents=True, exist_ok=True)
        private.chmod(0o700)
    with open(log_path(service.name), "ab") as log:
        log.write(f"\n--- sarathi up {datetime.now(UTC).isoformat(timespec='seconds')}: "
                  f"{' '.join(service.argv)}\n".encode())
        log.flush()
        proc = subprocess.Popen(service.argv, cwd=work_dir(), env={**os.environ, **service.env,
                                                       "PYTHONUNBUFFERED": "1"},
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
    _started.append(proc)
    _record_path(service.name).write_text(json.dumps({
        "pid": proc.pid, "sibling": service.sibling, "argv": service.argv,
        "url": service.url, "port": service.port,
        "started": datetime.now(UTC).isoformat(timespec="seconds")}))
    deadline = time.monotonic() + READY_TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _record_path(service.name).unlink(missing_ok=True)
            tail = "\n".join(f"         | {line}" for line in log_tail(service.name))
            return (f"{service.name:<{WIDTH}} exited at once (code {proc.returncode}); "
                    f"its log, {log_path(service.name)}:\n{tail}")
        if answers(service.port):
            address = said_address(service) or service.url
            _remember(service.name, address=address)
            return (f"{service.name:<{WIDTH}} up {place(service.name, address, owner)}  "
                    f"(pid {proc.pid})")
        time.sleep(0.2)
    return (f"{service.name:<{WIDTH}} started (pid {proc.pid}) but not answering on "
            f"{service.url} after {READY_TIMEOUT:.0f}s; see {log_path(service.name)}")


def place(name: str, address: str, owner: bool) -> str:
    """Where a piece is, for `up` and `status`: ``at <address>`` -- except
    Dvara. ITS ADDRESS IS NOT A PAGE: it answers Samay and Dvara's own
    page, and a browser sent there gets ``{"detail":"Not Found"}``. So its
    line gives the port alone and points at the page that is yours."""
    if name != "dvara":
        return f"at {address}"
    port = urlsplit(address).port
    mine = "yours is dvara-page, below" if owner else "turn on [pages] for one"
    return f"on {port} (no page here; {mine})"


def said_address(service: Service, wait: float = 3.0) -> str | None:
    """The address the piece printed for itself in this start's log, if it does."""
    if service.says_address is None:
        return None
    deadline = time.monotonic() + wait
    while True:
        text = log_path(service.name).read_text(errors="replace")
        latest = text.rsplit("\n--- sarathi up ", 1)[-1]
        for line in latest.splitlines():
            if line.startswith(service.says_address):
                return line[len(service.says_address):].strip()
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.1)


def _remember(name: str, **more: Any) -> None:
    path = _record_path(name)
    path.write_text(json.dumps({**json.loads(path.read_text()), **more}))


def up(config: Config, found: dict[str, Found]) -> tuple[list[str], bool]:
    """Start what is not already running; lines to print, and whether all is well."""
    services, lines = plan(config, found)
    ok = True
    ours = records()
    owner = any(service.name == "dvara-page" for service in services)
    for service in services:
        record = ours.get(service.name)
        if record and alive(record["pid"]):
            address = record.get("address") or record["url"]
            lines.append(f"{service.name:<{WIDTH}} already running "
                         f"{place(service.name, address, owner)}  (pid {record['pid']})")
            continue
        if service.name == "samay":
            elsewhere = _clock_elsewhere(found["samay"])
            if elsewhere:
                lines.append(f"{'samay':<{WIDTH}} already running at {elsewhere}, "
                             "not started by "
                             "Sarathi: left alone")
                continue
        if answers(service.port):
            ok = False
            setting = PORT_SETTINGS[service.name]
            lines.append(f"{service.name:<{WIDTH}} not started: something else is listening on "
                         f"port {service.port} (change {setting} in sarathi.toml)")
            continue
        said = start(service, owner)
        ok = ok and said.startswith(f"{service.name:<{WIDTH}} up ")
        lines.append(said)
    return lines, ok


def stop(name: str, record: dict[str, Any]) -> str:
    pid = record["pid"]
    if not alive(pid):
        _record_path(name).unlink(missing_ok=True)
        return f"{name:<{WIDTH}} had already stopped"
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + STOP_TIMEOUT
    while time.monotonic() < deadline and alive(pid):
        time.sleep(0.1)
    how = "stopped"
    if alive(pid):
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        how = f"stopped (did not stop within {STOP_TIMEOUT:.0f}s, so it was killed)"
    _record_path(name).unlink(missing_ok=True)
    return f"{name:<{WIDTH}} {how}  (pid {pid})"


def down() -> list[str]:
    ours = records()
    if not ours:
        return ["nothing started by `sarathi up` is running"]
    return [stop(name, record) for name, record in ours.items()]


def running() -> list[dict[str, Any]]:
    """Each record, with whether its process is alive and what it last said."""
    from sarathi.door import strangers

    out = []
    for name, record in records().items():
        live = alive(record["pid"])
        row = {"name": name, **record, "alive": live, "log": [] if live else log_tail(name)}
        if name == "dvara":
            row["strangers"] = strangers(log_tail(name, 400))
        out.append(row)
    return out
