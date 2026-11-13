"""The house's day ([usage]) and this computer's address for the containers.

The bias, for the day: a ceiling written in sarathi.toml that never reaches
the programs holding it; a minutes line that stops turns instead of saying
so; yesterday's lines counted as today's; a day run out that nobody is told
about the morning after.

And for the address: a pin that goes stale with the router's next lease
and nobody hears; a container started before it knows where this
computer is; a module half-written as a container reads it; a missing
module that stops every container starting; your own containers.conf
rewritten behind your back.
"""

from __future__ import annotations

import json
import subprocess
import time

import pytest

from sarathi import doctor, podman, services, usage
from sarathi.config import Config, ConfigError, Usage, parse, render

@pytest.fixture(autouse=True)
def fenced(world, monkeypatch, tmp_path):
    """Never this computer's settings, state or usage file."""
    monkeypatch.setenv("YANTRA_USAGE_FILE", str(tmp_path / "no-usage.jsonl"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return world


HOUSE = Config("anthropic", road="podman", usage=Usage(day_usd=2.5, day_minutes=120))


def stamp(at: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(at))


class TestTheSetting:
    def test_usage_round_trips_through_sarathi_toml(self):
        text = render(HOUSE)
        assert "[usage]\nday_usd = 2.5\nday_minutes = 120" in text
        assert parse(text).usage == Usage(day_usd=2.5, day_minutes=120)

    def test_none_set_is_no_line(self):
        assert parse(render(Config("ollama"))).usage == Usage()

    @pytest.mark.parametrize("bad", ["day_usd = -1", "day_usd = \"lots\"",
                                     "day_minutes = 1.5", "day_minutes = true"])
    def test_a_bad_number_is_refused_in_words(self, bad):
        with pytest.raises(ConfigError, match="usage.day_"):
            parse(f"[model]\nprovider = \"ollama\"\n[usage]\n{bad}\n")

    def test_the_ceiling_reaches_every_container_and_every_plain_program(self):
        assert podman.container_env(HOUSE)["YANTRA_HOUSE_DAY_USD"] == "2.5"
        plain = services.model_env(HOUSE, {"ANTHROPIC_API_KEY": "k"})
        assert plain["YANTRA_HOUSE_DAY_USD"] == "2.5"
        assert "YANTRA_HOUSE_DAY_USD" not in podman.container_env(Config("ollama"))

    def test_the_settings_form_saves_it(self, tmp_path, monkeypatch):
        from sarathi import editing
        from sarathi.config import settings_path

        settings_path().parent.mkdir(parents=True, exist_ok=True)
        settings_path().write_text(render(Config("ollama")))
        saved = editing.sarathi_apply({"usage": {"day_usd": "1.75", "day_minutes": "90"}})
        assert saved.usage == Usage(day_usd=1.75, day_minutes=90)
        with pytest.raises(editing.EditError, match="dollars"):
            editing.sarathi_apply({"usage": {"day_usd": "a lot"}})


class TestTheDay:
    def test_yesterday_is_its_own_day(self, tmp_path, monkeypatch):
        f = tmp_path / "usage.jsonl"
        monkeypatch.setenv("YANTRA_USAGE_FILE", str(f))
        now = time.time()
        midnight = usage.since_days(1, now)
        rows = [{"at": stamp(midnight - 600), "by": "samay", "usd": 3.0, "seconds": 60},
                {"at": stamp(now), "by": "dvara", "usd": 0.5, "seconds": 120}]
        f.write_text("".join(json.dumps({"format": "yantra.usage.v1", **r}) + "\n"
                             for r in rows))
        today = usage.day(HOUSE, 0, now, memory=False)["against"]
        yesterday = usage.day(HOUSE, 1, now, memory=False)["against"]
        assert today["billed_usd"] == 0.5 and today["minutes"] == 2.0
        assert not today["usd_near"] and yesterday["usd_reached"]

    def test_against_marks_near_reached_and_minutes(self):
        data = {"programs": {"dvara": {"usd": 2.1}}, "total": {"seconds": 7300}}
        got = usage.against(data, 2.5, 120)
        assert got["usd_near"] and not got["usd_reached"] and got["minutes_passed"]


QUIET = usage.against({"programs": {}, "total": {"seconds": 0}}, 2.5, 120)


class TestTheDoctorSaysIt:
    def test_a_quiet_day_is_one_green_line(self):
        [line] = doctor._usage(QUIET, QUIET)
        assert line.level == "green" and "$0.00 billed of $2.50 a day" in line.said

    def test_reached_today_says_billed_turns_wait_for_midnight(self):
        spent = usage.against({"programs": {"d": {"usd": 2.6}}, "total": {"seconds": 0}},
                              2.5, 0)
        [line] = doctor._usage(spent, QUIET)
        assert line.level == "amber" and "wait for midnight" in line.said

    def test_yesterday_run_out_is_the_mornings_news(self):
        spent = usage.against({"programs": {"d": {"usd": 3.0}}, "total": {"seconds": 0}},
                              2.5, 0)
        [line] = doctor._usage(QUIET, spent)
        assert line.level == "amber" and line.said.startswith("yesterday")

    def test_minutes_are_told_never_stopped(self):
        long_day = usage.against({"programs": {}, "total": {"seconds": 9000}}, 0, 120)
        [line] = doctor._usage(long_day, QUIET)
        assert "150 minutes of answering today, past the house's 120" in line.said


class TestTheAddress:
    @pytest.fixture
    def ip(self, monkeypatch):
        said = {"out": "1.1.1.1 via 192.168.1.1 dev eth0 src 192.168.1.44 uid 1000\n"}
        monkeypatch.setattr(podman, "run", lambda argv, **kw: subprocess.CompletedProcess(
            argv, 0, said["out"] if argv[:2] == ["ip", "-4"] else "", ""))
        monkeypatch.setattr(podman.shutil, "which",
                            lambda name, **kw: "/usr/bin/ip" if name == "ip" else None)
        return said

    def test_the_address_is_the_way_outs_source(self, ip):
        assert podman.this_address() == "192.168.1.44"
        ip["out"] = "RTNETLINK answers: Network is unreachable\n"
        assert podman.this_address() is None

    def test_written_whole_into_sarathis_own_module(self, ip):
        assert podman.refresh_host_address() == (None, "192.168.1.44")
        text = podman.host_address_file().read_text()
        assert '[containers]\nhost_containers_internal_ip = "192.168.1.44"\n' in text
        assert podman.written_host_address() == "192.168.1.44"
        assert not podman.host_address_file().with_suffix(".tmp").exists()

    def test_a_new_lease_is_written_and_said(self, ip):
        podman.refresh_host_address()
        ip["out"] = "1.1.1.1 dev wlan0 src 192.168.1.61\n"
        moved = podman.refresh_host_address()
        assert moved == ("192.168.1.44", "192.168.1.61")
        assert "(was 192.168.1.44)" in podman.host_address_line(moved)

    def test_no_network_keeps_the_last_address(self, ip):
        podman.refresh_host_address()
        ip["out"] = ""
        assert podman.refresh_host_address() == ("192.168.1.44", "192.168.1.44")
        assert podman.written_host_address() == "192.168.1.44"

    def test_no_network_ever_still_leaves_a_module_to_load(self, ip):
        ip["out"] = ""
        podman.refresh_host_address()
        assert podman.host_address_file().read_text().rstrip().endswith("[containers]")
        assert podman.written_host_address() is None

    def test_every_container_wants_the_address_first_and_loads_it(self, ip):
        made = podman.units(HOUSE)
        for name, text in made.items():
            if name.endswith(".container"):
                assert "Wants=sarathi-host-address.service\nAfter=sarathi-host-address" in text
                assert f"ContainersConfModule={podman.host_address_file()}" in text
        assert "ContainersConfModule" not in made["sarathi.network"]
        assert "WantedBy" not in podman.host_unit()      # it runs when asked, never alone
        assert "host-address" in podman.host_unit()

    def test_the_doctor_says_a_moved_address_in_red_with_its_button(self):
        [line] = doctor._host({"now": "192.168.1.61", "told": "192.168.1.44"})
        assert line.level == "red" and line.act == doctor.UP
        assert "moved from 192.168.1.44 to 192.168.1.61" in line.said
        [line] = doctor._host({"now": "192.168.1.44", "told": "192.168.1.44"})
        assert line.level == "green"


def test_every_command_still_reaches_podman_from_main(monkeypatch):
    """`host-address` once imported podman inside main(), which made the
    name local to all of main() and broke `sarathi image` and `up`."""
    from sarathi import cli

    called = []
    monkeypatch.setattr(podman, "build", lambda **kw: called.append(kw) or 0)
    monkeypatch.setattr(cli, "_settings_or_none", lambda: None, raising=False)
    try:
        cli.main(["image"])
    except SystemExit:
        pass
    except UnboundLocalError as exc:            # the bug itself
        raise AssertionError(exc) from None
    except Exception:  # noqa: BLE001 -- anything after podman is reached is fine here
        pass
