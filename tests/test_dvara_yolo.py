"""[dvara] yolo: "Never asked" in the actors file means it (config.py).

Dvara takes the stricter of the house, the person and the agent. Started
with --ask alone, the house is "ask", and a person or an agent set to
"yolo" is still asked before every change -- the setting looked like it
did something and did nothing. The bias here is the opposite mistake as
much as that one: the house's switch must reach both roads' start lines,
and turning it on must never quietly lift somebody who set nothing, who
Dvara would otherwise read as "no ceiling of their own".
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from sarathi import config as settings_mod
from sarathi import podman
from sarathi.config import ConfigError, parse, render

from test_home import send  # noqa: F401
from test_podman import DOOR, host, with_door_secrets  # noqa: F401
from test_settings_page import heard, owner_page  # noqa: F401
from test_home import keys  # noqa: F401

BASE = '[model]\nprovider = "ollama"\n[dvara]\non = true\n'


def test_off_unless_the_file_says_so():
    assert parse(BASE).door.yolo is False


def test_on_when_the_file_says_so_and_kept_when_written_back():
    config = parse(BASE + "yolo = true\n")
    assert config.door.yolo is True
    assert parse(render(config)).door.yolo is True


def test_a_word_is_not_a_yes():
    with pytest.raises(ConfigError, match="dvara.yolo must be true or false"):
        parse(BASE + 'yolo = "yes"\n')


def test_the_podman_road_starts_dvara_with_yolo_only_when_on(host, world):  # noqa: F811
    with_door_secrets(world)
    on = podman.units(replace(DOOR, door=replace(DOOR.door, yolo=True)))
    assert "--ask --yolo --owner owner" in on["sarathi-dvara.container"]
    off = podman.units(DOOR)
    assert "--yolo" not in off["sarathi-dvara.container"]


def test_a_person_saved_with_no_setting_is_written_as_asked(owner_page):  # noqa: F811
    path = settings_mod.settings_path()
    path.write_text(path.read_text().replace("yolo = false", "yolo = true"))
    send(owner_page, "/api/settings/person/priya", {"agents": ["greeter"]})
    assert json.loads(heard(owner_page)[-1]["stdin"])["permissions"] == "ask"
    send(owner_page, "/api/settings/person/mahen", {"permissions": "yolo"})
    assert json.loads(heard(owner_page)[-1]["stdin"])["permissions"] == "yolo"


def test_with_the_switch_off_a_person_is_sent_as_the_form_said(owner_page):  # noqa: F811
    send(owner_page, "/api/settings/person/priya", {"agents": ["greeter"]})
    assert "permissions" not in json.loads(heard(owner_page)[-1]["stdin"])
