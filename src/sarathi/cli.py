"""`sarathi`: what is on this machine, and what each piece says.

    sarathi status            each sibling: found where, and its own one line
    sarathi status --json     the same, as sarathi.status.v1

Exit status is 0 when every sibling Sarathi needs is found and readable,
1 when one is missing or its status could not be read. Dvara and
Smritikosh are optional: missing, they are reported, never failed on.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sarathi import __version__
from sarathi.siblings import Found, env_name, find_all

FORMAT = "sarathi.status.v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sarathi", description="Yantra and its siblings, found and started together.")
    parser.add_argument("--version", action="version", version=f"sarathi {__version__}")
    subs = parser.add_subparsers(dest="command", required=True)
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


def _ok(found: list[Found]) -> bool:
    return all(f.sibling.optional or (f.program is not None and f.error is None)
               for f in found)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        found = find_all()
        if args.json_out:
            print(json.dumps({"format": FORMAT, "version": __version__, "ok": _ok(found),
                              "siblings": [f.as_json() for f in found]}))
        else:
            print("\n".join(_lines(found)))
        return 0 if _ok(found) else 1
    return 2  # argparse rejects anything else before here
