"""The small world every test runs in: its own PATH, its own folders.

Nothing from the real machine leaks in -- not the siblings on its PATH,
not the checkouts beside this one, not the settings in ~/.config.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from sarathi import siblings


def program(where: Path, name: str, prints: str = "", code: int = 0) -> Path:
    where.mkdir(parents=True, exist_ok=True)
    path = where / name
    path.write_text(f"#!/bin/sh\n/bin/cat <<'EOF'\n{prints}\nEOF\nexit {code}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture
def world(tmp_path, monkeypatch):
    """An empty PATH and an empty folder of checkouts; nothing else is seen."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("SARATHI_SIBLINGS", str(tmp_path / "checkouts"))
    monkeypatch.setenv("SARATHI_CONFIG", str(tmp_path / "config"))
    monkeypatch.setenv("SARATHI_STATE", str(tmp_path / "state"))
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_HOST", "YANTRA_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    for s in siblings.SIBLINGS:
        monkeypatch.delenv(siblings.env_name(s), raising=False)
    return tmp_path
