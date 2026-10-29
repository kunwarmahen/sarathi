"""`sarathi`: set it up once, start it, see what is here, stop it.

    sarathi init              which model answers; writes sarathi.toml
    sarathi dvara             turn on Dvara, the door for other people and your
                              phone: its tokens, a Telegram bot, starter files
    sarathi phone [ADDRESS]   your phone for the door's agents, and over Wi-Fi
                              for the containers (`phone pair ADDRESS CODE` once,
                              or `phone tcpip` from the cable; `phone iphone`
                              for an iPhone's WebDriverAgent)
    sarathi smritikosh        memories found by meaning: set Smritikosh up (its
                              database, settings, tables, accounts, keys) and
                              switch to it; --off goes back to the built-in file;
                              --full adds Neo4j, MongoDB and Redis
    sarathi road [ROAD]       how `up` starts things: process (plain programs) or
                              podman (containers); switching stops the other road
    sarathi image             build the image the podman road runs
    sarathi up                start Yantra, Samay (and Dvara), and their pages
    sarathi down              stop what `up` started, and nothing else
    sarathi status            each piece: found where, what it says, and
                              what `up` started
    sarathi status --json     the same, as sarathi.status.v1
    sarathi doctor            what's wrong, green / amber / red, and the line
                              that fixes each (--json: sarathi.doctor.v1)
    sarathi version           which commit of each project is running: the
                              image's, on the podman road (--json: sarathi.version.v1)
    sarathi home              one page linking every program's page, with status,
                              and a chat with your agents
    sarathi invite NAME       a one-time link for someone in Dvara's actors file:
                              they choose a password and get their own chat
    sarathi people            who can sign in to the home page; --sign-out NAME
                              ends their devices, --remove NAME their sign-in
    sarathi backup            everything here in one locked file: each program's
                              own files, the settings, the memories (the first
                              time, it asks for the passphrase that opens it)
    sarathi backup list       the backups in [backup] folder, newest first, numbered
    sarathi backup delete N   delete backup N (or a file name; --all-but N keeps
                              the newest N), after a yes
    sarathi backup set        [backup] in sarathi.toml: --folder (a USB disk's
                              folder), --keep N, --also PATH, --no-also PATH
    sarathi restore FILE      put it all back, on this computer or a new one
                              (--list: what's in it; --only NAME,...: some of it)

``init`` takes flags for everything it asks (``--provider``, ``--model``,
``--base-url``, ``--yantra-port``, ``--samay-port``, ``--no-samay``,
``--prahari-port``, ``--no-prahari``, ``--memory``), so it
can run with nobody there.

``status`` exits 0 when every piece Sarathi needs is found and readable,
and 1 when one is missing or its status could not be read. Dvara,
Sparsh and Smritikosh are optional: missing, they are reported, never failed on.
``up`` exits 1 when anything it should have started is not answering.
``up`` and ``down`` start and stop plain processes, or -- with
``run.road = "podman"`` -- the systemd units podman.py writes.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from sarathi import door, first_run, podman, services, version
from sarathi.services import WIDTH
from sarathi.config import AWAKE, PROVIDERS, ConfigError, load, render, settings_path
from sarathi.siblings import SIBLINGS, Found, env_name, find, find_all, locate

FORMAT = "sarathi.status.v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sarathi", description="Yantra and its siblings, found and started together.")
    parser.add_argument("--version", action=version.Show)
    subs = parser.add_subparsers(dest="command", required=True)

    init = subs.add_parser("init", help="which model answers; writes sarathi.toml")
    init.add_argument("--provider", choices=PROVIDERS,
                      help="ollama (on this machine), anthropic or openai")
    init.add_argument("--model", help="the model's name (default: a pulled one, "
                                      "or the provider's usual)")
    init.add_argument("--base-url", dest="base_url", help="the provider's address, "
                      "when it is not the usual one")
    init.add_argument("--yantra-port", "--web-port", dest="web_port", type=int,
                      help="Yantra's page")
    init.add_argument("--samay-port", "--clock-port", dest="clock_port", type=int,
                      help="Samay's page")
    init.add_argument("--no-samay", "--no-clock", dest="no_clock", action="store_true",
                      help="do not start Samay")
    init.add_argument("--prahari-port", dest="watch_port", type=int,
                      help="Prahari's page and its inlet")
    init.add_argument("--no-prahari", dest="no_watch", action="store_true",
                      help="do not start Prahari")
    init.add_argument("--podman", action="store_true",
                      help="start things as Podman containers (see `sarathi image`)")
    init.add_argument("--memory", choices=("local", "smritikosh"),
                      help="where what you tell it is remembered: local (Yantra's own "
                           "file, the default) or smritikosh (set up now)")
    init.add_argument("--force", action="store_true", help="replace sarathi.toml")

    kosh = subs.add_parser("smritikosh", help="memories found by meaning: set up "
                           "Smritikosh and switch to it (--off: back to the built-in file)")
    kosh.add_argument("--off", action="store_true",
                      help="back to Yantra's built-in file; nothing is deleted")
    kosh.add_argument("--local", action="store_true",
                      help="a new Smritikosh on the local road (Ollama) even when "
                           "[model] is a cloud one")
    full = kosh.add_mutually_exclusive_group()
    full.add_argument("--full", action="store_true",
                      help="Neo4j, MongoDB and Redis too, yours where the .env names them "
                           "(Yantra needs PostgreSQL alone)")
    full.add_argument("--no-full", dest="no_full", action="store_true",
                      help="PostgreSQL alone again; the others' data is kept")

    door_cmd = subs.add_parser("dvara", aliases=["door"],
                               help="Dvara, for other people and your phone: "
                                    "turn it on, a Telegram bot, starter files")
    door_cmd.add_argument("--telegram", metavar="AGENT",
                          help="the agent a Telegram bot answers as ('' for no bot)")
    door_cmd.add_argument("--telegram-id", dest="telegram_id", metavar="ID",
                          help="your own Telegram user id, for a new actors file")
    door_cmd.add_argument("--port", type=int, help="Dvara's HTTP port (default 8770)")
    door_cmd.add_argument("--window-host", dest="window_host", metavar="ADDRESS",
                          help="where a streamed sign-in window listens (home network, "
                               "Tailscale, or 127.0.0.1 behind your own HTTPS)")
    door_cmd.add_argument("--window-port", dest="window_port", type=int, metavar="PORT")
    door_cmd.add_argument("--window-url", dest="window_url", metavar="URL",
                          help="the address in the link, when it differs from the host")
    door_cmd.add_argument("--ntfy", action=argparse.BooleanOptionalAction, default=None,
                          help="a push server here, so notices reach phones with the "
                               "ntfy app (--no-ntfy: stop starting it)")
    door_cmd.add_argument("--ntfy-port", dest="ntfy_port", type=int, metavar="PORT",
                          help="ntfy's port (default 8793)")
    door_cmd.add_argument("--voices", metavar="NAME,NAME",
                          help="Piper voices to read answers aloud in, e.g. "
                               "en_US-lessac-medium,hi_IN-pratham-medium (fetched here "
                               "on plain programs; `sarathi image` on Podman)")
    door_cmd.add_argument("--off", action="store_true", help="stop starting Dvara")

    phone_cmd = subs.add_parser("phone", help="your phone, through Sparsh, for Dvara's "
                                "agents and the containers: on, pair, its Wi-Fi address")
    phone_cmd.add_argument("words", nargs="*",
                           metavar="ADDRESS | tcpip | pair ADDRESS CODE | iphone [URL] | "
                                   "add NAME ... | remove NAME | list",
                           help="nothing: a phone on a cable; ADDRESS: over Wi-Fi; "
                                "tcpip: the phone on the cable listens over Wi-Fi "
                                "(again after each restart of the phone); "
                                "pair ADDRESS CODE: trust this computer, once; "
                                "iphone [URL]: an iPhone, its WebDriverAgent at URL "
                                "(default http://127.0.0.1:8100, started first when it "
                                "isn't answering); add NAME [same words]: one of "
                                "several phones, by name; remove NAME; list")
    phone_cmd.add_argument("--off", action="store_true", help="stop giving the phone out")
    phone_cmd.add_argument("--awake", choices=AWAKE, help="its screen while an agent works "
                           "it: working (default: kept on, then yours back), always, off")

    road = subs.add_parser("road", help="how `up` starts things: plain programs or "
                           "containers; with no road, say which")
    road.add_argument("road", nargs="?", choices=("process", "podman"),
                      help="process: plain programs on this machine; podman: containers "
                           "systemd keeps running")

    subs.add_parser("image", help="build the image for the podman road, from the "
                                  "checkouts' committed code")
    subs.add_parser("up", help="start Yantra, Samay and Dvara (when on), "
                               "and their pages")
    down = subs.add_parser("down", help="stop what `sarathi up` started")
    down.add_argument("--remove", action="store_true",
                      help="podman road: also remove the units, so nothing starts at login")
    home_cmd = subs.add_parser("home", help="one page that links to every program's own "
                               "page, each with its status")
    home_cmd.add_argument("--host", default="127.0.0.1",
                          help="this computer only, unless you say otherwise")
    home_cmd.add_argument("--port", type=int, default=8760)
    home_cmd.add_argument("--also-host", dest="also_host", metavar="ADDRESS",
                          help="listen on this address too, where phones at home reach "
                               "it (the door's window_host)")
    invite = subs.add_parser("invite", help="a one-time link for someone in the house: "
                             "they choose a password, then have their own chat")
    invite.add_argument("name", help="their id in Dvara's actors file")
    people_cmd = subs.add_parser("people", help="who can sign in to the home page")
    people_do = people_cmd.add_mutually_exclusive_group()
    people_do.add_argument("--sign-out", dest="sign_out", metavar="NAME",
                           help="sign NAME out on every device")
    people_do.add_argument("--remove", metavar="NAME",
                           help="NAME's sign-in gone: password, invite and devices")
    status = subs.add_parser("status", help="what is here, and what each piece says")
    status.add_argument("--json", dest="json_out", action="store_true",
                        help=f"print {FORMAT} instead of lines")
    doctor = subs.add_parser("doctor", help="what's wrong, and the line that fixes it")
    doctor.add_argument("--json", dest="json_out", action="store_true",
                        help="print sarathi.doctor.v1 instead of lines")
    shown = subs.add_parser("version", help="which commit of each project is running")
    shown.add_argument("--json", dest="json_out", action="store_true",
                         help="print sarathi.version.v1 instead of lines")
    backup = subs.add_parser("backup", help="everything here in one locked file")
    backup.add_argument("--to", metavar="FOLDER",
                        help="where to write it (default: [backup] folder)")
    backup.add_argument("--keep", type=int, metavar="N",
                        help="keep the newest N there, removing older ones "
                             "(default: [backup] keep; 0 keeps all)")
    backup.add_argument("--new-passphrase", dest="new_passphrase", action="store_true",
                        help="choose a new passphrase (older backups still open with "
                             "the one they were made with)")
    backup.add_argument("--json", dest="json_out", action="store_true",
                        help="print sarathi.backup.made.v1")
    kinds = backup.add_subparsers(dest="backup_cmd", metavar="list|delete|set")
    listed = kinds.add_parser("list", help="the backups there, newest first, numbered")
    listed.add_argument("--from", dest="source", metavar="FOLDER",
                        help="another folder (default: [backup] folder)")
    listed.add_argument("--json", dest="json_out", action="store_true",
                        help="print sarathi.backup.list.v1")
    gone = kinds.add_parser("delete", help="delete backups, by number or file name")
    gone.add_argument("picks", nargs="*", metavar="N|FILE",
                      help="numbers from `sarathi backup list`, or file names")
    gone.add_argument("--all-but", dest="all_but", type=int, metavar="N",
                      help="delete all but the newest N")
    gone.add_argument("--from", dest="source", metavar="FOLDER",
                      help="another folder (default: [backup] folder)")
    gone.add_argument("--yes", action="store_true", help="don't ask first")
    gone.add_argument("--json", dest="json_out", action="store_true",
                      help="print sarathi.backup.deleted.v1")
    sets = kinds.add_parser("set", help="[backup] in sarathi.toml; no backup is made")
    sets.add_argument("--folder", metavar="FOLDER",
                      help="where backups go, like a USB disk's folder")
    sets.add_argument("--keep", dest="keep_n", type=int, metavar="N",
                      help="how many are kept there (0: all)")
    sets.add_argument("--also", action="append", default=[], metavar="PATH",
                      help="a file or folder of yours to back up too (again for more)")
    sets.add_argument("--no-also", dest="no_also", action="append", default=[],
                      metavar="PATH", help="stop backing that one up")
    restore = subs.add_parser("restore", help="put a backup back, here or on a new "
                              "computer")
    restore.add_argument("file", help="the .sarathi-backup file")
    restore.add_argument("--list", dest="list_only", action="store_true",
                         help="say what's in it, and change nothing")
    restore.add_argument("--only", metavar="NAME,...",
                         help="only these: yantra, setu, samay, prahari, dvara, sparsh, "
                              "sarathi, smritikosh, you")
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
    owner = any(r["name"] == "dvara-page" and r["alive"] for r in started)
    for r in started:
        address = r.get("address") or r["url"]
        where = f"unit {r['unit']}" if "unit" in r else f"pid {r['pid']}, since {r['started']}"
        if r["alive"]:
            out.append(f"  {r['name']:<{WIDTH}} running "
                       f"{services.place(r['name'], address, owner)}  ({where})")
        else:
            log = f"its journal ({r['unit']})" if "unit" in r else \
                _home(str(services.log_path(r["name"])))
            out.append(f"  {r['name']:<{WIDTH}} STOPPED -- it exited; the end of {log}:")
            out += [f"         | {line}" for line in r["log"]]
        if r["name"] == "dvara" and r.get("strangers"):
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
    missing key is ``up``'s to report), and the Setu, Samay and Prahari
    programs ``up`` names with --setu, --samay, --prahari and --sparsh, as
    the variables that say the same (``off`` for one turned off)."""
    try:
        env = services.model_env(config)
    except ConfigError:
        env = {}
    for name, var in (("setu", "YANTRA_SETU"), ("samay", "YANTRA_SAMAY"),
                      ("prahari", "YANTRA_PRAHARI")):
        hit = locate(next(s for s in SIBLINGS if s.name == name))
        if hit is not None:
            env[var] = hit[0]
    if not config.clock_on:
        env["YANTRA_SAMAY"] = "off"
    if not config.watch_on:
        env["YANTRA_PRAHARI"] = "off"
    hit = locate(next(s for s in SIBLINGS if s.name == "sparsh"))
    if hit is not None:
        env["YANTRA_SPARSH"] = f"auto:{hit[0]}"
    return env


