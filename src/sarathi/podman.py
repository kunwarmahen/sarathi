"""The same pieces, as containers that systemd keeps running.

``run.road = "podman"`` in sarathi.toml changes how ``sarathi up`` starts
the clock and the page. Instead of plain processes, it writes two Quadlet
units (``sarathi-clock.container``, ``sarathi-page.container``), and
systemd starts them, restarts them when they crash, and starts them
again after a reboot. ``sarathi image`` builds the image they run.

ONE IMAGE, EVERY PROGRAM. The pieces call each other as programs: the
page runs ``setu run`` and ``samay mcp``, and the clock runs ``yantra``.
So every container holds all of them (Containerfile), and the links
note 01 relies on work unchanged inside.

BUILT FROM WHAT IS COMMITTED. The image is built from ``git archive HEAD``
of each checkout, not from the working tree. Two builds of the same
commits are the same image, and a half-finished edit never ships by
accident. Uncommitted changes are named when the image is built, so a
"why isn't my fix in there?" has its answer on the screen.

THE DATA STAYS WHERE IT IS, AT THE SAME PATH. Each project keeps its own
files (Samay's ``~/.samay``, Setu's ``~/.local/state/setu``, Yantra's
memory), and those folders are mounted into both containers at the
paths they have on the host, with ``HOME`` set to match. Setu's records
hold absolute paths, and a schedule names its agent's folder, so the
same paths mean the same files mean the same answers. ``UserNS=keep-id``
runs the container as you, so files written inside are yours outside.

ONE CLOCK, SEEN FROM BOTH. Samay's clock holds a lock on a file in its
state folder for as long as it runs (Samay's note 05), and the page's
container mounts the same folder, so it sees the same lock. The two
containers share nothing else: either can crash and come back alone.
The page starts after the clock (``Wants=``, ``After=``), because the
page asks about the clock once, at start-up (note 02).

KEYS ONLY FROM SECRETS.ENV. A systemd unit does not see the shell that
ran ``sarathi up``, so a key exported there would silently not arrive.
The cloud road on Podman therefore reads keys from secrets.env only. The
unit files hold no key; they can be read and pasted like sarathi.toml.

EACH CONTAINER GETS ONLY ITS OWN SECRETS. ``up`` copies from secrets.env
into one file per unit (``units/<unit>.env`` beside it, readable by you
only, ``EnvironmentFile=``): the model's key to each, the door's own
token and the Telegram bot's token to the door, and the door's token to
the clock, which checks schedules against it. The page never holds the
bot's token.

THE DOOR, WHEN IT IS ON, is a third container (``sarathi-door``), after
the clock. All of them share one network (``sarathi.network``), where
each finds another by its name: the clock reaches the door at
``http://sarathi-door:8765``. Nothing else is shared; dvara's folders
(agents, actors, state) are mounted into the door alone.

OLLAMA IS ON THE HOST. ``localhost`` inside a container is the
container, so the local road's address becomes
``host.containers.internal``, which Podman points at the host. Ollama
has to listen on more than 127.0.0.1 for that to reach it
(``OLLAMA_HOST=0.0.0.0``).

YANTRA'S .env IS NOT IN THE IMAGE. The image is built from each
checkout's last commit, and ``.env`` is never committed, so a setting
that works in a terminal on this machine is absent in a container. What
the model needs comes from ``[model]`` in sarathi.toml instead:
provider, model, base_url and context_window, each as Yantra's own
variable. A 64k model with no ``context_window`` would still answer, but
Yantra would shorten every long chat at its 8192 default.

A BROWSER, AND THE WALL AROUND A CONNECTOR, ARE IN THE IMAGE. Google
Chrome at the path a desktop has it, so the profiles Setu recorded open
with the browser that wrote them; Xvfb for a site that wants a real
window; bubblewrap, so Setu's connectors run walled off here as on a
desktop (Containerfile). Each container gets a 1 GB /dev/shm, since
Chrome keeps its pages there and Podman's 64 MB is not enough for a
heavy one. HOME IS WRITABLE: inside a container it would be a folder
Podman made only to hold the mounts, owned by root, and Chrome dies at
start when it cannot make its crash reporter's folder under it ("the
browser did not answer Target.createTarget"). So HOME is a scratch
filesystem of your own, emptied at each start, with the data folders
mounted inside it as before. ``/proc`` is unmasked: Setu's wall gives each connector a
fresh ``/proc`` of its own, and the kernel refuses to mount one while
Podman hides parts of the container's. The container runs as you, so
what that shows is what your own account can read here anyway. Chrome
refuses a profile written by a newer version of
itself, so ``up`` says when this machine's Chrome is newer than the
image's: a rebuild picks up the newer one.

THE PHONE OVER WI-FI, with ``[phone] on``. A container can't reach a
phone on a USB cable without being handed the host's whole USB bus, so
it reaches it the way another computer would: over the network, at
``[phone] address`` (wireless debugging), with adb in the image. The
page and the door mount ``~/.android``, so the key this computer paired
with is theirs too (nothing is paired twice), and ``~/.sparsh``, so the
person's rules hold inside. ``SPARSH_CONNECT`` tells Sparsh the address,
and it reconnects whenever it looks for phones. The page gets ``--sparsh
auto:…`` (no phone answering at the start means no tools until the
person says to use one); the door gets ``--sparsh`` for the one person
its actors file marks ``phone = true``.

THE PAGES PEOPLE LOOK AT, with ``[pages] on`` (the default). Setu's page
(``sarathi-setu``) and, with the door on, Dvara's owner page
(``sarathi-owner``) are two more containers from the same image, each
published on 127.0.0.1 only. The owner page reaches the door by name on
the network and holds the door's token from its own env file, so your
answers from the browser get to the door; no other page holds it. The
HOME PAGE IS NOT A CONTAINER: Sarathi is not in the image, and from a
container 127.0.0.1 is that container, so it could not see the other
pages' ports. It is an ordinary user service (``sarathi-home.service``
in ``~/.config/systemd/user``) running this machine's ``sarathi home``,
started at login with the rest.

THE DOOR'S WINDOW IS PUBLISHED. With ``[door] window_host`` set, Setu
streams a sign-in window from the door's container: it listens on
every address inside (``SETU_WINDOW_HOST=0.0.0.0``), on a fixed port
(``window_port``, else 8790), published on ``window_host`` alone, and
the link says ``window_url`` or ``http://window_host:port`` -- never the
container's own address, which no phone can reach. SETU'S PAGE IS
PUBLISHED THERE TOO, when ``window_host`` is one address (not 0.0.0.0):
a person's link from ``/accounts page`` then opens on their phone.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sarathi import services
from sarathi.config import (
    BOT_TOKEN,
    DOOR_TOKEN,
    KEY_NAMES,
    Config,
    ConfigError,
    config_dir,
    read_secrets,
    secrets_path,
    state_dir,
    write_private,
)
from sarathi.services import alive, answers, door_problems, records, sarathi_program, work_dir
from sarathi.siblings import beside_dir

IMAGE = "localhost/sarathi:latest"
IN_IMAGE = "/usr/local/bin"
CHECKOUTS = ("yantra", "setu", "samay")
#: Built into the image when its checkout is there: the door needs dvara,
#: and the phone needs sparsh.
OPTIONAL_CHECKOUTS = ("dvara", "sparsh")
#: Ports inside the containers; the host ports come from sarathi.toml.
PAGE_PORT, CLOCK_PORT, DOOR_PORT = 8321, 8780, 8765
SETU_PAGE_PORT, OWNER_PAGE_PORT = 8775, 8785
#: The streamed sign-in window's port when sarathi.toml names none: a
#: container's port has to be known to be published.
WINDOW_PORT = 8790
#: The browser in the image, and the one a desktop's Setu records.
BROWSER = "/usr/bin/google-chrome"
UNITS = {"clock": "sarathi-clock", "door": "sarathi-door", "page": "sarathi-page",
         "setu": "sarathi-setu", "owner": "sarathi-owner", "home": "sarathi-home"}
#: Not a container: an ordinary user service (see the module docstring).
SERVICE_UNITS = ("home",)
#: The sarathi.toml key that moves each one's host port.
SETTINGS = services.PORT_SETTINGS
NETWORK = "sarathi"
READY_TIMEOUT = 90.0
HEADER = ("# Written by `sarathi up` from sarathi.toml, and rewritten whenever it\n"
          "# changes: edit sarathi.toml, not this file.\n")


def run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False, **kw)


# ---- the image ------------------------------------------------------------------


def checkouts(env: dict[str, str] | None = None) -> dict[str, Path]:
    root = beside_dir(env)
    found, missing = {}, []
    for name in OPTIONAL_CHECKOUTS:
        repo = root / name if root is not None else None
        if repo is not None and (repo / ".git").exists():
            found[name] = repo
    for name in CHECKOUTS:
        repo = root / name if root is not None else None
        if repo is None or not (repo / ".git").exists():
            missing.append(name)
        else:
            found[name] = repo
    if missing:
        raise ConfigError(f"the image is built from checkouts kept side by side; not found "
                          f"in {root}: {', '.join(missing)} (set SARATHI_SIBLINGS)")
    return found


def stage(into: Path, env: dict[str, str] | None = None) -> list[str]:
    """A clean build context: each checkout's HEAD, and the Containerfile."""
    lines = []
    for name, repo in checkouts(env).items():
        head = run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"]).stdout.strip()
        dirty = run(["git", "-C", str(repo), "status", "--porcelain"]).stdout.splitlines()
        with tempfile.TemporaryDirectory() as tmp:
            tar = Path(tmp) / "head.tar"
            done = run(["git", "-C", str(repo), "archive", "--format=tar", "-o", str(tar),
                        "HEAD"])
            if done.returncode != 0:
                raise ConfigError(f"git archive failed in {repo}: {done.stderr.strip()}")
            with tarfile.open(tar) as t:
                t.extractall(into / name, filter="data")
        note = f"{name:<7} {head}"
        if dirty:
            note += f"  ({len(dirty)} uncommitted change(s) left out: commit to include them)"
        lines.append(note)
    for name in OPTIONAL_CHECKOUTS:
        if not (into / name).exists():
            (into / name).mkdir(parents=True)    # empty: the image is built without it
            lines.append(f"{name:<7} not found beside the others: built without it")
    shutil.copy(Path(__file__).with_name("Containerfile"), into / "Containerfile")
    return lines


