"""ntfy, for Dvara's notices on phones (`[dvara] ntfy`).

The bias is A PUSH SERVER NOBODY'S PHONE CAN REACH, OR ONE THAT REACHES
TOO FAR. A server on 127.0.0.1 tells a phone nothing, so ntfy listens on
the house address when there is one -- and on that address alone, never
every address. Dvara must be pointed at it (its flag before `serve`,
where Dvara reads it), and a person's page must name their own topic and
nobody else's. The other bias is a setting that silently does nothing:
`ntfy = true` with no ntfy installed says so, and the podman road brings
its own. And A WAKE-UP THAT LEAKS OR NEVER COMES: an iPhone is woken
through ntfy.sh only when that is asked for, and then with the address
the phone typed, or ntfy.sh's hash matches nothing.
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


def test_an_iphone_is_woken_through_ntfy_sh_only_when_asked_and_never_with_the_words(
        world, monkeypatch):
    """iOS wakes an app only through Apple's push, which only ntfy.sh can ask
    for: with `ntfy_upstream` ntfy is told that server, and the address the
    phone subscribed with as its base-url (the hash ntfy.sh is sent is of
    that address). Without it nothing leaves the house."""
    monkeypatch.setenv("SARATHI_NTFY", str(program(world / "bin", "ntfy")))
    planned, _ = plan(world, Config("ollama", door=HOUSE))
    serve = next(s for s in planned if s.name == "ntfy").argv
    assert "--upstream-base-url" not in serve and "--base-url" not in serve

    iphone = replace(HOUSE, ntfy_upstream="https://ntfy.sh")
    planned, _ = plan(world, Config("ollama", door=iphone))
    serve = next(s for s in planned if s.name == "ntfy").argv
    assert serve[serve.index("--upstream-base-url") + 1] == "https://ntfy.sh"
    assert serve[serve.index("--base-url") + 1] == "http://192.168.1.44:8793"

    monkeypatch.setenv("HOME", str(world / "home"))
    by_address = replace(iphone, ntfy_url="http://192.168.1.44:8793")
    config = Config("ollama", road="podman", door=by_address, pages=Pages(on=True),
                    house=settings_mod.House(name="beast.singhs", address="192.168.1.44"))
    push = podman.units(config)["sarathi-ntfy.container"]
    assert ("Exec=serve --cache-file /var/cache/ntfy/cache.db --cache-duration 24h "
            "--base-url http://192.168.1.44:8793 --upstream-base-url https://ntfy.sh") in push
    off = podman.units(replace(config, door=HOUSE))["sarathi-ntfy.container"]
    assert "upstream" not in off


def test_the_address_phones_subscribe_with_wins_over_the_house_name():
    house = settings_mod.House(name="beast.singhs", address="192.168.1.44")
    assert Config("ollama", door=HOUSE, house=house).ntfy_url() == "http://beast.singhs:8793"
    typed = replace(HOUSE, ntfy_url="http://192.168.1.44:8793")
    assert Config("ollama", door=typed, house=house).ntfy_url() == "http://192.168.1.44:8793"


def test_both_settings_are_read_written_and_a_wrong_one_is_refused():
    text = ('[model]\nprovider = "ollama"\n[dvara]\non = true\nntfy = true\n'
            'ntfy_url = "http://192.168.1.44:8793/"\nntfy_upstream = "https://ntfy.sh"\n')
    door = parse(text).door
    assert (door.ntfy_url, door.ntfy_upstream) == ("http://192.168.1.44:8793",
                                                    "https://ntfy.sh")
    assert parse(render(parse(text))).door == door
    plain = parse('[model]\nprovider = "ollama"\n[dvara]\non = true\nntfy = true\n').door
    assert plain.ntfy_upstream is None and plain.ntfy_url is None
    assert '# ntfy_upstream = "https://ntfy.sh"' in render(parse(
        '[model]\nprovider = "ollama"\n[dvara]\non = true\nntfy = true\n'))
    try:
        parse('[model]\nprovider = "ollama"\n[dvara]\non = true\nntfy_upstream = "ntfy.sh"\n')
    except ConfigError as exc:
        assert "dvara.ntfy_upstream must be an address" in str(exc)
    else:
        raise AssertionError("an address with no http was taken")
