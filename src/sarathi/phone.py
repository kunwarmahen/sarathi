"""`sarathi phone`: your phone, for the door's agents and the containers.

    sarathi phone                        on, for a phone on a USB cable
    sarathi phone tcpip                  on, over Wi-Fi: the phone on the cable is
                                         told to listen, and its address saved
    sarathi phone pair ADDRESS CODE      trust this computer over Wi-Fi, once
    sarathi phone ADDRESS                on, reached over Wi-Fi at ADDRESS
    sarathi phone iphone [URL]           on, an iPhone: its WebDriverAgent at URL
                                         (http://127.0.0.1:8100 when not given)
    sarathi phone --off

Several phones at once, each by a name (``[phone.NAME]``; whose each is,
Dvara's actors file says with ``phones = ["NAME"]``):

    sarathi phone add NAME               the phone on this computer's cable
    sarathi phone add NAME tcpip         the same, told to listen over Wi-Fi
    sarathi phone add NAME ADDRESS       one over Wi-Fi at ADDRESS
    sarathi phone add NAME SERIAL        one adb sees by its serial (emulator-5554)
    sarathi phone add NAME iphone [URL]  an iPhone
    sarathi phone remove NAME
    sarathi phone list                   the phones written down, and who answers

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
WebDriverAgent, an app on the phone that Sparsh's own script builds (on a
Mac, once a week) and ``sparsh iphone`` starts, here, with the iPhone on
this computer's cable: tunnel, developer image, port 8100, all without
sudo, and again by itself whenever the phone is plugged back in.
``iphone`` asks Sparsh whether WebDriverAgent answers; at this
computer's own address and not answering, it is started first, behind
(``sparsh iphone``, in a user unit of its own, ``sarathi-iphone``, so a
restart of the home page doesn't take it down), and ``up`` does the same
for a saved one. Its address is saved as ``[phone] wda``, beside any Android
address: Sparsh uses whichever phone answers, so an iPhone swapped for an
Android on the cable, or back, needs nothing run here. While an Android
answers, ``up`` starts the iPhone's unit without waiting for it, so it
is ready the moment the iPhone is plugged back in. The containers reach
it at ``host.containers.internal`` (podman.py). ``sparsh iphone --stop`` stops
it; ``down`` leaves it, since ``down && up`` is how settings are applied.

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

import os
import shutil
import subprocess
from dataclasses import replace

from sarathi.config import (
    PHONE_NAME,
    ConfigError,
    NamedPhone,
    Phone,
    load,
    render,
    settings_path,
    with_phone,
    without_phone,
)
from sarathi.siblings import Found

#: How long a pair or a first connect may take.
PHONE_TIMEOUT = 40.0


def _sparsh(found: Found, *argv: str, env: dict[str, str] | None = None) -> tuple[int, str]:
    try:
        done = subprocess.run([found.program, *argv], capture_output=True, text=True,
                              env={**os.environ, **env} if env else None,
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


#: Where `sparsh iphone` forwards WebDriverAgent to.
WDA_HERE = "http://127.0.0.1:8100"
#: How long `sparsh iphone --background` may take (a first developer
#: image is a download).
IPHONE_TIMEOUT = 300.0
#: The user unit `sparsh iphone` runs in, when systemd is there.
IPHONE_UNIT = "sarathi-iphone"


def is_here(url: str) -> bool:
    """WebDriverAgent forwarded to this computer: `sparsh iphone` can start it."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    return parts.hostname in ("127.0.0.1", "localhost") and parts.port in (8100, None)


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
    return False, (f"nothing answers at {url}: plug the iPhone into this computer, "
                   "unlock it, and run `sparsh iphone`" if is_here(url) else
                   f"nothing answers at {url}: is WebDriverAgent running on that iPhone?")


def start_behind(found: Found) -> None:
    """``sparsh iphone`` in its own unit, not waited for: it waits for the
    iPhone itself, and starts WebDriverAgent whenever it is plugged in."""
    if shutil.which("systemd-run"):
        # its own unit, so it outlives whatever asked: the home page is a
        # user service, and what it starts would stop when it restarts.
        # A unit already running is left as it is.
        subprocess.run(["systemd-run", "--user", "--quiet", "--collect", f"--unit={IPHONE_UNIT}",
                        found.program, "iphone"], capture_output=True, check=False, timeout=30)


def android_answers(found: Found) -> str | None:
    """The Android Sparsh can use now (its model, or its serial), or None:
    asked with no iPhone named, so only adb's phones are counted."""
    from sarathi.siblings import read_status

    try:
        status = read_status(found.program, "sparsh.status.v1", env={"SPARSH_WDA": ""})
    except ValueError:
        return None
    ready = [p for p in status.get("phones") or []
             if p.get("state") == "device" and not str(p.get("serial", "")).startswith("http")]
    return (ready[0].get("model") or ready[0].get("serial")) if ready else None


