"""The same pieces, as containers that systemd keeps running.

``run.road = "podman"`` in sarathi.toml changes how ``sarathi up`` starts
Samay and Yantra. Instead of plain processes, it writes two Quadlet
units (``sarathi-samay.container``, ``sarathi-yantra.container``), and
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
"why isn't my fix in there?" has its answer on the screen. The image
keeps that answer too, as its ``sarathi.build`` label: each project's
commit, read back by ``sarathi version`` and the home page (version.py).

THE DATA STAYS WHERE IT IS, AT THE SAME PATH. Each project keeps its own
files (Samay's ``~/.samay``, Setu's ``~/.local/state/setu``, Yantra's
memory), and those folders are mounted into both containers at the
paths they have on the host, with ``HOME`` set to match. Setu's records
hold absolute paths, and a schedule names its agent's folder, so the
same paths mean the same files mean the same answers. ``UserNS=keep-id``
runs the container as you, so files written inside are yours outside.

ONE CLOCK, SEEN FROM BOTH. Samay's clock holds a lock on a file in its
state folder for as long as it runs (Samay's note 05), and the page's
container mounts the same folder, so it sees the same lock. Prahari's
watch does the same with ``~/.prahari``, mounted in every container. The two
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

THE DOOR, WHEN IT IS ON, is a third container (``sarathi-dvara``), after
the clock. All of them share one network (``sarathi.network``), where
each finds another by its name: the clock reaches the door at
``http://sarathi-dvara:8765``. Nothing else is shared; dvara's folders
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

THE PHONE, with ``[phone] on``. A container can't reach a phone on a
USB cable without being handed the host's whole USB bus, and the cable
belongs to one adb server anyway: this computer's. So that server is
lent to the containers through a file. ``sarathi-adb``, a user service
here, runs Sparsh's ``adb-share``, which listens on ``~/.sparsh/adb.sock``
(mode 0600) and passes each connection to this computer's adb. The
containers get ``ADB_SERVER_SOCKET`` naming that file, so their adb
asks this computer's, and an Android on the cable is there inside too.
A file, not a port, because whoever reaches adb can work the phone, and
a port the containers reach is one the house could reach. An Android
over Wi-Fi works as before, at ``[phone] address``:
``SPARSH_CONNECT`` tells Sparsh the address, and it reconnects whenever
it looks for phones. The page and the door mount ``~/.android``, so the
key this computer paired with is theirs too (nothing is paired twice),
and ``~/.sparsh``, so the person's rules hold inside. The page gets ``--sparsh
auto:…`` (no phone answering at the start means no tools until the
person says to use one); the door gets ``--sparsh`` for the one person
its actors file marks ``phone = true``.

THE PAGES PEOPLE LOOK AT, with ``[pages] on`` (the default). Setu's page
(``sarathi-setu``) and, with the door on, Dvara's owner page
(``sarathi-dvara-page``) are two more containers from the same image, each
published on 127.0.0.1 only. The owner page reaches the door by name on
the network and holds the door's token from its own env file, so your
answers from the browser get to the door; no other page holds it. The
HOME PAGE IS NOT A CONTAINER: Sarathi is not in the image, and from a
container 127.0.0.1 is that container, so it could not see the other
pages' ports. It is an ordinary user service (``sarathi-home.service``
in ``~/.config/systemd/user``) running this machine's ``sarathi home``,
started at login with the rest.

THE DOOR'S WINDOW IS PUBLISHED. With ``[dvara] window_host`` set, Setu
streams a sign-in window from the door's container: it listens on
every address inside (``SETU_WINDOW_HOST=0.0.0.0``), on a fixed port
(``window_port``, else 8790), published on ``window_host`` alone, and
the link says ``window_url`` or ``http://window_host:port`` -- never the
container's own address, which no phone can reach. SETU'S PAGE IS
PUBLISHED THERE TOO, when ``window_host`` is one address (not 0.0.0.0):
a person's link from ``/accounts page`` then opens on their phone.

SMRITIKOSH, with ``[memory] via = "smritikosh"``, is two more units.
Its database (``sarathi-smritikosh-db``) runs the pgvector image on the
volume ``sarathi smritikosh`` found or made -- the same data on both
roads, so the plain container of the same name is stopped first: two
servers on one data folder would ruin it. Its server
(``sarathi-smritikosh``) runs from Sarathi's image, which has Smritikosh
in it when ``[smritikosh] checkout`` names one, and reads its own
``.env`` from a file of its own (``units/sarathi-smritikosh.env``) with
the database's address made the database container's name, and
Ollama's the host's. It runs ``alembic upgrade head`` before it serves:
a rebuilt image may carry a column the database has not got yet, and
every query would fail on it. Neither mounts anything of the other pieces'.
With ``[smritikosh] full``, Neo4j, MongoDB and Redis are a unit each
(``sarathi-smritikosh-neo4j`` and so on), COPIED FROM THE CONTAINER THAT
HOLDS THEIR DATA: the same image, by its id (a ``latest`` tag would pull
a newer server onto old data), the same mounts, the settings it was made
with, published on 127.0.0.1 at the same ports. The plain container is
stopped first, as the database's is.
Smritikosh's own dashboard is a user service like the home page
(``sarathi-smritikosh-ui.service``), run from its checkout's build with
this machine's Node: no Node in the image, and it reaches Smritikosh where
its unit publishes it, 127.0.0.1.
Yantra's and Dvara's containers start ``smritikosh-mcp`` from the image,
pointed at ``http://sarathi-smritikosh:8080``; Yantra gets your key in
its env file, Samay too (the runs it starts are yours, and remember as
the page does), and Dvara reads each person's from its memory.json.

A FIREWALL IS NAMED, NOT OPENED. Publishing a port on the house address
does nothing for a phone when ufw or firewalld drops it first: the page
just spins, with nothing in any log. So when those ports are on one
address and a firewall is on, ``up`` says which ports and the command
that opens them to that network alone. It runs nothing: opening a port
needs root, and is the owner's call; and it can't tell a port already
opened (reading ufw's rules needs root too), so it says "if".
"""

from __future__ import annotations

import ipaddress
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
    DEFAULT_VOICES,
    DOOR_TOKEN,
    KEY_NAMES,
    NOT_ONE_ADDRESS,
    YANTRA_TOKEN,
    Config,
    ConfigError,
    config_dir,
    read_secrets,
    secrets_path,
    state_dir,
    write_private,
    yantra_token,
)
from sarathi.services import (OLD_NAMES, WIDTH, alive, answers, door_problems, place,
                              records, sarathi_program, work_dir)
from sarathi.siblings import beside_dir

