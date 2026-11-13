"""`sarathi usage`: the house's model use, read and never written.

The bias: a local turn shown as $0.00 beside a cloud turn whose price is
unknown, so the unknown one passes for free; Smritikosh's own calls
missing, so the store that calls a model hundreds of times a day looks
idle; and a database asked for anything but a SELECT.
"""

from __future__ import annotations

import json
import subprocess

from sarathi import usage
from sarathi.config import Config

NOW = 1_800_000_000.0


def write(path, *rows):
    path.write_text("".join(json.dumps({"format": "yantra.usage.v1",
                                        "at": "2027-01-15T03:00:00+0000", **r}) + "\n"
                            for r in rows) + "half a line\n")


def test_each_program_by_its_turns_local_or_billed(tmp_path):
    f = tmp_path / "u.jsonl"
    write(f, {"by": "dvara", "who": "asha via telegram", "local": True, "model": "qwen3.8",
              "input_tokens": 3000, "output_tokens": 50, "seconds": 9, "usd": None},
          {"by": "dvara", "who": "owner", "local": False, "model": "claude-x",
           "input_tokens": 100, "output_tokens": 10, "seconds": 2, "usd": None},
          {"by": "samay", "who": "Samay: Brief (b) · mahen", "local": False,
           "model": "claude-sonnet-5-5", "usd": 0.0123, "seconds": 4})
    data = usage.report(usage.turns(f, 0), [], None, 1)
    dvara = data["programs"]["dvara"]
    assert dvara["turns"] == 2 and dvara["local"] == 1 and dvara["unpriced"] == 1
    assert dvara["who"] == {"asha": 1, "owner": 1}
    assert data["programs"]["samay"]["who"] == {"mahen": 1}
    text = "\n".join(usage.lines(data))
    assert "+1 with no price" in text and "$0.0123" in text


def test_smritikosh_is_asked_one_select_and_listed(tmp_path):
    asked = []

    def run(argv, **kw):
        asked.append(argv)
        if argv[:2] == ["podman", "inspect"]:
            return subprocess.CompletedProcess(argv, 0, "img\tPOSTGRES_USER=sk", "")
        return subprocess.CompletedProcess(argv, 0, "ollama_chat/qwen3.8-64k\t51\t10700\t488\t\n",
                                           "")
    config = Config("ollama", memory="smritikosh", road="podman")
    rows, why = usage.memory_calls(config, NOW, run=run)
    assert why is None and rows[0]["calls"] == 51 and rows[0]["usd"] is None
    sql = asked[-1][-1]
    assert sql.startswith("SELECT ") and "llm_usage" in sql
    assert asked[-1][asked[-1].index("-U") + 1] == "sk"
    text = "\n".join(usage.lines(usage.report([], rows, why, 1)))
    assert "51 calls" in text and "no turns recorded" in text


def test_a_database_that_doesnt_answer_is_said(tmp_path):
    run = lambda argv, **kw: subprocess.CompletedProcess(argv, 1, "", "no")  # noqa: E731
    rows, why = usage.memory_calls(Config("ollama", memory="smritikosh"), NOW, run=run)
    assert rows == [] and "didn't answer" in why


def test_today_starts_at_local_midnight():
    import time
    start = usage.since_days(1, NOW)
    assert time.localtime(start).tm_hour == 0 and start <= NOW < start + 86400
    assert usage.since_days(7, NOW) == start - 6 * 86400