def iphone_ready(found: Found, url: str) -> tuple[bool, str]:
    """:func:`iphone_answers`, after starting WebDriverAgent behind when it is
    this computer's and doesn't answer yet. ``sparsh iphone`` does every
    step, and keeps at it while the phone is away, so a phone that was
    unplugged, restarted or updated comes back by itself."""
    ok, said = iphone_answers(found, url)
    if ok or not is_here(url):
        return ok, said
    start_behind(found)
    try:
        done = subprocess.run([found.program, "iphone", "--background"], capture_output=True,
                              text=True, timeout=IPHONE_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return False, (f"the iPhone didn't answer in {IPHONE_TIMEOUT:.0f}s; Sparsh keeps "
                       "trying behind (~/.sparsh/iphone.log)")
    if done.returncode != 0:
        words = [ln for ln in (done.stdout + done.stderr).splitlines() if ln.strip()]
        why = words[-1].removeprefix("sparsh: ") if words else "it said nothing"
        return False, f"the iPhone couldn't be started: {why}"
    return iphone_answers(found, url)


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
    if words[:1] in (["add"], ["remove"], ["list"]) or (
            not words and config.phone is not None and config.phone.named):
        return named_step(args, found, config, words)
    if words[:1] == ["iphone"]:
        if len(words) > 2:
            print("error: sarathi phone iphone [URL] -- one address, like " + WDA_HERE)
            return 2
        url = (words[1] if len(words) == 2 else
               (config.phone.wda if config.phone and config.phone.wda else WDA_HERE))
        if is_here(url):
            print("starting the iPhone, if it isn't running (sparsh iphone)...", flush=True)
        ok, said = iphone_ready(found, url)
        if not ok:
            print(f"error: {said} -- not saved")
            return 1
        print(said)
        awake = args.awake or (config.phone.awake if config.phone else None)
        old = config.phone
        settings_path().write_text(render(replace(config, phone=Phone(
            wda=url, address=old.address if old else None, awake=awake))))
        print(f"the iPhone is on in {settings_path()}"
              + (f", beside the Android at {old.address} (the one that answers is used)"
                 if old and old.address else ""))
        if config.road == "podman":
            print("  the containers reach it at "
                  + url.replace("127.0.0.1", "host.containers.internal")
                       .replace("localhost", "host.containers.internal"))
        print("  keep the iPhone unlocked while an agent works it; WebDriverAgent comes "
              "back by itself when it is plugged in again (`sparsh iphone --stop` stops "
              "it), and is signed for 7 days with a free Apple ID")
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
        print("  the containers reach the phone on this computer's cable through its "
              "adb (sarathi-adb, started by `up`)")
    awake = args.awake or (config.phone.awake if config.phone else None)
    wda = config.phone.wda if config.phone else None
    settings_path().write_text(render(replace(config, phone=Phone(address=address, wda=wda,
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
        print(f"  nobody in {config.door.actors} has the phone yet (`phone = true`, or "
              f"`phones = [...]` with named phones): add it "
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
    return any(isinstance(body, dict) and (body.get("phone") is True or body.get("phones"))
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


def cable_serial(found: Found) -> tuple[str | None, str]:
    """The Android on this computer's USB cable, by its adb serial:
    (serial, what was found), or (None, why not)."""
    import json

    code, said = _sparsh(found, "status", "--json")
    if code != 0:
        return None, said
    try:
        phones = json.loads(said).get("phones") or []
    except ValueError:
        return None, "sparsh status didn't print JSON"
    cabled = [p for p in phones if p.get("state") == "device"
              and ":" not in str(p.get("serial")) and not str(p.get("serial")).startswith(
                  ("http", "emulator-"))]
    if not cabled:
        return None, ("no Android is on a USB cable here, ready (plugged in, USB "
                      "debugging on, and allowed on the phone)")
    if len(cabled) > 1:
        return None, ("more than one Android is on a cable ("
                      + ", ".join(p["serial"] for p in cabled) + "): unplug all but one")
    phone = cabled[0]
    return phone["serial"], f"{phone['serial']} ({phone.get('model') or '?'}), on the cable"


def attached_serial(found: Found, serial: str) -> tuple[str | None, str]:
    """An adb serial Sparsh sees now (``emulator-5554``, a second cable):
    (serial, what was found), or (None, why not)."""
    import json

    code, said = _sparsh(found, "status", "--json")
    if code != 0:
        return None, said
    try:
        phones = json.loads(said).get("phones") or []
    except ValueError:
        return None, "sparsh status didn't print JSON"
    match = next((p for p in phones if p.get("serial") == serial), None)
    if match is None or match.get("state") != "device":
        return None, (f"no phone called {serial} is attached and ready (`sparsh devices` "
                      "lists them)")
    return serial, f"{serial} ({match.get('model') or '?'})"


def named_step(args, found: Found, config, words: list[str]) -> int:
    """``sarathi phone add|remove|list`` (the module docstring)."""
    phone = config.phone
    if words[:1] == ["remove"]:
        if len(words) != 2:
            print("error: sarathi phone remove NAME")
            return 2
        try:
            kept = without_phone(phone, words[1])
        except ConfigError as exc:
            print(f"error: {exc}")
            return 2
        settings_path().write_text(render(replace(config, phone=kept)))
        print(f"{words[1]} is no longer in {settings_path()}"
              + ("" if kept else "; that was the last, so the phone is off"))
        print("  if it's in someone's phones in Dvara's actors file, take it out there too")
        print("next: `sarathi down && sarathi up`")
        return 0
    if words[:1] != ["add"]:
        named = phone.named if phone else ()
        if not named:
            print("no phones are named; `sarathi phone add NAME ...` names one")
            return 0
        import json

        from sarathi.services import phone_env

        # asked with the names, as Yantra and Dvara are: Sparsh asks an
        # iPhone only at an address it is given
        code, said = _sparsh(found, "status", "--json", env=phone_env(config))
        answering = {p.get("serial") for p in (json.loads(said).get("phones") or [])
                     if p.get("state") == "device"} if code == 0 else set()
        for each in named:
            here = "answers" if each.where in answering else "not answering"
            awake = f", awake {each.awake}" if each.awake else ""
            print(f"{each.name}: {each.kind} at {each.where} -- {here}{awake}")
        return 0
    if len(words) < 2 or not PHONE_NAME.fullmatch(words[1]):
        print("error: sarathi phone add NAME [tcpip | ADDRESS | iphone [URL]] -- NAME in "
              "lower case letters, digits and dashes (nexus, asha-iphone)")
        return 2
    name, rest = words[1], words[2:]
    awake = args.awake
    saved = (phone.wda, phone.address) if phone is not None and not phone.named else ()
    if rest[:1] == ["iphone"] and (rest[1] if len(rest) > 1 else WDA_HERE) in saved:
        # NAMING WHAT IS SAVED ASKS NOTHING OF THE PHONE: an iPhone in a
        # drawer must not stop the Android on the cable from being named
        said = "the iPhone already saved, named (not asked: it needn't be plugged in)"
        new = NamedPhone(name=name, wda=rest[1] if len(rest) > 1 else WDA_HERE,
                         awake=awake or phone.awake)
    elif rest[:1] and rest[0] in saved and ":" in rest[0]:
        said = "the Android already saved, named (not asked: it needn't be reachable)"
        new = NamedPhone(name=name, address=rest[0], awake=awake or phone.awake)
    elif rest[:1] == ["iphone"]:
        url = rest[1] if len(rest) > 1 else WDA_HERE
        if is_here(url):
            print("starting the iPhone, if it isn't running (sparsh iphone)...", flush=True)
        ok, said = iphone_ready(found, url)
        if not ok:
            print(f"error: {said} -- not saved")
            return 1
        new = NamedPhone(name=name, wda=url, awake=awake)
    elif rest == ["tcpip"]:
        code, address, said = from_cable(found)
        if code != 0:
            print(f"error: {said.removeprefix('sparsh: ')}")
            return 1
        new = NamedPhone(name=name, address=address, awake=awake)
    elif rest and ":" not in rest[0] and len(rest) == 1:
        serial, said = attached_serial(found, rest[0])
        if serial is None:
            print(f"error: {said}")
            return 1
        new = NamedPhone(name=name, serial=serial, awake=awake)
    elif rest:
        code, said = _sparsh(found, "connect", rest[0])
        if code != 0:
            print(f"error: {said} -- not saved")
            return 1
        new = NamedPhone(name=name, address=rest[0], awake=awake)
    else:
        serial, said = cable_serial(found)
        if serial is None:
            print(f"error: {said}")
            return 1
        new = NamedPhone(name=name, serial=serial, awake=awake)
    try:
        kept = with_phone(phone, new)
    except ConfigError as exc:
        print(f"error: {exc}")
        return 2
    print(said)
    settings_path().write_text(render(replace(config, phone=kept)))
    print(f"{name} is in {settings_path()}: {new.kind} at {new.where}")
    print(f"  give it to someone in Dvara's actors file: phones = [\"{name}\"] under "
          f"their [actor.…]")
    if config.road == "podman" and new.serial:
        print("  the containers reach it through this computer's adb (sarathi-adb)")
    print("next: `sarathi down && sarathi up`")
    return 0
