"""The people in the house, signing in to the home page (people.py).

The bias is A SIGN-IN THAT OPENS MORE THAN ITS CHAT. The home page is a
key ring: behind the owner's key are every program's page and its key.
A person signed in must get their own chat and nothing else -- no cards,
no keys, no memory switch, no inviting -- and must speak to Dvara as
themselves whatever their browser names. So the tests sign a person in
and try every owner's door with their session.

The other bias is A LINK OR A PASSWORD THAT WORKS TWICE. An invite works
once, runs out, and is replaced by a newer one; a reset ends the old
devices; a name gets a few guesses, not a list; and nothing kept on disk
is a secret anybody could use.
"""

from __future__ import annotations

import json
import stat

import pytest

from sarathi import people as people_mod
from sarathi.config import Config, Door, Pages
from sarathi.home import Chat, Home, HomeServer, invite_address
from sarathi.people import People, PeopleError, actor_ids
from test_home import DOOR_KEY, GOOD, ask, door, keys, send  # noqa: F401

ACTORS = """
[actor.mahen]

[actor.priya]
agents = ["greeter"]

[actor.ravi]
"""


@pytest.fixture
def house(keys, tmp_path):  # noqa: F811
    actors = tmp_path / "actors.toml"
    actors.write_text(ACTORS)
    return Config(provider="ollama", pages=Pages(on=True),
                  door=Door(state=str(keys / "door" / "state"), actors=str(actors),
                            owner="mahen", window_host="192.168.1.44"))


@pytest.fixture
def kept(tmp_path):
    return People(tmp_path / "state" / "people.json")


@pytest.fixture
def signed(house, kept, door):  # noqa: F811
    chat = Chat(f"http://127.0.0.1:{door.server_address[1]}", DOOR_KEY, "mahen")
    server = HomeServer(Home(house, lambda: {}), GOOD, port=0, chat=chat, people=kept)
    server.start()
    yield server
    server.stop()


def invited(kept, name="priya"):
    return kept.invite(name, ["mahen", "priya", "ravi"], "mahen")


def claim(server, link, password="a long password"):
    return send(server, "/api/claim", {"link": link, "password": password}, token="")


# ---- the file and the rules -------------------------------------------------------

def test_only_someone_in_dvaras_actors_file_and_not_the_owner_can_be_invited(kept):
    with pytest.raises(PeopleError, match="isn't in Dvara's actors file"):
        kept.invite("stranger", ["mahen", "priya"], "mahen")
    with pytest.raises(PeopleError, match="is you"):
        kept.invite("mahen", ["mahen", "priya"], "mahen")
    with pytest.raises(PeopleError, match="isn't an id"):
        kept.invite("../etc", ["../etc"], "mahen")


def test_an_invite_works_once(kept):
    link = invited(kept)
    name, session = kept.claim(link, "a long password")
    assert name == "priya" and kept.who(session) == "priya"
    with pytest.raises(PeopleError, match="has been used"):
        kept.claim(link, "another long one")


def test_a_newer_invite_replaces_the_older_one(kept):
    old, new = invited(kept), invited(kept)
    with pytest.raises(PeopleError, match="replaced"):
        kept.claim(old, "a long password")
    assert kept.claim(new, "a long password")[0] == "priya"


def test_an_invite_runs_out(kept):
    link = invited(kept)
    data = json.loads(kept.path.read_text())
    data["people"]["priya"]["invite"]["until"] = "2000-01-01T00:00:00+00:00"
    kept.path.write_text(json.dumps(data))
    with pytest.raises(PeopleError, match="run out"):
        kept.claim(link, "a long password")


def test_a_short_password_is_refused_and_the_invite_still_works(kept):
    link = invited(kept)
    with pytest.raises(PeopleError, match="at least 8"):
        kept.claim(link, "short")
    assert kept.claim(link, "long enough now")[0] == "priya"


def test_a_reset_ends_every_old_device(kept):
    _, first = kept.claim(invited(kept), "the first password")
    second = kept.sign_in("priya", "the first password")
    _, third = kept.claim(invited(kept), "a new password now")
    assert kept.who(first) is None and kept.who(second) is None
    assert kept.who(third) == "priya"
    with pytest.raises(PeopleError):
        kept.sign_in("priya", "the first password")
    assert kept.sign_in("priya", "a new password now")


def test_a_wrong_name_and_a_wrong_password_get_the_same_words(kept):
    kept.claim(invited(kept), "the right password")
    with pytest.raises(PeopleError) as wrong_password:
        kept.sign_in("priya", "the wrong password")
    with pytest.raises(PeopleError) as nobody:
        kept.sign_in("nobody", "the right password")
    assert str(wrong_password.value) == str(nobody.value)


def test_a_name_gets_a_few_guesses_then_waits(kept):
    kept.claim(invited(kept), "the right password")
    for _ in range(people_mod.TRIES):
        with pytest.raises(PeopleError, match="don't match"):
            kept.sign_in("priya", "a guess")
    with pytest.raises(PeopleError, match="try again in"):
        kept.sign_in("priya", "the right password")


def test_nothing_on_disk_is_a_secret_anybody_could_use(kept):
    link = invited(kept)
    _, session = kept.claim(link, "the right password")
    raw = kept.path.read_text()
    for secret in (link.partition(".")[2], session, "the right password"):
        assert secret not in raw
    assert stat.S_IMODE(kept.path.stat().st_mode) == 0o600


def test_signing_out_and_going_unused_end_a_device(kept, monkeypatch):
    _, one = kept.claim(invited(kept), "the right password")
    two = kept.sign_in("priya", "the right password")
    kept.leave(one)
    assert kept.who(one) is None and kept.who(two) == "priya"
    assert kept.sign_out("priya") == 1 and kept.who(two) is None
    three = kept.sign_in("priya", "the right password")
    monkeypatch.setattr(people_mod, "IDLE_DAYS", 0)
    assert kept.who(three) is None