IMAGE = "localhost/sarathi:latest"
IN_IMAGE = "/usr/local/bin"
CHECKOUTS = ("yantra", "setu", "samay")
#: Built into the image when its checkout is there: the door needs dvara,
#: the phone needs sparsh, and watches need prahari.
OPTIONAL_CHECKOUTS = ("dvara", "sparsh", "prahari")
#: Built in from where sarathi.toml says, when it says (``[smritikosh]``).
MEMORY_CHECKOUT = "smritikosh"
#: What a build is from, beside the Containerfile; the image's label (version.py).
BUILD_FILE = "build.json"
#: Ports inside the containers; the host ports come from sarathi.toml.
PAGE_PORT, CLOCK_PORT, DOOR_PORT = 8321, 8780, 8765
#: Prahari's page, its API and its inlet, inside its container.
WATCH_PORT = 8782
#: Prahari's inlet alone, inside its container (the public road's).
WATCH_INLET_PORT = 8783
SETU_PAGE_PORT, OWNER_PAGE_PORT = 8775, 8785
SMRITIKOSH_PORT = 8080
#: ntfy's own image (not Sarathi's: nothing of ours runs in it), pinned,
#: and its port inside.
NTFY_IMAGE, NTFY_PORT = "docker.io/binwiederhier/ntfy:v2.11.0", 80
#: The streamed sign-in window's port when sarathi.toml names none: a
#: container's port has to be known to be published.
WINDOW_PORT = 8790
#: The browser in the image, and the one a desktop's Setu records.
BROWSER = "/usr/bin/google-chrome"
UNITS = {"samay": "sarathi-samay", "prahari": "sarathi-prahari", "dvara": "sarathi-dvara",
         "yantra": "sarathi-yantra",
         "setu": "sarathi-setu", "dvara-page": "sarathi-dvara-page",
         "sarathi": "sarathi-home", "smritikosh-db": "sarathi-smritikosh-db",
         "smritikosh": "sarathi-smritikosh", "smritikosh-neo4j": "sarathi-smritikosh-neo4j",
         "smritikosh-mongodb": "sarathi-smritikosh-mongodb",
         "smritikosh-redis": "sarathi-smritikosh-redis",
         "smritikosh-ui": "sarathi-smritikosh-ui", "ntfy": "sarathi-ntfy",
         "adb": "sarathi-adb"}
#: Not a container: an ordinary user service (see the module docstring).
SERVICE_UNITS = ("sarathi", "smritikosh-ui", "adb")
#: Containers from an image of their own, so `sarathi image` doesn't restart them.
OWN_IMAGE = ("ntfy",)
#: The containers' names before each went by its project's name: stopped
#: and removed by `up` and `down`, so an old one never holds a port.
OLD_UNITS = ("sarathi-clock", "sarathi-door", "sarathi-page", "sarathi-owner")
#: The sarathi.toml key that moves each one's host port.
SETTINGS = services.PORT_SETTINGS
NETWORK = "sarathi"
READY_TIMEOUT = 90.0
#: Where ufw keeps its on/off switch, readable without root.
UFW_CONF = Path("/etc/ufw/ufw.conf")
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


def stage(into: Path, env: dict[str, str] | None = None,
          config: Config | None = None) -> list[str]:
    """A clean build context: each checkout's HEAD, and the Containerfile."""
    lines = []
    found = checkouts(env)
    memory = config.smritikosh.path() if config is not None else None
    if memory is not None and (memory / ".git").exists():
        found[MEMORY_CHECKOUT] = memory
    for name, repo in found.items():
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
        # the image has no git: each program's --version reads this instead
        from sarathi.version import dated

        (into / name / "VERSION").write_text(f"{dated(repo) or 'unknown'} {head}\n")
        note = f"{name:<7} {head}"
        if dirty:
            note += f"  ({len(dirty)} uncommitted change(s) left out: commit to include them)"
        lines.append(note)
    for name in OPTIONAL_CHECKOUTS:
        if not (into / name).exists():
            (into / name).mkdir(parents=True)    # empty: the image is built without it
            lines.append(f"{name:<7} not found beside the others: built without it")
    if not (into / MEMORY_CHECKOUT).exists():
        (into / MEMORY_CHECKOUT).mkdir(parents=True)
        lines.append(f"{MEMORY_CHECKOUT} not set up (`sarathi smritikosh`): built without it")
    shutil.copy(Path(__file__).with_name("Containerfile"), into / "Containerfile")
    # what this build is from, for the image's label (version.py)
    from sarathi.version import build_label

    (into / BUILD_FILE).write_text(json.dumps(build_label(found)))
    return lines


def platform() -> str:
    """This machine's own platform, named the way podman names one. Asked
    for on every build: an arm64 build on this machine had left arm64
    images under the base images' names, and a plain build then made an
    arm64 Sarathi that ran every service through qemu."""
    arch = {"x86_64": "amd64", "aarch64": "arm64", "armv7l": "arm/v7"}
    machine = os.uname().machine
    return f"linux/{arch.get(machine, machine)}"


def build(engine: str = "podman", config: Config | None = None) -> int:
    with tempfile.TemporaryDirectory(prefix="sarathi-build-") as tmp:
        print("building from:")
        for line in stage(Path(tmp), config=config):
            print(f"  {line}")
        print(flush=True)
        here = browser_version([BROWSER, "--version"]) if shutil.which(BROWSER) else None
        # the voices to read answers aloud with: [dvara] voices (Dvara's spoken.py)
        voices = config.door.voices if config is not None and config.door else DEFAULT_VOICES
        voice = ["--build-arg", f"PIPER_VOICES={' '.join(voices)}"]
        # each project's commit, on the image itself: `sarathi version` and
        # the home page read it back without starting a container
        stamp = Path(tmp) / BUILD_FILE
        label = ["--label", f"sarathi.build={stamp.read_text()}"] if stamp.exists() else []
        code = subprocess.run([engine, "build", "--platform", platform(), "-t", IMAGE,
                               "--build-arg",
                               f"HOST_BROWSER={'.'.join(map(str, here or ()))}", *voice,
                               *label, tmp],
                              check=False).returncode
    if code == 0:
        inside = run([engine, "run", "--rm", "--entrypoint", "/usr/local/bin/sarathi-browser",
                      IMAGE, "--version"]).stdout.strip()
        print(f"\nbrowser in the image: {inside or 'none found'}")
        voices = (run([engine, "run", "--rm", "--entrypoint", "/bin/ls", IMAGE,
                       "/usr/share/piper/voices"]).stdout or "").split()
        said = [v.removesuffix(".onnx") for v in voices if v.endswith(".onnx")]
        print(f"voices in the image:  {', '.join(said) or 'none (answers stay words)'}")
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
    prahari = os.environ.get("PRAHARI_STATE", "").strip()
    return [Path(samay).expanduser() if samay else home / ".samay",
            xdg_state / "setu", xdg_state / "yantra", home / ".yantra", work_dir(),
            Path(prahari).expanduser() if prahari else home / ".prahari"]


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


def host_timezone() -> str | None:
    """This computer's timezone by name (``America/New_York``), or None.
    A container is in UTC otherwise, and a browser there tells every page
    so: a site that also sees a New York address reads the mismatch as a
    bot (X refused the streamed window's password on it)."""
    raw = os.environ.get("TZ", "").lstrip(":")
    if "/" in raw and not raw.startswith("/"):
        return raw
    try:
        named = Path("/etc/timezone").read_text().strip()
        if named:
            return named
    except OSError:
        pass
    target = os.path.realpath("/etc/localtime")
    _, found, name = target.partition("/zoneinfo/")
    return name if found and name else None


