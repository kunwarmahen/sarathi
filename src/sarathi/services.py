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
    prahari prahari serve --port <prahari.port> [--inlet-port <prahari.inlet_port>]
                   with PRAHARI_YANTRA=<the yantra Sarathi found>; then Yantra
                   gets --prahari <it>, and Dvara --prahari <it> [--prahari-for
                   <prahari.people>] (each watch looks as its person, through
                   Dvara)
    dvara   dvara --root/--actors/--state <dvara.*> --ask --samay <samay>
                  [--sparsh <sparsh>, with [phone] on]
                  serve --port <dvara.port> --web [--telegram <dvara.telegram>]
    vaani   vaani serve, with [vaani] on and Dvara on: VAANI_DVARA_URL and
                  VAANI_DVARA_TOKEN (the door's), VAANI_PORT=<vaani.port>,
                  VAANI_PAGE_PORT=<vaani.page_port> (on 0.0.0.0 with [house]), and
                  VAANI_HEAR_URL=<dvara.whisper> when that names one; the pucks
                  are ~/.config/vaani/vaani.toml's
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
    home    sarathi home --port <pages.home_port> [--also-host <dvara.window_host>,
                  when that is one address: people sign in from their phones]
    smritikosh  uvicorn smritikosh.api.main:app --port <smritikosh.port>, in its
                  checkout (its .env is there), after its database container
                  and `alembic upgrade head` (new code never meets old tables),
                  with [memory] via = "smritikosh"; then Yantra gets
                  --mcp-config <its server> and YANTRA_MEMORY, YANTRA_USER and
                  SMRITIKOSH_API_KEY, Samay the same for the runs it starts
                  (in SAMAY_YANTRA, and its env), and Dvara --memory <its server>, each
                  person's key read from Dvara's memory.json (smritikosh.py)
    smritikosh-ui  next start --hostname 127.0.0.1 --port <smritikosh.dashboard_port>,
                  Smritikosh's own dashboard, in its ui/, once built
    ntfy    ntfy serve --listen-http <dvara.window_host, else 127.0.0.1>:<dvara.ntfy_port>,
                  with [dvara] ntfy = true: a push server for notices on phones;
                  then Dvara gets --ntfy <its address> and DVARA_NTFY_CLICK, the
                  home page (dvara's push.py)

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
whether the clock is running. Prahari is told the same three things
(``PRAHARI_DVARA_URL``, ``PRAHARI_DVARA_TOKEN``, ``PRAHARI_DVARA_ACTOR``):
what a watch sees reaches you through the door, and it starts beside the
clock, before the door and the page that ask about it.

Both get the same model settings (``YANTRA_PROVIDER``, ``<PROVIDER>_MODEL``,
``<PROVIDER>_CONTEXT_WINDOW`` and so on, plus secrets.env), so a scheduled
run is answered by the same model as the page. A real environment variable outranks secrets.env, the
same rule Yantra applies to its own ``.env``.

A PIECE STARTED WITH OTHER WORDS STARTS AGAIN. A piece still running
from an earlier ``up`` is left alone -- unless what ``up`` would start it
with now differs (memory switched on, say): then it is stopped and
started with the new, as the podman road restarts a rewritten unit.

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
import shlex
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
    YANTRA_TOKEN,
    Config,
    ConfigError,
    read_secrets,
    state_dir,
    yantra_token,
)
from sarathi.siblings import Found, read_status

HOST = "127.0.0.1"
#: Where a piece listens with ``[house]``: every address, so this computer
#: (127.0.0.1, which the pieces use to reach each other) and the house's
#: other devices both reach it. One flag takes one address; the firewall
#: line ``up`` prints opens them to the house's network alone.
EVERYWHERE = "0.0.0.0"
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
    #: Where it starts (its own checkout, for a program that reads a .env
    #: there); None: Sarathi's work folder.
    cwd: Path | None = None
    #: Run just before it starts: a line to print, or a SetupError.
    prepare: Any = None
    #: Where it listens, when that is not this computer alone (ntfy, for phones).
    host: str = HOST

    @property
    def url(self) -> str:
        return f"http://{f'[{self.host}]' if ':' in self.host else self.host}:{self.port}/"


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
    # as SAMAY_DVARA_TOKEN), and your Smritikosh key only to what runs as
    # you (Yantra's page, Samay's runs): never to every piece that reads
    # secrets.env
    from sarathi.smritikosh import SECRETS as MEMORY_SECRETS

    secrets = {k: v for k, v in read_secrets().items()
               if k not in environ and k not in (DOOR_TOKEN, BOT_TOKEN, YANTRA_TOKEN,
                                                 *MEMORY_SECRETS)}
    env.update(secrets)
    key = KEY_NAMES.get(config.provider)
    if key and key not in environ and key not in env:
        raise ConfigError(f"no key for {config.provider}: run `sarathi init` "
                          f"or set {key} in your environment")
    return env


def plan(config: Config, found: dict[str, Found]) -> tuple[list[Service], list[str]]:
    """What `up` would start, and lines about what it will not."""
    yantra, setu, samay = found["yantra"], found["setu"], found["samay"]
    prahari = found.get("prahari")
    if yantra.program is None:
        raise ConfigError("yantra was not found, so there is nothing to start "
                          "(see `sarathi status`)")
    env = model_env(config)
    notes: list[str] = []
    listen = EVERYWHERE if config.house is not None else HOST
    clock_on = config.clock_on and samay.program is not None
    if config.clock_on and samay.program is None:
        notes.append(f"{'samay':<{WIDTH}} not started: samay was not found "
                     "(see `sarathi status`)")
    elif not config.clock_on:
        notes.append(f"{'samay':<{WIDTH}} off in sarathi.toml")
    watch_on = config.watch_on and prahari is not None and prahari.program is not None
    if config.watch_on and not watch_on and prahari is not None:
        notes.append(f"{'prahari':<{WIDTH}} not started: prahari was not found "
                     "(see `sarathi status`; it's optional)")
    elif not config.watch_on:
        notes.append(f"{'prahari':<{WIDTH}} off in sarathi.toml")

    # The clock starts first: the page asks Samay whether its clock runs
    # once, at start-up, and tells the model what it heard for the whole
    # session -- so a page started first would say "not running" forever.
    services = []
    memory = memory_service(config, notes)
    if memory is not None:
        services.append(memory)
        dash = dashboard_service(config, notes)
        if dash is not None:
            services.append(dash)
    push = ntfy_service(config, notes)
    if push is not None:
        services.append(push)
    door = door_service(config, found, env, clock_on, notes, ntfy=push is not None,
                        watch_on=watch_on)
    meet = door_env(config) if door is not None else {}
    memory_env: dict[str, str] = {}
    run_yantra = [yantra.program]
    if memory is not None:
        from sarathi import smritikosh

        memory_env = smritikosh.yantra_env()
        run_yantra += ["--mcp-config", str(memory_files(config)[0])]
    if clock_on:
        # a schedule made at this computer runs as you, so it remembers as
        # Yantra's page does: your Smritikosh account, with your key. And
        # one made there that works the phone gets it (after Dvara's check):
        # the phone's settings, and the Sparsh the page was handed.
        run_scheduled = list(run_yantra)
        if config.phone is not None and found.get("sparsh") is not None \
                and found["sparsh"].program is not None:
            run_scheduled += ["--sparsh", f"auto:{found['sparsh'].program}"]
        services.append(Service(
            "samay", "samay", [samay.program, "serve", "--host", listen,
                               "--port", str(config.clock_port)],
            config.clock_port,
            {**env, "SAMAY_YANTRA": shlex.join(run_scheduled),
             **({"SAMAY_PUBLIC_URL": config.link(config.clock_port)} if config.house else {}),
             **doctor_env(config),
             "SAMAY_YANTRA_HOME": str(work_dir()), **meet, **memory_env,
             **phone_env(config)},
            says_address="page: "))
    if watch_on:
        # every look is `yantra --call` with your accounts and memory, as the
        # page's own; what it sees reaches you through the door
        services.append(Service(
            "prahari", "prahari", [prahari.program, "serve", "--host", listen,
                                   "--port", str(config.watch_port),
                                   # the inlet alone, for the public road: on
                                   # 127.0.0.1 only, where Tailscale Funnel reaches it
                                   *(["--inlet-port", str(config.watch_inlet_port)]
                                     if config.watch_inlet_port else [])],
            config.watch_port,
            {**env, "PRAHARI_YANTRA": shlex.join(run_yantra),
             **({"PRAHARI_PUBLIC_URL": config.link(config.watch_port)} if config.house
                else {}),
             **({"PRAHARI_INLET_PUBLIC_URL": config.watch_public}
                if config.watch_public else {}),
             "PRAHARI_YANTRA_HOME": str(work_dir()), **watch_door_env(meet), **memory_env},
            says_address="page: "))
    if door is not None:
        services.append(door)
    voice = voice_service(config, found, door is not None, notes)
    if voice is not None:
        services.append(voice)
    page_argv = [yantra.program, "--web", "--host", listen, "--port", str(config.web_port)]
    if setu.program is not None:
        page_argv += ["--setu", setu.program]
    page_argv += ["--samay", samay.program] if clock_on else ["--no-samay"]
    if watch_on:
        page_argv += ["--prahari", prahari.program]
    elif not config.watch_on:
        page_argv += ["--no-prahari"]
    if found.get("sparsh") is not None and found["sparsh"].program is not None:
        # auto, not on: no phone at the start still means no phone tools
        # until the person says to use one (Yantra's phone panel).
        page_argv += ["--sparsh", f"auto:{found['sparsh'].program}"]
    page_argv += run_yantra[1:]
    # its token: the page wants it, and the home page's link carries it
    services.append(Service("yantra", "yantra", page_argv, config.web_port,
                            {**env, **phone_env(config), **memory_env,
                             # with [house] the page opens on every device: a
                             # sign-in started there streams its window
                             **yantra_window_env(config),
                             YANTRA_TOKEN: yantra_token()}))
    if config.pages.on:
        services += page_services(config, found, door is not None, notes)
    return services, notes


def memory_files(config: Config) -> tuple[Path, Path]:
    """The Smritikosh server, as Yantra and Dvara start it on this road."""
    from sarathi import smritikosh

    checkout = config.smritikosh.path()
    assert checkout is not None
    return smritikosh.mcp_files(config, command=str(smritikosh.program(checkout)),
                                url=config.smritikosh.url, suffix="")


def memory_service(config: Config, notes: list[str]) -> Service | None:
    """Smritikosh's server, with ``[memory] via = "smritikosh"``: started
    in its checkout, after its database container."""
    if not config.remembers_in_smritikosh:
        return None
    from sarathi import smritikosh

    kosh = config.smritikosh
    checkout = kosh.path()
    assert checkout is not None
    uvicorn = smritikosh.program(checkout, "uvicorn")
    if not uvicorn.is_file():
        notes.append(f"{'smritikosh':<{WIDTH}} not started: no server program in "
                     f"{checkout} (run `sarathi smritikosh`)")
        return None

    def database() -> str | None:
        db = smritikosh.Database.parse(smritikosh.read_dotenv(checkout / ".env").get(
            "POSTGRES_URL", "postgresql://smritikosh:smritikosh@localhost:5432/smritikosh"))
        said: list[str] = []
        smritikosh.start_database(kosh, db, said.append)
        # A pulled checkout may add a column the server's queries name:
        # its tables are brought up first, and only a step run is said.
        smritikosh.migrate(checkout, lambda line: said.append(line)
                           if "step(s) run" in line else None)
        said += smritikosh.start_extras(kosh)      # with [smritikosh] full
        return "\n".join(said) or None

    return Service("smritikosh", "smritikosh",
                   [str(uvicorn), "smritikosh.api.main:app", "--host", HOST,
                    "--port", str(kosh.port)],
                   kosh.port, {"BOOTSTRAP_ADMIN": "0"}, cwd=checkout, prepare=database)


def dashboard_service(config: Config, notes: list[str]) -> Service | None:
    """Smritikosh's own dashboard, after Smritikosh (smritikosh.py)."""
    from sarathi import smritikosh

    kosh = config.smritikosh
    argv = smritikosh.dashboard_argv(kosh, house=config.house is not None)
    if argv is None:
        if kosh.dashboard and smritikosh.dashboard(config) is not None:
            notes.append(f"{'smritikosh-ui':<{WIDTH}} not started: "
                         f"{smritikosh.unbuilt(kosh.path())} "
                         "(`sarathi smritikosh` builds it)")
        return None
    return Service("smritikosh-ui", "smritikosh", argv, kosh.dashboard_port,
                   smritikosh.dashboard_env(kosh, config.house.name if config.house
                                            else "localhost"),
                   cwd=smritikosh.ui_dir(kosh.path()))


#: Width of a piece's name in the lines `up`, `down` and `status` print.
WIDTH = 10
#: What each piece was called before it went by its project's name.
OLD_NAMES = {"clock": "samay", "door": "dvara", "page": "yantra", "owner": "dvara-page",
             "home": "sarathi"}

#: The sarathi.toml key that moves each piece's port, for "change it" lines.
PORT_SETTINGS = {"yantra": "yantra.port", "samay": "samay.port",
                 "prahari": "prahari.port", "dvara": "dvara.port",
                 "setu": "pages.setu_port", "dvara-page": "pages.dvara_port",
                 "sarathi": "pages.sarathi_port", "smritikosh": "smritikosh.port",
                 "smritikosh-db": "smritikosh.db_port",
                 "smritikosh-ui": "smritikosh.dashboard_port", "ntfy": "dvara.ntfy_port"}


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
        if (door_on or config.house is not None) and config.people_host():
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
             "page", "--as", door.owner,
             *(["--host", EVERYWHERE] if config.house is not None else []),
             "--port", str(pages.door_port)],
            pages.door_port,
            # the door's token stays server-side in the page, never in a browser
            {DOOR_TOKEN: token, "DVARA_URL": f"http://{HOST}:{door.port}"},
            says_address="  "))
    home = [sarathi_program(), "home", "--port", str(pages.home_port)]
    if (door_on or config.house is not None) and config.people_host():
        # the people in the house sign in from their phones (people.py)
        home += ["--also-host", config.people_host()]
    out.append(Service("sarathi", "sarathi", home, pages.home_port, says_address="  "))
    return out


