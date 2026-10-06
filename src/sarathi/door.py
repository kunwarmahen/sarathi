"""`sarathi door`: your agents for other people, and for you on your phone.

The door is dvara: one always-on service that many people (and you, from
Telegram) talk to, each as themselves, each with their own allowance,
their own accounts and their own schedules. ``sarathi door`` turns it on
the way ``sarathi init`` chose the model: a few questions, and files
that say what was chosen.

    sarathi door                         ask: which agent a Telegram bot answers as
    sarathi door --telegram greeter      the same, without asking
    sarathi door --telegram-id 8675309   you, in a new actors file, on Telegram
    sarathi door --off                   stop starting it

WHAT IT WRITES, AND WHERE.

* ``[door]`` in sarathi.toml: on, its port, the bot's agent.
* secrets.env: ``DVARA_TOKEN``, made here (dvara refuses to serve
  without one, and nobody should have to invent 48 hex digits), and
  ``TELEGRAM_TOKEN``, typed at a hidden prompt -- BotFather's token for
  your bot. Never on the command line, where it would stay in history.
* dvara's own files, ONLY WHEN THEY ARE NOT THERE: an actors file with
  you in it as the owner, and a folder of agents copied from dvara's
  own examples. Both are dvara's formats, documented in dvara's
  tutorial; Sarathi writes a starting point and never touches them again.
  The agents are dvara's examples, not Sarathi's: Sarathi has no agent
  of its own.

WHO MAY TALK TO IT is the actors file, and only that. A Telegram user
not in it gets silence, and the door writes their id in its log, where
``sarathi status`` shows it -- which is also how you find your own id:
message your bot once, and read it there.
"""

from __future__ import annotations

import getpass
import os
import secrets as random
import shutil
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from sarathi.config import (
    BOT_TOKEN,
    DEFAULT_DOOR_PORT,
    DOOR_TOKEN,
    ConfigError,
    Door,
    load,
    read_secrets,
    render,
    save_secret,
    settings_path,
)
from sarathi.siblings import Found

#: How the door writes down a stranger, in its log (dvara's telegram.py).
STRANGER = "is not in the actors file"


def starter_actors(telegram_id: str | None) -> str:
    """A first actors file: the owner, and how to add the rest."""
    channel = (f'[[actor.owner.channel]]\nkind = "telegram"\nid   = {telegram_id}\n'
               if telegram_id else
               '# Your Telegram id: message your bot once, then `sarathi status`\n'
               '# shows it. Put it here and remove the #s:\n'
               '# [[actor.owner.channel]]\n# kind = "telegram"\n# id   = 8675309\n')
    return f"""\
# Who the door serves. Written once by `sarathi door`; it is yours now
# (dvara's format: its tutorial explains every key). Anyone not in this
# file gets no answer at all. Edits are picked up without a restart.

[actor.owner]
permissions = "ask"     # you may be asked before an agent changes anything
# Your own accounts (Gmail, Home Assistant...) from your phone too:
# setu = "~/.local/state/setu"

{channel}
# Someone else, with a Setu folder of their own (they connect their
# accounts from the chat with /connect gmail):
#
# [actor.priya]
# agents = ["greeter"]
# max_usd_per_day = 0.50
# setu = true
# [[actor.priya.channel]]
# kind = "telegram"
# id   = 1234567
"""


def dvara_examples(found: Found) -> Path | None:
    """dvara's own example agents, from the checkout its program lives in."""
    if found.program is None:
        return None
    checkout = Path(found.program).resolve().parent.parent.parent   # .venv/bin/dvara
    agents = checkout / "examples" / "agents"
    return agents if agents.is_dir() else None


def run(args, found: Found, *, ask: Callable[[str], str] = input,
        ask_secret: Callable[[str], str] = getpass.getpass,
        interactive: bool | None = None) -> int:
    if interactive is None:
        interactive = sys.stdin.isatty()
    try:
        config = load()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.off:
        settings_path().write_text(render(replace(config, door=None)))
        print("the door is off in sarathi.toml; `sarathi down && sarathi up` to stop it")
        return 0
    if found.program is None:
        print("error: dvara was not found -- install it, or set SARATHI_DVARA=/path/to/dvara "
              "(see `sarathi status`)", file=sys.stderr)
        return 2

    door = config.door or Door()
    said: list[str] = []
    telegram = args.telegram if args.telegram is not None else door.telegram
    if args.telegram is None and interactive and not door.telegram:
        telegram = ask("Which agent should a Telegram bot answer as? "
                       "(Enter: no bot, only the door's HTTP address) ").strip() or None
    door = replace(door, telegram=telegram or None,
                   port=args.port or door.port or DEFAULT_DOOR_PORT)

    have = read_secrets()
    if DOOR_TOKEN not in have:
        save_secret(DOOR_TOKEN, random.token_hex(24))
        said.append(f"made the door's own token ({DOOR_TOKEN}, in secrets.env)")
    if door.telegram and BOT_TOKEN not in have:
        if os.environ.get(BOT_TOKEN):
            save_secret(BOT_TOKEN, os.environ[BOT_TOKEN])
            said.append(f"{BOT_TOKEN} from your environment saved to secrets.env "
                        "(the units cannot see your shell)")
        elif interactive:
            value = ask_secret(f"Your bot's token from BotFather ({BOT_TOKEN}; hidden as "
                               "you type; Enter to skip): ").strip()
            if value:
                save_secret(BOT_TOKEN, value)
                said.append(f"{BOT_TOKEN} saved to secrets.env (readable only by you)")
        if BOT_TOKEN not in read_secrets():
            said.append(f"no {BOT_TOKEN} yet: run `sarathi door` in a terminal to paste "
                        "it; until then the door will not start")

    actors = door.path("actors")
    if not actors.exists():
        actors.parent.mkdir(parents=True, exist_ok=True)
        actors.write_text(starter_actors(args.telegram_id))
        said.append(f"wrote {door.actors}: you, as the owner"
                    + ("" if args.telegram_id else " (your Telegram id still to add)"))
    elif args.telegram_id:
        said.append(f"{door.actors} is already there and was left alone: add your id "
                    "to it yourself")
    root = door.path("root")
    if not root.is_dir() or not any(root.iterdir()):
        examples = dvara_examples(found)
        if examples is None:
            said.append(f"no agents at {door.root}, and dvara's examples were not found "
                        "to copy: put an agent package there")
        else:
            shutil.copytree(examples, root, dirs_exist_ok=True)
            names = ", ".join(sorted(p.name for p in root.iterdir() if p.is_dir()))
            said.append(f"copied dvara's example agents to {door.root} ({names}): "
                        "replace them with your own")
    if door.telegram and not (root / door.telegram).is_dir():
        said.append(f"there is no agent {door.telegram!r} in {door.root} for the bot "
                    "to answer as")

    settings_path().write_text(render(replace(config, door=door)))
    bot = f", a Telegram bot answering as {door.telegram}" if door.telegram else ""
    print(f"the door is on in {settings_path()}: port {door.port}{bot}")
    for line in said:
        print(f"  {line}")
    print("next: `sarathi down && sarathi up` (or just `sarathi up`)")
    return 0


def strangers(log_lines: list[str]) -> list[str]:
    """Who messaged the door and is not in the actors file, newest last."""
    seen: list[str] = []
    for line in log_lines:
        if STRANGER in line:
            who = line.split("telegram:", 1)[-1].split(STRANGER)[0].strip().split()[0]
            if who not in seen:
                seen.append(who)
    return seen