def platform() -> str:
    """This machine's own platform, named the way podman names one. Asked
    for on every build: an arm64 build on this machine had left arm64
    images under the base images' names, and a plain build then made an
    arm64 Sarathi that ran every service through qemu."""
    arch = {"x86_64": "amd64", "aarch64": "arm64", "armv7l": "arm/v7"}
    machine = os.uname().machine
    return f"linux/{arch.get(machine, machine)}"


def build(engine: str = "podman") -> int:
    with tempfile.TemporaryDirectory(prefix="sarathi-build-") as tmp:
        print("building from:")
        for line in stage(Path(tmp)):
            print(f"  {line}")
        print(flush=True)
        here = browser_version([BROWSER, "--version"]) if shutil.which(BROWSER) else None
        code = subprocess.run([engine, "build", "--platform", platform(), "-t", IMAGE,
                               "--build-arg",
                               f"HOST_BROWSER={'.'.join(map(str, here or ()))}", tmp],
                              check=False).returncode
    if code == 0:
        inside = run([engine, "run", "--rm", "--entrypoint", "/usr/local/bin/sarathi-browser",
                      IMAGE, "--version"]).stdout.strip()
        print(f"\nbrowser in the image: {inside or 'none found'}")
    return code


def image_id(of: str) -> str:
    """The image a container runs, or the image a tag names now; "" when
    there is no such thing."""
    kind = ["image", "inspect"] if of == IMAGE else ["container", "inspect"]
    return run(["podman", *kind, "--format", "{{.Id}}" if of == IMAGE else "{{.Image}}",
                of]).stdout.strip()


