"""Every settings file, from the owner's home page.

A person who installed Sarathi should never have to open a TOML file:
who may talk to their agents, each agent, the standing answers, Setu's
settings and each site's rules, Sarathi's own settings and its keys are
all changed from the page. The files stay the record; the page is
another way to write them.

EACH PROGRAM WRITES ITS OWN FILE, AND CHECKS IT FIRST. Sarathi parses and
writes ``sarathi.toml`` (config.parse) and ``secrets.env``. Dvara's
files go through ``dvara settings`` (people, rules, agents), Setu's
through ``setu config`` and ``setu site file``. Each refuses a change it
could not load, with the words a hand edit would have got, so the page
can never leave a file that stops a program at its next start. Sarathi
holds no logic here: it finds the program, passes the change, and shows
what came back.

FORMS, AND THE WHOLE FILE AS TEXT. The page has a form for each setting
the programs know, and an "Edit as text" view of every file for anything
else. Text goes through the same check.

THE PHONE, FROM THIS COMPUTER (``phone``). Its Wi-Fi address can be typed
like any setting, but a phone that restarted stops listening and may
move: the page's buttons run Sparsh's own ``tcpip``, ``connect`` and
``pair`` here, where the USB cable is (phone.py says why), and save the
address that answered. The containers reach it only after ``sarathi up``
gives them a new address; the same address needs no restart, since
Sparsh reconnects by itself. An iPhone is one more button, ``iphone``:
Sparsh is asked whether WebDriverAgent answers at the address, and only
then is it saved, in place of any Android (Sarathi gives out one phone).

KEYS GO IN, NEVER OUT. A cloud key or the bot's token can be typed in;
the page is only ever told whether one is set.

THE OWNER'S ALONE. Every route here answers 403 to a person signed in
(home.py): these files decide what everybody else may do.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from sarathi.config import (
    AWAKE,
    BOT_TOKEN,
    DEFAULT_NTFY_PORT,
    KEY_NAMES,
    MEMORY_ROADS,
    PROVIDERS,
    ROADS,
    Config,
    ConfigError,
    Door,
    Phone,
    load,
    parse,
    read_secrets,
    render,
    save_secret,
    settings_path,
)

#: How long one program may take to answer.
WITHIN = 60.0
#: The keys the page may set (never read back).
KEYS = (*KEY_NAMES.values(), BOT_TOKEN)


class EditError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status


def program(name: str) -> str | None:
    from sarathi.siblings import SIBLINGS, find

    sibling = next(s for s in SIBLINGS if s.name == name)
    return find(sibling, ask=False).program


def _run(argv: list[str], stdin: str = "", env: dict | None = None,
         within: float = WITHIN) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, input=stdin, capture_output=True, text=True,
                              timeout=within, env={**os.environ, **(env or {})})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EditError(502, f"{Path(argv[0]).name} didn't answer: {exc}") from None


# ---- Dvara's files ---------------------------------------------------------------

def _dvara(config: Config) -> list[str]:
    door = config.door
    if door is None:
        raise EditError(409, "Dvara is off: turn it on under Settings first")
    found = program("dvara")
    if found is None:
        raise EditError(409, "dvara wasn't found on this computer (see `sarathi status`)")
    return [found, "--root", str(door.path("root")), "--actors", str(door.path("actors")),
            "--state", str(door.path("state"))]


def dvara(config: Config, args: list[str], body: Any = None, *,
          within: float = WITHIN, model: bool = False) -> dict:
    """``dvara settings ARGS`` with ``body`` (JSON, or text as is) on stdin.
    ``model``: the call asks a model, so it gets this house's own."""
    stdin = body if isinstance(body, str) else (json.dumps(body) if body is not None else "")
    which = (["--provider", config.provider] + (["--model", config.model]
                                                if config.model else [])) if model else []
    done = _run(_dvara(config) + which + ["settings", *args], stdin, within=within)
    try:
        out = json.loads(done.stdout)
    except ValueError:
        raise EditError(502, (done.stderr or done.stdout).strip()[-400:]
                        or "dvara said nothing") from None
    if not out.get("ok"):
        raise EditError(400, out.get("error") or "dvara refused it")
    return out