def container_env(config: Config) -> dict[str, str]:
    prefix = config.provider.upper()
    run_yantra = f"{IN_IMAGE}/yantra"
    if config.remembers_in_smritikosh:
        # Samay's runs keep memories where Yantra's page does (units)
        run_yantra += f" --mcp-config {memory_files(config)[0]}"
    env = {"HOME": str(Path.home()), "YANTRA_PROVIDER": config.provider,
           "SAMAY_YANTRA": run_yantra, "SAMAY_YANTRA_HOME": str(work_dir()),
           # every look is `yantra --call`, with the page's accounts and memory
           "PRAHARI_YANTRA": run_yantra, "PRAHARI_YANTRA_HOME": str(work_dir())}
    zone = host_timezone()
    if zone:
        env["TZ"] = zone          # the browser's clock, the logs', the schedules'

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
    """The phone's Wi-Fi address, as Sparsh's ``SPARSH_CONNECT``, an
    iPhone's WebDriverAgent as ``SPARSH_WDA``, and its screen while an
    agent works it, as ``SPARSH_AWAKE``. WebDriverAgent forwarded to this
    computer (``http://127.0.0.1:8100``) is reached from a container at
    ``host.containers.internal``; go-ios's forward listens on every
    address, so that answers."""
    env = services.phone_env(config)
    if "SPARSH_WDA" in env:
        env["SPARSH_WDA"] = from_container(env["SPARSH_WDA"])
    if "SPARSH_PHONES" in env:
        env["SPARSH_PHONES"] = ",".join(
            f"{p.name}={from_container(p.wda) if p.wda else p.where}"
            for p in config.phone.named)
    if config.phone is not None:
        # this computer's adb, lent through a file (module docstring)
        env["ADB_SERVER_SOCKET"] = f"localfilesystem:{adb_socket()}"
    return "".join(f"Environment={k}={v}\n" for k, v in env.items())


def adb_socket() -> Path:
    """Where ``sarathi-adb`` lends this computer's adb: Sparsh's own
    folder, which the containers that work the phone already mount."""
    sparsh = os.environ.get("SPARSH_STATE", "").strip()
    return (Path(sparsh).expanduser() if sparsh else Path.home() / ".sparsh") / "adb.sock"


def adb_unit(config: Config) -> str | None:
    """``sparsh adb-share`` as a user service, with [phone] on and Sparsh
    on this computer; None otherwise."""
    from sarathi.siblings import SIBLINGS, locate

    if config.phone is None:
        return None
    hit = locate(next(s for s in SIBLINGS if s.name == "sparsh"))
    if hit is None:
        return None
    return f"""{HEADER}
[Unit]
Description=Sarathi: this computer's adb, lent to the containers (the phone on the cable)

[Service]
ExecStart={hit[0]} adb-share --socket {adb_socket()}
Restart=on-failure

[Install]
WantedBy=default.target
"""


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
    # Yantra's page wants its token in the container, where it listens on
    # every address (Yantra's gate.py); the home page's link carries it
    out = {UNITS["yantra"]: {**model, YANTRA_TOKEN: yantra_token()},
           UNITS["samay"]: {**model, **door,
                            **{k: v for k, v in services.doctor_env(config).items()
                               if k in ("SAMAY_DOCTOR_TOKEN", "SAMAY_BACKUP_TOKEN")}}}
    if services.watching(config):
        # a watch's then-turn is a turn: the key; its news goes to the door
        out[UNITS["prahari"]] = {**model, **{k.replace("SAMAY_", "PRAHARI_", 1): v
                                             for k, v in door.items()}}
    if config.remembers_in_smritikosh:
        from sarathi import smritikosh

        if smritikosh.KEY in held:
            # yours: Yantra's page, and the runs Samay starts for you
            out[UNITS["yantra"]][smritikosh.KEY] = held[smritikosh.KEY]
            out[UNITS["samay"]][smritikosh.KEY] = held[smritikosh.KEY]
            if UNITS["prahari"] in out:
                out[UNITS["prahari"]][smritikosh.KEY] = held[smritikosh.KEY]
        checkout = config.smritikosh.path()
        assert checkout is not None
        out[UNITS["smritikosh"]] = smritikosh.container_dotenv(
            checkout, db_host=UNITS["smritikosh-db"],
            extras={store: UNITS[f"smritikosh-{store}"]
                    for store in config.smritikosh.extras()})
        db = smritikosh.Database.parse(smritikosh.read_dotenv(checkout / ".env").get(
            "POSTGRES_URL", "postgresql://smritikosh:smritikosh@localhost:5432/smritikosh"))
        out[UNITS["smritikosh-db"]] = {"POSTGRES_USER": db.user,
                                       "POSTGRES_PASSWORD": db.password,
                                       "POSTGRES_DB": db.name}
    if config.door is not None:
        out[UNITS["dvara"]] = {**model, **door,
                              # what Dvara's per-turn `prahari mcp` checks a watch against
                              **({"PRAHARI_DVARA_TOKEN": door["SAMAY_DVARA_TOKEN"]}
                                 if services.watching(config) and door else {}),
                              **{k: held[k] for k in (DOOR_TOKEN, BOT_TOKEN) if k in held}}
        if config.pages.on and DOOR_TOKEN in held:
            # the owner page passes your answers to the door: its token, nothing else
            out[UNITS["dvara-page"]] = {DOOR_TOKEN: held[DOOR_TOKEN]}
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
    if door is None or not (door.window_env() or config.house and config.people_host()):
        return None
    host = (config.people_host() if config.house else None) or door.window_host \
        or "127.0.0.1"
    port = door.window_port or WINDOW_PORT
    return host, str(port), door.window_url or (config.link(port, "") if config.house
                                                else f"http://{host}:{port}")


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
    return host, port, config.link(int(port), "")


def yantra_window(config: Config) -> tuple[str, str, str] | None:
    """(host it is published on, port, the link's base) for the streamed
    window of a sign-in started on Yantra's page -- a site added, an
    account connected. In its container every browser is "another
    device", you at this computer too (Podman's bridge), so it always has
    one: on the house address with ``[house]``, where the page opens on
    every device, else on 127.0.0.1 for you alone. The port after Setu's
    page's window; None behind ``window_url``, as there."""
    door = config.door
    if door is not None and door.window_url:
        return None
    port = ((door.window_port if door else None) or WINDOW_PORT) + 2
    host = config.people_host() if config.house is not None else None
    if host:
        return host, str(port), config.link(port, "")
    return "127.0.0.1", str(port), f"http://127.0.0.1:{port}"


