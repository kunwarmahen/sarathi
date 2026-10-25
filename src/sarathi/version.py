"""`sarathi version`: which code is running here, project by project.

"Is my fix in there?" is a question about commits, so a version here is
worked out from them, never bumped by hand: ``YEAR.MONTH.DAY.N``, the day
of the last commit (in the time zone it was made in) and N the commits
made that day up to it. ``2026.10.25.3`` is the third commit of 25
October; the commit beside it says exactly which. Each sibling's
``--version`` and ``status --json`` say the same (their own version.py),
and Sarathi's does here.

ON THE PODMAN ROAD, THE IMAGE SAYS. ``sarathi image`` builds from each
checkout's committed code (podman.py), and it writes down what it built
from as a label on the image (``sarathi.build``): each project's commit,
and how many uncommitted changes were left out. Reading it back needs no
container started, and it stays true however much the checkouts move on
after. Against it, each checkout's commit now: "3 newer" means three
commits since the build, which the next ``sarathi image`` takes in. A
container still on an older image than the newest built is named too:
``sarathi up`` restarts it on the new one. An image built before images
carried the label says only when it was built. The image has no git,
so the build also writes a ``VERSION`` file at the top of each project
in it (``YEAR.MONTH.DAY.N COMMIT``), which each program's own
``--version`` reads there.

ON THE PLAIN-PROGRAMS ROAD, THE CHECKOUTS SAY. Each program runs from its
checkout, so what runs is what is checked out, uncommitted changes and
all. A program started before your last commit still runs the code it
started with until ``sarathi down && sarathi up``.

SARATHI ITSELF runs from its own checkout on both roads (the home page
is a user service, not a container), so its line is that checkout.

    sarathi version          the lines
    sarathi version --json   the same, as sarathi.version.v1

The home page's Settings → Check shows the same, and its footer the
first line.
"""

from __future__ import annotations

import argparse
import functools
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from sarathi import __version__, podman
from sarathi.siblings import SIBLINGS, beside_dir

FORMAT = "sarathi.version.v1"
#: The image's label holding what it was built from.
LABEL = "sarathi.build"
BUILD_FORMAT = "sarathi.build.v1"


#: Commits looked back through to count a day's (the siblings' version.py).
LOOK = 500


def _git(argv: list[str]) -> subprocess.CompletedProcess:
    """git, or a failed answer where there is no git (an install with none)."""
    try:
        return podman.run(argv)
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


def dated(repo: Path, rev: str = "HEAD") -> str | None:
    """``YEAR.MONTH.DAY.N`` of a commit: its day, and its place in that day."""
    said = _git(["git", "-C", str(repo), "log", f"-{LOOK}", "--format=%cd",
                       "--date=format:%Y.%m.%d", rev])
    days = said.stdout.split()
    if said.returncode != 0 or not days:
        return None
    count = next((i for i, day in enumerate(days) if day != days[0]), len(days))
    return f"{days[0]}.{count}"


def commit(repo: Path) -> dict[str, Any] | None:
    """A checkout's last commit, its version, and its uncommitted
    changes, or None when it isn't a git checkout."""
    said = _git(["git", "-C", str(repo), "log", "-1", "--format=%h%x00%ct%x00%s"])
    parts = said.stdout.strip().split("\0")
    if said.returncode != 0 or len(parts) != 3 or not parts[1].isdigit():
        return None
    dirty = _git(["git", "-C", str(repo), "status", "--porcelain"]).stdout
    return {"commit": parts[0], "version": dated(repo) or "", "date": int(parts[1]),
            "subject": parts[2], "left_out": len(dirty.splitlines())}


def newer(repo: Path, since: str) -> int | None:
    """Commits in the checkout after ``since``; None when the checkout
    doesn't have it (another branch, or history rewritten)."""
    said = _git(["git", "-C", str(repo), "rev-list", "--count", f"{since}..HEAD"])
    out = said.stdout.strip()
    return int(out) if said.returncode == 0 and out.isdigit() else None


def build_label(found: dict[str, Path]) -> dict[str, Any]:
    """What ``sarathi image`` writes on the image: each checkout's commit."""
    # no time here: the image's own Created says when, and the same
    # commits make the same label
    return {"format": BUILD_FORMAT, "sarathi": __version__,
            "projects": {name: c for name, repo in found.items()
                         if (c := commit(repo)) is not None}}


def image_build(ref: str = podman.IMAGE) -> dict[str, Any] | None:
    """(when it was made, what it was built from) of an image, or None
    when there is no such image. ``projects`` is empty for an image built
    before the label."""
    said = podman.run(["podman", "image", "inspect", ref, "--format",
                       "{{.Created.Unix}} {{json .Labels}}"])
    made, _, labels = said.stdout.strip().partition(" ")
    if said.returncode != 0 or not made.isdigit():
        return None
    try:
        stamp = json.loads(((json.loads(labels or "null") or {}).get(LABEL)) or "{}")
    except (ValueError, AttributeError):
        stamp = {}
    if not isinstance(stamp, dict) or stamp.get("format") != BUILD_FORMAT:
        stamp = {}
    return {"made": int(made), "projects": stamp.get("projects") or {}}


def checkouts(config: Any) -> dict[str, Path]:
    """Every project's checkout that is here: beside this one, and
    Smritikosh where sarathi.toml says."""
    root = beside_dir()
    found = {}
    for sibling in SIBLINGS:
        repo = root / sibling.name if root is not None else None
        if repo is not None and (repo / ".git").exists():
            found[sibling.name] = repo
    memory = config.smritikosh.path() if config is not None else None
    if memory is not None and (memory / ".git").exists():
        found[podman.MEMORY_CHECKOUT] = memory
    return found