#: A skill made a tool: one model call, maybe a retry, and its test.
TOOL_WITHIN = 300.0


def make_tool(config: Config, agent: str, person: str, skill: str) -> dict:
    """A person's learned skill made a tool (Dvara's promoting.py): its
    script runs once as a test, and it is kept only if that passes."""
    if not person or not skill:
        raise EditError(400, "say whose skill, and which")
    return dvara(config, ["tool", agent, "--person", person, "--skill", skill],
                 within=TOOL_WITHIN, model=True).get("tool") or {}


def unmake_tool(config: Config, agent: str, person: str, skill: str) -> str:
    """The tool taken back; the skill stays a recipe."""
    if not person or not skill:
        raise EditError(400, "say whose skill, and which")
    return dvara(config, ["tool", agent, "--person", person, "--skill", skill,
                          "--remove"]).get("untool") or skill


def dvara_examples(config: Config) -> str | None:
    from sarathi.door import dvara_examples as find_examples
    from sarathi.siblings import SIBLINGS, find

    found = find(next(s for s in SIBLINGS if s.name == "dvara"), ask=False)
    where = find_examples(found)
    return str(where) if where else None


# ---- Setu's ------------------------------------------------------------------------

def setu_settings() -> dict:
    setu = program("setu")
    if setu is None:
        return {"found": False, "settings": {}, "sites": []}
    done = _run([setu, "config"])
    settings = {}
    for line in done.stdout.splitlines():
        name, _, value = line.partition(": ")
        settings[name.strip()] = None if value.strip() == "(not set)" else value.strip()
    sites = []
    from sarathi.siblings import read_status
    try:
        status = read_status(setu, "setu.status.v1")
        sites = [c["id"] for c in status.get("connectors", []) if c.get("local")]
    except (ValueError, KeyError, TypeError):
        pass
    texts = {}
    for site in sites:
        try:
            texts[site] = setu_site(site)
        except EditError:
            pass
    return {"found": True, "settings": settings,
            "sites": [{"id": s, "text": texts.get(s, "")} for s in sites]}


def setu_set(name: str, value: str | None) -> str:
    setu = program("setu")
    if setu is None:
        raise EditError(409, "setu wasn't found on this computer")
    argv = [setu, "config", name] + (["--unset"] if value in (None, "") else [value])
    done = _run(argv)
    if done.returncode:
        raise EditError(400, (done.stderr or done.stdout).strip().removeprefix("error: "))
    return done.stdout.strip()


def setu_site(site: str, text: str | None = None) -> str:
    setu = program("setu")
    if setu is None:
        raise EditError(409, "setu wasn't found on this computer")
    done = _run([setu, "site", "file", site] + (["--set"] if text is not None else []),
                text or "")
    if done.returncode:
        raise EditError(400, (done.stderr or done.stdout).strip().removeprefix("error: "))
    return done.stdout


# ---- Sarathi's own -----------------------------------------------------------------

