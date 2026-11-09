"""Vidhi, routines, started with the rest.

The bias these tests encode: A ROUTINE RUNS AS ITS PERSON, AND WHAT IT
SAYS MUST REACH THEM. Vidhi gets the door's address, token and owner (in
its own names), its folder is in EVERY container -- Samay's, Prahari's
and Dvara's start a run by adding it there -- and Dvara is started with
``--vidhi`` so ``/routines`` and a run's Yes and No answer on every
channel. And IT IS OPTIONAL: with no Vidhi on this machine, nothing about
it is started, published, passed or carded.
"""

from __future__ import annotations

from sarathi import podman, services
from sarathi.config import Config, Door, House, Pages, parse, render
from sarathi.siblings import Found
from test_podman import host, with_door_secrets  # noqa: F401  (the fixture)


def found(*names: str) -> dict[str, Found]:
    return {name: Found(name, f"/bin/{name}", None, None) for name in names}


def installed(world) -> None:
    """A vidhi beside the other checkouts, the way `status` finds one."""
    program = world / "checkouts" / "vidhi" / ".venv" / "bin" / "vidhi"
    program.parent.mkdir(parents=True)
    program.write_text("#!/bin/sh\n")
    program.chmod(0o755)


def test_on_by_default_and_read_back_as_written():
    assert Config("ollama").routine_on and Config("ollama").routine_port == 8786
    off = parse('[model]\nprovider = "ollama"\n[vidhi]\non = false\nport = 8789\n')
    assert (off.routine_on, off.routine_port) == (False, 8789)
    assert parse(render(off)) == off and "[vidhi]" in render(Config("ollama"))


class TestThePodmanRoad:
    def test_a_container_of_its_own_told_where_the_door_is(self, host, world):  # noqa: F811
        with_door_secrets(world)
        installed(world)
        made = podman.units(Config("ollama", road="podman", door=Door(owner="mahen"),
                                   pages=Pages(on=False)))
        unit = made["sarathi-vidhi.container"]
        assert "Exec=/usr/local/bin/vidhi serve --host 0.0.0.0 --port 8786" in unit
        assert "PublishPort=127.0.0.1:8786:8786" in unit
        assert "Environment=VIDHI_DVARA_URL=http://sarathi-dvara:8765" in unit
        assert "Environment=VIDHI_DVARA_ACTOR=mahen" in unit
        assert "Environment=VIDHI_YANTRA=/usr/local/bin/yantra" in unit
        door = made["sarathi-dvara.container"]
        assert "--vidhi /usr/local/bin/vidhi " in door
        assert "/.vidhi:" in door and "/.vidhi:" in made["sarathi-samay.container"]
        assert "--vidhi /usr/local/bin/vidhi" in made["sarathi-yantra.container"]
        secrets = podman.unit_secrets(Config("ollama", road="podman",
                                             door=Door(owner="mahen")))
        assert secrets["sarathi-vidhi"]["VIDHI_DVARA_TOKEN"] == "dvara-token"

    def test_with_a_house_its_page_is_on_the_house_address(self, host, world):  # noqa: F811
        installed(world)
        config = Config("ollama", road="podman", house=House("beast.local", "192.168.1.44"),
                        pages=Pages(on=False))
        unit = podman.units(config)["sarathi-vidhi.container"]
        assert "PublishPort=192.168.1.44:8786:8786" in unit
        assert "Environment=VIDHI_PUBLIC_URL=http://beast.local:8786/" in unit
        assert 8786 in podman.lan_ports(config)

    def test_not_installed_no_unit_no_flag_no_port(self, host, world):  # noqa: F811
        config = Config("ollama", road="podman", house=House("beast.local", "192.168.1.44"),
                        pages=Pages(on=False))
        made = podman.units(config)
        assert "sarathi-vidhi.container" not in made
        assert "--vidhi" not in made["sarathi-yantra.container"]
        assert 8786 not in podman.lan_ports(config)

    def test_turned_off_tells_the_page_so(self, host, world):  # noqa: F811
        installed(world)
        made = podman.units(Config("ollama", road="podman", routine_on=False,
                                   pages=Pages(on=False)))
        assert "sarathi-vidhi.container" not in made
        assert "--no-vidhi" in made["sarathi-yantra.container"]


def test_the_process_road_starts_it_and_tells_the_door(world, monkeypatch):
    installed(world)
    monkeypatch.setattr(services, "model_env", lambda c: {})
    planned, _ = services.plan(Config("ollama", pages=Pages(on=False)),
                               found("yantra", "setu", "samay", "vidhi"))
    vidhi = next(s for s in planned if s.name == "vidhi")
    assert vidhi.argv[1:] == ["serve", "--host", "127.0.0.1", "--port", "8786"]
    assert vidhi.env["VIDHI_YANTRA"] == "/bin/yantra"


# The marketplace, alone. The bias: A MARKETPLACE ON THE INTERNET MUST BE
# THE MARKETPLACE ONLY -- never Vidhi's page with its routines and runs --
# on 127.0.0.1 where Tailscale Funnel reaches it, and the house's own Vidhi
# must be told where to fetch from.


def test_the_marketplace_settings_are_read_back_as_written():
    text = ('[model]\nprovider = "ollama"\n[vidhi]\nmarket_port = 8787\n'
            'market_url = "https://beast.tail.ts.net:10000/"\n')
    config = parse(text)
    assert config.routine_market_port == 8787
    assert config.routine_market_url == "https://beast.tail.ts.net:10000"
    assert parse(render(config)) == config
    import pytest

    from sarathi.config import ConfigError
    with pytest.raises(ConfigError, match="a marketplace's address"):
        parse('[model]\nprovider = "ollama"\n[vidhi]\nmarket_url = "beast:10000"\n')


def test_the_podman_road_runs_the_marketplace_alone_on_this_computer(
        host, world, tmp_path, monkeypatch):  # noqa: F811
    installed(world)
    monkeypatch.setenv("VIDHI_MARKET_DIR", str(tmp_path / "shop"))
    config = Config("ollama", road="podman", house=House("beast.local", "192.168.1.44"),
                    pages=Pages(on=False), routine_market_port=8787,
                    routine_market_url="https://beast.tail.ts.net:10000")
    made = podman.units(config)
    shop = made["sarathi-vidhi-market.container"]
    assert (f"Exec=/usr/local/bin/vidhi market serve --dir {tmp_path / 'shop'} "
            "--host 0.0.0.0 --port 8787") in shop
    assert "PublishPort=127.0.0.1:8787:8787" in shop and "192.168.1.44:8787" not in shop
    assert "VIDHI_MARKET_PUBLIC_URL=https://beast.tail.ts.net:10000" in shop
    assert f"Volume={tmp_path / 'shop'}:" in shop
    assert ("Environment=VIDHI_MARKET=https://beast.tail.ts.net:10000"
            in made["sarathi-vidhi.container"])


def test_a_house_running_its_own_market_fetches_from_it_by_default(world, monkeypatch):
    installed(world)
    monkeypatch.setattr(services, "model_env", lambda c: {})
    planned, _ = services.plan(Config("ollama", pages=Pages(on=False),
                                      routine_market_port=8787),
                               found("yantra", "setu", "samay", "vidhi"))
    shop = next(s for s in planned if s.name == "vidhi-market")
    assert shop.argv[1:4] == ["market", "serve", "--dir"]
    assert shop.argv[-4:] == ["--host", "127.0.0.1", "--port", "8787"]
    vidhi = next(s for s in planned if s.name == "vidhi")
    assert vidhi.env["VIDHI_MARKET"] == "http://127.0.0.1:8787"
