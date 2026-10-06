"""Five programs, found -- and each one asked what it is doing.

Sarathi puts together projects that were each built to stand alone:
Yantra (the agent), Setu (your accounts), Dvara (many people behind one
door), Samay (the clock) and Smritikosh (a memory store). Before it can
start any of them it has to answer a plainer question: which of them are
on this machine, where, and what does each say about itself?

A PROGRAM, NOT AN IMPORT. Every sibling lives in its own environment with
its own dependencies -- Setu usually in ``~/.local/bin``, the others in
their checkouts' ``.venv``. Importing them into one Python would force
them into one set of versions. So Sarathi finds each as a program and,
where the sibling offers one, runs its ``status --json`` and reads the
JSON. The ``format`` field is the whole contract: an unknown format is
refused rather than guessed at, the same rule Yantra applies to Setu and
Samay.

WHERE TO LOOK, IN ORDER:

    SARATHI_<NAME>    a path you set (SARATHI_SAMAY=/opt/samay/bin/samay)
    PATH              what your shell would run
    beside            <dir>/<name>/.venv/bin/<program>, for checkouts kept
                      side by side; <dir> is SARATHI_SIBLINGS, or the
                      folder this checkout of Sarathi sits in

The first hit wins, and the answer says which rule found it, so "why is
it running THAT one?" always has an answer on screen.

ONLY WHAT THE SIBLING SAYS. Setu knows its connections, Samay knows
whether its clock is running, Dvara knows whether the door is serving
(asked of its folders as sarathi.toml names them, so the answer is about
the door Sarathi starts), and Yantra knows its release and which model
it would ask (asked with the model settings ``up`` gives it, so the
answer is about the Yantra Sarathi starts). Sarathi repeats them and
adds nothing. Smritikosh has no status command, so for it the answer is
"found, here" -- not a guess about whether something is listening on a
port.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: How long a sibling's ``status --json`` may take.
STATUS_TIMEOUT = 20.0


@dataclass(frozen=True)
class Sibling:
    name: str
    program: str
    role: str
    status_format: str | None = None   # None: the sibling has no status command
    optional: bool = False


SIBLINGS: tuple[Sibling, ...] = (
    Sibling("yantra", "yantra", "the machine: the agent itself",
            status_format="yantra.status.v1"),
    Sibling("setu", "setu", "the bridge: your accounts, signed in once",
            status_format="setu.status.v1"),
    Sibling("samay", "samay", "the clock: work done later, with receipts",
            status_format="samay.status.v1"),
    Sibling("dvara", "dvara", "the door: many people and agents behind one service",
            status_format="dvara.status.v1", optional=True),
    Sibling("smritikosh", "smritikosh-mcp",
            "a memory store (Yantra keeps its own without it)", optional=True),
)


@dataclass
class Found:
    sibling: Sibling
    program: str | None = None
    how: str | None = None             # "env" | "path" | "beside"
    status: dict[str, Any] | None = None
    said: str | None = None            # one line, from the sibling's own status
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        s = self.sibling
        return {"name": s.name, "role": s.role, "optional": s.optional,
                "found": self.program is not None, "program": self.program,
                "how": self.how, "said": self.said, "error": self.error,
                "status": self.status}


def env_name(sibling: Sibling) -> str:
    return f"SARATHI_{sibling.name.upper()}"


def beside_dir(env: dict[str, str] | None = None) -> Path | None:
    """The folder sibling checkouts are looked for in, or None."""
    env = os.environ if env is None else env
    if env.get("SARATHI_SIBLINGS"):
        return Path(env["SARATHI_SIBLINGS"]).expanduser()
    checkout = Path(__file__).resolve().parents[2]
    # Only a checkout (an editable install) has a folder worth looking beside.
    return checkout.parent if (checkout / "pyproject.toml").is_file() else None


def locate(sibling: Sibling, env: dict[str, str] | None = None) -> tuple[str, str] | None:
    """(program, how) for the first rule that finds it, or None."""
    env = os.environ if env is None else env
    named = env.get(env_name(sibling))
    if named:
        return str(Path(named).expanduser()), "env"
    on_path = shutil.which(sibling.program, path=env.get("PATH"))
    if on_path:
        return on_path, "path"
    root = beside_dir(env)
    if root is not None:
        candidate = root / sibling.name / ".venv" / "bin" / sibling.program
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate), "beside"
    return None


def read_status(program: str, expected: str, before: list[str] | None = None,
                env: dict[str, str] | None = None) -> dict[str, Any]:
    """Run ``program [before...] status --json``; the parsed object, or
    ValueError saying why not. ``before`` are the program's own options
    (dvara's folders); ``env`` is added to this process's environment
    (Yantra's model settings)."""
    try:
        done = subprocess.run([program, *(before or []), "status", "--json"],
                              capture_output=True,
                              env={**os.environ, **env} if env else None,
                              text=True, timeout=STATUS_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        raise ValueError(f"`status --json` took longer than {STATUS_TIMEOUT:.0f}s") from None
    except OSError as exc:
        raise ValueError(f"could not be run: {exc.strerror or exc}") from None
    if done.returncode != 0:
        last = (done.stderr.strip().splitlines() or ["(no message)"])[-1]
        raise ValueError(f"`status --json` failed: {last}")
    try:
        data = json.loads(done.stdout)
    except json.JSONDecodeError:
        raise ValueError("`status --json` did not print JSON") from None
    got = data.get("format") if isinstance(data, dict) else None
    if got != expected:
        raise ValueError(f"`status --json` speaks {got!r}, not {expected!r}: "
                         "a version this Sarathi does not know")
    return data


def _say_setu(data: dict[str, Any]) -> str:
    refs = [c.get("ref", "?") for c in data.get("connections") or []]
    if not refs:
        return "no accounts connected (connect one: setu connect gmail)"
    return f"{len(refs)} account{'s' * (len(refs) != 1)} connected: {', '.join(refs)}"


def _say_samay(data: dict[str, Any]) -> str:
    counts = data.get("schedules") or {}
    tally = f"{counts.get('active', 0)} active, {counts.get('paused', 0)} paused"
    if data.get("serving"):
        return f"clock running at {data.get('url') or '(no page)'}; schedules: {tally}"
    return f"clock not running (start it: samay serve); schedules: {tally}"


def _say_dvara(data: dict[str, Any]) -> str:
    running = data.get("running") or {}
    agents = len(data.get("agents") or [])
    tally = f"{agents} agent{'s' * (agents != 1)}, {data.get('people', 0)} people"
    url = data.get("url") or ""
    if data.get("serving"):
        # a container's own bind says nothing about where to reach it
        where = f" at {url}" if url and "//0.0.0.0" not in url else ""
        said = f"door serving{where} ({running.get('command')}); {tally}"
    elif running:
        said = f"door not serving: {running.get('command')} is using its folder; {tally}"
    else:
        said = f"door not serving; {tally}"
    problems = data.get("problems") or []
    return said + "".join(f"; {p}" for p in problems)


def _say_yantra(data: dict[str, Any]) -> str:
    said = f"yantra {data.get('version', '?')}"
    if data.get("provider"):
        said += f"; would ask {data['provider']} for {data.get('model')}"
    # Only what it does NOT find: Setu's and Samay's own lines already say
    # what they are, and a Yantra that cannot see one is the news.
    for name in ("setu", "samay"):
        if isinstance(data.get(name), dict) and not data[name].get("found"):
            said += f"; finds no {name}"
    problems = data.get("problems") or []
    return said + "".join(f"; {p}" for p in problems)


SAY = {"yantra": _say_yantra, "setu": _say_setu, "samay": _say_samay, "dvara": _say_dvara}


#: A ``before`` that means "do not ask": the door is off in sarathi.toml,
#: and dvara's answer about its default folders would be about nothing.
NOT_ASKED = "door off in sarathi.toml (`sarathi door` turns it on)"


def find(sibling: Sibling, env: dict[str, str] | None = None,
         before: list[str] | None = None, ask: bool = True,
         asked_with: dict[str, str] | None = None) -> Found:
    found = Found(sibling)
    hit = locate(sibling, env)
    if hit is None:
        return found
    found.program, found.how = hit
    if sibling.status_format is None:
        return found
    if not ask:
        found.said = NOT_ASKED
        return found
    try:
        found.status = read_status(found.program, sibling.status_format, before,
                                   asked_with)
    except ValueError as exc:
        found.error = str(exc)
        return found
    found.said = SAY[sibling.name](found.status)
    return found


def find_all(env: dict[str, str] | None = None,
             before: dict[str, list[str] | None] | None = None,
             asked_with: dict[str, dict[str, str]] | None = None) -> list[Found]:
    """Every sibling. ``before``: options a sibling's status is asked
    with, by name -- the door's folders, from sarathi.toml; None for a
    name means not asked at all (the door is off). ``asked_with``:
    environment added when asking, by name -- Yantra's model settings."""
    before = before or {}
    asked_with = asked_with or {}
    return [find(s, env, before.get(s.name), ask=before.get(s.name, []) is not None,
                 asked_with=asked_with.get(s.name))
            for s in SIBLINGS]
