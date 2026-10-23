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


def test_every_page_is_published_on_the_house_address_too(host):  # noqa: F811
    made = podman.units(housed())
    for unit, publish in (("sarathi-yantra", "192.168.1.44:8321:8321"),
                          ("sarathi-samay", "192.168.1.44:8780:8780"),
                          ("sarathi-dvara-page", "192.168.1.44:8785:8785"),
                          ("sarathi-setu", "192.168.1.44:8775:8775"),
                          ("sarathi-ntfy", "192.168.1.44:8793:80")):
        text = made[f"{unit}.container"]
        assert f"PublishPort={publish}" in text, unit
        assert "PublishPort=127.0.0.1:" in text, unit          # and here, as before
    # Dvara's own port answers Samay and its page, not a browser
    door = made["sarathi-dvara.container"]
    assert "192.168.1.44:8770" not in door and "PublishPort=127.0.0.1:8770:8765" in door


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


def test_a_sign_in_on_yantras_page_from_a_phone_has_its_own_window(host):  # noqa: F811
    """With the house's name Yantra's page opens on every device, and a
    site added there had no window a phone could open."""
    config = housed()
    page = podman.units(config)["sarathi-yantra.container"]
    assert "PublishPort=192.168.1.44:8792:8792" in page
    assert "SETU_WINDOW_HOST=0.0.0.0" in page and "SETU_WINDOW_PORT=8792" in page
    assert "SETU_WINDOW_URL=http://beast.local:8792" in page
    # no house: still one, for you at this computer (Podman's bridge
    # makes your own browser "another device" to the page)
    alone = podman.units(Config("ollama", road="podman", door=Door(), pages=Pages(on=True)))
    page = alone["sarathi-yantra.container"]
    assert "PublishPort=127.0.0.1:8792:8792" in page
    assert "SETU_WINDOW_URL=http://127.0.0.1:8792" in page


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
    monkeypatch.setattr(podman.shutil, "which", lambda name, **_: f"/usr/bin/{name}")
    (world / "ufw.conf").write_text("ENABLED=yes\n")
    host.answers[("ip", "-o", "addr")] = subprocess.CompletedProcess(
        [], 0, "2: eno1    inet 192.168.1.44/24 brd 192.168.1.255 scope global eno1\n", "")
    note = podman.firewall_note(housed())
    assert note[1] == ("  sudo ufw allow from 192.168.1.0/24 to any port "
                       "8321,8760,8775,8780,8782,8785,8790,8791,8792,8793 proto tcp")


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
    assert by["yantra"].env["SETU_WINDOW_NAME"] == "beast.local"


def test_smritikosh_is_on_the_house_by_its_dashboard_alone(host, monkeypatch):  # noqa: F811
    """Its server, PostgreSQL, Neo4j, MongoDB and Redis are reached by the
    pieces alone, on this computer: only the dashboard is a page."""
    from sarathi import smritikosh

    monkeypatch.setattr(smritikosh, "container", lambda name: {
        "Image": "redis:7", "Config": {"Env": []}, "Mounts": [],
        "HostConfig": {"PortBindings": {"6379/tcp": [{"HostPort": "6379"}]}}})
    from sarathi.config import Smritikosh
    config = housed(memory="smritikosh",
                    smritikosh=Smritikosh(checkout="/x", full=True))
    made = podman.extra_units(config)["sarathi-smritikosh-redis.container"]
    assert "PublishPort=127.0.0.1:6379:6379" in made and "192.168.1.44" not in made
    units = podman.memory_units(config)
    for unit in ("sarathi-smritikosh.container", "sarathi-smritikosh-db.container"):
        assert "192.168.1.44" not in units[unit], unit
    # a rebuilt image's new column reaches the database before any query does
    assert ('Exec=/bin/sh -c "cd /opt/smritikosh && .venv/bin/alembic upgrade head && '
            'exec .venv/bin/uvicorn' in units["sarathi-smritikosh.container"])
    published = podman.lan_ports(config)
    assert 3000 in published and not {5432, 6379, 8080, 8770} & set(published)