def image_exists() -> bool:
    return run(["podman", "image", "exists", IMAGE]).returncode == 0


# ---- the units ------------------------------------------------------------------


def data_dirs() -> list[Path]:
    """Every folder the pieces keep their files in -- mounted at the same path."""
    home = Path.home()
    xdg_state = Path(os.environ.get("XDG_STATE_HOME") or home / ".local" / "state")
    samay = os.environ.get("SAMAY_STATE", "").strip()
    return [Path(samay).expanduser() if samay else home / ".samay",
            xdg_state / "setu", xdg_state / "yantra", home / ".yantra", work_dir()]


def setu_files() -> list[Path]:
    """Files Setu's settings name outside its own folder, mounted read-only
    at the same path: today, the Google client file a Gmail sign-in uses.
    Setu keeps only its path, and a person usually leaves the file where
    Google's download put it -- ~/Downloads, the Desktop -- which no
    container sees. ONE FILE, NOT ITS FOLDER: the rest of a Desktop is
    none of a container's business."""
    named = os.environ.get("SETU_GOOGLE_CLIENT_FILE", "").strip()
    if not named:
        try:
            settings = json.loads((data_dirs()[1] / "config.json").read_text())
        except (OSError, ValueError):
            settings = {}
        named = str(settings.get("google_client_file") or "") if isinstance(
            settings, dict) else ""
    if not named:
        return []
    path = Path(named).expanduser()
    return [path] if path.is_file() else []


def from_container(url: str) -> str:
    """An address on this machine, as a container must say it."""
    parts = urlsplit(url)
    if parts.hostname in ("localhost", "127.0.0.1", "::1"):
        netloc = "host.containers.internal" + (f":{parts.port}" if parts.port else "")
        return urlunsplit(parts._replace(netloc=netloc))
    return url


