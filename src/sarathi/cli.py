"""`sarathi`: set it up once, start it, see what is here, stop it.

    sarathi init              which model answers; writes sarathi.toml
    sarathi door              turn on dvara, the door for other people and your
                              phone: its tokens, a Telegram bot, starter files
    sarathi road [ROAD]       how `up` starts things: process (plain programs) or
                              podman (containers); switching stops the other road
    sarathi image             build the image the podman road runs
    sarathi up                start Yantra's page and Samay's clock (and the door)
    sarathi down              stop what `up` started, and nothing else
    sarathi status            each piece: found where, what it says, and
                              what `up` started
    sarathi status --json     the same, as sarathi.status.v1
    sarathi home              one page linking every program's page, with status

``init`` takes flags for everything it asks (``--provider``, ``--model``,
``--base-url``, ``--web-port``, ``--clock-port``, ``--no-clock``), so it
can run with nobody there.

``status`` exits 0 when every piece Sarathi needs is found and readable,
and 1 when one is missing or its status could not be read. Dvara and
Smritikosh are optional: missing, they are reported, never failed on.
``up`` exits 1 when anything it should have started is not answering.
``up`` and ``down`` start and stop plain processes, or -- with
``run.road = "podman"`` -- the systemd units podman.py writes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from sarathi import __version__, door, first_run, podman, services
from sarathi.config import PROVIDERS, ConfigError, load, render, settings_path
from sarathi.siblings import SIBLINGS, Found, env_name, find_all, locate

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
    init.add_argument("--podman", action="store_true",
                      help="start things as Podman containers (see `sarathi image`)")
    init.add_argument("--force", action="store_true", help="replace sarathi.toml")

    door_cmd = subs.add_parser("door", help="dvara, for other people and your phone: "
                               "turn it on, a Telegram bot, starter files")
    door_cmd.add_argument("--telegram", metavar="AGENT",
                          help="the agent a Telegram bot answers as ('' for no bot)")
    door_cmd.add_argument("--telegram-id", dest="telegram_id", metavar="ID",
                          help="your own Telegram user id, for a new actors file")
    door_cmd.add_argument("--port", type=int, help="the door's HTTP port (default 8770)")
    door_cmd.add_argument("--window-host", dest="window_host", metavar="ADDRESS",
                          help="where a streamed sign-in window listens (home network, "
                               "Tailscale, or 127.0.0.1 behind your own HTTPS)")
    door_cmd.add_argument("--window-port", dest="window_port", type=int, metavar="PORT")
    door_cmd.add_argument("--window-url", dest="window_url", metavar="URL",
                          help="the address in the link, when it differs from the host")
    door_cmd.add_argument("--off", action="store_true", help="stop starting the door")

    road = subs.add_parser("road", help="how `up` starts things: plain programs or "
                           "containers; with no road, say which")
    road.add_argument("road", nargs="?", choices=("process", "podman"),
                      help="process: plain programs on this machine; podman: containers "
                           "systemd keeps running")

    subs.add_parser("image", help="build the image for the podman road, from the "
                                  "checkouts' committed code")
    subs.add_parser("up", help="start Yantra's page and Samay's clock, and the door "
                               "when it is on")
    down = subs.add_parser("down", help="stop what `sarathi up` started")
    down.add_argument("--remove", action="store_true",
                      help="podman road: also remove the units, so nothing starts at login")
    home_cmd = subs.add_parser("home", help="one page that links to every program's own "
                               "page, each with its status")
    home_cmd.add_argument("--host", default="127.0.0.1",
                          help="this computer only, unless you say otherwise")
    home_cmd.add_argument("--port", type=int, default=8760)
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
        address = r.get("address") or r["url"]
        where = f"unit {r['unit']}" if "unit" in r else f"pid {r['pid']}, since {r['started']}"
        if r["alive"]:
            out.append(f"  {r['name']:<6} running at {address}  ({where})")
        else:
            log = f"its journal ({r['unit']})" if "unit" in r else \
                _home(str(services.log_path(r["name"])))
            out.append(f"  {r['name']:<6} STOPPED -- it exited; the end of {log}:")
            out += [f"         | {line}" for line in r["log"]]
        if r["name"] == "door" and r.get("strangers"):
            out.append("         messaged the bot but not in the actors file (telegram "
                       f"id): {', '.join(r['strangers'])}")
    return out


def _ok(found: list[Found]) -> bool:
    return all(f.sibling.optional or (f.program is not None and f.error is None)
               for f in found)


ROADS = {"process": "plain programs on this machine, using its own browser and bubblewrap",
         "podman": "containers that systemd keeps running and starts at login"}


def switch_road(wanted: str | None) -> int:
    """Say the road, or change it. LEAVING A ROAD STOPS IT: both roads use
    the same ports, and Podman's units would otherwise start again at the
    next login and take them. Nothing new is started; `up` does that."""
    config = load()
    if wanted is None:
        print(f"road: {config.road} -- {ROADS[config.road]}")
        other = "podman" if config.road == "process" else "process"
        print(f"  (`sarathi road {other}` for {ROADS[other]})")
        return 0
    if wanted == config.road:
        print(f"already on the {wanted} road")
        return 0
    stopped = podman.down(remove=True) if config.road == "podman" else services.down()
    print("\n".join(stopped))
    settings_path().write_text(render(replace(config, road=wanted)))
    print(f"road: {wanted} -- {ROADS[wanted]}")
    if wanted == "podman" and not podman.image_exists():
        print("next: `sarathi image` (once), then `sarathi up`")
    else:
        print("next: `sarathi up`")
    return 0


def door_folders(config) -> list[str] | None:
    """dvara's own options naming the door's folders, as sarathi.toml has
    them: its status is then about the door `up` starts. None when the
    door is off, and dvara is not asked."""
    door = config.door
    if door is None:
        return None
    return ["--root", str(door.path("root")), "--actors", str(door.path("actors")),
            "--state", str(door.path("state"))]


def _settings_or_none():
    try:
        return load()
    except ConfigError:
        return None


def _yantra_env(config) -> dict[str, str]:
    """What ``up`` gives Yantra, so its status is about that Yantra: the
    model settings (left out when there is no key to give it yet -- the
    missing key is ``up``'s to report), and the Setu and Samay programs
    ``up`` names with --setu and --samay, as the variables that say the
    same (``off`` for a clock turned off)."""
    try:
        env = services.model_env(config)
    except ConfigError:
        env = {}
    for name, var in (("setu", "YANTRA_SETU"), ("samay", "YANTRA_SAMAY")):
        hit = locate(next(s for s in SIBLINGS if s.name == name))
        if hit is not None:
            env[var] = hit[0]
    if not config.clock_on:
        env["YANTRA_SAMAY"] = "off"
    return env


def _said() -> dict[str, str]:
    """Each sibling's one line, asked as `sarathi status` asks it."""
    config = _settings_or_none()
    found = find_all(before={"dvara": door_folders(config)} if config else None,
                     asked_with={"yantra": _yantra_env(config)} if config else None)
    return {f.sibling.name: f.said or f.error or ("not found" if f.program is None else "")
            for f in found}


def _serve_home(args) -> int:
    from sarathi.home import Home, HomeServer, home_token

    try:
        server = HomeServer(Home(load(), _said), home_token(), host=args.host,
                            port=args.port)
    except (ConfigError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"your home page:\n  {server.page_url}\n"
          "(the part after # is its key: open it once, the page keeps it. Ctrl-C stops.)",
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.httpd.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "home":
        return _serve_home(args)
    if args.command == "init":
        return first_run.run(args)
    if args.command == "door":
        dvara = next(f for f in find_all() if f.sibling.name == "dvara")
        return door.run(args, dvara)
    try:
        if args.command == "road":
            return switch_road(args.road)
        if args.command == "image":
            return podman.build()
        if args.command == "down":
            config = _settings_or_none()
            on_podman = config is not None and config.road == "podman"
            print("\n".join(podman.down(args.remove) if on_podman else services.down()))
            return 0
        config = _settings_or_none()
        found = find_all(before={"dvara": door_folders(config)} if config else None,
                         asked_with={"yantra": _yantra_env(config)} if config else None)
        if args.command == "up":
            config = load()
            if config.road == "podman":
                lines, ok = podman.up(config)
            else:
                lines, ok = services.up(config, {f.sibling.name: f for f in found})
            print("\n".join(lines))
            return 0 if ok else 1
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    # status
    started = podman.running(config) if config and config.road == "podman" \
        else services.running()
    if args.json_out:
        print(json.dumps({"format": FORMAT, "version": __version__, "ok": _ok(found),
                          "siblings": [f.as_json() for f in found], "started": started}))
    else:
        print("\n".join(_lines(found) + _running_lines(started)))
    return 0 if _ok(found) else 1
