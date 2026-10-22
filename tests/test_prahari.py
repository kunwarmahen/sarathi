"""Prahari, the watch, started with the rest.

The bias these tests encode: A WATCH THAT READS ONE PERSON'S ACCOUNTS
MUST BE THAT PERSON'S, AND ITS NEWS MUST REACH THEM. Prahari's looks run
this computer's Yantra with this computer's accounts, so Dvara is told
whose watches they are (the owner, ``--prahari-for``), and Prahari gets
the same door address, token and owner the clock does, so what a watch
sees comes to the owner's chat. And IT IS OPTIONAL: with no Prahari on
this machine, nothing about it is started, published, passed or carded.
"""

from __future__ import annotations

from sarathi import podman, services
from sarathi.config import Config, Door, House, Pages, parse, render
from sarathi.siblings import Found
from test_podman import host, with_door_secrets  # noqa: F401  (the fixture)


def found(*names: str) -> dict[str, Found]:
    return {name: Found(name, f"/bin/{name}", None, None) for name in names}


ALL = ("yantra", "setu", "samay", "prahari", "dvara", "sparsh")


def installed(world) -> None:
    """A prahari beside the other checkouts, the way `status` finds one."""
    program = world / "checkouts" / "prahari" / ".venv" / "bin" / "prahari"
    program.parent.mkdir(parents=True)
    program.write_text("#!/bin/sh\n")
    program.chmod(0o755)


class TestTheSetting:
    def test_on_by_default_and_read_back_as_written(self):
        assert Config("ollama").watch_on and Config("ollama").watch_port == 8782
        off = parse('[model]\nprovider = "ollama"\n[prahari]\non = false\nport = 8799\n')
        assert (off.watch_on, off.watch_port) == (False, 8799)
        assert parse(render(off)) == off and "[prahari]" in render(Config("ollama"))


class TestThePlainRoad:
    def test_it_starts_before_the_door_and_the_page_wired_to_both(self, world, monkeypatch):
        with_door_secrets(world)
        monkeypatch.setattr(services, "model_env", lambda c: {})
        monkeypatch.setattr(services, "door_problems", lambda c, f: [])
        config = Config("ollama", door=Door(owner="mahen"), pages=Pages(on=False))
        planned, _ = services.plan(config, found(*ALL))
        names = [s.name for s in planned]
        assert names.index("prahari") < names.index("dvara") < names.index("yantra")
        watch = next(s for s in planned if s.name == "prahari")
        assert watch.argv == ["/bin/prahari", "serve", "--host", "127.0.0.1", "--port",
                              "8782"]
        assert watch.env["PRAHARI_YANTRA"] == "/bin/yantra"
        assert watch.env["PRAHARI_DVARA_URL"] == "http://127.0.0.1:8770"
        assert watch.env["PRAHARI_DVARA_TOKEN"] == "dvara-token"
        assert watch.env["PRAHARI_DVARA_ACTOR"] == "mahen"
        page = next(s for s in planned if s.name == "yantra").argv
        assert page[page.index("--prahari") + 1] == "/bin/prahari"
        door = next(s for s in planned if s.name == "dvara")
        at = door.argv.index("--prahari")
        assert door.argv[at:at + 4] == ["--prahari", "/bin/prahari", "--prahari-for", "mahen"]
        assert door.env["PRAHARI_DVARA_URL"] == "http://127.0.0.1:8770"

    def test_not_installed_is_nothing_at_all(self, world, monkeypatch):
        monkeypatch.setattr(services, "model_env", lambda c: {})
        planned, notes = services.plan(Config("ollama", pages=Pages(on=False)),
                                       found("yantra", "setu", "samay"))
        assert "prahari" not in [s.name for s in planned]
        page = next(s for s in planned if s.name == "yantra").argv
        assert "--prahari" not in page and "--no-prahari" not in page
        assert not any("prahari" in n for n in notes)

    def test_turned_off_tells_the_page_so(self, world, monkeypatch):
        monkeypatch.setattr(services, "model_env", lambda c: {})
        planned, notes = services.plan(Config("ollama", watch_on=False, pages=Pages(on=False)),
                                       found(*ALL))
        assert "prahari" not in [s.name for s in planned]
        assert "--no-prahari" in next(s for s in planned if s.name == "yantra").argv
        assert any(n.startswith("prahari") and "off in sarathi.toml" in n for n in notes)


class TestThePodmanRoad:
    def test_a_container_of_its_own_and_the_door_names_whose(self, host, world):  # noqa: F811
        with_door_secrets(world)
        installed(world)
        made = podman.units(Config("ollama", road="podman", door=Door(owner="mahen"),
                                   pages=Pages(on=False)))
        unit = made["sarathi-prahari.container"]
        assert "Exec=/usr/local/bin/prahari serve --host 0.0.0.0 --port 8782" in unit
        assert "PublishPort=127.0.0.1:8782:8782" in unit
        assert "Environment=PRAHARI_DVARA_URL=http://sarathi-dvara:8765" in unit
        assert "Environment=PRAHARI_DVARA_ACTOR=mahen" in unit
        assert "Environment=PRAHARI_YANTRA=/usr/local/bin/yantra" in unit
        assert "/.prahari:" in unit                      # its state, mounted everywhere
        door = made["sarathi-dvara.container"]
        assert "--prahari /usr/local/bin/prahari --prahari-for mahen " in door
        assert "After=sarathi-prahari.service" in door
        page = made["sarathi-yantra.container"]
        assert "--prahari /usr/local/bin/prahari" in page
        secrets = podman.unit_secrets(Config("ollama", road="podman",
                                             door=Door(owner="mahen")))
        assert secrets["sarathi-prahari"]["PRAHARI_DVARA_TOKEN"] == "dvara-token"
        assert secrets["sarathi-dvara"]["PRAHARI_DVARA_TOKEN"] == "dvara-token"

    def test_with_a_house_the_inlet_is_published_for_a_phone(self, host, world):  # noqa: F811
        installed(world)
        config = Config("ollama", road="podman", house=House("beast.local", "192.168.1.44"),
                        pages=Pages(on=False))
        unit = podman.units(config)["sarathi-prahari.container"]
        assert "PublishPort=192.168.1.44:8782:8782" in unit
        assert "Environment=PRAHARI_PUBLIC_URL=http://beast.local:8782/" in unit
        assert 8782 in podman.lan_ports(config)

    def test_not_installed_no_unit_no_flag_no_port(self, host, world):  # noqa: F811
        config = Config("ollama", road="podman", house=House("beast.local", "192.168.1.44"),
                        pages=Pages(on=False))
        made = podman.units(config)
        assert "sarathi-prahari.container" not in made
        assert "--prahari" not in made["sarathi-yantra.container"]   # (its folder,
        # empty, is mounted like every data folder: `up` makes them all first)
        assert 8782 not in podman.lan_ports(config)


class TestTheHomePage:
    def test_its_card_when_it_is_here(self, world, monkeypatch):
        from sarathi.home import pages

        monkeypatch.setenv("HOME", str(world / "home"))
        assert "prahari" not in [p.name for p in pages(Config("ollama"))]
        installed(world)
        card = next(p for p in pages(Config("ollama")) if p.name == "prahari")
        assert card.port == 8782 and "inlet" in card.purpose
        assert "prahari" not in [p.name for p in pages(Config("ollama", watch_on=False))]


def test_optional_in_status():
    from sarathi.siblings import SIBLINGS

    assert next(s for s in SIBLINGS if s.name == "prahari").optional