def sarathi_view(config: Config) -> dict:
    """sarathi.toml as the form shows it, and which keys are set."""
    door, phone = config.door, config.phone
    have = {**read_secrets(), **{k: v for k, v in os.environ.items() if k in KEYS}}
    try:
        text = settings_path().read_text()
    except OSError:
        text = ""
    return {
        "text": text, "providers": list(PROVIDERS), "roads": list(ROADS),
        "awake": list(AWAKE), "memory_roads": list(MEMORY_ROADS),
        "model": {"provider": config.provider, "model": config.model,
                  "base_url": config.base_url, "context_window": config.context_window},
        "yantra": {"port": config.web_port},
        "samay": {"on": config.clock_on, "port": config.clock_port},
        "run": {"road": config.road},
        "pages": {"on": config.pages.on, "sarathi_port": config.pages.home_port,
                  "setu_port": config.pages.setu_port, "dvara_port": config.pages.door_port},
        "dvara": None if door is None else {
            "port": door.port, "telegram": door.telegram, "owner": door.owner,
            "window_host": door.window_host, "window_port": door.window_port,
            "window_url": door.window_url, "ntfy": door.ntfy_port is not None,
            "ntfy_port": door.ntfy_port or DEFAULT_NTFY_PORT},
        "phone": None if phone is None else {"address": phone.address, "wda": phone.wda,
                                             "awake": phone.awake},
        "memory": {"via": config.memory},
        "keys": {k: k in have for k in KEYS},
    }


def _num(value, what: str, *, low: int = 1, high: int = 65535) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise EditError(400, f"{what} must be a number, not {value!r}") from None
    if not low <= number <= high:
        raise EditError(400, f"{what} must be between {low} and {high}")
    return number


def sarathi_apply(changes: dict) -> Config:
    """Apply the form's changes to sarathi.toml: checked by reading the
    result back as `up` will, the old file kept as .bak."""
    try:
        config = load()
    except ConfigError as exc:
        raise EditError(409, str(exc)) from None
    if "model" in changes:
        m = changes["model"]
        config = replace(config, provider=m.get("provider", config.provider),
                         model=m.get("model", config.model) or None,
                         base_url=m.get("base_url", config.base_url) or None,
                         context_window=_num(m.get("context_window", config.context_window),
                                             "the context window", low=1024,
                                             high=10_000_000))
    if "yantra" in changes:
        config = replace(config, web_port=_num(changes["yantra"].get("port"),
                                               "Yantra's port") or config.web_port)
    if "samay" in changes:
        s = changes["samay"]
        config = replace(config, clock_on=bool(s.get("on", config.clock_on)),
                         clock_port=_num(s.get("port"), "Samay's port") or config.clock_port)
    if "run" in changes:
        config = replace(config, road=changes["run"].get("road", config.road))
    if "pages" in changes:
        p, pages = changes["pages"], config.pages
        config = replace(config, pages=replace(
            pages, on=bool(p.get("on", pages.on)),
            home_port=_num(p.get("sarathi_port"), "the home page's port") or pages.home_port,
            setu_port=_num(p.get("setu_port"), "Setu's page's port") or pages.setu_port,
            door_port=_num(p.get("dvara_port"), "Dvara's page's port") or pages.door_port))
    if "dvara" in changes:
        d = changes["dvara"]
        if d is None or d.get("on") is False:
            config = replace(config, door=None)
        else:
            door = config.door or Door()
            ntfy = d.get("ntfy", door.ntfy_port is not None)
            config = replace(config, door=replace(
                door, port=_num(d.get("port"), "Dvara's port") or door.port,
                telegram=d.get("telegram", door.telegram) or None,
                owner=d.get("owner", door.owner) or "owner",
                window_host=d.get("window_host", door.window_host) or None,
                window_port=_num(d.get("window_port", door.window_port), "the window's port"),
                window_url=d.get("window_url", door.window_url) or None,
                ntfy_port=(_num(d.get("ntfy_port"), "ntfy's port") or door.ntfy_port
                           or DEFAULT_NTFY_PORT) if ntfy else None))
    if "phone" in changes:
        ph = changes["phone"]
        config = replace(config, phone=None if ph is None or ph.get("on") is False else
                         Phone(address=ph.get("address") or None,
                               wda=ph.get("wda") or None,
                               awake=ph.get("awake") or None))
    if "memory" in changes:
        config = replace(config, memory=changes["memory"].get("via", config.memory))
    return sarathi_text(render(config))