def container_env(config: Config) -> dict[str, str]:
    prefix = config.provider.upper()
    env = {"HOME": str(Path.home()), "YANTRA_PROVIDER": config.provider,
           "SAMAY_YANTRA": f"{IN_IMAGE}/yantra", "SAMAY_YANTRA_HOME": str(work_dir())}
    if config.model:
        env[f"{prefix}_MODEL"] = config.model
    base = config.base_url or ("http://localhost:11434/v1" if config.provider == "ollama"
                               else None)
    if base:
        env[f"{prefix}_BASE_URL"] = from_container(base)
    if config.context_window:
        env[f"{prefix}_CONTEXT_WINDOW"] = str(config.context_window)
    return env


def phone_dirs(config: Config) -> list[Path]:
    """With [phone] on: adb's key folder, so a phone that trusts this
    computer trusts its containers (paired once, here), and Sparsh's, so
    your rules (``never``, ``ask``) hold inside too. Made if missing."""
    if config.phone is None:
        return []
    home = Path.home()
    sparsh = os.environ.get("SPARSH_STATE", "").strip()
    dirs = [home / ".android", Path(sparsh).expanduser() if sparsh else home / ".sparsh"]
    for d in dirs:
        d.mkdir(mode=0o700, parents=True, exist_ok=True)
    return dirs


def phone_env(config: Config) -> str:
    """The phone's Wi-Fi address, as Sparsh's ``SPARSH_CONNECT``."""
    phone = config.phone
    return (f"Environment=SPARSH_CONNECT={phone.address}\n"
            if phone is not None and phone.address else "")


def people_dir(config: Config) -> Path | None:
    """People's own Setu folders (the door's state/setu), for Setu's page:
    that folder alone is mounted into its container, not the door's
    whole state."""
    return config.door.path("state") / "setu" if config.door is not None else None


def door_dirs(config: Config) -> list[Path]:
    """dvara's folders, for the door's container alone."""
    door = config.door
    if door is None:
        return []
    return [door.path("root"), door.path("actors").parent, door.path("state")]


def env_file(unit: str) -> Path:
    return config_dir() / "units" / f"{unit}.env"


def unit_secrets(config: Config) -> dict[str, dict[str, str]]:
    """Unit -> the secrets it, and only it, gets."""
    held = read_secrets()
    key = KEY_NAMES.get(config.provider)
    model = {key: held[key]} if key and key in held else {}
    door = {} if config.door is None or DOOR_TOKEN not in held else \
        {"SAMAY_DVARA_TOKEN": held[DOOR_TOKEN]}
    out = {UNITS["page"]: dict(model), UNITS["clock"]: {**model, **door}}
    if config.door is not None:
        out[UNITS["door"]] = {**model, **door,
                              **{k: held[k] for k in (DOOR_TOKEN, BOT_TOKEN) if k in held}}
        if config.pages.on and DOOR_TOKEN in held:
            # the owner page passes your answers to the door: its token, nothing else
            out[UNITS["owner"]] = {DOOR_TOKEN: held[DOOR_TOKEN]}
    return out


def write_env_files(config: Config) -> None:
    folder = env_file("x").parent
    folder.mkdir(parents=True, exist_ok=True)
    folder.chmod(0o700)
    for unit, values in unit_secrets(config).items():
        body = "".join(f"{k}={v}\n" for k, v in values.items())
        write_private(env_file(unit), "# Written by `sarathi up` from secrets.env.\n" + body)


def _unit(description: str, name: str, exec_: str, publish: str, config: Config,
          extra_unit: str = "", extra_container: str = "",
          more_volumes: list[Path] | None = None) -> str:
    env = "".join(f"Environment={k}={v}\n" for k, v in container_env(config).items())
    volumes = "".join(f"Volume={d}:{d}:z\n" for d in data_dirs() + (more_volumes or []))
    volumes += "".join(f"Volume={f}:{f}:ro,z\n" for f in setu_files())
    secrets = f"EnvironmentFile={env_file(name)}\n" if unit_secrets(config).get(name) else ""
    return f"""{HEADER}
[Unit]
Description={description}
{extra_unit}
[Container]
Image={IMAGE}
ContainerName={name}
Network={NETWORK}.network
Exec={exec_}
PublishPort={publish}
UserNS=keep-id
RunInit=true
ShmSize=1g
Unmask=/proc/*
Tmpfs={Path.home()}:rw,mode=0700,U
WorkingDir={work_dir()}
{env}{secrets}{volumes}{extra_container}
[Service]
Restart=on-failure
SuccessExitStatus=143

[Install]
WantedBy=default.target
"""


def people_url(config: Config) -> str:
    """The door's SETU_PAGE_URL, for people's links (config.people_env)."""
    return "".join(f"Environment={k}={v}\n" for k, v in config.people_env().items())


