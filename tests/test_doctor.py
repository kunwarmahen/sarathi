"""`sarathi doctor`: what's wrong, green / amber / red, and its fix.

Two biases, pulling against each other:

* **A problem a program already knew, not said.** Setu's expired mark,
  Samay's failed run, a stopped unit, a shut firewall port, an image older
  than the code, a model that holds less than Yantra plans for: each one
  must come out red or amber, with a fix to type.
* **A doctor that cries wolf.** A cloud model isn't tried (that costs a
  call), a turned-off piece isn't missing, the memory store's own
  databases aren't "on an old image", rules nobody can read aren't
  called open OR shut -- and anything unknown is amber, never red.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from sarathi import doctor
from sarathi.config import Config
from sarathi.home import Home, HomeServer
from sarathi.siblings import NOT_ASKED, SIBLINGS, Found

from test_home import GOOD, get


def found(name: str, status: dict | None = None, *, program: str | None = "/bin/x",
          said: str | None = "ok", error: str | None = None) -> Found:
    sibling = next(s for s in SIBLINGS if s.name == name)
    return Found(sibling, program=program, how="path", status=status, said=said,
                 error=error)


def world(**override) -> list[Found]:
    """Every sibling answering well, unless told otherwise."""
    statuses = {
        "yantra": {"provider": "ollama", "model": "qwen3.8-64k", "context_window": 65536,
                   "local": {"answering": True, "pulled": True, "holds": 65536,
                             "holds_from": "num_ctx"}, "problems": []},
        "setu": {"connections": [{"ref": "gmail:me", "expired": None}], "problems": []},
        "samay": {"serving": True, "recent": {"runs": 3, "failed": 0, "named": []}},
        "prahari": {"serving": True},
        "dvara": {"serving": True, "problems": []},
        "sparsh": {"phones": [], "named": []},
    }
    statuses.update(override)
    out = [found(name, data) for name, data in statuses.items()]
    return out + [found("smritikosh", None)]


def probes(**kw) -> doctor.Probes:
    return doctor.Probes(image=kw.get("image", lambda c: {"exists": True, "made": 0,
                                                          "newer": [], "behind": []}),
                         firewall=kw.get("firewall", lambda c: None),
                         disk=kw.get("disk", lambda p: 50 * 1024**3),
                         disk_paths=lambda: [Path("/")])


CONFIG = Config(provider="ollama")
STARTED = [{"name": "yantra", "alive": True, "log": []}]


def lines(found_=None, config=CONFIG, started=STARTED, memory=None, **kw):
    return doctor.examine(config, found_ or world(), started, memory, probes(**kw))


def level(got, about):
    return [line.level for line in got if line.about == about]


class TestAProblemAlreadyKnownIsSaid:
    def test_all_well_is_all_green_and_exits_well(self):
        got = lines()
        assert {line.level for line in got} == {"green"}
        assert doctor.report(got)["ok"] is True

    def test_an_expired_sign_in_is_red_with_the_command(self):
        got = lines(world(setu={"connections": [
            {"ref": "gmail:me", "connector": "gmail", "account": "me",
             "expired": "2026-10-20"}], "problems": []}))
        red = [line for line in got if line.level == "red"]
        assert red[0].about == "setu" and "gmail:me" in red[0].said
        assert red[0].fix.startswith("setu connect gmail --as me")
        assert doctor.report(got)["ok"] is False

    def test_a_failed_schedule_is_named_by_its_own_words(self):
        got = lines(world(samay={"serving": True, "recent": {
            "runs": 2, "failed": 1, "named": [{"prompt": "check my inbox",
                                               "at": "2026-10-23T08:00:00+00:00",
                                               "outcome": "timed_out",
                                               "summary": "no answer in 600s"}]}}))
        amber = next(line for line in got if line.about == "samay")
        assert amber.level == "amber"
        assert '"check my inbox"' in amber.said and "timed out" in amber.said
        assert "no answer in 600s" in amber.said

    def test_a_stopped_piece_is_red_with_the_end_of_its_log(self):
        got = lines(started=[{"name": "dvara", "alive": False,
                              "log": ["starting", "Traceback: port taken", ""]}])
        red = next(line for line in got if line.about == "dvara" and line.level == "red")
        assert "Traceback: port taken" in red.said and red.fix.startswith("sarathi up")

    def test_a_model_holding_less_than_the_plan_is_red(self):
        problem = ("qwen3.8 holds 8192 tokens but Yantra plans for 65536: ... "
                   "Set OLLAMA_CONTEXT_WINDOW=8192, or use a model")
        got = lines(world(yantra={"provider": "ollama", "model": "qwen3.8",
                                  "context_window": 65536, "problems": [problem],
                                  "local": {"answering": True, "pulled": True,
                                            "holds": 8192}}))
        red = next(line for line in got if line.about == "model")
        assert red.level == "red" and red.fix.endswith("context_window = 8192")

    def test_a_model_that_says_nothing_of_its_window_is_amber(self):
        got = lines(world(yantra={"provider": "ollama", "model": "qwen3.8",
                                  "context_window": 8192, "problems": [],
                                  "local": {"answering": True, "pulled": True,
                                            "holds": None}}))
        assert level(got, "model") == ["amber"]

    def test_an_image_older_than_the_code_is_amber_and_says_which(self):
        got = lines(config=replace(CONFIG, road="podman"),
                    image=lambda c: {"exists": True, "made": 0,
                                     "newer": ["yantra ac1a9a7"], "behind": []})
        amber = next(line for line in got if line.about == "image")
        assert "yantra ac1a9a7" in amber.said and "sarathi image" in amber.fix

    def test_no_image_on_the_podman_road_is_red(self):
        got = lines(config=replace(CONFIG, road="podman"),
                    image=lambda c: {"exists": False})
        assert level(got, "image") == ["red"]

    def test_a_shut_port_is_red_with_the_line_that_opens_it(self):
        wall = {"host": "192.168.1.44", "ports": [8760, 8792], "wall": "ufw",
                "open": {8760}, "command": "sudo ufw allow ... 8760,8792"}
        got = lines(firewall=lambda c: wall)
        red = next(line for line in got if line.about == "firewall")
        assert red.level == "red" and "8792" in red.said and "8760" not in red.said
        assert red.fix == "sudo ufw allow ... 8760,8792"

    def test_the_iphones_signature_close_to_its_end_is_amber_and_past_it_red(self):
        soon = lines(world(sparsh={"phones": [], "wda": {"days_left": 1.2,
                                                        "note": "runs out Sat"}}))
        gone = lines(world(sparsh={"phones": [], "wda": {"days_left": -0.5}}))
        assert level(soon, "phone") == ["amber"] and level(gone, "phone") == ["red"]

    def test_a_named_phone_not_connected_says_why(self):
        got = lines(world(sparsh={"phones": [{"serial": "1.2.3.4:5555", "state": "offline",
                                              "note": "not answering over Wi-Fi"}],
                                  "named": [{"name": "nexus", "kind": "Android",
                                             "where": "1.2.3.4:5555"}]}))
        amber = next(line for line in got if line.about == "phone")
        assert "nexus isn't connected: not answering over Wi-Fi" == amber.said

    def test_little_disk_is_red(self):
        got = lines(disk=lambda p: 1024**3)
        assert level(got, "disk") == ["red"]

    def test_a_required_program_missing_is_red(self):
        got = lines([*world()[1:], found("yantra", program=None, said=None)])
        assert level(got, "yantra") == ["red"]

    def test_red_comes_first(self):
        got = lines(disk=lambda p: 1024**3)
        assert got[0].level == "red"


class TestADoctorThatCriesWolf:
    def test_a_cloud_model_is_not_tried(self):
        got = lines(world(yantra={"provider": "anthropic", "model": "claude-opus-5-5",
                                  "context_window": 200000, "problems": []}))
        assert level(got, "model") == ["green"]
        assert "isn't tried" in next(x.said for x in got if x.about == "model")

    def test_unreadable_firewall_rules_are_amber_never_red(self):
        wall = {"host": "192.168.1.44", "ports": [8760], "wall": "ufw", "open": None,
                "command": "sudo ufw allow ..."}
        assert level(lines(firewall=lambda c: wall), "firewall") == ["amber"]

    def test_a_turned_off_door_is_not_asked_and_not_missing(self):
        off = [f for f in world() if f.sibling.name != "dvara"]
        off.append(found("dvara", None, said=NOT_ASKED))
        assert level(lines(off), "dvara") == []

    def test_samay_turned_off_is_not_a_problem(self):
        got = lines(world(samay={"serving": False}),
                    config=replace(CONFIG, clock_on=False))
        assert level(got, "samay") == []

    def test_an_optional_program_missing_is_said_nowhere(self):
        got = lines([*world()[:-1], found("smritikosh", program=None, said=None)])
        assert level(got, "smritikosh") == []

    def test_64000_planned_on_a_65536_model_is_fine(self):
        got = lines(world(yantra={"provider": "ollama", "model": "qwen3.8-64k",
                                  "context_window": 64000, "problems": [],
                                  "local": {"answering": True, "pulled": True,
                                            "holds": 65536}}))
        assert level(got, "model") == ["green"]

    def test_one_disk_is_one_line(self):
        many = doctor.Probes(image=lambda c: None, firewall=lambda c: None,
                             disk=lambda p: 50 * 1024**3,
                             disk_paths=lambda: [Path("/"), Path("/")])
        got = doctor.examine(CONFIG, world(), STARTED, None, many)
        assert level(got, "disk") == ["green"]

    def test_ufw_status_is_read_with_lists_and_ranges(self):
        said = ("Status: active\n\nTo                         Action      From\n"
                "--                         ------      ----\n"
                "8760,8775/tcp              ALLOW       192.168.1.0/24\n"
                "8790:8792/tcp              ALLOW       192.168.1.0/24\n"
                "22                         DENY        Anywhere\n")
        assert doctor.ufw_open(said) == {8760, 8775, 8790, 8791, 8792}


class TestThePagesCheck:
    def test_check_is_the_owners_and_says_the_same(self, tmp_path):
        from test_home import config
        answer = doctor.report(lines())
        home = Home(config(tmp_path), lambda: {}, doctor=lambda: answer)
        server = HomeServer(home, GOOD, port=0)
        server.start()
        try:
            assert get(server, "/api/doctor", token=None).status_code == 401
            got = get(server, "/api/doctor")
            assert got.status_code == 200 and got.json() == json.loads(json.dumps(answer))
        finally:
            server.stop()

    def test_the_check_button_is_on_the_settings_page(self):
        js = (Path(doctor.__file__).parent / "static" / "settings.js").read_text()
        assert '["check", "Check"]' in js and "/api/doctor" in js


def test_the_text_form_puts_each_fix_under_its_line():
    got = lines(disk=lambda p: 1024**3)
    shown = doctor.text(got)
    assert shown.splitlines()[0].startswith("1 to fix")
    assert "      fix: free some space" in shown


# ---- a Google sign-in's end, the buttons, what's new, the morning road -----------

def ends_in(days: float) -> str:
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="seconds")


class TestAGoogleSignInsEnd:
    def setu(self, **row):
        return world(setu={"connections": [{"ref": "gmail:me", "connector": "gmail",
                                            "account": "me", "expired": None, **row}],
                           "problems": []})

    def test_in_its_last_days_it_is_amber_with_setus_page(self):
        line = next(x for x in lines(self.setu(ends=ends_in(2))) if x.about == "setu")
        assert line.level == "amber" and "Google ends this sign-in" in line.said
        assert "setu config google-published on" in line.fix
        assert line.act == doctor.SETU_PAGE

    def test_a_week_away_or_none_is_fine(self):
        assert level(lines(self.setu(ends=ends_in(5))), "setu") == ["green"]
        assert level(lines(self.setu(ends=None)), "setu") == ["green"]

    def test_an_expired_one_is_red_once_not_also_ending(self):
        got = lines(self.setu(ends=ends_in(-1), expired={"since": "x"}))
        assert level(got, "setu") == ["red"]


class TestAButtonOnlyWhereThePageCanDoIt:
    def test_a_stopped_piece_offers_starting_again(self):
        got = lines(started=[{"name": "dvara", "alive": False, "log": []}])
        assert next(x for x in got if x.about == "dvara").act == doctor.UP

    def test_an_old_image_offers_the_rebuild(self):
        got = lines(config=replace(CONFIG, road="podman"),
                    image=lambda c: {"exists": True, "made": 0,
                                     "newer": ["yantra x"], "behind": []})
        assert next(x for x in got if x.about == "image").act["do"] == "image"

    def test_a_window_too_small_for_the_plan_offers_the_right_number(self):
        problem = ("m holds 8192 tokens but Yantra plans for 65536: ... "
                   "Set OLLAMA_CONTEXT_WINDOW=8192, or use a model")
        got = lines(world(yantra={"provider": "ollama", "model": "m", "problems": [problem],
                                  "context_window": 65536, "local": {}}))
        act = next(x for x in got if x.about == "model").act
        assert act["do"] == "window" and act["value"] == 8192

    def test_an_android_offers_bring_it_back_and_an_iphone_nothing(self):
        named = [{"name": "nexus", "kind": "Android", "where": "a"},
                 {"name": "iphone", "kind": "iPhone", "where": "b"}]
        got = [x for x in lines(world(sparsh={"phones": [], "named": named}))
               if x.about == "phone"]
        assert got[0].act == {"do": "phone", "name": "nexus",
                              "label": "Bring it back (plugged in first)"}
        assert got[1].act is None

    def test_root_and_the_mac_get_no_button(self):
        wall = {"host": "h", "ports": [1], "wall": "ufw", "open": set(), "command": "c"}
        got = lines(firewall=lambda c: wall, disk=lambda p: 1024**3)
        assert all(x.act is None for x in got if x.about in ("firewall", "disk"))


class TestWhatsNewSinceTheLastMorning:
    def test_once_said_it_is_not_new_and_a_fix_is_gone(self, tmp_path):
        told = tmp_path / "told.json"
        first = doctor.report(lines(started=[{"name": "dvara", "alive": False, "log": []}]))
        assert [x["about"] for x in doctor.news(first, told)["news"]["new"]] == ["dvara"]
        assert doctor.news(first, told)["news"]["new"] == []
        fixed = doctor.news(doctor.report(lines()), told)["news"]
        assert fixed["new"] == [] and [x["about"] for x in fixed["gone"]] == ["dvara"]


class TestTheDoctorKey:
    def served(self, tmp_path, told):
        from test_home import config
        answer = doctor.report(lines(started=[{"name": "dvara", "alive": False,
                                               "log": []}]))
        home = Home(config(tmp_path), lambda: {}, doctor=lambda: answer)
        server = HomeServer(home, GOOD, port=0, doctor_key="the-doctor-key-long-enough")
        server.start()
        return server

    def test_it_opens_the_doctor_with_news_and_nothing_else(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SARATHI_STATE", str(tmp_path / "state"))
        server = self.served(tmp_path, tmp_path / "told.json")
        try:
            key = "the-doctor-key-long-enough"
            got = get(server, "/api/doctor?news=1", token=key)
            assert got.status_code == 200 and got.json()["news"]["new"]
            assert get(server, "/api/doctor?news=1", token=key).json()["news"]["new"] == []
            for path in ("/api/pieces", "/api/settings", "/api/people", "/api/chat"):
                assert get(server, path, token=key).status_code == 401
            assert "news" not in get(server, "/api/doctor").json()
        finally:
            server.stop()


class TestTheMorningRoad:
    def test_samay_is_asked_once(self, tmp_path):
        from test_home import config
        asked = []

        def samay(cfg, method, path, body=None):
            asked.append((method, body))
            return {"schedules": [{"runner": "doctor"}] if len(asked) > 2 else []}
        home = Home(config(tmp_path), lambda: {}, ask_samay=samay)
        assert home.morning()[0] == 200
        assert asked[1] == ("POST", doctor_home_morning())
        assert "already" in home.morning()[1]

    def test_samay_is_told_where_and_with_which_key(self, tmp_path, monkeypatch):
        from sarathi import services
        from sarathi.config import Pages
        monkeypatch.setenv("SARATHI_STATE", str(tmp_path))
        env = services.doctor_env(replace(CONFIG, pages=Pages(on=True)))
        assert env["SAMAY_DOCTOR_URL"].endswith("/api/doctor?news=1")
        assert len(env["SAMAY_DOCTOR_TOKEN"]) >= 16
        assert services.doctor_env(replace(CONFIG, pages=Pages(on=False))) == {}

    def test_the_rebuild_runs_behind_the_answer(self, tmp_path, monkeypatch):
        from test_home import config
        monkeypatch.setenv("SARATHI_STATE", str(tmp_path))
        ran = []
        home = Home(config(tmp_path), lambda: {}, rebuild=lambda: ran.append(1))
        assert "Rebuilding the image" in home.rebuild() and ran == [1]


def doctor_home_morning():
    from sarathi.home import MORNING
    return MORNING
