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