def doctor_env(config: Config, host: str = HOST) -> dict[str, str]:
    """Where Samay's doctor and backup roads ask, and their keys (Sarathi's home page
    must be one `up` starts: it is where the doctor answers)."""
    if not config.pages.on:
        return {}
    from sarathi.home import backup_token, doctor_token

    return {"SAMAY_DOCTOR_URL": f"http://{host}:{config.pages.home_port}/api/doctor?news=1",
            "SAMAY_DOCTOR_TOKEN": doctor_token(),
            # the backup road makes the backup there too, by its own key
            "SAMAY_BACKUP_URL": f"http://{host}:{config.pages.home_port}/api/backup",
            "SAMAY_BACKUP_TOKEN": backup_token()}


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


def watching(config: Config, env: dict[str, str] | None = None) -> bool:
    """Prahari is on in sarathi.toml AND on this machine (found the way
    `status` finds it). It's optional: with no checkout and nothing on
    PATH, nothing about it is started, published or passed."""
    from sarathi.siblings import SIBLINGS, locate

    if not config.watch_on:
        return False
    return locate(next(s for s in SIBLINGS if s.name == "prahari"), env) is not None


def voicing(config: Config, env: dict[str, str] | None = None) -> bool:
    """Vaani is on in sarathi.toml, Dvara is on (it answers through it),
    and vaani is on this machine, found the way `status` finds it."""
    from sarathi.siblings import SIBLINGS, locate

    if not config.voice_on or config.door is None:
        return False
    return locate(next(s for s in SIBLINGS if s.name == "vaani"), env) is not None