def own_checkout() -> Path | None:
    here = Path(__file__).resolve().parents[2]
    return here if (here / ".git").exists() else None


@functools.lru_cache(maxsize=1)
def own() -> tuple[str, str]:
    """(version, commit) of this Sarathi: its checkout's, ``+dirty`` with
    uncommitted changes; else the package's own number and no commit."""
    mine = own_checkout()
    found = commit(mine) if mine else None
    if not found or not found["version"]:
        return __version__, ""
    dirty = _git(["git", "-C", str(mine), "status", "--porcelain",
                        "--untracked-files=no"]).stdout.strip()
    return found["version"] + ("+dirty" if dirty else ""), found["commit"]


def own_line() -> str:
    number, at = own()
    return f"{number} ({at})" if at else number


class Show(argparse.Action):
    """``sarathi --version``, worked out only when asked."""

    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS,
                 help="the version: the day of the last commit, that day's count, "
                      "and the commit"):
        super().__init__(option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        sys.stdout.write(f"{parser.prog} {own_line()}\n")      # where argparse's own prints
        parser.exit()


def behind() -> list[str]:
    """Containers from Sarathi's image still on an older one than the newest."""
    newest = podman.image_id(podman.IMAGE)
    out = []
    for name, unit in podman.UNITS.items():
        if name in podman.SERVICE_UNITS + podman.OWN_IMAGE or not podman.active(unit):
            continue
        made_from = podman.run(["podman", "container", "inspect", unit, "--format",
                                "{{.ImageName}}"]).stdout.strip()
        if made_from == podman.IMAGE and podman.image_id(unit) not in ("", newest):
            out.append(name)
    return out


def report(config: Any) -> dict[str, Any]:
    """sarathi.version.v1: the road, the image (podman road), and each
    project's running commit against its checkout's now."""
    road = getattr(config, "road", "process")
    repos = checkouts(config)
    image = None
    built: dict[str, Any] = {}
    if road == "podman":
        found = image_build()
        if found is None:
            image = {"exists": False}
        else:
            built = found["projects"]
            image = {"exists": True, "made": found["made"], "stamped": bool(built),
                     "behind": behind()}
    projects = []
    names = list(dict.fromkeys([*repos, *built]))
    for name in names:
        repo = repos.get(name)
        now = commit(repo) if repo is not None else None
        if road == "podman":
            running = built.get(name)
            if running and not running.get("version") and repo is not None:
                # an image from before versions were stamped: its commit says
                running = {**running, "version": dated(repo, running["commit"]) or ""}
            count = newer(repo, running["commit"]) \
                if running and repo is not None and now else None
        else:
            running, count = now, 0
        projects.append({"name": name, "running": running, "now": now, "newer": count})
    mine = own_checkout()
    projects.append({"name": "sarathi", "running": commit(mine) if mine else None,
                     "now": None, "newer": None, "here": True})
    return {"format": FORMAT, "sarathi": own()[0], "road": road, "image": image,
            "projects": projects}


def _day(unix: int) -> str:
    return time.strftime("%a %d %b %H:%M", time.localtime(unix))


def headline(got: dict[str, Any]) -> str:
    """The first line: the page's footer says this one."""
    image = got.get("image")
    if got["road"] != "podman":
        return f"Sarathi {got['sarathi']}, plain programs from their checkouts"
    if not image or not image.get("exists"):
        return f"Sarathi {got['sarathi']}, containers, but no image built yet"
    return f"Sarathi {got['sarathi']}, containers from the image of {_day(image['made'])}"


def text(got: dict[str, Any]) -> str:
    lines = [headline(got)]
    image = got.get("image") or {}
    if image.get("exists") and not image.get("stamped"):
        lines.append("  built before images said their commits: `sarathi image` once "
                     "to see them")
    if image.get("behind"):
        lines.append(f"  still on an older image: {', '.join(image['behind'])} "
                     "(sarathi up restarts them)")
    unstamped = image.get("exists") and not image.get("stamped")
    for p in got["projects"]:
        run = p["running"]
        if run is None:
            if unstamped and p["now"]:
                lines.append(f"  {p['name']:<11}?        the checkout is on "
                             f"{p['now']['commit']} now")
            else:
                lines.append(f"  {p['name']:<11}"
                             + ("not in the image" if got["road"] == "podman"
                                else "no checkout"))
            continue
        subject = run["subject"] if len(run["subject"]) <= 50 else run["subject"][:49] + "…"
        line = (f"  {p['name']:<11}{run.get('version') or '?':<14}{run['commit']:<9}"
                f"{subject}")
        if run.get("left_out"):
            line += (f"  ({run['left_out']} uncommitted change(s) left out)"
                     if got["road"] == "podman" and not p.get("here") else
                     f"  (+{run['left_out']} uncommitted change(s))")
        if p.get("newer"):
            line += f"  -- {p['newer']} newer in the checkout"
        elif got["road"] == "podman" and p["now"] and p["newer"] is None and not p.get("here"):
            line += f"  -- the checkout is on {p['now']['commit']}, not after it"
        lines.append(line)
    if any(p.get("newer") for p in got["projects"]):
        lines.append("the next `sarathi image && sarathi up` takes in the newer commits")
    return "\n".join(lines)
