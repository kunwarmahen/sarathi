"""The podman road: the image, the units, and what reaches the containers.

The bias these tests encode: A CONTAINER SEES THE SAME THINGS AT THE SAME
PATHS, AND NOTHING SECRET IS WRITTEN INTO A UNIT. The image holds only
committed code, and says what it left out; the data folders are mounted
where they are on the host; the page starts after the clock and shares
nothing else with it, so either comes back alone; a key reaches a
container only through secrets.env, never as a line in a file that can
be pasted; and a unit is rewritten -- and systemd reloaded -- only when sarathi.toml changed it.

podman and systemctl are replaced by a recorder; git is real.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sarathi import podman, services
from sarathi.config import Config, ConfigError

LOCAL = Config("ollama", "gemma4:12b", web_port=8410, clock_port=8790, road="podman")


class Recorder:
    def __init__(self):
        self.calls: list[list[str]] = []
        self.answers: dict[tuple, subprocess.CompletedProcess] = {}

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        for prefix, done in self.answers.items():
            if tuple(argv[:len(prefix)]) == prefix:
                return done
        return subprocess.CompletedProcess(argv, 0, "", "")

    def said(self, *prefix) -> int:
        return sum(1 for c in self.calls if tuple(c[:len(prefix)]) == prefix)


@pytest.fixture
def host(world, monkeypatch):
    monkeypatch.setenv("HOME", str(world / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(world / "home" / ".config"))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.delenv("SAMAY_STATE", raising=False)
    recorder = Recorder()
    monkeypatch.setattr(podman, "run", recorder)
    return recorder


def page(config=LOCAL) -> str:
    return podman.units(config)["sarathi-page.container"]


def test_the_page_starts_after_the_clock_and_shares_nothing_else_with_it(host):
    text = page()
    assert "Wants=sarathi-clock.service\nAfter=sarathi-clock.service" in text
    assert "BindsTo" not in text and "--pid" not in text
    assert "--samay /usr/local/bin/samay" in text and "PublishPort=127.0.0.1:8410:8321" in text
    assert "Upholds" not in podman.units(LOCAL)["sarathi-clock.container"]


def test_with_the_clock_off_there_is_no_clock_and_nothing_bound_to_one(host):
    made = podman.units(Config("ollama", clock_on=False, road="podman"))
    assert list(made) == ["sarathi-page.container"]
    text = made["sarathi-page.container"]
    assert "--no-samay" in text and "sarathi-clock" not in text


def test_every_data_folder_is_mounted_where_it_is_on_the_host(host, world):
    home = world / "home"
    text = page()
    for folder in (home / ".samay", home / ".local/state/setu", home / ".local/state/yantra",
                   home / ".yantra", services.work_dir()):
        assert f"Volume={folder}:{folder}:z" in text
    assert f"Environment=HOME={home}" in text and "UserNS=keep-id" in text


def test_a_local_model_is_reached_on_the_host_and_a_remote_one_where_it_is(host):
    assert "OLLAMA_BASE_URL=http://host.containers.internal:11434/v1" in page()
    remote = Config("ollama", base_url="http://gpu-box:11434/v1", road="podman")
    assert "OLLAMA_BASE_URL=http://gpu-box:11434/v1" in page(remote)


def test_a_key_reaches_the_containers_only_through_secrets_env(host, world):
    cloud = Config("anthropic", road="podman")
    assert "EnvironmentFile" not in page(cloud)
    secrets = world / "config" / "secrets.env"
    secrets.parent.mkdir(parents=True)
    secrets.write_text("ANTHROPIC_API_KEY=sk-secret\n")
    text = page(cloud)
    assert f"EnvironmentFile={secrets}" in text and "sk-secret" not in text


def test_a_key_in_the_shell_does_not_count_on_the_podman_road(host, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-shell")
    with pytest.raises(ConfigError, match="keys come only from there"):
        podman.preflight(Config("anthropic", road="podman"))


def test_no_image_yet_says_how_to_build_one(host):
    host.answers[("podman", "image", "exists")] = subprocess.CompletedProcess([], 1, "", "")
    with pytest.raises(ConfigError, match="run `sarathi image` first"):
        podman.preflight(LOCAL)


def test_processes_from_the_other_road_must_be_stopped_first(host):
    services.state_dir().joinpath("run").mkdir(parents=True)
    services.state_dir().joinpath("run", "page.json").write_text(json.dumps({"pid": 1}))
    with pytest.raises(ConfigError, match="`sarathi down` on the process road first"):
        podman.preflight(LOCAL)


def test_units_are_rewritten_and_systemd_reloaded_only_on_a_change(host):
    assert podman.install(podman.units(LOCAL)) is True
    assert podman.install(podman.units(LOCAL)) is False
    assert host.said("systemctl", "--user", "daemon-reload") == 1
    assert podman.install(podman.units(Config("ollama", clock_on=False, road="podman")))
    assert sorted(p.name for p in podman.unit_dir().iterdir()) == ["sarathi-page.container"]
    assert host.said("systemctl", "--user", "daemon-reload") == 2


def test_the_clocks_address_is_its_own_line_said_from_this_machine(host):
    host.answers[("podman", "logs")] = subprocess.CompletedProcess(
        [], 0, "samay 0.1.0: ...\npage: http://0.0.0.0:8780/#token=abc\n", "")
    assert podman.clock_address(LOCAL) == "http://127.0.0.1:8790/#token=abc"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_the_image_holds_only_what_is_committed_and_says_what_it_left_out(world, tmp_path,
                                                                         monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    checkouts = world / "checkouts"
    for name in podman.CHECKOUTS:
        repo = checkouts / name
        repo.mkdir(parents=True)
        git(repo, "init", "-q")
        (repo / "kept.txt").write_text("committed\n")
        git(repo, "add", ".")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "one")
    (checkouts / "samay" / "kept.txt").write_text("edited, not committed\n")
    (checkouts / "samay" / "new.txt").write_text("never added\n")
    into = tmp_path / "context"
    lines = podman.stage(into)
    assert (into / "samay" / "kept.txt").read_text() == "committed\n"
    assert not (into / "samay" / "new.txt").exists()
    assert (into / "Containerfile").exists()
    samay = next(line for line in lines if line.startswith("samay"))
    assert "2 uncommitted change(s) left out" in samay
    assert "uncommitted" not in next(line for line in lines if line.startswith("yantra"))


def test_a_missing_checkout_is_named(world, tmp_path):
    with pytest.raises(ConfigError, match="yantra, setu, samay"):
        podman.stage(tmp_path / "context")


def test_down_says_the_units_come_back_at_login_unless_removed(host):
    podman.install(podman.units(LOCAL))
    said = podman.down()
    assert said[-1].startswith("they start again at your next login")
    assert (podman.unit_dir() / "sarathi-page.container").exists()
    said = podman.down(remove=True)
    assert said[-1].startswith("units removed")
    assert list(podman.unit_dir().iterdir()) == []
    assert podman.down() == ["no Sarathi units are installed"]