def lan_address(config: Config) -> str:
    """This computer's address on the house's network, as a device there
    reaches it: ``[house] address`` when set, else the one the system
    would send from towards the internet (no packet is sent)."""
    if config.house is not None and config.house.address:
        return config.house.address
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("192.0.2.1", 9))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def voice_service(config: Config, found: dict[str, Found], door_on: bool,
                  notes: list[str]) -> Service | None:
    """Vaani, when ``[vaani] on``: its pucks are vaani.toml's; Sarathi says
    where Dvara is, with its token, and where Whisper is when ``[dvara]
    whisper`` names one. The answers it serves are for the pucks on the
    house's network, so it listens on every address."""
    if not config.voice_on:
        return None
    vaani = found.get("vaani")
    if vaani is None or vaani.program is None:
        notes.append(f"{'vaani':<{WIDTH}} not started: vaani was not found "
                     "(see `sarathi status`; it's optional)")
        return None
    if not door_on or config.door is None:
        notes.append(f"{'vaani':<{WIDTH}} not started: it answers through Dvara, "
                     "which is off (`sarathi dvara`)")
        return None
    meet = door_env(config)
    return Service("vaani", "vaani", [vaani.program, "serve"], config.voice_port,
                   {"VAANI_DVARA_URL": meet["SAMAY_DVARA_URL"],
                    "VAANI_DVARA_TOKEN": meet["SAMAY_DVARA_TOKEN"],
                    "VAANI_PORT": str(config.voice_port),
                    # its page: this computer alone, or the house with [house]
                    "VAANI_PAGE_PORT": str(config.voice_page_port),
                    "VAANI_PAGE_HOST": EVERYWHERE if config.house is not None else HOST,
                    **({"VAANI_HEAR_URL": config.door.whisper} if config.door.whisper
                       else {})})