def test_the_actors_file_is_read_for_its_ids(tmp_path):
    actors = tmp_path / "actors.toml"
    actors.write_text(ACTORS)
    assert actor_ids(actors) == ["mahen", "priya", "ravi"]
    with pytest.raises(PeopleError, match="can't read"):
        actor_ids(tmp_path / "missing.toml")


def test_the_link_opens_on_the_house_address_or_says_it_is_this_computer_only(house):
    url, reachable = invite_address(house, "priya.x")
    assert url == "http://192.168.1.44:8760/#invite=priya.x" and reachable
    alone = Config(provider="ollama", pages=Pages(on=True), door=Door())
    url, reachable = invite_address(alone, "priya.x")
    assert url == "http://127.0.0.1:8760/#invite=priya.x" and not reachable


# ---- the page --------------------------------------------------------------------

def test_a_person_signs_in_with_the_link_and_speaks_as_themselves(signed, kept, door):  # noqa: F811
    status, got = claim(signed, invited(kept))
    assert status == 200 and got["name"] == "priya"
    session = got["session"]
    assert ask(signed, "/api/me", token=session).json() == {
        "owner": False, "name": "priya", "chat": True}
    status, _ = send(signed, "/api/chat", {"agent": "greeter", "text": "hi",
                                           "actor": "mahen"}, token=session)
    assert status == 200 and door.heard[-1][2]["actor"] == "priya"
    ask(signed, "/api/chat?after=0", token=session)
    assert "actor=priya" in door.heard[-1][1]


def test_a_person_gets_none_of_the_owners_doors(signed, kept, door):  # noqa: F811
    session = claim(signed, invited(kept))[1]["session"]
    assert ask(signed, "/api/pieces", token=session).status_code == 403
    assert ask(signed, "/api/people", token=session).status_code == 403
    assert send(signed, "/api/memory", {"via": "local"}, token=session)[0] == 403
    assert send(signed, "/api/people/ravi/invite", {}, token=session)[0] == 403
    assert send(signed, "/api/people/priya/sign-out", {}, token=session)[0] == 403


def test_the_owner_invites_from_the_page_and_sees_who_is_in(signed, kept):
    status, got = send(signed, "/api/people/priya/invite", {})
    assert status == 200 and got["url"].startswith("http://192.168.1.44:8760/#invite=priya.")
    listed = {p["name"]: p for p in ask(signed, "/api/people").json()["people"]}
    assert set(listed) == {"priya", "ravi"}         # the owner isn't on their own list
    assert listed["priya"]["invite_until"] and not listed["priya"]["signed_up"]
    claim(signed, got["url"].partition("#invite=")[2])
    listed = {p["name"]: p for p in ask(signed, "/api/people").json()["people"]}
    assert listed["priya"]["signed_up"] and listed["priya"]["devices"] == 1
    assert send(signed, "/api/people/stranger/invite", {})[0] == 409


def test_a_signed_out_device_is_turned_away(signed, kept):
    session = claim(signed, invited(kept))[1]["session"]
    assert send(signed, "/api/sign-out", {}, token=session)[0] == 200
    assert ask(signed, "/api/me", token=session).status_code == 401
    status, got = send(signed, "/api/sign-in", {"name": "priya",
                                                "password": "a long password"}, token="")
    assert status == 200 and ask(signed, "/api/me", token=got["session"]).status_code == 200
    assert send(signed, "/api/sign-in", {"name": "priya", "password": "nope nope"},
                token="")[0] == 403


def test_the_owners_key_still_opens_everything(signed):
    assert ask(signed, "/api/me").json()["owner"] is True
    assert ask(signed, "/api/pieces").json()["people"] is True


def test_a_house_address_that_cant_be_listened_on_leaves_the_owners_page(house, kept):
    server = HomeServer(Home(house, lambda: {}), GOOD, port=0, people=kept,
                        also_host="203.0.113.9")
    assert server.also is None and "203.0.113.9" in server.also_problem
    server.httpd.server_close()


def test_my_accounts_asks_dvara_for_their_own_link_only(signed, kept, door):  # noqa: F811
    session = claim(signed, invited(kept))[1]["session"]
    status, _ = send(signed, "/api/chat/accounts-page", {"actor": "mahen"}, token=session)
    assert status == 200
    method, path, body = door.heard[-1]
    assert (method, path.split("?")[0]) == ("POST", "/web/accounts-page")
    assert body["actor"] == "priya" and "actor=priya" in path
    assert send(signed, "/api/chat/accounts-page", {}, token="s.nobody")[0] == 401


def test_notices_on_this_phone_name_their_own_topic_on_the_house_server(house, kept, door):  # noqa: F811
    from dataclasses import replace
    chat = Chat(f"http://127.0.0.1:{door.server_address[1]}", DOOR_KEY, "mahen")
    for config, on in ((house, False), (replace(house, door=replace(house.door,
                                                                     ntfy_port=8793)), True)):
        server = HomeServer(Home(config, lambda: {}), GOOD, port=0, chat=chat, people=kept)
        server.start()
        try:
            session = claim(server, invited(kept))[1]["session"]
            got = ask(server, "/api/chat/push", token=session).json()
        finally:
            server.stop()
        assert got["on"] is on
        if on:
            assert got["server"] == "http://192.168.1.44:8793"
            assert got["topic"] == "dvara-priya-0123456789abcdef"
            assert got["link"] == ("ntfy://192.168.1.44:8793/dvara-priya-0123456789abcdef"
                                   "?secure=false")
