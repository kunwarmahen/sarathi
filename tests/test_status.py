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
from pathlib import Path

import pytest

from sarathi import siblings
from sarathi.cli import main

from conftest import program

YANTRA = {"format": "yantra.status.v1", "version": "0.1.0", "provider": "ollama",
          "model": "qwen3.8:latest", "problems": []}
SETU = {"format": "setu.status.v1", "connections": [{"ref": "gmail:mine"},
                                                     {"ref": "homeassistant:house"}]}
SAMAY = {"format": "samay.status.v1", "serving": True, "url": "http://127.0.0.1:8780/",
         "schedules": {"active": 2, "paused": 1, "done": 0}}
DVARA = {"format": "dvara.status.v1", "serving": True, "url": "http://127.0.0.1:8765",
         "running": {"command": "dvara serve"}, "agents": ["greeter", "minder"],
         "people": 3, "problems": []}


def everything(world: Path) -> None:
    bin_dir = world / "bin"
    program(bin_dir, "yantra", json.dumps(YANTRA))
    program(bin_dir, "setu", json.dumps(SETU))
    program(bin_dir, "samay", json.dumps(SAMAY))
    program(bin_dir, "dvara", json.dumps(DVARA))
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
    assert named["yantra"]["status"] == YANTRA
    assert named["smritikosh"] == {**named["smritikosh"], "found": True, "how": "path",
                                   "status": None}


def test_the_door_says_whether_it_is_serving_not_just_that_it_was_found(world, capsys):
    everything(world)
    code, out = run(capsys, "status")
    assert "door serving at http://127.0.0.1:8765 (dvara serve); 2 agents, 3 people" in out


@pytest.mark.parametrize("status, says", [
    ({**DVARA, "serving": False, "url": None, "running": None}, "door not serving; 2 agents"),
    ({**DVARA, "serving": False, "url": None, "running": {"command": "dvara say"}},
     "door not serving: dvara say is using its folder"),
    ({**DVARA, "url": "http://0.0.0.0:8765"}, "door serving (dvara serve)"),
    ({**DVARA, "problems": ["no actors file at /x"]}, "; no actors file at /x"),
])
def test_what_the_door_says_is_repeated_in_its_own_terms(world, status, says):
    everything(world)
    program(world / "bin", "dvara", json.dumps(status))
    assert says in by_name(siblings.find_all())["dvara"].said


def test_the_door_is_asked_about_the_folders_sarathi_toml_names(world, monkeypatch):
    """Not dvara's defaults: the door `up` starts may live elsewhere."""
    everything(world)
    asked = world / "asked.txt"
    script = world / "bin" / "dvara"
    script.write_text(f"#!/bin/sh\necho \"$@\" > {asked}\n/bin/cat <<'EOF'\n"
                      f"{json.dumps(DVARA)}\nEOF\n")
    from sarathi.cli import door_folders
    from sarathi.config import Door

    class Config:
        door = Door(root="/r/agents", actors="/r/actors.toml", state="/r/state")
    siblings.find_all(before={"dvara": door_folders(Config)})
    assert asked.read_text().split() == ["--root", "/r/agents", "--actors",
                                         "/r/actors.toml", "--state", "/r/state",
                                         "status", "--json"]


def test_a_dvara_without_a_status_command_is_reported_not_failed(world, capsys):
    everything(world)
    program(world / "bin", "dvara", "dvara: error: invalid choice: 'status'", 2)
    code, out = run(capsys, "status")
    assert code == 0
    assert "found, but: `status --json` failed" in out


def test_a_door_that_is_off_is_not_asked_about(world, capsys):
    """dvara's default folders are nobody's door; their problems are noise."""
    everything(world)
    program(world / "bin", "dvara", json.dumps({**DVARA, "problems": ["no actors file"]}))
    (world / "config").mkdir()
    (world / "config" / "sarathi.toml").write_text('[model]\nprovider = "ollama"\n')
    code, out = run(capsys, "status")
    assert code == 0
    assert "door off in sarathi.toml (`sarathi door` turns it on)" in out
    assert "no actors file" not in out


def test_yantra_says_its_release_and_the_model_it_would_ask(world, capsys):
    everything(world)
    program(world / "bin", "yantra", json.dumps(
        {**YANTRA, "problems": ["qwen3.8:latest is not pulled (ollama pull qwen3.8:latest)"]}))
    code, out = run(capsys, "status")
    assert ("yantra 0.1.0; would ask ollama for qwen3.8:latest; "
            "qwen3.8:latest is not pulled (ollama pull qwen3.8:latest)") in out


def test_yantra_is_asked_with_the_model_settings_up_would_give_it(world, capsys):
    """Asked with its own settings, Yantra would describe a model ``up``
    never starts it with."""
    everything(world)
    echo = world / "bin" / "yantra"
    echo.write_text('#!/bin/sh\nprintf \'{"format": "yantra.status.v1", "version": "0.1.0", '
                    '"provider": "%s", "model": "%s", "problems": []}\' '
                    '"$YANTRA_PROVIDER" "$OLLAMA_MODEL"\n')
    config = Path(os.environ["SARATHI_CONFIG"])
    config.mkdir(parents=True, exist_ok=True)
    (config / "sarathi.toml").write_text(
        '[model]\nprovider = "ollama"\nmodel = "gemma4:12b"\n')
    code, out = run(capsys, "status")
    assert "would ask ollama for gemma4:12b" in out
