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


def test_a_tool_taken_back_is_asked_of_dvara_with_remove(owner_page):
    status, got = send(owner_page, "/api/settings/tool/helper",
                       {"person": "priya", "skill": "greet-someone", "remove": True})
    assert status == 200 and "a recipe again" in got["said"]
    argv = heard(owner_page)[-1]["argv"]
    assert argv[-1] == "--remove" and "--provider" not in argv     # no model asked


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


def test_voices_are_typed_with_commas_and_a_wrong_name_is_refused(owner_page):
    status, _ = send(owner_page, "/api/settings/sarathi",
                     {"dvara": {"on": True, "voices": "en_US-lessac-medium, hi_IN-pratham-medium"}})
    assert status == 200
    assert settings_mod.load().door.voices == ("en_US-lessac-medium", "hi_IN-pratham-medium")
    status, got = send(owner_page, "/api/settings/sarathi",
                       {"dvara": {"on": True, "voices": "Hindi please"}})
    assert status == 400 and "not a voice's name" in got["detail"]


def test_the_house_is_set_and_cleared_from_the_page(owner_page):
    status, _ = send(owner_page, "/api/settings/sarathi",
                     {"house": {"name": "beast.local", "address": ""}})
    assert status == 200
    assert settings_mod.load().house == settings_mod.House("beast.local")
    view = json.loads(ask(owner_page, "/api/settings").text)["sarathi"]["house"]
    assert view == {"name": "beast.local", "address": None}
    status, got = send(owner_page, "/api/settings/sarathi", {"house": {"name": "a b"}})
    assert status == 400 and "house.name" in got["detail"]
    send(owner_page, "/api/settings/sarathi", {"house": {"name": ""}})
    assert settings_mod.load().house is None


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
  status) case "$SPARSH_WDA" in *:8100) state=device;; *) state=offline;; esac
          printf '{{"format": "sparsh.status.v1", '
          printf '"phones": [{{"serial": "%s", "state": "%s"}}]}}\n' "$SPARSH_WDA" "$state";;
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


def test_a_phone_with_a_name_is_added_and_the_rest_then_need_one(with_sparsh):
    status, got = send(with_sparsh, "/api/settings/phone",
                       {"do": "connect", "address": "192.168.1.160:5555", "name": "nexus"})
    assert status == 200 and "saved as nexus" in got["said"]
    assert settings_mod.load().phone.named[0].address == "192.168.1.160:5555"
    status, got = send(with_sparsh, "/api/settings/phone", {"do": "tcpip"})
    assert status == 400 and "say which one this is (nexus" in got["detail"]
    status, got = send(with_sparsh, "/api/settings/phone", {"do": "remove", "name": "nexus"})
    assert status == 200 and settings_mod.load().phone is None


def test_a_person_signed_in_cannot_touch_the_phone(with_sparsh):
    link = with_sparsh.people_book.invite("priya", ["mahen", "priya"], "mahen")
    session = send(with_sparsh, "/api/claim", {"link": link, "password": "a long password"},
                   token="")[1]["session"]
    assert send(with_sparsh, "/api/settings/phone", {"do": "tcpip"}, token=session)[0] == 403
    assert not with_sparsh.sparsh_log.exists()


def test_use_the_iphone_saves_it_beside_the_android_once_it_answers(with_sparsh):
    send(with_sparsh, "/api/settings/phone", {"do": "tcpip"})
    status, got = send(with_sparsh, "/api/settings/phone", {"do": "iphone", "wda": ""})
    assert status == 200 and got["restart"] is True, got
    assert "the iPhone answers at http://127.0.0.1:8100" in got["said"]
    saved = settings_mod.load().phone
    assert saved.wda == "http://127.0.0.1:8100" and saved.address == "192.168.1.160:5555"
    # the Android's address again: the iPhone stays written beside it
    send(with_sparsh, "/api/settings/phone", {"do": "connect", "address": "192.168.1.160:5555"})
    assert settings_mod.load().phone.wda == "http://127.0.0.1:8100"


def test_an_iphone_that_does_not_answer_is_said_and_not_saved(with_sparsh):
    status, got = send(with_sparsh, "/api/settings/phone",
                       {"do": "iphone", "wda": "http://127.0.0.1:8101"})
    assert status == 400 and "not saved" in got["detail"]
    assert "is WebDriverAgent running on that iPhone?" in got["detail"]
    assert settings_mod.load().phone is None


