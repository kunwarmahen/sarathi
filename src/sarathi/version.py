"""`sarathi version`: which code is running here, project by project.

"Is my fix in there?" is a question about commits, and every project
here says ``0.1.0``. So the version Sarathi shows is each project's last
commit: its short id, its day and its first line.

ON THE PODMAN ROAD, THE IMAGE SAYS. ``sarathi image`` builds from each
checkout's committed code (podman.py), and it writes down what it built
from as a label on the image (``sarathi.build``): each project's commit,
and how many uncommitted changes were left out. Reading it back needs no
container started, and it stays true however much the checkouts move on
after. Against it, each checkout's commit now: "3 newer" means three
commits since the build, which the next ``sarathi image`` takes in. A
container still on an older image than the newest built is named too:
``sarathi up`` restarts it on the new one. An image built before images
carried the label says only when it was built.

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

import json
import time
from pathlib import Path
from typing import Any

from sarathi import __version__, podman
from sarathi.siblings import SIBLINGS, beside_dir

FORMAT = "sarathi.version.v1"
#: The image's label holding what it was built from.
LABEL = "sarathi.build"
BUILD_FORMAT = "sarathi.build.v1"


def commit(repo: Path) -> dict[str, Any] | None:
    """A checkout's last commit and its uncommitted changes, or None
    when it isn't a git checkout."""
    said = podman.run(["git", "-C", str(repo), "log", "-1", "--format=%h%x00%ct%x00%s"])
    parts = said.stdout.strip().split("\0")
    if said.returncode != 0 or len(parts) != 3 or not parts[1].isdigit():
        return None
    dirty = podman.run(["git", "-C", str(repo), "status", "--porcelain"]).stdout
    return {"commit": parts[0], "date": int(parts[1]), "subject": parts[2],
            "left_out": len(dirty.splitlines())}


def newer(repo: Path, since: str) -> int | None:
    """Commits in the checkout after ``since``; None when the checkout
    doesn't have it (another branch, or history rewritten)."""
    said = podman.run(["git", "-C", str(repo), "rev-list", "--count", f"{since}..HEAD"])
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
            count = newer(repo, running["commit"]) \
                if running and repo is not None and now else None
        else:
            running, count = now, 0
        projects.append({"name": name, "running": running, "now": now, "newer": count})
    mine = own_checkout()
    projects.append({"name": "sarathi", "running": commit(mine) if mine else None,
                     "now": None, "newer": None, "here": True})
    return {"format": FORMAT, "sarathi": __version__, "road": road, "image": image,
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
        subject = run["subject"] if len(run["subject"]) <= 60 else run["subject"][:59] + "…"
        line = (f"  {p['name']:<11}{run['commit']:<9}"
                f"{time.strftime('%d %b', time.localtime(run['date']))}  {subject}")
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
