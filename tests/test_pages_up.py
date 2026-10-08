"""`sarathi up` starts the pages people look at, wired to what they show.

The bias is A PAGE STARTED WITHOUT WHAT IT NEEDS, OR WITH WHAT IT MUST
NOT HAVE. Dvara's owner page needs the door's token and address to pass
your answers on, and nothing else does; it must ask as the owner the
settings name. Each page's port is a setting, and a taken one says which.
And the home page is the real one: asked for its pieces, it answers.
"""

from __future__ import annotations

import json
import urllib.request

from conftest import fake, free_port, settings
from test_door import door_on, home  # noqa: F401  (the fixture)
from test_up import run, seen

from sarathi import services


def pages_on(stage, extra: str = "") -> dict:
    ports = {"setu": free_port(), "door": free_port(), "home": free_port()}
    fake(stage["world"] / "bin", "setu", {"format": "setu.status.v1", "connections": []})
    settings(stage["world"], stage["ports"],
             extra + f'\n[pages]\non = true\nsetu_port = {ports["setu"]}\n'
                     f'door_port = {ports["door"]}\nhome_port = {ports["home"]}\n')
    return ports


def test_setus_page_and_the_home_page_start_with_their_keys_shown(stage, capsys):
    ports = pages_on(stage)
    code, out = run(capsys, "up")
    assert code == 0, out
    assert f"setu   up at http://127.0.0.1:{ports['setu']}/#token=k-setu" in out
    assert f"home   up at http://127.0.0.1:{ports['home']}/#token=" in out
    assert seen(stage, "setu")["argv"] == ["serve", "--port", str(ports["setu"])]
    assert "owner" not in services.records()          # no door, no owner page


def test_the_owner_page_gets_the_doors_token_and_address_and_asks_as_the_owner(
        stage, home, capsys):  # noqa: F811
    door_port = door_on(stage, home)
    extra = (stage["world"] / "config" / "sarathi.toml").read_text().split("[door]", 1)[1]
    ports = pages_on(stage, "[door]" + extra.replace("[pages]\non = false\n", "")
                     + 'owner = "mahen"\n')
    code, out = run(capsys, "up")
    assert code == 0, out
    page = seen(stage, "dvara-page")
    assert page["argv"] == [
        "--root", str(home / "dvara" / "agents"), "--actors",
        str(home / "dvara" / "actors.toml"), "--state", str(home / "dvara" / "state"),
        "--samay", str(stage["world"] / "bin" / "samay"),     # for each person's schedules
        "page", "--as", "mahen", "--port", str(ports["door"])]
    # Setu's page serves each person their own folder, for /accounts page
    assert seen(stage, "setu")["argv"][-2:] == ["--people",
                                                str(home / "dvara" / "state" / "setu")]
    assert page["env"]["DVARA_TOKEN"] == "d" * 48
    assert page["env"]["DVARA_URL"] == f"http://127.0.0.1:{door_port}"
    assert seen(stage, "dvara")["at"] < page["at"]
    for other in ("setu", "yantra", "samay"):
        assert "DVARA_TOKEN" not in seen(stage, other)["env"]


def test_a_taken_page_port_names_its_setting(stage, capsys):
    import socket
    ports = pages_on(stage)
    with socket.socket() as held:
        held.bind(("127.0.0.1", ports["setu"]))
        held.listen()
        code, out = run(capsys, "up")
    assert code == 1
    assert "change pages.setu_port in sarathi.toml" in out


def test_the_home_page_up_started_answers_with_every_page(stage, capsys):
    ports = pages_on(stage)
    run(capsys, "up")
    token = (services.state_dir() / "home.token").read_text().strip()
    req = urllib.request.Request(f"http://127.0.0.1:{ports['home']}/api/pieces",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as res:
        pieces = {p["name"]: p for p in json.loads(res.read())["pieces"]}
    assert pieces["setu"]["up"] is True and pieces["yantra"]["up"] is True
    assert pieces["setu"]["start"] == "sarathi up"


def test_down_stops_the_pages_too(stage, capsys):
    pages_on(stage)
    run(capsys, "up")
    _, out = run(capsys, "down")
    assert "setu   stopped" in out and "home   stopped" in out


def test_on_one_window_address_setus_page_listens_there_too_and_the_door_links_to_it(
        stage, home, capsys):  # noqa: F811
    door_on(stage, home)
    extra = (stage["world"] / "config" / "sarathi.toml").read_text().split("[door]", 1)[1]
    ports = pages_on(stage, "[door]" + extra.replace("[pages]\non = false\n", "")
                     + 'window_host = "100.101.102.103"\n')
    code, out = run(capsys, "up")
    assert code == 0, out
    assert seen(stage, "setu")["argv"][-2:] == ["--also-host", "100.101.102.103"]
    assert seen(stage, "dvara")["env"]["SETU_PAGE_URL"] == \
        f"http://100.101.102.103:{ports['setu']}/"
