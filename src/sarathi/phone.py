"""`sarathi phone`: your phone, for the door's agents and the containers.

    sarathi phone                        on, for a phone on a USB cable
    sarathi phone tcpip                  on, over Wi-Fi: the phone on the cable is
                                         told to listen, and its address saved
    sarathi phone pair ADDRESS CODE      trust this computer over Wi-Fi, once
    sarathi phone ADDRESS                on, reached over Wi-Fi at ADDRESS
    sarathi phone iphone [URL]           on, an iPhone: its WebDriverAgent at URL
                                         (http://127.0.0.1:8100 when not given)
    sarathi phone --off

WIRING, NOT A PHONE. Sparsh knows phones; this only writes ``[phone]``
into sarathi.toml and runs the Sparsh that ``sarathi status`` found for
the two things that need the phone in front of you: ``pair`` (the six
digits on its "Pair device with pairing code" screen) and a first
``connect``, so a wrong address is said now rather than at ``up``.

THE CABLE, FOR A PHONE WITH NO WIRELESS DEBUGGING PAGE. Android 10 and
older (a Nexus 6P on Android 8, here) can still be reached over Wi-Fi:
told over USB to listen (``sparsh tcpip``), trusting the key the cable
already does. A restart of the phone turns that off, and its address
may move, so ``tcpip`` is the one step to repeat; it runs Sparsh's, and
saves the address it found, so nobody looks one up. The home page's
Settings has the same button (editing.py), since it runs on this
computer, where the cable is; the containers never see the cable.

AN IPHONE IS AN ADDRESS TOO. Sparsh drives an iPhone through
WebDriverAgent, an app on the phone that Sparsh's own scripts build (on a
Mac, once a week) and start (``scripts/start-wda-from-linux.sh``, here,
with the iPhone on this computer's cable). That script stays running and
needs ``sudo`` for iOS 17's tunnel, so it is the person's to start, not
``up``'s. ``iphone`` asks Sparsh whether WebDriverAgent answers, saves its
address as ``[phone] wda``, and drops an Android address: Sarathi gives
its agents one phone. The containers reach it at
``host.containers.internal`` (podman.py).

ONE KEY, THIS COMPUTER'S. Pairing runs this computer's ``adb``, so the
phone trusts the key in ``~/.android``. The containers mount that folder
at the same path, so a phone that trusts this computer trusts its
containers, and nothing is paired twice.

The door's agents get the phone only for the person marked ``phone =
true`` in its actors file, and only through a package whose ``[tools]
allow`` lets ``mcp__sparsh__*`` in; this says so when nobody is marked,
or when the agent on Telegram leaves the phone out.
"""

from __future__ import annotations

import subprocess
from dataclasses import replace

from sarathi.config import ConfigError, Phone, load, render, settings_path
from sarathi.siblings import Found

#: How long a pair or a first connect may take.
PHONE_TIMEOUT = 40.0