def watch_door_env(meet: dict[str, str]) -> dict[str, str]:
    """The door's address, token and owner, in Prahari's own names: the
    same three the clock gets (``door_env``), so a watch's news reaches
    you as a schedule's answer does."""
    return {key.replace("SAMAY_", "PRAHARI_", 1): value for key, value in meet.items()}


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


def ntfy_program() -> str | None:
    return os.environ.get("SARATHI_NTFY") or shutil.which("ntfy")


def ntfy_service(config: Config, notes: list[str]) -> Service | None:
    """ntfy, for notices on phones, with [dvara] ntfy = true. Its own
    program on this road (the podman road brings its own image)."""
    door = config.door
    if door is None or door.ntfy_port is None:
        return None
    program = ntfy_program()
    if program is None:
        notes.append(f"{'ntfy':<{WIDTH}} not started: ntfy isn't installed here "
                     "(https://docs.ntfy.sh/install/), or set SARATHI_NTFY; the podman "
                     "road brings its own")
        return None
    cache = state_dir() / "ntfy"
    cache.mkdir(parents=True, exist_ok=True)
    return Service("ntfy", "ntfy",
                   [program, "serve", "--listen-http",
                    f"{config.ntfy_host()}:{door.ntfy_port}",
                    "--cache-file", str(cache / "cache.db"), "--cache-duration", "24h"],
                   door.ntfy_port, host=config.ntfy_host())


