"""The same two pieces, as containers that systemd keeps running.

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
The cloud road on Podman therefore reads keys from secrets.env only
(``EnvironmentFile=``). The unit files hold no key; they can be read and
pasted like sarathi.toml.

OLLAMA IS ON THE HOST. ``localhost`` inside a container is the
container, so the local road's address becomes
``host.containers.internal``, which Podman points at the host. Ollama
has to listen on more than 127.0.0.1 for that to reach it
(``OLLAMA_HOST=0.0.0.0``).

Not here: a browser. Setu's sign-ins that drive a browser (Amazon, X)
and Yantra's browser tools need one on the host. The accounts Setu
reaches over an API (Gmail, Home Assistant) work.
"""

from __future__ import annotations

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

from sarathi.config import KEY_NAMES, Config, ConfigError, read_secrets, secrets_path
from sarathi.services import alive, records, work_dir
from sarathi.siblings import beside_dir

IMAGE = "localhost/sarathi:latest"
IN_IMAGE = "/usr/local/bin"
CHECKOUTS = ("yantra", "setu", "samay")
#: Ports inside the containers; the host ports come from sarathi.toml.
PAGE_PORT, CLOCK_PORT = 8321, 8780
UNITS = {"clock": "sarathi-clock", "page": "sarathi-page"}
READY_TIMEOUT = 90.0
HEADER = ("# Written by `sarathi up` from sarathi.toml, and rewritten whenever it\n"
          "# changes: edit sarathi.toml, not this file.\n")


def run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False, **kw)


# ---- the image ------------------------------------------------------------------


def checkouts(env: dict[str, str] | None = None) -> dict[str, Path]:
    root = beside_dir(env)
    found, missing = {}, []
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
    shutil.copy(Path(__file__).with_name("Containerfile"), into / "Containerfile")
    return lines


def build(engine: str = "podman") -> int:
    with tempfile.TemporaryDirectory(prefix="sarathi-build-") as tmp:
        print("building from:")
        for line in stage(Path(tmp)):
            print(f"  {line}")
        print(flush=True)
        return subprocess.run([engine, "build", "-t", IMAGE, tmp], check=False).returncode


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
    return env


def _unit(description: str, name: str, exec_: str, publish: str, config: Config,
          extra_unit: str = "", extra_container: str = "") -> str:
    env = "".join(f"Environment={k}={v}\n" for k, v in container_env(config).items())
    volumes = "".join(f"Volume={d}:{d}:z\n" for d in data_dirs())
    secrets = f"EnvironmentFile={secrets_path()}\n" if secrets_path().exists() else ""
    return f"""{HEADER}
[Unit]
Description={description}
{extra_unit}
[Container]
Image={IMAGE}
ContainerName={name}
Exec={exec_}
PublishPort={publish}
UserNS=keep-id
WorkingDir={work_dir()}
{env}{secrets}{volumes}{extra_container}
[Service]
Restart=on-failure

[Install]
WantedBy=default.target
"""


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
                            f"{config.clock_port}/\n")
        page_exec += f"--samay {IN_IMAGE}/samay"
        page_unit = f"Wants={UNITS['clock']}.service\nAfter={UNITS['clock']}.service\n"
    else:
        page_exec += "--no-samay"
    out[f"{UNITS['page']}.container"] = _unit(
        "Sarathi: Yantra's page", UNITS["page"], page_exec,
        f"127.0.0.1:{config.web_port}:{PAGE_PORT}", config, page_unit)
    return out


def unit_dir() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "containers" / "systemd"


def install(wanted: dict[str, str]) -> bool:
    """Write the units that differ, remove ours that are no longer wanted;
    reload systemd if anything changed. Returns whether it did."""
    folder = unit_dir()
    folder.mkdir(parents=True, exist_ok=True)
    changed = False
    for name in UNITS.values():
        path = folder / f"{name}.container"
        text = wanted.get(path.name)
        if text is None:
            if path.exists():
                path.unlink()
                changed = True
        elif not path.exists() or path.read_text() != text:
            path.write_text(text)
            changed = True
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


def preflight(config: Config) -> None:
    if not image_exists():
        raise ConfigError(f"no image yet ({IMAGE}): run `sarathi image` first")
    key = KEY_NAMES.get(config.provider)
    if key and key not in read_secrets():
        raise ConfigError(f"no {key} in {secrets_path()}: on the podman road keys come "
                          "only from there (a unit does not see your shell); "
                          "`sarathi init --force --podman` saves it")
    ours = [name for name, r in records().items() if alive(r["pid"])]
    if ours:
        raise ConfigError(f"{', '.join(ours)} still running as plain processes: "
                          "`sarathi down` on the process road first")


def up(config: Config) -> tuple[list[str], bool]:
    preflight(config)
    for folder in data_dirs():
        folder.mkdir(parents=True, exist_ok=True)
    lines = ["units rewritten from sarathi.toml"] if install(units(config)) else []
    if not config.clock_on:
        lines.append("clock  off in sarathi.toml")
    ok = True
    wanted = [("clock", config.clock_port)] if config.clock_on else []
    wanted.append(("page", config.web_port))
    for name, port in wanted:
        unit = UNITS[name]
        url = f"http://127.0.0.1:{port}/"
        if active(unit):
            address = (clock_address(config) if name == "clock" else None) or url
            lines.append(f"{name:<6} already running at {address}  (unit {unit})")
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
            address = (clock_address(config) if name == "clock" else None) or url
            lines.append(f"{name:<6} up at {address}  (unit {unit})")
            continue
        ok = False
        lines.append(f"{name:<6} did not come up (unit {unit}); the end of its journal:")
        lines += [f"         | {line}" for line in journal_tail(unit)]
    return lines, ok


def down(remove: bool = False) -> list[str]:
    """Stop the units. They stay installed -- and so start again at the
    next login, which is what they are for -- unless ``remove``."""
    lines = []
    for name in ("page", "clock"):
        unit = UNITS[name]
        if not (unit_dir() / f"{unit}.container").exists():
            continue
        if active(unit):
            run(["systemctl", "--user", "stop", f"{unit}.service"])
            lines.append(f"{name:<6} stopped  (unit {unit})")
        else:
            lines.append(f"{name:<6} was not running  (unit {unit})")
    if not lines:
        return ["no Sarathi units are installed"]
    if remove:
        install({})
        lines.append("units removed: nothing starts at login until the next `sarathi up`")
    else:
        lines.append("they start again at your next login "
                     "(`sarathi down --remove` to stop that too)")
    return lines


def running(config: Config) -> list[dict]:
    out = []
    for name, port in (("clock", config.clock_port), ("page", config.web_port)):
        unit = UNITS[name]
        if not (unit_dir() / f"{unit}.container").exists():
            continue
        live = active(unit)
        address = (clock_address(config) if live and name == "clock" else None) or \
            f"http://127.0.0.1:{port}/"
        out.append({"name": name, "unit": unit, "alive": live, "address": address,
                    "log": [] if live else journal_tail(unit)})
    return out