def window(config: Config) -> tuple[str, str, str] | None:
    """(host it is published on, port, the link's base) for the door's
    streamed window, or None when sarathi.toml asks for none."""
    door = config.door
    if door is None or not door.window_env():
        return None
    host = door.window_host or "127.0.0.1"
    port = door.window_port or WINDOW_PORT
    return host, str(port), door.window_url or f"http://{host}:{port}"


def setu_window(config: Config) -> tuple[str, str, str] | None:
    """(host it is published on, port, the link's base) for Setu's page's
    own streamed window. In its container everyone is on "another
    device" -- you too, at this computer -- so Amazon from that page is
    always the streamed window: on the door's window address when it is
    one (people's phones), else on 127.0.0.1 (you alone). The port after
    the door's window, so both can be open at once. None behind
    ``window_url``: a public address that isn't Sarathi's to split."""
    door = config.door
    if not config.pages.on or (door is not None and door.window_url):
        return None
    host = config.people_host() or "127.0.0.1"
    port = str(((door.window_port if door else None) or WINDOW_PORT) + 1)
    shown = f"[{host}]" if ":" in host else host
    return host, port, f"http://{shown}:{port}"


def units(config: Config) -> dict[str, str]:
    """File name -> contents, for the Quadlet folder."""
    out = {}
    page_exec = (f"{IN_IMAGE}/yantra --web --host 0.0.0.0 --port {PAGE_PORT} "
                 f"--setu {IN_IMAGE}/setu ")
    page_unit = ""
    if config.clock_on:
        out[f"{UNITS['clock']}.container"] = _unit(
            "Sarathi: Samay's clock", UNITS["clock"],
            f"{IN_IMAGE}/samay serve --host 0.0.0.0 --port {CLOCK_PORT}",
            f"127.0.0.1:{config.clock_port}:{CLOCK_PORT}", config,
            # where a browser here reaches it, so Samay prints and reports
            # that, not the container's own bind (an older image ignores it)
            extra_container=f"Environment=SAMAY_PUBLIC_URL=http://127.0.0.1:"
                            f"{config.clock_port}/\n"
                            + (f"Environment=SAMAY_DVARA_URL=http://{UNITS['door']}:"
                               f"{DOOR_PORT}\n" if config.door else ""))
        page_exec += f"--samay {IN_IMAGE}/samay"
        page_unit = f"Wants={UNITS['clock']}.service\nAfter={UNITS['clock']}.service\n"
    else:
        page_exec += "--no-samay"
    if config.door is not None:
        door, after = config.door, ""
        door_exec = (f"{IN_IMAGE}/dvara --root {door.path('root')} --actors "
                     f"{door.path('actors')} --state {door.path('state')} --ask "
                     f"--provider {config.provider} "
                     + (f"--model {config.model} " if config.model else "")
                     + (f"--samay {IN_IMAGE}/samay " if config.clock_on else "--samay off ")
                     + (f"--sparsh {IN_IMAGE}/sparsh " if config.phone else "")
                     + f"serve --host 0.0.0.0 --port {DOOR_PORT}"
                     + (f" --telegram {door.telegram}" if door.telegram else ""))
        if config.clock_on:
            after = f"Wants={UNITS['clock']}.service\nAfter={UNITS['clock']}.service\n"
        shown = window(config)
        streamed = "" if shown is None else (
            f"PublishPort={shown[0]}:{shown[1]}:{shown[1]}\n"
            f"Environment=SETU_WINDOW_HOST=0.0.0.0\n"
            f"Environment=SETU_WINDOW_PORT={shown[1]}\n"
            f"Environment=SETU_WINDOW_URL={shown[2]}\n")
        out[f"{UNITS['door']}.container"] = _unit(
            "Sarathi: dvara, the door", UNITS["door"], door_exec,
            f"127.0.0.1:{door.port}:{DOOR_PORT}", config, after,
            extra_container=f"Environment=SAMAY_DVARA_URL=http://127.0.0.1:{DOOR_PORT}\n"
                            + streamed + people_url(config) + phone_env(config),
            more_volumes=door_dirs(config) + phone_dirs(config))
        page_unit += f"After={UNITS['door']}.service\n"
    if config.phone is not None:
        # auto: no phone answering at the start means no phone tools until
        # you press "use this phone" -- as on the process road
        page_exec += f" --sparsh auto:{IN_IMAGE}/sparsh"
    out[f"{UNITS['page']}.container"] = _unit(
        "Sarathi: Yantra's page", UNITS["page"], page_exec,
        f"127.0.0.1:{config.web_port}:{PAGE_PORT}", config, page_unit,
        extra_container=phone_env(config), more_volumes=phone_dirs(config))
    if config.pages.on:
        pages = config.pages
        folders = people_dir(config)
        people = f" --people {folders}" if folders else ""
        phones = config.people_host()
        out[f"{UNITS['setu']}.container"] = _unit(
            "Sarathi: Setu's page", UNITS["setu"],
            f"{IN_IMAGE}/setu serve --host 0.0.0.0 --port {SETU_PAGE_PORT} "
            f"--public-url http://127.0.0.1:{pages.setu_port}/{people}",
            f"127.0.0.1:{pages.setu_port}:{SETU_PAGE_PORT}", config,
            # people's links open on their phones (config.people_host)
            extra_container=(f"PublishPort={phones}:{pages.setu_port}:{SETU_PAGE_PORT}\n"
                             if phones else "") + setu_window_lines(config),
            more_volumes=[folders] if folders else None)
        if config.door is not None:
            door = config.door
            out[f"{UNITS['owner']}.container"] = _unit(
                "Sarathi: dvara's owner page", UNITS["owner"],
                f"{IN_IMAGE}/dvara --root {door.path('root')} --actors "
                f"{door.path('actors')} --state {door.path('state')} page --as {door.owner} "
                f"--host 0.0.0.0 --port {OWNER_PAGE_PORT}",
                f"127.0.0.1:{pages.door_port}:{OWNER_PAGE_PORT}", config,
                f"Wants={UNITS['door']}.service\nAfter={UNITS['door']}.service\n",
                extra_container=f"Environment=DVARA_URL=http://{UNITS['door']}:{DOOR_PORT}\n",
                more_volumes=door_dirs(config))
    out[f"{NETWORK}.network"] = (f"{HEADER}\n[Network]\nNetworkName={NETWORK}\n")
    return out