def ntfy_click(config: Config) -> dict[str, str]:
    """Where tapping a notice opens: the home page, on the address a phone
    reaches; nothing when there is no such address."""
    host = config.people_host()
    if host is None:
        return {}
    shown = f"[{host}]" if ":" in host else host
    return {"DVARA_NTFY_CLICK": f"http://{shown}:{config.pages.home_port}/"}


def door_service(config: Config, found: dict[str, Found], env: dict[str, str],
                 clock_on: bool, notes: list[str], *, ntfy: bool = False,
                 watch_on: bool = False) -> Service | None:
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
            "--state", str(door.path("state")), "--ask",
            # "don't ask" in the actors file means it ([dvara] yolo)
            *(["--yolo"] if door.yolo else []),
            # whose word keeps a fact for everyone's agents (dvara household.py)
            "--owner", door.owner]
    # the same model as the page, overruling a package that names another
    argv += ["--provider", config.provider] + (["--model", config.model] if config.model
                                               else [])
    argv += ["--samay", samay] if clock_on and samay else ["--samay", "off"]
    prahari = found["prahari"].program if "prahari" in found else None
    # each person's watch looks with their own accounts, through Dvara (its notes/56)
    if watch_on and prahari:
        argv += ["--prahari", prahari]
        argv += ["--prahari-for", ",".join(config.watch_people)] if config.watch_people \
            else []
    if config.remembers_in_smritikosh and config.smritikosh.path() is not None:
        # each person's turns, with each person's own key (memory.json)
        argv += ["--memory", str(memory_files(config)[1])]
    sparsh = found["sparsh"].program if "sparsh" in found else None
    if config.phone is not None:
        if sparsh is not None:
            # for the one person marked `phone = true` in the actors file
            argv += ["--sparsh", sparsh]
        else:
            notes.append(f"{'dvara':<{WIDTH}} no phone: sparsh was not found "
                         "(see `sarathi status`)")
    if ntfy and config.ntfy_url():
        # every person's notices, also to their own topic (dvara push.py)
        argv += ["--ntfy", config.ntfy_url()]
    # --web: the home page's chat, and every notice kept for it (dvara web.py)
    argv += ["serve", "--host", HOST, "--port", str(door.port), "--web"]
    if door.telegram:
        argv += ["--telegram", door.telegram]
    secrets = read_secrets()
    tokens = {k: secrets[k] for k in (DOOR_TOKEN, BOT_TOKEN) if k in secrets}
    return Service("dvara", "dvara", argv, door.port,
                   {**env, **tokens, **door_env(config),
                    **watch_door_env(door_env(config)), **door.window_env(),
                    # with [house], a sign-in window (Gmail's page too) on it
                    **(config.setu_window_env() if config.house is not None else {}),
                    **config.people_env(), **phone_env(config),
                    **({"DVARA_WHISPER": door.whisper} if door.whisper else {}),
                    **(ntfy_click(config) if ntfy else {})})