def _sparsh(found: Found, *argv: str) -> tuple[int, str]:
    try:
        done = subprocess.run([found.program, *argv], capture_output=True, text=True,
                              timeout=PHONE_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return 1, f"`sparsh {argv[0]}` took longer than {PHONE_TIMEOUT:.0f}s"
    return done.returncode, (done.stdout + done.stderr).strip()


#: What each ``--awake`` word does, said back.
SCREEN = {"working": "kept on, then your own timeout 2 minutes after the last step",
          "always": "never asleep (a phone set aside for the agent)",
          "off": "left to its own timeout"}


def from_cable(found: Found) -> tuple[int, str | None, str]:
    """``sparsh tcpip``: (exit code, the address it now listens at, what
    to say). The address comes back even when the connect after it
    didn't: the phone was told, and the person may try it again."""
    import json

    code, said = _sparsh(found, "tcpip", "--json")
    try:
        done = json.loads(said.splitlines()[-1]) if said else {}
    except ValueError:
        return code or 1, None, said
    if not isinstance(done, dict) or "address" not in done:
        return code or 1, None, said
    if not done.get("connected"):
        return 1, done["address"], (f"the phone was told to listen at {done['address']}, "
                                    f"but didn't answer there: {done.get('said', '')}")
    return 0, done["address"], f"the phone listens over Wi-Fi at {done['address']}"


#: Where start-wda-from-linux.sh forwards WebDriverAgent to.
WDA_HERE = "http://127.0.0.1:8100"


def iphone_answers(found: Found, url: str) -> tuple[bool, str]:
    """(whether WebDriverAgent at ``url`` answers, what to say): Sparsh's
    own status, asked with ``SPARSH_WDA`` set, so the check is Sparsh's."""
    from sarathi.siblings import read_status

    try:
        status = read_status(found.program, "sparsh.status.v1", env={"SPARSH_WDA": url})
    except ValueError as exc:
        return False, f"sparsh couldn't be asked: {exc}"
    mine = [p for p in status.get("phones") or [] if p.get("serial") == url]
    note = ((status.get("wda") or {}).get("note") or "").strip()
    if mine and mine[0].get("state") == "device":
        return True, f"the iPhone answers at {url}" + (f" ({note})" if note else "")
    return False, (f"nothing answers at {url}: start WebDriverAgent with the iPhone on "
                   "this computer's cable (in Sparsh's folder: PREFIX=com.you.sparsh "
                   "scripts/start-wda-from-linux.sh), leave it running, and try again")


def run(args, found: Found) -> int:
    try:
        config = load()
    except ConfigError as exc:
        print(f"error: {exc}")
        return 2
    if args.off:
        settings_path().write_text(render(replace(config, phone=None)))
        print("the phone is off in sarathi.toml; `sarathi down && sarathi up` to stop "
              "giving it to Dvara")
        return 0
    if found.program is None:
        print("error: sparsh was not found -- install it (its SETUP.md), or set "
              "SARATHI_SPARSH=/path/to/sparsh (see `sarathi status`)")
        return 2
    words = list(args.words)
    if words[:1] == ["iphone"]:
        if len(words) > 2:
            print("error: sarathi phone iphone [URL] -- one address, like " + WDA_HERE)
            return 2
        url = (words[1] if len(words) == 2 else
               (config.phone.wda if config.phone and config.phone.wda else WDA_HERE))
        ok, said = iphone_answers(found, url)
        if not ok:
            print(f"error: {said} -- not saved")
            return 1
        print(said)
        awake = args.awake or (config.phone.awake if config.phone else None)
        old = config.phone
        settings_path().write_text(render(replace(config, phone=Phone(wda=url, awake=awake))))
        print(f"the iPhone is on in {settings_path()}"
              + (f", in place of the Android at {old.address}" if old and old.address else ""))
        if config.road == "podman":
            print("  the containers reach it at "
                  + url.replace("127.0.0.1", "host.containers.internal")
                       .replace("localhost", "host.containers.internal"))
        print("  keep the iPhone unlocked while an agent works it, and WebDriverAgent "
              "running; it is signed for 7 days with a free Apple ID")
        _mention_door(config)
        if old is not None and old.wda == url and not args.awake:
            print("  the same address as before: nothing to restart")
            return 0
        print("next: `sarathi down && sarathi up` (or just `sarathi up`)")
        return 0
    if words[:1] == ["pair"]:
        if len(words) != 3:
            print("error: sarathi phone pair ADDRESS CODE -- both as the phone's "
                  "'Pair device with pairing code' screen shows them")
            return 2
        code, said = _sparsh(found, "pair", words[1], words[2])
        print(said)
        if code == 0:
            print("next: sarathi phone ADDRESS -- the address on the Wireless debugging "
                  "page itself, not the pairing one")
        return code
    if words == ["tcpip"]:
        code, address, said = from_cable(found)
        print(said if code == 0 else f"error: {said.removeprefix('sparsh: ')}")
        if code != 0:
            return 1
        words = [address]
    if len(words) > 1:
        print("error: sarathi phone [ADDRESS] -- one address, like 192.168.1.23:41234")
        return 2
    address = words[0] if words else (config.phone.address if config.phone else None)
    if address:
        code, said = _sparsh(found, "connect", address)
        print(said)
        if code != 0:
            print("error: not saved -- check the phone's Wireless debugging page for its "
                  "address, and pair first if this computer is new to it "
                  "(sarathi phone pair ADDRESS CODE)")
            return 1
    elif config.road == "podman":
        print("note: on the podman road the containers can't reach a phone on a cable: "
              "give its Wi-Fi address (sarathi phone ADDRESS)")
    awake = args.awake or (config.phone.awake if config.phone else None)
    settings_path().write_text(render(replace(config, phone=Phone(address=address,
                                                                  awake=awake))))
    where = f"over Wi-Fi at {address}" if address else "on a USB cable"
    print(f"the phone is on in {settings_path()}, {where}")
    if args.awake:
        print(f"  its screen while an agent works it: {SCREEN[args.awake]}")
    _mention_door(config)
    if address and config.phone is not None and config.phone.address == address \
            and not args.awake:
        print("  the same address as before: nothing to restart, Sparsh reconnects by itself")
        return 0
    print("next: `sarathi down && sarathi up` (or just `sarathi up`)")
    return 0


def _mention_door(config) -> None:
    """What would still keep the phone from Dvara's agents: nobody marked
    for it, or the Telegram agent's [tools] leaving Sparsh out."""
    if config.door is not None and not _anyone_marked(config.door.path("actors")):
        print(f"  nobody in {config.door.actors} is marked `phone = true` yet: add it "
              "under your own [actor.…] so Dvara's agents may work the phone for you")
    if config.door is not None and config.door.telegram:
        package = config.door.path("root") / config.door.telegram / "agent.toml"
        if not _lets_phone_in(package):
            print(f"  {config.door.telegram}, the agent on Telegram, can't use the phone: "
                  f"its [tools] in {package} leaves out \"mcp__sparsh__*\" -- add it "
                  "there (Sparsh still holds Send, Pay and Delete for your yes)")


def _anyone_marked(actors) -> bool:
    import tomllib

    try:
        data = tomllib.loads(actors.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return any(isinstance(body, dict) and body.get("phone") is True
               for body in (data.get("actor") or {}).values())


def _lets_phone_in(package) -> bool:
    """Whether an agent package lets Sparsh's tools in. Its ``[tools]
    allow``, when present, is a complete list (Yantra's rule): one that
    leaves out ``mcp__sparsh__*`` hides the phone from that agent however
    the door was started. A schedule on a real phone found it: its
    person unlocked the phone when asked, and the run had no phone tool.
    A package that can't be read is not this command's to judge."""
    import fnmatch
    import tomllib

    try:
        tools = tomllib.loads(package.read_text()).get("tools") or {}
    except (OSError, tomllib.TOMLDecodeError):
        return True
    name = "mcp__sparsh__look"
    if any(fnmatch.fnmatch(name, pat) for pat in tools.get("deny") or ()):
        return False
    allow = tools.get("allow")
    return allow is None or any(fnmatch.fnmatch(name, pat) for pat in allow)