def house_ports(config: Config) -> tuple[str, list[int]] | None:
    """(the house address, the ports published on it) for the door's
    window, Setu's page and its window -- and with ``[house]``, every
    piece's; None when nothing is published beyond this computer."""
    if config.house is not None:
        address = config.people_host()
        return (address, sorted(set(lan_ports(config)))) if address else None
    door = config.door
    if door is None or not door.window_host or door.window_host in NOT_ONE_ADDRESS:
        return None
    ports = [int(window(config)[1])]
    if config.people_host():
        ports += [config.pages.setu_port, config.pages.home_port]
        if door.ntfy_port:
            ports.append(door.ntfy_port)
        shown = setu_window(config)
        if shown:
            ports.append(int(shown[1]))
    return door.window_host, sorted(ports)


def lan_ports(config: Config) -> list[int]:
    """Every port ``[house]`` publishes on the house address: the pages
    you open, and what they send a phone to (a sign-in window, ntfy).
    Never what only the pieces talk to -- Dvara's own port, Smritikosh's
    server and its stores."""
    kosh, door, pages = config.smritikosh, config.door, config.pages
    ports = [config.web_port]
    shown = yantra_window(config) if config.house is not None else None
    ports += [int(shown[1])] if shown else []
    ports += [config.clock_port] if config.clock_on else []
    # Prahari's page, and its inlet: what a phone app knocks on
    ports += [config.watch_port] if services.watching(config) else []
    if door is not None:
        shown = window(config)
        ports += [int(shown[1])] if shown else []
        ports += [door.ntfy_port] if door.ntfy_port else []
    if pages.on:
        ports += [pages.setu_port, pages.home_port]
        ports += [pages.door_port] if door is not None else []
        shown = setu_window(config)
        ports += [int(shown[1])] if shown else []
    if config.remembers_in_smritikosh and kosh.dashboard:
        ports.append(kosh.dashboard_port)
    return ports


def lan(config: Config, port: int, inner: int) -> str:
    """A second PublishPort, on the house address, with ``[house]``."""
    address = config.people_host() if config.house else None
    return f"PublishPort={address}:{port}:{inner}\n" if address else ""


def firewall() -> str | None:
    """"ufw" or "firewalld" when one is on, else None."""
    try:
        if "ENABLED=yes" in UFW_CONF.read_text().replace(" ", ""):
            return "ufw"
    except OSError:
        pass
    if run(["systemctl", "is-active", "--quiet", "firewalld"]).returncode == 0:
        return "firewalld"
    return None


def house_network(host: str) -> str:
    """192.168.1.44 -> 192.168.1.0/24, from the address's own interface;
    the /24 around it when no interface says."""
    said = run(["ip", "-o", "addr", "show"]).stdout if shutil.which("ip") else ""
    for word in said.split():
        if word.startswith(host + "/"):
            return str(ipaddress.ip_interface(word).network)
    try:
        return str(ipaddress.ip_network(f"{host}/24", strict=False))
    except ValueError:
        return host


def firewall_note(config: Config) -> list[str]:
    """Lines naming the house ports and how to open them, when a firewall
    is on (the module docstring)."""
    shown = house_ports(config)
    wall = firewall() if shown else None
    if wall is None:
        return []
    host, ports = shown
    if wall == "ufw":
        command = (f"sudo ufw allow from {house_network(host)} to any port "
                   f"{','.join(map(str, ports))} proto tcp")
    else:
        adds = " ".join(f"--add-port={p}/tcp" for p in ports)
        command = f"sudo firewall-cmd --permanent {adds} && sudo firewall-cmd --reload"
    return [f"firewall: {wall} is on; if a phone can't open {host} on "
            f"{', '.join(map(str, ports))}, open them to your network (once is enough):",
            f"  {command}"]