def setu_window_lines(config: Config) -> str:
    shown = setu_window(config)
    if shown is None:
        return ""
    host, port, url = shown
    return (f"PublishPort={host}:{port}:{port}\n"
            f"Environment=SETU_WINDOW_HOST=0.0.0.0\n"
            f"Environment=SETU_WINDOW_PORT={port}\n"
            f"Environment=SETU_WINDOW_URL={url}\n")


def home_unit(config: Config) -> str | None:
    """The home page's user service, or None when the pages are off."""
    if not config.pages.on:
        return None
    env = "".join(f"Environment={k}={v}\n" for k, v in (
        ("SARATHI_CONFIG", config_dir()), ("SARATHI_STATE", state_dir())))
    return f"""{HEADER}
[Unit]
Description=Sarathi: the home page, linking every program's page
After={UNITS['page']}.service

[Service]
ExecStart={sarathi_program()} home --port {config.pages.home_port}
{env}Restart=on-failure

[Install]
WantedBy=default.target
"""


def service_dir() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "systemd" / "user"


def unit_file(name: str) -> Path:
    unit = UNITS[name]
    return (service_dir() / f"{unit}.service" if name in SERVICE_UNITS
            else unit_dir() / f"{unit}.container")


def install_home(text: str | None) -> bool:
    """Write, or remove, the home page's service; True when it changed. It
    is enabled, so it starts at login as the Quadlet units do."""
    path = unit_file("home")
    if text is None:
        if not path.exists():
            return False
        run(["systemctl", "--user", "disable", path.name])
        path.unlink()
        return True
    if path.exists() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", path.name])
    return True


def keyed_address(config: Config, name: str, url: str) -> str:
    """A page's address with its key after '#', read where its program keeps
    it -- the line a person can open. The plain address when there is none."""
    from sarathi.home import TOKEN_FILE, pages

    token = None
    if name == "home":
        try:
            token = (state_dir() / TOKEN_FILE).read_text().strip() or None
        except OSError:
            token = None
    else:
        wanted = {"setu": "setu", "owner": "dvara"}.get(name)
        page = next((p for p in pages(config) if p.name == wanted), None)
        token = page.token() if page else None
    return f"{url}#token={token}" if token else url


def unit_dir() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "containers" / "systemd"


def install(wanted: dict[str, str]) -> set[str]:
    """Write the units that differ, remove ours that are no longer wanted;
    reload systemd if anything changed. Returns the files that changed."""
    folder = unit_dir()
    folder.mkdir(parents=True, exist_ok=True)
    changed: set[str] = set()
    for path in [folder / f"{name}.container" for name in UNITS.values()] + \
            [folder / f"{NETWORK}.network"]:
        text = wanted.get(path.name)
        if text is None:
            if path.exists():
                path.unlink()
                changed.add(path.name)
        elif not path.exists() or path.read_text() != text:
            path.write_text(text)
            changed.add(path.name)
    if changed:
        run(["systemctl", "--user", "daemon-reload"])
    return changed


