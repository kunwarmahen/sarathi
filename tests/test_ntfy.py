"""ntfy, for Dvara's notices on phones (`[dvara] ntfy`).

The bias is A PUSH SERVER NOBODY'S PHONE CAN REACH, OR ONE THAT REACHES
TOO FAR. A server on 127.0.0.1 tells a phone nothing, so ntfy listens on
the house address when there is one -- and on that address alone, never
every address. Dvara must be pointed at it (its flag before `serve`,
where Dvara reads it), and a person's page must name their own topic and
nobody else's. The other bias is a setting that silently does nothing:
`ntfy = true` with no ntfy installed says so, and the podman road brings
its own.
"""

from __future__ import annotations

from dataclasses import replace

from sarathi import config as settings_mod
from sarathi import podman, services
from sarathi.config import Config, ConfigError, Door, Pages, parse, render

from conftest import program  # noqa: F401

HOUSE = Door(window_host="192.168.1.44", ntfy_port=8793)


def test_the_setting_reads_writes_and_refuses_what_it_cannot_use():
    text = ('[model]\nprovider = "ollama"\n[dvara]\non = true\nntfy = true\n')
    door = parse(text).door
    assert door.ntfy_port == 8793
    assert parse(render(parse(text))).door.ntfy_port == 8793
    assert parse('[model]\nprovider = "ollama"\n[dvara]\non = true\n').door.ntfy_port is None
    try:
        parse('[model]\nprovider = "ollama"\n[dvara]\non = true\nntfy = "yes"\n')
    except ConfigError as exc:
        assert "dvara.ntfy must be true or false" in str(exc)
    else:
        raise AssertionError("a word for ntfy was taken")


def test_it_listens_on_the_house_address_or_this_computer_alone():
    assert Config("ollama", door=HOUSE).ntfy_url() == "http://192.168.1.44:8793"
    alone = Config("ollama", door=replace(HOUSE, window_host="0.0.0.0"))
    assert alone.ntfy_url() == "http://127.0.0.1:8793"
    assert Config("ollama", door=Door()).ntfy_url() is None


def plan(world, config):
    from sarathi.siblings import SIBLINGS, Found

    bin_dir = world / "bin"
    found = {s.name: Found(s, str(program(bin_dir, s.name)) if s.name in
                           ("yantra", "setu", "samay", "dvara") else None)
             for s in SIBLINGS}
    door = replace(config.door, actors=str(program(world, "actors.toml")),
                   root=str(world), state=str(world / "state"))
    settings_mod.save_secret("DVARA_TOKEN", "t")
    return services.plan(replace(config, door=door), found)


def test_dvara_is_pointed_at_it_before_serve_and_told_where_a_tap_opens(world,
                                                                        monkeypatch):
    monkeypatch.setenv("SARATHI_NTFY", str(program(world / "bin", "ntfy")))
    planned, _ = plan(world, Config("ollama", door=HOUSE, pages=Pages(on=True)))
    by = {s.name: s for s in planned}
    names = [s.name for s in planned]
    assert names.index("ntfy") < names.index("dvara")
    assert by["ntfy"].argv[1:4] == ["serve", "--listen-http", "192.168.1.44:8793"]
    assert by["ntfy"].host == "192.168.1.44"
    dvara = by["dvara"].argv
    assert dvara[dvara.index("--ntfy") + 1] == "http://192.168.1.44:8793"
    assert dvara.index("--ntfy") < dvara.index("serve")
    assert by["dvara"].env["DVARA_NTFY_CLICK"] == "http://192.168.1.44:8760/"


def test_with_no_ntfy_installed_it_says_so_and_dvara_is_not_pointed_at_nothing(world):
    planned, notes = plan(world, Config("ollama", door=HOUSE))
    assert "ntfy" not in [s.name for s in planned]
    assert any("ntfy isn't installed here" in n for n in notes)
    dvara = next(s for s in planned if s.name == "dvara")
    assert "--ntfy" not in dvara.argv and "DVARA_NTFY_CLICK" not in dvara.env


def test_the_podman_road_brings_its_own_on_the_house_address(world, monkeypatch):
    monkeypatch.setenv("HOME", str(world / "home"))
    settings_mod.save_secret("DVARA_TOKEN", "t")
    config = Config("ollama", road="podman", door=HOUSE, pages=Pages(on=True))
    made = podman.units(config)
    push = made["sarathi-ntfy.container"]
    assert f"Image={podman.NTFY_IMAGE}" in push
    assert "PublishPort=127.0.0.1:8793:80" in push
    assert "PublishPort=192.168.1.44:8793:80" in push
    door = made["sarathi-dvara.container"]
    assert "--ntfy http://sarathi-ntfy:80 serve" in door
    assert "After=sarathi-ntfy.service" in door
    assert "Environment=DVARA_NTFY_CLICK=http://192.168.1.44:8760/" in door
    assert 8793 in podman.house_ports(config)[1]
    assert "sarathi-ntfy.container" not in podman.units(replace(config, door=Door()))