def _iphone_up(config, found) -> list[str]:
    """A saved iPhone on this computer's cable, started when it isn't
    answering (phone.py): after a restart, `up` brings it back too."""
    from sarathi import phone

    wda = next(iter(config.phone.wdas), None) if config.phone else None
    sparsh = next((f for f in found if f.sibling.name == "sparsh"), None)
    if not wda or not phone.is_here(wda) or sparsh is None or sparsh.program is None:
        return []
    android = phone.android_answers(sparsh)
    if android:
        # the Android is the phone today: nothing to wait for, but the
        # iPhone's unit waits behind, so plugging it in is all it takes
        phone.start_behind(sparsh)
        return [f"{'iphone':<{services.WIDTH}} waiting behind; the Android on the cable "
                f"({android}) is the phone now"]
    ok, said = phone.iphone_ready(sparsh, wda)
    return [f"{'iphone':<{services.WIDTH}} {said if ok else 'not ready: ' + said}"]


def _kept(config) -> dict[str, str] | None:
    """Programs where sarathi.toml records them: Smritikosh's, once set up."""
    checkout = config.smritikosh.path() if config else None
    if checkout is None:
        return None
    from sarathi.smritikosh import program

    return {"smritikosh": str(program(checkout))}


def _said() -> dict[str, str]:
    """Each sibling's one line, asked as `sarathi status` asks it."""
    config = _settings_or_none()
    found = find_all(before={"dvara": door_folders(config)} if config else None,
                     asked_with={"yantra": _yantra_env(config),
                                 "sparsh": services.phone_env(config)} if config else None,
                     kept=_kept(config))
    return {f.sibling.name: f.said or f.error or ("not found" if f.program is None else "")
            for f in found}


