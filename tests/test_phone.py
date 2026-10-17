"""The phone: one setting, a container that reaches it over Wi-Fi, and
the person it is for.

The bias these tests encode: THE PHONE IS GIVEN OUT ONLY WHERE IT WAS
TURNED ON, AND REACHED THE WAY ANOTHER COMPUTER WOULD. With no [phone],
no unit, no door and no page mentions it. With it, the containers get
the address (never a USB device), the key folder this computer paired
with, and the person's Sparsh rules, at the same paths. A wrong address
is said when it is set, not saved to fail at `up`. The screen's word
(`awake`) reaches Sparsh on both roads, and survives the address being
set again; a word Sparsh doesn't know is said, not passed on. An iPhone
is ONE PHONE, NOT A SECOND: its WebDriverAgent address replaces the
Android's (Sparsh would take the iPhone over it anyway), is saved only
once Sparsh says it answers, and reaches a container at the host's name,
never the container's own 127.0.0.1.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from sarathi import phone, podman, services
from sarathi.config import Config, ConfigError, Door, Pages, Phone, load, parse, render
from sarathi.home import pages
from sarathi.siblings import Found, SIBLINGS

from conftest import program

ADDRESS = "192.168.1.23:41234"
WIFI = Phone(address=ADDRESS)


def podman_config(**kw) -> Config:
    return Config("ollama", "gemma4:12b", road="podman", pages=Pages(on=False), **kw)


@pytest.fixture
def host(world, monkeypatch):
    monkeypatch.setenv("HOME", str(world / "home"))
    monkeypatch.delenv("SPARSH_STATE", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.delenv("SAMAY_STATE", raising=False)
    return world / "home"


# -- the setting ----------------------------------------------------------------


def test_the_phone_reads_back_as_written():
    for chosen in (Config("ollama", phone=WIFI), Config("ollama", phone=Phone()),
                   Config("ollama")):
        assert parse(render(chosen)) == chosen


def test_the_screens_word_reads_back_and_a_wrong_one_is_said():
    chosen = Config("ollama", phone=Phone(address=ADDRESS, awake="always"))
    assert parse(render(chosen)) == chosen
    assert '# awake = "working"' in render(Config("ollama", phone=WIFI))
    with pytest.raises(ConfigError, match="phone.awake is one of working, always, off"):
        parse('[model]\nprovider = "ollama"\n[phone]\non = true\nawake = "on"\n')


def test_the_screens_word_reaches_sparsh_on_both_roads(host):
    config = podman_config(phone=Phone(address=ADDRESS, awake="always"))
    assert services.phone_env(config) == {"SPARSH_CONNECT": ADDRESS, "SPARSH_AWAKE": "always"}
    assert "Environment=SPARSH_AWAKE=always\n" in podman.phone_env(config)
    assert "SPARSH_AWAKE" not in podman.phone_env(podman_config(phone=WIFI))


def test_an_address_that_is_not_one_stops_everything():
    with pytest.raises(ConfigError, match="phone.address must be an address and port"):
        parse('[model]\nprovider = "ollama"\n[phone]\non = true\naddress = "my phone"\n')


# -- the containers ---------------------------------------------------------------


def test_without_the_phone_no_unit_mentions_it(host):
    made = "".join(podman.units(podman_config(door=Door())).values())
    assert "sparsh" not in made and "SPARSH" not in made and ".android" not in made


def test_the_page_reaches_the_phone_over_wifi_with_this_computers_key(host):
    page = podman.units(podman_config(phone=WIFI))["sarathi-yantra.container"]
    assert "--sparsh auto:/usr/local/bin/sparsh" in page
    assert f"Environment=SPARSH_CONNECT={ADDRESS}" in page
    for folder in (host / ".android", host / ".sparsh"):
        assert f"Volume={folder}:{folder}:z" in page and folder.is_dir()
    assert "/dev/bus/usb" not in page and "AddDevice" not in page


def test_the_door_is_given_the_phone_for_its_one_person(host):
    door = podman.units(podman_config(phone=WIFI, door=Door()))["sarathi-dvara.container"]
    assert "--sparsh /usr/local/bin/sparsh serve" in door
    assert f"Environment=SPARSH_CONNECT={ADDRESS}" in door
    assert f"Volume={host / '.sparsh'}:{host / '.sparsh'}:z" in door


def test_the_image_takes_sparsh_beside_the_others():
    assert "sparsh" in podman.OPTIONAL_CHECKOUTS
    containerfile = (Path(podman.__file__).with_name("Containerfile")).read_text()
    assert "platform-tools-latest-linux.zip" in containerfile
    assert "ln -s /opt/sparsh/.venv/bin/sparsh /usr/local/bin/" in containerfile


def test_the_home_card_on_the_podman_road_needs_the_wifi_address(host, world):
    program(world / "bin", "sparsh")
    names = lambda c: [p.name for p in pages(c)]  # noqa: E731
    assert "sparsh" not in names(podman_config(phone=Phone()))
    assert "sparsh" in names(podman_config(phone=WIFI))


# -- the process road ----------------------------------------------------------------


def test_on_the_process_road_the_page_and_door_get_the_address(world, monkeypatch):
    (world / "agents").mkdir()
    (world / "actors.toml").write_text("[actor.owner]\nphone = true\n")
    monkeypatch.setenv("DVARA_TOKEN", "door-token")
    found = {s.name: Found(s, program=f"/bin/{s.program}") for s in SIBLINGS}
    config = Config("ollama", phone=WIFI, pages=Pages(on=False),
                    door=Door(root=str(world / "agents"), actors=str(world / "actors.toml"),
                              state=str(world / "state")))
    notes: list[str] = []
    door = services.door_service(config, found, {}, True, notes)
    assert door is not None, notes
    assert door.argv[door.argv.index("--sparsh") + 1] == "/bin/sparsh"
    assert door.env["SPARSH_CONNECT"] == ADDRESS
    assert services.phone_env(Config("ollama")) == {}


# -- `sarathi phone` -------------------------------------------------------------------


@pytest.fixture
def settings(world):
    (world / "config").mkdir(exist_ok=True)
    (world / "config" / "sarathi.toml").write_text(render(Config("ollama", road="podman")))


def sparsh_that(world, says: str, code: int = 0) -> Found:
    prog = program(world / "bin", "sparsh", says, code)
    return Found(next(s for s in SIBLINGS if s.name == "sparsh"), program=str(prog))


def args(*words, off=False, awake=None):
    return argparse.Namespace(words=list(words), off=off, awake=awake)


def test_an_address_that_answers_is_saved(world, settings, capsys):
    found = sparsh_that(world, f"connected to {ADDRESS}")
    assert phone.run(args(ADDRESS), found) == 0
    assert load().phone == WIFI
    assert f"over Wi-Fi at {ADDRESS}" in capsys.readouterr().out


def test_an_address_that_does_not_answer_is_not_saved(world, settings, capsys):
    found = sparsh_that(world, f"failed to connect to {ADDRESS}", code=1)
    assert phone.run(args(ADDRESS), found) == 1
    assert load().phone is None
    assert "not saved" in capsys.readouterr().out


def test_pair_runs_sparsh_and_says_what_comes_next(world, settings, capsys):
    found = sparsh_that(world, "Successfully paired to 192.168.1.23:37000")
    assert phone.run(args("pair", "192.168.1.23:37000", "123456"), found) == 0
    out = capsys.readouterr().out
    assert "Successfully paired" in out and "not the pairing one" in out
    assert load().phone is None                  # pairing alone turns nothing on


def test_a_cable_on_the_podman_road_is_warned_about(world, settings, capsys):
    assert phone.run(args(), sparsh_that(world, "")) == 0
    assert "can't reach a phone on a cable" in capsys.readouterr().out


def test_awake_is_saved_and_kept_when_the_address_is_set_again(world, settings, capsys):
    found = sparsh_that(world, f"connected to {ADDRESS}")
    assert phone.run(args(awake="always"), found) == 0
    assert "never asleep" in capsys.readouterr().out
    phone.run(args(ADDRESS), found)
    assert load().phone == Phone(address=ADDRESS, awake="always")


def test_off_turns_it_off(world, settings):
    phone.run(args(ADDRESS), sparsh_that(world, f"connected to {ADDRESS}"))
    assert phone.run(args(off=True), Found(SIBLINGS[0])) == 0
    assert load().phone is None


def test_nobody_marked_in_the_door_is_said(world, settings, capsys, monkeypatch):
    actors = world / "actors.toml"
    actors.write_text("[actor.owner]\n")
    (world / "config" / "sarathi.toml").write_text(
        render(Config("ollama", door=Door(actors=str(actors)))))
    phone.run(args(ADDRESS), sparsh_that(world, f"connected to {ADDRESS}"))
    assert "nobody in" in capsys.readouterr().out
    actors.write_text("[actor.owner]\nphone = true\n")
    phone.run(args(ADDRESS), sparsh_that(world, f"connected to {ADDRESS}"))
    assert "nobody in" not in capsys.readouterr().out


def test_an_agent_on_telegram_that_leaves_the_phone_out_is_said(world, settings, capsys):
    # A real schedule: its person unlocked the phone when asked, and the
    # run on minder had no phone tool, minder's allow list leaving it out.
    root = world / "agents"
    (root / "minder").mkdir(parents=True)
    package = root / "minder" / "agent.toml"
    package.write_text('[agent]\nname = "minder"\n[tools]\nallow = ["web_fetch"]\n')
    (world / "config" / "sarathi.toml").write_text(
        render(Config("ollama", door=Door(telegram="minder", root=str(root)))))
    phone.run(args(ADDRESS), sparsh_that(world, f"connected to {ADDRESS}"))
    assert 'leaves out "mcp__sparsh__*"' in capsys.readouterr().out
    for tools in ('allow = ["web_fetch", "mcp__sparsh__*"]', "", 'deny = ["bash"]'):
        package.write_text(f'[agent]\nname = "minder"\n[tools]\n{tools}\n')
        phone.run(args(ADDRESS), sparsh_that(world, f"connected to {ADDRESS}"))
        assert "leaves out" not in capsys.readouterr().out, tools
    package.write_text('[agent]\nname = "minder"\n[tools]\ndeny = ["mcp__sparsh__*"]\n')
    phone.run(args(ADDRESS), sparsh_that(world, f"connected to {ADDRESS}"))
    assert "leaves out" in capsys.readouterr().out


# -- `sarathi phone tcpip`: the cable turns Wi-Fi on ------------------------------------
# A real Nexus 6P (Android 8, no Wireless debugging page) was switched off and
# on: it stopped listening and its address moved from .161 to .160, so the
# containers said "no phone yet". One step finds the new address and saves it.

MOVED = "192.168.1.160:5555"


def test_tcpip_saves_the_address_the_phone_on_the_cable_now_has(world, settings, capsys):
    told = json.dumps({"serial": "84B7N", "address": MOVED, "connected": True,
                       "said": f"connected to {MOVED}"})
    sparsh = program(world / "bin", "sparsh")
    sparsh.write_text(f"#!/bin/sh\ncase \"$1\" in\n  tcpip) echo '{told}';;\n"
                      "  connect) echo \"connected to $2\";;\nesac\n")
    found = Found(next(s for s in SIBLINGS if s.name == "sparsh"), program=str(sparsh))
    assert phone.run(args("tcpip"), found) == 0
    assert load().phone == Phone(address=MOVED)
    assert f"over Wi-Fi at {MOVED}" in capsys.readouterr().out


def test_tcpip_with_no_phone_on_the_cable_saves_nothing_and_says_why(world, settings, capsys):
    found = sparsh_that(world, "sparsh: no phone is on a USB cable here. Plug it in", code=1)
    assert phone.run(args("tcpip"), found) == 1
    assert load().phone is None
    assert "error: no phone is on a USB cable here" in capsys.readouterr().out


def test_tcpip_that_could_not_connect_saves_nothing(world, settings, capsys):
    found = sparsh_that(world, json.dumps({"serial": "84B7N", "address": MOVED,
                                           "connected": False, "said": "Connection refused"}),
                        code=1)
    assert phone.run(args("tcpip"), found) == 1
    assert load().phone is None
    assert f"told to listen at {MOVED}" in capsys.readouterr().out


def test_the_same_address_again_needs_no_restart(world, settings, capsys):
    found = sparsh_that(world, f"connected to {ADDRESS}")
    phone.run(args(ADDRESS), found)
    assert "sarathi up" in capsys.readouterr().out
    phone.run(args(ADDRESS), found)
    out = capsys.readouterr().out
    assert "nothing to restart" in out and "sarathi up" not in out


# -- an iPhone: WebDriverAgent's address, one phone at a time --------------------------
# A real iPhone 17 (iOS 26) was driven by Sparsh from Linux through WebDriverAgent,
# forwarded to http://127.0.0.1:8100 by go-ios. Sarathi gives it out like the
# Android: saved once it answers, handed to both roads, in place of the Android.

WDA = "http://127.0.0.1:8100"
IPHONE = Phone(wda=WDA)


def iphone_sparsh(world, state: str = "device") -> Found:
    """A Sparsh whose status lists the iPhone at $SPARSH_WDA as ``state``."""
    sparsh = program(world / "bin", "sparsh")
    sparsh.write_text(
        "#!/bin/sh\n"
        'printf \'{"format": "sparsh.status.v1", "phones": [{"serial": "%s", '
        f'"state": "{state}", "model": "iPhone"}}], '
        '"wda": {"note": "signed for 6 more days"}}\\n\' "$SPARSH_WDA"\n')
    return Found(next(s for s in SIBLINGS if s.name == "sparsh"), program=str(sparsh))


def test_an_iphone_reads_back_as_written_and_is_one_phone_not_two():
    for chosen in (Config("ollama", phone=IPHONE),
                   Config("ollama", phone=Phone(wda=WDA, awake="always"))):
        assert parse(render(chosen)) == chosen
    assert '# wda = "http://127.0.0.1:8100"' in render(Config("ollama", phone=WIFI))
    with pytest.raises(ConfigError, match="two phones; Sarathi gives its agents one"):
        parse(f'[model]\nprovider = "ollama"\n[phone]\non = true\naddress = "{ADDRESS}"\n'
              f'wda = "{WDA}"\n')
    with pytest.raises(ConfigError, match="phone.wda must be WebDriverAgent's address"):
        parse('[model]\nprovider = "ollama"\n[phone]\non = true\nwda = "my iphone"\n')


def test_the_iphone_reaches_sparsh_here_as_itself_and_in_a_container_at_the_host(host):
    assert services.phone_env(Config("ollama", phone=IPHONE)) == {"SPARSH_WDA": WDA}
    units = podman.units(podman_config(phone=IPHONE, door=Door()))
    for unit in ("sarathi-yantra.container", "sarathi-dvara.container"):
        assert ("Environment=SPARSH_WDA=http://host.containers.internal:8100\n"
                in units[unit]), unit
        assert "127.0.0.1:8100" not in units[unit]
        assert "SPARSH_CONNECT" not in units[unit]


def test_the_home_card_shows_for_an_iphone_on_the_podman_road(host, world):
    program(world / "bin", "sparsh")
    assert "sparsh" in [p.name for p in pages(podman_config(phone=IPHONE))]


def test_an_iphone_that_answers_is_saved_in_place_of_the_android(world, settings, capsys):
    phone.run(args(ADDRESS), sparsh_that(world, f"connected to {ADDRESS}"))
    capsys.readouterr()
    assert phone.run(args("iphone"), iphone_sparsh(world)) == 0
    assert load().phone == IPHONE
    out = capsys.readouterr().out
    assert f"the iPhone answers at {WDA} (signed for 6 more days)" in out
    assert f"in place of the Android at {ADDRESS}" in out
    assert "host.containers.internal:8100" in out          # the podman road


def test_an_iphone_that_does_not_answer_is_not_saved_and_says_how_to_start_it(
        world, settings, capsys):
    assert phone.run(args("iphone", "http://127.0.0.1:8101"),
                     iphone_sparsh(world, "offline")) == 1
    assert load().phone is None
    out = capsys.readouterr().out
    assert "nothing answers at http://127.0.0.1:8101" in out
    assert "start-wda-from-linux.sh" in out and "not saved" in out


def test_an_android_address_afterwards_takes_the_iphones_place(world, settings):
    phone.run(args("iphone"), iphone_sparsh(world))
    phone.run(args(ADDRESS), sparsh_that(world, f"connected to {ADDRESS}"))
    assert load().phone == WIFI


def test_status_asks_sparsh_about_the_iphone_sarathi_gives_out(world, settings):
    from sarathi.cli import _said

    (world / "config" / "sarathi.toml").write_text(render(Config("ollama", phone=IPHONE)))
    iphone_sparsh(world)
    assert "http://127.0.0.1:8100 (iPhone) ready" in _said()["sparsh"]
