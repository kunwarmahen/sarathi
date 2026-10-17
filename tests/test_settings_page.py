"""Every settings file from the owner's home page (editing.py, home.py).

The bias is A PAGE THAT WRITES WHAT A PROGRAM WOULD REFUSE, OR LETS
SOMEBODY ELSE WRITE AT ALL. Each change goes to the program whose file
it is, with what the form said, and that program's refusal comes back
as the page's answer, with nothing written. Sarathi's own file is read
back as `up` reads it before it's kept. A key goes in and is never sent
back out. And a person signed in gets none of it.
"""

from __future__ import annotations

import json
import stat
import sys

import pytest

from sarathi import config as settings_mod
from sarathi.config import Config, Door, Pages, render
from sarathi.home import Home, HomeServer
from sarathi.people import People

from test_home import GOOD, ask, keys, send  # noqa: F401

STAND_IN = """#!{python}
import json, sys
argv = sys.argv[1:]
log = {log!r}
with open(log, "a") as out:
    out.write(json.dumps({{"argv": argv, "stdin": sys.stdin.read()}}) + "\\n")
if "show" in argv:
    print(json.dumps({{"ok": True, "people": [{{"id": "mahen"}}], "agents": [],
                      "rules": [], "examples": [], "actors": {{"text": "", "path": "a"}},
                      "policy": {{"text": "", "path": "p"}}}}))
elif "refuse" in open(log).read():
    print(json.dumps({{"ok": False, "error": "[actor.x] permissions must be one of ..."}}))
    sys.exit(2)
else:
    print(json.dumps({{"ok": True}}))
"""


@pytest.fixture
def owner_page(keys, world, tmp_path, monkeypatch):  # noqa: F811
    log = tmp_path / "dvara.log"
    dvara = world / "bin" / "dvara"
    dvara.write_text(STAND_IN.format(python=sys.executable, log=str(log)))
    dvara.chmod(dvara.stat().st_mode | stat.S_IXUSR)
    actors = tmp_path / "actors.toml"
    actors.write_text("[actor.mahen]\n")
    config = Config("ollama", pages=Pages(on=True),
                    door=Door(actors=str(actors), root=str(tmp_path / "agents"),
                              state=str(tmp_path / "state"), owner="mahen"))
    settings_mod.settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings_mod.settings_path().write_text(render(config))
    people = People(tmp_path / "people.json")
    server = HomeServer(Home(config, lambda: {}, restart=lambda: None), GOOD, port=0,
                        people=people)
    server.start()
    server.log, server.people_book = log, people
    yield server
    server.stop()


def heard(server):
    return [json.loads(line) for line in server.log.read_text().splitlines()]


def test_the_owner_sees_every_file_and_dvara_is_asked_with_its_folders(owner_page):
    got = json.loads(ask(owner_page, "/api/settings").text)
    assert got["sarathi"]["model"]["provider"] == "ollama"
    assert got["dvara"]["people"] == [{"id": "mahen"}]
    assert got["sarathi"]["keys"]["TELEGRAM_TOKEN"] is False
    argv = heard(owner_page)[0]["argv"]
    assert argv[argv.index("--actors") + 1].endswith("actors.toml")
    assert argv[-1] == "show" or "show" in argv


def test_a_person_is_sent_to_dvara_with_what_the_form_said(owner_page):
    status, got = send(owner_page, "/api/settings/person/priya",
                       {"agents": ["greeter"], "setu": "own", "telegram": ["8675309"]})
    assert status == 200 and "priya saved" in got["said"]
    last = heard(owner_page)[-1]
    assert last["argv"][-3:] == ["settings", "person", "priya"]
    assert json.loads(last["stdin"]) == {"agents": ["greeter"], "setu": "own",
                                         "telegram": ["8675309"]}


def test_a_skill_made_a_tool_asks_dvara_with_this_houses_model(owner_page):
    status, got = send(owner_page, "/api/settings/tool/helper",
                       {"person": "priya", "skill": "greet-someone"})
    assert status == 200
    argv = heard(owner_page)[-1]["argv"]
    assert argv[argv.index("--provider") + 1] == "ollama"
    assert argv[argv.index("settings"):] == ["settings", "tool", "helper", "--person",
                                             "priya", "--skill", "greet-someone"]


def test_a_tool_needs_whose_and_which(owner_page):
    status, got = send(owner_page, "/api/settings/tool/helper", {"person": "priya"})
    assert status == 400 and "whose skill" in got["detail"]


def test_dvaras_refusal_is_the_pages_answer(owner_page):
    owner_page.log.write_text(json.dumps({"argv": ["refuse"], "stdin": ""}) + "\n")
    status, got = send(owner_page, "/api/settings/person/x", {"permissions": "all"})
    assert status == 400 and "permissions must be one of" in got["detail"]


def test_you_cannot_remove_yourself(owner_page):
    status, got = send(owner_page, "/api/settings/person/mahen", {"remove": True})
    assert status == 400 and "yourself" in got["detail"]


