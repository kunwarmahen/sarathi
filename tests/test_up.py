"""Starting the pieces, and stopping only what was started.

The bias these tests encode: ONE OF EACH, AND NEVER SOMEONE ELSE'S. A
second `up` starts nothing new; a clock already running some other way
is left alone, because a second one would run every schedule twice; a
port someone else holds is reported, not fought over; `down` stops what
`up` wrote down and nothing more. And A START IS NOT A SUCCESS UNTIL THE
PORT ANSWERS: a piece that dies on its first breath is reported with
its own last words, not as "started".

The siblings here are small Python stand-ins that write down how they
were started and, when given --port, really listen on it.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import stat
import time


from sarathi import services
from sarathi.cli import main

from conftest import SAMAY_IDLE, fake, free_port, program, settings  # noqa: F401

def seen(stage, name: str) -> dict:
    return json.loads((stage["seen"] / f"{name}.json").read_text())


def run(capsys, *argv) -> tuple[int, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def test_up_starts_both_with_what_was_found_and_the_same_model(stage, capsys):
    code, out = run(capsys, "up")
    assert code == 0, out
    web, clock = stage["ports"]["web"], stage["ports"]["clock"]
    assert f"page   up at http://127.0.0.1:{web}/" in out
    assert f"clock  up at http://127.0.0.1:{clock}/#token=t0k3n" in out
    bin_dir = stage["world"] / "bin"
    page = seen(stage, "yantra")
    assert page["argv"] == ["--web", "--host", "127.0.0.1", "--port", str(web),
                            "--setu", str(bin_dir / "setu"), "--samay", str(bin_dir / "samay")]
    clock_seen = seen(stage, "samay")
    for got in (page["env"], clock_seen["env"]):
        assert got["YANTRA_PROVIDER"] == "ollama" and got["OLLAMA_MODEL"] == "gemma4:12b"
    assert clock_seen["env"]["SAMAY_YANTRA"] == str(bin_dir / "yantra")
    assert page["cwd"] == clock_seen["env"]["SAMAY_YANTRA_HOME"] == str(services.work_dir())


def test_the_clock_starts_before_the_page_that_asks_about_it(stage, capsys):
    run(capsys, "up")
    assert seen(stage, "samay")["at"] < seen(stage, "yantra")["at"]


def test_logs_and_records_that_hold_a_token_are_the_owners_alone(stage, capsys):
    run(capsys, "up")
    for folder in (services.log_path("clock").parent, services.state_dir() / "run"):
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    _, out = run(capsys, "status")
    assert "clock  running at http://127.0.0.1:" in out and "#token=t0k3n" in out


def test_a_second_up_starts_nothing_new(stage, capsys):
    run(capsys, "up")
    pid = services.records()["page"]["pid"]
    code, out = run(capsys, "up")
    assert code == 0
    assert f"page   already running at http://127.0.0.1:{stage['ports']['web']}/  (pid {pid})" \
        in out


def test_down_stops_what_up_started_and_status_says_so(stage, capsys):
    run(capsys, "up")
    pids = [r["pid"] for r in services.records().values()]
    _, out = run(capsys, "status")
    assert "started by `sarathi up`:" in out and "page   running at" in out
    _, out = run(capsys, "down")
    assert "page   stopped" in out and "clock  stopped" in out
    assert not any(services.alive(pid) for pid in pids)
    assert not services.answers(stage["ports"]["web"])
    _, out = run(capsys, "status")
    assert "started by `sarathi up`" not in out
    _, out = run(capsys, "down")
    assert "nothing started by `sarathi up` is running" in out


def test_a_clock_started_some_other_way_is_left_alone(stage, capsys):
    fake(stage["world"] / "bin", "samay",
         {**SAMAY_IDLE, "serving": True, "url": "http://127.0.0.1:8780/#token"})
    code, out = run(capsys, "up")
    assert code == 0
    assert "clock  already running at http://127.0.0.1:8780/#token, not started by Sarathi" \
        in out
    assert not (stage["seen"] / "samay.json").exists()
    assert "--samay" in seen(stage, "yantra")["argv"]


def test_a_port_someone_else_holds_is_reported_not_fought_over(stage, capsys):
    with socket.socket() as other:
        other.bind(("127.0.0.1", stage["ports"]["web"]))
        other.listen()
        code, out = run(capsys, "up")
    assert code == 1
    assert (f"page   not started: something else is listening on port "
            f"{stage['ports']['web']} (change web.port in sarathi.toml)") in out
    assert "page" not in services.records()


def test_a_piece_that_dies_at_once_is_reported_with_its_last_words(stage, capsys,
                                                                    monkeypatch):
    monkeypatch.setenv("FAKE_CRASH", "yantra")
    code, out = run(capsys, "up")
    assert code == 1
    assert "page   exited at once (code 3)" in out
    assert "| Traceback: the web extra is not installed" in out
    assert "page" not in services.records()


def test_a_piece_that_died_later_shows_as_stopped_with_its_log(stage, capsys):
    run(capsys, "up")
    pid = services.records()["clock"]["pid"]
    os.killpg(pid, signal.SIGKILL)
    deadline = time.monotonic() + 5
    while services.alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    _, out = run(capsys, "status")
    assert "clock  STOPPED -- it exited" in out


def test_with_the_clock_off_the_page_is_told_there_is_none(stage, capsys):
    settings(stage["world"], stage["ports"], extra="on = false\n")
    _, out = run(capsys, "up")
    assert "clock  off in sarathi.toml" in out
    assert seen(stage, "yantra")["argv"][-1] == "--no-samay"
    assert "clock" not in services.records()


def test_a_cloud_road_with_no_key_starts_nothing(stage, capsys):
    settings(stage["world"], stage["ports"], provider="anthropic")
    code, out = run(capsys, "up")
    assert code == 2
    assert "no key for anthropic: run `sarathi init` or set ANTHROPIC_API_KEY" in out
    assert services.records() == {}


def test_the_environment_outranks_secrets_env(stage, monkeypatch, capsys):
    settings(stage["world"], stage["ports"], provider="anthropic")
    (stage["world"] / "config" / "secrets.env").write_text("ANTHROPIC_API_KEY=from-file\n")
    run(capsys, "up")
    assert seen(stage, "yantra")["env"]["ANTHROPIC_API_KEY"] == "from-file"
    services.down()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-shell")
    run(capsys, "up")
    assert seen(stage, "yantra")["env"]["ANTHROPIC_API_KEY"] == "from-shell"