def units(config: Config) -> dict[str, str]:
    """File name -> contents, for the Quadlet folder."""
    out = {}
    page_exec = (f"{IN_IMAGE}/yantra --web --host 0.0.0.0 --port {PAGE_PORT} "
                 f"--setu {IN_IMAGE}/setu ")
    page_unit = ""
    memory_env, memory_dirs, memory_after = "", [], ""
    if config.remembers_in_smritikosh:
        from sarathi import smritikosh

        memory_env = "".join(f"Environment={k}={v}\n" for k, v in
                             smritikosh.yantra_env().items() if k != smritikosh.KEY)
        memory_dirs = [smritikosh.mcp_dir()]
        memory_after = (f"Wants={UNITS['smritikosh']}.service\n"
                        f"After={UNITS['smritikosh']}.service\n")
    if config.clock_on:
        # a schedule made at this computer runs as you, so it remembers as
        # Yantra's page does (SAMAY_YANTRA, container_env)
        out[f"{UNITS['samay']}.container"] = _unit(
            "Sarathi: Samay", UNITS["samay"],
            f"{IN_IMAGE}/samay serve --host 0.0.0.0 --port {CLOCK_PORT}",
            f"127.0.0.1:{config.clock_port}:{CLOCK_PORT}", config, memory_after,
            # where a browser here reaches it, so Samay prints and reports
            # that, not the container's own bind (an older image ignores it)
            extra_container=lan(config, config.clock_port, CLOCK_PORT)
                            + f"Environment=SAMAY_PUBLIC_URL={config.link(config.clock_port)}\n"
                            # the doctor answers on the host (it looks at systemd,
                            # Podman, the firewall): reached as the host, keyed
                            + "".join(f"Environment={k}={v}\n" for k, v in
                                      services.doctor_env(config, "host.containers.internal")
                                      .items() if k in ("SAMAY_DOCTOR_URL", "SAMAY_BACKUP_URL"))
                            + (f"Environment=SAMAY_DVARA_URL=http://{UNITS['dvara']}:"
                               f"{DOOR_PORT}\n"
                               # a schedule made on Yantra's page is told to you
                               f"Environment=SAMAY_DVARA_ACTOR={config.door.owner}\n"
                               if config.door else "") + memory_env
                            # one made there that works the phone gets it, after
                            # Dvara's check: the phone's address, your rules
                            + phone_env(config),
            more_volumes=(memory_dirs + phone_dirs(config)) or None)
        page_exec += f"--samay {IN_IMAGE}/samay"
        page_unit = f"Wants={UNITS['samay']}.service\nAfter={UNITS['samay']}.service\n"
    else:
        page_exec += "--no-samay"
    watch = services.watching(config)
    if watch:
        out[f"{UNITS['prahari']}.container"] = _unit(
            "Sarathi: Prahari", UNITS["prahari"],
            f"{IN_IMAGE}/prahari serve --host 0.0.0.0 --port {WATCH_PORT}"
            + (f" --inlet-port {WATCH_INLET_PORT}" if config.watch_inlet_port else ""),
            f"127.0.0.1:{config.watch_port}:{WATCH_PORT}", config, memory_after,
            # its page and its inlet on the house address too: a phone app knocks
            extra_container=lan(config, config.watch_port, WATCH_PORT)
                            # the inlet alone, on 127.0.0.1, where Tailscale Funnel
                            # reaches it for the public road
                            + (f"PublishPort=127.0.0.1:{config.watch_inlet_port}:"
                               f"{WATCH_INLET_PORT}\n" if config.watch_inlet_port else "")
                            + (f"Environment=PRAHARI_INLET_PUBLIC_URL={config.watch_public}\n"
                               if config.watch_public else "")
                            + f"Environment=PRAHARI_PUBLIC_URL={config.link(config.watch_port)}\n"
                            + (f"Environment=PRAHARI_DVARA_URL=http://{UNITS['dvara']}:"
                               f"{DOOR_PORT}\n"
                               f"Environment=PRAHARI_DVARA_ACTOR={config.door.owner}\n"
                               if config.door else "") + memory_env,
            more_volumes=memory_dirs or None)
        page_exec += f" --prahari {IN_IMAGE}/prahari"
        page_unit += f"Wants={UNITS['prahari']}.service\nAfter={UNITS['prahari']}.service\n"
    elif not config.watch_on:
        page_exec += " --no-prahari"
    if config.door is not None:
        door, after = config.door, ""
        door_exec = (f"{IN_IMAGE}/dvara --root {door.path('root')} --actors "
                     f"{door.path('actors')} --state {door.path('state')} --ask "
                     f"--owner {door.owner} --provider {config.provider} "
                     + (f"--model {config.model} " if config.model else "")
                     + (f"--samay {IN_IMAGE}/samay " if config.clock_on else "--samay off ")
                     # each person's watch looks with their own accounts
                     + (f"--prahari {IN_IMAGE}/prahari " if watch else "")
                     + (f"--prahari-for {','.join(config.watch_people)} "
                        if watch and config.watch_people else "")
                     + (f"--sparsh {IN_IMAGE}/sparsh " if config.phone else "")
                     + (f"--memory {memory_files(config)[1]} "
                        if config.remembers_in_smritikosh else "")
                     + (f"--ntfy http://{UNITS['ntfy']}:{NTFY_PORT} " if door.ntfy_port else "")
                     + f"serve --host 0.0.0.0 --port {DOOR_PORT} --web"
                     + (f" --telegram {door.telegram}" if door.telegram else ""))
        if config.clock_on:
            after = f"Wants={UNITS['samay']}.service\nAfter={UNITS['samay']}.service\n"
        if watch:
            after += (f"Wants={UNITS['prahari']}.service\n"
                      f"After={UNITS['prahari']}.service\n")
        if config.remembers_in_smritikosh:
            after += (f"Wants={UNITS['smritikosh']}.service\n"
                      f"After={UNITS['smritikosh']}.service\n")
        push = ""
        if door.ntfy_port:
            out[f"{UNITS['ntfy']}.container"] = ntfy_unit(config)
            after += f"Wants={UNITS['ntfy']}.service\nAfter={UNITS['ntfy']}.service\n"
            push = "".join(f"Environment={k}={v}\n"
                           for k, v in services.ntfy_click(config).items())
        shown = window(config)
        streamed = "" if shown is None else (
            f"PublishPort={shown[0]}:{shown[1]}:{shown[1]}\n"
            f"Environment=SETU_WINDOW_HOST=0.0.0.0\n"
            f"Environment=SETU_WINDOW_PORT={shown[1]}\n"
            f"Environment=SETU_WINDOW_URL={shown[2]}\n")
        out[f"{UNITS['dvara']}.container"] = _unit(
            "Sarathi: Dvara", UNITS["dvara"], door_exec,
            f"127.0.0.1:{door.port}:{DOOR_PORT}", config, after,
            extra_container=f"Environment=SAMAY_DVARA_URL=http://127.0.0.1:{DOOR_PORT}\n"
                            + (f"Environment=PRAHARI_DVARA_URL=http://127.0.0.1:{DOOR_PORT}\n"
                               if watch else "")
                            + streamed + people_url(config) + phone_env(config) + push
                            + (f"Environment=DVARA_WHISPER={from_container(door.whisper)}\n"
                               if door.whisper else ""),
            more_volumes=door_dirs(config) + phone_dirs(config)
            + ([mcp_dir()] if config.remembers_in_smritikosh else []))
        page_unit += f"After={UNITS['dvara']}.service\n"
    if config.phone is not None:
        # auto: no phone answering at the start means no phone tools until
        # you press "use this phone" -- as on the process road
        page_exec += f" --sparsh auto:{IN_IMAGE}/sparsh"
    if config.remembers_in_smritikosh:
        yantra_file, _ = memory_files(config)
        page_exec += f" --mcp-config {yantra_file}"
        page_unit += memory_after
        out.update(memory_units(config))
    out[f"{UNITS['yantra']}.container"] = _unit(
        "Sarathi: Yantra's page", UNITS["yantra"], page_exec,
        f"127.0.0.1:{config.web_port}:{PAGE_PORT}", config, page_unit,
        extra_container=lan(config, config.web_port, PAGE_PORT) + phone_env(config)
        + memory_env + (setu_window_lines(config, yantra_window(config))
                        if yantra_window(config) else ""),
        more_volumes=phone_dirs(config) + memory_dirs)
    if config.pages.on:
        pages = config.pages
        folders = people_dir(config)
        people = f" --people {folders}" if folders else ""
        phones = config.people_host()
        out[f"{UNITS['setu']}.container"] = _unit(
            "Sarathi: Setu's page", UNITS["setu"],
            f"{IN_IMAGE}/setu serve --host 0.0.0.0 --port {SETU_PAGE_PORT} "
            f"--public-url {config.link(pages.setu_port) if config.house else
                            f'http://127.0.0.1:{pages.setu_port}/'}{people}",
            f"127.0.0.1:{pages.setu_port}:{SETU_PAGE_PORT}", config,
            # people's links open on their phones (config.people_host)
            extra_container=(f"PublishPort={phones}:{pages.setu_port}:{SETU_PAGE_PORT}\n"
                             if phones else "") + setu_window_lines(config),
            more_volumes=[folders] if folders else None)
        if config.door is not None:
            door = config.door
            out[f"{UNITS['dvara-page']}.container"] = _unit(
                "Sarathi: dvara's owner page", UNITS["dvara-page"],
                f"{IN_IMAGE}/dvara --root {door.path('root')} --actors "
                f"{door.path('actors')} --state {door.path('state')} page --as {door.owner} "
                f"--host 0.0.0.0 --port {OWNER_PAGE_PORT}",
                f"127.0.0.1:{pages.door_port}:{OWNER_PAGE_PORT}", config,
                f"Wants={UNITS['dvara']}.service\nAfter={UNITS['dvara']}.service\n",
                extra_container=lan(config, pages.door_port, OWNER_PAGE_PORT)
                + f"Environment=DVARA_URL=http://{UNITS['dvara']}:{DOOR_PORT}\n",
                more_volumes=door_dirs(config))
    out[f"{NETWORK}.network"] = (f"{HEADER}\n[Network]\nNetworkName={NETWORK}\n")
    return out


