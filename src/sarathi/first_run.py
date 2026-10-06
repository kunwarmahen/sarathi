"""`sarathi init`: the questions asked once, and the file they leave behind.

The first question is the one that splits Sarathi's readers in two:
**which model answers?** About half of them run a model on their own
machine with Ollama, and the rest use a cloud key. Neither is a default
hidden behind the other. Both are asked about the same way, and both get
a working file at the end.

THE LOCAL ROAD LOOKS BEFORE IT SUGGESTS. Ollama is asked which models are
already pulled, so the suggestion is one that will answer today. Yantra's
own default is preferred when it is there. Embedding models are never
offered: they cannot hold a conversation. A model that is not pulled is
written down anyway, with the one command that pulls it. Ollama not
running is not an error at setup time either: the file is written, and
the line says how to start it.

THE CLOUD ROAD NEVER TAKES A KEY ON THE COMMAND LINE, where it would
stay in the shell's history. It is typed at a hidden prompt and saved
to secrets.env, readable only by its owner. A key already in the
environment is used where it is and never copied.

Everything can be given as flags, so a script or a container can run
``sarathi init --provider ollama --model qwen3.8:latest`` with nobody
there to answer.
"""

from __future__ import annotations

import getpass
import json
import os
import sys
import urllib.request
from collections.abc import Callable

from sarathi.config import (
    DEFAULT_CLOCK_PORT,
    DEFAULT_WEB_PORT,
    KEY_NAMES,
    PROVIDERS,
    Config,
    render,
    save_secret,
    settings_path,
)

OLLAMA_URL = "http://localhost:11434"
#: Yantra's own default for the local road; suggested first when pulled.
PREFERRED_LOCAL = "qwen3.8:latest"


def ollama_root(base_url: str | None) -> str:
    root = (base_url or os.environ.get("OLLAMA_HOST") or OLLAMA_URL).rstrip("/")
    if not root.startswith("http"):
        root = f"http://{root}"
    return root.removesuffix("/v1")


def ollama_models(root: str, timeout: float = 3.0) -> list[str] | None:
    """The models Ollama has pulled, or None if it is not answering."""
    try:
        with urllib.request.urlopen(f"{root}/api/tags", timeout=timeout) as reply:
            data = json.load(reply)
    except (OSError, ValueError):
        return None
    return [m["name"] for m in data.get("models", []) if isinstance(m, dict) and "name" in m]


def chat_models(names: list[str]) -> list[str]:
    """Pulled models that can hold a conversation, the preferred one first."""
    talk = [n for n in names if "embed" not in n]
    return sorted(talk, key=lambda n: n != PREFERRED_LOCAL)


def run(args, *, ask: Callable[[str], str] = input,
        ask_secret: Callable[[str], str] = getpass.getpass,
        interactive: bool | None = None) -> int:
    if interactive is None:
        interactive = sys.stdin.isatty()
    path = settings_path()
    if path.exists() and not args.force:
        print(f"already set up: {path}\n"
              "edit it by hand, or start over with `sarathi init --force`")
        return 1

    provider = args.provider
    if provider is None:
        if not interactive:
            print(f"error: say which model answers: --provider {'|'.join(PROVIDERS)}",
                  file=sys.stderr)
            return 2
        print("Which model should answer?\n"
              "  1) one on this machine, through Ollama -- free, private, needs a GPU or patience\n"
              "  2) Anthropic's, with an API key\n"
              "  3) OpenAI's, with an API key")
        choice = ask("Choose 1, 2 or 3 [1]: ").strip() or "1"
        provider = {"1": "ollama", "2": "anthropic", "3": "openai"}.get(choice)
        if provider is None:
            print(f"error: {choice!r} is not one of 1, 2, 3", file=sys.stderr)
            return 2

    said: list[str] = []
    model = args.model
    if provider == "ollama":
        root = ollama_root(args.base_url)
        pulled = ollama_models(root)
        if pulled is None:
            said.append(f"Ollama is not answering at {root}: start it (`ollama serve`) "
                        "before `sarathi up`")
        else:
            offer = chat_models(pulled)
            if model is None and offer:
                model = offer[0]
                if interactive and len(offer) > 1:
                    print("Pulled models that can talk:")
                    for n, name in enumerate(offer, 1):
                        print(f"  {n}) {name}")
                    pick = ask(f"Choose one [1 = {offer[0]}]: ").strip()
                    if pick.isdigit() and 1 <= int(pick) <= len(offer):
                        model = offer[int(pick) - 1]
            if model is None:
                said.append(f"Ollama has no model that can talk yet: "
                            f"`ollama pull {PREFERRED_LOCAL}`")
            elif model not in pulled:
                said.append(f"{model} is not pulled yet: `ollama pull {model}`")
    else:
        key = KEY_NAMES[provider]
        if os.environ.get(key):
            said.append(f"using {key} from your environment (not copied anywhere)")
        elif interactive:
            value = ask_secret(f"{key} (hidden as you type; Enter to skip): ").strip()
            if value:
                where = save_secret(key, value)
                said.append(f"{key} saved to {where} (readable only by you)")
            else:
                said.append(f"no key saved: set {key} before `sarathi up`")
        else:
            said.append(f"no key saved: set {key} in the environment, or run "
                        "`sarathi init --force` in a terminal to type it")

    config = Config(provider=provider, model=model, base_url=args.base_url,
                    web_port=args.web_port or DEFAULT_WEB_PORT,
                    clock_on=not args.no_clock,
                    clock_port=args.clock_port or DEFAULT_CLOCK_PORT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(config))
    answering = f"{provider}, {model}" if model else f"{provider}, its default model"
    print(f"wrote {path}\n  answering: {answering}")
    for line in said:
        print(f"  {line}")
    print("next: `sarathi up`")
    return 0
