"""`sarathi doctor`: what's wrong, in plain words, and the line that fixes it.

`sarathi status` says what each piece is doing. The question a person
has when something stops working is different: *what's broken, and
what do I type?* A phone that can't open a page, an image built before
yesterday's fix, a Gmail sign-in Google ended, a schedule that failed
at 08:00 -- each of those is already known to some program here, and
each is otherwise found only by the thing it breaks.

So the doctor reads, it doesn't guess. Every line comes from a program
that knows: each sibling's own ``status --json`` (Setu's expired
sign-ins, Samay's failed runs of the last day, Sparsh's phones and the
iPhone's signature, Yantra's model and how much it really holds, Dvara's
problems), what ``up`` started and whether it is still running, Podman's
image against each checkout's last commit, the firewall, and the disk.

GREEN, AMBER, RED, AND NOTHING CHANGED. Red is broken now: something
you rely on doesn't work until it's fixed. Amber is worth a look: it
works, or nobody can tell from here, and it may not tomorrow. Green is
fine. Every red and amber line carries its fix as a command or a place
to click, and the doctor runs none of them: opening a port needs root,
a rebuild takes minutes, a sign-in needs the person. It exits 1 when
anything is red, so a script can ask it too.

A BUTTON ONLY WHERE THE PAGE CAN ALREADY DO IT. On the home page's Check
tab a line may carry ``act``: start everything again (Apply), rebuild
the image and start again, set ``context_window`` to what the model
holds, bring a Wi-Fi phone back from its cable, open Setu's page to
sign in. Each is a button the page already had somewhere, offered where
the problem is said, and pressed by the person. Nothing that needs root
or a Mac gets one.

A GOOGLE SIGN-IN'S END, BEFORE IT HAPPENS. Setu says the day each
Google sign-in will end (an app in Testing: 7 days after it was made),
and in its last three days that's an amber line here.

WHAT'S NEW SINCE THE LAST MORNING. Samay's doctor road asks with
``news``: the answer then also says which red and amber lines weren't
there last time (``new``) and which are gone (``gone``), and the doctor
remembers this answer for the next. A phone left unplugged all week is
told once.

WHAT IT CAN'T SEE, IT SAYS. ufw's rules are root's to read; the doctor
tries ``sudo -n`` (which never asks for a password) and, when that
can't, says so in amber with the line to run, instead of guessing
"open". A Google sign-in's end is known only by using it, which Setu
does once a day; the doctor reports Setu's mark, not a new try.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sarathi.siblings import NOT_ASKED, Found, env_name

FORMAT = "sarathi.doctor.v1"
LEVELS = ("red", "amber", "green")

#: Below this, a local model's window is small for tools plus a talk.
SMALL_WINDOW = 16384
#: Free space under which something will soon fail to write.
DISK_RED, DISK_AMBER = 2 * 1024**3, 10 * 1024**3
#: A model holding this many times what Yantra plans for is room unused
#: (64000 planned on a 65536 model is the docs' own advice, not a waste).
ROOM = 1.25
#: The iPhone's signature, this close to its end, is worth a look.
WDA_DAYS = 3.0
#: A Google sign-in this close to its end (an app in Testing) too.
SIGN_IN_DAYS = 3.0
UP = {"do": "up", "label": "Start everything again"}
SETU_PAGE = {"do": "page", "page": "setu", "label": "Open Setu's page"}


@dataclass
class Line:
    level: str          # red | amber | green
    about: str          # the piece: "setu", "image", "firewall"
    said: str           # what is the matter, in plain words
    fix: str = ""       # what to type or click; "" for green
    #: The page's button for it, when the page can do the fix itself:
    #: {"do": "up"|"image"|"window"|"phone"|"page", "label", ...}.
    act: dict | None = None

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Probes:
    """Everything the doctor asks of this computer beyond the siblings'
    own answers, as functions, so a test hands in its own world."""

    image: Callable[[Any], dict | None] = lambda config: image_state(config)
    firewall: Callable[[Any], dict | None] = lambda config: firewall_state(config)
    disk: Callable[[Path], int] = lambda path: shutil.disk_usage(path).free
    disk_paths: Callable[[], list[Path]] = field(default=lambda: disk_paths())


def examine(config: Any, found: list[Found], started: list[dict],
            memory: dict | None, probes: Probes | None = None) -> list[Line]:
    """Every line, red first."""
    probes = probes or Probes()
    lines: list[Line] = []
    if config is None:
        lines.append(Line("red", "sarathi", "there is no sarathi.toml yet, so nothing "
                          "here knows which model to ask", "sarathi init"))
    for f in found:
        lines += _sibling(f, config)
    lines += _started(started, config)
    if config is not None:
        if config.road == "podman":
            lines += _image(probes.image(config))
        lines += _firewall(probes.firewall(config))
        lines += _memory(config, memory)
    lines += _disk(probes)
    return sorted(lines, key=lambda line: LEVELS.index(line.level))


def report(lines: list[Line]) -> dict[str, Any]:
    counts = {level: sum(1 for line in lines if line.level == level) for level in LEVELS}
    return {"format": FORMAT, "ok": counts["red"] == 0, **counts,
            "lines": [line.as_json() for line in lines]}


def news(answer: dict[str, Any], told: Path) -> dict[str, Any]:
    """``answer`` with ``news``: its red and amber lines that weren't in the
    last answer kept at ``told``, and the ones gone since; this answer is
    kept there for the next time. A first time has everything new."""
    def key(line: dict) -> tuple[str, str]:
        return (line.get("about", ""), line.get("said", ""))
    bad = [line for line in answer.get("lines", []) if line.get("level") != "green"]
    try:
        before = json.loads(told.read_text())
    except (OSError, ValueError):
        before = []
    before = before if isinstance(before, list) else []
    was = {key(line) for line in before if isinstance(line, dict)}
    now = {key(line) for line in bad}
    told.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    staged = told.with_suffix(".tmp")
    staged.write_text(json.dumps(bad))
    os.replace(staged, told)
    return {**answer, "news": {
        "new": [line for line in bad if key(line) not in was],
        "gone": [line for line in before if isinstance(line, dict) and key(line) not in now]}}


MARK = {"red": "✗ needs fixing", "amber": "! worth a look", "green": "✓ fine"}
COLOUR = {"red": "\033[31m", "amber": "\033[33m", "green": "\033[32m"}


def text(lines: list[Line], colour: bool = False) -> str:
    counts = report(lines)
    head = (f"{counts['red']} to fix, {counts['amber']} worth a look, "
            f"{counts['green']} fine")
    out = [head, ""]
    for line in lines:
        mark = MARK[line.level]
        if colour:
            mark = f"{COLOUR[line.level]}{mark}\033[0m"
        out.append(f"{mark}  {line.about}: {line.said}")
        if line.fix:
            out.append(f"      fix: {line.fix}")
    return "\n".join(out)


# ---- what each sibling says ------------------------------------------------------


def _sibling(f: Found, config: Any) -> list[Line]:
    s = f.sibling
    if f.program is None:
        if s.optional:
            return []
        return [Line("red", s.name, f"not found on this computer ({s.role})",
                     f"install it, or set {env_name(s)}=/path/to/{s.program}")]
    if f.error:
        return [Line("red", s.name, f"found, but it didn't answer: {f.error}",
                     f"{f.program} status")]
    if f.said == NOT_ASKED or f.status is None:
        return []
    read = READERS.get(s.name)
    return read(f.status, config) if read else []


def _yantra(data: dict, config: Any) -> list[Line]:
    lines = [Line("red", "model", problem, _model_fix(problem),
                  act=_window(_held(problem)) if _held(problem) else None)
             for problem in data.get("problems") or []]
    provider, model = data.get("provider"), data.get("model")
    local = data.get("local") or {}
    if provider == "ollama" and local.get("answering") and local.get("pulled"):
        holds, plans = local.get("holds"), data.get("context_window")
        if holds is None:
            lines.append(Line(
                "amber", "model", f"Ollama doesn't say how many tokens {model} holds, so "
                f"its own default applies -- often less than the {plans} Yantra plans "
                f"for, and past it the start of a talk (the tools first) is dropped "
                f"without a word",
                "use a model made with a num_ctx (as qwen3.8-64k is), and set "
                "[model] context_window to it in Settings → Sarathi"))
        elif holds < SMALL_WINDOW:
            lines.append(Line(
                "amber", "model", f"{model} holds {holds} tokens: a connection with many "
                f"tools (Notion brings 65) and a long talk may not fit",
                "a model made with num_ctx 65536, then [model] context_window = 65536"))
        elif plans and holds > plans * ROOM:
            lines.append(Line(
                "amber", "model", f"{model} holds {holds} tokens but Yantra plans for "
                f"{plans}, so long talks are shortened sooner than they need to be",
                f"Settings → Sarathi → [model] context_window = {holds}",
                act=_window(holds)))
        if not any(line.level != "green" for line in lines):
            lines.append(Line("green", "model", f"{model} is pulled and answering"
                              + (f"; it holds {holds} tokens" if holds else "")))
    elif provider and not lines:
        lines.append(Line("green", "model", f"{provider} {model} (a cloud model isn't "
                          f"tried here: that costs a call)"))
    return lines


def _held(problem: str) -> int | None:
    """The tokens a "holds N tokens but Yantra plans for M" problem names."""
    if "OLLAMA_CONTEXT_WINDOW=" not in problem:
        return None
    said = problem.split("OLLAMA_CONTEXT_WINDOW=", 1)[1].split(",")[0].strip()
    return int(said) if said.isdigit() else None


def _window(tokens: int) -> dict:
    return {"do": "window", "value": tokens, "label": f"Set it to {tokens} and restart"}


def _model_fix(problem: str) -> str:
    if "ollama serve" in problem:
        return "ollama serve (or: systemctl start ollama)"
    if "ollama pull" in problem:
        return "ollama pull " + problem.split("ollama pull ", 1)[1].rstrip(")")
    if "OLLAMA_CONTEXT_WINDOW=" in problem:
        holds = problem.split("OLLAMA_CONTEXT_WINDOW=", 1)[1].split(",")[0]
        return f"Settings → Sarathi → [model] context_window = {holds}"
    return ""


def _setu(data: dict, config: Any) -> list[Line]:
    rows = data.get("connections") or []
    lines = [Line("red", "setu", f"{c.get('ref')}: the sign-in stopped working "
                  f"(the site ended it); your agents can't use it",
                  f"setu connect {c.get('connector')} --as {c.get('account')}, "
                  f"or sign in again on Setu's page", act=SETU_PAGE)
             for c in rows if c.get("expired")]
    now = time.time()
    for c in rows:
        end = _epoch(c.get("ends"))
        if c.get("expired") or end is None or end - now > SIGN_IN_DAYS * 86400:
            continue
        when = time.strftime("%a %d %b %H:%M", time.localtime(end))
        lines.append(Line(
            "amber", "setu", f"{c.get('ref')}: Google ends this sign-in {when} (an app "
            f"in Testing signs you out 7 days after you sign in)",
            f"sign in again before then: setu connect {c.get('connector')} --as "
            f"{c.get('account')}; or publish the Google app, then `setu config "
            f"google-published on`", act=SETU_PAGE))
    lines += [Line("amber", "setu", str(p), "") for p in data.get("problems") or []]
    if not lines:
        lines.append(Line("green", "setu", f"{len(rows)} account"
                          f"{'s' * (len(rows) != 1)}, none marked stopped "
                          f"(Setu tries each sign-in once a day)"))
    return lines


def _samay(data: dict, config: Any) -> list[Line]:
    if config is not None and not config.clock_on:
        return []
    if not data.get("serving"):
        return [Line("red", "samay", "Samay isn't running: nothing scheduled runs",
                     "sarathi up", act=UP)]
    recent = data.get("recent") or {}
    lines = [Line("amber", "samay",
                  f"a schedule {row.get('outcome', 'failed').replace('_', ' ')} at "
                  f"{_when(row.get('at'))}: \"{row.get('prompt')}\""
                  + (f" -- {row['summary']}" if row.get("summary") else ""),
                  "Samay's page (Your pages) shows the run and its schedule")
             for row in recent.get("named") or []]
    more = int(recent.get("failed") or 0) - len(lines)
    if more > 0:
        lines.append(Line("amber", "samay", f"and {more} more failed runs in the last "
                          f"{recent.get('hours', 24)} hours", "Samay's page"))
    if not lines:
        runs = recent.get("runs")
        lines.append(Line("green", "samay", "Samay is running" + (
            f"; {runs} run{'s' * (runs != 1)} in the last day, none failed"
            if isinstance(runs, int) else "")))
    return lines


def _prahari(data: dict, config: Any) -> list[Line]:
    if config is not None and not getattr(config, "watch_on", True):
        return []
    if not data.get("serving"):
        return [Line("red", "prahari", "Prahari isn't running: no watch looks or "
                     "hears a knock", "sarathi up", act=UP)]
    return [Line("green", "prahari", "Prahari is watching")]


def _dvara(data: dict, config: Any) -> list[Line]:
    lines = [Line("amber", "dvara", str(p), "") for p in data.get("problems") or []]
    if not data.get("serving"):
        lines.insert(0, Line("red", "dvara", "Dvara isn't serving: Telegram and the "
                             "home page's chat get no answer", "sarathi up", act=UP))
    elif not lines:
        lines.append(Line("green", "dvara", "Dvara is serving"))
    return lines


def _sparsh(data: dict, config: Any) -> list[Line]:
    lines = []
    phones = {p.get("serial"): p for p in data.get("phones") or []}
    for each in data.get("named") or []:
        if not isinstance(each, dict) or not each.get("name"):
            continue
        phone = phones.get(each.get("where")) or {}
        if phone.get("state") == "device":
            lines.append(Line("green", "phone", f"{each['name']} is connected"))
            continue
        iphone = each.get("kind") == "iPhone"
        lines.append(Line(
            "amber", "phone", f"{each['name']} isn't connected"
            + (f": {phone['note']}" if phone.get("note") else ""),
            "plug it in, unlock it, then `sparsh iphone`" if iphone else
            "plug it in by cable, then Bring it back (or `sparsh tcpip`)",
            act=None if iphone else {"do": "phone", "name": each["name"],
                                     "label": "Bring it back (plugged in first)"}))
    wda = data.get("wda") or {}
    left = wda.get("days_left")
    if isinstance(left, (int, float)) and left <= 0:
        lines.append(Line("red", "phone", "the iPhone's WebDriverAgent signature ran "
                          "out: the iPhone can't be worked until it's rebuilt",
                          "on the Mac: ./build-wda-on-mac.sh, then `sparsh iphone WDA.ipa`"))
    elif isinstance(left, (int, float)) and left < WDA_DAYS:
        lines.append(Line("amber", "phone", wda.get("note") or "the iPhone's "
                          "signature runs out soon",
                          "on the Mac: ./build-wda-on-mac.sh, then `sparsh iphone WDA.ipa`"))
    if data.get("adb") not in (None, "ok"):
        lines.append(Line("amber", "phone", str(data["adb"]), ""))
    return lines


READERS: dict[str, Callable[[dict, Any], list[Line]]] = {
    "yantra": _yantra, "setu": _setu, "samay": _samay, "prahari": _prahari,
    "dvara": _dvara, "sparsh": _sparsh}


def _epoch(at: Any) -> float | None:
    if not at:
        return None
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(at)).timestamp()
    except ValueError:
        return None


def _when(at: str | None) -> str:
    if not at:
        return "some time today"
    try:
        from datetime import datetime

        return datetime.fromisoformat(at).astimezone().strftime("%a %H:%M")
    except ValueError:
        return at


# ---- what `up` started -----------------------------------------------------------


def _started(started: list[dict], config: Any) -> list[Line]:
    if config is None:
        return []
    if not started:
        return [Line("amber", "running", "nothing `sarathi up` starts is running",
                     "sarathi up")]
    lines = []
    for row in started:
        if row.get("alive"):
            continue
        last = next((x for x in reversed(row.get("log") or []) if x.strip()), "")
        lines.append(Line("red", row["name"], "stopped" + (f"; its log ends: {last.strip()}"
                                                          if last else ""),
                          "sarathi up (`sarathi status` shows the end of its log)",
                          act=UP))
    alive = sum(1 for row in started if row.get("alive"))
    if alive:
        lines.append(Line("green", "running", f"{alive} of {len(started)} pieces "
                          f"`sarathi up` started are running"))
    return lines


# ---- the image, on the podman road -----------------------------------------------


def image_state(config: Any) -> dict | None:
    """The image's age against each checkout's last commit, and the
    containers still on an older image."""
    from sarathi import podman

    if not podman.image_exists():
        return {"exists": False}
    created = podman.run(["podman", "image", "inspect", podman.IMAGE, "--format",
                          "{{.Created.Unix}}"]).stdout.strip()
    try:
        made = int(created)
    except ValueError:
        return None
    newer = []
    try:
        repos = podman.checkouts()
    except Exception:
        repos = {}
    memory = config.smritikosh.path() if config is not None else None
    if memory is not None and (memory / ".git").exists():
        repos[podman.MEMORY_CHECKOUT] = memory
    for name, repo in repos.items():
        said = podman.run(["git", "-C", str(repo), "log", "-1",
                           "--format=%h %ct"]).stdout.split()
        if len(said) == 2 and said[1].isdigit() and int(said[1]) > made:
            newer.append(f"{name} {said[0]}")
    newest = podman.image_id(podman.IMAGE)
    behind = []
    for name, unit in podman.UNITS.items():
        if name in podman.SERVICE_UNITS + podman.OWN_IMAGE or not podman.active(unit):
            continue
        # only containers made from Sarathi's image: the memory store's
        # databases run their own (Postgres, Neo4j), which `image` never builds
        made_from = podman.run(["podman", "container", "inspect", unit, "--format",
                                "{{.ImageName}}"]).stdout.strip()
        if made_from == podman.IMAGE and podman.image_id(unit) not in ("", newest):
            behind.append(name)
    return {"exists": True, "made": made, "newer": newer, "behind": behind}


def _image(state: dict | None) -> list[Line]:
    if state is None:
        return [Line("amber", "image", "Podman didn't say when the image was built", "")]
    if not state.get("exists"):
        return [Line("red", "image", "there is no image yet, and the podman road runs "
                     "everything from it", "sarathi image",
                     act={"do": "image", "label": "Build it and start everything"})]
    lines = []
    if state.get("newer"):
        lines.append(Line("amber", "image", "the image is older than the code: "
                          + ", ".join(state["newer"]) + " came after it",
                          "sarathi image && sarathi up",
                          act={"do": "image", "label": "Rebuild and restart (minutes)"}))
    if state.get("behind"):
        lines.append(Line("amber", "image", "still running an older image: "
                          + ", ".join(state["behind"]), "sarathi up (it restarts them)",
                          act=UP))
    if not lines:
        built = time.strftime("%a %d %b %H:%M", time.localtime(state["made"]))
        lines.append(Line("green", "image", f"built {built}, newer than every checkout"))
    return lines


# ---- the firewall, for phones on the house network ------------------------------


def firewall_state(config: Any) -> dict | None:
    """None when no page is published beyond this computer; else which
    firewall, the ports, and which of them it lets in (None: can't read)."""
    from sarathi import podman

    shown = podman.house_ports(config)
    if shown is None:
        return None
    host, ports = shown
    wall = podman.firewall()
    state = {"host": host, "ports": ports, "wall": wall, "open": None,
             "command": "\n".join(podman.firewall_note(config)[1:]).strip()}
    if wall == "ufw":
        said = _quiet(["sudo", "-n", "ufw", "status"])
        state["open"] = ufw_open(said) if said is not None else None
    elif wall == "firewalld":
        said = _quiet(["firewall-cmd", "--list-ports"])
        state["open"] = ({int(p.split("/")[0]) for p in said.split()
                          if p.split("/")[0].isdigit()} if said is not None else None)
    return state


def _quiet(argv: list[str]) -> str | None:
    """A command's output, or None when it can't run without asking."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=5,
                              check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def ufw_open(said: str) -> set[int]:
    """Ports ``ufw status`` lets in: "8770,8775/tcp", "8790:8799/tcp"."""
    found: set[int] = set()
    for line in said.splitlines():
        if "ALLOW" not in line:
            continue
        first = line.split()[0].split("/")[0]
        for part in first.split(","):
            low, _, high = part.partition(":")
            if low.isdigit() and (not high or high.isdigit()):
                found.update(range(int(low), int(high or low) + 1))
    return found


def _firewall(state: dict | None) -> list[Line]:
    if state is None:
        return []
    ports = state["ports"]
    if state["wall"] is None:
        return [Line("green", "firewall", "no firewall is on, so phones in the house "
                     "reach the pages")]
    if state["open"] is None:
        return [Line("amber", "firewall", f"{state['wall']} is on, and its rules need root "
                     f"to read; if a phone can't open a page on {state['host']}, these "
                     f"ports are shut: {', '.join(map(str, ports))}", state["command"])]
    shut = [p for p in ports if p not in state["open"]]
    if shut:
        return [Line("red", "firewall", f"{state['wall']} keeps phones in the house off "
                     f"{', '.join(map(str, shut))}: those pages just spin on a phone",
                     state["command"])]
    return [Line("green", "firewall", f"{state['wall']} lets the house reach every page")]


# ---- memory and disk -------------------------------------------------------------


def _memory(config: Any, memory: dict | None) -> list[Line]:
    if memory is None or not config.remembers_in_smritikosh:
        return []
    if memory.get("up") is False:
        return [Line("red", "memory", "Smritikosh isn't answering: nothing is remembered "
                     "or recalled", "sarathi up", act=UP)]
    return [Line("green", "memory", "Smritikosh is answering")]


def disk_paths() -> list[Path]:
    home = Path.home()
    paths = [home]
    containers = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share") \
        / "containers"
    if containers.exists():
        paths.append(containers)
    return paths


def _disk(probes: Probes) -> list[Line]:
    seen: dict[int, tuple[int, Path]] = {}      # one line per disk
    for path in probes.disk_paths():
        try:
            seen.setdefault(os.stat(path).st_dev, (probes.disk(path), path))
        except OSError:
            continue
    lines = []
    for free, path in seen.values():
        size = f"{free / 1024**3:.1f} GB free where {path} is"
        if free < DISK_RED:
            lines.append(Line("red", "disk", size + ": logs, pictures and sign-ins "
                              "will fail to save", "free some space (podman image prune "
                              "clears old images)"))
        elif free < DISK_AMBER:
            lines.append(Line("amber", "disk", size, "podman image prune clears old images"))
        else:
            lines.append(Line("green", "disk", size))
    return lines
