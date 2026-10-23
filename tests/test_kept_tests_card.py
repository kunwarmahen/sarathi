"""The Kept tests card: what last night said, and the night run asked once.

The bias is A CARD THAT SAYS GREEN WHEN IT CHECKED LESS, and A HOME PAGE
THAT GROWS LOGIC. The card shows Yantra's own summary as it is -- a
suite that could not run is said -- and its one button asks Samay's
own API for Samay's own tests road; Samay checks and keeps the schedule.
Asked twice, it is asked once.
"""

from __future__ import annotations

import json
import urllib.error

from sarathi.config import Config
from sarathi.home import NIGHTLY, Home, kept_tests_status


def config(**over) -> Config:
    return Config(provider="ollama", web_port=8321, clock_port=8780, **over)


def night(tmp_path, **over):
    root = tmp_path / "yantra-tests"
    (root / "yantra").mkdir(parents=True, exist_ok=True)
    (root / "yantra" / "cases.toml").write_text("")
    data = {"format": "yantra.tests.v1", "at": "2026-10-23T03:00:00-04:00",
            "suites": [{"agent": "yantra", "person": "", "cases": 2, "passed": 1,
                        "red": ["kept-a"], "broke": ["kept-a"], "fixed": [],
                        "error": ""}],
            "cases": 2, "passed": 1, "broke": 1, "fixed": 0, "errors": 0,
            "green": False, **over}
    (root / "last.json").write_text(json.dumps(data))
    return root


def test_the_card_shows_yantras_own_summary(world, tmp_path):
    night(tmp_path)
    got = kept_tests_status(config())
    assert got["summary"]["broke"] == 1 and got["suites"] == 1
    assert got["samay"] is False            # nobody answering in tests


def test_a_summary_in_a_shape_it_does_not_know_is_not_shown(world, tmp_path):
    night(tmp_path, format="yantra.tests.v9")
    assert kept_tests_status(config())["summary"] is None


def test_nothing_kept_is_an_empty_card(world):
    got = kept_tests_status(config())
    assert got["summary"] is None and got["suites"] == 0


class Samay:
    def __init__(self, rows=()):
        self.rows, self.asked = list(rows), []

    def __call__(self, _config, method, path, body=None):
        self.asked.append((method, path, body))
        if method == "GET":
            return {"schedules": self.rows}
        self.rows.append({**body, "id": "n1"})
        return self.rows[-1]


def test_the_button_asks_samay_for_its_own_tests_road(world):
    samay = Samay()
    home = Home(config(), dict, ask_samay=samay)
    code, said = home.nightly()
    assert code == 200 and "03:00" in said
    assert samay.asked[-1] == ("POST", "schedules", NIGHTLY)
    assert NIGHTLY["runner"] == "tests"


def test_asked_twice_it_is_asked_once(world):
    samay = Samay([{"runner": "tests", "id": "n1"}])
    code, said = Home(config(), dict, ask_samay=samay).nightly()
    assert code == 200 and "already" in said
    assert [m for m, *_ in samay.asked] == ["GET"]


def test_samay_saying_no_is_said(world):
    def refuses(_c, method, *_a):
        if method == "GET":
            return {"schedules": []}
        raise urllib.error.HTTPError("u", 400, "bad", {}, None)
    code, said = Home(config(), dict, ask_samay=refuses).nightly()
    assert code == 400 and said.startswith("Samay said no")
