"""What is here, and what each piece says about itself.

The bias these tests encode: SARATHI NEVER CLAIMS MORE THAN IT SAW. A
sibling is reported where it was found and by which rule; its status is
the sibling's own words or a reason they could not be read -- a format
Sarathi does not know is refused, not guessed at; and a missing piece
comes with the one line that fixes it. Each test builds its own small
world (a PATH, a folder of checkouts) so the real machine never leaks in.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from sarathi import siblings
from sarathi.cli import main

SETU = {"format": "setu.status.v1", "connections": [{"ref": "gmail:mine"},
                                                     {"ref": "homeassistant:house"}]}
SAMAY = {"format": "samay.status.v1", "serving": True, "url": "http://127.0.0.1:8780/",
         "schedules": {"active": 2, "paused": 1, "done": 0}}


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
    for s in siblings.SIBLINGS:
        monkeypatch.delenv(siblings.env_name(s), raising=False)
    return tmp_path


def everything(world: Path) -> None:
    bin_dir = world / "bin"
    program(bin_dir, "yantra")
    program(bin_dir, "setu", json.dumps(SETU))
    program(bin_dir, "samay", json.dumps(SAMAY))
    program(bin_dir, "dvara")
    program(bin_dir, "smritikosh-mcp")


def run(capsys, *argv) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def by_name(found):
    return {f.sibling.name: f for f in found}


def test_each_sibling_is_reported_with_its_own_words(world, capsys):
    everything(world)
    code, out = run(capsys, "status")
    assert code == 0
    assert "2 accounts connected: gmail:mine, homeassistant:house" in out
    assert "clock running at http://127.0.0.1:8780/; schedules: 2 active, 1 paused" in out


def test_a_path_you_set_wins_over_what_the_shell_would_run(world, monkeypatch):
    everything(world)
    mine = program(world / "elsewhere", "samay", json.dumps({**SAMAY, "serving": False}))
    monkeypatch.setenv("SARATHI_SAMAY", str(mine))
    samay = by_name(siblings.find_all())["samay"]
    assert (samay.program, samay.how) == (str(mine), "env")
    assert samay.said.startswith("clock not running (start it: samay serve)")


def test_a_checkout_beside_is_found_when_the_shell_has_none(world):
    made = program(world / "checkouts" / "dvara" / ".venv" / "bin", "dvara")
    dvara = by_name(siblings.find_all())["dvara"]
    assert (dvara.program, dvara.how) == (str(made), "beside")


def test_a_missing_piece_comes_with_the_line_that_fixes_it(world, capsys):
    everything(world)
    os.remove(world / "bin" / "samay")
    code, out = run(capsys, "status")
    assert code == 1
    line = next(x for x in out.splitlines() if x.startswith("samay "))
    assert line.endswith("not found -- install it, or set SARATHI_SAMAY=/path/to/samay")


def test_an_optional_piece_missing_does_not_fail(world, capsys):
    everything(world)
    os.remove(world / "bin" / "dvara")
    os.remove(world / "bin" / "smritikosh-mcp")
    code, out = run(capsys, "status")
    assert code == 0
    assert "not found (optional)" in out


def test_a_format_it_does_not_know_is_refused_not_guessed(world, capsys):
    everything(world)
    program(world / "bin", "setu", json.dumps({**SETU, "format": "setu.status.v2"}))
    code, out = run(capsys, "status")
    assert code == 1
    assert "found, but: `status --json` speaks 'setu.status.v2', not 'setu.status.v1'" in out
    assert "accounts connected" not in out


@pytest.mark.parametrize("prints, code, says", [
    ("not json at all", 0, "did not print JSON"),
    ("", 3, "failed"),
])
def test_a_status_that_cannot_be_read_says_why(world, prints, code, says):
    everything(world)
    program(world / "bin", "samay", prints, code)
    samay = by_name(siblings.find_all())["samay"]
    assert samay.program is not None and samay.said is None
    assert says in samay.error


def test_a_status_that_hangs_is_given_up_on(world, monkeypatch):
    everything(world)
    slow = world / "bin" / "samay"
    slow.write_text("#!/bin/sh\n/bin/sleep 5\n")
    monkeypatch.setattr(siblings, "STATUS_TIMEOUT", 0.2)
    assert "took longer than" in by_name(siblings.find_all())["samay"].error


def test_no_accounts_connected_says_how_to_connect_one(world):
    everything(world)
    program(world / "bin", "setu", json.dumps({**SETU, "connections": []}))
    assert "setu connect gmail" in by_name(siblings.find_all())["setu"].said


def test_the_json_answer_carries_each_siblings_own_status(world, capsys):
    everything(world)
    code, out = run(capsys, "status", "--json")
    data = json.loads(out)
    assert code == 0 and data["format"] == "sarathi.status.v1" and data["ok"] is True
    named = {s["name"]: s for s in data["siblings"]}
    assert named["setu"]["status"] == SETU
    assert named["yantra"] == {**named["yantra"], "found": True, "how": "path", "status": None}
