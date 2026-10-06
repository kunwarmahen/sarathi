"""The door: dvara started beside the page and the clock, and wired to both.

The bias these tests encode: THE WIRING A PERSON WOULD COPY BY HAND IS
DONE ONCE, THE SAME IN EVERY PLACE, AND THE DOOR'S SECRETS GO TO THE
DOOR. The clock and the door get the same address and token for each
other; the bot's token reaches dvara and nothing else; a door that
cannot start says why and costs nobody the page or the clock; and
`sarathi door` writes dvara's files only where there were none.
"""

from __future__ import annotations

import argparse
import stat

import pytest

from sarathi import config, door, services
from sarathi.config import Door, load, read_secrets
from sarathi.siblings import Found, Sibling

from conftest import fake, free_port, program, settings
from test_up import run, seen


def door_args(**given) -> argparse.Namespace:
    return argparse.Namespace(**{**dict(telegram=None, telegram_id=None, port=None,
                                        window_host=None, window_port=None, window_url=None,
                                        off=False), **given})


@pytest.fixture
def home(world, monkeypatch):
    monkeypatch.setenv("HOME", str(world / "home"))
    (world / "home").mkdir()
    return world / "home"


@pytest.fixture
def dvara_checkout(world):
    """A dvara checkout with its examples, and its program inside .venv/bin."""
    checkout = world / "checkouts" / "dvara"
    for agent in ("greeter", "scribe"):
        (checkout / "examples" / "agents" / agent).mkdir(parents=True)
        (checkout / "examples" / "agents" / agent / "agent.toml").write_text(
            f'[agent]\nname = "{agent}"\n')
    prog = program(checkout / ".venv" / "bin", "dvara")
    return Found(Sibling("dvara", "dvara", "the door", optional=True), program=str(prog))


class TestTurningItOn:
    def test_it_makes_its_token_asks_for_the_bots_and_writes_starter_files(
            self, world, home, dvara_checkout, capsys):
        settings(world, {"web": 8321, "clock": 8780})
        asked = []
        code = door.run(door_args(telegram="greeter", telegram_id="8675309"), dvara_checkout,
                        ask_secret=lambda q: asked.append(q) or "123:bot-token",
                        interactive=True)
        assert code == 0
        cfg = load()
        assert cfg.door == Door(telegram="greeter")
        held = read_secrets()
        assert len(held["DVARA_TOKEN"]) == 48 and held["TELEGRAM_TOKEN"] == "123:bot-token"
        assert stat.S_IMODE(config.secrets_path().stat().st_mode) == 0o600
        assert "BotFather" in asked[0]
        actors = (home / "dvara" / "actors.toml").read_text()
        assert "[actor.owner]" in actors and "id   = 8675309" in actors
        assert sorted(p.name for p in (home / "dvara" / "agents").iterdir()) == [
            "greeter", "scribe"]
        assert "123:bot-token" not in config.settings_path().read_text()

    def test_files_already_there_are_left_alone(self, world, home, dvara_checkout, capsys):
        settings(world, {"web": 8321, "clock": 8780})
        (home / "dvara").mkdir()
        (home / "dvara" / "actors.toml").write_text("# mine\n")
        door.run(door_args(telegram="", telegram_id="1"), dvara_checkout, interactive=False)
        assert (home / "dvara" / "actors.toml").read_text() == "# mine\n"
        assert "left alone" in capsys.readouterr().out
        assert load().door.telegram is None

    def test_a_bot_with_no_token_says_the_door_will_not_start(self, world, home,
                                                              dvara_checkout, capsys):
        settings(world, {"web": 8321, "clock": 8780})
        door.run(door_args(telegram="greeter"), dvara_checkout, interactive=False)
        assert "until then the door will not start" in capsys.readouterr().out

    def test_off_turns_it_off(self, world, home, dvara_checkout):
        settings(world, {"web": 8321, "clock": 8780})
        door.run(door_args(telegram=""), dvara_checkout, interactive=False)
        door.run(door_args(off=True), dvara_checkout, interactive=False)
        assert load().door is None


def door_on(stage, home, telegram: bool = True) -> int:
    """The door on, with its files and tokens in place; returns its port."""
    port = free_port()
    (home / "dvara" / "agents" / "greeter").mkdir(parents=True)
    (home / "dvara" / "actors.toml").write_text("[actor.owner]\n")
    config.save_secret("DVARA_TOKEN", "d" * 48)
    if telegram:
        config.save_secret("TELEGRAM_TOKEN", "123:bot")
    extra = (f'[door]\non = true\nport = {port}\n'
             + ('telegram = "greeter"\n' if telegram else ""))
    settings(stage["world"], stage["ports"], extra)
    fake(stage["world"] / "bin", "dvara")
    return port