def ntfy_unit(config: Config) -> str:
    """ntfy, for notices on phones (dvara's push.py): its own image, its
    cache in a volume, on 127.0.0.1 and on the house address a phone reaches."""
    assert config.door is not None and config.door.ntfy_port
    port, phones = config.door.ntfy_port, config.people_host()
    house = f"PublishPort={phones}:{port}:{NTFY_PORT}\n" if phones else ""
    return f"""{HEADER}
[Unit]
Description=Sarathi: ntfy, for notices on phones

[Container]
Image={NTFY_IMAGE}
ContainerName={UNITS['ntfy']}
Network={NETWORK}.network
Exec=serve --cache-file /var/cache/ntfy/cache.db --cache-duration 24h
Volume=sarathi-ntfy-cache:/var/cache/ntfy
PublishPort=127.0.0.1:{port}:{NTFY_PORT}
{house}
[Service]
Restart=on-failure

[Install]
WantedBy=default.target
"""


def mcp_dir() -> Path:
    from sarathi.smritikosh import mcp_dir as folder

    return folder()


def memory_files(config: Config) -> tuple[Path, Path]:
    """Smritikosh's server as Yantra's and Dvara's containers start it."""
    from sarathi.smritikosh import mcp_files

    return mcp_files(config, command=f"{IN_IMAGE}/smritikosh-mcp",
                     url=f"http://{UNITS['smritikosh']}:{SMRITIKOSH_PORT}",
                     suffix="-podman")


def memory_units(config: Config) -> dict[str, str]:
    """Smritikosh's database and server (the module docstring). Lean on
    purpose: neither runs as you nor mounts any other piece's files."""
    from sarathi.smritikosh import DB_IMAGE

    kosh = config.smritikosh
    db, api = UNITS["smritikosh-db"], UNITS["smritikosh"]
    serve = ('/bin/sh -c "cd /opt/smritikosh && .venv/bin/alembic upgrade head && '
             'exec .venv/bin/uvicorn smritikosh.api.main:app '
             f'--host 0.0.0.0 --port {SMRITIKOSH_PORT}"')
    extras = extra_units(config)
    after = "".join(f"Wants={UNITS[n]}.service\nAfter={UNITS[n]}.service\n"
                    for n in ("smritikosh-db", *(f"smritikosh-{e}" for e in
                                                 kosh.extras())))
    return {**extras,
        f"{db}.container": f"""{HEADER}
[Unit]
Description=Sarathi: Smritikosh's database

[Container]
Image={DB_IMAGE}
ContainerName={db}
Network={NETWORK}.network
PublishPort=127.0.0.1:{kosh.db_port}:5432
Volume={kosh.volume}:/var/lib/postgresql/data:Z
EnvironmentFile={env_file(db)}

[Service]
Restart=on-failure

[Install]
WantedBy=default.target
""",
        f"{api}.container": f"""{HEADER}
[Unit]
Description=Sarathi: Smritikosh, the memory server
{after}
[Container]
Image={IMAGE}
ContainerName={api}
Network={NETWORK}.network
Exec={serve}
PublishPort=127.0.0.1:{kosh.port}:{SMRITIKOSH_PORT}
RunInit=true
EnvironmentFile={env_file(api)}

[Service]
Restart=on-failure
SuccessExitStatus=143

[Install]
WantedBy=default.target
"""}


def extra_units(config: Config) -> dict[str, str]:
    """Neo4j, MongoDB and Redis, each a unit copied from its plain
    container (the module docstring). A container that is gone is left
    out, and `up` says so."""
    from sarathi.smritikosh import container

    out = {}
    for store, name in config.smritikosh.extras().items():
        found = container(name)
        if found is None:
            continue
        unit = UNITS[f"smritikosh-{store}"]
        image = found.get("Image") or found.get("ImageName")
        own = set(run(["podman", "image", "inspect", "--format",
                       "{{range .Config.Env}}{{println .}}{{end}}", str(image)]
                      ).stdout.splitlines())
        made = [e for e in (found.get("Config") or {}).get("Env") or []
                if e not in own and not e.startswith(("HOSTNAME=", "container=", "HOME="))]
        if made:
            write_private(env_file(unit), "# Written by `sarathi up` from the container "
                          f"{name}.\n" + "".join(f"{e}\n" for e in made))
        mounts = "".join(
            f"Volume={m.get('Name') if m.get('Type') == 'volume' else m.get('Source')}:"
            f"{m.get('Destination')}\n" for m in found.get("Mounts") or [])
        bindings = [(int(b["HostPort"]), int(inner.split("/")[0]))
                    for inner, bound in ((found.get("HostConfig") or {}).get("PortBindings")
                                         or {}).items()
                    for b in bound or [] if str(b.get("HostPort", "")).isdigit()]
        # this computer only, [house] or not: Smritikosh's server reaches
        # them on the containers' own network, and nothing else needs them
        ports = "".join(f"PublishPort=127.0.0.1:{port}:{inner}\n" for port, inner in bindings)
        out[f"{unit}.container"] = f"""{HEADER}
[Unit]
Description=Sarathi: Smritikosh's {store}, from the container {name}

[Container]
Image={image}
ContainerName={unit}
Network={NETWORK}.network
{ports}{mounts}{f"EnvironmentFile={env_file(unit)}" + chr(10) if made else ""}
[Service]
Restart=on-failure

[Install]
WantedBy=default.target
"""
    return out


def setu_window_lines(config: Config, shown: tuple[str, str, str] | None = None) -> str:
    """A container's streamed window: published on its address, listened
    for on every one inside -- Setu's page's, or ``shown``'s (Yantra's)."""
    shown = shown or setu_window(config)
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
    # the people in the house sign in from their phones (people.py)
    house = f" --also-host {config.people_host()}" if config.people_host() else ""
    return f"""{HEADER}
[Unit]
Description=Sarathi: the home page, linking every program's page
After={UNITS['yantra']}.service

[Service]
ExecStart={sarathi_program()} home --port {config.pages.home_port}{house}
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


def dashboard_unit(config: Config) -> str | None:
    """Smritikosh's dashboard as a user service, or None when it isn't to run."""
    from sarathi import smritikosh

    kosh = config.smritikosh
    argv = smritikosh.dashboard_argv(kosh, house=config.house is not None) \
        if config.remembers_in_smritikosh else None
    if argv is None:
        return None
    env = "".join(f"Environment={k}={v}\n" for k, v in smritikosh.dashboard_env(
        kosh, config.house.name if config.house else "localhost").items())
    return f"""{HEADER}
[Unit]
Description=Sarathi: Smritikosh's own dashboard
After={UNITS['smritikosh']}.service

[Service]
WorkingDirectory={smritikosh.ui_dir(kosh.path())}
ExecStart={' '.join(argv)}
{env}Restart=on-failure