def _doctor() -> dict:
    """`sarathi doctor --json`, for the home page's Check: everything asked
    again, with sarathi.toml as it is on disk now."""
    from sarathi import doctor

    config = _settings_or_none()
    found = find_all(before={"dvara": door_folders(config)} if config else None,
                     asked_with={"yantra": _yantra_env(config),
                                 "sparsh": services.phone_env(config)} if config else None,
                     kept=_kept(config))
    started = podman.running(config) if config and config.road == "podman" \
        else services.running()
    return doctor.report(doctor.examine(config, found, started, _memory(config)))


def _memory(config) -> dict | None:
    """Where memories are kept, and how that is going (smritikosh.py)."""
    if config is None:
        return None
    from sarathi import smritikosh

    seen = smritikosh.health(config) if config.remembers_in_smritikosh else {}
    said = smritikosh.health_line(config, seen or None)
    dash = smritikosh.dashboard(config) if config.remembers_in_smritikosh else None
    if dash:
        said += (f"\n  its dashboard: {dash['url']}" if dash["up"] else
                 f"\n  its dashboard isn't running: {dash['start']}")
    return {"via": config.memory, "said": said, "dashboard": dash,
            **{k: seen.get(k) for k in ("up", "url", "memories")}}


def _home_answers(port: int) -> bool:
    """Whether Sarathi's own home page answers on ``port`` here, to this
    computer's key: something else on the port is an error, not a link."""
    import urllib.request

    from sarathi.home import home_token

    request = urllib.request.Request(f"http://127.0.0.1:{port}/api/pieces",
                                     headers={"Authorization": f"Bearer {home_token()}"})
    try:
        with urllib.request.urlopen(request, timeout=3) as answer:
            return answer.status == 200
    except OSError:
        return False