def yantra_window_env(config: Config) -> dict[str, str]:
    """Yantra's page's streamed window, on the plain-programs road: with
    ``[house]`` the page opens on every device, and a sign-in started
    there (a site added, an account connected) shows its window on the
    house address under the house's name, on any free port. Nothing
    without a house, or behind the door's ``window_url``."""
    host = config.people_host() if config.house is not None else None
    if not host or (config.door is not None and config.door.window_url):
        return {}
    return {"SETU_WINDOW_HOST": host, "SETU_WINDOW_NAME": config.house.name}


def phone_env(config: Config) -> dict[str, str]:
    """Sparsh's name for the phone's Wi-Fi address: it reconnects to it
    whenever it looks for phones, so a restart finds the phone again. An
    iPhone's WebDriverAgent, as ``SPARSH_WDA``. And ``[phone] awake``, its
    screen while an agent works it.

    Several phones by name (``[phone.NAME]``): ``SPARSH_PHONES``, every
    one as ``NAME=WHERE`` -- Sparsh reconnects a named Wi-Fi address by
    itself -- ``SPARSH_AWAKE`` one word per phone that says one, and
    ``SPARSH_SPARE`` the phones a watch may open a page on unasked."""
    phone = config.phone
    if phone is None:
        return {}
    if phone.named:
        env = {"SPARSH_PHONES": ",".join(f"{p.name}={p.where}" for p in phone.named)}
        awake = ",".join(f"{p.name}={p.awake}" for p in phone.named if p.awake)
        if awake:
            env["SPARSH_AWAKE"] = awake
        spare = ",".join(p.name for p in phone.named if p.spare)
        if spare:
            env["SPARSH_SPARE"] = spare
        return env
    pairs = (("SPARSH_CONNECT", phone.address), ("SPARSH_WDA", phone.wda),
             ("SPARSH_AWAKE", phone.awake))
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


def answers(port: int, timeout: float = 0.5, *, host: str = HOST) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
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


def _watch_elsewhere(prahari: Found | None) -> str | None:
    """The address of a Prahari Sarathi did not start, if one is watching."""
    if prahari is None or prahari.program is None:
        return None
    try:
        status = read_status(prahari.program, "prahari.status.v1")
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
        proc = subprocess.Popen(service.argv, cwd=service.cwd or work_dir(),
                                env={**os.environ, **service.env, "PYTHONUNBUFFERED": "1"},
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
        if answers(service.port, host=service.host):
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
        if record and alive(record["pid"]) and record.get("argv") != service.argv:
            # started with other words (memory switched, say): start again
            stop(service.name, record)
            lines.append(f"{service.name:<{WIDTH}} restarting with the new settings")
            record = None
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
        if service.name == "prahari":
            elsewhere = _watch_elsewhere(found.get("prahari"))
            if elsewhere:
                lines.append(f"{'prahari':<{WIDTH}} already watching at {elsewhere}, not "
                             "started by Sarathi: left alone")
                continue
        if answers(service.port, host=service.host):
            ok = False
            setting = PORT_SETTINGS[service.name]
            lines.append(f"{service.name:<{WIDTH}} not started: something else is listening on "
                         f"port {service.port} (change {setting} in sarathi.toml)")
            continue
        if service.prepare is not None:
            from sarathi.smritikosh import SetupError

            try:
                ready = service.prepare()
            except SetupError as exc:
                ok = False
                lines.append(f"{service.name:<{WIDTH}} not started: {exc}")
                continue
            if ready:
                lines.append(ready)
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