# ---- up, down, status -----------------------------------------------------------


def active(unit: str) -> bool:
    return run(["systemctl", "--user", "is-active", "--quiet", f"{unit}.service"]
               ).returncode == 0


def speaks_http(url: str, timeout: float = 1.0) -> bool:
    """True once a server answers. A published port accepts connections
    before the program inside listens, so a bare connect proves nothing."""
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except (OSError, ValueError):
        return False


def clock_address(config: Config) -> str | None:
    """Samay's own 'page:' line, with this machine's address for the container's.
    Samay says it right itself once told (SAMAY_PUBLIC_URL, set on the
    unit); the rewrite stays for an image built before it could be told."""
    logs = run(["podman", "logs", UNITS["clock"]])
    for line in reversed((logs.stdout + logs.stderr).splitlines()):
        if line.startswith("page: "):
            parts = urlsplit(line[len("page: "):].strip())
            return urlunsplit(parts._replace(netloc=f"127.0.0.1:{config.clock_port}"))
    return None


def journal_tail(unit: str, lines: int = 5) -> list[str]:
    out = run(["journalctl", "--user", "-u", f"{unit}.service", "-n", str(lines),
               "--no-pager", "-o", "cat"]).stdout
    return [line for line in out.splitlines() if line.strip()]


def browser_version(argv: list[str]) -> tuple[int, ...] | None:
    """``Google Chrome 154.0.8037.97`` -> (154, 0, 8037, 97); None when
    there is no such browser or it says something else."""
    try:
        said = run(argv, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    for word in said.split():
        parts = word.split(".")
        if len(parts) >= 2 and all(p.isdigit() for p in parts):
            return tuple(int(p) for p in parts)
    return None


def browser_note() -> str | None:
    """A line when this machine's Chrome is newer than the image's: a
    profile signed in to here would be refused in there."""
    if shutil.which(BROWSER) is None:
        return None
    here = browser_version([BROWSER, "--version"])
    inside = browser_version(["podman", "run", "--rm", "--entrypoint", BROWSER, IMAGE,
                              "--version"])
    if here is None or inside is None or here <= inside:
        return None
    show = ".".join
    return (f"browser: this machine has Chrome {show(map(str, here))}, the image "
            f"{show(map(str, inside))}; a profile signed in to here won't open in "
            "there until `sarathi image` builds it again")


def preflight(config: Config) -> None:
    if not image_exists():
        raise ConfigError(f"no image yet ({IMAGE}): run `sarathi image` first")
    key = KEY_NAMES.get(config.provider)
    if key and key not in read_secrets():
        raise ConfigError(f"no {key} in {secrets_path()}: on the podman road keys come "
                          "only from there (a unit does not see your shell); "
                          "`sarathi init --force --podman` saves it")
    if config.door is not None:
        problems = door_problems(config, None)
        if run(["podman", "run", "--rm", "--entrypoint", "test", IMAGE, "-x",
                f"{IN_IMAGE}/dvara"]).returncode != 0:
            problems.insert(0, "the image has no dvara: put its checkout beside the "
                               "others and run `sarathi image` again")
        door = config.door
        if door.window_host in ("0.0.0.0", "::") and not door.window_url:
            problems.append(f"window_host = \"{door.window_host}\" listens everywhere, so "
                            "window_url must say the address a phone opens")
        if problems:
            raise ConfigError("the door cannot start: " + "; ".join(problems))
    ours = [name for name, r in records().items() if alive(r["pid"])]
    if ours:
        raise ConfigError(f"{', '.join(ours)} still running as plain processes: "
                          "`sarathi down` on the process road first")


def up(config: Config) -> tuple[list[str], bool]:
    preflight(config)
    for folder in data_dirs() + door_dirs(config) + [p for p in [people_dir(config)] if p]:
        folder.mkdir(parents=True, exist_ok=True)
    write_env_files(config)
    changed = install(units(config))
    if install_home(home_unit(config)):
        changed.add(unit_file("home").name)
    lines = ["units rewritten from sarathi.toml"] if changed else []
    newest = image_id(IMAGE)
    note = browser_note()
    if note:
        lines.append(note)
    if run(["podman", "network", "exists", NETWORK]).returncode != 0:
        # removed by hand, or by an older `down --remove` that left its
        # one-shot service "active": made again before anything joins it
        run(["systemctl", "--user", "restart", f"{NETWORK}-network.service"])
    if not config.clock_on:
        lines.append("clock  off in sarathi.toml")
    ok = True
    wanted = [("clock", config.clock_port)] if config.clock_on else []
    if config.door is not None:
        wanted.append(("door", config.door.port))
    wanted.append(("page", config.web_port))
    if config.pages.on:
        wanted.append(("setu", config.pages.setu_port))
        if config.door is not None:
            wanted.append(("owner", config.pages.door_port))
        wanted.append(("home", config.pages.home_port))
    for name, port in wanted:
        unit = UNITS[name]
        url = f"http://127.0.0.1:{port}/"
        if active(unit) and unit_file(name).name in changed:
            # a running container keeps the settings it started with: a
            # rewritten unit means nothing until it starts again
            run(["systemctl", "--user", "stop", f"{unit}.service"])
            lines.append(f"{name:<6} restarting with the new settings  (unit {unit})")
        elif (active(unit) and name not in SERVICE_UNITS and newest
              and image_id(unit) not in ("", newest)):
            # and the image it started from: `sarathi image` changes nothing
            # in a container already running
            run(["systemctl", "--user", "stop", f"{unit}.service"])
            lines.append(f"{name:<6} restarting with the new image  (unit {unit})")
        if active(unit):
            address = _address(config, name, url)
            lines.append(f"{name:<6} already running at {address}  (unit {unit})")
            continue
        taken = [(port, SETTINGS[name])] if answers(port) else []
        shown = window(config) if name == "door" else None
        if shown and answers(int(shown[1])):
            taken.append((int(shown[1]), "door.window_port"))
        shown = setu_window(config) if name == "setu" else None
        if shown and answers(int(shown[1])):
            taken.append((int(shown[1]), "door.window_port"))
        if taken:
            # a published port something else holds fails inside systemd,
            # restarted every few seconds, with the reason deep in a journal
            ok = False
            run(["systemctl", "--user", "stop", f"{unit}.service"])   # if it was looping
            lines += [f"{name:<6} not started: something else is listening on port "
                      f"{busy} (change {setting} in sarathi.toml)" for busy, setting in taken]
            continue
        started = run(["systemctl", "--user", "start", f"{unit}.service"])
        deadline = time.monotonic() + READY_TIMEOUT
        while started.returncode == 0 and time.monotonic() < deadline:
            if speaks_http(url):
                break
            if not active(unit):
                break
            time.sleep(0.5)
        if started.returncode == 0 and speaks_http(url):
            address = _address(config, name, url)
            lines.append(f"{name:<6} up at {address}  (unit {unit})")
            continue
        ok = False
        lines.append(f"{name:<6} did not come up (unit {unit}); the end of its journal:")
        lines += [f"         | {line}" for line in journal_tail(unit)]
    return lines, ok


def _address(config: Config, name: str, url: str) -> str:
    if name == "clock":
        return clock_address(config) or url
    if name in ("setu", "owner", "home"):
        return keyed_address(config, name, url)
    return url


def down(remove: bool = False) -> list[str]:
    """Stop the units. They stay installed -- and so start again at the
    next login, which is what they are for -- unless ``remove``."""
    lines = []
    for name in ("home", "owner", "setu", "page", "door", "clock"):
        unit = UNITS[name]
        if not unit_file(name).exists():
            continue
        if active(unit):
            run(["systemctl", "--user", "stop", f"{unit}.service"])
            lines.append(f"{name:<6} stopped  (unit {unit})")
        else:
            lines.append(f"{name:<6} was not running  (unit {unit})")
    if not lines:
        return ["no Sarathi units are installed"]
    if remove:
        # its service is a one-shot that stays "active (exited)": stopped
        # first, or the next `up` would find it active and never make the
        # network again
        run(["systemctl", "--user", "stop", f"{NETWORK}-network.service"])
        install({})
        install_home(None)
        run(["podman", "network", "rm", NETWORK])    # quadlet made it; nothing uses it now
        lines.append("units removed: nothing starts at login until the next `sarathi up`")
    else:
        lines.append("they start again at your next login "
                     "(`sarathi down --remove` to stop that too)")
    return lines


def running(config: Config) -> list[dict]:
    from sarathi.door import strangers

    out = []
    door_port = config.door.port if config.door else None
    pages = config.pages
    for name, port in (("clock", config.clock_port), ("door", door_port),
                       ("page", config.web_port), ("setu", pages.setu_port),
                       ("owner", pages.door_port), ("home", pages.home_port)):
        unit = UNITS[name]
        if port is None or not unit_file(name).exists():
            continue
        live = active(unit)
        url = f"http://127.0.0.1:{port}/"
        address = _address(config, name, url) if live else url
        row = {"name": name, "unit": unit, "alive": live, "address": address,
               "log": [] if live else journal_tail(unit)}
        if name == "door":
            row["strangers"] = strangers(journal_tail(unit, 400))
        out.append(row)
    return out