class TestStartedTogether:
    def test_clock_door_page_in_that_order_and_wired_to_each_other(self, stage, home,
                                                                   capsys):
        port = door_on(stage, home)
        code, out = run(capsys, "up")
        assert code == 0, out
        assert f"door   up at http://127.0.0.1:{port}/" in out
        clock, gate, page = seen(stage, "samay"), seen(stage, "dvara"), seen(stage, "yantra")
        assert clock["at"] < gate["at"] < page["at"]
        bin_dir = stage["world"] / "bin"
        assert gate["argv"] == [
            "--root", str(home / "dvara" / "agents"), "--actors",
            str(home / "dvara" / "actors.toml"), "--state", str(home / "dvara" / "state"),
            "--ask", "--provider", "ollama", "--model", "gemma4:12b",
            "--samay", str(bin_dir / "samay"),
            "serve", "--host", "127.0.0.1", "--port", str(port), "--telegram", "greeter"]
        for env in (clock["env"], gate["env"]):
            assert env["SAMAY_DVARA_URL"] == f"http://127.0.0.1:{port}"
            assert env["SAMAY_DVARA_TOKEN"] == "d" * 48
        assert gate["env"]["DVARA_TOKEN"] == "d" * 48
        assert gate["env"]["TELEGRAM_TOKEN"] == "123:bot"
        assert gate["env"]["OLLAMA_MODEL"] == "gemma4:12b"

    def test_the_bots_token_reaches_the_door_and_nothing_else(self, stage, home, capsys):
        door_on(stage, home)
        run(capsys, "up")
        for other in ("samay", "yantra"):
            assert "TELEGRAM_TOKEN" not in seen(stage, other)["env"]
            assert "DVARA_TOKEN" not in seen(stage, other)["env"]

    def test_a_door_that_cannot_start_costs_nobody_the_page(self, stage, home, capsys):
        door_on(stage, home)
        (home / "dvara" / "actors.toml").unlink()
        code, out = run(capsys, "up")
        assert "door   not started: no actors file" in out
        assert "page   up at" in out and "clock  up at" in out
        assert not (stage["seen"] / "dvara.json").exists()

    def test_without_the_clock_the_door_has_no_schedules(self, stage, home, capsys):
        door_on(stage, home, telegram=False)
        text = config.settings_path().read_text().replace("[clock]\n", "[clock]\non = false\n")
        config.settings_path().write_text(text)
        run(capsys, "up")
        gate = seen(stage, "dvara")
        assert gate["argv"][gate["argv"].index("--samay") + 1] == "off"
        assert "--telegram" not in gate["argv"]

    def test_status_names_whoever_messaged_and_is_not_in_the_actors_file(self, stage, home,
                                                                          capsys):
        door_on(stage, home)
        run(capsys, "up")
        with open(services.log_path("door"), "a") as log:
            log.write('telegram: 5551212 messaged and is not in the actors file (add '
                      '[[actor.NAME.channel]] kind="telegram" id=5551212)\n')
        _, out = run(capsys, "status")
        assert "door   running at" in out
        assert "not in the actors file (telegram id): 5551212" in out


def test_strangers_are_read_once_each_in_order():
    lines = ["telegram: 1 messaged and is not in the actors file (add ...)",
             "something else", "telegram: 2 messaged and is not in the actors file",
             "telegram: 1 messaged and is not in the actors file"]
    assert door.strangers(lines) == ["1", "2"]


def test_a_door_section_reads_back_as_written():
    chosen = config.Config("ollama", door=Door(port=9000, telegram="greeter",
                                               actors="~/elsewhere/actors.toml"))
    assert config.parse(config.render(chosen)) == chosen
    with pytest.raises(config.ConfigError, match="door.on must be true or false"):
        config.parse('[model]\nprovider = "ollama"\n[door]\non = "yes"\n')


def test_the_window_settings_reach_the_door_in_setus_own_names(stage, home, capsys):
    door_on(stage, home)
    text = config.settings_path().read_text().replace(
        "telegram = \"greeter\"\n",
        'telegram = "greeter"\nwindow_host = "100.101.102.103"\nwindow_port = 8767\n')
    config.settings_path().write_text(text)
    run(capsys, "up")
    gate = seen(stage, "dvara")["env"]
    assert gate["SETU_WINDOW_HOST"] == "100.101.102.103"
    assert gate["SETU_WINDOW_PORT"] == "8767" and "SETU_WINDOW_URL" not in gate
    assert "SETU_WINDOW_HOST" not in seen(stage, "yantra")["env"]


def test_the_door_command_keeps_the_window_address(world, home, dvara_checkout):
    settings(world, {"web": 8321, "clock": 8780})
    door.run(door_args(telegram="", window_host="100.101.102.103",
                       window_url="https://door.example.net"), dvara_checkout,
             interactive=False)
    assert load().door.window_env() == {"SETU_WINDOW_HOST": "100.101.102.103",
                                        "SETU_WINDOW_URL": "https://door.example.net"}
