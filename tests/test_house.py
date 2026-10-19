"""``[house]``: every server on the home network, and every link by one name.

The bias is A LINK TO SOMEWHERE THE PHONE CANNOT GO. A page published on
the house address but linked as 127.0.0.1 opens the phone itself; a page
linked by name but published on 127.0.0.1 alone opens nothing. So each
piece is checked on both sides: published on the house address, and
named by the house's name in what it hands out. And A SHELL FOR THE
WHOLE WI-FI: Yantra's page always gets its token, never in a unit file.
"""

from __future__ import annotations

import subprocess

import pytest

from sarathi import config as settings
from sarathi import podman, services
from sarathi.config import Config, ConfigError, Door, House, Pages, parse, render
from test_podman import host  # noqa: F401  (the fixture)

HOUSE = House("beast.local", "192.168.1.44")


def housed(**kw) -> Config:
    return Config("ollama", road="podman", house=HOUSE,
                  door=Door(ntfy_port=8793), pages=Pages(on=True), **kw)


def test_the_house_is_read_written_and_checked():
    text = '[model]\nprovider = "ollama"\n[house]\nname = "beast.local"\n'
    got = parse(text)
    assert got.house == House("beast.local") and parse(render(got)).house == got.house
    assert parse(render(Config("ollama"))).house is None       # shown commented out
    with pytest.raises(ConfigError, match="house.name"):
        parse('[model]\nprovider = "ollama"\n[house]\nname = "a b"\n')
    with pytest.raises(ConfigError, match="house.address"):
        parse('[model]\nprovider = "ollama"\n[house]\nname = "x.local"\n'
              'address = "0.0.0.0"\n')


def test_with_no_address_the_house_is_published_on_what_its_name_finds(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("192.168.1.44", 0))])
    assert House("beast.local").published_on() == "192.168.1.44"
    assert HOUSE.published_on() == "192.168.1.44"


def test_every_piece_is_published_on_the_house_address_too(host):  # noqa: F811
    made = podman.units(housed())
    for unit, publish in (("sarathi-yantra", "192.168.1.44:8321:8321"),
                          ("sarathi-samay", "192.168.1.44:8780:8780"),
                          ("sarathi-dvara", "192.168.1.44:8770:8765"),
                          ("sarathi-dvara-page", "192.168.1.44:8785:8785"),
                          ("sarathi-setu", "192.168.1.44:8775:8775"),
                          ("sarathi-ntfy", "192.168.1.44:8793:80")):
        text = made[f"{unit}.container"]
        assert f"PublishPort={publish}" in text, unit
        assert "PublishPort=127.0.0.1:" in text, unit          # and here, as before


def test_every_link_says_the_name(host):  # noqa: F811
    config = housed()
    made = podman.units(config)
    assert "SAMAY_PUBLIC_URL=http://beast.local:8780/" in made["sarathi-samay.container"]
    assert "--public-url http://beast.local:8775/" in made["sarathi-setu.container"]
    door = made["sarathi-dvara.container"]
    # the sign-in window (Gmail's page in it too) and a person's Setu link
    assert "SETU_WINDOW_URL=http://beast.local:8790" in door
    assert "SETU_PAGE_URL=http://beast.local:8775/" in door
    assert config.ntfy_url() == "http://beast.local:8793"


def test_yantras_page_gets_its_token_through_its_own_env_file_only(host):  # noqa: F811
    config = housed()
    text = podman.units(config)["sarathi-yantra.container"]
    podman.write_env_files(config)
    token = settings.read_secrets()[settings.YANTRA_TOKEN]
    assert token not in text
    assert f"YANTRA_WEB_TOKEN={token}" in podman.env_file("sarathi-yantra").read_text()
    for other in ("sarathi-samay", "sarathi-dvara"):
        path = podman.env_file(other)
        assert not path.exists() or token not in path.read_text()


def test_the_firewall_line_names_every_house_port(host, world, monkeypatch):  # noqa: F811
    monkeypatch.setattr(podman.shutil, "which", lambda name: f"/usr/bin/{name}")
    (world / "ufw.conf").write_text("ENABLED=yes\n")
    host.answers[("ip", "-o", "addr")] = subprocess.CompletedProcess(
        [], 0, "2: eno1    inet 192.168.1.44/24 brd 192.168.1.255 scope global eno1\n", "")
    note = podman.firewall_note(housed())
    assert note[1] == ("  sudo ufw allow from 192.168.1.0/24 to any port "
                       "8321,8760,8770,8775,8780,8785,8790,8791,8793 proto tcp")


def test_on_the_plain_programs_road_the_pieces_listen_everywhere_and_say_the_name(
        world, monkeypatch):
    config = Config("ollama", house=HOUSE, door=None, pages=Pages(on=False))
    monkeypatch.setattr(services, "model_env", lambda c: {})
    from sarathi.siblings import Found
    found = {name: Found(name, f"/bin/{name}", None, None) for name in
             ("yantra", "setu", "samay", "dvara", "sparsh")}
    planned, _ = services.plan(config, found)
    by = {s.name: s for s in planned}
    assert by["yantra"].argv[by["yantra"].argv.index("--host") + 1] == "0.0.0.0"
    assert by["samay"].env["SAMAY_PUBLIC_URL"] == "http://beast.local:8780/"
    assert by["yantra"].env[settings.YANTRA_TOKEN] == \
        settings.read_secrets()[settings.YANTRA_TOKEN]
    assert settings.YANTRA_TOKEN not in by["samay"].env
