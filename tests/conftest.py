"""The small world every test runs in: its own PATH, its own folders.

Nothing from the real machine leaks in -- not the siblings on its PATH,
not the checkouts beside this one, not the settings in ~/.config.
"""

from __future__ import annotations

import json
import socket
import stat
import sys
from pathlib import Path

import pytest

from sarathi import services, siblings


def program(where: Path, name: str, prints: str = "", code: int = 0) -> Path:
    where.mkdir(parents=True, exist_ok=True)
    path = where / name
    path.write_text(f"#!/bin/sh\n/bin/cat <<'EOF'\n{prints}\nEOF\nexit {code}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture
def world(tmp_path, monkeypatch):
    """An empty PATH and an empty folder of checkouts; nothing else is seen."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("SARATHI_SIBLINGS", str(tmp_path / "checkouts"))
    monkeypatch.setenv("SARATHI_CONFIG", str(tmp_path / "config"))
    monkeypatch.setenv("SARATHI_STATE", str(tmp_path / "state"))
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_HOST", "YANTRA_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    for s in siblings.SIBLINGS:
        monkeypatch.delenv(siblings.env_name(s), raising=False)
    return tmp_path


# ---- siblings that really start (test_up, test_door) ------------------------------

FAKE = """#!{python}
import http.server, json, os, sys, time
name, args = {name!r}, sys.argv[1:]
if args[-2:] == ["status", "--json"]:
    print(json.dumps({status}))
    sys.exit(0)
seen = os.environ["FAKE_SEEN"]
keep = {{k: v for k, v in os.environ.items()
        if k.startswith(("YANTRA_", "SAMAY_", "OLLAMA_", "ANTHROPIC_", "OPENAI_",
                          "DVARA_", "TELEGRAM_", "SETU_WINDOW_", "SETU_PAGE_"))}}
tag = name + ("-page" if "page" in args else "")
with open(os.path.join(seen, tag + ".json"), "w") as out:
    json.dump({{"argv": args, "env": keep, "cwd": os.getcwd(), "at": time.monotonic()}}, out)
if os.environ.get("FAKE_CRASH") == name:
    print("Traceback: the web extra is not installed")
    sys.exit(3)
port = int(args[args.index("--port") + 1])
if name == "samay":
    print(f"page: http://127.0.0.1:{{port}}/#token=t0k3n", flush=True)
if tag in ("setu", "dvara-page"):          # as `setu serve` and `dvara page` print it
    print(f"{{tag}}'s page:\\n  http://127.0.0.1:{{port}}/#token=k-{{tag}}", flush=True)
http.server.HTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
"""

SAMAY_IDLE = {"format": "samay.status.v1", "serving": False, "url": None,
              "schedules": {"active": 0, "paused": 0}}


def fake(where: Path, name: str, status: dict | None = None) -> Path:
    path = where / name
    path.write_text(FAKE.format(python=sys.executable, name=name, status=status or {}))
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def stage(world, monkeypatch):
    """Siblings that really start, settings on free ports; everything stopped after."""
    bin_dir = world / "bin"
    fake(bin_dir, "yantra")
    fake(bin_dir, "samay", SAMAY_IDLE)
    program(bin_dir, "setu", json.dumps({"format": "setu.status.v1", "connections": []}))
    seen = world / "seen"
    seen.mkdir()
    monkeypatch.setenv("FAKE_SEEN", str(seen))
    monkeypatch.setattr(services, "READY_TIMEOUT", 10.0)
    ports = {"web": free_port(), "clock": free_port()}
    settings(world, ports)
    yield {"world": world, "seen": seen, "ports": ports}
    services.down()


def settings(world: Path, ports: dict, extra: str = "", provider: str = "ollama") -> None:
    (world / "config").mkdir(exist_ok=True)
    (world / "config" / "sarathi.toml").write_text(
        f'[model]\nprovider = "{provider}"\nmodel = "gemma4:12b"\n'
        f'[web]\nport = {ports["web"]}\n[clock]\nport = {ports["clock"]}\n'
        # the pages stay off unless a test turns them on: their programs
        # here are stand-ins that only print a status
        + extra + ("" if "[pages]" in extra else "\n[pages]\non = false\n"))