def sarathi_text(text: str) -> Config:
    """The whole of sarathi.toml as text: read as `up` reads it, then written."""
    try:
        config = parse(text, str(settings_path()))
    except ConfigError as exc:
        raise EditError(400, str(exc)) from None
    path = settings_path()
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    tmp = path.with_name(f".{path.name}.new")
    tmp.write_text(text)
    os.replace(tmp, path)
    return config


def phone_step(config: Config, body: dict) -> tuple[str, bool]:
    """One of the phone card's buttons: ``tcpip``, ``connect``, ``pair``
    or ``iphone`` (module docstring). (What to say, whether `sarathi up`
    is needed)."""
    from sarathi import phone as phone_cmd
    from sarathi.siblings import SIBLINGS, find

    found = find(next(s for s in SIBLINGS if s.name == "sparsh"), ask=False)
    if found.program is None:
        raise EditError(409, "sparsh wasn't found on this computer (see `sarathi status`)")
    do = str(body.get("do") or "")
    address = str(body.get("address") or "").strip()
    if do == "pair":
        code = str(body.get("code") or "").strip()
        if not address or not code:
            raise EditError(400, "pairing needs both the address and the six digits the "
                                 "phone's 'Pair device with pairing code' screen shows")
        status, said = phone_cmd._sparsh(found, "pair", address, code)
        if status:
            raise EditError(400, said.removeprefix("sparsh: "))
        return (f"{said}. Now Connect, with the address on the Wireless debugging page "
                "itself (not the pairing one).", False)
    if do == "iphone":
        url = str(body.get("wda") or "").strip() or phone_cmd.WDA_HERE
        ok, said = phone_cmd.iphone_answers(found, url)
        if not ok:
            raise EditError(400, f"{said} -- not saved")
        old = config.phone
        sarathi_apply({"phone": {"on": True, "wda": url,
                                 "awake": old.awake if old else None}})
        if old is not None and old.wda == url:
            return f"{said}. Same address as before: nothing to restart.", False
        return (f"{said}; saved, in place of any Android. Apply, so Yantra and Dvara "
                "use the iPhone.", True)
    if do == "tcpip":
        status, address, said = phone_cmd.from_cable(found)
        if status:
            raise EditError(400, said.removeprefix("sparsh: "))
    elif do == "connect":
        if not address:
            raise EditError(400, "type the phone's address first, like 192.168.1.23:5555")
        status, said = phone_cmd._sparsh(found, "connect", address)
        if status:
            raise EditError(400, f"{said.removeprefix('sparsh: ')} -- not saved. Is the "
                                 "phone listening? Turn it on from the cable, or check its "
                                 "Wireless debugging page")
    else:
        raise EditError(400, "the phone's steps are tcpip, connect, pair and iphone")
    old = config.phone
    moved = old is None or old.address != address
    sarathi_apply({"phone": {"on": True, "address": address,
                             "awake": old.awake if old else None}})
    moved = moved or (old is not None and old.wda is not None)
    if moved:
        return (f"{said}; saved. Apply, so the containers reach it at {address}.", True)
    return (f"{said}. Same address as before: nothing to restart. Yantra's phone panel "
            "finds it on its next look.", False)


def set_key(name: str, value: str) -> None:
    if name not in KEYS:
        raise EditError(400, f"the keys set here are {', '.join(KEYS)}")
    value = (value or "").strip()
    if not value or "\n" in value:
        raise EditError(400, "paste the key on one line")
    save_secret(name, value)


# ---- one look at everything --------------------------------------------------------

def snapshot(config: Config, strangers: list[str] | None = None) -> dict:
    """Everything the owner's Settings draws, each program asked once."""
    out: dict[str, Any] = {"sarathi": sarathi_view(config), "setu": setu_settings(),
                           "strangers": strangers or []}
    try:
        examples = dvara_examples(config) if config.door else None
        out["dvara"] = dvara(config, ["show"] + (["--examples", examples]
                                                 if examples else []))
        out["dvara_problem"] = None
    except EditError as exc:
        out["dvara"], out["dvara_problem"] = None, str(exc)
    return out