def test_a_household_fact_goes_to_dvara_as_the_owner(owner_page):
    """Settings → Household: kept by Dvara as the owner (--owner), and only
    the words a change can be made of are sent on."""
    status, got = send(owner_page, "/api/settings/household",
                       {"add": "bins go out Tuesday", "sneak": "x"})
    assert status == 200 and "everyone's agents" in got["said"]
    last = heard(owner_page)[-1]
    assert last["argv"][last["argv"].index("--owner") + 1] == "mahen"
    assert last["argv"][-2:] == ["settings", "household"]
    assert json.loads(last["stdin"]) == {"add": "bins go out Tuesday"}


# -- Settings → Vaani: who each puck answers, asked of Vaani ----------------------------

VAANI = """#!{python}
import json, sys
argv = sys.argv[1:]
with open({log!r}, "a") as out:
    out.write(json.dumps(argv) + "\\n")
if argv[0] == "runs":
    print(json.dumps({{"format": "vaani.runs.v1", "runs": [{{"heard": "what day"}}],
                      "pucks": [{{"name": "kitchen", "person": "owner", "people": []}}],
                      "voices": [{{"person": "owner", "samples": 3}}], "enrolling": None}}))
elif "nobody" in argv:
    print("error: no puck called 'nobody' (yours: kitchen)", file=sys.stderr)
    sys.exit(2)
else:
    print("the kitchen puck: person house (from its next question)")
"""


@pytest.fixture
def with_vaani(owner_page, world, tmp_path):
    from dataclasses import replace
    log = tmp_path / "vaani.log"
    vaani = world / "bin" / "vaani"
    vaani.write_text(VAANI.format(python=sys.executable, log=str(log)))
    vaani.chmod(vaani.stat().st_mode | stat.S_IXUSR)
    owner_page.home.config = replace(owner_page.home.config, voice_on=True)
    owner_page.vaani_log = log
    return owner_page


def test_the_vaani_tab_has_the_pucks_and_voices_but_not_the_questions(with_vaani):
    got = ask(with_vaani, "/api/vaani").json()
    assert got["pucks"][0]["name"] == "kitchen" and got["voices"][0]["person"] == "owner"
    assert "runs" not in got                       # those are on Vaani's own page


def test_a_puck_is_changed_by_vaani_and_its_refusal_is_the_answer(with_vaani):
    code, said = send(with_vaani, "/api/vaani", {"do": "puck", "puck": "kitchen",
                                                 "person": "house",
                                                 "people": ["owner", "asha"]})
    assert code == 200 and "person house" in said["said"]
    code, said = send(with_vaani, "/api/vaani", {"do": "puck", "puck": "nobody",
                                                 "person": "house"})
    assert code == 400 and said["detail"].startswith("no puck called")
    assert send(with_vaani, "/api/vaani", {"do": "puck", "puck": "kitchen",
                                           "people": ["asha", "--x"]})[0] == 400
    assert send(with_vaani, "/api/vaani", {"do": "puck", "puck": "../k"})[0] == 400
    assert send(with_vaani, "/api/vaani", {"do": "enroll", "person": "asha",
                                           "puck": "kitchen"})[0] == 400   # Vaani's page
    asked = [json.loads(line) for line in with_vaani.vaani_log.read_text().splitlines()]
    assert ["puck", "kitchen", "--person", "house", "--people", "owner,asha"] in asked
    assert not any("--x" in ",".join(a) or "../k" in a for a in asked)


def test_vaani_off_or_a_person_signed_in_gets_nothing(with_vaani):
    from dataclasses import replace
    link = with_vaani.people_book.invite("priya", ["mahen", "priya"], "mahen")
    session = send(with_vaani, "/api/claim", {"link": link, "password": "a long password"},
                   token="")[1]["session"]
    assert ask(with_vaani, "/api/vaani", token=session).status_code == 403
    assert send(with_vaani, "/api/vaani", {"do": "puck", "puck": "kitchen"},
                token=session)[0] == 403
    with_vaani.home.config = replace(with_vaani.home.config, voice_on=False)
    assert ask(with_vaani, "/api/vaani").json() == {"on": False}
    assert send(with_vaani, "/api/vaani", {"do": "puck", "puck": "kitchen"})[0] == 409