def test_sarathis_own_file_is_checked_and_the_old_one_kept(owner_page):
    path = settings_mod.settings_path()
    before = path.read_text()
    status, got = send(owner_page, "/api/settings/sarathi",
                       {"model": {"provider": "ollama", "model": "gemma4:12b"},
                        "dvara": {"on": True, "ntfy": True}})
    assert status == 200 and got["restart"] is True
    after = settings_mod.load()
    assert after.model == "gemma4:12b" and after.door.ntfy_port == 8793
    assert path.with_name("sarathi.toml.bak").read_text() == before
    status, got = send(owner_page, "/api/settings/sarathi", {"yantra": {"port": "99999"}})
    assert status == 400 and "between" in got["detail"]
    status, got = send(owner_page, "/api/settings/text/sarathi", {"text": "[clok]\n"})
    assert status == 400 and "unknown table" in got["detail"]
    assert settings_mod.load().model == "gemma4:12b"


def test_a_key_goes_in_and_never_comes_back_out(owner_page):
    status, _ = send(owner_page, "/api/settings/key/TELEGRAM_TOKEN", {"value": "123:secret"})
    assert status == 200
    body = ask(owner_page, "/api/settings").text
    assert "123:secret" not in body and json.loads(body)["sarathi"]["keys"]["TELEGRAM_TOKEN"]
    assert settings_mod.read_secrets()["TELEGRAM_TOKEN"] == "123:secret"
    assert send(owner_page, "/api/settings/key/PATH", {"value": "/x"})[0] == 400


def test_a_person_signed_in_gets_none_of_it(owner_page):
    link = owner_page.people_book.invite("priya", ["mahen", "priya"], "mahen")
    session = send(owner_page, "/api/claim", {"link": link, "password": "a long password"},
                   token="")[1]["session"]
    assert ask(owner_page, "/api/settings", token=session).status_code == 403
    assert send(owner_page, "/api/settings/person/priya", {"agents": None},
                token=session)[0] == 403
    assert send(owner_page, "/api/settings/key/TELEGRAM_TOKEN", {"value": "x"},
                token=session)[0] == 403


# -- the phone card: Sparsh's own steps, run here, where the cable is -----------------

PHONE_SPARSH = """#!/bin/sh
echo "$@" >> {log}
case "$1" in
  tcpip) echo '{told}';;
  connect) case "$2" in 192.168.1.160:*) echo "connected to $2";;
             *) echo "failed to connect to '$2': Connection refused"; exit 1;; esac;;
  pair) echo "Successfully paired to $2 [guid=adb-1]";;
esac
"""


@pytest.fixture
def with_sparsh(owner_page, world, tmp_path):
    log = tmp_path / "sparsh.log"
    sparsh = world / "bin" / "sparsh"
    told = json.dumps({"serial": "84B7N", "address": "192.168.1.160:5555",
                       "connected": True, "said": "connected to 192.168.1.160:5555"})
    sparsh.write_text(PHONE_SPARSH.format(log=log, told=told))
    sparsh.chmod(sparsh.stat().st_mode | stat.S_IXUSR)
    owner_page.sparsh_log = log
    return owner_page


def test_from_the_cable_the_found_address_is_saved_and_apply_is_asked(with_sparsh):
    status, got = send(with_sparsh, "/api/settings/phone", {"do": "tcpip"})
    assert status == 200 and got["restart"] is True and "Apply" in got["said"]
    assert settings_mod.load().phone.address == "192.168.1.160:5555"
    # the same address again: the containers reconnect by themselves
    status, got = send(with_sparsh, "/api/settings/phone",
                       {"do": "connect", "address": "192.168.1.160:5555"})
    assert status == 200 and got["restart"] is False and "nothing to restart" in got["said"]


def test_an_address_that_does_not_answer_is_said_and_not_saved(with_sparsh):
    status, got = send(with_sparsh, "/api/settings/phone",
                       {"do": "connect", "address": "192.168.1.161:5555"})
    assert status == 400 and "not saved" in got["detail"]
    assert settings_mod.load().phone is None


def test_pairing_runs_sparsh_and_saves_nothing(with_sparsh):
    status, got = send(with_sparsh, "/api/settings/phone",
                       {"do": "pair", "address": "192.168.1.160:37000", "code": "123456"})
    assert status == 200 and "Successfully paired" in got["said"]
    assert settings_mod.load().phone is None
    assert send(with_sparsh, "/api/settings/phone", {"do": "pair"})[0] == 400
    assert send(with_sparsh, "/api/settings/phone", {"do": "reboot"})[0] == 400


def test_a_person_signed_in_cannot_touch_the_phone(with_sparsh):
    link = with_sparsh.people_book.invite("priya", ["mahen", "priya"], "mahen")
    session = send(with_sparsh, "/api/claim", {"link": link, "password": "a long password"},
                   token="")[1]["session"]
    assert send(with_sparsh, "/api/settings/phone", {"do": "tcpip"}, token=session)[0] == 403
    assert not with_sparsh.sparsh_log.exists()