[Install]
WantedBy=default.target
"""


def dashboard_note(config: Config, unit: str | None) -> list[str]:
    """Why the dashboard is not among the units, when it is wanted: a
    rebuild of Smritikosh's ui/ is the usual cause, and without this line
    it simply vanished from the list."""
    from sarathi import smritikosh

    kosh = config.smritikosh
    if unit is not None or not config.remembers_in_smritikosh or not kosh.dashboard:
        return []
    checkout = kosh.path()
    if checkout is None or smritikosh.dashboard(config) is None:
        return []
    return [f"{'smritikosh-ui':<{WIDTH}} not started: {smritikosh.unbuilt(checkout)} "
            "(`sarathi smritikosh` builds it, then `sarathi up`)"]


def install_home(text: str | None, name: str = "sarathi") -> bool:
    """Write, or remove, a user service (the home page's, or the
    dashboard's); True when it changed. It is enabled, so it starts at
    login as the Quadlet units do."""
    path = unit_file(name)
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
    if name == "sarathi":
        try:
            token = (state_dir() / TOKEN_FILE).read_text().strip() or None
        except OSError:
            token = None
    else:
        wanted = {"setu": "setu", "dvara-page": "dvara"}.get(name)
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


def retire_old() -> list[str]:
    """Stop and remove units under their old names (OLD_UNITS). A unit
    file removed while its container still ran would leave the container
    holding its port, so each is stopped first."""
    lines = []
    for unit in OLD_UNITS:
        path = unit_dir() / f"{unit}.container"
        if not path.exists():
            continue
        run(["systemctl", "--user", "stop", f"{unit}.service"])
        path.unlink()
        env_file(unit).unlink(missing_ok=True)
        lines.append(f"{unit} stopped and removed: it is {UNITS[OLD_NAMES[unit[8:]]]} now")
    if lines:
        run(["systemctl", "--user", "daemon-reload"])
    return lines


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
    logs = run(["podman", "logs", UNITS["samay"]])
    for line in reversed((logs.stdout + logs.stderr).splitlines()):
        if line.startswith("page: "):
            parts = urlsplit(line[len("page: "):].strip())
            return urlunsplit(parts._replace(netloc=f"127.0.0.1:{config.clock_port}"))
    return None


def watch_address(config: Config) -> str | None:
    """Prahari's own 'page:' line (it says this computer's address itself,
    told by PRAHARI_PUBLIC_URL)."""
    logs = run(["podman", "logs", UNITS["prahari"]])
    for line in reversed((logs.stdout + logs.stderr).splitlines()):
        if line.startswith("page: "):
            return line[len("page: "):].strip()
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
            raise ConfigError("dvara cannot start: " + "; ".join(problems))
    if config.remembers_in_smritikosh and run(
            ["podman", "run", "--rm", "--entrypoint", "test", IMAGE, "-x",
             f"{IN_IMAGE}/smritikosh-mcp"]).returncode != 0:
        raise ConfigError("memory.via is smritikosh, but the image has no Smritikosh: "
                          "run `sarathi image` again")
    ours = [name for name, r in records().items() if alive(r["pid"])]
    if ours:
        raise ConfigError(f"{', '.join(ours)} still running as plain processes: "
                          "`sarathi down` on the process road first")


def up(config: Config) -> tuple[list[str], bool]:
    preflight(config)
    for folder in data_dirs() + door_dirs(config) + [p for p in [people_dir(config)] if p]:
        folder.mkdir(parents=True, exist_ok=True)
    write_env_files(config)
    retired = retire_old()
    changed = install(units(config))
    if install_home(home_unit(config)):
        changed.add(unit_file("sarathi").name)
    dash = dashboard_unit(config)
    if install_home(dash, "smritikosh-ui"):
        changed.add(unit_file("smritikosh-ui").name)
    lend = adb_unit(config)
    lent = install_home(lend, "adb")
    if lent:
        changed.add(unit_file("adb").name)
    lines = retired + (["units rewritten from sarathi.toml"] if changed else [])
    if lend is not None:
        run(["systemctl", "--user", "restart" if lent else "start", f"{UNITS['adb']}.service"])
        lines.append(f"{'adb':<{WIDTH}} the phone on this computer's cable, lent to the "
                     f"containers  (unit {UNITS['adb']})")
    lines += dashboard_note(config, dash)
    newest = image_id(IMAGE)
    note = browser_note()
    if note:
        lines.append(note)
    if run(["podman", "network", "exists", NETWORK]).returncode != 0:
        # removed by hand, or by an older `down --remove` that left its
        # one-shot service "active": made again before anything joins it
        run(["systemctl", "--user", "restart", f"{NETWORK}-network.service"])
    if not config.clock_on:
        lines.append(f"{'samay':<{WIDTH}} off in sarathi.toml")
    if not config.watch_on:
        lines.append(f"{'prahari':<{WIDTH}} off in sarathi.toml")
    ok = True
    wanted = []
    if config.remembers_in_smritikosh:
        said, db_ok = memory_database(config, changed)
        lines += said
        ok = ok and db_ok
        said, extras_ok = memory_extras(config, changed)
        lines += said
        ok = ok and extras_ok
        wanted.append(("smritikosh", config.smritikosh.port))
    wanted += [("samay", config.clock_port)] if config.clock_on else []
    wanted += [("prahari", config.watch_port)] if services.watching(config) else []
    if config.door is not None:
        if config.door.ntfy_port:
            wanted.append(("ntfy", config.door.ntfy_port))
        wanted.append(("dvara", config.door.port))
    wanted.append(("yantra", config.web_port))
    if config.pages.on:
        wanted.append(("setu", config.pages.setu_port))
        if config.door is not None:
            wanted.append(("dvara-page", config.pages.door_port))
        wanted.append(("sarathi", config.pages.home_port))
    if dashboard_unit(config) is not None:
        wanted.append(("smritikosh-ui", config.smritikosh.dashboard_port))
    owner = any(name == "dvara-page" for name, _ in wanted)
    for name, port in wanted:
        unit = UNITS[name]
        url = f"http://127.0.0.1:{port}/"
        if active(unit) and unit_file(name).name in changed:
            # a running container keeps the settings it started with: a
            # rewritten unit means nothing until it starts again
            run(["systemctl", "--user", "stop", f"{unit}.service"])
            lines.append(f"{name:<{WIDTH}} restarting with the new settings  (unit {unit})")
        elif (active(unit) and name not in SERVICE_UNITS + OWN_IMAGE and newest
              and image_id(unit) not in ("", newest)):
            # and the image it started from: `sarathi image` changes nothing
            # in a container already running
            run(["systemctl", "--user", "stop", f"{unit}.service"])
            lines.append(f"{name:<{WIDTH}} restarting with the new image  (unit {unit})")
        if active(unit):
            address = _address(config, name, url)
            lines.append(f"{name:<{WIDTH}} already running {place(name, address, owner)}  "
                         f"(unit {unit})")
            continue
        taken = [(port, SETTINGS[name])] if answers(port) else []
        shown = window(config) if name == "dvara" else None
        if shown and answers(int(shown[1])):
            taken.append((int(shown[1]), "dvara.window_port"))
        shown = setu_window(config) if name == "setu" else None
        if shown and answers(int(shown[1])):
            taken.append((int(shown[1]), "dvara.window_port"))
        shown = yantra_window(config) if name == "yantra" else None
        if shown and answers(int(shown[1])):
            taken.append((int(shown[1]), "dvara.window_port"))
        if taken:
            # a published port something else holds fails inside systemd,
            # restarted every few seconds, with the reason deep in a journal
            ok = False
            run(["systemctl", "--user", "stop", f"{unit}.service"])   # if it was looping
            lines += [f"{name:<{WIDTH}} not started: something else is listening on port "
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
            lines.append(f"{name:<{WIDTH}} up {place(name, address, owner)}  (unit {unit})")
            continue
        ok = False
        lines.append(f"{name:<{WIDTH}} did not come up (unit {unit}); the end of its journal:")
        lines += [f"         | {line}" for line in journal_tail(unit)]
    return lines + firewall_note(config), ok


def memory_database(config: Config, changed: set[str]) -> tuple[list[str], bool]:
    """Smritikosh's database unit, running and ready, before its server.
    The plain container on the same volume is stopped first."""
    from sarathi import smritikosh

    kosh, unit, lines = config.smritikosh, UNITS["smritikosh-db"], []
    name = "smritikosh-db"
    if smritikosh.stop_database(kosh):
        lines.append(f"{name:<{WIDTH}} the plain container {kosh.database} stopped: "
                     f"{unit} uses its volume ({kosh.volume}) now")
    if active(unit) and f"{unit}.container" in changed:
        run(["systemctl", "--user", "stop", f"{unit}.service"])
        lines.append(f"{name:<{WIDTH}} restarting with the new settings  (unit {unit})")
    if active(unit):
        lines.append(f"{name:<{WIDTH}} already running on 127.0.0.1:{kosh.db_port}  "
                     f"(unit {unit})")
        return lines, True
    if answers(kosh.db_port):
        lines.append(f"{name:<{WIDTH}} not started: something else is listening on port "
                     f"{kosh.db_port} (change smritikosh.db_port in sarathi.toml)")
        return lines, False
    started = run(["systemctl", "--user", "start", f"{unit}.service"])
    db = smritikosh.Database.parse(smritikosh.read_dotenv(
        (kosh.path() or Path(".")) / ".env").get(
        "POSTGRES_URL", "postgresql://smritikosh:smritikosh@localhost:5432/smritikosh"))
    if started.returncode == 0 and smritikosh.db_ready(unit, db, READY_TIMEOUT):
        lines.append(f"{name:<{WIDTH}} up on 127.0.0.1:{kosh.db_port}  (unit {unit})")
        return lines, True
    lines.append(f"{name:<{WIDTH}} did not come up (unit {unit}); the end of its journal:")
    lines += [f"         | {line}" for line in journal_tail(unit)]
    return lines, False


def memory_extras(config: Config, changed: set[str]) -> tuple[list[str], bool]:
    """Neo4j, MongoDB and Redis units, with ``full``: the plain containers
    stopped first, then each unit started and listening."""
    from sarathi import smritikosh

    lines, ok = [], True
    for name in smritikosh.stop_extras(config.smritikosh):
        lines.append(f"{'smritikosh':<{WIDTH}} the plain container {name} stopped: its "
                     "unit uses its data now")
    for store, plain in config.smritikosh.extras().items():
        key, unit = f"smritikosh-{store}", UNITS[f"smritikosh-{store}"]
        if not unit_file(key).exists():
            ok = False
            lines.append(f"{key:<{WIDTH}} not started: no container {plain} to copy "
                         "(`sarathi smritikosh --full`)")
            continue
        if active(unit) and f"{unit}.container" in changed:
            run(["systemctl", "--user", "stop", f"{unit}.service"])
        if active(unit):
            lines.append(f"{key:<{WIDTH}} already running  (unit {unit})")
            continue
        started = run(["systemctl", "--user", "start", f"{unit}.service"])
        if started.returncode == 0 and active(unit):
            lines.append(f"{key:<{WIDTH}} up  (unit {unit}, from {plain})")
        else:
            ok = False
            lines.append(f"{key:<{WIDTH}} did not come up (unit {unit}); its journal:")
            lines += [f"         | {line}" for line in journal_tail(unit)]
    return lines, ok


def _address(config: Config, name: str, url: str) -> str:
    if name == "smritikosh-db":
        return f"127.0.0.1:{config.smritikosh.db_port} (PostgreSQL)"
    if name == "samay":
        return clock_address(config) or url
    if name == "prahari":
        return watch_address(config) or url
    if name in ("setu", "dvara-page", "sarathi"):
        return keyed_address(config, name, url)
    return url


def down(remove: bool = False) -> list[str]:
    """Stop the units. They stay installed -- and so start again at the
    next login, which is what they are for -- unless ``remove``."""
    lines = retire_old()
    for name in ("smritikosh-ui", "sarathi", "dvara-page", "setu", "yantra", "dvara",
                 "ntfy", "prahari", "samay",
                 "smritikosh", "smritikosh-db", "smritikosh-neo4j", "smritikosh-mongodb",
                 "smritikosh-redis"):
        unit = UNITS[name]
        if not unit_file(name).exists():
            continue
        if active(unit):
            run(["systemctl", "--user", "stop", f"{unit}.service"])
            lines.append(f"{name:<{WIDTH}} stopped  (unit {unit})")
        else:
            lines.append(f"{name:<{WIDTH}} was not running  (unit {unit})")
    if not lines:
        return ["no Sarathi units are installed"]
    if remove:
        # its service is a one-shot that stays "active (exited)": stopped
        # first, or the next `up` would find it active and never make the
        # network again
        run(["systemctl", "--user", "stop", f"{NETWORK}-network.service"])
        install({})
        install_home(None)
        install_home(None, "smritikosh-ui")
        if unit_file("adb").exists():
            run(["systemctl", "--user", "stop", f"{UNITS['adb']}.service"])
        install_home(None, "adb")
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
    for name, port in (("smritikosh-db", config.smritikosh.db_port),
                       ("smritikosh", config.smritikosh.port),
                       ("samay", config.clock_port),
                       ("prahari", config.watch_port),
                       ("ntfy", config.door.ntfy_port if config.door else None),
                       ("dvara", door_port),
                       ("yantra", config.web_port), ("setu", pages.setu_port),
                       ("dvara-page", pages.door_port), ("sarathi", pages.home_port),
                       ("smritikosh-ui", config.smritikosh.dashboard_port)):
        unit = UNITS[name]
        if port is None or not unit_file(name).exists():
            continue
        live = active(unit)
        url = f"http://127.0.0.1:{port}/"
        address = _address(config, name, url) if live else url
        row = {"name": name, "unit": unit, "alive": live, "address": address,
               "log": [] if live else journal_tail(unit)}
        if name == "dvara":
            row["strangers"] = strangers(journal_tail(unit, 400))
        out.append(row)
    return out
