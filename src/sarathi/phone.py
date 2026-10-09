"""`sarathi phone`: your phone, for the door's agents and the containers.

    sarathi phone                        on, for a phone on a USB cable
    sarathi phone pair ADDRESS CODE      trust this computer over Wi-Fi, once
    sarathi phone ADDRESS                on, reached over Wi-Fi at ADDRESS
    sarathi phone --off

WIRING, NOT A PHONE. Sparsh knows phones; this only writes ``[phone]``
into sarathi.toml and runs the Sparsh that ``sarathi status`` found for
the two things that need the phone in front of you: ``pair`` (the six
digits on its "Pair device with pairing code" screen) and a first
``connect``, so a wrong address is said now rather than at ``up``.

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
    settings_path().write_text(render(replace(config, phone=Phone(address=address))))
    where = f"over Wi-Fi at {address}" if address else "on a USB cable"
    print(f"the phone is on in {settings_path()}, {where}")
    if config.door is not None and not _anyone_marked(config.door.path("actors")):
        print(f"  nobody in {config.door.actors} is marked `phone = true` yet: add it "
              "under your own [actor.…] so Dvara's agents may work the phone for you")
    if config.door is not None and config.door.telegram:
        package = config.door.path("root") / config.door.telegram / "agent.toml"
        if not _lets_phone_in(package):
            print(f"  {config.door.telegram}, the agent on Telegram, can't use the phone: "
                  f"its [tools] in {package} leaves out \"mcp__sparsh__*\" -- add it "
                  "there (Sparsh still holds Send, Pay and Delete for your yes)")
    print("next: `sarathi down && sarathi up` (or just `sarathi up`)")
    return 0


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
