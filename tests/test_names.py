"""Each piece goes by its project's name: Samay, Dvara, Yantra, Setu, Sarathi.

The bias these tests encode: NOTHING SET UP UNDER AN OLD NAME IS LOST,
AND NO LINE POINTS A BROWSER AT SOMETHING THAT IS NOT A PAGE. A file
that still says [clock], [door] or [web] reads the same as one that says
[samay], [dvara] and [yantra]; one that says both is refused, since one
of the two would be ignored; a record an older `up` wrote under "clock"
is still found, so `down` still stops it; and Dvara's line gives its
port, not an address that answers a browser with "Not Found".
"""

from __future__ import annotations

import json

import pytest

from sarathi import services
from sarathi.config import Config, ConfigError, Door, parse, render

OLD = """[model]
provider = "ollama"
[web]
port = 8400
[clock]
on = false
port = 8781
[door]
on = true
port = 8771
[pages]
home_port = 8761
door_port = 8786
"""


def test_a_file_in_the_old_names_reads_as_the_same_settings():
    new = (OLD.replace("[web]", "[yantra]").replace("[clock]", "[samay]")
           .replace("[door]", "[dvara]").replace("home_port", "sarathi_port")
           .replace("door_port", "dvara_port"))
    assert parse(OLD) == parse(new)
    read = parse(OLD)
    assert (read.web_port, read.clock_on, read.clock_port) == (8400, False, 8781)
    assert read.door.port == 8771
    assert (read.pages.home_port, read.pages.door_port) == (8761, 8786)


@pytest.mark.parametrize("both, says", [
    ("[clock]\non = true\n[samay]\non = true\n", r"both \[clock\] and \[samay\]"),
    ("[pages]\nhome_port = 1\nsarathi_port = 2\n", "both pages.home_port and pages.sarathi_port"),
])
def test_an_old_name_beside_its_new_one_is_refused(both, says):
    with pytest.raises(ConfigError, match=says):
        parse('[model]\nprovider = "ollama"\n' + both)


def test_what_sarathi_writes_uses_only_the_new_names():
    text = render(Config("ollama", door=Door()))
    for old in ("[web]", "[clock]", "[door]", "home_port", "door_port"):
        assert old not in text
    for new in ("[yantra]", "[samay]", "[dvara]", "sarathi_port", "dvara_port"):
        assert new in text


def test_a_record_an_older_up_wrote_is_found_under_the_new_name(world):
    run = services.state_dir() / "run"
    run.mkdir(parents=True)
    (run / "clock.json").write_text(json.dumps({"pid": 1, "url": "http://127.0.0.1:8780/"}))
    services.log_path("clock").parent.mkdir(parents=True, exist_ok=True)
    services.log_path("clock").write_text("page: http://127.0.0.1:8780/\n")
    assert list(services.records()) == ["samay"]
    assert services.log_path("samay").read_text().startswith("page: ")
    assert not (run / "clock.json").exists()


def test_dvaras_line_gives_its_port_and_points_at_the_page_that_is_yours():
    address = "http://127.0.0.1:8770/"
    assert services.place("dvara", address, owner=True) == \
        "on 8770 (no page here; yours is dvara-page, below)"
    assert services.place("dvara", address, owner=False) == \
        "on 8770 (no page here; turn on [pages] for one)"
    assert services.place("yantra", "http://127.0.0.1:8321/", owner=True) == \
        "at http://127.0.0.1:8321/"
