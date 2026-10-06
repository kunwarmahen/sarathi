"""`sarathi`: set it up once, start it, see what is here, stop it.

    sarathi init              which model answers; writes sarathi.toml
    sarathi up                start Yantra's page and Samay's clock
    sarathi down              stop what `up` started, and nothing else
    sarathi status            each piece: found where, what it says, and
                              what `up` started
    sarathi status --json     the same, as sarathi.status.v1

``init`` takes flags for everything it asks (``--provider``, ``--model``,
``--base-url``, ``--web-port``, ``--clock-port``, ``--no-clock``), so it
can run with nobody there.

``status`` exits 0 when every piece Sarathi needs is found and readable,
and 1 when one is missing or its status could not be read. Dvara and
Smritikosh are optional: missing, they are reported, never failed on.
``up`` exits 1 when anything it should have started is not answering.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sarathi import __version__, first_run, services
from sarathi.config import PROVIDERS, ConfigError, load
from sarathi.siblings import Found, env_name, find_all

FORMAT = "sarathi.status.v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sarathi", description="Yantra and its siblings, found and started together.")
    parser.add_argument("--version", action="version", version=f"sarathi {__version__}")
    subs = parser.add_subparsers(dest="command", required=True)

    init = subs.add_parser("init", help="which model answers; writes sarathi.toml")
    init.add_argument("--provider", choices=PROVIDERS,
                      help="ollama (on this machine), anthropic or openai")
    init.add_argument("--model", help="the model's name (default: a pulled one, "
                                      "or the provider's usual)")
    init.add_argument("--base-url", dest="base_url", help="the provider's address, "
                      "when it is not the usual one")
    init.add_argument("--web-port", dest="web_port", type=int, help="Yantra's page")
    init.add_argument("--clock-port", dest="clock_port", type=int, help="Samay's page")
    init.add_argument("--no-clock", dest="no_clock", action="store_true",
                      help="do not start Samay")
    init.add_argument("--force", action="store_true", help="replace sarathi.toml")

    subs.add_parser("up", help="start Yantra's page and Samay's clock")
    subs.add_parser("down", help="stop what `sarathi up` started")
    status = subs.add_parser("status", help="what is here, and what each piece says")
    status.add_argument("--json", dest="json_out", action="store_true",
                        help=f"print {FORMAT} instead of lines")
    return parser


def _home(path: str) -> str:
    home = str(Path.home())
    return "~" + path[len(home):] if path.startswith(home + os.sep) else path


def _lines(found: list[Found]) -> list[str]:
    width = max(len(f.sibling.name) for f in found)
    out = []
    for f in found:
        s = f.sibling
        head = f"{s.name:<{width}}  "
        if f.program is None:
            extra = " (optional)" if s.optional else ""
            out.append(f"{head}not found{extra} -- install it, or set "
                       f"{env_name(s)}=/path/to/{s.program}")
        else:
            out.append(f"{head}{_home(f.program)}  ({f.how})")
        pad = " " * (width + 2)
        out.append(f"{pad}{s.role}")
        if f.error:
            out.append(f"{pad}found, but: {f.error}")
        elif f.said:
            out.append(f"{pad}{f.said}")
    return out


def _running_lines(started: list[dict]) -> list[str]:
    if not started:
        return []
    out = ["", "started by `sarathi up`:"]
    for r in started:
        if r["alive"]:
            address = r.get("address") or r["url"]
            out.append(f"  {r['name']:<6} running at {address}  (pid {r['pid']}, "
                       f"since {r['started']})")
        else:
            out.append(f"  {r['name']:<6} STOPPED -- it exited; the end of "
                       f"{_home(str(services.log_path(r['name'])))}:")
            out += [f"         | {line}" for line in r["log"]]
    return out


def _ok(found: list[Found]) -> bool:
    return all(f.sibling.optional or (f.program is not None and f.error is None)
               for f in found)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return first_run.run(args)
    if args.command == "down":
        print("\n".join(services.down()))
        return 0
    found = find_all()
    if args.command == "up":
        try:
            lines, ok = services.up(load(), {f.sibling.name: f for f in found})
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print("\n".join(lines))
        return 0 if ok else 1
    # status
    started = services.running()
    if args.json_out:
        print(json.dumps({"format": FORMAT, "version": __version__, "ok": _ok(found),
                          "siblings": [f.as_json() for f in found], "started": started}))
    else:
        print("\n".join(_lines(found) + _running_lines(started)))
    return 0 if _ok(found) else 1