def _running_home(config, port: int) -> int:
    """The running home page's links: here, and by the house's name."""
    from sarathi.home import home_token

    token = home_token()
    print(f"your home page is already running:\n  http://127.0.0.1:{port}/#token={token}")
    shown = config.link_host() if config.people_host() else None
    if shown:
        print(f"on your other devices:\n  {config.link(port)}#token={token}")
    print("(the part after # is its key: open it once, the page keeps it)")
    return 0


def _serve_home(args) -> int:
    from sarathi.home import Chat, Home, HomeServer, backup_token, doctor_token, home_token
    from sarathi.people import People

    try:
        config = load()
        server = HomeServer(Home(config, _said, doctor=_doctor,
                                 backup=lambda: run_backup(ask=False).as_json()),
                            home_token(), doctor_key=doctor_token(),
                            backup_key=backup_token(), host=args.host,
                            port=args.port, chat=Chat.for_config(config),
                            people=People(), also_host=args.also_host)
    except OSError as exc:
        # already running (`sarathi up` starts it): its link is what was wanted
        if exc.errno == errno.EADDRINUSE and _home_answers(args.port):
            return _running_home(config, args.port)
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ConfigError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"your home page:\n  {server.page_url}\n"
          "(the part after # is its key: open it once, the page keeps it. Ctrl-C stops.)",
          flush=True)
    if server.also_problem:
        print(f"not for the people in the house: {server.also_problem}; this computer "
              "only until it can be", flush=True)
    if server.also is not None:
        print(f"and for the people in the house: http://{args.also_host}:"
              f"{server.httpd.server_address[1]}/ (they sign in)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.httpd.server_close()
    return 0


def _people(args) -> int:
    """`sarathi invite NAME` and `sarathi people`: the home page's sign-ins."""
    from sarathi.home import invite_address
    from sarathi.people import INVITE_HOURS, People, PeopleError, actor_ids

    try:
        config = load()
        people = People()
        if config.door is None:
            raise PeopleError("Dvara is off: the people in the house talk to their agents "
                              "through it. Turn it on with `sarathi dvara`")
        if args.command == "invite":
            link = people.invite(args.name, actor_ids(config.door.path("actors")),
                                 config.door.owner)
            url, reachable = invite_address(config, link)
            print(f"{args.name}'s link, for one device, within {INVITE_HOURS} hours:\n"
                  f"  {url}\n"
                  "They open it and choose a password; after that they sign in with "
                  f"{args.name!r} and that password, and see their own chat only.")
            if not reachable:
                print("It opens on this computer only: for a phone at home, give Dvara a "
                      "window address (`sarathi dvara --window-host ADDRESS`), then "
                      "`sarathi up` and invite again.")
            return 0
        if args.sign_out:
            gone = people.sign_out(args.sign_out)
            print(f"{args.sign_out} signed out on {gone} device{'s' if gone != 1 else ''}")
            return 0
        if args.remove:
            people.remove(args.remove)
            print(f"{args.remove}'s sign-in is gone; they're still in Dvara's actors file")
            return 0
        known = actor_ids(config.door.path("actors"))
        kept = {p.name: p for p in people.listing()}
        names = [n for n in sorted(set(known) | set(kept)) if n != config.door.owner]
        if not names:
            print("Nobody but you in Dvara's actors file yet.")
        for name in names:
            p = kept.get(name)
            if p is None:
                said = "no sign-in yet: `sarathi invite " + name + "`"
            elif p.signed_up:
                said = f"signed up, on {p.devices} device{'s' if p.devices != 1 else ''}"
                said += f", last {p.last_used}" if p.last_used else ""
            else:
                said = "invited, not opened yet"
            if p is not None and p.invite_until:
                said += f"; a link open until {p.invite_until}"
            if name not in known:
                said += "; not in Dvara's actors file any more"
            print(f"{name:<{WIDTH}} {said}")
        return 0
    except (ConfigError, PeopleError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def backup_places(config) -> tuple[list, list[str]]:
    """Every program's places (each asked what it keeps), Sarathi's own
    after them; and what couldn't be asked, in words."""
    from sarathi import backup

    places, problems = [], []
    for s in SIBLINGS:
        if s.status_format is None:
            continue                  # Smritikosh: its .env and database are Sarathi's
        hit = locate(s)
        if hit is None:
            if not s.optional:
                problems.append(f"{s.name} isn't on this computer, so nothing of its "
                                f"is in this backup")
            continue
        before = None
        if s.name == "dvara":
            if config is None or config.door is None:
                continue              # off: no door's folders to ask about
            before = door_folders(config)
        try:
            places += backup.ask_keeps(Found(s, program=hit[0], how=hit[1]), before)
        except backup.BackupError as exc:
            problems.append(str(exc))
    return places + backup.own_places(config), problems


def run_backup(*, to: str | None = None, keep: int | None = None,
               new_passphrase: bool = False, ask: bool = True,
               say=lambda _line: None):
    """`sarathi backup`, for the command and the home page alike. With
    ``ask`` False (the home page, Samay), a missing key is an error: the
    passphrase is chosen by a person, at a terminal."""
    from sarathi import backup
    from sarathi.config import Backup

    config = _settings_or_none()
    settings = config.backup if config is not None else Backup()
    key = None if new_passphrase else backup.read_key()
    if key is None:
        if not ask and not os.environ.get(backup.ENV_PASSPHRASE):
            raise backup.BackupError("there is no backup passphrase yet: run `sarathi "
                                     "backup` once at a terminal to choose it")
        print("Choose the passphrase that opens your backups. Without it nothing can "
              "open them -- not even you -- so write it down somewhere safe.",
              file=sys.stderr)
        key = backup.make_key(backup.ask_passphrase(twice=True))
        print(f"its key: {_home(str(backup.save_key(key)))}", file=sys.stderr)
    places, problems = backup_places(config)
    folder = Path(to).expanduser() if to else settings.path()
    made = backup.make(places, key, folder, config=config, problems=problems, say=say)
    made.removed = backup.prune(folder, settings.keep if keep is None else keep)
    return made


def _backup(args) -> int:
    from sarathi import backup

    if args.backup_cmd:
        return _backup_kept(args)
    try:
        made = run_backup(to=args.to, keep=args.keep, new_passphrase=args.new_passphrase,
                          say=(lambda _line: None) if args.json_out else
                          (lambda line: print(line, flush=True)))
    except backup.BackupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        print(json.dumps(made.as_json()))
    else:
        print("\n".join([""] + backup.made_lines(made)))
    return 0 if not made.problems else 1


def _restore(args) -> int:
    from sarathi import backup

    file = Path(args.file).expanduser()
    only = {n.strip() for n in args.only.split(",") if n.strip()} if args.only else None
    try:
        if not file.is_file():
            raise backup.BackupError(f"there is no file at {file}")
        if not args.list_only:
            config = _settings_or_none()
            started = podman.running(config) if config and config.road == "podman" \
                else services.running()
            alive = [r["name"] for r in started if r.get("alive")]
            if alive:
                raise backup.BackupError(
                    f"these are running and write into what a restore replaces: "
                    f"{', '.join(alive)}. Stop them first: `sarathi down`")
        passphrase = backup.ask_passphrase(twice=False)
        if args.list_only:
            manifest = backup.peek(file, passphrase)
            print(f"made {manifest.get('made')} on {manifest.get('host')}:")
            for row in manifest.get("places") or []:
                kind = row.get("kind")
                said = {"folder": f"{row.get('files')} files, {backup.size(row['bytes'])}",
                        "file": backup.size(row.get("bytes", 0))}.get(kind, "wasn't there")
                where = backup.tilde(backup.rebase(row["path"], manifest.get("home", "")))
                print(f"  {row['owner'] + ' ' + row['id']:<24} {said:<22} {where}")
            if manifest.get("memory"):
                print(f"  {'smritikosh database':<24} its memories")
            for p in manifest.get("problems") or []:
                print(f"  not in it: {p}")
            return 0
        restored = backup.unpack(file, passphrase, only=only,
                                 say=lambda line: print(line, flush=True))
    except backup.BackupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    code = 0
    lines = ["", f"put back, from {restored.manifest.get('host')} "
                 f"({restored.manifest.get('made')}):", *restored.lines]
    if restored.memory_dump is not None:
        try:
            config = load()
            lines.append(f"  {'smritikosh database':<24} "
                         + backup.restore_memory(config, restored.memory_dump,
                                                 say=lambda line: print(line, flush=True)))
        except (backup.BackupError, ConfigError) as exc:
            lines.append(f"NOT PUT BACK: {exc}")
            code = 1
    backup.finish(restored)
    for refused in restored.refused:
        lines.append(f"left out (it would have pointed outside its folder): {refused}")
    if restored.moved_aside:
        lines += ["", "what was here before is kept beside each, not deleted:",
                  *(f"  {_home(p)}" for p in restored.moved_aside)]
    config = _settings_or_none()
    nxt = "sarathi up"
    if config is not None and config.road == "podman" and not podman.image_exists():
        nxt = "sarathi image && sarathi up"
    lines += ["", f"next: `{nxt}` (each program must be installed here first: a "
                  "backup holds what is yours, not the programs)"]
    print("\n".join(lines))
    return code


def _backup_kept(args) -> int:
    """`sarathi backup list | delete | set`: the files that are there, and
    the settings for the next ones. None of them makes a backup."""
    from sarathi import backup, editing
    from sarathi.config import Backup

    config = _settings_or_none()
    settings = config.backup if config is not None else Backup()
    if args.backup_cmd == "set":
        changes = {"folder": args.folder, "keep": args.keep_n,
                   "add_also": args.also, "drop_also": args.no_also}
        if any(v not in (None, []) for v in changes.values()):
            try:
                settings = editing.sarathi_apply({"backup": changes}).backup
            except editing.EditError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            print(f"saved [backup] in {_home(str(settings_path()))}")
        also = ", ".join(settings.also) or "nothing else"
        print(f"folder: {settings.folder}\nkeep:   "
              f"{settings.keep or 'every one'}\nalso:   {also}")
        gone = backup.missing_disk(settings.path())
        if gone:
            print(f"note: {gone} The next backup says so too, and makes nothing.")
        return 0
    folder = Path(args.source).expanduser() if args.source else settings.path()
    if args.backup_cmd == "list":
        rows = backup.listing(folder)
        if args.json_out:
            print(json.dumps({"format": "sarathi.backup.list.v1", "folder": str(folder),
                              "backups": rows}, indent=2))
            return 0
        if not rows:
            print(f"no backups in {_home(str(folder))}")
            return 0
        print(f"in {_home(str(folder))}, newest first:")
        for r in rows:
            print(f"  {r['n']:>2}  {r['made']}  {backup.size(r['bytes']):>9}  {r['name']}")
        return 0
    if not args.picks and args.all_but is None:
        print("error: which? a number from `sarathi backup list`, a file name, or "
              "--all-but N", file=sys.stderr)
        return 2
    rows = backup.listing(folder)
    try:
        if not args.yes:
            names = ([r["name"] for r in rows[args.all_but:]] if args.all_but is not None
                     else None)
            if names is None:
                picked = {p for p in args.picks}
                names = [r["name"] for r in rows if str(r["n"]) in picked or r["name"] in picked]
            if not names:
                print("nothing to delete")
                return 0
            print("\n".join(f"  {n}" for n in names))
            if input(f"Delete {'this' if len(names) == 1 else f'these {len(names)}'} "
                     "for good? [y/N] ").strip().lower() not in ("y", "yes"):
                print("nothing deleted")
                return 1
        deleted = backup.delete(folder, args.picks, all_but=args.all_but)
    except backup.BackupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except EOFError:
        print("nothing deleted (no one to say yes: --yes)", file=sys.stderr)
        return 1
    if args.json_out:
        print(json.dumps({"format": "sarathi.backup.deleted.v1", "folder": str(folder),
                          "deleted": deleted}, indent=2))
    else:
        print(f"deleted {len(deleted)}: {', '.join(deleted)}" if deleted
              else "nothing to delete")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "backup":
        return _backup(args)
    if args.command == "restore":
        return _restore(args)
    if args.command == "home":
        return _serve_home(args)
    if args.command in ("invite", "people"):
        return _people(args)
    if args.command == "init":
        return first_run.run(args)
    if args.command in ("dvara", "door"):
        dvara = next(f for f in find_all() if f.sibling.name == "dvara")
        return door.run(args, dvara)
    if args.command == "smritikosh":
        from sarathi import smritikosh

        try:
            return smritikosh.run_command(args, load())
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if args.command == "phone":
        from sarathi import phone

        sparsh = next(s for s in SIBLINGS if s.name == "sparsh")
        return phone.run(args, find(sparsh, ask=False))
    try:
        if args.command == "road":
            return switch_road(args.road)
        if args.command == "image":
            return podman.build(config=_settings_or_none())
        if args.command == "version":
            got = version.report(_settings_or_none())
            print(json.dumps(got) if args.json_out else version.text(got))
            return 0
        if args.command == "down":
            config = _settings_or_none()
            on_podman = config is not None and config.road == "podman"
            print("\n".join(podman.down(args.remove) if on_podman else services.down()))
            return 0
        config = _settings_or_none()
        found = find_all(before={"dvara": door_folders(config)} if config else None,
                         asked_with={"yantra": _yantra_env(config),
                                 "sparsh": services.phone_env(config)} if config else None,
                         kept=_kept(config))
        if args.command == "up":
            config = load()
            if config.road == "podman":
                lines, ok = podman.up(config)
            else:
                lines, ok = services.up(config, {f.sibling.name: f for f in found})
            lines += _iphone_up(config, found)
            print("\n".join(lines))
            return 0 if ok else 1
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    # status, doctor
    started = podman.running(config) if config and config.road == "podman" \
        else services.running()
    memory = _memory(config)
    if args.command == "doctor":
        from sarathi import doctor

        lines = doctor.examine(config, found, started, memory)
        if args.json_out:
            print(json.dumps(doctor.report(lines)))
        else:
            print(doctor.text(lines, colour=sys.stdout.isatty()))
        return 0 if doctor.report(lines)["ok"] else 1
    if args.json_out:
        print(json.dumps({"format": FORMAT, "version": version.own()[0],
                          "commit": version.own()[1], "ok": _ok(found),
                          "siblings": [f.as_json() for f in found], "started": started,
                          "memory": memory}))
    else:
        tail = ["", memory["said"]] if memory else []
        print("\n".join(_lines(found) + _running_lines(started) + tail))
    return 0 if _ok(found) else 1
