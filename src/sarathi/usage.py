"""`sarathi usage`: what the house's models did today, and for whom.

Every turn any program runs is one line in Yantra's usage file
(``yantra.usage.v1``, Yantra's usage_log.py): the page, the terminal, each
person's turns through Dvara, Samay's runs, Prahari's questions and the
pictures it looks at, Vidhi's steps. The one program that calls a model
without Yantra is Smritikosh, which shortens and files memories with its
own, and keeps each call in its database's ``llm_usage`` table. This puts
the two side by side, one day at a time.

READ, NEVER WRITTEN. Yantra's file is read where Sarathi's containers
share it (``~/.local/state/yantra``). Smritikosh's table is asked with one
``SELECT`` in its database's container, the way `doctor` asks a program
how it is: nothing is changed, and a database that isn't running is said
rather than guessed.

MONEY ONLY WHERE THERE IS A PRICE. A local model's turns are counted in
tokens and seconds, and their dollars are blank, never $0.00. A turn on a
model with no list price says *no price*, so a cloud turn of unknown cost
never passes for a free one.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

FORMAT = "sarathi.usage.v1"
LINE_FORMAT = "yantra.usage.v1"


def usage_file() -> Path:
    named = os.environ.get("YANTRA_USAGE_FILE", "").strip()
    if named:
        return Path(named).expanduser()
    state = os.environ.get("XDG_STATE_HOME", "").strip() or str(Path.home() / ".local/state")
    return Path(state) / "yantra" / "usage.jsonl"


def turns(path: Path, since: float) -> list[dict]:
    from datetime import datetime
    out: list[dict] = []
    try:
        handle = path.open(encoding="utf-8")
    except OSError:
        return out
    with handle:
        for raw in handle:
            try:
                row = json.loads(raw)
                at = datetime.strptime(row["at"], "%Y-%m-%dT%H:%M:%S%z").timestamp()
            except (ValueError, KeyError, TypeError):
                continue
            if row.get("format") == LINE_FORMAT and at >= since:
                out.append(row)
    return out


def memory_calls(config: Any, since: float,
                 run: Callable[..., subprocess.CompletedProcess] = subprocess.run
                 ) -> tuple[list[dict], str | None]:
    """Smritikosh's own model calls since ``since``, by model: one SELECT
    in its database's container. (rows, why not)."""
    if config is None or not getattr(config, "remembers_in_smritikosh", False):
        return [], None
    from sarathi import podman
    from sarathi.drill import live_database
    name = podman.UNITS["smritikosh-db"] if config.road == "podman" \
        else config.smritikosh.database
    twin = live_database(config, run)
    user = twin[1] if twin else "smritikosh"
    stamp = time.strftime("%Y-%m-%d %H:%M:%S%z", time.localtime(since))
    sql = ("SELECT model, count(*), coalesce(sum(prompt_tokens),0), "
           "coalesce(sum(completion_tokens),0), sum(cost_usd) FROM llm_usage "
           f"WHERE created_at >= '{stamp}' GROUP BY model ORDER BY 2 DESC")
    seen = run(["podman", "exec", name, "psql", "-U", user, "-d", user,
                "-AtF", "\t", "-c", sql], capture_output=True, text=True, check=False)
    if seen.returncode != 0:
        return [], "Smritikosh's database didn't answer (is it running? sarathi up)"
    rows = []
    for line in seen.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 5:
            continue
        model, calls, tin, tout, usd = parts
        rows.append({"model": model, "calls": int(calls), "input_tokens": int(tin),
                     "output_tokens": int(tout), "usd": float(usd) if usd else None})
    return rows, None


