"""Several phones, each by a name: what exists, written down once.

The bias these tests encode: NOTHING WRITTEN DOWN IS DROPPED QUIETLY.
Naming the phone [phone] already holds takes its place; adding another
beside an unnamed one is refused with the command that names it; a
named phone carries exactly one way to reach it. The names reach
Sparsh on both roads as SPARSH_PHONES -- an iPhone at the host's name
from inside a container -- with one screen word per phone. Whose each
phone is stays Dvara's to say (People), not this file's.
"""

from __future__ import annotations

import argparse
import json

import pytest

from sarathi import phone, podman, services
from sarathi.config import (
    Config,
    ConfigError,
    NamedPhone,
    Pages,
    Phone,
    load,
    parse,
    render,
    with_phone,
    without_phone,
)
from sarathi.siblings import SIBLINGS, Found

from conftest import program

NEXUS = NamedPhone(name="nexus", serial="84B7N16128001616", awake="always")
IPHONE = NamedPhone(name="iphone", wda="http://127.0.0.1:8100")
TWO = Phone(named=(NEXUS, IPHONE))


def test_named_phones_read_back_as_written():
    chosen = Config("ollama", phone=TWO)
    text = render(chosen)
    assert "[phone.nexus]\nserial = \"84B7N16128001616\"\nawake = \"always\"" in text
    assert parse(text) == chosen


def test_a_named_phone_is_reached_one_way():
    base = '[model]\nprovider = "ollama"\n[phone]\non = true\n'
    for body, said in [('[phone.nexus]\nawake = "always"\n', "exactly one of"),
                       ('[phone.nexus]\nserial = "x"\nwda = "http://a:1"\n', "exactly one of"),
                       ('[phone.Nexus]\nserial = "x"\n', "lower case"),
                       ('[phone.nexus]\nserial = "x"\ncolour = "red"\n', "unknown key"),
                       ('[phone.nexus]\naddress = "my phone"\n', "can't be")]:
        with pytest.raises(ConfigError, match=said):
            parse(base + body)
    with pytest.raises(ConfigError, match="each phone says its own"):
        parse(base.replace("on = true\n", 'on = true\naddress = "1.2.3.4:5"\n')
              + '[phone.nexus]\nserial = "x"\n')


def test_naming_the_unnamed_phone_takes_its_place_and_another_is_refused():
    old = Phone(wda="http://127.0.0.1:8100")
    assert with_phone(old, IPHONE) == Phone(named=(IPHONE,))
    with pytest.raises(ConfigError, match="name it first -- sarathi phone add NAME "
                                          "iphone http://127.0.0.1:8100"):
        with_phone(old, NEXUS)
    again = with_phone(TWO, NamedPhone(name="nexus", address="192.168.1.160:5555"))
    assert [p.where for p in again.named] == ["http://127.0.0.1:8100", "192.168.1.160:5555"]


def test_one_phone_under_two_names_is_refused():
    with pytest.raises(ConfigError, match="84B7N16128001616 is already named nexus"):
        with_phone(TWO, NamedPhone(name="pixel", serial="84B7N16128001616"))


def test_removing_the_last_turns_the_phone_off():
    assert without_phone(TWO, "iphone") == Phone(named=(NEXUS,))
    assert without_phone(Phone(named=(NEXUS,)), "nexus") is None
    with pytest.raises(ConfigError, match=r"no phone is called 'pixel' \(nexus, iphone\)"):
        without_phone(TWO, "pixel")


def test_the_names_reach_sparsh_on_both_roads(world, monkeypatch):
    monkeypatch.setenv("HOME", str(world / "home"))
    config = Config("ollama", road="podman", pages=Pages(on=False), phone=TWO)
    assert services.phone_env(config) == {
        "SPARSH_PHONES": "nexus=84B7N16128001616,iphone=http://127.0.0.1:8100",
        "SPARSH_AWAKE": "nexus=always"}
    inside = podman.phone_env(config)
    assert ("Environment=SPARSH_PHONES=nexus=84B7N16128001616,"
            "iphone=http://host.containers.internal:8100\n") in inside
    assert "ADB_SERVER_SOCKET=" in inside and "SPARSH_WDA" not in inside


# -- `sarathi phone add|remove|list` ---------------------------------------------------

STATUS = {"phones": [{"serial": "84B7N16128001616", "state": "device", "model": "Nexus_6P"},
                     {"serial": "emulator-5554", "state": "device", "model": "sdk"}]}


@pytest.fixture
def settings(world):
    (world / "config").mkdir(exist_ok=True)
    (world / "config" / "sarathi.toml").write_text(render(Config("ollama")))


def sparsh_saying(world, said: str) -> Found:
    prog = program(world / "bin", "sparsh", said, 0)
    return Found(next(s for s in SIBLINGS if s.name == "sparsh"), program=str(prog))


def args(*words, awake=None):
    return argparse.Namespace(words=list(words), off=False, awake=awake)


def test_add_names_the_phone_on_the_cable_by_its_serial(world, settings, capsys):
    found = sparsh_saying(world, json.dumps(STATUS))
    assert phone.run(args("add", "nexus", awake="always"), found) == 0
    assert load().phone == Phone(named=(NEXUS,))
    out = capsys.readouterr().out
    assert "nexus is in" in out and 'phones = ["nexus"]' in out


def test_add_an_address_then_list_then_remove(world, settings, capsys):
    connected = sparsh_saying(world, "connected to 192.168.1.160:5555")
    assert phone.run(args("add", "pixel", "192.168.1.160:5555"), connected) == 0
    assert load().phone.named[0].address == "192.168.1.160:5555"
    capsys.readouterr()
    listing = sparsh_saying(world, json.dumps(
        {"phones": [{"serial": "192.168.1.160:5555", "state": "device"}]}))
    assert phone.run(args("list"), listing) == 0
    assert "pixel: Android at 192.168.1.160:5555 -- answers" in capsys.readouterr().out
    assert phone.run(args("remove", "pixel"), listing) == 0
    assert load().phone is None


def test_a_serial_adb_sees_is_named_directly(world, settings, capsys):
    found = sparsh_saying(world, json.dumps(STATUS))
    assert phone.run(args("add", "pixel", "emulator-5554"), found) == 0
    assert load().phone.named[0].serial == "emulator-5554"
    assert phone.run(args("add", "spare", "R58M123"), found) == 1
    assert "no phone called R58M123 is attached" in capsys.readouterr().out


def test_naming_the_saved_iphone_needs_no_iphone_plugged_in(world, capsys):
    (world / "config").mkdir(exist_ok=True)
    (world / "config" / "sarathi.toml").write_text(
        render(Config("ollama", phone=Phone(wda="http://127.0.0.1:8100"))))
    nobody = sparsh_saying(world, json.dumps(STATUS))     # no iPhone answers
    assert phone.run(args("add", "iphone", "iphone", "http://127.0.0.1:8100"), nobody) == 0
    assert phone.run(args("add", "nexus"), nobody) == 0
    assert [p.name for p in load().phone.named] == ["iphone", "nexus"]
    assert "not asked" in capsys.readouterr().out


def test_a_bad_name_saves_nothing(world, settings, capsys):
    found = sparsh_saying(world, json.dumps(STATUS))
    assert phone.run(args("add", "My Phone"), found) == 2
    assert load().phone is None