def report(rows: list[dict], memory: list[dict], memory_why: str | None,
           days: int) -> dict:
    """The day (or days) by program, then by model, plus Smritikosh."""
    by: dict[str, dict] = {}
    for row in rows:
        key = row.get("by") or "yantra"
        b = by.setdefault(key, {"turns": 0, "local": 0, "input_tokens": 0,
                                "output_tokens": 0, "seconds": 0.0, "usd": 0.0,
                                "unpriced": 0, "switched": 0, "models": {}, "who": {}})
        b["turns"] += 1
        b["local"] += 1 if row.get("local") else 0
        b["input_tokens"] += int(row.get("input_tokens") or 0)
        b["output_tokens"] += int(row.get("output_tokens") or 0)
        b["seconds"] += float(row.get("seconds") or 0)
        if row.get("usd") is not None:
            b["usd"] += float(row["usd"])
        elif not row.get("local"):
            b["unpriced"] += 1
        b["switched"] += 1 if row.get("switched") else 0
        model = row.get("model") or "?"
        b["models"][model] = b["models"].get(model, 0) + 1
        who = (row.get("who") or "").split(" via ")[0].split(" · ")[-1] or "-"
        b["who"][who] = b["who"].get(who, 0) + 1
    for b in by.values():
        b["seconds"] = round(b["seconds"], 1)
        b["usd"] = round(b["usd"], 4)
    return {"format": FORMAT, "days": days, "programs": by, "memory": memory,
            "memory_why": memory_why,
            "total": {"turns": sum(b["turns"] for b in by.values()),
                      "usd": round(sum(b["usd"] for b in by.values())
                                   + sum(m["usd"] or 0 for m in memory), 4),
                      "seconds": round(sum(b["seconds"] for b in by.values()), 1)}}


def _tokens(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def lines(data: dict) -> list[str]:
    span = "today" if data["days"] == 1 else f"the last {data['days']} days"
    total = data["total"]
    out = [f"The house's models, {span}: {total['turns']} turns, "
           f"{total['seconds'] / 60:.0f} minutes of answering"
           + (f", ${total['usd']:.2f}" if total["usd"] else ", nothing billed")]
    for name, b in sorted(data["programs"].items(), key=lambda kv: -kv[1]["turns"]):
        money = (f"${b['usd']:.4f}" if b["usd"] else "") + (
            f" (+{b['unpriced']} with no price)" if b["unpriced"] else "")
        where = ("local" if b["local"] == b["turns"] else
                 "cloud" if b["local"] == 0 else f"{b['local']} local")
        out.append(f"  {name:<8} {b['turns']:>4} turns  {where:<9} "
                   f"{_tokens(b['input_tokens']):>7} in / {_tokens(b['output_tokens']):>6} out  "
                   f"{b['seconds'] / 60:>5.1f} min  {money}".rstrip())
        models = ", ".join(f"{m} ×{n}" for m, n in sorted(b["models"].items(),
                                                           key=lambda kv: -kv[1]))
        out.append(f"           {models}")
        whose = ", ".join(f"{w} ×{n}" for w, n in sorted(b["who"].items(),
                                                          key=lambda kv: -kv[1])[:5])
        if whose and whose != "- ×" + str(b["turns"]):
            out.append(f"           for {whose}")
        if b["switched"]:
            out.append(f"           {b['switched']} answered by a model standing by")
    if not data["programs"]:
        out.append("  no turns recorded (programs write this from their next turn on)")
    if data["memory"]:
        calls = sum(m["calls"] for m in data["memory"])
        tin = sum(m["input_tokens"] for m in data["memory"])
        tout = sum(m["output_tokens"] for m in data["memory"])
        usd = sum(m["usd"] or 0 for m in data["memory"])
        out.append(f"  {'smritikosh':<8} {calls:>4} calls  filing memories  "
                   f"{_tokens(tin):>7} in / {_tokens(tout):>6} out"
                   + (f"  ${usd:.4f}" if usd else ""))
        out.append("           " + ", ".join(f"{m['model']} ×{m['calls']}"
                                              for m in data["memory"]))
    elif data["memory_why"]:
        out.append(f"  smritikosh: {data['memory_why']}")
    return out


def since_days(days: int, now: float | None = None) -> float:
    """Local midnight ``days - 1`` days ago: "today" starts at midnight."""
    now = now or time.time()
    day = time.localtime(now)
    midnight = time.mktime((day.tm_year, day.tm_mon, day.tm_mday, 0, 0, 0, 0, 0, -1))
    return midnight - (max(1, days) - 1) * 86400
